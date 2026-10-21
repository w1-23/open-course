"""Figure reproducibility: every SVG must be produced by its chapter script and
must not have changed since it was recorded.

The acceptance matrix asks for a REPRODUCED state, and mtime is not evidence:
re-running a plotting script rewrites the file whether or not the numbers moved.
So the manifest stores a content hash.  A figure that no longer matches means
either the script changed output or someone edited the SVG by hand - both have
to be looked at before the chapter counts as reproducible.

    python scripts\\check_figures.py --update   # after regenerating figures
    python scripts\\check_figures.py            # compare (default)
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIG_DIR = os.path.join(ROOT, "figures", "out")
MANIFEST = os.path.join(ROOT, "figures", "manifest.json")
CONTENT = os.path.join(ROOT, "content")

REF = re.compile(r"\]\(figures/out/([^)]+\.svg)\)")


def digest(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def scan() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for path in sorted(glob.glob(os.path.join(FIG_DIR, "*.svg"))):
        name = os.path.basename(path)
        out[name] = {"sha256": digest(path), "bytes": os.path.getsize(path)}
    return out


def referenced() -> dict[str, str]:
    """figure file -> the chapter that refers to it."""
    used: dict[str, str] = {}
    for path in sorted(glob.glob(os.path.join(CONTENT, "ch*.md"))):
        with open(path, encoding="utf-8") as fh:
            for name in REF.findall(fh.read()):
                used[name] = os.path.basename(path)
    return used


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true")
    args = ap.parse_args()
    os.makedirs(FIG_DIR, exist_ok=True)
    now = scan()
    used = referenced()
    old: dict[str, dict] = {}
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf-8") as fh:
            old = json.load(fh).get("figures", {})

    problems: list[str] = []
    if not args.update:
        for name, rec in now.items():
            if name not in old:
                problems.append(f"未登记的图：{name}（先确认是脚本产物，再 --update）")
            elif old[name]["sha256"] != rec["sha256"]:
                problems.append(f"内容已变：{name}")
        for name in old:
            if name not in now:
                problems.append(f"清单里有、磁盘上没有：{name}")
    for name, owner in used.items():
        if name not in now:
            problems.append(f"{owner} 引用了不存在的图：{name}")
    orphans = [n for n in now if n not in used]
    for name in orphans:
        problems.append(f"没有任何章节引用的孤儿图：{name}")

    if args.update:
        with open(MANIFEST, "w", encoding="utf-8") as fh:
            json.dump({"figures": now}, fh, ensure_ascii=False, indent=1, sort_keys=True)
        print(f"已登记 {len(now)} 幅图 → {os.path.relpath(MANIFEST, ROOT)}")
        return 0

    for p in problems:
        print("FAIL " + p)
    print(f"\n图形检查：{len(now)} 幅图，{len(used)} 处引用，{len(problems)} 处问题")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
