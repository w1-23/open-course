"""Shared LaTeX fragment handling used by both the MathJax cache and the layout.

Two things must agree exactly between the stage that *renders* formulas
(``mathjax.py``) and the stage that *looks them up* (``prepare.py``):

* normalization of the fragment (whitespace, the delimiters, HTML entities);
* removal of the ``\\tag{2.7}`` equation number, which is printed separately at
  the right margin by ``render.py`` and therefore must not be part of the
  rendered formula nor of its cache key.

Keeping both rules in one module is what stops "formula not found in cache"
from silently degrading into a black bar.
"""

import html as htmllib
import re

INLINE_RE = re.compile(r"\\\([\s\S]*?\\\)")
DISPLAY_RE = re.compile(r"\\\[[\s\S]*?\\\]")

# \tag{2.7} / \tag*{2.7}
EQ_TAG_RE = re.compile(r"\\tag\*?\s*\{([^{}]*)\}")


def strip_delims(raw: str) -> str:
    """Turn ``\\( x \\)`` / ``\\[ x \\]`` into bare TeX for MathJax."""
    s = htmllib.unescape(raw).strip()
    if s.startswith("\\[") and s.endswith("\\]"):
        s = s[2:-2]
    elif s.startswith("\\(") and s.endswith("\\)"):
        s = s[2:-2]
    return s.strip()


def split_eqno(tex: str) -> tuple[str, str | None]:
    """Separate ``\\tag{2.7}`` from the formula body.

    Returns (body, "2.7") or (body, None).  The tag is removed wherever it
    appears, because MathJax would otherwise draw it *inside* the formula's own
    SVG box, which is not where a thesis prints an equation number.
    """
    nums = EQ_TAG_RE.findall(tex)
    if not nums:
        return tex, None
    body = EQ_TAG_RE.sub("", tex)
    return body.strip(), nums[-1].strip()


def normalize(tex: str) -> str:
    """Whitespace-only normalisation, safe to apply to both sides of the cache."""
    return re.sub(r"\s+", " ", tex).strip()


def cache_key(raw: str, display: bool) -> str:
    """Stable lookup key: tagless, whitespace-normalised TeX plus the mode flag."""
    body, _ = split_eqno(strip_delims(raw))
    return ("D|" if display else "I|") + normalize(body)


def iter_fragments(body_html: str):
    """Yield (raw_fragment, is_display) in document order (display first per span)."""
    for m in DISPLAY_RE.finditer(body_html):
        yield m.group(0), True
    for m in INLINE_RE.finditer(body_html):
        yield m.group(0), False
