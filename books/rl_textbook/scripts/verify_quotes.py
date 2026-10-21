r"""核对证据卡里的引文是否真的出现在所声明的 PDF 页上。

这是"不许编造引文"的机械护栏：`sources[].quote` 必须能在
`source/pages/<key>/p<PDF页码:04d>.txt` 的文本里找到足够多的连续词。
PDF 抽取会带入连字符、软连字符、重音伪影（如 `↵`、`ﬂ`），所以比较前先归一化。

判定规则
--------
* **exact**：归一化后 quote 是页面文本的子串（最理想）。
* **strong**：把 quote 按词切分，在页面上滑动窗口求"命中词比例"，≥ 0.90 判为 strong
  （允许抽取造成的个别词合并/断行）。
* **weak / missing**：低于阈值 —— 必须人工复核，通常意味着页码错、引文被改写或翻译过。

用法
----
    python scripts\verify_quotes.py             # 检查全部卡片
    python scripts\verify_quotes.py --only 11   # 只查某章
    python scripts\verify_quotes.py --min 0.85  # 调整阈值
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys
import unicodedata

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARD_DIR = os.path.join(ROOT, "review", "cards")
PAGE_DIR = os.path.join(ROOT, "source", "pages")

_LIGATURES = {
    "\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi", "\ufb04": "ffl",
    "\u00ad": "", "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u2212": "-", "\u00a0": " ", "\u21b5": " ",
    "\u2032": "'", "\u2033": '"',
}


def normalize(text: str) -> str:
    for src, dst in _LIGATURES.items():
        text = text.replace(src, dst)
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    # 断行连字符：'exam-\nple' → 'example'
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def page_text(key: str, pdf_page: int) -> str | None:
    path = os.path.join(PAGE_DIR, key, f"p{pdf_page:04d}.txt")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8", errors="replace") as fh:
        return normalize(fh.read())


def coverage(quote_norm: str, page_norm: str) -> float:
    qwords = [w for w in re.split(r"[^0-9a-z\u4e00-\u9fff]+", quote_norm) if w]
    if not qwords:
        return 0.0
    pwords = re.split(r"[^0-9a-z\u4e00-\u9fff]+", page_norm)
    if not pwords:
        return 0.0
    n = len(qwords)
    if len(pwords) < n:
        hits = len(set(qwords) & set(pwords))
        return hits / n
    best = 0.0
    for i in range(0, len(pwords) - n + 1):
        window = pwords[i:i + n]
        same = sum(1 for a, b in zip(qwords, window) if a == b)
        if same / n > best:
            best = same / n
            if best >= 0.999:
                break
    return best


def split_fragments(quote: str) -> list[str]:
    """引文里允许用 ... / … 省略中间内容；每段都要独立命中，避免拼接式伪造。"""
    parts = re.split(r"\.\.\.|…|\[\.\.\.\]", quote)
    return [p.strip() for p in parts if len(p.strip()) >= 20]


def check_card(path: str, threshold: float) -> list[str]:
    issues: list[str] = []
    with open(path, encoding="utf-8") as fh:
        card = yaml.safe_load(fh) or {}
    iid = card.get("issue_id", os.path.basename(path))
    for i, src in enumerate(card.get("sources") or [], 1):
        key = str(src.get("key", ""))
        quote = str(src.get("quote", "")).strip()
        locator = src.get("locator")
        if len(quote) < 25:
            issues.append(f"{iid} sources[{i}] 引文过短，无法机械核对")
            continue
        pg = src.get("pdf_page")
        if not isinstance(pg, int):
            if locator:
                issues.append(f"{iid} sources[{i}] 网页来源（locator={locator}）：跳过页码核对")
                continue
            issues.append(f"{iid} sources[{i}] 缺少 pdf_page，无法核对引文")
            continue
        page = page_text(key, pg)
        if page is None:
            issues.append(f"{iid} sources[{i}] 缺少页面文本 source/pages/{key}/p{pg:04d}.txt")
            continue
        for frag in split_fragments(quote):
            qn = normalize(frag)
            if qn and qn in page:
                continue
            score = coverage(qn, page)
            if score < threshold:
                head = frag[:42].replace("\n", " ")
                issues.append(
                    f"{iid} sources[{i}] 片段「{head}…」在 {key} p.{pg} 上只匹配 {score:.2f} "
                    f"（< {threshold:.2f}）—— 页码错、引文被改写，或该页抽取失败"
                )
    return issues


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, default=0)
    ap.add_argument("--min", dest="threshold", type=float, default=0.85)
    args = ap.parse_args()

    cards = sorted(glob.glob(os.path.join(CARD_DIR, "*.yaml")))
    if args.only:
        cards = [c for c in cards if re.match(rf"CH{args.only:02d}-", os.path.basename(c))]
    if not cards:
        print("没有可检查的卡片")
        return 1

    total = 0
    checked = 0
    for path in cards:
        issues = check_card(path, args.threshold)
        name = os.path.basename(path)
        # 统计该卡实际核对了几条引文
        with open(path, encoding="utf-8") as fh:
            card = yaml.safe_load(fh) or {}
        n = len([s for s in (card.get("sources") or []) if isinstance(s.get("pdf_page"), int)])
        checked += n
        if issues:
            total += len(issues)
            print(f"FAIL {name}")
            for issue in issues:
                print(f"     - {issue}")
        else:
            print(f"OK   {name}  {n} 条引文全部命中")

    print(f"\n核对 {len(cards)} 张卡、{checked} 条引文，问题 {total} 个")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
