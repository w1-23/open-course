"""W0A/W0B：把 source/ 下的原始资料变成"可取证"的本地文献库。

做三件事，彼此独立，可分开跑：

  1. --meta   为每个源文件生成 source/library/<key>/meta.yaml
               （身份、版本、DOI/arXiv、sha256、页数、级别、许可证/使用限制）
  2. --pages  把 PDF 逐页切成 source/pages/<key>/pNNNN.txt（保留物理页码）
  3. --index  建 source/index.db（SQLite FTS5），供 search_sources.py 检索

设计约束（来自 v3.1 的工程规范）：

  * key 是稳定身份，version 是具体版本；证据卡引用 key+version+pdf_page。
  * 不复制原始 PDF（工作区里已有 30MB+73MB，复制只会让 sha256 分叉）；
    meta.yaml 用 path 指向原文件，sha256 校验该文件本身。
  * 印刷页码（printed_page）无法从所有 PDF 稳定提取，这里只记录物理页；
    缺印刷页时证据卡必须写 pdf_page，并注明"印刷页未提取"。
  * 元数据一律从 arXiv API / 文件本身取，不从模型记忆里写。

用法：
    python scripts/build_library.py --meta
    python scripts/build_library.py --pages
    python scripts/build_library.py --index
    python scripts/build_library.py --all
    python scripts/build_library.py --meta --only RLbook2020
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from datetime import date

import fitz
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "source")
LIB = os.path.join(SRC, "library")
PAGES = os.path.join(SRC, "pages")
DB = os.path.join(SRC, "index.db")
CACHE = os.path.join(ROOT, "cache")
ARXIV_CACHE = os.path.join(CACHE, "arxiv_meta.json")

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
    )
}

# key -> (相对 source/ 的路径, level, role)
#   level: S=教材/原始论文（可作定理依据） A=课程讲义 B=官方实现文档 C=综述（只建地图）
SOURCES = {
    "RLbook2020": ("book/RLbook2020.pdf", "S", "textbook"),
    "1509.02971_ddpg": ("papers/1509.02971_ddpg.pdf", "S", "algorithm"),
    "1509.06461_double-dqn": ("papers/1509.06461_double-dqn.pdf", "S", "algorithm"),
    "1511.05952_prioritized-replay": ("papers/1511.05952_prioritized-replay.pdf", "S", "algorithm"),
    "1511.06581_dueling-dqn": ("papers/1511.06581_dueling-dqn.pdf", "S", "algorithm"),
    "1602.01783_a3c": ("papers/1602.01783_a3c.pdf", "S", "algorithm"),
    "1706.03741_christiano-rlhf": ("papers/1706.03741_christiano-rlhf.pdf", "S", "algorithm"),
    "1707.06347_ppo": ("papers/1707.06347_ppo.pdf", "S", "algorithm"),
    "1712.01815_alphazero": ("papers/1712.01815_alphazero.pdf", "S", "algorithm"),
    "1801.01290_sac": ("papers/1801.01290_sac.pdf", "S", "algorithm"),
    "1802.01561_apex": ("papers/1802.01561_apex.pdf", "S", "algorithm"),
    "1811.12560_intro-to-deep-rl": ("papers/1811.12560_intro-to-deep-rl.pdf", "C", "survey"),
    "1911.08265_muzero": ("papers/1911.08265_muzero.pdf", "S", "algorithm"),
    "2006.04779_cql": ("papers/2006.04779_cql.pdf", "S", "algorithm"),
    "2203.02155_instructgpt": ("papers/2203.02155_instructgpt.pdf", "S", "algorithm"),
    "2305.18290_dpo": ("papers/2305.18290_dpo.pdf", "S", "algorithm"),
    "2402.03300_deepseekmath-grpo": ("papers/2402.03300_deepseekmath-grpo.pdf", "S", "algorithm"),
    "2407.16216_rl-for-llm-post-training": (
        "papers/2407.16216_rl-for-llm-post-training-survey.pdf", "C", "survey"),
    "2509.16679_rl-meets-llms": ("papers/2509.16679_rl-meets-llms-survey.pdf", "C", "survey"),
    # 网页：不给 S 级，只作教学与实现辅助
    "spinningup_rl_intro": ("pages/spinningup_rl_intro.html", "B", "docs"),
    "spinningup_rl_intro2": ("pages/spinningup_rl_intro2.html", "B", "docs"),
    "spinningup_rl_intro3": ("pages/spinningup_rl_intro3.html", "B", "docs"),
    "spinningup_vpg": ("pages/spinningup_vpg.html", "B", "docs"),
    "spinningup_ppo": ("pages/spinningup_ppo.html", "B", "docs"),
    "spinningup_trpo": ("pages/spinningup_trpo.html", "B", "docs"),
    "spinningup_ddpg": ("pages/spinningup_ddpg.html", "B", "docs"),
    "spinningup_td3": ("pages/spinningup_td3.html", "B", "docs"),
    "spinningup_sac": ("pages/spinningup_sac.html", "B", "docs"),
    "weng_policy_gradient": ("pages/weng_policy_gradient.html", "A", "teaching"),
    "weng_reward_hacking": ("pages/weng_reward_hacking.html", "A", "teaching"),
    "cs224r_index": ("pages/cs224r_index.html", "A", "teaching"),
    "cs285_index": ("pages/cs285_index.html", "A", "teaching"),
    "awesome_rlhf_readme": ("pages/awesome_rlhf_readme.md", "C", "map"),
}

LICENSE_NOTE = {
    "S": "本地核验用；原始论文/教材版权归原作者与出版方，不得随交付物再分发全文。",
    "A": "课程讲义/博客：本地核验与教学参考用，引用时标注出处与链接。",
    "B": "官方文档与代码文档：可引用，但只作实现说明，不作定理论据。",
    "C": "综述：只用于建立方法地图，不得作为关键定理的唯一依据。",
}


# ---------------------------------------------------------------- helpers

def _key_from_name(name: str) -> str:
    stem = os.path.splitext(name)[0]
    return stem


def _arxiv_id(stem: str) -> str | None:
    m = re.match(r"^(\d{4}\.\d{4,5})", stem)
    return m.group(1) if m else None


def _sha256(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(chunk), b""):
            h.update(blk)
    return h.hexdigest()


def _load_arxiv_cache() -> dict:
    if os.path.exists(ARXIV_CACHE):
        try:
            with open(ARXIV_CACHE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_arxiv_cache(d: dict) -> None:
    os.makedirs(CACHE, exist_ok=True)
    with open(ARXIV_CACHE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1, sort_keys=True)


def _arxiv_query(ids: list[str], cache: dict) -> dict:
    """批量取 arXiv 元数据（标题/作者/日期/DOI/主分类）。"""
    todo = [i for i in ids if i not in cache]
    if not todo:
        return cache
    url = "http://export.arxiv.org/api/query"
    for start in range(0, len(todo), 20):
        chunk = todo[start:start + 20]
        params = {"id_list": ",".join(chunk), "max_results": str(len(chunk))}
        for attempt in range(3):
            try:
                r = requests.get(url, params=params, headers=UA, timeout=60)
                if r.status_code == 200 and "<entry" in r.text:
                    break
            except Exception:
                pass
            time.sleep(1.5 * (attempt + 1))
        else:
            print(f"  [arxiv] 放弃 {chunk}")
            continue
        ns = {"a": "http://www.w3.org/2005/Atom",
              "arxiv": "http://arxiv.org/schemas/atom"}
        from xml.etree import ElementTree as ET
        root = ET.fromstring(r.text)
        for entry in root.findall("a:entry", ns):
            eid = (entry.findtext("a:id", default="", namespaces=ns) or "").rsplit("/", 1)[-1]
            eid = re.sub(r"v\d+$", "", eid)
            title = " ".join((entry.findtext("a:title", default="", namespaces=ns) or "").split())
            authors = [(a.findtext("a:name", default="", namespaces=ns) or "").strip()
                       for a in entry.findall("a:author", ns)]
            published = (entry.findtext("a:published", default="", namespaces=ns) or "")[:10]
            doi = entry.findtext("arxiv:doi", default="", namespaces=ns) or ""
            jref = entry.findtext("arxiv:journal_ref", default="", namespaces=ns) or ""
            primary = ""
            pc = entry.find("arxiv:primary_category", ns)
            if pc is not None:
                primary = pc.get("term", "")
            cache[eid] = {
                "title": title,
                "authors": [a for a in authors if a],
                "published": published,
                "doi": doi,
                "journal_ref": jref,
                "primary_category": primary,
            }
        print(f"  [arxiv] 取到 {len(chunk)} 条")
        time.sleep(3.0)  # arXiv 要求请求间隔
    _save_arxiv_cache(cache)
    return cache


def _yaml_str(s: str) -> str:
    if s is None:
        return "null"
    s = str(s).replace("\n", " ").strip()
    if s == "":
        return '""'
    # 一律加引号，除非是无歧义的纯 ASCII 词：YAML 里 "Title: 副标题" 这种含冒号的
    # 未加引号字符串会被解析成映射，直接让 safe_load 抛 ScannerError。
    if (re.fullmatch(r"[A-Za-z0-9_./+\-()\[\] ]+", s)
            and ":" not in s and "#" not in s
            and not s.startswith(("-", "?", ":"))):
        return s
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def _page_count(path: str) -> int | None:
    if not path.lower().endswith(".pdf"):
        return None
    try:
        with fitz.open(path) as doc:
            return doc.page_count
    except Exception as exc:  # pragma: no cover
        print(f"  [warn] 打不开 {path}: {exc}")
        return None


# ---------------------------------------------------------------- --meta

def discover() -> None:
    """把 source/ 里新抓到的文件自动纳入库（key 由文件名推断，不需改本文件）。

    级别默认：papers/*.pdf = S（综述按文件名含 survey/tutorial 判为 C），
    book/*.pdf = S，pages/*.html|.md = B（课程/博客按 names 判 A/C）。
    新抓的文献如要改级别，在 source/library/<key>/meta.yaml 里手动改 level。
    """
    for sub, ext_level in (("papers", "S"), ("book", "S")):
        d = os.path.join(SRC, sub)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.lower().endswith(".pdf"):
                continue
            rel = f"{sub}/{name}"
            if rel in {v[0] for v in SOURCES.values()}:
                continue          # 同一文件已登记（可能用了不同的 key），不要重复入库
            key = os.path.splitext(name)[0]
            if key in SOURCES:
                continue
            low = name.lower()
            level = "C" if ("survey" in low or "tutorial" in low) else ext_level
            role = "survey" if level == "C" else ("textbook" if sub == "book" else "algorithm")
            SOURCES[key] = (f"{sub}/{name}", level, role)
    d = os.path.join(SRC, "pages")
    if os.path.isdir(d):
        for name in sorted(os.listdir(d)):
            if not name.lower().endswith((".html", ".htm", ".md")):
                continue
            rel = f"pages/{name}"
            if rel in {v[0] for v in SOURCES.values()}:
                continue
            key = os.path.splitext(name)[0]
            if key in SOURCES:
                continue
            low = name.lower()
            level = "C" if "awesome" in low else ("A" if ("weng" in low or "cs2" in low) else "B")
            SOURCES[key] = (f"pages/{name}", level, "docs" if level == "B" else "teaching")


def build_meta(only: str | None = None) -> int:
    os.makedirs(LIB, exist_ok=True)
    arxiv_ids = []
    for key, (rel, level, role) in SOURCES.items():
        if only and key != only:
            continue
        aid = _arxiv_id(key)
        if aid:
            arxiv_ids.append(aid)
    cache = _load_arxiv_cache()
    if arxiv_ids:
        cache = _arxiv_query(arxiv_ids, cache)

    made = 0
    for key, (rel, level, role) in SOURCES.items():
        if only and key != only:
            continue
        path = os.path.join(SRC, rel)
        if not os.path.exists(path):
            print(f"MISS {key}: {rel} 不存在")
            continue
        aid = _arxiv_id(key)
        meta = cache.get(aid, {}) if aid else {}
        out_dir = os.path.join(LIB, key)
        os.makedirs(out_dir, exist_ok=True)
        pages = _page_count(path)
        sha = _sha256(path)
        version = date.fromtimestamp(os.path.getmtime(path)).isoformat()

        lines = [
            f"key: {_yaml_str(key)}",
            f"version: {_yaml_str(version)}",
            f"level: {_yaml_str(level)}",
            f"role: {_yaml_str(role)}",
            "title: " + _yaml_str(meta.get("title") or _title_from_file(path, key)),
        ]
        authors = meta.get("authors") or []
        if authors:
            lines.append("authors:")
            for a in authors:
                lines.append(f"  - {_yaml_str(a)}")
        else:
            lines.append("authors: []")
        lines.append("year: " + _yaml_str((meta.get("published") or "")[:4] or "null"))
        lines.append("published: " + _yaml_str(meta.get("published") or ""))
        lines.append("arxiv_id: " + _yaml_str(aid or ""))
        lines.append("doi: " + _yaml_str(meta.get("doi") or ""))
        lines.append("journal_ref: " + _yaml_str(meta.get("journal_ref") or ""))
        lines.append("primary_category: " + _yaml_str(meta.get("primary_category") or ""))
        lines.append("path: " + _yaml_str(os.path.join("source", rel).replace("\\", "/")))
        lines.append(f"bytes: {os.path.getsize(path)}")
        lines.append(f"pages: {pages if pages is not None else 'null'}")
        lines.append(f"sha256: {_yaml_str(sha)}")
        lines.append("retrieved: " + _yaml_str(date.today().isoformat()))
        lines.append("license_note: " + _yaml_str(LICENSE_NOTE.get(level, "")))
        lines.append("printed_page_note: " + _yaml_str(
            "只登记 PDF 物理页；未从版面稳定提取印刷页码，证据卡须写 pdf_page。"))
        with open(os.path.join(out_dir, "meta.yaml"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        made += 1
        print(f"OK   {key:36s} level={level} pages={pages} sha={sha[:12]}")
    print(f"meta: {made} 个")
    return 0


def _title_from_file(path: str, key: str) -> str:
    if path.lower().endswith((".html", ".htm")):
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                html = f.read(20000)
            m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
            if m:
                return " ".join(m.group(1).split())
        except Exception:
            pass
    if path.lower().endswith(".md"):
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.startswith("#"):
                        return line.lstrip("# ").strip()
                    if line.strip():
                        return line.strip()[:120]
        except Exception:
            pass
    return key


# ---------------------------------------------------------------- --pages

def _html_to_text(path: str) -> str:
    """HTML/Markdown -> 纯文本。网页只作教学/实现辅助（A/B/C 级），故不做版面保真。"""
    with open(path, encoding="utf-8", errors="ignore") as f:
        raw = f.read()
    if path.lower().endswith(".md"):
        return raw
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(raw, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        main = soup.find("article") or soup.find("main") or soup.body or soup
        return main.get_text("\n", strip=True)
    except Exception:
        return re.sub(r"<[^>]+>", " ", raw)


def build_pages(only: str | None = None) -> int:
    os.makedirs(PAGES, exist_ok=True)
    n_pdf = 0
    for key, (rel, level, role) in SOURCES.items():
        if only and key != only:
            continue
        path = os.path.join(SRC, rel)
        if not os.path.exists(path):
            continue
        if not path.lower().endswith(".pdf"):
            # 网页/README：整篇转成一个 p0001.txt，让 FTS 也能检索到（级别 A/B/C，不作定理论据）
            out_dir = os.path.join(PAGES, key)
            os.makedirs(out_dir, exist_ok=True)
            txt = _html_to_text(path)
            with open(os.path.join(out_dir, "p0001.txt"), "w", encoding="utf-8") as f:
                f.write(txt)
            print(f"OK   {key:36s} 网页转文本 {len(txt)} 字符")
            continue
        out_dir = os.path.join(PAGES, key)
        os.makedirs(out_dir, exist_ok=True)
        existing = [f for f in os.listdir(out_dir) if f.endswith(".txt")]
        with fitz.open(path) as doc:
            if len(existing) == doc.page_count:
                print(f"SKIP {key:36s} 已切分 {doc.page_count} 页")
                n_pdf += 1
                continue
            for i, page in enumerate(doc):
                txt = page.get_text("text") or ""
                with open(os.path.join(out_dir, f"p{i + 1:04d}.txt"), "w",
                          encoding="utf-8") as f:
                    f.write(txt)
            print(f"OK   {key:36s} {doc.page_count} 页")
        n_pdf += 1
    print(f"pages: {n_pdf} 个 PDF 已切分 -> {os.path.relpath(PAGES, ROOT)}")
    return 0


# ---------------------------------------------------------------- --index

def _guess_section(text: str) -> str:
    """从页首几行里猜一个章节标题，供检索结果展示（不保证准确）。"""
    for line in text.splitlines()[:12]:
        s = line.strip()
        if re.match(r"^\d+(\.\d+)*\s+[A-Z\u4e00-\u9fff]", s) and len(s) < 90:
            return s
    return ""


def build_index(only: str | None = None) -> int:
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""CREATE TABLE pages(
        key TEXT NOT NULL, pdf_page INTEGER NOT NULL,
        section TEXT, chars INTEGER, text TEXT,
        PRIMARY KEY(key, pdf_page))""")
    con.execute("""CREATE TABLE sources(
        key TEXT PRIMARY KEY, title TEXT, level TEXT, role TEXT, pages INTEGER)""")
    # FTS5：内容索引，供 search_sources.py 用
    try:
        con.execute("""CREATE VIRTUAL TABLE fts USING fts5(
            key UNINDEXED, pdf_page UNINDEXED, body,
            tokenize='unicode61 remove_diacritics 2')""")
        fts_ok = True
    except sqlite3.OperationalError as exc:
        print(f"  [warn] 本机 SQLite 无 FTS5（{exc}），退化为 LIKE 检索")
        fts_ok = False

    n_rows = 0
    for key in SOURCES:
        if only and key != only:
            continue
        d = os.path.join(PAGES, key)
        if not os.path.isdir(d):
            continue
        files = sorted(f for f in os.listdir(d) if f.endswith(".txt"))
        if not files:
            continue
        meta = _read_meta(key)
        con.execute("INSERT OR REPLACE INTO sources(key,title,level,role,pages) VALUES(?,?,?,?,?)",
                    (key, meta.get("title", key), meta.get("level", ""),
                     meta.get("role", ""), len(files)))
        rows = []
        for f in files:
            pno = int(re.sub(r"\D", "", f) or 0)
            with open(os.path.join(d, f), encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
            sec = _guess_section(text)
            con.execute("INSERT OR REPLACE INTO pages(key,pdf_page,section,chars,text) "
                        "VALUES(?,?,?,?,?)", (key, pno, sec, len(text), text))
            if fts_ok:
                rows.append((key, pno, text))
            n_rows += 1
        if fts_ok and rows:
            con.executemany("INSERT INTO fts(key,pdf_page,body) VALUES(?,?,?)", rows)
        print(f"OK   {key:36s} {len(files)} 页入索引")
    con.commit()
    if fts_ok:
        try:
            con.execute("INSERT INTO fts(fts) VALUES('optimize')")
            con.commit()
        except sqlite3.OperationalError:
            pass
    con.close()
    print(f"index: {n_rows} 页 -> {os.path.relpath(DB, ROOT)}")
    return 0


def _read_meta(key: str) -> dict:
    p = os.path.join(LIB, key, "meta.yaml")
    out = {}
    if not os.path.exists(p):
        return out
    with open(p, encoding="utf-8") as f:
        for line in f:
            if ":" in line and not line.startswith(("  ", "-")):
                k, _, v = line.partition(":")
                out[k.strip()] = v.strip().strip('"')
    return out


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description="建本地文献库（元数据/逐页/索引）")
    ap.add_argument("--meta", action="store_true")
    ap.add_argument("--pages", action="store_true")
    ap.add_argument("--index", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--only", default=None, help="只处理某个 key")
    args = ap.parse_args()
    if not (args.meta or args.pages or args.index or args.all):
        ap.print_help()
        return 2
    discover()
    if args.meta or args.all:
        build_meta(args.only)
    if args.pages or args.all:
        build_pages(args.only)
    if args.index or args.all:
        build_index(args.only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
