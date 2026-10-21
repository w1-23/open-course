"""Build entry point: one chapter, every chapter, or the bound volume.

    python main.py --only 1        # build chapter 1 (md -> html -> math -> pdf)
    python main.py --all           # every chapter, then the combined book
    python main.py --merge         # rebuild only the combined book

Per chapter the stages run in a fixed order:

    content/chNN.md --md2html--> cache/chNN/page.html
                    --mathjax--> cache/chNN/math.json
                    --render --> output/NN_<title>.pdf

Each chapter owns ``cache/<slug>/`` so several chapters can be built in
parallel by different authors without touching each other's state.
"""

import argparse
import json
import os
import sys
import time

import fitz

import config
import frontmatter
import mathjax
import md2html
import render


def load_math(slug: str) -> dict[str, str]:
    path = config.math_json(slug)
    if not os.path.exists(path):
        raise SystemExit(f"math cache missing: {path}\nrun mathjax.py --only N first")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def build_chapter(index: int, keep_temp: bool = False, verbose: bool = True) -> dict:
    ch = config.chapter_by_index(index)
    slug = ch["slug"]
    t0 = time.time()
    md2html.build(index, quiet=not verbose)
    mathjax.build_chapter(index, quiet=not verbose)
    cache = load_math(slug)
    info = render.render_chapter(index, cache, config.OUTPUT_DIR, keep_temp)
    info["seconds"] = round(time.time() - t0, 1)
    info["budget"] = list(ch.get("budget") or (0, 10 ** 6))
    if verbose:
        print(f"  {info['file']}: {info['pages']}p, {info['images']} figures, "
              f"{info['formula_overlays']} formulas ({info['eqnos']} numbered), "
              f"{info['size_bytes'] / 1048576:.2f} MB, {info['seconds']}s")
        wide = info.get("wide_inline") or []
        if wide:
            print(f"  ! {len(wide)} 个行内公式过宽（>220pt，建议改为独占一行的 \\[...\\]）：")
            for w, tex in wide[:4]:
                print(f"      {w:5.1f}pt  {tex}")
        if info.get("narrowed_eq"):
            listed = "、".join(f"({no}) {w:.0f}pt"
                              for no, w in (info.get("narrowed") or [])[:8])
            print(f"  ! {info['narrowed_eq']} 个编号公式过宽（>340pt）已缩到 340pt："
                  f"{listed}；建议改写为多行 aligned 以免字号变小")
        tight = info.get("eqno_tight") or []
        if tight:
            print(f"  !! {len(tight)} 个编号公式仍压到编号：")
            for item in tight[:4]:
                print(f"      ({item['eqno']}) 第 {item['page']} 页 宽 {item['width']}pt")
    return info


def cmd_all(keep_temp: bool) -> int:
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    results = []
    for i in range(len(config.CHAPTERS)):
        ch = config.chapter_by_index(i)
        print(f"[{i + 1}/{len(config.CHAPTERS)}] {ch['slug']} {ch['title']}")
        try:
            results.append(build_chapter(i, keep_temp))
        except SystemExit as exc:
            print(f"  [error] {exc}", file=sys.stderr)
            raise
    for r in results:
        lo, hi = r.get("budget") or (0, 10 ** 6)
        if not lo <= r["pages"] <= hi:
            print(f"  ! 第 {r['no']} 章 {r['pages']} 页，超出预算 {lo}–{hi}", file=sys.stderr)
    print("\nbinding...")
    merged = frontmatter.assemble(results)
    print(f"  {merged['file']}: {merged['pages']}p, "
          f"{merged['bookmarks']} bookmarks, {merged['size_bytes'] / 1048576:.1f} MB")

    totals = {
        "chapters": len(results),
        "pages": sum(r["pages"] for r in results),
        "figures": sum(r["images"] for r in results),
        "formulas": sum(r["formulas"] for r in results),
        "eqnos": sum(r["eqnos"] for r in results),
        "math_failed": sum(r["math_failed"] for r in results),
        "bytes": sum(r["size_bytes"] for r in results) + merged["size_bytes"],
    }
    report = {
        "book": f"{config.BOOK_TITLE} — {config.BOOK_SUBTITLE}",
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "output_dir": config.OUTPUT_DIR,
        "chapters": [{k: v for k, v in r.items() if k != "toc"} for r in results],
        "combined": merged,
        "totals": totals,
    }
    with open(config.REPORT_PATH, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    print(f"\ndone: {totals['chapters']} chapters, {totals['pages']} pages, "
          f"{totals['figures']} figures, {totals['formulas']} formulas, "
          f"{totals['eqnos']} numbered equations, "
          f"{totals['bytes'] / 1048576:.1f} MB total")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, help="1-based chapter index")
    ap.add_argument("--all", action="store_true", help="build every chapter and bind")
    ap.add_argument("--merge", action="store_true", help="only rebuild the bound volume")
    ap.add_argument("--keep-temp", action="store_true")
    ap.add_argument("--preview", action="store_true",
                    help="bind even when chapters are missing (proof-reading only)")
    args = ap.parse_args()

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    if args.only is not None:
        nos = [c["no"] for c in config.CHAPTERS]
        if args.only not in nos:
            ap.error("--only must be one of " + ", ".join(str(n) for n in nos))
        build_chapter(nos.index(args.only), args.keep_temp)
        return 0

    if args.merge:
        results = []
        for i in range(len(config.CHAPTERS)):
            ch = config.chapter_by_index(i)
            path = config.out_pdf(ch["stem"])
            if not os.path.exists(path):
                # Binding a half-finished book is useful while authors are still
                # writing: the front matter and the table of contents can be
                # proof-read before the last chapter exists.
                print(f"  [skip] {ch['stem']}: not built yet", file=sys.stderr)
                continue
            doc = fitz.open(path)
            results.append({"file": os.path.basename(path), "no": ch["no"],
                            "title": ch["title"], "pages": doc.page_count,
                            "toc": doc.get_toc()})
            doc.close()
        merged = frontmatter.assemble(results, allow_missing=args.preview)
        if merged["missing"]:
            print(f"  [preview] 缺章 {merged['missing']}：合订本仅供校对，不得作为交付版",
                  file=sys.stderr)
        print(f"merged: {merged['file']} {merged['pages']}p "
              f"{merged['bookmarks']} bookmarks {merged['size_bytes'] / 1048576:.1f} MB")
        return 0

    if not args.all:
        ap.error("choose --only N, --all, or --merge")

    return cmd_all(args.keep_temp)


if __name__ == "__main__":
    raise SystemExit(main())
