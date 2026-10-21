"""Author a chapter as Markdown -> the HTML that the layout stage consumes.

Why a separate converter instead of writing HTML by hand: the chapters are long
and math-heavy, and Pandoc's Markdown gives fenced divs, pipe tables with
captions, fenced code and ``\\(..\\)`` / ``\\[..\\]`` math for free.  The one
thing Pandoc does *not* know about is the contract the rest of this pipeline
expects (raw ``\\(..\\)`` text, figure blocks, table captions above the table,
section rules), so this module normalises its output into exactly that shape:

    content/chNN.md  --pandoc-->  normalised HTML  -->  cache/chNN/page.html

Conventions the authoring contract (content/_STYLE.md) documents and this
module enforces:

* first heading level used in the body is ``##`` (h2 = a numbered section);
  the chapter title (h1) comes from the front matter so it can never drift;
* ``::: algorithm 算法 2-1 REINFORCE`` / ``::: note 注`` shorthand is expanded
  to Pandoc fenced divs and becomes a bordered box with a title line;
* ``![图 1-2 说明](figures/out/ch01_f02.svg)`` becomes a figure block with the
  caption underneath;
* ``: 表 2-1 比较`` after a pipe table becomes a centred caption *above* the
  table (thesis convention), not a ``<caption>`` Story may not support;
* every ``##`` gets a double rule, and the closing sections flow on instead of
  forcing a page break each.

Usage:  python md2html.py --only 1        (or --all)
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys

from bs4 import BeautifulSoup, NavigableString

import config

BOX_TYPES = ("algorithm", "def", "thm", "prop", "note", "warn", "example")
# Sections that close a chapter: they keep the rule but do not force a new page.
TIGHT_PREFIXES = ("关键公式", "习题", "延伸阅读", "参考文献", "附录")

DIV_SHORT_RE = re.compile(r"^:::\s*([A-Za-z][\w-]*)\s*(.*?)\s*$")
IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
PANDOC_CANDIDATES = tuple(filter(None, (os.environ.get("PANDOC"), shutil.which("pandoc"), "pandoc")))


def find_pandoc() -> str:
    for c in PANDOC_CANDIDATES:
        if os.path.isabs(c):
            if os.path.exists(c):
                return c
        else:
            found = shutil.which(c)
            if found:
                return found
    raise SystemExit("pandoc not found; install Pandoc or set the PANDOC environment variable")


# ------------------------------------------------------------------ markdown
def read_front_matter(path: str) -> tuple[dict, str]:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    text = text.replace("\r\n", "\n")
    meta: dict[str, str] = {}
    if not text.startswith("---\n"):
        raise SystemExit(f"{path}: front matter block missing (--- title: ... ---)")
    end = text.find("\n---", 4)
    if end < 0:
        raise SystemExit(f"{path}: unterminated front matter block")
    block = text[4:end]
    body = text[end + 4:].lstrip("\n")
    for line in block.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, val = line.split(":", 1)
        meta[key.strip()] = val.strip().strip('"').strip("'")
    return meta, body


def expand_div_shorthand(body: str) -> str:
    """``::: note 注`` -> ``::: {.note title="注"}`` (Pandoc fenced-div syntax)."""
    out = []
    for line in body.split("\n"):
        m = DIV_SHORT_RE.match(line)
        if m:
            kind, title = m.group(1), m.group(2)
            if title:
                title = title.replace('"', "'")
                out.append(f'::: {{.{kind} title="{title}"}}')
            else:
                out.append(f"::: {{.{kind}}}")
        else:
            out.append(line)
    return "\n".join(out)


def smart_quotes(body: str) -> str:
    """Turn ``"…"`` into “…” (full-width) outside code and maths.

    Pandoc's ``smart`` extension does this for Latin prose but not reliably for
    Chinese, where a straight ``"`` next to a CJK character is left alone and
    then typeset in Times New Roman - which looks wrong in a 宋体 paragraph.
    A quote toggles open/closed per line, which matches how the chapters are
    written (every ``"`` has exactly one partner on the same line).
    """
    out: list[str] = []
    in_fence = False
    for line in body.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith(":::"):
            in_fence = (not in_fence) if stripped.startswith("```") else in_fence
            out.append(line)
            continue
        if in_fence or '"' not in line:
            out.append(line)
            continue
        # keep LaTeX untouched: split the line at math delimiters
        pieces = re.split(r"(\\\(.*?\\\)|\\\[.*?\\\])", line, flags=re.S)
        open_q = True
        for i, piece in enumerate(pieces):
            if i % 2:
                continue                      # a formula, leave as is
            buf = []
            for ch in piece:
                if ch == '"':
                    buf.append("“" if open_q else "”")
                    open_q = not open_q
                else:
                    buf.append(ch)
            pieces[i] = "".join(buf)
        out.append("".join(pieces))
    return "\n".join(out)


def run_pandoc(md_path: str) -> str:
    cmd = [
        find_pandoc(),
        "-f", "markdown+east_asian_line_breaks+tex_math_single_backslash",
        "-t", "html5",
        "--wrap=none",
        # html5 defaults to MathML, which would bake the formula into <em>/<sub>
        # markup and lose the TeX source the MathJax stage needs.  --mathjax
        # keeps the delimiters and the original TeX inside the span.
        "--mathjax",
        "--highlight-style=tango",
        md_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)
        raise SystemExit(f"pandoc failed on {md_path}")
    return proc.stdout


# ------------------------------------------------------------------ normalise
def _unwrap_math_spans(soup) -> None:
    """Pandoc wraps TeX in <span class="math ..">; the pipeline wants it bare."""
    for node in soup.select("span.math, div.math"):
        node.unwrap()


def _promote_display_blocks(soup) -> int:
    """A paragraph holding nothing but display math becomes the bare fragment.

    The layout stage replaces a ``\\[..\\]`` fragment with its own marker block;
    leaving it inside a ``<p>`` would nest paragraphs and the formula would be
    laid out as an inline image in the middle of an empty line.
    """
    changed = 0
    for p in list(soup.find_all("p")):
        text = p.get_text()
        stripped = text.strip()
        if not (stripped.startswith("\\[") and stripped.endswith("\\]")):
            continue
        if stripped.count("\\[") != 1 or stripped.count("\\]") != 1:
            continue
        p.replace_with(NavigableString("\n" + stripped + "\n"))
        changed += 1
    return changed


def _fix_mixed_display(soup) -> int:
    """Display maths written inside a sentence is re-shaped, not left inline.

    ``文字 \\[ 公式 \\] 文字`` inside one paragraph would otherwise become a
    nested block inside a ``<p>``: the formula is laid out at display size and
    the following words continue on the same line, which both looks wrong and
    stretches the leading.  Two repairs:

    * a short formula (a symbol being introduced, e.g. ``\\hat v(s,\\mathbf w)``)
      becomes inline maths, which is what the author meant;
    * a long one is split out into its own centred display block.
    """
    count = 0
    for p in list(soup.find_all("p")):
        html = p.decode_contents()
        if "\\[" not in html:
            continue
        parts = re.split(r"(\\\[.*?\\\])", html, flags=re.S)
        texts = [s for i, s in enumerate(parts) if i % 2 == 0]
        if len(parts) < 3 or not any(
                re.sub(r"<[^>]+>", "", s).strip() for s in texts):
            continue                      # pure display: handled elsewhere
        nodes = []
        for i, seg in enumerate(parts):
            if i % 2:
                inner = seg[2:-2].strip()
                tex_len = len(re.sub(r"\\[A-Za-z]+", "x", inner))
                if tex_len <= 56:
                    nodes.append(NavigableString(f"\\({inner}\\)"))
                else:
                    nodes.append(NavigableString("\n" + seg + "\n"))
            elif re.sub(r"<[^>]+>", "", seg).strip():
                frag = BeautifulSoup(f"<p>{seg}</p>", "lxml").find("p")
                if frag is not None:
                    nodes.append(frag)
        if not nodes:
            continue
        for n in nodes:
            p.insert_before(n)
        p.decompose()
        count += 1
    return count


def _figures(soup) -> int:
    """<figure><img><figcaption> -> div.figwrap > div.figure + div.caption."""
    count = 0
    for fig in list(soup.find_all("figure")):
        img = fig.find("img")
        if img is None:
            fig.decompose()
            continue
        cap = fig.find("figcaption")
        wrap = soup.new_tag("div")
        wrap["class"] = "figwrap"
        wrap["id"] = f"fg{count}"
        holder = soup.new_tag("div")
        holder["class"] = "figure"
        holder.append(img.extract())
        wrap.append(holder)
        if cap is not None:
            capdiv = soup.new_tag("div")
            capdiv["class"] = "caption"
            for child in list(cap.contents):
                capdiv.append(child.extract())
            wrap.append(capdiv)
        fig.replace_with(wrap)
        count += 1
    return count


def _table_captions(soup) -> int:
    """<caption> -> centred paragraph above the table, both in one no-split box.

    The caption has to travel with its table: if the table is pushed to the next
    page by ``break-inside: avoid`` (Story gives a table no way to split its
    header from its rows), a caption left behind would sit alone at the foot of
    the previous page.
    """
    count = 0
    for cap in list(soup.find_all("caption")):
        table = cap.find_parent("table")
        if table is None:
            cap.decompose()
            continue
        para = soup.new_tag("p")
        para["class"] = "tabcap"
        for child in list(cap.contents):
            para.append(child.extract())
        wrap = soup.new_tag("div")
        wrap["class"] = "tablewrap"
        # A stable id lets render.py push a table onto the next page when it
        # would otherwise be split away from its header row.
        wrap["id"] = f"tbw{count}"
        table.insert_before(wrap)
        wrap.append(para)
        wrap.append(table.extract())
        cap.decompose()
        count += 1
    return count


def _boxes(soup) -> int:
    """Fenced divs become bordered boxes with a title line."""
    count = 0
    for div in soup.find_all("div"):
        classes = div.get("class") or []
        kind = next((c for c in classes if c in BOX_TYPES), None)
        if kind is None:
            continue
        title = div.get("title")
        if title:
            div.attrs.pop("title", None)
        if "box" not in classes:
            div["class"] = list(classes) + ["box"]
        if not div.get("id"):
            div["id"] = f"bx{count}"
        if title:
            head = soup.new_tag("div")
            head["class"] = "box-title"
            head.string = title
            div.insert(0, head)
        count += 1
    return count


def _code_blocks(soup) -> int:
    """Flatten Pandoc's div.sourceCode wrapper; keep the token spans."""
    count = 0
    for div in soup.select("div.sourceCode"):
        pre = div.find("pre")
        if pre is None:
            continue
        code = pre.find("code")
        if code is not None:
            code["class"] = [c for c in (code.get("class") or []) if c != "sourceCode"]
            if not code["class"]:
                del code["class"]
        div.replace_with(pre.extract())
        count += 1
    for pre in soup.find_all("pre"):
        pre.attrs.pop("class", None)
    return count


def _section_rules(soup, all_tight: bool = False) -> int:
    heads = soup.find_all("h2")
    for i, head in enumerate(heads):
        text = head.get_text().strip()
        rule = soup.new_tag("div")
        # The id lets the layout stage push an orphaned rule+heading pair onto
        # the next page (render._low_headings).
        rule["id"] = f"sr{i + 1}"
        if i == 0:
            rule["class"] = "secrule first"
        elif all_tight or text.startswith(TIGHT_PREFIXES):
            rule["class"] = "secrule tight"
        else:
            rule["class"] = "secrule"
        head.insert_before(rule)
    return len(heads)


def _label_of(no: int) -> str:
    """章名标签：普通章是「第 N 章」，预备章之类用 label 字段。"""
    try:
        ch = config.chapter_by_no(int(no))
    except (KeyError, TypeError, ValueError):
        return f"第 {no} 章"
    return ch.get("label") or f"第 {no} 章"


def check_images(soup, base_dir: str) -> list[str]:
    """Every referenced figure must exist before the long build starts."""
    missing = []
    for img in soup.find_all("img"):
        src = img.get("src") or ""
        if not src or src.startswith(("http://", "https://", "data:")):
            continue
        if resolve_asset(src, base_dir) is None:
            missing.append(src)
    return missing


def resolve_asset(src: str, base_dir: str) -> str | None:
    """Resolve a figure path written relative to content/ or to the project root."""
    src = src.split("?")[0]
    candidates = [src] if os.path.isabs(src) else [
        os.path.join(base_dir, src),
        os.path.join(config.BUILD_DIR, src),
        os.path.normpath(os.path.join(base_dir, "..", src)),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


# ------------------------------------------------------------------ convert
def build(index: int, quiet: bool = False) -> dict:
    ch = config.chapter_by_index(index)
    slug = ch["slug"]
    md_path = config.chapter_md(slug)
    if not os.path.exists(md_path):
        raise SystemExit(f"missing chapter source: {md_path}")

    meta, body_md = read_front_matter(md_path)
    title = meta.get("title") or ch["title"]
    no = meta.get("no") or str(ch["no"])

    for m in IMG_RE.finditer(body_md):
        if resolve_asset(m.group(1), config.CONTENT_DIR) is None:
            raise SystemExit(f"{slug}: figure not found: {m.group(1)}")

    work_md = os.path.join(config.cache_dir(slug), "_pandoc_input.md")
    os.makedirs(config.cache_dir(slug), exist_ok=True)
    with open(work_md, "w", encoding="utf-8") as fh:
        fh.write(expand_div_shorthand(smart_quotes(body_md)))

    raw_html = run_pandoc(work_md)
    soup = BeautifulSoup(raw_html, "lxml")

    _unwrap_math_spans(soup)
    n_display = _promote_display_blocks(soup)
    n_mixed = _fix_mixed_display(soup)
    n_figs = _figures(soup)
    n_caps = _table_captions(soup)
    n_boxes = _boxes(soup)
    _code_blocks(soup)
    n_secs = _section_rules(soup, all_tight=(slug == "ch00"))

    missing = check_images(soup, config.CONTENT_DIR)
    if missing:
        raise SystemExit(f"{slug}: unresolved figures: {', '.join(missing[:5])}")

    h1 = soup.new_tag("h1")
    h1.string = f"{_label_of(no)}　{title}"
    art = soup.new_tag("article")
    art["class"] = "md-content__inner"
    art.append(h1)
    for child in list(soup.body.children if soup.body else soup.children):
        art.append(child.extract())

    html = ("<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>"
            + str(art) + "</body></html>")
    out = config.page_html(slug)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)

    stats = {"slug": slug, "title": title, "display_blocks": n_display,
             "figures": n_figs, "table_captions": n_caps, "boxes": n_boxes,
             "sections": n_secs, "html_bytes": len(html)}
    if not quiet:
        print(f"  {slug}: {n_secs} sections, {n_figs} figures, {n_boxes} boxes, "
              f"{len(html)/1024:.0f} KB html")
    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, help="1-based chapter index")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    if args.only:
        build(args.only - 1)
        return 0
    if not args.all:
        ap.error("choose --only N or --all")
    for i in range(len(config.CHAPTERS)):
        build(i)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

