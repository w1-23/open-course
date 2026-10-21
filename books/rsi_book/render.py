"""Render one lecture to a Cornell-layout PDF.

Pipeline per lecture:
  1. prepare()  -> Story HTML with marker placeholders + asset bag
  2. Story.write()  -> temporary PDF that reserves the right box for each formula
  3. decode markers -> exact placement rectangles
  4. white-out the marker, overlay the vector formula via show_pdf_page
  5. draw Cornell rules, header, footer, cue labels
  6. bookmarks from heading positions, subset fonts, save
"""

import html as htmllib
import os
import re
import struct
import zlib

import fitz
from PIL import Image

import config
import layout
import prepare


# ------------------------------------------------------------------ markers
def decode_marker(img: dict, tmp_path: str) -> int | None:
    """Decode the formula index out of a 1x1 marker image.

    Returns None for anything that is not a marker.  This check is essential:
    an arbitrary photo's top-left pixel (usually black, i.e. index 0) decodes
    into the same 24-bit space as a marker index, so without the size test a
    real illustration would be silently replaced by whichever formula happens
    to own that index.
    """
    if img.get("width") != 1 or img.get("height") != 1:
        return None
    with open(tmp_path, "wb") as fh:
        fh.write(img["image"])
    px = Image.open(tmp_path).convert("RGB").getpixel((0, 0))
    idx = px[0] | (px[1] << 8) | (px[2] << 16)
    return None if idx == 0xFFFFFF else idx


def svg_to_pdf_bytes(svg_text: str, tmp_svg: str) -> bytes:
    with open(tmp_svg, "w", encoding="utf-8") as fh:
        fh.write(svg_text)
    doc = fitz.open(tmp_svg)
    data = doc.convert_to_pdf()
    doc.close()
    return data


# ------------------------------------------------------------------ archive
def build_archive(assets: prepare.AssetBag) -> fitz.Archive:
    arch = fitz.Archive()
    arch.add(config.FONT_CJK, "song.ttf")          # 宋体
    arch.add(config.FONT_CJK_BOLD, "hei.ttf")      # 黑体
    arch.add(config.FONT_LATIN, "latin.ttf")       # Times New Roman
    arch.add(config.FONT_LATIN_BOLD, "latinb.ttf") # Times New Roman Bold
    arch.add(config.FONT_MONO, "mono.ttf")
    for name, path in assets.files.items():
        arch.add(path, name)
    for name, text in assets.svgs.items():
        tmp = os.path.join(config.CACHE_DIR, "_svg_" + name)
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
        arch.add(tmp, name)
    return arch


# ------------------------------------------------------------------ cleanup
# Only the inline `code` chip keeps a background colour in the CSS; MuPDF Story
# documents the block-boxes with borders instead, because an interrupted block
# background is re-painted as a 10pt sliver in the next page's top margin.
LIGHT_FILLS = [
    (0.9490196108818054, 0.95686274766922, 0.9686274528503418),     # code chip
]


def _is_light(fill) -> bool:
    if not fill or len(fill) != 3:
        return False
    return any(all(abs(a - b) < 0.012 for a, b in zip(fill, ref)) for ref in LIGHT_FILLS)


def clean_stray_bands(page) -> int:
    """Erase a box background that Story painted in the page's top margin.

    The signature of the artifact is exact: the sliver starts above
    ``BODY_Y0`` and ends within a few points of it, so it cannot belong to any
    body content. Anything that starts at or below the body top is left alone.
    """
    removed = 0
    for dr in page.get_drawings():
        if dr["type"] not in ("f", "fs"):
            continue
        if not _is_light(dr.get("fill")):
            continue
        r = fitz.Rect(dr["rect"])
        if r.height < 1.2 or r.width < 1.2:
            continue
        if r.y0 < config.BODY_Y0 - 0.5 and r.y1 <= config.BODY_Y0 + 6.5:
            page.draw_rect(r + (-0.6, -0.6, 0.6, 0.6),
                           color=(1, 1, 1), fill=(1, 1, 1), width=0.4)
            removed += 1
    return removed


# ------------------------------------------------------------------ furniture
_MEASURE_FONT = {}


def _measure(text: str, size: float) -> float:
    """Width in points using the real CJK body font (helv metrics are ~2.5x off)."""
    font = _MEASURE_FONT.get("body")
    if font is None:
        font = fitz.Font(fontfile=config.FONT_BODY)
        _MEASURE_FONT["body"] = font
    return font.text_length(text, fontsize=size)


def _measure_latin(text: str, size: float) -> float:
    font = _MEASURE_FONT.get("latin")
    if font is None:
        font = fitz.Font(fontfile=config.FONT_LATIN)
        _MEASURE_FONT["latin"] = font
    return font.text_length(text, fontsize=size)


def _measure_mixed(text: str, size: float) -> float:
    parts = re.split(r"([\x20-\x7E]+)", text)
    return sum(_measure_latin(part, size) if re.fullmatch(r"[\x20-\x7E]+", part)
               else _measure(part, size) for part in parts if part)


def _insert_mixed(page, point: fitz.Point, text: str, size: float, color) -> None:
    """Draw Chinese in SimSun and every Latin/digit run in Times New Roman."""
    x = point.x
    for part in re.split(r"([\x20-\x7E]+)", text):
        if not part:
            continue
        is_latin = re.fullmatch(r"[\x20-\x7E]+", part) is not None
        fontname = "latin" if is_latin else "cjk"
        page.insert_text(fitz.Point(x, point.y), part, fontsize=size,
                         fontname=fontname, color=color)
        x += (_measure_latin(part, size) if is_latin else _measure(part, size))


def _truncate(text: str, size: float, width: float) -> str:
    """Shorten from the right with an ellipsis until it fits in `width` points."""
    text = " ".join((text or "").split())
    if not text or _measure(text, size) <= width:
        return text
    ell = "…"
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _measure(text[:mid] + ell, size) <= width:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo] + ell if lo else ""


def draw_cornell(doc: fitz.Document, cue_labels: dict[int, str],
                 lecture_title: str, lecture_no: str,
                 chapter_label: str | None = None) -> None:
    """Cornell rules, header, footer and running section label.

    The cue column and the summary band are left completely blank on purpose:
    they are the two writing areas this layout reserves for handwriting.
    chapter_label overrides "第 NN 章" in header/footer (used for the appendix).
    """
    for pno in range(doc.page_count):
        page = doc[pno]

        # The cue rule stops at the summary band so that band stays full width.
        page.draw_line(fitz.Point(config.RULE_X, config.RULE_TOP),
                       fitz.Point(config.RULE_X, config.SUMMARY_RULE_Y),
                       color=config.RULE_GREY, width=0.5)
        page.draw_line(fitz.Point(config.SUMMARY_X0, config.SUMMARY_RULE_Y),
                       fitz.Point(config.SUMMARY_X1, config.SUMMARY_RULE_Y),
                       color=config.RULE_GREY, width=0.5)
        page.insert_font(fontname="cjk", fontfile=config.FONT_BODY)
        page.insert_font(fontname="latin", fontfile=config.FONT_LATIN)

        # header: course + lecture on the left, running section on the right.
        # The section label lives in the top margin, never in the writing
        # column, so that column stays completely free for handwriting.
        head_size = 7.2
        chap = chapter_label or f"第 {lecture_no} 章"
        head = f"RSI · {chap} · {lecture_title}"
        _insert_mixed(page, fitz.Point(config.MARGIN_LEFT, config.HEADER_Y - 5),
                      head, head_size, config.LABEL_GREY)

        cue = cue_labels.get(pno)
        if cue:
            room = (config.SUMMARY_X1 - config.MARGIN_LEFT
                    - _measure_mixed(head, head_size) - 18)
            label = _truncate(cue, 7.0, max(0.0, room))
            if label:
                w = _measure_mixed(label, 7.0)
                _insert_mixed(page, fitz.Point(config.SUMMARY_X1 - w, config.HEADER_Y - 5),
                              label, 7.0, config.LABEL_GREY)

        # footer
        _insert_mixed(page, fitz.Point(config.MARGIN_LEFT, config.FOOTER_Y),
                      (chapter_label or lecture_no) + f" · {lecture_title}",
                      7, config.LABEL_GREY)
        label = str(pno + 1)
        w = _measure_latin(label, 8)
        page.insert_text(fitz.Point(config.SUMMARY_X1 - w, config.FOOTER_Y),
                         label, fontsize=8, fontname="latin", color=config.LABEL_GREY)

        # summary band label
        page.insert_text(fitz.Point(config.MARGIN_LEFT, config.SUMMARY_RULE_Y - 6),
                         "SUMMARY / 总结", fontsize=7, fontname="cjk",
                         color=config.LABEL_GREY)


# ------------------------------------------------------------------ render
# ------------------------------------------------- squashed-marker detection
def _insert_breaks(body: str, ids: set, avoid: set = frozenset(),
                   nudge: set = frozenset(), placer=None) -> str:
    """Force a page break, and optionally a no-split rule, on marker blocks.

    A display formula owns a ``<p id="mkpN">``; an inline formula is anchored
    on whatever block carries it (see prepare._tag_inline_anchors), which may
    be a shared paragraph whose id belongs to the first formula in it — hence
    the anchor lookup through the placer rather than a fixed name.
    """
    def anchor_of(idx):
        if placer is not None:
            a = placer.entries.get(idx, {}).get("anchor")
            if a:
                return a
        return f"mkp{idx}"

    out = body
    seen = set()
    for idx in sorted(ids):
        anchor = anchor_of(idx)
        if anchor in seen:
            continue
        seen.add(anchor)
        # Several inline formulas can share one paragraph, so the same anchor
        # may arrive more than once; breaking that block twice would only add
        # an empty page.
        key = f'id="{anchor}"'
        pos = out.find(key)
        if pos < 0:
            continue
        start = out.rfind("<", 0, pos)
        if start < 0:
            continue
        out = (out[:start]
               + '<div style="page-break-before: always;"></div>'
               + out[start:])
    for idx in sorted(avoid):
        key = f'id="{anchor_of(idx)}"'
        pos = out.find(key)
        if pos < 0:
            continue
        start = out.rfind("<", 0, pos)
        end = out.find(">", pos)
        if start < 0 or end < 0:
            continue
        tag = out[start:end]
        if "break-inside" in tag:
            continue
        # Keeping the whole block on one page moves it away from the foot of the
        # page, which is the only place MuPDF squeezes a picture.  Long blocks
        # simply ignore the rule and are left to the scaled overlay.
        out = out[:start] + tag.replace(
            f' {key}', f' style="break-inside:avoid;" {key}', 1) + out[end:]
    for idx in sorted(nudge):
        # A line break in front of the picture puts it at the start of a line,
        # where there is a full line of room, so it is never squeezed.
        key = f'<img src="mk{idx}.png"'
        pos = out.find(key)
        if pos < 0:
            continue
        out = out[:pos] + "<br/>" + out[pos:]
    return out


def _expected_size(placer, idx: int) -> tuple:
    """The box size the layout was asked to reserve for this marker."""
    entry = placer.entries[idx]
    if entry.get("kind") == "diagram":
        return placer.diagram_size(idx)
    return placer.sheet_size(idx)


def _squashed_markers(placer, pdf_path: str, work: str) -> list:
    """Return [(idx, page, ratio)] for markers Story failed to place at size."""
    bad = []
    doc = fitz.open(pdf_path)
    try:
        for pno in range(doc.page_count):
            page = doc[pno]
            for img in page.get_images(full=True):
                xref = img[0]
                idx = decode_marker(doc.extract_image(xref),
                                    os.path.join(work, "_decode.png"))
                if idx is None or idx not in placer.entries:
                    continue
                try:
                    w, h = _expected_size(placer, idx)
                except Exception:
                    continue
                if w <= 0 or h <= 0:
                    continue
                # An inline marker deliberately reserves less height than the
                # formula needs (see prepare.MathPlacer._tag) so MuPDF has no
                # reason to squeeze it, and the formula is drawn at full size
                # afterwards.  The reserved WIDTH is what keeps the sentence
                # flowing, so that is the dimension worth checking.
                for rect in page.get_image_rects(xref):
                    if rect.width < 0.5:
                        bad.append((idx, pno + 1, 0.0))
                        continue
                    k = rect.width / w
                    if k < 0.985:
                        bad.append((idx, pno + 1, round(k, 3)))
                        continue
                    # An inline formula sitting on the very last baseline of a
                    # page has its whole descender below BODY_Y1: the overlay is
                    # drawn bottom-anchored on the marker, so it bleeds into the
                    # summary band.  Treat that as a layout defect too — the
                    # nudge/break machinery will move it to a fresh line/page.
                    if rect.y1 > config.BODY_Y1 + 2.0:
                        bad.append((idx, pno + 1, 1.0))
    finally:
        doc.close()
    return bad


def render_lecture(index: int, slug: str, title: str, stem: str,
                   math_cache: dict[str, str], out_dir: str,
                   keep_temp: bool = False) -> dict:
    lecture_no = config.lecture_no(index)
    chap_label = ("第 0 章" if slug == "ch00" else
                  "附录" if slug == "appx" else None)
    url = config.lecture_url(slug)
    work = os.path.join(config.CACHE_DIR, "work", slug)
    os.makedirs(work, exist_ok=True)

    body, assets, placer, stats = prepare.prepare(slug, url, math_cache, work)
    arch = build_archive(assets)

    tmp_pdf = os.path.join(work, "stage1.pdf")

    # MuPDF squeezes a marker image down into the space left at the bottom of a
    # page instead of carrying it over to the next one, which silently squashed
    # formulas to a fraction of their size.  Lay the lecture out, look for
    # markers whose placed aspect ratio is wrong, force those paragraphs onto a
    # fresh page and lay it out again.  Two extra passes is plenty.
    breaks: set[int] = set()
    avoids: set[int] = set()
    nudges: set[int] = set()
    squashed: list = []
    headings: list = []
    for _attempt in range(5):
        # A fresh file per pass: MuPDF cannot always delete the previous one,
        # and a partly written stage would poison the next attempt.
        tmp_pdf = os.path.join(work, f"stage1_{_attempt}.pdf")
        html_body = (_insert_breaks(body, breaks, avoids, nudges, placer)
                     if (breaks or avoids or nudges) else body)
        headings.clear()

        def positionfn(pos):
            pid = getattr(pos, "id", None)
            if not pid:
                return
            oc = getattr(pos, "open_close", None)
            text = getattr(pos, "text", "") or ""
            if oc == 1 and text:
                headings.append({"id": pid, "text": text,
                                 "page": getattr(pos, "page_num", 1),
                                 "rect": tuple(getattr(pos, "rect", ()))})

        story = fitz.Story(html=f"<html><body>{html_body}</body></html>",
                           user_css=layout.CSS, archive=arch)
        writer = fitz.DocumentWriter(tmp_pdf)
        story.write(writer, layout.rectfn, positionfn=positionfn)
        writer.close()
        squashed = _squashed_markers(placer, tmp_pdf, work)
        if not squashed:
            break
        grew = False
        for idx, _page, _k in squashed:
            entry = placer.entries[idx]
            inline = entry.get("kind") != "display" and entry.get("kind") != "diagram"
            if inline and idx not in nudges:
                # Cheapest cure for an inline formula squeezed onto the last line:
                # start it on a fresh line instead of pushing the block to the
                # next page (which would leave most of the page empty).
                nudges.add(idx)
                grew = True
                continue
            if idx in avoids:
                if idx not in nudges:
                    nudges.add(idx)
                    grew = True
                continue
            if idx in breaks:
                avoids.add(idx)
                grew = True
            else:
                breaks.add(idx)
                grew = True
        if not grew:
            break

    doc = fitz.open(tmp_pdf)

    # ---- drop any background sliver Story left in the top margin ----
    strays = 0
    for pno in range(doc.page_count):
        strays += clean_stray_bands(doc[pno])

    # ---- formulas: locate markers, white them out, overlay vector ----
    formula_pdf_cache: dict[int, bytes] = {}
    overlays = 0
    for pno in range(doc.page_count):
        page = doc[pno]
        for img in page.get_images(full=True):
            xref = img[0]
            idx = decode_marker(doc.extract_image(xref),
                                os.path.join(work, "_decode.png"))
            if idx is None or idx not in placer.entries:
                continue
            rects = page.get_image_rects(xref)
            if not rects:
                continue
            if idx not in formula_pdf_cache:
                entry = placer.entries[idx]
                formula_pdf_cache[idx] = svg_to_pdf_bytes(
                    entry["svg"], os.path.join(work, f"f{idx}.svg"))
            data = formula_pdf_cache[idx]
            # Story squeezes a picture that sits on the last baseline of a page
            # into the space BELOW that baseline, so a formula came out at a
            # fraction of its size even though there was room above the line.
            # Draw at the size the formula really needs, keep its bottom edge on
            # the marker's own bottom edge (the baseline), and only clamp when
            # it would leave the text column.
            want_w, want_h = _expected_size(placer, idx)
            for rect in rects:
                if want_w > 1.0 and want_h > 1.0:
                    # Draw at the size the formula needs, but never larger than
                    # the box Story reserved for it, so nothing can collide with
                    # a neighbouring line.  Anchor on the box's baseline corner:
                    # a formula grows upwards into the leading, which is where
                    # its own ascender belongs.
                    k = min(1.0, rect.width / want_w, rect.height / want_h)
                    w = want_w * k
                    h = want_h * k
                    x0 = min(max(rect.x0, config.BODY_X0),
                             config.BODY_X1 - w)
                    placed = fitz.Rect(x0, rect.y1 - h, x0 + w, rect.y1)
                else:
                    placed = rect
                # Clear slightly oversized to swallow the hairline of marker
                # colour that anti-aliasing leaves along the boundary.
                clear = (placed | rect) + (-0.6, -0.6, 0.6, 0.6)
                page.draw_rect(clear, color=(1, 1, 1), fill=(1, 1, 1), width=0.5)
                fdoc = fitz.open("pdf", data)
                page.show_pdf_page(placed, fdoc, 0)
                fdoc.close()
                overlays += 1

    # ---- running section label (top margin): last h2 owning each page ----
    levels = {m.group(2): int(m.group(1))
              for m in re.finditer(r"<h([1-6])[^>]*\bid=\"([^\"]+)\"", body)}
    section_marks = sorted(
        ((h["page"], h["text"]) for h in headings
         if levels.get(h["id"]) == 2 and h["text"]),
        key=lambda x: x[0])
    cue_labels = {}
    current = None
    for pno in range(doc.page_count):
        for page_no, text in section_marks:
            if page_no - 1 <= pno:
                current = text
        if current:
            cue_labels[pno] = current

    draw_cornell(doc, cue_labels, title, lecture_no, chapter_label=chap_label)

    # ---- bookmarks ----
    toc = [[1, (chap_label or f"第 {lecture_no} 章") + f" · {title}", 1]]
    seen = set()
    for h in headings:
        text = h["text"].strip()
        if not text or text in seen:
            continue
        # The chapter title itself is an h1 and is already the level-1 entry.
        if levels.get(h["id"], 2) < 2:
            continue
        seen.add(text)
        toc.append([min(3, levels.get(h["id"], 2)), text, max(1, h["page"])])
    doc.set_toc(toc)

    # ---- shrink and save ----
    doc.subset_fonts()
    out_path = os.path.join(out_dir, f"{stem}.pdf")
    doc.save(out_path, garbage=4, deflate=True, clean=True)
    doc.close()

    if not keep_temp:
        try:
            os.remove(tmp_pdf)
        except OSError:
            pass

    final = fitz.open(out_path)
    result = {
        "index": index,
        "lecture_no": lecture_no,
        "slug": slug,
        "title": title,
        "file": os.path.basename(out_path),
        "pages": final.page_count,
        "size_bytes": os.path.getsize(out_path),
        "formulas": stats["formulas"],
        "formula_overlays": overlays,
        "strays": strays,
        "math_failed": stats["math_failed"],
        "images": stats["images"],
        "bookmarks": len(toc),
        "toc": toc,
    }
    final.close()
    return result
