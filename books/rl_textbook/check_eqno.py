"""Equation-number audit: the tags in the Markdown, the numbers the renderer
recorded, and the digits actually printed in the PDF must agree.

``\\tag{N.k}`` is destroyed whenever a display block is parsed as inline maths
(pandoc does that when the blank line above is missing), and the symptom is a
formula that renders without a number.  Nothing else notices, because the
formula itself still looks fine.  This script compares three sources:

    1. ``content/chNN.md``            - the intended sequence of tags
    2. ``cache/<slug>/eqno.json``     - what render.py actually drew
    3. ``output/<stem>.pdf``          - the text found at the right margin

    python check_eqno.py              # every chapter that has been built
    python check_eqno.py --only 5
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

import fitz

import config

TAG = re.compile(r"\\tag\{([0-9A-Za-z]+)\.(\d+)\}")


def md_tags(path: str) -> list[tuple[str, int]]:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    return [(a, int(b)) for a, b in TAG.findall(text)]


def check_one(no: int) -> list[str]:
    ch = config.chapter_by_no(no)
    problems: list[str] = []
    md_path = os.path.join(config.CONTENT_DIR, ch["slug"] + ".md")
    if not os.path.exists(md_path):
        return [f"缺少 {os.path.basename(md_path)}"]
    want = md_tags(md_path)
    pref = config.chapter_prefix(ch)
    bad = sorted({p for p, _ in want if p != pref})
    if bad:
        problems.append(f"\\tag 前缀应为 {pref}，出现了 {bad}")
    nums = [k for _, k in want]
    if nums != list(range(1, len(nums) + 1)):
        problems.append(f"Markdown 里的 \\tag 编号不连续：{nums[:12]}…")
    if len(set(nums)) != len(nums):
        dup = sorted({k for k in nums if nums.count(k) > 1})
        problems.append(f"重复编号：{dup}")

    data_path = os.path.join(config.cache_dir(ch["slug"]), "eqno.json")
    pdf_path = os.path.join(config.OUTPUT_DIR, ch["stem"] + ".pdf")
    if not os.path.exists(data_path) or not os.path.exists(pdf_path):
        return problems + [f"尚未构建（缺 eqno.json 或 {ch['stem']}.pdf）"]
    data = json.load(open(data_path, encoding="utf-8"))
    drawn = [(e["eqno"], e["page"]) for e in data.get("eqnos", [])]
    if len(drawn) != len(want):
        problems.append(f"渲染了 {len(drawn)} 个编号，Markdown 有 {len(want)} 个")

    doc = fitz.open(pdf_path)
    for label, page in drawn:
        want_text = f"({label})"
        page_no = page - 1
        if not 0 <= page_no < doc.page_count:
            problems.append(f"式 ({label}) 记录页码 {page} 越界")
            continue
        found = False
        for block in doc[page_no].get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    if span["text"].strip() == want_text and span["bbox"][2] > 425:
                        found = True
        if not found:
            problems.append(f"式 ({label}) 在第 {page} 页右边距找不到编号")
    doc.close()
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, default=0)
    args = ap.parse_args()
    nos = [args.only] if args.only else [c["no"] for c in config.CHAPTERS]
    bad = 0
    for no in nos:
        problems = check_one(no)
        ch = config.chapter_by_no(no)
        if problems:
            bad += len(problems)
            print(f"FAIL 第 {no} 章 {ch['title']}")
            for p in problems[:12]:
                print("      " + p)
        else:
            print(f"OK   第 {no} 章 {ch['title']}")
    print(f"\n编号检查：{len(nos)} 章，{bad} 处问题")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
