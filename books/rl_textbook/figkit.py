"""Figure kit: one consistent visual language for every diagram in the book.

All figures are matplotlib SVG written to ``figures/out``.  The layout stage
keeps author SVG vector, so lines stay crisp at any zoom and the text inside a
figure never turns into a bitmap.

Two settings matter for the Chinese text:

``svg.fonttype = "path"``
    Glyphs are emitted as vector outlines, so the reader never needs 宋体 or
    Times installed for a figure to look right.

``svg.hashsalt``
    Fixed, so rebuilding an unchanged figure produces byte-identical SVG.  The
    cache and the PDF diff stay stable, and a rebuild that changes nothing does
    not make every page look modified.
"""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import font_manager

import config

OUT_DIR = config.FIG_OUT

# thesis-safe palette: muted, print-friendly, distinguishable in greyscale
INK = "#1f2328"
GREY = "#8b949e"
GRID = "#d8dbe0"
C0 = "#2f4b7c"   # main series
C1 = "#c85200"   # contrast / second series
C2 = "#7a5195"   # third series
C3 = "#4a7a3a"   # policy / reward
C4 = "#8a6d00"   # highlight
PALETTE = [C0, C1, C2, C3, C4]

_CJK_CANDIDATES = ("SimSun", "宋体", "Microsoft YaHei", "SimHei", "DengXian")
_registered = False


def _cjk_family() -> list[str]:
    """Find a CJK family matplotlib can actually use, registering a file if needed."""
    global _registered
    if not _registered:
        for name in _CJK_CANDIDATES:
            try:
                font_manager.findfont(name, fallback_to_default=False)
                return [name, "DejaVu Sans"]
            except Exception:
                continue
        for path in (config.FONT_CJK, config.FONT_CJK_BOLD):
            try:
                font_manager.fontManager.addfont(path)
            except Exception:
                continue
        _registered = True
    for name in _CJK_CANDIDATES:
        try:
            font_manager.findfont(name, fallback_to_default=False)
            return [name, "DejaVu Sans"]
        except Exception:
            continue
    return ["DejaVu Sans"]


def setup() -> None:
    """Apply the book's figure style.  Idempotent; call once per figure script."""
    family = _cjk_family()
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": family,
        "mathtext.fontset": "cm",
        "font.size": 8.5,
        "axes.titlesize": 9.0,
        "axes.labelsize": 8.5,
        "xtick.labelsize": 8.0,
        "ytick.labelsize": 8.0,
        "legend.fontsize": 8.0,
        "axes.linewidth": 0.6,
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.5,
        "grid.linestyle": (0, (2, 2)),
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 2.6,
        "ytick.major.size": 2.6,
        "legend.frameon": False,
        "figure.dpi": 120,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.04,
        "svg.fonttype": "path",
        "svg.hashsalt": "rl-textbook",
        "lines.linewidth": 1.1,
        "lines.markersize": 3.2,
        "axes.prop_cycle": matplotlib.cycler(color=PALETTE),
    })


def new(w_in: float = 3.3, h_in: float = 2.1, ncols: int = 1):
    """A figure sized for the 399pt text column (3.3in ≈ 238pt wide)."""
    fig, ax = plt.subplots(1, ncols, figsize=(w_in, h_in), constrained_layout=True,
                           facecolor="none")
    for a in (ax if ncols > 1 else [ax]):
        for side in ("top", "right"):
            a.spines[side].set_visible(False)
        # No axes background either: a white <rect> in the SVG renders as a
        # faint grey-lavender wash over the page instead of pure paper white, so
        # the figure is drawn on the page itself.
        a.set_facecolor("none")
    return fig, ax


def box(ax, xy, w, h, text, fc="#eef3fb", ec="#7d93b2", fs=8.0, **kw):
    """A labelled rounded box, the building block of the pipeline diagrams."""
    from matplotlib.patches import FancyBboxPatch
    ax.add_patch(FancyBboxPatch((xy[0], xy[1]), w, h,
                                boxstyle="round,pad=0.012,rounding_size=0.02",
                                linewidth=0.7, facecolor=fc, edgecolor=ec, **kw))
    ax.text(xy[0] + w / 2, xy[1] + h / 2, text, ha="center", va="center",
            fontsize=fs, color=INK, wrap=True)


def arrow(ax, start, end, text="", color=GREY, fs=7.5, style="-|>", rad=0.0, **kw):
    """An annotated arrow between two points in axes coordinates."""
    ax.annotate("", xy=end, xytext=start,
                arrowprops=dict(arrowstyle=style, color=color, linewidth=0.8,
                                shrinkA=1.5, shrinkB=1.5,
                                connectionstyle=f"arc3,rad={rad}", **kw))
    if text:
        mx, my = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
        ax.text(mx, my + 0.035, text, ha="center", va="bottom", fontsize=fs, color=color)


def blank(ax, xlim=(0, 1), ylim=(0, 1)):
    """A drawing surface: no ticks, no spines, for schematic figures."""
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)


def save(fig, name: str, verbose: bool = True) -> str:
    """Write ``figures/out/<name>.svg`` and report its natural size in points."""
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{name}.svg")
    fig.savefig(path, format="svg", metadata={"Date": None}, transparent=True)
    plt.close(fig)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    # Strip the XML declaration and DOCTYPE: both confuse MuPDF's SVG loader,
    # which only needs the root element onward.
    i = text.find("<svg")
    if i > 0:
        text = text[i:]
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    if verbose:
        import re
        m = re.search(r'viewBox="([\d.\s-]+)"', text)
        size = m.group(1) if m else "?"
        print(f"  {name}.svg  viewBox={size}  {os.path.getsize(path)/1024:.1f} KB")
    return path
