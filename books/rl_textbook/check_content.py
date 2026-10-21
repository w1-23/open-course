"""Content self-check for a chapter written by an author agent.

The renderer guarantees the *typography*; this script guards the *writing
contract* documented in ``content/_STYLE.md`` so a chapter can be rejected
before anyone looks at a page image:

  * front matter with ``title`` and ``no``
  * sections numbered ``N.1 .. N.M`` in order, no gaps, no duplicates
  * ``\\tag{N.k}`` equation numbers consecutive from 1
  * ``图 N-k`` / ``表 N-k`` captions consecutive from 1, and every referenced
    figure file present on disk
  * the four closing sections (本章小结 / 关键公式 / 习题 / 延伸阅读)
  * forbidden constructs: ``$...$`` math, ``\\label`` / ``\\ref``, a table as
    the last thing in a section, Chinese inside a plain code fence

Usage:  python check_content.py            # every content/chNN.md
        python check_content.py --only 2
Exit code 1 if any chapter fails.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys

import config

CLOSING = ("本章小结", "关键公式", "习题", "延伸阅读")
CODE_FENCE = re.compile(r"^(```+)(.*)$")
CJK = re.compile(r"[\u4e00-\u9fff]")


def _read(path: str) -> tuple[dict, str]:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    meta: dict[str, str] = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            for line in text[3:end].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            text = text[end + 4:]
    return meta, text


def _code_ranges(lines: list[str]) -> list[tuple[int, int, str]]:
    """(start, end, fence_info) for every fenced block, 0-based inclusive."""
    out, open_at, info = [], None, ""
    for i, line in enumerate(lines):
        m = CODE_FENCE.match(line)
        if not m:
            continue
        if open_at is None:
            open_at, info = i, m.group(2).strip()
        else:
            out.append((open_at, i, info))
            open_at = None
    if open_at is not None:
        out.append((open_at, len(lines) - 1, info))
    return out


def _mask(lines: list[str]) -> list[str]:
    """Blank out fenced code so prose checks never look inside it."""
    masked = list(lines)
    for start, end, _ in _code_ranges(lines):
        for i in range(start, end + 1):
            masked[i] = ""
    return masked


def _blank_in_display(lines: list[str]) -> list[int]:
    """1-based line numbers of blank lines that fall inside a display formula."""
    bad: list[int] = []
    inside = False
    for i, raw in enumerate(lines):
        s = raw.strip()
        if not inside and s == r"\[":
            inside = True
            continue
        if inside:
            if s == r"\]":
                inside = False
            elif not s:
                bad.append(i + 1)
    return bad


def _in_box(lines: list[str], i: int) -> bool:
    """True when line i sits inside a ``::: ...`` fenced div."""
    depth = 0
    for j in range(i):
        s = lines[j].strip()
        if s.startswith(":::"):
            rest = s[3:].strip()
            depth = depth + 1 if rest else max(0, depth - 1)
    return depth > 0


def check(path: str) -> list[str]:
    name = os.path.basename(path)
    meta, body = _read(path)
    problems: list[str] = []
    if not meta.get("title"):
        problems.append("front matter 缺少 title")
    try:
        no = int(meta.get("no", ""))
    except ValueError:
        problems.append("front matter 缺少数字 no")
        no = 0

    lines = body.splitlines()
    masked = _mask(lines)
    prose = "\n".join(masked)

    # ---- sections ------------------------------------------------------
    heads = [s.strip() for s in masked if s.strip().startswith("## ")
             and not s.strip().startswith("###")]
    secs = []
    for h in heads:
        m = re.match(r"##\s+(\d+)\.(\d+)\s+(\S.*)$", h)
        if m:
            if no and int(m.group(1)) != no:
                problems.append(f"节号章号不符：{h[:24]}")
            secs.append(int(m.group(2)))
    if secs != list(range(1, len(secs) + 1)):
        problems.append(f"节编号不连续：{secs}")
    for need in CLOSING:
        if not any(s.endswith(need) or s == f"## {need}" for s in heads):
            problems.append(f"缺少收尾小节：{need}")

    # ---- equation numbers ---------------------------------------------
    tags = [int(m.group(2)) for m in
            re.finditer(r"\\tag\{([0-9A-Za-z]+)\.(\d+)\}", prose)]
    if tags and tags != list(range(1, len(tags) + 1)):
        bad = next(i for i, v in enumerate(tags, 1) if v != i)
        problems.append(f"公式编号断档：第 {bad} 个 tag 是 {tags[bad - 1]}")

    # A blank line inside \[ ... \] ends the display early: pandoc keeps the
    # first half, the tag is dropped and the trailing \] falls into the prose,
    # so the equation is printed without its number.  One real case: ch08 (8.16).
    bad_blank = _blank_in_display(lines)
    if bad_blank:
        problems.append("显示公式内部有空行（会把公式截断、丢编号），"
                        f"行号 {bad_blank[:6]}")

    # ---- figures / tables ---------------------------------------------
    figs = [int(m.group(2)) for m in
            re.finditer(r"图\s*([0-9A-Za-z]+)-(\d+)", prose)]
    fig_caps = [int(m.group(2)) for m in
                re.finditer(r"!\[图\s*([0-9A-Za-z]+)-(\d+)", prose)]
    if fig_caps and fig_caps != list(range(1, len(fig_caps) + 1)):
        problems.append(f"图号不连续：{fig_caps}")
    tabs = [int(m.group(2)) for m in
            re.finditer(r"^:\s*表\s*([0-9A-Za-z]+)-(\d+)", prose, re.M)]
    if tabs and tabs != list(range(1, len(tabs) + 1)):
        problems.append(f"表号不连续：{tabs}")

    for m in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", prose):
        src = m.group(1).strip()
        if src.startswith(("http://", "https://")):
            problems.append(f"图用了外链：{src}")
            continue
        full = src if os.path.isabs(src) else os.path.join(config.BUILD_DIR, src)
        if not os.path.exists(full):
            problems.append(f"图文件不存在：{src}")
        elif os.path.getsize(full) < 200:
            problems.append(f"图文件为空：{src}")

    # ---- forbidden constructs -----------------------------------------
    if re.search(r"(?<![\\$])\$[^$\n]+\$", prose):
        problems.append("出现 $...$ 行内公式（应使用 \\(...\\)）")
    for bad in ("\\label", "\\ref", "\\eqref"):
        if bad in prose:
            problems.append(f"出现 {bad}（编号由构建脚本负责）")
    if re.search(r"^##\s+.*\\\(", prose, re.M):
        problems.append("标题中含行内公式")

    # Display maths needs a blank line on both sides, or pandoc parses it as
    # inline maths: the \tag is dropped and a wide formula tears the sentence
    # apart.  Authors hit this constantly, so it is a hard error here.
    tight = []
    for i, line in enumerate(lines):
        if line.startswith("\\[") and i and lines[i - 1].strip():
            tight.append(i + 1)
        elif line.lstrip().startswith("\\]") and i + 1 < len(lines) and lines[i + 1].strip():
            tight.append(i + 1)
    if tight:
        problems.append(f"显示公式缺空行（{len(tight)} 处，行号 {tight[:6]}），"
                        f"请运行 python scripts\\fix_display.py 修正")

    # table as the last block of a section
    for i, line in enumerate(masked):
        if line.strip().startswith("## "):
            j = i + 1
            last = ""
            while j < len(lines) and not masked[j].strip().startswith("## "):
                if masked[j].strip():
                    last = masked[j].strip()
                j += 1
            if last.startswith("|") or re.match(r"^:\s*表", last):
                problems.append(f"小节 {line.strip()[3:20]} 以表格结尾")

    # Chinese inside a plain code fence (Consolas has no CJK glyphs)
    for start, end, info in _code_ranges(lines):
        if _in_box(lines, start):
            continue
        chunk = "\n".join(lines[start:end + 1])
        if CJK.search(chunk):
            problems.append(f"代码块内含中文（第 {start + 1} 行）")

    # ---- size ----------------------------------------------------------
    # A maths-heavy page carries ~700 characters, so 10k is already 16+ pages;
    # the floor only catches a chapter that is obviously a stub.
    chars = len(re.sub(r"\s", "", prose))
    if chars < 9000:
        problems.append(f"正文偏短：{chars} 字（目标 10000+，含公式的页面字数偏低是正常的）")
    return [f"{name}: {p}" for p in problems]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, default=0)
    args = ap.parse_args()
    files = sorted(glob.glob(os.path.join(config.CONTENT_DIR, "ch*.md")))
    if args.only:
        # 章号 -> slug：文件名不一定是 chNN.md（ch00、ch13prep 都不是），
        # 直接按 config.CHAPTERS 查，否则 --only 95 会静默地什么都不检查。
        try:
            slug = config.chapter_by_no(args.only)["slug"]
        except KeyError:
            raise SystemExit(f"--only {args.only}: 没有这个章号")
        files = [f for f in files if os.path.basename(f) == f"{slug}.md"]
        if not files:
            raise SystemExit(f"--only {args.only}: 找不到 content/{slug}.md")
    problems: list[str] = []
    for f in files:
        meta, body = _read(f)
        chars = len(re.sub(r"\s", "", body))
        found = check(f)
        problems += found
        status = "OK  " if not found else "FAIL"
        print(f"{status} {os.path.basename(f):12} {chars:6d} 字  "
              f"{len(found)} 问题")
        for p in found:
            print(f"     - {p.split(': ', 1)[1]}")
    print(f"\n{len(files)} 章 | 问题 {len(problems)}")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
