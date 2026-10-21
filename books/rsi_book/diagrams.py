"""Hand-redrawn vector versions of the text-only figures in the course notes.

Most of the 700-odd figures on the site are real screenshots, plots or video
frames and are embedded untouched.  A few, however, are pure text-and-box
diagrams that went through a lossy JPEG/PNG pass on the original site: those get
redrawn here as SVG so the labels stay readable at any zoom (and so the reader
can still edit them in the HTML edition).

A figure spec is keyed by ``(slug, image_index)`` where ``image_index`` is the
same 1-based ``NNN`` name used for the cached download of that page's images.
Return value is ``(svg_text, natural_width_pt, natural_height_pt)``.
"""

from __future__ import annotations

# --------------------------------------------------------------------- canvas
W = 384.0          # design width: the body column is 399pt wide
FONT = "DengXian"  # installed on Windows; MuPDF and every browser resolve it
MONO = "Consolas"

INK = "#1f2328"
LINE = "#8b949e"
BOX_FILL = "#eef3fb"
BOX_EDGE = "#7d93b2"
ACCENT_FILL = "#e8f0e4"
ACCENT_EDGE = "#7d9b6a"
WARN_FILL = "#fdf1d8"
WARN_EDGE = "#c9a227"


def _esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;"))


def _label(x, y, text, size=9.0, anchor="middle", fill=None, weight="normal",
           family=None, italic=False):
    extra = ' font-style="italic"' if italic else ""
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="{family or FONT}" '
            f'font-size="{size:.2f}" font-weight="{weight}" text-anchor="{anchor}" '
            f'fill="{fill or INK}"{extra}>{_esc(text)}</text>')


def _box(x, y, w, h, fill=BOX_FILL, edge=BOX_EDGE, rx=3.0, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
            f'rx="{rx}" fill="{fill}" stroke="{edge}" stroke-width="0.8"{d}/>')


def _vline(x, y0, y1, color=LINE, width=0.8, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x:.2f}" y1="{y0:.2f}" x2="{x:.2f}" y2="{y1:.2f}" '
            f'stroke="{color}" stroke-width="{width}"{d}/>')


def _hline(x0, x1, y, color=LINE, width=0.8, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x0:.2f}" y1="{y:.2f}" x2="{x1:.2f}" y2="{y:.2f}" '
            f'stroke="{color}" stroke-width="{width}"{d}/>')


def _arrow_down(x, y0, y1, color=LINE):
    return (_vline(x, y0, y1 - 5, color) +
            f'<path d="M {x-3.2:.2f} {y1-5:.2f} L {x:.2f} {y1:.2f} L {x+3.2:.2f} {y1-5:.2f} Z" fill="{color}"/>')


def _arrow_up(x, y0, y1, color=LINE):
    return (_vline(x, y0 + 5, y1, color) +
            f'<path d="M {x-3.2:.2f} {y0+5:.2f} L {x:.2f} {y0:.2f} L {x+3.2:.2f} {y0+5:.2f} Z" fill="{color}"/>')


def _svg(height: float, parts: list[str], width: float = W) -> str:
    body = "\n".join(parts)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" '
            f'height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}">\n'
            f'{body}\n</svg>')


# ------------------------------------------------------- 01 / fig 9: roundtrip
def _roundtrip() -> tuple[str, float, float]:
    """text -> encode -> token ids -> decode -> text, as a vertical cycle.

    Drawn as a straight three-box column so nothing overlaps: the earlier
    swooping-Bezier version had its arrow label sitting on the curve.
    """
    parts = []
    h = 158.0
    bx, bw, bh = 58.0, 268.0, 30.0
    cx = bx + bw / 2.0

    def row(y, text, caption, size, family=None, dash=None):
        out = [_box(bx, y, bw, bh, fill="#ffffff" if dash else BOX_FILL,
                    edge=BOX_EDGE, dash=dash)]
        out.append(_label(cx, y + bh / 2.0 + size * 0.35, text, size,
                          family=family))
        out.append(_label(bx + bw - 7.0, y + bh / 2.0 + 2.4, caption, 6.6,
                          anchor="end", fill="#8b949e"))
        return out

    y1, y2, y3 = 8.0, 68.0, 128.0
    parts += row(y1, "Stanford was founded in 1885.", "原文", 8.4,
                 family=MONO, dash="3 2")
    parts.append(_arrow_down(cx, y1 + bh, y2))
    parts.append(_label(cx + 8.0, y1 + bh + 15.0, "encode 编码", 8.0,
                        anchor="start"))
    parts += row(y2, "93447 9201 673 24363 306 228 13696", "token IDs", 7.6,
                 family=MONO)
    parts.append(_arrow_down(cx, y2 + bh, y3))
    parts.append(_label(cx + 8.0, y2 + bh + 15.0, "decode 解码", 8.0,
                        anchor="start"))
    parts += row(y3, "Stanford was founded in 1885.", "还原", 8.4, family=MONO)

    return _svg(h, parts), W, h


# ------------------------------------------------- 01 / fig 5: transformer stack
def _transformer_stack() -> tuple[str, float, float]:
    parts = []
    h = 250.0
    x0, bw = 40.0, 96.0

    def stack(x, labels, top, step=21.0, boxh=17.0):
        y = top
        for text, fill, edge in labels:
            parts.append(_box(x, y, bw, boxh, fill=fill, edge=edge))
            parts.append(_label(x + bw / 2, y + 12, text, 7.6))
            y += step

    left = [
        ("Softmax", BOX_FILL, BOX_EDGE),
        ("Linear Unembedding", BOX_FILL, BOX_EDGE),
        ("Norm", "#ffffff", BOX_EDGE),
        ("Transformer Block", ACCENT_FILL, ACCENT_EDGE),
        ("Transformer Block", ACCENT_FILL, ACCENT_EDGE),
        ("Add & Dropout", "#ffffff", BOX_EDGE),
        ("Token Embedding", WARN_FILL, WARN_EDGE),
        ("Absolute Position Embeddings", WARN_FILL, WARN_EDGE),
    ]
    stack(x0, left, 16)
    parts.append(_label(x0 + bw / 2, 243, "inputs", 7.6))

    rx = 232.0
    right = [
        ("Add", "#ffffff", BOX_EDGE),
        ("Dropout", "#ffffff", BOX_EDGE),
        ("Position-Wise Feed-Forward", ACCENT_FILL, ACCENT_EDGE),
        ("Norm", "#ffffff", BOX_EDGE),
        ("Add", "#ffffff", BOX_EDGE),
        ("Dropout", "#ffffff", BOX_EDGE),
        ("Causal Multi-Head Self-Attention", ACCENT_FILL, ACCENT_EDGE),
        ("Norm", "#ffffff", BOX_EDGE),
    ]
    stack(rx, right, 16)
    parts.append(_label(rx + bw / 2, 243, "input tensor with shape", 7.0))
    parts.append(_label(rx + bw / 2, 237, "[batch_size, seq_len, d_model]", 6.4,
                        family=MONO))

    # output arrows
    parts.append(_label(x0 + bw / 2 - 12, 8, "Output Probabilities", 7.2))
    parts.append(_vline(x0 + bw / 2, 9, 15))
    parts.append(_label(rx + bw / 2, 8, "Output tensor with shape", 7.0))
    parts.append(_vline(rx + bw / 2, 9, 15))

    # residual connections: a bracket on the right of each sub-block
    for y, target in ((16 + 21 * 7, 16 + 21 * 4),):
        pass
    parts.append(_vline(rx - 8, 16 + 21 * 0, 16 + 21 * 0 + 17, color="#b45309"))
    return _svg(h, parts), W, h


# ------------------------------------------------------- 01 / fig 6: compute box
def _compute_memory() -> tuple[str, float, float]:
    parts = []
    h = 150.0
    parts.append(_box(30, 12, 324, 40, fill=WARN_FILL, edge=WARN_EDGE, rx=2))
    parts.append(_label(192, 38, "Compute", 13.0, weight="bold"))
    parts.append('<path d="M 192 52 L 210 84 L 174 84 Z" fill="none" '
                 f'stroke="{LINE}" stroke-width="1"/>')
    parts.append(_vline(192, 84, 100))
    parts.append(_box(30, 100, 324, 40, fill=BOX_FILL, edge=BOX_EDGE, rx=2))
    parts.append(_label(192, 126, "Memory", 13.0, weight="bold"))
    parts.append(_label(256, 74, "数据搬运是瓶颈", 7.6, anchor="start"))
    return _svg(h, parts), W, h


# ----------------------------------------------- 01 / fig 7: prefill vs decoding
def _prefill_decoding() -> tuple[str, float, float]:
    parts = []
    h = 190.0
    parts.append(_hline(24, 360, 30, color="#b91c1c", width=1.2))
    parts.append(_hline(24, 360, 78, color="#15803d", width=1.2))
    parts.append(_label(30, 26, "Prefill Phase", 8.6, anchor="start", fill="#b91c1c"))
    parts.append(_label(354, 26, "Decoding Phase", 8.6, anchor="end", fill="#15803d"))
    parts.append(_label(192, 74, "KV-Cache", 8.6, fill="#b91c1c"))

    parts.append(_box(24, 30, 336, 48, fill="#eef3fb", edge="#c4cfe0"))
    parts.append(_box(24, 78, 336, 60, fill="#f4f7f2", edge="#cbdcc4"))

    xs = [40.0, 130.0, 220.0, 310.0]
    names = ["iteration 1", "iteration 2", "iteration 3", "iteration 4"]
    for i, (x, nm) in enumerate(zip(xs, names)):
        parts.append(_box(x, 92, 68, 20, fill="#ffffff", edge=BOX_EDGE, rx=2))
        parts.append(_label(x + 34, 106, nm, 7.4))
        parts.append('<path d="M '
                     f'{x + 34:.2f} 112 L {x + 46:.2f} 124 L {x + 34:.2f} 136 L '
                     f'{x + 22:.2f} 124 Z" fill="#e7ddf5" stroke="#9b8ac4" '
                     'stroke-width="0.7"/>')
        parts.append(_label(x + 34, 126, "decode", 6.6))
        if i < 3:
            parts.append(_hline(x + 68, x + 90, 124, color=LINE))
    parts.append(_label(30, 160, '"computer science is"', 8.0, anchor="start",
                        family=MONO))
    parts.append(_label(354, 160, "[EOS]", 8.0, anchor="end", family=MONO))
    parts.append(_label(192, 182, "每一轮解码都要重新读一遍 KV-Cache", 7.4))
    return _svg(h, parts), W, h


# --------------------------------------------------- 01 / fig 3: FLOPs table
def _flops_table() -> tuple[str, float, float]:
    head = ["PARAM", "FLOPs", "FLOPs", "FLOPs", "FLOPs"]
    sub = ["", "update", "MHA", "FFN", "attn"]
    rows = [
        ("OPT setups", "760M", "4.3E+15", "35%", "44%", "14.8%"),
        ("1.3B", "1.3B", "3.1E+15", "32%", "51%", "12.7%"),
        ("2.7B", "2.7B", "2.5E+15", "29%", "56%", "11.2%"),
        ("6.7B", "6.7B", "1.7E+15", "24%", "65%", "8.1%"),
        ("13B", "13B", "4.1E+17", "22%", "69%", "6.9%"),
        ("30B", "30B", "9.0E+17", "20%", "74%", "5.3%"),
        ("66B", "66B", "9.5E+17", "18%", "77%", "4.3%"),
        ("175B", "175B", "2.4E+18", "17%", "80%", "3.3%"),
    ]
    cols = [96.0, 60.0, 74.0, 46.0, 46.0, 46.0]
    parts = []
    x0, y0, rh = 24.0, 16.0, 15.0
    h = y0 + rh * (len(rows) + 2) + 14
    xs = [x0]
    for c in cols:
        xs.append(xs[-1] + c)
    total = xs[-1] - x0
    # header
    parts.append(_box(x0, y0, total, rh * 2, fill="#f5f7fa", edge=LINE, rx=0))
    for i, (name, subw) in enumerate(zip(head, sub)):
        cx = (xs[i] + xs[i + 1]) / 2
        if i == 0:
            parts.append(_label(xs[0] + 4, y0 + 19, name, 7.4, anchor="start"))
        else:
            parts.append(_label(cx, y0 + 10, name, 6.8))
        parts.append(_label(cx, y0 + 21, subw, 6.8))
    for r, row in enumerate(rows):
        y = y0 + rh * 2 + rh * r
        if r % 2 == 1:
            parts.append(_box(x0, y, total, rh, fill="#fafbfc", edge="#ffffff", rx=0))
        for i, cell in enumerate(row):
            cx = (xs[i] + xs[i + 1]) / 2
            if i == 0:
                parts.append(_label(xs[0] + 4, y + 10.4, cell, 6.8, anchor="start"))
            else:
                bold = "bold" if 0 < i < 3 else "normal"
                parts.append(_label(cx, y + 10.4, cell, 6.8, weight=bold))
    parts.append(_hline(x0, xs[-1], y0 + rh * 2, color=LINE))
    parts.append(_label(x0, h - 4, "表 1：各类算力占比（原文 Table 1）", 7.2, anchor="start"))
    return _svg(h, parts), W, h


FIGS = {
    ("lecture01-overview-tokenization", 3): _flops_table,
    ("lecture01-overview-tokenization", 5): _transformer_stack,
    ("lecture01-overview-tokenization", 6): _compute_memory,
    ("lecture01-overview-tokenization", 7): _prefill_decoding,
    ("lecture01-overview-tokenization", 9): _roundtrip,
}


def build(slug: str, index: int):
    """Return (svg, w, h) for a redrawn figure, or None to keep the original."""
    fn = FIGS.get((slug, index))
    if fn is None:
        return None
    return fn()
