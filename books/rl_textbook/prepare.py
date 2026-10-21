"""Turn the converted chapter HTML into Story-ready HTML plus asset tables.

Responsibilities:
  * rewrite <img src> to local files held in a fitz.Archive
  * turn authored .svg figures into vector diagram markers
  * replace LaTeX with correctly sized 1x1 marker images (vector formulas are
    overlaid later, once the exact placement rectangles are known)
  * remember each display formula's equation number so render.py can print it
    against the right margin
"""

import html as htmllib
import os
import re
import struct
import zlib

from bs4 import BeautifulSoup, NavigableString
from PIL import Image

import config
import mathutil
import md2html

MARKER_NAME = "marker.png"
SVG_EXT = ".svg"


# ------------------------------------------------------------------ markers
def make_marker(path: str, idx: int) -> None:
    """1x1 opaque PNG encoding `idx` in its RGB channels.

    Must stay opaque: a transparent marker has its colour zeroed by MuPDF on
    embed, which destroys the index.
    """
    raw = b"\x00" + bytes([idx & 0xFF, (idx >> 8) & 0xFF, (idx >> 16) & 0xFF, 255])

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) +
                 chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


# ------------------------------------------------------------------ helpers
def _normalise_nbsp(art) -> None:
    for node in art.find_all(string=True):
        if "\xa0" in node:
            node.replace_with(node.replace("\xa0", " "))


# ------------------------------------------------------------------ math
class MathPlacer:
    """Replaces LaTeX with sized marker images and records the mapping."""

    def __init__(self, math_cache: dict[str, str], work_dir: str):
        self.cache = math_cache
        self.work_dir = work_dir
        self.marker_files: dict[str, str] = {}     # marker name -> png path
        self.entries: dict[int, dict] = {}         # marker idx -> formula meta
        self.next_idx = 0
        self.failed: list[str] = []
        self.eqno_count = 0
        self.wide_inline: list[tuple[float, str]] = []   # over-wide inline maths
        self.narrowed_eq = 0        # numbered displays shrunk to clear the number
        self.narrowed: list[tuple[str, float]] = []   # (eqno, natural width)

    def _new_marker(self, entry: dict) -> int:
        idx = self.next_idx
        self.next_idx += 1
        name = f"mk{idx}.png"
        path = os.path.join(self.work_dir, name)
        make_marker(path, idx)
        self.marker_files[name] = path
        self.entries[idx] = entry
        return idx

    def _register(self, raw: str, display: bool) -> int | None:
        tex, eqno = mathutil.split_eqno(mathutil.strip_delims(raw))
        # Pandoc turns a \[ ... \] block that directly follows a paragraph line
        # without a blank line into inline \( ... \) math.  A \tag can only ever
        # mark a numbered display equation, so the tag itself is the signal to
        # promote the marker back to a display (centred, with a margin number).
        if eqno and not display:
            display = True
        key = ("D|" if display else "I|") + mathutil.normalize(tex)
        svg = self.cache.get(key)
        if not svg and eqno:
            svg = self.cache.get("I|" + mathutil.normalize(tex))
        if not svg:
            self.failed.append(raw)
            return None
        if eqno and display:
            self.eqno_count += 1
        return self._new_marker({"latex": raw, "display": display, "svg": svg,
                                 "kind": "formula", "eqno": eqno if display else None})

    def register_diagram(self, svg_text: str, nat_w: float, nat_h: float,
                         frac: float = 1.0) -> int:
        """Reserve space for an .svg figure that must stay vector.

        ``frac`` scales the finished figure against the body column, which is how
        an author asks for "this one a bit smaller" (``![](x.svg){width=78%}``)
        when a full-width figure would not fit the rest of a page.
        """
        idx = self._new_marker({"latex": "", "display": False, "svg": svg_text,
                                "kind": "diagram", "nat_w": nat_w, "nat_h": nat_h,
                                "frac": max(0.2, min(1.0, frac))})
        return idx

    def register_block(self, block_id: str, role: str) -> int:
        """A 1pt marker at a block's first/last child, used to detect a split.

        A theorem, definition or algorithm that breaks across a page boundary is
        a typographic defect: the reader loses the frame that says "this whole
        thing is one statement".  The same pair-of-markers trick as for tables
        detects it after layout, and render.py then pushes the block to the next
        page.
        """
        return self._new_marker({"latex": "", "display": False, "svg": "",
                                 "kind": "block", "block": block_id,
                                 "role": role, "eqno": None})

    def register_table(self, table_id: str, role: str) -> int:
        """A 1pt marker in a table's first/last row, used to detect a split.

        Story splits a table at a row boundary and does not repeat the header,
        so a table that straddles pages loses its header row (or, worse, only
        its header lands on the previous page).  Two markers tell render.py
        whether the two ends of the same table ended up on the same page.
        """
        return self._new_marker({"latex": "", "display": False, "svg": "",
                                 "kind": "table", "table": table_id,
                                 "role": role, "eqno": None})

    def diagram_size(self, idx: int) -> tuple[float, float]:
        e = self.entries[idx]
        avail = (config.BODY_X1 - config.BODY_X0) * float(e.get("frac") or 1.0)
        w, h = e["nat_w"], e["nat_h"]
        if w > avail:
            k = avail / w
            w, h = w * k, h * k
        return w, h

    def diagram_tag(self, idx: int) -> str:
        w, h = self.diagram_size(idx)
        self.entries[idx]["box"] = (w, h)
        return (f'<p id="mkp{idx}" class="figpara" style="text-align:center;'
                f'margin:6pt 0;text-indent:0;break-inside:avoid;">'
                f'<img src="mk{idx}.png" style="width:{w:.2f}pt;height:{h:.2f}pt"/>'
                f'</p>')

    def _size(self, svg: str, display: bool, eqno: bool = False) -> tuple[float, float]:
        wm = re.search(r'width="([\d.]+)ex"', svg)
        hm = re.search(r'height="([\d.]+)ex"', svg)
        wx = float(wm.group(1)) if wm else 3.0
        hx = float(hm.group(1)) if hm else 1.2
        if display:
            w, h = wx * config.DISPLAY_SCALE, hx * config.DISPLAY_SCALE
            # A numbered formula must leave the right margin free for its number,
            # otherwise the two collide (nothing else checks this).
            limit = config.DISPLAY_MAX_NUMBERED if eqno else config.DISPLAY_MAX_WIDTH
            if w > limit:
                k = limit / w
                w, h = w * k, h * k
                if eqno:
                    self.narrowed_eq += 1
        else:
            w, h = wx * config.EX_PT, hx * config.EX_PT
        return w, h

    def formula_size(self, idx: int) -> tuple[float, float]:
        entry = self.entries[idx]
        return self._size(entry["svg"], entry["display"], bool(entry.get("eqno")))

    def set_box(self, idx: int, w: float, h: float) -> None:
        """Override the box a marker was laid out with (used by table clamping)."""
        self.entries[idx]["box"] = (w, h)

    def sheet_size(self, idx: int) -> tuple[float, float]:
        """The size the marker box was actually laid out with."""
        box = self.entries[idx].get("box")
        if box:
            return box
        return self.formula_size(idx)

    def _tag(self, idx: int, display: bool) -> str:
        svg = self.entries[idx]["svg"]
        entry = self.entries[idx]
        w, h = self._size(svg, display, bool(entry.get("eqno")))
        if display:
            entry["box"] = (w, h)
            # Name the formulas that had to be shrunk, so the author knows which
            # ones to rewrite as multi-line aligned instead of guessing.
            if entry.get("eqno"):
                wm = re.search(r'width="([\d.]+)ex"', svg)
                natural = (float(wm.group(1)) if wm else 3.0) * config.DISPLAY_SCALE
                if natural > config.DISPLAY_MAX_NUMBERED + 0.5:
                    self.narrowed.append((str(entry["eqno"]), round(natural, 1)))
            img = f'<img src="mk{idx}.png" style="width:{w:.2f}pt;height:{h:.2f}pt"/>'
            return (f'<p id="mkp{idx}" style="text-align:center;text-indent:0;'
                    f'margin:8pt 0;break-inside:avoid;">{img}</p>')
        # An inline formula with a fraction or a big operator can be taller than
        # the leading; left at full size it would reach into the line above.  It
        # is scaled down just enough to sit inside the leading, which keeps the
        # rhythm of the page even and never lets a formula collide with its
        # neighbours.  render.py draws it at the box's own scale.
        lead = config.BODY_FONT_SIZE * config.BODY_LINE_HEIGHT
        k = min(1.0, lead / h) if h > lead else 1.0
        self.entries[idx]["box"] = (w * k, h * k)
        # A formula this wide cannot flow inside a line: with the text before it
        # the line is already full, so it starts a new line and the following
        # words continue after it - which reads as a left-aligned display
        # formula glued to the sentence.  Collect such cases so the author can
        # turn them into ``\\[..\\]``; the layout itself stays honest.
        if w * k > config.INLINE_MAX_WIDTH:
            self.wide_inline.append((round(w * k, 1),
                                      self.entries[idx].get("latex", "")[:90]))
        return (f'<img src="mk{idx}.png" '
                f'style="width:{w * k:.2f}pt;height:{h * k:.2f}pt"/>')

    def replace(self, body: str) -> str:
        def do_display(m):
            idx = self._register(m.group(0), True)
            return self._tag(idx, True) if idx is not None else m.group(0)

        def do_inline(m):
            idx = self._register(m.group(0), False)
            return self._tag(idx, False) if idx is not None else m.group(0)

        body = mathutil.DISPLAY_RE.sub(do_display, body)
        return mathutil.INLINE_RE.sub(do_inline, body)


_MARKER_SRC_RE = re.compile(r"^mk(\d+)\.png$")


def _clamp_table_markers(frag, placer: "MathPlacer") -> int:
    """Shrink a formula that sits in a table cell so the table stays in its column.

    MuPDF Story gives a table at least the natural width of its widest cell, and
    the width of a maths marker is fixed, so one long formula in one cell would
    push a four-column table straight through the writing column and across the
    page rule.  Each cell gets an equal share of the body width, with a little
    slack for padding; the drawing is vector, so shrinking costs no sharpness.
    """
    avail = config.BODY_X1 - config.BODY_X0
    clamped = 0
    for img in frag.find_all("img"):
        m = _MARKER_SRC_RE.match(img.get("src") or "")
        if m is None:
            continue
        idx = int(m.group(1))
        cell = img.find_parent(["td", "th"])
        if cell is None:
            continue
        row = cell.find_parent("tr")
        cells = row.find_all(["td", "th"], recursive=False) if row else [cell]
        ncols = max(1, len(cells))
        table = cell.find_parent("table")
        if table is not None and ncols >= 4:
            table["class"] = "dense"
        cap = max(72.0, avail / ncols * 0.88)
        w, h = placer.sheet_size(idx)
        if w <= cap:
            continue
        k = cap / w
        placer.set_box(idx, w * k, h * k)
        img["style"] = f"width:{w * k:.2f}pt;height:{h * k:.2f}pt"
        clamped += 1
    return clamped


def _tag_inline_anchors(body: str, placer: "MathPlacer") -> str:
    """Give the block carrying an inline formula a stable id.

    MuPDF Story squeezes an inline picture that does not fit the foot of a page
    instead of carrying the line over, which reduced some formulas to a few
    points wide.  An inline image has no paragraph of its own to break before,
    so the block that owns it gets ``id="mkpN"`` and render._insert_breaks can
    push that block onto a fresh page when the marker comes out too small.
    """
    frag = BeautifulSoup(body, "html.parser")
    clamped = _clamp_table_markers(frag, placer)
    tagged = 0
    for img in frag.find_all("img"):
        m = _MARKER_SRC_RE.match(img.get("src") or "")
        if m is None:
            continue
        idx = int(m.group(1))
        entry = placer.entries[idx]
        if entry.get("kind") in ("table", "block") or entry.get("display"):
            continue
        block = img.find_parent(
            ["p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th"])
        if block is None:
            continue
        # Breaking inside a boxed block would strand its title or its caption on
        # the previous page, so the whole box is what moves.
        box = block.find_parent("div", class_=["box", "figwrap"])
        if box is not None:
            block = box
        if block.get("id"):
            continue
        block["id"] = f"mkp{idx}"
        tagged += 1
    placer.inline_anchors = tagged
    placer.table_clamps = clamped
    return "".join(str(child) for child in frag.contents)


# ------------------------------------------------------------------ assets
class AssetBag:
    """Collects the files that must be mounted in the Story archive."""

    def __init__(self):
        self.files: dict[str, str] = {}      # archive name -> local path
        self.svgs: dict[str, str] = {}       # archive name -> svg source text

    def add(self, name: str, path: str) -> None:
        self.files[name] = path

    def add_svg(self, name: str, svg_text: str) -> None:
        self.svgs[name] = svg_text


def _svg_natural_size(svg_text: str) -> tuple[float, float]:
    """Natural size in points, from viewBox when present (matplotlib writes pt)."""
    vb = re.search(r'viewBox="([\d.\s-]+)"', svg_text)
    if vb:
        parts = [float(x) for x in vb.group(1).split()]
        if len(parts) == 4 and parts[2] > 0 and parts[3] > 0:
            return parts[2], parts[3]
    m = re.search(r'<svg[^>]*?width="([\d.]+)\s*(?:pt|px)?"[^>]*?height="([\d.]+)', svg_text)
    if m:
        return float(m.group(1)), float(m.group(2))
    return 600.0, 300.0


def _px_size(path: str) -> tuple[int, int]:
    try:
        with Image.open(path) as im:
            return im.size
    except Exception:
        return 0, 0


def _rewrite_images(art, soup, slug: str, assets: AssetBag,
                    placer: "MathPlacer") -> int:
    """Point every <img> at a local file; authored SVGs stay vector."""
    count = 0
    for i, img in enumerate(art.find_all("img")):
        src = img.get("src")
        if not src:
            continue
        local = md2html.resolve_asset(src, config.CONTENT_DIR)
        if local is None:
            print(f"  [warn] {slug}: unresolved image {src}")
            img.decompose()
            continue
        ext = os.path.splitext(local)[1].lower() or ".jpg"
        if ext == SVG_EXT:
            with open(local, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            nw, nh = _svg_natural_size(text)
            frac = 1.0
            # Pandoc puts `{width=76%}` on the style attribute, not on width.
            width_attr = (img.get("width") or "").strip()
            if not width_attr:
                m = re.search(r"width\s*:\s*([\d.]+)\s*%",
                              img.get("style") or "")
                width_attr = f"{m.group(1)}%" if m else ""
            if width_attr.endswith("%"):
                try:
                    frac = float(width_attr[:-1]) / 100.0
                except ValueError:
                    frac = 1.0
            idx = placer.register_diagram(text, nw, nh, frac)
            holder = BeautifulSoup(placer.diagram_tag(idx), "html.parser")
            anchor = img.find_parent("a")
            target = anchor if anchor is not None else img
            target.replace_with(holder)
            count += 1
            continue
        name = f"{slug}_img{i}{ext}"
        assets.add(name, local)
        img["src"] = name
        img.attrs.pop("width", None)
        img.attrs.pop("height", None)
        # Story sizes a bitmap from the resolution recorded in the file; pin an
        # explicit width so identical-looking figures come out at equal widths.
        if img.find_parent("div", class_="figure") is not None:
            px_w, px_h = _px_size(local)
            if px_w and px_h:
                avail = config.BODY_X1 - config.BODY_X0
                w_pt = min(avail, max(120.0, px_w * 0.5))
                h_pt = w_pt * px_h / px_w
                # Story only honours an explicit size when both dimensions are
                # present; the inline-block wrapper stops MuPDF squeezing the
                # illustration into whatever space is left at the foot of a page.
                img["style"] = f"width:{w_pt:.1f}pt;height:{h_pt:.1f}pt;"
                box = soup.new_tag("span")
                box["style"] = (f"display:inline-block;width:{w_pt:.1f}pt;"
                                f"height:{h_pt:.1f}pt;")
                img.wrap(box)
        count += 1
    return count


# ------------------------------------------------------------------ prepare
_LATIN_RUN = re.compile(r"[\x20-\x7E]+")
_BOLD_ANCESTORS = ("strong", "b", "h1", "h2", "h3", "h4", "h5", "h6", "th")


def _split_fonts(frag) -> int:
    """Route Latin letters and digits to Times New Roman, Chinese to SimSun.

    MuPDF Story resolves only a single family name per element: given a list
    such as ``"latin, song"`` it silently falls back to its built-in default
    face instead of mixing the two, so the mixture has to be expressed as
    per-run spans, which it does lay out correctly on one line.
    """
    changed = 0
    for node in frag.find_all(string=True):
        holder = node.find_parent(["pre", "code"])
        if holder is not None:
            # Real source code stays monospaced and untouched; pseudocode inside
            # a definition/theorem/algorithm box is Chinese prose and must be
            # split like body text (see layout.CSS: .box pre uses the body face).
            if holder.find_parent("div", class_=["box", "algorithm"]) is None:
                continue
        if node.find_parent(["script", "style"]) is not None:
            continue
        text = str(node)
        runs = _LATIN_RUN.findall(text)
        if not runs:
            continue
        bold = node.find_parent(list(_BOLD_ANCESTORS)) is not None
        cls = "latinb" if bold else "latin"
        new_nodes = []
        for i, piece in enumerate(_LATIN_RUN.split(text)):
            if piece:
                new_nodes.append(NavigableString(piece))
            if i < len(runs):
                span = frag.new_tag("span")
                span["class"] = cls
                span.append(NavigableString(runs[i]))
                new_nodes.append(span)
        if new_nodes:
            node.replace_with(*new_nodes)
            changed += 1
    return changed


def _mark_tables(art, soup, placer: "MathPlacer") -> int:
    """Put a 1pt marker in the first and last row of every table."""
    count = 0
    for n, wrap in enumerate(art.select("div.tablewrap")):
        tid = wrap.get("id") or f"tbw{n}"
        rows = wrap.select("tbody tr") or wrap.select("tr")
        if len(rows) < 2:
            continue
        for role, row in (("first", rows[0]), ("last", rows[-1])):
            cells = row.find_all(["td", "th"])
            if not cells:
                continue
            idx = placer.register_table(tid, role)
            img = soup.new_tag("img")
            img["src"] = f"mk{idx}.png"
            img["style"] = "width:1pt;height:1pt;"
            cell = cells[0] if role == "first" else cells[-1]
            if role == "first":
                cell.insert(0, img)
            else:
                cell.append(img)
            count += 1
    return count


MARKER_IMG = r"mk\d+\.png"

# A lead-in paragraph that introduces its formula ("集成方差，式 (7.2)：") and the
# display paragraph right after it.  Matching has to happen on the rendered HTML,
# because at this point the formula is a marker <p> created by MathPlacer, and
# the display in the source is a bare text fragment rather than an element.
PAIR_RE = re.compile(
    r"(<p>(?:(?!</p>).){0,240}?[：:]</p>)\s*"
    r'(<p id="mkp\d+"[^>]*>.*?</p>)', re.S)


def _pair_in_html(body: str, placer: "MathPlacer") -> tuple[str, int]:
    """Glue a short colon-ended lead-in to its display formula.

    Without this, MuPDF is free to break between the two and the reader gets
    "集成方差，式 (7.2)：" at the foot of one page and σ̂² at the top of the next
    (ch07 and ch04 both hit it).  The pair is wrapped in a div carrying the same
    1pt first/last markers as a box, so the existing keep-together pass moves it.
    """
    count = 0

    def repl(m):
        nonlocal count
        lead, disp = m.group(1), m.group(2)
        plain = re.sub(r"<[^>]+>", "", lead).strip()
        # Only a short label ("集成方差，式 (7.2)：") is worth keeping whole.  A
        # full paragraph ending in a colon may break normally: forcing every
        # such paragraph onto the next page costs a page or two per chapter.
        if len(plain) > 60:
            return m.group(0)
        pid = f"pr{count}"
        first = placer.register_block(pid, "first")
        last = placer.register_block(pid, "last")
        count += 1
        return (f'<div class="pair" id="{pid}">'
                f'<img src="mk{first}.png" style="width:1pt;height:1pt;"/>'
                f"{lead}{disp}"
                f'<img src="mk{last}.png" style="width:1pt;height:1pt;"/></div>')

    return PAIR_RE.sub(repl, body), count


def _mark_blocks(art, soup, placer: "MathPlacer") -> int:
    """Put a 1pt marker at the start and end of every framed block."""
    count = 0
    for n, block in enumerate(art.select("div.box, div.pair")):
        bid = block.get("id")
        if not bid:
            bid = f"bx{n}"
            block["id"] = bid
        kids = [k for k in block.children if getattr(k, "name", None)]
        content = [k for k in kids if "box-title" not in (k.get("class") or [])]
        # Only a box that could actually be torn in two needs the two markers.
        # A prose-only box (title + one paragraph) splits harmlessly, and its
        # 1pt markers cost more than they buy: they can be dropped by the page
        # builder and then look like lost formulas.
        if len(kids) < 2 or (len(content) == 1 and content[0].name == "p"):
            # A single-child box cannot split; skip the markers so the page
            # stays clean of 1pt artefacts.
            continue
        for role in ("first", "last"):
            idx = placer.register_block(bid, role)
            img = soup.new_tag("img")
            img["src"] = f"mk{idx}.png"
            img["style"] = "width:1pt;height:1pt;"
            if role == "first":
                block.insert(0, img)
            else:
                block.append(img)
            count += 1
    return count


def prepare(slug: str, math_cache: dict[str, str], work_dir: str):
    """Return (body_html, assets, math_placer, stats)."""
    page_path = config.page_html(slug)
    if not os.path.exists(page_path):
        raise SystemExit(f"{slug}: converted HTML missing ({page_path}); run md2html.py first")
    with open(page_path, encoding="utf-8") as fh:
        raw = fh.read()

    soup = BeautifulSoup(raw, "lxml")
    art = soup.select_one("article.md-content__inner")
    if art is None:
        raise RuntimeError(f"article body not found in {slug}")

    for sel in ("script", "style", "nav"):
        for node in art.select(sel):
            node.decompose()
    _normalise_nbsp(art)

    assets = AssetBag()
    placer = MathPlacer(math_cache, work_dir)
    n_img = _rewrite_images(art, soup, slug, assets, placer)
    n_tbl = _mark_tables(art, soup, placer)
    n_blk = _mark_blocks(art, soup, placer)

    body = str(art)
    body = placer.replace(body)
    # NOTE: pairing a colon-ended label with its display (see _pair_in_html) was
    # tried and withdrawn: markers placed directly inside the wrapper div were
    # sometimes not found again by the overlay scan (ch07 lost 10 formulas) and
    # the forced breaks added four pages to ch04.  The remaining orphan label is
    # cosmetic; a lost formula is not.  Kept here, disabled, as a record.
    n_pair = 0
    # Font splitting runs after the formulas have become <img> markers, because
    # it wraps ASCII runs in spans and would otherwise shred the LaTeX source.
    frag = BeautifulSoup(body, "html.parser")
    n_runs = _split_fonts(frag)
    body = "".join(str(child) for child in frag.contents)
    body = _tag_inline_anchors(body, placer)

    for name, path in placer.marker_files.items():
        assets.add(name, path)

    stats = {"images": n_img, "tables": n_tbl // 2,
             "formulas": sum(1 for e in placer.entries.values()
                             if e.get("kind") == "formula"),
             "math_failed": len(placer.failed), "latin_runs": n_runs,
             "eqnos": placer.eqno_count,
             "wide_inline": list(placer.wide_inline),
             "narrowed_eq": placer.narrowed_eq,
             "narrowed": list(placer.narrowed),
             "table_clamps": getattr(placer, "table_clamps", 0)}
    return body, assets, placer, stats
