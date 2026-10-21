"""正文口吻的机械自检（配合 content/_VOICE.md）。

只查可以机械判定的几件事，不评价文采：

1. 空话词表命中；
2. 以「本节将介绍 / 下面我们来看 / 本节介绍」开头的段落；
3. 连续三条及以上 bullet（堆叠列表）；
4. 「首先/其次/最后」或「第一/第二/第三」连用三次以上的段落序列；
5. 本章小结是否为 bullet 清单（应为散文）。

用法：
    python scripts/check_voice.py                # 全部章节
    python scripts/check_voice.py --only 3       # 只查第 3 章
    python scripts/check_voice.py content/x.md   # 指定文件
"""
from __future__ import annotations

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import config  # noqa: E402

BANNED = ["具有重要意义", "值得注意的是", "从某种意义上说", "不仅", "综上所述",
          "众所周知", "不难发现", "极大地", "至为关键", "在本文中", "总而言之",
          "有着重要的", "起到了重要作用"]

OPENER = re.compile(r"^本节(将)?(介绍|讨论|讲解|给出|阐述)")
BULLET = re.compile(r"^\s*[-*+]\s+\S")
HEAD2 = re.compile(r"^##\s+(.+?)\s*$")
ORDINAL = ("首先", "其次", "最后")
ENUM = ("第一", "第二", "第三")

CLOSING = "本章小结"
# 这几个节按体例就是清单（公式表、文献表、题号），不计入「堆叠 bullet」
LIST_SECTIONS = ("关键公式", "延伸阅读", "习题")


def _section_ids(lines: list[str]) -> list[int]:
    """每行所属的 h2 节序号（h2 之前的行归 0）。"""
    out, sid = [], 0
    for ln in lines:
        if HEAD2.match(ln):
            sid += 1
        out.append(sid)
    return out


def _list_sections(lines: list[str]) -> set[int]:
    """这些节的序号可以合法用列表。"""
    bad, sid = set(), 0
    for ln in lines:
        m = HEAD2.match(ln)
        if m:
            sid += 1
            if any(k in m.group(1) for k in LIST_SECTIONS):
                bad.add(sid)
    return bad


def _code_ranges(lines: list[str]) -> set[int]:
    """行号集合：围栏代码块内部（不参与口吻检查）。"""
    inside, out, fence = False, set(), ""
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith("```"):
            if not inside:
                inside, fence = True, s[:4]
            elif s.startswith(fence[:3]):
                inside = False
            zero = i
            out.add(zero)
            continue
        if inside:
            out.add(i)
    return out


def check(path: str) -> list[str]:
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    skip = _code_ranges(lines)
    problems: list[str] = []

    # 1. 空话
    hits: dict[str, int] = {}
    for i, ln in enumerate(lines):
        if i in skip:
            continue
        for w in BANNED:
            if w in ln:
                hits[w] = hits.get(w, 0) + 1
    if hits:
        detail = "、".join(f"{w}×{n}" for w, n in sorted(hits.items(), key=lambda kv: -kv[1]))
        problems.append(f"空话 {sum(hits.values())} 处：{detail}")

    # 2. 模板开场
    openers = [i + 1 for i, ln in enumerate(lines)
               if i not in skip and OPENER.match(ln.strip())]
    if openers:
        problems.append(f"模板开场 {len(openers)} 处（行 {openers[:5]}）")

    # 3. 堆叠列表（公式表、文献表、题号节除外）
    sections = _section_ids(lines)
    list_ok = _list_sections(lines)
    runs, cur, cur_start = [], 0, 0
    for i, ln in enumerate(lines):
        legal = i in skip or sections[i] in list_ok
        if BULLET.match(ln) and not legal:
            if cur == 0:
                cur_start = i + 1
            cur += 1
        else:
            if cur >= 3:
                runs.append((cur_start, cur))
            cur = 0
    if cur >= 3:
        runs.append((cur_start, cur))
    if runs:
        worst = max(runs, key=lambda r: r[1])
        problems.append(f"连续 3 条以上 bullet {len(runs)} 处（最长 {worst[1]} 条，行 {worst[0]}）")

    # 4. 序数连用：只查「首先/其次/最后」这类脚手架；
    # 「第一/第二/第三」在中文教材里常用来编号并列要点，不算病。
    ord_hits = []
    for i, ln in enumerate(lines):
        if i in skip or sections[i] in list_ok:
            continue
        if any(ln.strip().startswith(o) for o in ORDINAL):
            ord_hits.append(i + 1)
    streak, best = 1, 1
    for a, b in zip(ord_hits, ord_hits[1:]):
        streak = streak + 1 if b - a <= 3 else 1
        best = max(best, streak)
    if best >= 3:
        problems.append(f"「首先/其次/第一…」连用 {best} 次")

    # 5. 本章小结是否为 bullet
    in_sum = False
    bullets = 0
    for i, ln in enumerate(lines):
        m = HEAD2.match(ln)
        if m:
            in_sum = CLOSING in m.group(1)
            continue
        if in_sum and i not in skip and BULLET.match(ln):
            bullets += 1
    if bullets:
        problems.append(f"「本章小结」仍是 {bullets} 条 bullet（应为 1–2 段散文）")

    return problems


def resolve(no: int) -> str:
    ch = config.chapter_by_no(no)
    return os.path.join(config.CONTENT_DIR, ch["slug"] + ".md")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int)
    ap.add_argument("paths", nargs="*")
    args = ap.parse_args()

    if args.paths:
        targets = args.paths
    elif args.only is not None:
        targets = [resolve(args.only)]
    else:
        targets = [resolve(ch["no"]) for ch in config.CHAPTERS]

    bad = 0
    for path in targets:
        if not os.path.exists(path):
            print(f"MISS {path}")
            bad += 1
            continue
        problems = check(path)
        name = os.path.basename(path)
        if problems:
            bad += 1
            print(f"FAIL {name}")
            for p in problems:
                print(f"     - {p}")
        else:
            print(f"OK   {name}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
