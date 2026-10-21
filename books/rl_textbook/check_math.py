"""Math-review record audit.

``verify.py`` proves the pages are laid out correctly; it proves nothing about
the mathematics.  The two conclusions are kept apart on purpose: a chapter can
be BUILD_PASS and still be un-reviewed.  This script checks that the review
record in ``review/math_review.yaml`` is *complete* - every chapter present,
every required field filled once the status is ``reviewed``, every tagged
equation claimed - and prints the resulting MATH_REVIEWED state.  It cannot
judge whether a derivation is right; that is what the ``reviewer`` field means.

    python check_math.py                 # summary + exit status
    python check_math.py --write-report  # also写入 output/构建报告.json 的 states
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

import yaml

import config

REVIEW = os.path.join(config.BUILD_DIR, "review", "math_review.yaml")
FIELDS = ("no", "status", "notes")
REVIEWED_FIELDS = ("reviewer", "reviewed_at", "source_hash", "equations",
                   "primary_sources")
STATUSES = {"pending", "reviewed", "blocked"}
TAG = re.compile(r"\\tag\{(\d+)\.(\d+)\}")


def load() -> list[dict]:
    with open(REVIEW, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data.get("chapters", [])


def tags_of(no: int) -> list[str]:
    # 章号并不等于下标（预备章 no=95 排在末尾），必须按 no 查。
    ch = config.chapter_by_no(no)
    path = os.path.join(config.CONTENT_DIR, ch["slug"] + ".md")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [f"{a}.{b}" for a, b in TAG.findall(fh.read())]


def check(rows: list[dict]) -> tuple[list[str], dict[int, str]]:
    problems: list[str] = []
    states: dict[int, str] = {}
    seen = {r.get("no") for r in rows}
    for ch in config.CHAPTERS:
        if ch["no"] not in seen:
            problems.append(f"第 {ch['no']} 章缺少审校记录")
    for row in rows:
        no = row.get("no")
        if not isinstance(no, int):
            problems.append(f"记录缺少整数 no：{row}")
            continue
        missing = [f for f in FIELDS if f not in row]
        if missing:
            problems.append(f"第 {no} 章记录缺字段：{missing}")
        status = row.get("status")
        if status not in STATUSES:
            problems.append(f"第 {no} 章 status 非法：{status!r}")
            states[no] = "MATH_UNREVIEWED"
            continue
        if status == "reviewed":
            for f in REVIEWED_FIELDS:
                if f not in row:
                    problems.append(f"第 {no} 章已标记 reviewed 但缺字段 {f}")
            for f in ("reviewer", "reviewed_at", "source_hash"):
                if not str(row.get(f) or "").strip():
                    problems.append(f"第 {no} 章已标记 reviewed 但 {f} 为空")
            claimed = [str(x) for x in (row.get("equations") or [])]
            want = tags_of(no)
            absent = [k for k in want if k not in claimed]
            if want and absent:
                problems.append(
                    f"第 {no} 章 reviewed 但未覆盖编号：{absent[:8]}"
                    f"（共 {len(absent)}/{len(want)} 条未声明）")
            extra = [k for k in claimed if want and k not in want]
            if extra:
                problems.append(f"第 {no} 章声明了不存在的编号：{extra[:8]}")
            if not (row.get("primary_sources") or []):
                problems.append(f"第 {no} 章 reviewed 但未列 primary_sources")
            states[no] = "MATH_REVIEWED"
        elif status == "blocked":
            states[no] = "MATH_BLOCKED"
        else:
            states[no] = "MATH_UNREVIEWED"
    return problems, states


def state_summary(states: dict[int, str]) -> str:
    counts: dict[str, int] = {}
    for v in states.values():
        counts[v] = counts.get(v, 0) + 1
    return "  ".join(f"{k}={v}" for k, v in sorted(counts.items()))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-report", action="store_true")
    args = ap.parse_args()
    if not os.path.exists(REVIEW):
        print(f"缺少 {REVIEW}")
        return 1
    rows = load()
    problems, states = check(rows)
    for p in problems:
        print("FAIL " + p)
    print(f"\n数学审校：{len(rows)} 章记录，{len(problems)} 处问题")
    print("状态：" + state_summary(states))
    if args.write_report:
        path = os.path.join(config.OUTPUT_DIR, "审校记录.json")
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"states": {str(k): v for k, v in states.items()},
                       "problems": problems}, fh, ensure_ascii=False, indent=1)
        print(f"写入 {path}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
