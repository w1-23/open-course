"""Turn a cached lecture page into Story-ready HTML plus asset tables.

Responsibilities:
  * strip site chrome, code line-number anchors, headerlinks
  * rewrite <img src> to local files held in a fitz.Archive
  * replace LaTeX with correctly sized 1x1 marker images (vector formulas are
    overlaid later, once the exact placement rectangles are known)
  * convert the few .svg diagrams into PDFs so they stay vector
"""

import html as htmllib
import os

from PIL import Image
import re
import struct
import zlib

from bs4 import BeautifulSoup, NavigableString

import config
import diagrams

INLINE_RE = re.compile(r"\\\([\s\S]*?\\\)")
DISPLAY_RE = re.compile(r"\\\[[\s\S]*?\\\]")

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
def _drop(art, selectors) -> None:
    for sel in selectors:
        for node in art.select(sel):
            node.decompose()


def _clean_code(art, soup) -> None:
    """Remove line-number anchors and the empty leading span Pygments emits."""
    for block in art.select("div.highlight"):
        pre = block.find("pre")
        if pre is None:
            continue
        code = pre.find("code")
        if code is None:
            code = soup.new_tag("code")
            code.string = pre.get_text()
            pre.clear()
            pre.append(code)
        for a in code.select("a"):
            a.decompose()
        for span in code.find_all("span", recursive=False):
            if not span.get_text(strip=True) and not span.find("span"):
                span.decompose()


def _unwrap_links(art) -> None:
    for a in art.select("a.glightbox"):
        a.unwrap()


def _normalise_nbsp(art) -> None:
    """Code text comes back with U+00A0 instead of spaces; normalise it."""
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

    def _new_marker(self, entry: dict) -> int:
        idx = self.next_idx
        self.next_idx += 1
        name = f"mk{idx}.png"
        path = os.path.join(self.work_dir, name)
        make_marker(path, idx)
        self.marker_files[name] = path
        self.entries[idx] = entry
        return idx

    def _register(self, latex: str, display: bool) -> int | None:
        svg = self.cache.get(("D|" if display else "I|") + htmllib.unescape(latex))
        if not svg:
            self.failed.append(latex)
            return None
        return self._new_marker({"latex": latex, "display": display,
                                 "svg": svg, "kind": "formula"})

    def register_diagram(self, svg_text: str, nat_w: float, nat_h: float) -> int:
        """Reserve space for an .svg figure that must stay vector."""
        idx = self._new_marker({"latex": "", "display": False, "svg": svg_text,
                                "kind": "diagram", "nat_w": nat_w, "nat_h": nat_h})
        return idx

    def diagram_size(self, idx: int) -> tuple[float, float]:
        e = self.entries[idx]
        avail = config.BODY_X1 - config.BODY_X0
        w, h = e["nat_w"], e["nat_h"]
        if w > avail:
            k = avail / w
            w, h = w * k, h * k
        return w, h

    def diagram_tag(self, idx: int) -> str:
        w, h = self.diagram_size(idx)
        self.entries[idx]["box"] = (w, h)
        return (f'<p id="mkp{idx}" style="text-align:center;margin:8pt 0;'
                f'break-inside:avoid;">'
                f'<img src="mk{idx}.png" style="width:{w:.2f}pt;height:{h:.2f}pt"/>'
                f'</p>')

    def _size(self, svg: str, display: bool) -> tuple[float, float]:
        wm = re.search(r'width="([\d.]+)ex"', svg)
        hm = re.search(r'height="([\d.]+)ex"', svg)
        wx = float(wm.group(1)) if wm else 3.0
        hx = float(hm.group(1)) if hm else 1.2
        if display:
            w, h = wx * config.DISPLAY_SCALE, hx * config.DISPLAY_SCALE
            if w > config.DISPLAY_MAX_WIDTH:
                k = config.DISPLAY_MAX_WIDTH / w
                w, h = w * k, h * k
        else:
            w, h = wx * config.EX_PT, hx * config.EX_PT
        return w, h

    def formula_size(self, idx: int) -> tuple[float, float]:
        entry = self.entries[idx]
        return self._size(entry["svg"], entry["display"])

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
        w, h = self._size(svg, display)
        if display:
            self.entries[idx]["box"] = (w, h)
            img = f'<img src="mk{idx}.png" style="width:{w:.2f}pt;height:{h:.2f}pt"/>'
            return (f'<p id="mkp{idx}" style="text-align:center;text-indent:0;'
                    f'margin:8pt 0;break-inside:avoid;">{img}</p>')
        # An inline formula with a fraction or a big operator can be taller than
        # the leading; left at full size it would reach into the line above.  It
        # is scaled down just enough to sit inside the leading, which keeps the
        # rhythm of the page even and never lets a formula collide with its
        # neighbours.  render.render_lecture draws it at the box's own scale.
        lead = config.BODY_FONT_SIZE * config.BODY_LINE_HEIGHT
        k = min(1.0, lead / h) if h > lead else 1.0
        self.entries[idx]["box"] = (w * k, h * k)
        return (f'<img src="mk{idx}.png" '
                f'style="width:{w * k:.2f}pt;height:{h * k:.2f}pt"/>')

    def replace(self, body: str) -> str:
        def do_display(m):
            idx = self._register(m.group(0), True)
            return self._tag(idx, True) if idx is not None else m.group(0)

        def do_inline(m):
            idx = self._register(m.group(0), False)
            return self._tag(idx, False) if idx is not None else m.group(0)

        body = DISPLAY_RE.sub(do_display, body)
        return INLINE_RE.sub(do_inline, body)


_MARKER_SRC_RE = re.compile(r"^mk(\d+)\.png$")


def _clamp_table_markers(frag, placer: "MathPlacer") -> int:
    """Shrink a formula that sits in a table cell so the table stays in its column.

    MuPDF Story gives a table at least the natural width of its widest cell, and
    the width of a maths marker is fixed, so one long formula in one cell used to
    push a four column table straight through the writing column and across the
    page rule.  Each cell is allowed an equal share of the body width, with a
    little slack for the padding, and anything wider is scaled down.  The drawing
    is vector, so shrinking the box costs no sharpness.
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
            # A four column table of prose is already at the limit of the body
            # column; a slightly smaller face is the only way it fits without
            # bleeding into the writing column.
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
        if placer.entries[idx].get("display"):
            continue
        block = img.find_parent(
            ["p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th"])
        if block is None:
            continue
        # Breaking inside a boxed block would strand its title or its caption on
        # the previous page, so the whole box is what moves.
        box = block.find_parent("div", class_=["admonition", "figwrap"])
        if box is not None:
            block = box
        if not block.get("id"):
            block["id"] = f"mkp{idx}"
        # Every marker in the block needs to know which block owns it: a
        # paragraph can carry several inline formulas, and the break/nudge
        # machinery must be able to find the owner for any of them, not just
        # for the first one that claimed the id.
        placer.entries[idx]["anchor"] = block["id"]
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
    m = re.search(r'<svg[^>]*?width="([\d.]+)"[^>]*?height="([\d.]+)"', svg_text)
    if m:
        return float(m.group(1)), float(m.group(2))
    vb = re.search(r'viewBox="([\d.\s-]+)"', svg_text)
    if vb:
        parts = [float(x) for x in vb.group(1).split()]
        if len(parts) == 4:
            return parts[2], parts[3]
    return 600.0, 300.0


def _px_size(path: str) -> tuple[int, int]:
    """Pixel size of an image file, or (0, 0) when it cannot be read."""
    try:
        with Image.open(path) as im:
            return im.size
    except Exception:
        return 0, 0


def _fix_figures(art, soup) -> int:
    """Pull a lone illustration out of its paragraph so it can be full width.

    On the source site every figure is written as
        <p><a class="glightbox"><img ...></a><em>caption</em></p>
    so the caption shares the paragraph with the image.  Story then lays the
    image out inline and shrinks it to whatever width is left beside the
    caption text, which produced small, oddly cropped figures.  Splitting the
    paragraph into a figure block plus a caption block fixes the geometry and
    keeps the caption (and any formula inside it) intact.
    """
    changed = 0
    for p in list(art.find_all("p")):
        imgs = p.find_all("img")
        if len(imgs) != 1:
            continue
        img = imgs[0]
        holder = img.parent if getattr(img.parent, "name", None) == "a" else img
        fig = soup.new_tag("div")
        fig["class"] = "figure"
        fig.append(holder.extract())
        p.insert_before(fig)

        rest = [c.extract() for c in list(p.children)]
        wrap = soup.new_tag("div")
        wrap["class"] = "figwrap"
        fig.insert_before(wrap)
        wrap.append(fig)
        if any(str(c).strip() for c in rest):
            cap = soup.new_tag("div")
            cap["class"] = "caption"
            for child in rest:
                cap.append(child)
            wrap.append(cap)
        p.decompose()
        changed += 1
    return changed


def _rewrite_images(art, soup, slug: str, url: str, assets: AssetBag,
                    placer: "MathPlacer") -> int:
    """Resolve the two figure conventions used in authored chapters.

    ``fig:<label>/<file>.png``  a paper figure mirrored under source/img/
    ``dia:<name>.svg``          a hand-drawn diagram under source/diagrams/,
                                embedded as a vector (stays sharp at any zoom).

    Raster figures keep a pinned explicit size: Story would otherwise size them
    from the file resolution, and would squeeze a caption-sharing image into the
    leftover space at the foot of a page instead of carrying it over.
    """
    count = 0
    for img in list(art.find_all("img")):
        src = img.get("src") or ""
        if src.startswith("dia:"):
            path = os.path.join(config.DIAG_DIR, src[4:])
            if not os.path.exists(path):
                img.replace_with(NavigableString(f"[缺图 {src}]"))
                continue
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            nw, nh = _svg_natural_size(text)
            idx = placer.register_diagram(text, nw, nh)
            holder = BeautifulSoup(placer.diagram_tag(idx), "html.parser")
            anchor = img.find_parent("a")
            target = anchor if anchor is not None else img
            target.replace_with(holder)
            count += 1
            continue
        if src.startswith("fig:"):
            local = os.path.join(config.SRC_IMG_DIR, src[4:])
        else:
            local = ""
        if not local or not os.path.exists(local):
            img.replace_with(NavigableString(f"[缺图 {src}]"))
            continue
        ext = os.path.splitext(local)[1].lower() or ".jpg"
        name = f"{slug}_fig{count:02d}{ext}"
        assets.add(name, local)
        img["src"] = name
        img.attrs.pop("width", None)
        img.attrs.pop("height", None)
        if img.find_parent("div", class_="figure") is not None:
            px_w, px_h = _px_size(local)
            if px_w and px_h:
                avail = config.BODY_X1 - config.BODY_X0
                w_pt = min(avail, max(120.0, px_w * 0.5))
                h_pt = w_pt * px_h / px_w
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
        if node.find_parent(["pre", "code", "script", "style"]) is not None:
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


def _section_breaks(art, soup) -> int:
    """Open each top-level section on a fresh page without a divider rule."""
    heads = art.find_all("h2")
    for i, head in enumerate(heads):
        classes = list(head.get("class", []))
        classes.append("section-start")
        if i == 0:
            classes.append("section-start-first")
        head["class"] = classes
    return len(heads)


def prepare(slug: str, url: str, math_cache: dict[str, str], work_dir: str):
    """Return (body_html, assets, math_placer, stats).

    Authored chapters live in author/<slug>.html (the canonical source); the
    build stages a byte-identical copy into source/html/<slug>.html so every
    stage (mathjax collection included) reads one location.
    """
    src_html = os.path.join(config.AUTHOR_DIR, f"{slug}.html")
    page_path = os.path.join(config.PAGE_DIR, f"{slug}.html")
    if os.path.exists(src_html):
        os.makedirs(config.PAGE_DIR, exist_ok=True)
        with open(src_html, encoding="utf-8") as fh:
            raw = fh.read()
        with open(page_path, "w", encoding="utf-8") as fh:
            fh.write(raw)
    elif not os.path.exists(page_path):
        raise RuntimeError(f"no chapter source for {slug}")
    with open(page_path, encoding="utf-8") as fh:
        raw = fh.read()

    soup = BeautifulSoup(raw, "lxml")
    art = soup.select_one("article.md-content__inner")
    if art is None:
        raise RuntimeError(f"article body not found in {slug}")

    _drop(art, ["a.headerlink", "a.md-content__button", "script", "style", "nav"])
    _unwrap_links(art)
    _clean_code(art, soup)
    _normalise_nbsp(art)
    _fix_figures(art, soup)
    n_sections = _section_breaks(art, soup)

    assets = AssetBag()
    placer = MathPlacer(math_cache, work_dir)
    n_img = _rewrite_images(art, soup, slug, url, assets, placer)

    body = str(art)
    body = placer.replace(body)
    # Font splitting runs after the formulas have become <img> markers, because
    # it wraps ASCII runs in spans and would otherwise shred the LaTeX source.
    frag = BeautifulSoup(body, "html.parser")
    n_runs = _split_fonts(frag)
    body = "".join(str(child) for child in frag.contents)
    body = _tag_inline_anchors(body, placer)

    for name, path in placer.marker_files.items():
        assets.add(name, path)

    stats = {"images": n_img, "formulas": len(placer.entries),
             "math_failed": len(placer.failed), "sections": n_sections,
             "latin_runs": n_runs,
             "table_clamps": getattr(placer, "table_clamps", 0)}
    return body, assets, placer, stats
