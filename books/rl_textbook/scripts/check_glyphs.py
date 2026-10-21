"""Check that every character we print has a glyph in the font that draws it.

MuPDF does not fall back across the two faces we register: an ASCII run goes to
Times New Roman, everything else to SimSun.  A missing glyph prints as a blank
or an empty box, and that defect survives every other check because the text is
still in the extractable stream.  Run this after editing any prose, appendix or
figure label that introduces new Greek/mathematical characters.

    python scripts\\check_glyphs.py                 # content/*.md + frontmatter
    python scripts\\check_glyphs.py content\\ch03.md  # one file (math is skipped)
    python scripts\\check_glyphs.py --chars γ−≥

Inside \\(...\\) and \\[...\\] the characters never reach SimSun: they are drawn by
MathJax into an SVG, so those spans are skipped when a path is given.  LaTeX
commands are skipped as well, otherwise a backslash-name would look like prose.
"""
from __future__ import annotations

import glob
import os
import re
import sys

import fitz

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import config  # noqa: E402

LATIN = fitz.Font(fontfile=config.FONT_LATIN)
CJK = fitz.Font(fontfile=config.FONT_CJK)

MATH_INLINE = re.compile(r"\\\(.+?\\\)", re.S)
MATH_DISPLAY = re.compile(r"\\\[.+?\\\]", re.S)
LATEX_CMD = re.compile(r"\\[A-Za-z]+")


def strip_math(text: str) -> str:
    """Remove the spans that MathJax draws, keeping the line structure."""
    text = MATH_DISPLAY.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    text = MATH_INLINE.sub("", text)
    return LATEX_CMD.sub("", text)


def missing(ch: str) -> str | None:
    """Return the face that lacks the glyph, or None when both can draw it."""
    if ch in "\n\r\t ":
        return None
    font = LATIN if ord(ch) < 128 else CJK
    try:
        if font.has_glyph(ord(ch)):
            return None
    except Exception:
        return "?"
    return "TNR" if font is LATIN else "宋体"


def scan_text(text: str) -> dict[str, str]:
    bad: dict[str, str] = {}
    for ch in text:
        face = missing(ch)
        if face:
            bad[ch] = face
    return bad


def scan_file(path: str) -> list[tuple[int, str, str]]:
    """(line number, character, face) for one file, maths excluded."""
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    hits: list[tuple[int, str, str]] = []
    for i, line in enumerate(lines, 1):
        for ch, face in scan_text(strip_math(line)).items():
            hits.append((i, ch, face))
    return hits


def _report_file(path: str) -> int:
    hits = scan_file(path)
    if not hits:
        print(f"OK  {os.path.basename(path)} 无缺字形")
        return 0
    by_char: dict[str, list[int]] = {}
    for line, ch, face in hits:
        by_char.setdefault(f"U+{ord(ch):04X} {ch!r} ({face})", []).append(line)
    for label, lines in sorted(by_char.items()):
        shown = "、".join(str(n) for n in lines[:8])
        more = "" if len(lines) <= 8 else f" 等 {len(lines)} 处"
        print(f"MISS {label}  行 {shown}{more}")
    print(f"{os.path.basename(path)}：{len(by_char)} 个字符缺字形")
    return 1


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "--chars":
        bad = scan_text(args[1])
        for ch, face in sorted(bad.items(), key=lambda kv: ord(kv[0])):
            print(f"MISS U+{ord(ch):04X} {ch!r}  缺少字形：{face}")
        print(f"共 {len(bad)} 个字符缺字形")
        return 1 if bad else 0
    if args:
        status = 0
        for path in args:
            path = path if os.path.isabs(path) else os.path.join(os.getcwd(), path)
            if not os.path.exists(path):
                print(f"跳过不存在的文件：{path}")
                continue
            status |= _report_file(path)
        return status

    parts = []
    for path in sorted(glob.glob(os.path.join(ROOT, "content", "*.md"))):
        if os.path.basename(path).startswith("_"):
            continue      # _STYLE.md / _CONVENTIONS.md 是规范文档，不排版
        with open(path, encoding="utf-8") as fh:
            parts.append(strip_math(fh.read()))
    with open(os.path.join(ROOT, "frontmatter.py"), encoding="utf-8") as fh:
        parts.append(strip_math(fh.read()))
    bad = scan_text("\n".join(parts))
    if not bad:
        print("OK  所有字符都有字形")
        return 0
    for ch, face in sorted(bad.items(), key=lambda kv: ord(kv[0])):
        print(f"MISS U+{ord(ch):04X} {ch!r}  缺少字形：{face}")
    print(f"共 {len(bad)} 个字符缺字形（全量模式：数学段已跳过，但代码块未排除）")
    return 1


if __name__ == "__main__":
    sys.exit(main())
