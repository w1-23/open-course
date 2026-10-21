"""Collect every LaTeX fragment of one chapter and render it with MathJax 3.

MathJax runs under node (mathjax-full is vendored under ``vendor/mathjax``);
the result is a per-chapter cache of ``{normalised TeX key: svg markup}`` that
the layout stage consumes.  Keys are built by ``mathutil.cache_key`` so the
producer and the consumer can never disagree.
"""

import json
import os
import subprocess
import sys
import shutil

import config
import mathutil


def extract_article(page_html: str) -> str:
    """Slice out the article body so chrome is never scanned for math."""
    marker = "md-content__inner"
    i = page_html.find(marker)
    if i < 0:
        return page_html
    start = page_html.rfind("<", 0, i)
    end = page_html.find("</article>", start)
    if end < 0:
        end = len(page_html)
    return page_html[start:end]


def collect_keys(page_html: str) -> list[dict]:
    """Unique delimited fragments in document order, display flag included."""
    body = extract_article(page_html)
    seen: dict[str, dict] = {}
    for raw, display in mathutil.iter_fragments(body):
        tex, eqno = mathutil.split_eqno(mathutil.strip_delims(raw))
        # A \tag marks a numbered display equation even when pandoc decided the
        # fragment was inline (a \[ ... \] block glued to the preceding line).
        # Rendering it in display style keeps the layout stage honest: it
        # promotes such markers back to displays and looks the key up.
        if eqno and not display:
            display = True
        key = mathutil.cache_key(raw, display)
        if key in seen:
            continue
        seen[key] = {"key": key, "src": tex, "display": display}
    return list(seen.values())


def render(items: list[dict], work: str) -> dict:
    """Run node once over the whole batch and return the payload."""
    os.makedirs(work, exist_ok=True)
    tmp_in = os.path.join(work, "_math_in.json")
    tmp_out = os.path.join(work, "_math_out.json")
    with open(tmp_in, "w", encoding="utf-8") as fh:
        json.dump({"items": items}, fh, ensure_ascii=False)

    node = os.environ.get("DSH_NODE") or _find_node()
    script = os.path.join(config.BUILD_DIR, "mathjax_render.js")
    proc = subprocess.run([node, script, tmp_in, tmp_out],
                          capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        print(proc.stdout, proc.stderr, file=sys.stderr)
        raise RuntimeError("MathJax render failed")
    print("  " + (proc.stdout or "").strip())

    with open(tmp_out, encoding="utf-8") as fh:
        return json.load(fh)


def _find_node() -> str:
    node = os.environ.get("NODE") or os.environ.get("DSH_NODE") or shutil.which("node")
    if node:
        return node
    raise RuntimeError("Node.js not found; install Node.js or set the NODE environment variable")


def build_chapter(index: int, quiet: bool = False) -> dict:
    ch = config.chapter_by_index(index)
    slug = ch["slug"]
    html_path = config.page_html(slug)
    if not os.path.exists(html_path):
        raise SystemExit(f"{slug}: converted HTML missing; run md2html.py first")
    with open(html_path, encoding="utf-8") as fh:
        page = fh.read()

    items = collect_keys(page)
    if not quiet:
        print(f"  {slug}: {len(items)} unique formulas")
    if items:
        payload = render(items, config.cache_dir(slug))
    else:
        payload = {"ok": 0, "total": 0, "results": [], "failures": []}

    out = config.math_json(slug)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({r["key"]: r["svg"] for r in payload["results"] if r.get("ok")},
                  fh, ensure_ascii=False)
    if payload.get("failures"):
        for f in payload["failures"][:10]:
            print(f"  FAIL {f['key'][:70]!r}: {f['error'][:90]}", file=sys.stderr)
        # A MathJax parse error renders as a solid black bar in the final PDF,
        # so a failure here must stop the build instead of shipping silently.
        raise SystemExit(f"{slug}: {len(payload['failures'])} formula(s) failed to render")
    if not quiet:
        print(f"  {slug}: cached {payload.get('ok', 0)}/{payload.get('total', 0)} formulas")
    return {"slug": slug, "formulas": payload.get("total", 0),
            "rendered": payload.get("ok", 0), "failures": len(payload.get("failures") or [])}


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, help="1-based chapter index")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    if args.only:
        build_chapter(args.only - 1)
        return 0
    if not args.all:
        ap.error("choose --only N or --all")
    bad = 0
    for i in range(len(config.CHAPTERS)):
        try:
            build_chapter(i)
        except SystemExit as exc:
            print(f"  [error] {exc}", file=sys.stderr)
            bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
