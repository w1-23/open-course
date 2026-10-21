r"""检查 review/cards/*.yaml 的结构与引用完整性，并生成修订台账。

用途
----
在"据证据改正文"之前，先把证据卡本身检查成可施工的状态。它**不判断数学是否正确**，
只判断：
  * 必填字段是否齐全、取值是否在允许集合内；
  * 每条 claim 的证据是否指向真实存在的文献与页码（页码不得超过该文献总页数）；
  * 引文是否足够长（防止空引文冒充核对过）；
  * 推导文件 / 复现脚本是否真的存在；
  * planned_fix 是否给出了可施工的落点。

用法
----
    python scripts\check_cards.py            # 检查全部卡片
    python scripts\check_cards.py --only 11  # 只检查某章
    python scripts\check_cards.py --ledger   # 另外刷新 review/revision_ledger.csv
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARD_DIR = os.path.join(ROOT, "review", "cards")
LIB_DIR = os.path.join(ROOT, "source", "library")
LEDGER = os.path.join(ROOT, "review", "revision_ledger.csv")

REQUIRED = ("issue_id", "chapter", "severity", "status", "title", "summary",
            "current_text", "sources", "claims", "planned_fix")
SEVERITY = {"P0", "P1", "P2"}
STATUS = {"已有依据", "待证据核验", "已核验", "作废"}
CLAIM_STATUS = {"已核对", "替代证据", "待核验"}
REVIEW_KEYS = ("math_check", "source_check", "consistency_check", "independent_reviewer")

ISSUE_ID = re.compile(r"^CH(\d{2})-([A-Z0-9]+)-(\d{3})$")


def _meta(key: str) -> dict | None:
    path = os.path.join(LIB_DIR, key, "meta.yaml")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _pending_keys() -> dict[str, str]:
    path = os.path.join(LIB_DIR, "PENDING.yaml")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    return {m.group(1): m.group(0) for m in re.finditer(r"^## ([a-z0-9_\-]+)$", text, re.M)}


def check(path: str, pending: dict[str, str]) -> tuple[list[str], dict]:
    problems: list[str] = []
    with open(path, encoding="utf-8") as fh:
        card = yaml.safe_load(fh) or {}
    name = os.path.basename(path)

    for key in REQUIRED:
        if key not in card or card[key] in (None, "", [], {}):
            problems.append(f"缺少字段 {key}")

    iid = str(card.get("issue_id", ""))
    m = ISSUE_ID.match(iid)
    if not m:
        problems.append(f"issue_id 格式应为 CHNN-XXX-000，当前 {iid!r}")
    elif iid != os.path.splitext(name)[0]:
        problems.append(f"issue_id {iid} 与文件名 {name} 不一致")
    else:
        ch = int(m.group(1))
        if card.get("chapter") != ch:
            problems.append(f"chapter={card.get('chapter')} 与 issue_id 章号 {ch} 不一致")

    if card.get("severity") not in SEVERITY:
        problems.append(f"severity 必须是 {sorted(SEVERITY)}，当前 {card.get('severity')!r}")
    if card.get("status") not in STATUS:
        problems.append(f"status 必须是 {sorted(STATUS)}，当前 {card.get('status')!r}")

    cur = card.get("current_text") or {}
    if not cur.get("file") or not os.path.exists(os.path.join(ROOT, str(cur.get("file")))):
        problems.append(f"current_text.file 不存在：{cur.get('file')!r}")
    if not str(cur.get("lines", "")).strip():
        problems.append("current_text.lines 为空（必须给出可定位的行号范围）")
    if len(str(cur.get("excerpt", ""))) < 20:
        problems.append("current_text.excerpt 太短，无法据此定位原文")

    srcs = card.get("sources") or []
    if not srcs:
        problems.append("sources 为空")
    keys_seen: list[str] = []
    for i, s in enumerate(srcs, 1):
        key = str(s.get("key", ""))
        keys_seen.append(key)
        level = s.get("level")
        if level not in {"S", "A", "B", "C"}:
            problems.append(f"sources[{i}] level 必须是 S/A/B/C，当前 {level!r}")
        if not s.get("role"):
            problems.append(f"sources[{i}] 缺少 role（这条证据用来支持什么）")
        quote = str(s.get("quote", "")).strip()
        if len(quote) < 25:
            problems.append(f"sources[{i}] quote 太短（{len(quote)} 字符），须是原文摘录")
        meta = _meta(key)
        if meta is None:
            if key in pending:
                if level != "C":
                    problems.append(f"sources[{i}] {key} 一手文献缺失（见 PENDING.yaml），"
                                    f"level 必须降为 C，当前 {level}")
            else:
                problems.append(f"sources[{i}] 文献库中没有 {key}（source/library/{key}/meta.yaml）")
        else:
            is_pdf = str(meta.get("path", "")).lower().endswith(".pdf")
            pages = int(meta.get("pages") or 0)
            pg = s.get("pdf_page")
            if is_pdf:
                if not isinstance(pg, int):
                    problems.append(f"sources[{i}] pdf_page 必须是整数，当前 {pg!r}")
                elif pages and not (1 <= pg <= pages):
                    problems.append(f"sources[{i}] pdf_page={pg} 超出 {key} 的 {pages} 页范围")
            else:
                # 网页类来源没有 PDF 页码，用 locator（章节标题/锚点）定位
                if not s.get("locator") and pg not in (1, None):
                    problems.append(f"sources[{i}] {key} 是网页来源，请用 locator 说明位置")
            if meta.get("level") and level and meta["level"] != level:
                problems.append(f"sources[{i}] level={level} 与库中记录 {meta['level']} 不一致")

    claims = card.get("claims") or []
    if not claims:
        problems.append("claims 为空")
    ids = []
    for i, c in enumerate(claims, 1):
        cid = str(c.get("id", ""))
        ids.append(cid)
        if not re.match(r"^c\d+$", cid):
            problems.append(f"claims[{i}] id 应为 c1/c2/...，当前 {cid!r}")
        if len(str(c.get("text", ""))) < 10:
            problems.append(f"claims[{i}] text 太短")
        if len(str(c.get("evidence", ""))) < 8:
            problems.append(f"claims[{i}] evidence 太短（须写明依据）")
        if c.get("status") not in CLAIM_STATUS:
            problems.append(f"claims[{i}] status 必须是 {sorted(CLAIM_STATUS)}，"
                            f"当前 {c.get('status')!r}")
        if c.get("status") == "已核对":
            ev = str(c.get("evidence", ""))
            markers = ("推导", "复现", "derivation", "reproduction", "式 (")
            if not any(k in ev for k in keys_seen) and not any(m in ev for m in markers):
                problems.append(f"claims[{i}] 标为已核对，但 evidence 未指向任何 source key 或推导/复现")
    if len(ids) != len(set(ids)):
        problems.append("claims 的 id 有重复")

    for field in ("derivation_file", "reproduction_file"):
        val = card.get(field)
        if val and not os.path.exists(os.path.join(ROOT, str(val))):
            problems.append(f"{field} 指向的文件不存在：{val}")

    pf = card.get("planned_fix") or []
    if len(pf) < 2:
        problems.append(f"planned_fix 只有 {len(pf)} 条，至少 2 条且要写到行/式级别")
    for i, item in enumerate(pf, 1):
        if len(str(item)) < 20:
            problems.append(f"planned_fix[{i}] 太笼统（{len(str(item))} 字符），须写清落点")

    review = card.get("review") or {}
    for key in REVIEW_KEYS:
        if key not in review:
            problems.append(f"review 缺少 {key}")

    rows = {
        "issue_id": iid,
        "chapter": card.get("chapter"),
        "severity": card.get("severity"),
        "status": card.get("status"),
        "claims": len(claims),
        "sources": ",".join(keys_seen),
        "fixes": len(pf),
        "math_check": review.get("math_check"),
        "source_check": review.get("source_check"),
        "title": str(card.get("title", ""))[:60],
    }
    return problems, rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, default=0, help="只检查某一章")
    ap.add_argument("--ledger", action="store_true", help="刷新修订台账 CSV")
    args = ap.parse_args()

    pending = _pending_keys()
    cards = sorted(glob.glob(os.path.join(CARD_DIR, "*.yaml")))
    if not cards:
        print("没有找到证据卡（review/cards/*.yaml）")
        return 1

    total_problems = 0
    rows: list[dict] = []
    for path in cards:
        name = os.path.basename(path)
        if args.only:
            m = ISSUE_ID.match(os.path.splitext(name)[0])
            if not m or int(m.group(1)) != args.only:
                continue
        problems, row = check(path, pending)
        rows.append(row)
        if problems:
            total_problems += len(problems)
            print(f"FAIL {name}  {len(problems)} 问题")
            for p in problems:
                print(f"     - {p}")
        else:
            print(f"OK   {name}  {row['claims']} claims / {row['sources'].count(',') + 1} 源 / {row['fixes']} 处修")

    if args.ledger and rows:
        with open(LEDGER, "w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"\n台账已写：{os.path.relpath(LEDGER, ROOT)}（{len(rows)} 条）")

    print(f"\n共 {len(rows)} 张卡，问题 {total_problems} 个")
    return 1 if total_problems else 0


if __name__ == "__main__":
    sys.exit(main())
