"""Build entry point: one lecture, all lectures, or merge only.

    python main.py --only 1        # single lecture (by 1-based index)
    python main.py --all           # every lecture + combined book
    python main.py --merge         # rebuild the combined book from existing PDFs
"""

import argparse
import json
import os
import sys
import time

import fitz

import config
import render
from tools import frontmatter


def load_math_cache() -> dict[str, str]:
    if not os.path.exists(config.MATH_JSON):
        raise SystemExit(f"math cache missing: {config.MATH_JSON}\nrun mathjax.py first")
    with open(config.MATH_JSON, encoding="utf-8") as fh:
        return json.load(fh)


def build_one(index: int, math_cache, out_dir: str, keep_temp=False) -> dict:
    slug, title, stem = config.LECTURES[index]
    t0 = time.time()
    info = render.render_lecture(index, slug, title, stem, math_cache, out_dir, keep_temp)
    info["seconds"] = round(time.time() - t0, 1)
    print(f"  {info['file']}: {info['pages']}p, {info['images']} imgs, "
          f"{info['formula_overlays']} formulas, {info['size_bytes'] / 1048576:.2f} MB, "
          f"{info['seconds']}s")
    return info


def merge(results: list[dict], out_dir: str) -> dict:
    """Combine the per-lecture PDFs into one book with re-based bookmarks."""
    out = fitz.open()
    toc = []
    body_starts = []
    offset = 0
    for r in results:
        path = os.path.join(out_dir, r["file"])
        src = fitz.open(path)
        body_starts.append(offset + 1)
        out.insert_pdf(src)
        for entry in r["toc"]:
            level, title, page = entry[0], entry[1], entry[2]
            toc.append([level, title, page + offset])
        offset += src.page_count
        src.close()

    # Add front matter with a hierarchical contents generated from chapter
    # bookmarks. Printed body page numbers restart at 1 after the front pages.
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    os.makedirs(config.PDF_COMBINED_DIR, exist_ok=True)
    front_path = os.path.join(config.CACHE_DIR, "combined_frontmatter.pdf")
    frontmatter.make_frontmatter(toc, front_path)
    front = fitz.open(front_path)
    front_count = front.page_count
    out.insert_pdf(front, start_at=0)
    front.close()

    # Replace chapter-local page numbers with one continuous body page count so
    # the printed numbers agree with the contents page.
    for pno in range(front_count, out.page_count):
        page = out[pno]
        page.add_redact_annot(fitz.Rect(510, 812, 562, 834), fill=(1, 1, 1))
        page.apply_redactions()
        label = str(pno - front_count + 1)
        width = fitz.Font(fontfile=config.FONT_LATIN).text_length(label, fontsize=8)
        page.insert_font(fontname="globalnum", fontfile=config.FONT_LATIN)
        page.insert_text(fitz.Point(561 - width, config.FOOTER_Y), label,
                         fontsize=8, fontname="globalnum", color=config.LABEL_GREY)

    shifted_toc = [[level, title, page + front_count] for level, title, page in toc]
    front_toc = [
        [1, "封面", 1],
        [1, "版权与出处说明", 2],
        [1, "使用说明", 3],
        [1, "目录", 4],
    ]
    if front_count > 4:
        front_toc.append([1, "目录（续）", 5])
    out.set_toc(front_toc + shifted_toc)
    out.set_metadata({"title": config.COURSE_TITLE,
                      "subject": "个人学习教材；递归自我改进的概念、方法与证据",
                      "keywords": "RSI, recursive self-improvement, textbook"})
    out.subset_fonts()
    combined = os.path.join(config.PDF_COMBINED_DIR, f"{config.COMBINED_STEM}.pdf")
    out.save(combined, garbage=4, deflate=True, clean=True)
    pages = out.page_count
    out.close()

    return {
        "file": os.path.basename(combined),
        "path": combined,
        "pages": pages,
        "size_bytes": os.path.getsize(combined),
        "bookmarks": len(front_toc) + len(toc),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, help="1-based lecture index")
    ap.add_argument("--all", action="store_true", help="build every lecture")
    ap.add_argument("--merge", action="store_true", help="only rebuild the combined book")
    ap.add_argument("--keep-temp", action="store_true")
    args = ap.parse_args()

    os.makedirs(config.PDF_CHAPTER_DIR, exist_ok=True)
    os.makedirs(config.PDF_COMBINED_DIR, exist_ok=True)
    os.makedirs(config.OUTPUT_NOTES_DIR, exist_ok=True)
    math_cache = load_math_cache()
    print(f"math cache: {len(math_cache)} formulas")

    if args.only:
        build_one(args.only - 1, math_cache, config.PDF_CHAPTER_DIR, args.keep_temp)
        return 0

    if args.merge:
        results = []
        for i in range(len(config.LECTURES)):
            stem = config.LECTURES[i][2]
            path = os.path.join(config.PDF_CHAPTER_DIR, f"{stem}.pdf")
            if not os.path.exists(path):
                continue
            doc = fitz.open(path)
            results.append({"file": f"{stem}.pdf", "pages": doc.page_count,
                            "toc": doc.get_toc()})
            doc.close()
        info = merge(results, config.PDF_CHAPTER_DIR)
        print(f"merged: {info['file']} {info['pages']}p "
              f"{info['size_bytes'] / 1048576:.1f} MB")
        return 0

    if not args.all:
        ap.error("choose --only N, --all, or --merge")

    results = []
    for i in range(len(config.LECTURES)):
        print(f"[{i + 1}/{len(config.LECTURES)}] {config.LECTURES[i][0]}")
        try:
            results.append(build_one(i, math_cache, config.PDF_CHAPTER_DIR, args.keep_temp))
        except Exception as exc:
            print(f"  [error] {exc}", file=sys.stderr)
            raise

    print("\nmerging...")
    merged = merge(results, config.PDF_CHAPTER_DIR)
    print(f"  {merged['file']}: {merged['pages']}p, {merged['bookmarks']} bookmarks, "
          f"{merged['size_bytes'] / 1048576:.1f} MB")

    report = {
        "course": config.COURSE_TITLE,
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "output_dir": config.OUTPUT_DIR,
        "lectures": [{k: v for k, v in r.items() if k != "toc"} for r in results],
        "combined": merged,
        "totals": {
            "lectures": len(results),
            "pages": sum(r["pages"] for r in results),
            "images": sum(r["images"] for r in results),
            "formulas": sum(r["formulas"] for r in results),
            "math_failed": sum(r["math_failed"] for r in results),
            "bytes": sum(r["size_bytes"] for r in results) + merged["size_bytes"],
        },
    }
    with open(config.REPORT_PATH, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    t = report["totals"]
    print(f"\ndone: {t['lectures']} lectures, {t['pages']} pages, "
          f"{t['images']} images, {t['formulas']} formulas, "
          f"{t['bytes'] / 1048576:.1f} MB total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
