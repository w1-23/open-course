"""Acceptance matrix: the five states are computed, never asserted by hand.

    BUILD_PASS        PDF exists, pages/figures/formulas were produced, no formula
                      failed to render and none went missing.
    STRUCTURE_PASS    every layout and writing gate is clean (verify, content,
                      refs, eqno) - this says nothing about the mathematics.
    MATH_REVIEWED     review/math_review.yaml records a completed review.
    SOURCE_VERIFIED   review/source_review.yaml records that the chapter's claims
                      were traced to primary sources.
    REPRODUCED        the figures still hash to the recorded manifest.

Keeping them apart is the point: a chapter can be layout-perfect and still be
mathematically unreviewed, and this file must never suggest otherwise.

    python status.py                 # print + write output/验收矩阵.md
    python status.py --no-write
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import yaml

import check_math
import check_refs
import config
import verify
from check_content import check as content_check
from check_eqno import check_one as eqno_check
from scripts import check_figures

SOURCE_REVIEW = os.path.join(config.BUILD_DIR, "review", "source_review.yaml")


def _report() -> dict:
    path = config.REPORT_PATH
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return {c["no"]: c for c in data.get("chapters", [])}


def _source_states() -> dict[int, str]:
    if not os.path.exists(SOURCE_REVIEW):
        return {}
    with open(SOURCE_REVIEW, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    out: dict[int, str] = {}
    for row in data.get("chapters", []):
        # 不能写 `row.get("no") or ...`：第 0 章的 0 是合法值，假值会把整章跳过。
        no = row.get("no")
        if no is None:
            no = row.get(False)
        if not isinstance(no, int):
            continue
        out[no] = ("SOURCE_VERIFIED"
                   if row.get("status") == "reviewed"
                   and row.get("reviewer") and row.get("reviewed_at")
                   else "SOURCE_UNVERIFIED")
    return out


def _figure_state() -> str:
    manifest = check_figures.MANIFEST
    if not os.path.exists(manifest):
        return "REPRO_UNKNOWN"
    with open(manifest, encoding="utf-8") as fh:
        old = json.load(fh).get("figures", {})
    now = check_figures.scan()
    if not old:
        return "REPRO_UNKNOWN"
    if set(old) != set(now):
        return "REPRO_CHANGED"
    for name, rec in old.items():
        if rec.get("sha256") != now[name]["sha256"]:
            return "REPRO_CHANGED"
    return "REPRODUCED"


def build() -> list[dict]:
    report = _report()
    math_rows, math_states = check_math.check(check_math.load())
    src_states = _source_states()
    fig_state = _figure_state()
    files = sorted(glob.glob(os.path.join(config.CONTENT_DIR, "ch*.md")))
    all_anchors: dict[int, dict] = {}
    for f in files:
        all_anchors[check_refs.mine_no(f)] = check_refs.anchors(f)

    rows: list[dict] = []
    for ch in config.CHAPTERS:
        no = ch["no"]
        pdf = os.path.join(config.OUTPUT_DIR, ch["stem"] + ".pdf")
        md = os.path.join(config.CONTENT_DIR, ch["slug"] + ".md")
        info = report.get(no, {})
        notes: list[str] = []

        if not (os.path.exists(pdf) and os.path.exists(md)):
            rows.append({"no": no, "title": ch["title"], "pages": 0,
                         "budget": ch["budget"], "states": ["MISSING"],
                         "notes": ["尚未构建"]})
            continue

        pages = info.get("pages") or 0
        if not pages:
            import fitz
            with fitz.open(pdf) as doc:
                pages = doc.page_count
        build_ok = (info.get("math_failed", 0) == 0
                    and not info.get("lost_formulas")
                    and os.path.getsize(pdf) > 200000)
        if not build_ok and info:
            if info.get("math_failed"):
                notes.append(f"{info['math_failed']} 个公式渲染失败")
            if info.get("lost_formulas"):
                notes.append(f"{len(info['lost_formulas'])} 个公式未绘制")

        v = verify.check(pdf)

        def _n(key: str) -> int:
            value = v.get(key, 0)
            return len(value) if isinstance(value, list) else int(value)

        v_bad = sum(_n(k) for k in ("blank", "cue_hits", "band_hits",
                                    "slivers", "black_bars"))
        c_bad = len(content_check(md))
        r_bad = len(check_refs.check(md, all_anchors))
        e_bad = len(eqno_check(no)) if os.path.exists(
            os.path.join(config.cache_dir(ch["slug"]), "eqno.json")) else 1
        structure_ok = v_bad == 0 and c_bad == 0 and r_bad == 0 and e_bad == 0
        for label, n in (("版面", v_bad), ("写作", c_bad),
                         ("引用", r_bad), ("编号", e_bad)):
            if n:
                notes.append(f"{label} {n} 处")

        states = [
            "BUILD_PASS" if build_ok else "BUILD_FAIL",
            "STRUCTURE_PASS" if structure_ok else "STRUCTURE_FAIL",
            math_states.get(no, "MATH_UNREVIEWED"),
            src_states.get(no, "SOURCE_UNVERIFIED"),
            fig_state,
        ]
        lo, hi = ch["budget"]
        if not lo <= pages <= hi:
            notes.append(f"页数 {pages} 越界（{lo}–{hi}）")
        rows.append({"no": no, "title": ch["title"], "pages": pages,
                     "budget": ch["budget"], "states": states, "notes": notes})
    return rows


def render(rows: list[dict]) -> str:
    short = {"BUILD_PASS": "B✓", "BUILD_FAIL": "B✗", "MISSING": "—",
             "STRUCTURE_PASS": "S✓", "STRUCTURE_FAIL": "S✗",
             "MATH_REVIEWED": "M✓", "MATH_UNREVIEWED": "M·",
             "MATH_BLOCKED": "M✗", "SOURCE_VERIFIED": "T✓",
             "SOURCE_UNVERIFIED": "T·", "REPRODUCED": "R✓",
             "REPRO_CHANGED": "R✗", "REPRO_UNKNOWN": "R·"}
    lines = ["| 章 | 标题 | 页 | 预算 | B | S | M | T | R | 备注 |",
             "|:--|:--|--:|:--|:--|:--|:--|:--|:--|:--|"]
    for row in rows:
        st = [short.get(s, s) for s in row["states"]]
        st += [""] * (5 - len(st))
        note = "；".join(row["notes"])
        lines.append(f"| {row['no']} | {row['title']} | {row['pages']} | "
                     f"{row['budget'][0]}–{row['budget'][1]} | "
                     + " | ".join(st) + f" | {note} |")
    done = sum(1 for r in rows if "BUILD_PASS" in r["states"])
    struct = sum(1 for r in rows if "STRUCTURE_PASS" in r["states"])
    pages = sum(r["pages"] for r in rows)
    lines.append("")
    total = len(rows)
    lines.append(f"正文合计 {pages} 页；BUILD_PASS {done}/{total}；"
                 f"STRUCTURE_PASS {struct}/{total}。")
    lines.append("")
    lines.append("图例：B 构建、S 版式与写作、M 数学审校、T 来源核对、R 图形可复现。"
                 "「✓」= 通过，「·」= 未做，「✗」= 未通过。")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()
    rows = build()
    text = render(rows)
    print(text)
    if not args.no_write:
        path = os.path.join(config.OUTPUT_DIR, "验收矩阵.md")
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("# 验收矩阵\n\n" + text + "\n")
        with open(os.path.join(config.OUTPUT_DIR, "验收矩阵.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=1)
        print(f"\n写入 {path}")
    return 0 if all("STRUCTURE_FAIL" not in r["states"] for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
