"""W0B：取证检索。任何"论文里说…"必须先变成这里的一条命中，再写进证据卡。

用法：
    python scripts/search_sources.py "baseline policy gradient"
    python scripts/search_sources.py "reward hacking" --key RLbook2020 --level S
    python scripts/search_sources.py "组内 优势" --limit 8
    python scripts/search_sources.py --eq "r_i" --key 2402.03300_deepseekmath-grpo

说明：
  * 命中按文献级别排序（S 在前），同级按 BM25 得分；
  * 每条命中给出 `key p.NNN`（PDF 物理页）与原文片段，片段前后各留 90 字符；
  * `--eq` 走的是字面量检索（FTS 会把 `r_i` 拆词），用于核对具体公式记号；
  * 结果仅供定位，是否成立必须回原文读上下文（见 _STYLE 的引用纪律第 3 条）。
"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "source", "index.db")
LEVEL_ORDER = {"S": 0, "A": 1, "B": 2, "C": 3}


def _connect() -> sqlite3.Connection:
    if not os.path.exists(DB):
        raise SystemExit("没有 source/index.db：先跑 python scripts\\build_library.py --all")
    return sqlite3.connect(DB)


def _has_fts(con: sqlite3.Connection) -> bool:
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='fts'").fetchone()
    return bool(row)


def _meta_map(con: sqlite3.Connection) -> dict:
    out = {}
    for key, title, level, role, pages in con.execute(
            "SELECT key,title,level,role,pages FROM sources"):
        out[key] = {"title": title, "level": level, "role": role, "pages": pages}
    return out


def _snippet(text: str, needle: str, width: int = 90) -> str:
    t = " ".join(text.split())
    idx = t.lower().find(needle.lower())
    if idx < 0:
        return t[: width * 2]
    lo = max(0, idx - width)
    hi = min(len(t), idx + len(needle) + width)
    pre = "…" if lo > 0 else ""
    suf = "…" if hi < len(t) else ""
    return f"{pre}{t[lo:idx]}【{t[idx:idx + len(needle)]}】{t[idx + len(needle):hi]}{suf}"


def search(query: str, key: str | None, level: str | None, limit: int,
           eq: bool, any_term: bool) -> int:
    con = _connect()
    meta = _meta_map(con)
    fts = _has_fts(con) and not eq
    hits = []

    if fts:
        q = query
        if any_term:
            q = " OR ".join(q.split())
        else:
            # 多词默认 AND：FTS5 里空格即 AND；加引号会变成短语，故只转义特殊符号
            q = re.sub(r'["\']', " ", q)
        try:
            rows = con.execute(
                "SELECT key, pdf_page, snippet(fts, 2, '»,', '«', ' … ', 24) "
                "FROM fts WHERE fts MATCH ? LIMIT ?", (q, limit * 6)).fetchall()
        except sqlite3.OperationalError as exc:
            print(f"[warn] FTS 查询失败（{exc}），退化为字面量检索")
            fts = False
            rows = []
        for k, pno, sn in rows:
            hits.append((k, pno, sn))
    if not fts:
        rows = con.execute(
            "SELECT key, pdf_page, text FROM pages WHERE text LIKE ? LIMIT ?",
            (f"%{query}%", limit * 6)).fetchall()
        for k, pno, text in rows:
            hits.append((k, pno, _snippet(text, query)))

    # 过滤 + 排序
    def _ok(k: str) -> bool:
        if key and k != key:
            return False
        if level and meta.get(k, {}).get("level") != level:
            return False
        return True

    hits = [h for h in hits if _ok(h[0])]
    hits.sort(key=lambda h: LEVEL_ORDER.get(meta.get(h[0], {}).get("level", "Z"), 9))
    hits = hits[:limit]

    if not hits:
        print(f'无命中："{query}"'
              + (f"（key={key}）" if key else "")
              + (f"（level={level}）" if level else ""))
        print("提示：换英文同义词（优势→advantage、组内→group、基线→baseline）或用 --eq 查记号。")
        return 1

    print(f'命中 {len(hits)} 条："{query}"'
          + (f"  key={key}" if key else "") + (f"  level={level}" if level else ""))
    for k, pno, sn in hits:
        m = meta.get(k, {})
        print(f"\n[{m.get('level', '?')}] {k} p.{pno}"
              f"  ({m.get('role', '')}, 共 {m.get('pages') or '?'} 页)")
        print(f"    {m.get('title', '')[:110]}")
        print(f"    {sn.strip()}")
        mp = os.path.join(ROOT, "source", "library", k, "meta.yaml")
        if os.path.exists(mp):
            with open(mp, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("path: "):
                        print(f"    原文：{line[6:].strip()} 第 {pno} 页")
                        break
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="在本地文献库中取证检索")
    ap.add_argument("query", nargs="+", help="检索词（可含中文，需英文同义词时参考 synonyms.yaml）")
    ap.add_argument("--key", default=None)
    ap.add_argument("--level", default=None, choices=["S", "A", "B", "C"])
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--eq", action="store_true", help="字面量检索（查公式记号、代码片段）")
    ap.add_argument("--any", action="store_true", help="任一词命中即可（默认全部命中）")
    args = ap.parse_args()
    return search(" ".join(args.query), args.key, args.level, args.limit,
                  args.eq, args.any)


if __name__ == "__main__":
    sys.exit(main())
