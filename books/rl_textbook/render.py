"""Render one authored chapter to a Cornell-layout PDF.

Pipeline per chapter:
  1. prepare()  -> Story HTML with marker placeholders + asset bag
  2. Story.write()  -> temporary PDF that reserves the right box for each formula
  3. decode markers -> exact placement rectangles
  4. white-out the marker, overlay the vector formula via show_pdf_page, and
     print its equation number against the right margin
  5. draw Cornell rules, header, footer, summary label
  6. bookmarks from heading positions, subset fonts, save

Two classes of layout defect are repaired by re-laying out the chapter:

* a formula marker that Story squeezed to a fraction of the width it asked for
  (MuPDF shrinks a picture sitting at the foot of a page instead of moving it);
* a table that was split across pages, which would separate its header row from
  its body (Story does not repeat the header on the continuation page), or from
  its caption.
"""

import os
import re
import json
import sys

import fitz
from PIL import Image

import config
import layout
import prepare

_CJK = re.compile(r"[\u4e00-\u9fff]")


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
def build_archive(assets: prepare.AssetBag, work: str) -> fitz.Archive:
    arch = fitz.Archive()
    arch.add(config.FONT_CJK, "song.ttf")          # 宋体
    arch.add(config.FONT_CJK_BOLD, "hei.ttf")      # 黑体
    arch.add(config.FONT_LATIN, "latin.ttf")       # Times New Roman
    arch.add(config.FONT_LATIN_BOLD, "latinb.ttf") # Times New Roman Bold
    arch.add(config.FONT_MONO, "mono.ttf")
    for name, path in assets.files.items():
        arch.add(path, name)
    for name, text in assets.svgs.items():
        tmp = os.path.join(work, "_svg_" + name)
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
        arch.add(tmp, name)
    return arch


# ------------------------------------------------------------------ cleanup
# Only the inline `code` chip keeps a background colour in the CSS; the block
# boxes are documented with borders instead, because an interrupted block
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
    body content.  Anything that starts at or below the body top is left alone.
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
_FONTS = {}


def _font(kind: str) -> fitz.Font:
    if kind not in _FONTS:
        path = {"body": config.FONT_BODY, "latin": config.FONT_LATIN}[kind]
        _FONTS[kind] = fitz.Font(fontfile=path)
    return _FONTS[kind]


def _measure(text: str, size: float, kind: str = "body") -> float:
    """Width in points using the real font (helv metrics are ~2.5x off for CJK)."""
    return _font(kind).text_length(text, fontsize=size)


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


def _label_of(no: int) -> str:
    """章名标签：普通章是「第 N 章」，预备章之类用 label 字段。"""
    try:
        ch = config.chapter_by_no(int(no))
    except (KeyError, TypeError, ValueError):
        return f"第 {no} 章"
    return ch.get("label") or f"第 {no} 章"


def draw_cornell(doc: fitz.Document, cue_labels: dict[int, str],
                 chapter_title: str, chapter_no: int) -> None:
    """Cornell rules, header, footer and running section label.

    The cue column and the summary band are left completely blank on purpose:
    they are the two writing areas this layout reserves for handwriting.
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
        # No horizontal rule across the top margin: the running head is set in
        # light grey and reads fine without a line above it, and a line there is
        # the first thing the eye lands on (it read as page furniture).

        page.insert_font(fontname="cjk", fontfile=config.FONT_BODY)

        # header: book + chapter on the left, running section on the right, both
        # inside the top margin so the writing column stays free for handwriting.
        head_size = 7.2
        head = f"{config.BOOK_TITLE_HEADER} · {_label_of(chapter_no)} · {chapter_title}"
        page.insert_text(fitz.Point(config.MARGIN_LEFT, config.HEADER_Y - 5),
                         head, fontsize=head_size, fontname="cjk", color=config.LABEL_GREY)

        cue = cue_labels.get(pno)
        if cue:
            room = (config.SUMMARY_X1 - config.MARGIN_LEFT
                    - _measure(head, head_size) - 18)
            label = _truncate(cue, 7.0, max(0.0, room))
            if label:
                w = _measure(label, 7.0)
                page.insert_text(fitz.Point(config.SUMMARY_X1 - w, config.HEADER_Y - 5),
                                 label, fontsize=7.0, fontname="cjk",
                                 color=config.LABEL_GREY)

        # footer
        page.insert_text(fitz.Point(config.MARGIN_LEFT, config.FOOTER_Y),
                         f"{_label_of(chapter_no)} · {chapter_title}", fontsize=7,
                         fontname="cjk", color=config.LABEL_GREY)
        label = str(pno + 1)
        w = fitz.get_text_length(label, fontname="helv", fontsize=8)
        page.insert_text(fitz.Point(config.SUMMARY_X1 - w, config.FOOTER_Y),
                         label, fontsize=8, fontname="helv", color=config.LABEL_GREY)

        # summary band label
        page.insert_text(fitz.Point(config.MARGIN_LEFT, config.SUMMARY_RULE_Y - 6),
                         "SUMMARY / 总结", fontsize=7, fontname="cjk",
                         color=config.LABEL_GREY)


# ------------------------------------------------------------------ repairs
def _insert_breaks(body: str, ids: set, avoid: set = frozenset(),
                   nudge: set = frozenset()) -> str:
    """Force a page break, and optionally a no-split rule, on marker blocks.

    A display formula owns a ``<p id="mkpN">``; an inline formula is anchored
    on whatever block carries it (see prepare._tag_inline_anchors), so the id
    is looked up first and the enclosing start tag is found by walking back to
    the nearest ``<``.
    """
    out = body
    for idx in sorted(ids):
        out = _break_before_id(out, f"mkp{idx}", style="page-break-before: always;")
    for idx in sorted(avoid):
        key = f'id="mkp{idx}"'
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
            f' id="mkp{idx}"',
            f' style="break-inside:avoid;" id="mkp{idx}"', 1) + out[end:]
    for idx in sorted(nudge):
        # A line break in front of the picture puts it at the start of a line,
        # where there is a full line of room, so it is never squeezed.
        key = f'<img src="mk{idx}.png"'
        pos = out.find(key)
        if pos < 0:
            continue
        out = out[:pos] + "<br/>" + out[pos:]
    return out


def _break_before_id(body: str, elem_id: str, style: str) -> str:
    key = f'id="{elem_id}"'
    pos = body.find(key)
    if pos < 0:
        return body
    start = body.rfind("<", 0, pos)
    if start < 0:
        return body
    return body[:start] + f'<div style="{style}"></div>' + body[start:]


def _expected_size(placer, idx: int) -> tuple:
    """The box size the layout was asked to reserve for this marker."""
    entry = placer.entries[idx]
    if entry.get("kind") == "diagram":
        return placer.diagram_size(idx)
    if entry.get("kind") in ("table", "block"):
        return (1.0, 1.0)
    return placer.sheet_size(idx)


def _scan_markers(placer, pdf_path: str, work: str) -> dict:
    """{marker index: [(page, [rect, ...]), ...]} for the laid-out chapter."""
    found: dict[int, list] = {}
    doc = fitz.open(pdf_path)
    try:
        tmp = os.path.join(work, "_decode.png")
        for pno in range(doc.page_count):
            page = doc[pno]
            for img in page.get_images(full=True):
                xref = img[0]
                idx = decode_marker(doc.extract_image(xref), tmp)
                if idx is None or idx not in placer.entries:
                    continue
                found.setdefault(idx, []).append((pno + 1, page.get_image_rects(xref)))
    finally:
        doc.close()
    return found


def _squashed_markers(placer, positions: dict) -> list:
    """[(idx, page, ratio)] for markers Story failed to place at the asked width.

    An inline marker deliberately reserves less height than the formula needs
    (see prepare.MathPlacer._tag) so MuPDF has no reason to squeeze it.  The
    reserved WIDTH is what keeps the sentence flowing, so that is the dimension
    worth checking.
    """
    bad = []
    for idx, hits in positions.items():
        try:
            w, _h = _expected_size(placer, idx)
        except Exception:
            continue
        if w <= 1.5:
            continue
        for page, rects in hits:
            for rect in rects:
                if rect.width < 0.5:
                    bad.append((idx, page, 0.0))
                    continue
                k = rect.width / w
                if k < 0.985:
                    bad.append((idx, page, round(k, 3)))
    return bad


def _blank_pages(pdf_path: str) -> list[int]:
    """Pages of the laid-out story that carry nothing but the furniture.

    Header, footer and Cornell rules are drawn after layout, so a page whose
    own content is empty is a defect: it means a forced break landed at the top
    of a page that was already empty.
    """
    doc = fitz.open(pdf_path)
    out = []
    try:
        for pno in range(doc.page_count):
            page = doc[pno]
            if page.get_text().strip():
                continue
            big = [r for img in page.get_images(full=True)
                   for r in page.get_image_rects(img[0])
                   if r.width > 2 and r.height > 2]
            if not big:
                out.append(pno + 1)
    finally:
        doc.close()
    return out


def _blocks_starting_at(placer, positions: dict, page_no: int) -> set:
    hit = set()
    for idx, hits in positions.items():
        e = placer.entries.get(idx) or {}
        if e.get("kind") == "block" and e.get("role") == "first":
            if any(p == page_no for p, _r in hits):
                hit.add(e["block"])
    return hit


def _split_ids(placer, positions: dict) -> set:
    """Ids of tables/blocks whose start marker and end marker landed apart."""
    first: dict[str, int] = {}
    last: dict[str, int] = {}
    for idx, hits in positions.items():
        e = placer.entries.get(idx) or {}
        if e.get("kind") not in ("table", "block"):
            continue
        pages = [p for p, _r in hits]
        if not pages:
            continue
        key = e["table"] if e["kind"] == "table" else e["block"]
        if e["role"] == "first":
            first[key] = min(pages)
        else:
            last[key] = max(pages)
    return {k for k in first if k in last and first[k] != last[k]}


def _secrule_map(body: str) -> dict[str, str]:
    """Heading id -> the id of the ``.secrule`` div that opens its section."""
    out = {}
    pattern = (r'<div[^>]*class="secrule[^"]*"[^>]*id="(sr\d+)"[^>]*>\s*</div>'
               r'\s*<h[23][^>]*id="([^"]+)"')
    for m in re.finditer(pattern, body):
        out[m.group(2)] = m.group(1)
    return out


def _clean_label(text: str) -> str:
    """Normalise a heading for bookmarks and the running head.

    MuPDF reports inter-word spaces as U+00A0 and can leave a soft hyphen where
    a Latin run meets CJK, which in a bookmark reads as "TD(\u00a0λ\u00a0)".
    """
    out = (text or "").replace("\u00a0", " ")
    # MuPDF reports the hyphen of "图 1-1" as a soft hyphen; dropping it would
    # turn the caption into "图 11", so it is restored as a real hyphen.
    out = out.replace("\u00ad", "-")
    while "  " in out:
        out = out.replace("  ", " ")
    return out.strip()


def _low_headings(headings: list, sr_map: dict[str, str],                  already: set) -> list[str]:
    """Section headings stranded at the foot of a page.

    ``.tight`` sections do not force a page break, so their double rule and
    heading can land in the last few lines of a page and leave the section body
    on the next one - an orphan heading.  Anything with less than ~3 lines of
    room below it is pushed to the following page.
    """
    out = []
    for h in headings:
        rect = h.get("rect") or ()
        if len(rect) != 4:
            continue
        sid = sr_map.get(h["id"])
        if sid and sid not in already and rect[3] > config.BODY_Y1 - 62:
            out.append(sid)
    return out


# ------------------------------------------------------------------ render
def render_chapter(index: int, math_cache: dict[str, str], out_dir: str,
                   keep_temp: bool = False) -> dict:
    ch = config.chapter_by_index(index)
    slug, title, stem, no = ch["slug"], ch["title"], ch["stem"], ch["no"]
    work = config.work_dir(slug)
    os.makedirs(work, exist_ok=True)

    body, assets, placer, stats = prepare.prepare(slug, math_cache, work)
    if stats["math_failed"]:
        missing = placer.failed[:5]
        raise SystemExit(f"{slug}: {stats['math_failed']} formula(s) missing from the "
                         f"MathJax cache, e.g. {missing}")
    arch = build_archive(assets, work)

    breaks: set[int] = set()
    avoids: set[int] = set()
    nudges: set[int] = set()
    tbreaks: set[str] = set()
    tried_tables: set[str] = set()
    head_breaks: set[str] = set()
    positions: dict = {}
    headings: list = []
    squashed: list = []
    splits: set = set()
    sr_map = _secrule_map(body)
    tmp_pdf = os.path.join(work, "stage1.pdf")

    for attempt in range(6):
        # A fresh file per pass: MuPDF cannot always delete the previous one,
        # and a partly written stage would poison the next attempt.
        tmp_pdf = os.path.join(work, f"stage1_{attempt}.pdf")
        html_body = body
        if os.environ.get("RL_PLAIN") == "1":
            # Diagnostic switch: lay the document out with no forced breaks at
            # all, to tell "the break insertion dropped this" apart from "the
            # page builder dropped this".
            html_body = body
            breaks, avoids, nudges, tbreaks, head_breaks = (set(), set(), set(),
                                                           set(), set())
        elif breaks or avoids or nudges:
            html_body = _insert_breaks(html_body, breaks, avoids, nudges)
        for table_id in sorted(tbreaks):
            html_body = _break_before_id(html_body, table_id,
                                         "page-break-before: always;")
        for sr_id in sorted(head_breaks):
            html_body = _break_before_id(html_body, sr_id,
                                         "page-break-before: always;")
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

        positions = _scan_markers(placer, tmp_pdf, work)
        squashed = _squashed_markers(placer, positions)
        splits = _split_ids(placer, positions) - tried_tables

        # A forced break can itself create an empty page when the preceding
        # content ended exactly at the foot of a page.  Undo that break instead:
        # a split box is a blemish, a blank page is a defect.
        blanks = _blank_pages(tmp_pdf)
        if blanks:
            drop = set()
            for b in blanks:
                drop |= _blocks_starting_at(placer, positions, b + 1)
            if drop:
                for bid in drop:
                    tbreaks.discard(bid)
                    tried_tables.add(bid)
                continue

        # An h2/h3 stranded in the last lines of a page is an orphan heading:
        # push its section rule to the next page and lay out again.
        low_heads = _low_headings(headings, sr_map, head_breaks)
        if low_heads:
            head_breaks.update(low_heads)
            continue

        if not squashed and not splits:
            break

        grew = False
        for table_id in splits:
            tbreaks.add(table_id)
            tried_tables.add(table_id)
            grew = True
        for idx, _page, _k in squashed:
            entry = placer.entries[idx]
            inline = entry.get("kind") not in ("display", "diagram", "table")
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
    eqnos = 0
    eqno_set: set[str] = set()
    eqno_records: list[dict] = []
    eqno_tight: list[dict] = []
    table_marks = 0
    drawn = set()
    for idx, hits in positions.items():
        entry = placer.entries[idx]
        kind = entry.get("kind")
        if kind in ("table", "block"):
            # A table/block marker only measures where the two ends of the block
            # landed; it is erased like a formula marker but draws nothing.
            for page_no, rects in hits:
                for rect in rects:
                    doc[page_no - 1].draw_rect(
                        rect + (-0.4, -0.4, 0.4, 0.4),
                        color=(1, 1, 1), fill=(1, 1, 1), width=0.3)
                    table_marks += 1
            continue
        if not entry.get("svg"):
            continue
        if idx not in formula_pdf_cache:
            formula_pdf_cache[idx] = svg_to_pdf_bytes(entry["svg"],
                                                      os.path.join(work, f"f{idx}.svg"))
        data = formula_pdf_cache[idx]
        want_w, want_h = _expected_size(placer, idx)
        for page_no, rects in hits:
            page = doc[page_no - 1]
            page.insert_font(fontname="latin", fontfile=config.FONT_LATIN)
            for rect in rects:
                # Story squeezes a picture that sits on the last baseline of a
                # page into the space BELOW that baseline, so a formula came out
                # at a fraction of its size even though there was room above the
                # line.  Draw at the size the formula really needs, keep its
                # bottom edge on the marker's own bottom edge (the baseline), and
                # only clamp when it would leave the text column.
                if want_w > 1.0 and want_h > 1.0:
                    k = min(1.0, rect.width / want_w, rect.height / want_h)
                    w, h = want_w * k, want_h * k
                    x0 = min(max(rect.x0, config.BODY_X0), config.BODY_X1 - w)
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
                drawn.add(idx)

                eqno = entry.get("eqno")
                if eqno:
                    # Count distinct tags: the same numbered formula can be
                    # repeated (e.g. restated in 关键公式) and would otherwise
                    # inflate the reported total.
                    eqno_set.add(str(eqno))
                    label = f"({eqno})"
                    wnum = _measure(label, 10.0, "latin")
                    # A tall formula (products, sums, fractions) has no single
                    # baseline the eye can hang the number on, so it is centred
                    # against the formula's own height instead of sitting at the
                    # bottom edge.
                    ny = (placed.y0 + placed.height * 0.5 + 3.4
                          if placed.height > 22 else placed.y1)
                    # A formula that reaches the very bottom of the text column
                    # would push its number into the blank summary band, which
                    # is reserved for handwriting (verify flags it as a band hit).
                    ny = min(ny, config.BODY_Y1 - 2.0)
                    page.insert_text(fitz.Point(config.BODY_X1 - wnum, ny),
                                     label, fontsize=10.0, fontname="latin",
                                     color=(0.07, 0.07, 0.07))
                    eqnos += 1
                    # A numbered display is centred while its number is flush
                    # right: if the picture reaches past the number's left edge
                    # the two are printed on top of each other, and no layout
                    # check notices because both are single elements.
                    if placed.x1 > config.BODY_X1 - wnum - 4:
                        eqno_tight.append({
                            "eqno": str(eqno), "page": page_no + 1,
                            "width": round(placed.width, 1)})
                    # Machine-readable record: check_eqno.py compares this set
                    # against the \tag values in the markdown source.  A visual
                    # "10pt + right edge" test is only a cross-check, because a
                    # 12pt body reference such as 式 (2.3) looks the same-ish.
                    eqno_records.append({
                        "eqno": str(eqno),
                        "page": page_no,
                        "x": round(config.BODY_X1 - wnum, 1),
                        "y": round(ny, 1),
                        "latex": entry.get("latex", "")[:200],
                    })

    # ---- coverage: every registered formula must have been drawn ----------
    # A marker that Story places but that never shows up in the scan means the
    # formula vanished (typically an inline image pushed onto the next page at
    # a break).  Silence would hide it inside a blank 60pt gap, so say it out
    # loud and put the count in the build report.
    lost = [i for i, e in placer.entries.items()
            if e.get("kind") in ("formula", "diagram") and i not in drawn]
    if lost:
        shown = " ｜ ".join(
            f"#{i} {placer.entries[i].get('latex', '?')[:26]!r}" for i in lost[:8]
        )
        msg = f"{len(lost)} 个公式未渲染：{shown}"
        print(f"  !! {msg}")
        # 这不是"警告"：没画出来的公式连同它所在的正文一起消失，而页数可能
        # 恰好还在预算内（ch06 曾整节丢失仍报 130/130）。诊断时可设
        # RL_ALLOW_LOST=1 放行，正式构建一律失败。
        if os.environ.get("RL_ALLOW_LOST") != "1":
            raise SystemExit(f"构建失败（内容丢失）：{msg}")

    # ---- running section label (top margin): last h2 owning each page ----
    levels = {m.group(2): int(m.group(1))
              for m in re.finditer(r"<h([1-6])[^>]*\bid=\"([^\"]+)\"", body)}
    section_marks = sorted(
        ((h["page"], h["text"]) for h in headings
         if (levels.get(h["id"]) == 2 or h["text"].startswith(("第 ",))) and h["text"]),
        key=lambda x: x[0])
    # The running head names the section the page *starts* in, not the last one
    # that happens to begin somewhere on it: 本章小结 and 关键公式 can share a
    # page, and the head should say 本章小结 then.
    by_page: dict[int, list[str]] = {}
    for page_no, text in section_marks:
        by_page.setdefault(page_no, []).append(text)
    cue_labels = {}
    current = None
    for pno in range(doc.page_count):
        page_no = pno + 1
        starts = by_page.get(page_no)
        if starts:
            current = starts[0]
        elif current is None:
            for prev in range(page_no - 1, 0, -1):
                if by_page.get(prev):
                    current = by_page[prev][-1]
                    break
        if current:
            cue_labels[pno] = current

    draw_cornell(doc, cue_labels, title, no)

    # ---- machine-readable equation-number manifest ----
    # Written next to the chapter cache so check_eqno.py can compare the numbers
    # actually printed in the PDF with the \tag values in the markdown source.
    eqno_path = os.path.join(config.cache_dir(slug), "eqno.json")
    os.makedirs(os.path.dirname(eqno_path), exist_ok=True)
    with open(eqno_path, "w", encoding="utf-8") as fh:
        json.dump({"slug": slug, "no": no, "eqnos": eqno_records},
                  fh, ensure_ascii=False, indent=1)

    # ---- bookmarks ----
    toc = [[1, f"{_label_of(no)} · {title}", 1]]
    seen = set()
    for h in headings:
        text = _clean_label(h["text"])
        if not text or text in seen:
            continue
        seen.add(text)
        # h2 -> level 2, h3/h4 -> level 3, so the PDF reader can collapse a
        # section's subsections instead of showing one flat list.
        lvl = 2 if levels.get(h["id"], 2) == 2 else 3
        toc.append([lvl, text, max(1, h["page"])])
    doc.set_toc(toc)

    # ---- 正文对账（防止 Story 静默吞段） ----
    # MuPDF Story occasionally drops a whole paragraph when a page's fill lands
    # in a bad spot: during this build two chapters lost a page of prose and the
    # only symptom was a formula-coverage warning.  Counting CJK characters
    # against the prepared HTML is cheap insurance against that class of loss.
    plain = re.sub(r"<[^>]{0,600}>", "", body)
    want = len(_CJK.findall(plain))
    got = sum(len(_CJK.findall(pg.get_text())) for pg in doc)
    cjk_ratio = got / want if want else 1.0
    if cjk_ratio < 0.995:
        print(f"!! 正文可能丢失：排版后汉字 {got} / 源 {want}"
              f"（{cjk_ratio * 100:.1f}%）", file=sys.stderr)

    # ---- shrink and save ----
    doc.subset_fonts()
    out_path = config.out_pdf(stem)
    os.makedirs(out_dir, exist_ok=True)
    doc.save(out_path, garbage=4, deflate=True, clean=True)
    pages = doc.page_count
    doc.close()

    if not keep_temp:
        try:
            os.remove(tmp_pdf)
        except OSError:
            pass

    return {
        "index": index + 1,
        "no": no,
        "slug": slug,
        "title": title,
        "file": os.path.basename(out_path),
        "pages": pages,
        "size_bytes": os.path.getsize(out_path),
        "formulas": stats["formulas"],
        "eqnos": eqnos,
        "formula_overlays": overlays,
        "table_marks": table_marks,
        "tables_pushed": len(tbreaks),
        "tables_split": len(splits),
        "strays": strays,
        "cjk_ratio": round(cjk_ratio, 3),
        "lost_formulas": len(lost),
        "wide_inline": stats.get("wide_inline", []),
        "narrowed_eq": stats.get("narrowed_eq", 0),
        "narrowed": stats.get("narrowed", []),
        "eqno_tight": eqno_tight,
        "math_failed": stats["math_failed"],
        "images": stats["images"],
        "bookmarks": len(toc),
        "toc": toc,
    }
