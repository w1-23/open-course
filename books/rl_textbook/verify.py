"""Structural self-check of every produced PDF.

Runs the acceptance checks that can be measured mechanically:

  * page count, size, bookmarks
  * blank pages
  * body text / images spilling into the cue column or the summary band
  * grey or yellow background slivers left over from layout
  * black bars produced by a failed maths render
  * markers that Story failed to place at their intended size
"""
import json
import os
import re
import sys

import fitz

import config

LIGHT_FILLS = [
    (0.9490196, 0.9568627, 0.9686275),
    (0.9647059, 0.9725490, 0.9803922),
    (1.0, 0.9843137, 0.9176471),
    (0.9411765, 0.9490196, 0.9607843),
]


def _near(fill, target, tol=0.02):
    return fill is not None and len(fill) >= 3 and all(
        abs(fill[i] - target[i]) <= tol for i in range(3))


def _first_chapter_page(doc) -> int:
    """1-based page of the first chapter bookmark (0 when the file is a chapter)."""
    for lvl, title, page in doc.get_toc():
        if lvl == 1 and title.startswith("第 "):
            return page
    return 0


def _appendix_pages(doc) -> set[int]:
    """0-based pages of the appendices, which are set full width like the front.

    The symbol table and the formula index are reference tables, not reading
    pages: they have no Cornell frame, so their headings may cross the rule.
    """
    pages: set[int] = set()
    for lvl, title, page in doc.get_toc():
        if lvl == 1 and title.startswith("附录"):
            pages.update(range(page - 1, doc.page_count))
    return pages


def check(path: str) -> dict:
    doc = fitz.open(path)
    info = {
        "file": os.path.basename(path),
        "pages": doc.page_count,
        "mb": round(os.path.getsize(path) / 1048576, 2),
        "bookmarks": len(doc.get_toc()),
        "blank": [],
        "cue_hits": [],
        "band_hits": [],
        "slivers": 0,
        "black_bars": 0,
        "images": 0,
    }
    # Front matter (title, credits, how-to, contents) is set full width and has
    # no Cornell frame, so the column checks do not apply before the first
    # chapter starts.
    skip = _first_chapter_page(doc) - 1
    appendix = _appendix_pages(doc)
    for pno in range(doc.page_count):
        page = doc[pno]
        cornell_page = pno >= skip and pno not in appendix
        # body content must stay inside its column
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                x0, y0, x1, y1 = line["bbox"]
                text = "".join(s["text"] for s in line["spans"]).strip()
                if not text or not cornell_page:
                    continue
                # header / footer furniture lives outside the body band
                if y0 >= config.BODY_Y0 - 2 and y1 <= config.BODY_Y1 + 2:
                    # The writing column sits on the RIGHT: nothing may cross
                    # BODY_X1 into the rule at RULE_X and the blank column.
                    if x1 > config.BODY_X1 + 1.5:
                        if not text.startswith("SUMMARY"):
                            info["cue_hits"].append((pno + 1, text[:24]))
                # Anything between the bottom of the text column and the
                # summary rule is the gap that holds the "SUMMARY / 总结" label:
                # a caption or a table tail drifting there collides with it.
                # (Story text ends at BODY_Y1; furniture is drawn by render.py.)
                if (config.BODY_Y1 + 1 <= y0
                        and y1 <= config.FOOTER_Y - 8):
                    if not text.startswith("SUMMARY"):
                        info["band_hits"].append((pno + 1, text[:24]))

        big_images = 0
        for img in page.get_images(full=True):
            if img[2] <= 3 or img[3] <= 3:
                continue          # the 1x1 maths markers
            big_images += 1
            info["images"] += 1
        if len(page.get_text().strip()) < 60 and big_images == 0:
            info["blank"].append(pno + 1)

        for dr in page.get_drawings():
            r = dr["rect"]
            fill = dr.get("fill")
            if dr["type"] in ("f", "fs") and fill is not None:
                if any(_near(fill, c) for c in LIGHT_FILLS):
                    # a real leftover sliver is a thin bar, not a code chip
                    if r.width > 60 and r.height < 8:
                        info["slivers"] += 1
                if (fill[0] < 0.05 and fill[1] < 0.05 and fill[2] < 0.05
                        and r.width > 60 and 3 < r.height < 40
                        and [it[0] for it in dr["items"]] == ["re"]):
                    info["black_bars"] += 1
    doc.close()
    return info


def _chapter_tails(doc) -> set[int]:
    """章末页的页码集合：每个章/附录起点之前那一页。

    单章 PDF 里"最后一页"天然被 `1 < p < total` 排除，但合订本里章末页
    夹在中间，不排掉就会把每章的收尾留白都报成 thin。
    """
    starts: list[int] = []
    try:
        toc = doc.get_toc()
    except Exception:
        return set()
    for _lvl, title, page in toc:
        t = (title or "").strip()
        if (t.startswith("第") and "章" in t[:6]) or t.startswith("预备") \
                or t.startswith("附录") \
                or re.match(r"第\s*[一二三四五六七八九十\d]+\s*部分", t):
            if page > 1:
                starts.append(page)
    return {s - 1 for s in starts if s > 1}


def _thin_pages(name: str, min_chars: int = 300) -> list[int]:
    """正文过少且没有大图的页：多半是节末溢出造成的"近空白页"。

    它不是错误（每个 ## 强制换页就会产生），但它是"再压两行就能省一页"的
    定位信号——第 2 章曾因为 2 行溢出多出一整页。
    """
    path = os.path.join(config.OUTPUT_DIR, name)
    # 并发构建时另一个进程可能正好在重写这个 PDF，此刻它是 0 字节。
    # 直接 fitz.open 会抛 EmptyFileError 并把整张表打断，所以按"此刻不可读"处理。
    try:
        if os.path.getsize(path) < 1024:
            return []
        doc = fitz.open(path)
    except Exception:
        return []
    tails = _chapter_tails(doc)
    out: list[int] = []
    for pno in range(doc.page_count):
        page = doc[pno]
        if len([c for c in page.get_text() if c.strip()]) >= min_chars:
            continue
        big = False
        for img in page.get_images(full=True):
            try:
                for rect in page.get_image_rects(img[0]):
                    if rect.width > 60 and rect.height > 60:
                        big = True
            except Exception:
                pass
        if big:
            continue
        # 部分分隔页按设计就稀疏（"第 N 部分"+部分标题+章名清单），
        # 不能按"节末溢出"处理。
        head = page.get_text().strip()[:12]
        if re.match(r"第\s*[一二三四五六七八九十\d]+\s*部分", head):
            continue
        # 章末页（下一章/附录开始前的最后一页）按设计是收尾留白：
        # 单章 PDF 里它就是最后一页，合订本里它在前一章的末尾。
        if (pno + 1) in tails:
            continue
        out.append(pno + 1)
    total = doc.page_count
    doc.close()
    return [p for p in out if 1 < p < total]


def main() -> int:
    out = config.OUTPUT_DIR
    files = sorted(f for f in os.listdir(out) if f.lower().endswith(".pdf"))
    skipped = [f for f in files if os.path.getsize(os.path.join(out, f)) < 1024]
    files = [f for f in files if f not in skipped]
    rows = [check(os.path.join(out, f)) for f in files]
    print(f"{'file':38} {'p':>4} {'MB':>6} {'bm':>4} {'img':>4} "
          f"{'blank':>5} {'cue':>4} {'band':>4} {'sliv':>4} {'bar':>3} {'thin':>4}")
    problems = 0
    thin_pages: dict[str, list[int]] = {}
    for r in rows:
        flags = (len(r["blank"]) + len(r["cue_hits"]) + len(r["band_hits"])
                 + r["slivers"] + r["black_bars"])
        problems += flags
        thin = _thin_pages(r["file"])
        thin_pages[r["file"]] = thin
        print(f"{r['file']:38} {r['pages']:4d} {r['mb']:6.2f} "
              f"{r['bookmarks']:4d} {r['images']:4d} {len(r['blank']):5d} "
              f"{len(r['cue_hits']):4d} {len(r['band_hits']):4d} "
              f"{r['slivers']:4d} {r['black_bars']:3d} {len(thin):4d}")
        for kind in ("blank", "cue_hits", "band_hits"):
            if r[kind]:
                print(f"    {kind}: {r[kind][:6]}")
    total_thin = sum(len(v) for v in thin_pages.values())
    for name, pages in thin_pages.items():
        if pages:
            print(f"    thin (正文 <300 字，多为节末溢出或图占位): {name} → {pages[:8]}")
    print(f"\ntotal pages {sum(r['pages'] for r in rows)} | "
          f"problems {problems} | thin pages {total_thin}")
    # 「近空白页」只作提示，不计入 problems：它多半是分节强制换页的副产物，
    # 但作者可以用它定位"少了 2 行就掉一页"的位置（第 2 章的经验）。
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
