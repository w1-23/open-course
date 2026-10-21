"""Cross-reference integrity: every 第 N 章 / 第 N.M 节 / 式 (N.k) / 图 N-k /
表 N-k / 算法 N-k that the prose points at must actually exist.

This is the check that catches the class of error a human reviewer found by hand
in the first edition ("第 2.2 节的 PPO" pointing at a section that does not
discuss PPO).  It cannot tell whether the reference is *appropriate*, only that
the target exists; that distinction is recorded in the verification matrix.

    python check_refs.py              # all chapters
    python check_refs.py --only 5     # one chapter
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys

import config
from check_content import _code_ranges, _mask, _read

SEC2 = re.compile(r"^##\s+(\d+)\.(\d+)\s")
SEC3 = re.compile(r"^###\s+(\d+)\.(\d+)\.(\d+)\s")
FIG = re.compile(r"!\[图\s*([0-9A-Za-z]+)-(\d+)")
TAB = re.compile(r"^:\s*表\s*([0-9A-Za-z]+)-(\d+)")
ALG = re.compile(r"^:::\s*algorithm\s+算法\s*([0-9A-Za-z]+)-(\d+)")
TAG = re.compile(r"\\tag\{([0-9A-Za-z]+)\.(\d+)\}")

REF_CH = re.compile(r"第\s*(\d+)\s*章")
REF_PART = re.compile(r"第\s*(\d+)\s*部分")
REF_SEC = re.compile(r"第\s*(\d+)(?:\.(\d+))?(?:\.(\d+))?\s*节")
REF_EQ = re.compile(r"式\s*[（(]\s*([0-9A-Za-z]+)\.(\d+)\s*[)）]")
REF_FIG = re.compile(r"图\s*([0-9A-Za-z]+)-(\d+)")
REF_TAB = re.compile(r"表\s*([0-9A-Za-z]+)-(\d+)")
REF_ALG = re.compile(r"算法\s*([0-9A-Za-z]+)-(\d+)")


def _strip_math(text: str) -> str:
    """Drop LaTeX so numbers inside formulas are not read as references."""
    text = re.sub(r"\\\[.*?\\\]", " ", text, flags=re.S)
    text = re.sub(r"\\\(.*?\\\)", " ", text, flags=re.S)
    return text


def anchors(path: str) -> dict[str, set]:
    """Everything in one chapter that a reference may legitimately point at."""
    _, text = _read(path)
    lines = text.splitlines()
    masked = _mask(lines)
    got: dict[str, set] = {"sec2": set(), "sec3": set(), "fig": set(),
                           "tab": set(), "alg": set(), "eq": set()}
    for line in masked:
        if m := SEC2.match(line):
            got["sec2"].add((int(m.group(1)), int(m.group(2))))
        if m := SEC3.match(line):
            got["sec3"].add((int(m.group(1)), int(m.group(2)), int(m.group(3))))
        if m := FIG.search(line):
            if (no := config.no_of_prefix(m.group(1))) is not None:
                got["fig"].add((no, int(m.group(2))))
        if m := TAB.match(line):
            if (no := config.no_of_prefix(m.group(1))) is not None:
                got["tab"].add((no, int(m.group(2))))
        if m := ALG.match(line):
            if (no := config.no_of_prefix(m.group(1))) is not None:
                got["alg"].add((no, int(m.group(2))))
    # Equations live in display blocks, which _mask keeps (it only hides code).
    for m in TAG.finditer(text):
        if (no := config.no_of_prefix(m.group(1))) is not None:
            got["eq"].add((no, int(m.group(2))))
    return got


EXTERNAL = ("原书", "该书", "教材", "书中", "课程", "讲义", "原著", "上文",
            "Sutton", "Barto", "Puterman", "Bertsekas", "Szepesv", "S&B",
            "Kaelbling", "Arulkumaran")


def refs(path: str) -> list[tuple[int, str, tuple]]:
    """(line number, kind, key) for every cross reference in the prose."""
    _, text = _read(path)
    lines = _mask(text.splitlines())
    out: list[tuple[int, str, tuple]] = []

    def add(i: int, line: str, m, kind: str, key: tuple) -> None:
        # "原书第 16 章" / "CS285 第 4 讲" point at other books, not at this one;
        # only the clause just before the reference decides.
        # 40 个字符足够覆盖「（Sutton & Barto, 2018, 第 13.5 节）」这类括注，
        # 又不会把本句前面真正的内部引用误判成外部。
        window = line[max(0, m.start() - 40):m.start()]
        if any(mark in window for mark in EXTERNAL):
            return
        out.append((i, kind, key))

    for i, raw in enumerate(lines, 1):
        line = _strip_math(raw)
        for m in REF_PART.finditer(line):
            add(i, line, m, "part", (int(m.group(1)),))
        for m in REF_CH.finditer(line):
            add(i, line, m, "chapter", (int(m.group(1)),))
        for m in REF_SEC.finditer(line):
            if m.group(2) is None:
                continue          # "第 3 节" style is not used in this book
            if m.group(3) is None:
                add(i, line, m, "sec2", (int(m.group(1)), int(m.group(2))))
            else:
                add(i, line, m, "sec3", (int(m.group(1)), int(m.group(2)),
                                         int(m.group(3))))
        for m in REF_EQ.finditer(line):
            if (no := config.no_of_prefix(m.group(1))) is not None:
                add(i, line, m, "eq", (no, int(m.group(2))))
        for m in REF_FIG.finditer(line):
            if (no := config.no_of_prefix(m.group(1))) is not None:
                add(i, line, m, "fig", (no, int(m.group(2))))
        for m in REF_TAB.finditer(line):
            if (no := config.no_of_prefix(m.group(1))) is not None:
                add(i, line, m, "tab", (no, int(m.group(2))))
        for m in REF_ALG.finditer(line):
            if (no := config.no_of_prefix(m.group(1))) is not None:
                add(i, line, m, "alg", (no, int(m.group(2))))
    return out


LABEL = {"part": "第 N 部分", "chapter": "第 N 章", "sec2": "第 N.M 节",
         "sec3": "第 N.M.K 节", "eq": "式 (N.k)", "fig": "图 N-k",
         "tab": "表 N-k", "alg": "算法 N-k"}


def check(path: str, all_anchors: dict[str, dict[str, set]]) -> list[str]:
    problems: list[str] = []
    mine = anchors(path)
    top = len(config.CHAPTERS)
    for line, kind, key in refs(path):
        if kind == "chapter":
            if key[0] < 1:
                problems.append(f"第 {line} 行：引用不存在的第 {key[0]} 章")
            continue
        if kind == "part":
            if not 1 <= key[0] <= len(config.PARTS):
                problems.append(f"第 {line} 行：引用不存在的第 {key[0]} 部分")
            continue
        if key[0] > top:
            # A number beyond this book's chapters can only point at another
            # work ("Sutton & Barto 第 13 章"), so it is not ours to verify.
            continue
        pool = mine if key[0] == mine_no(path) else all_anchors.get(key[0], {})
        if key not in pool.get(kind, set()):
            # A section may also be addressed only by its subsection number.
            if kind == "sec2" and any(k[:2] == key for k in pool.get("sec3", set())):
                continue
            problems.append(f"第 {line} 行：{LABEL[kind]} 不存在（{key}）")
    return problems


def mine_no(path: str) -> int:
    meta, _ = _read(path)
    try:
        return int(meta.get("no", "0"))
    except ValueError:
        return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, default=0)
    args = ap.parse_args()
    files = sorted(glob.glob(os.path.join(config.CONTENT_DIR, "ch*.md")))
    # --only narrows what is REPORTED, not what counts as an anchor: a chapter
    # that cites 第 4.3 节 must still be checked against chapter 4's headings.
    all_anchors: dict[int, dict[str, set]] = {}
    for f in files:
        all_anchors[mine_no(f)] = anchors(f)
    if args.only:
        files = [f for f in files if mine_no(f) == args.only]
    bad = 0
    for f in files:
        problems = check(f, all_anchors)
        bad += len(problems)
        name = os.path.basename(f)
        if problems:
            print(f"FAIL {name}  {len(problems)} 处引用无效")
            for p in problems[:20]:
                print("      " + p)
            if len(problems) > 20:
                print(f"      …… 另有 {len(problems) - 20} 处")
        else:
            print(f"OK   {name}")
    print(f"\n引用检查：{len(files)} 章，{bad} 处问题")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
