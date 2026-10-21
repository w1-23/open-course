"""Collect every LaTeX fragment from the cached pages and render it with MathJax 3.

MathJax runs under node (mathjax-full is vendored); the result is a cache of
{raw_source_key: svg_markup} that the layout stage consumes.
"""

import html as htmllib
import json
import os
import re
import subprocess
import sys
import shutil

import config

INLINE_RE = re.compile(r"\\\([\s\S]*?\\\)")
DISPLAY_RE = re.compile(r"\\\[[\s\S]*?\\\]")


def extract_article(page_html: str) -> str:
    """Slice out the article body so nav/sidebar math is never picked up."""
    marker = 'md-content__inner'
    i = page_html.find(marker)
    if i < 0:
        return page_html
    start = page_html.rfind("<", 0, i)
    end = page_html.find("</article>", start)
    if end < 0:
        end = len(page_html)
    return page_html[start:end]


def strip_delims(key: str) -> str:
    """MathJax takes bare TeX, so the \\( ... \\) / \\[ ... \\] wrappers are removed."""
    s = key
    if s.startswith("\\[") and s.endswith("\\]"):
        s = s[2:-2]
    elif s.startswith("\\(") and s.endswith("\\)"):
        s = s[2:-2]
    return s.strip()


def cache_key(src: str, display: bool) -> str:
    """Stable lookup key: unescaped TeX plus the display flag.

    Entities (`&lt;`) differ between the raw page and BeautifulSoup's
    re-serialisation, so the key is normalised rather than raw.
    """
    return ("D|" if display else "I|") + htmllib.unescape(src)


def collect_keys(pages: dict[str, str]) -> list[dict]:
    """Unique delimited fragments in document order, display flag included."""
    seen = {}
    for slug in pages:
        body = extract_article(pages[slug])
        for m in DISPLAY_RE.finditer(body):
            seen.setdefault(cache_key(m.group(0), True), (m.group(0), True))
        for m in INLINE_RE.finditer(body):
            seen.setdefault(cache_key(m.group(0), False), (m.group(0), False))
    items = []
    for key, (raw, display) in seen.items():
        items.append({"key": key, "src": strip_delims(htmllib.unescape(raw)), "display": display})
    return items


def render(items: list[dict]) -> dict:
    """Run node once over the whole batch and return {key: svg}."""
    tmp_in = os.path.join(config.CACHE_DIR, "_math_in.json")
    tmp_out = os.path.join(config.CACHE_DIR, "_math_out.json")
    os.makedirs(config.CACHE_DIR, exist_ok=True)
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
        payload = json.load(fh)
    return payload


def _find_node() -> str:
    node = os.environ.get("NODE") or os.environ.get("DSH_NODE") or shutil.which("node")
    if node:
        return node
    raise RuntimeError("Node.js not found; install Node.js or set the NODE environment variable")


def main() -> int:
    pages = {}
    for slug, _, _ in config.LECTURES:
        # Authored chapters live in author/; source/html/ only holds the staged
        # copy created during render, which does not exist when this stage runs.
        path = os.path.join(config.AUTHOR_DIR, f"{slug}.html")
        if not os.path.exists(path):
            path = os.path.join(config.PAGE_DIR, f"{slug}.html")
        if not os.path.exists(path):
            print(f"  [skip] missing page {slug}", file=sys.stderr)
            continue
        with open(path, encoding="utf-8") as fh:
            pages[slug] = fh.read()

    items = collect_keys(pages)
    print(f"unique formulas: {len(items)}")

    payload = render(items)
    with open(config.MATH_JSON, "w", encoding="utf-8") as fh:
        json.dump({r["key"]: r["svg"] for r in payload["results"] if r.get("ok")},
                  fh, ensure_ascii=False)
    print(f"cached {payload['ok']}/{payload['total']} formulas -> {config.MATH_JSON}")
    if payload["failures"]:
        for f in payload["failures"][:10]:
            print(f"  FAIL {f['key'][:60]!r}: {f['error'][:90]}", file=sys.stderr)
        # A MathJax parse error renders as a solid black bar in the final PDF,
        # so a failure here must stop the build instead of shipping silently.
        print(f"  {len(payload['failures'])} formula(s) failed to render", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
