"""Page geometry and the CSS used for the Cornell three-zone thesis layout.

Layout (A4, points) — the writing column is on the RIGHT:

    y=40   ┌───────────────────────────────────────────────┐
           │ body column (399pt)      │ cue column         │
    y=694  │                          │ (114pt, blank)     │
    y=706  ├──────────────────────────┴────────────────────┤
           │ SUMMARY / 总结   (blank writing band)         │
    y=806  └───────────────────────────────────────────────┘

Typography follows the Chinese thesis convention: 小四 (12pt) SimSun body,
Times New Roman for Latin letters and digits, 1.5 line spacing, two-character
first-line indent, justified paragraphs, headings in SimHei.
"""

import fitz

import config

BODY_RECT = fitz.Rect(config.BODY_X0, config.BODY_Y0, config.BODY_X1, config.BODY_Y1)
PAGE_RECT = fitz.paper_rect("a4")

_ALIGN = "justify" if config.JUSTIFY else "left"


def rectfn(rect_num: int, filled: tuple | None):
    """Story callback: media box, body rectangle, transformation matrix."""
    return PAGE_RECT, BODY_RECT, None


CSS = f"""
@font-face {{ font-family: song;   src: url(song.ttf); }}
@font-face {{ font-family: hei;    src: url(hei.ttf); }}
@font-face {{ font-family: latin;  src: url(latin.ttf); }}
@font-face {{ font-family: latinb; src: url(latinb.ttf); }}
@font-face {{ font-family: mono;   src: url(mono.ttf); }}

* {{ box-sizing: border-box; }}

/* 毕业论文正文：小四宋体 + Times New Roman，1.5 倍行距，首行缩进两字。
   Chinese inherits the base face (SimSun); prepare._split_fonts wraps every
   Latin/digit run in a span that switches to Times New Roman. */
body {{
  font-family: song;
  font-size: {config.BODY_FONT_SIZE}pt;
  line-height: {config.BODY_LINE_HEIGHT};
  color: #111111;
  margin: 0;
}}

.latin  {{ font-family: latin; }}
.latinb {{ font-family: latinb; }}

p {{ margin: 0 0 6pt 0; text-align: {_ALIGN}; text-indent: 2em; }}
ul, ol {{ margin: 0 0 6pt 0; padding-left: 20pt; }}
li {{ margin: 0 0 2.5pt 0; text-align: {_ALIGN}; text-indent: 0; }}
li p {{ text-indent: 0; }}

h1 {{ font-family: hei; font-size: 16pt; line-height: 1.35;
      margin: 0 0 6pt 0; text-align: center; text-indent: 0;
      break-after: avoid; }}
h2 {{ font-family: hei; font-size: 14pt; line-height: 1.35;
      margin: 6pt 0 10pt 0; text-indent: 0; break-after: avoid; }}
h3 {{ font-family: hei; font-size: 12.5pt; line-height: 1.4;
      margin: 13pt 0 5pt 0; text-indent: 0; break-after: avoid; }}
h4 {{ font-family: hei; font-size: 12pt; line-height: 1.4;
      margin: 10pt 0 4pt 0; text-indent: 0; break-after: avoid; }}

/* Section opener: a naked spacer that starts a fresh page, so every top-level
   section of a chapter begins on its own page.  It carries NO rules: the
   chapter's own typography is expected to separate sections, and a line above
   every section opener read as page furniture.  The element must stay -- it is
   the anchor for both the forced page break and render.py's orphan-heading
   repair, so it is invisible but structurally load-bearing. */
.secrule {{ height: 4pt; text-indent: 0; margin: 0 0 8pt 0;
            page-break-before: always; }}
.secrule.first {{ page-break-before: auto; }}
.secrule.tight {{ page-break-before: auto; margin-top: 16pt; }}

strong, b {{ font-family: hei; }}
em, i {{ font-style: italic; }}

a {{ color: #1a4f8a; text-decoration: none; }}

code {{ font-family: mono; font-size: 9.4pt; background-color: #f2f4f7;
        padding: 0 1pt; }}
/* No background-color on block boxes: MuPDF Story re-paints an interrupted
   block's background as a 10pt sliver in the top margin of the next page.
   Borders and edges are painted correctly, so all block decoration here is
   done with borders only. */
pre {{ font-family: mono; font-size: 8.6pt; line-height: 1.45; text-indent: 0;
       border-left: 2pt solid #b8bfc8;
       border-top: 0.5pt solid #dadde2;
       border-bottom: 0.5pt solid #dadde2;
       border-right: 0.5pt solid #dadde2;
       padding: 5pt 6pt; margin: 6pt 0 8pt 0;
       white-space: pre-wrap; break-inside: avoid; }}
pre code {{ background: none; padding: 0; font-size: 8.6pt; }}

/* 三线表：顶线与底线较粗，表头下一条细线，中间不画竖线也不画行线。
   Story honours per-cell borders, so the rules are expressed on the cells
   rather than on the table box. */
table {{ border-collapse: collapse; width: 100%; table-layout: auto;
         font-size: 10pt; margin: 2pt 0 10pt 0; break-inside: avoid; }}
th, td {{ padding: 3pt 5pt; vertical-align: top; word-wrap: break-word;
          text-indent: 0; border: none; }}
thead th {{ font-family: hei; font-size: 10pt; text-align: left;
            border-top: 1.2pt solid #23272e;
            border-bottom: 0.7pt solid #23272e; padding-top: 4pt; }}
tbody tr:last-child td {{ border-bottom: 1.2pt solid #23272e; }}
table p {{ text-indent: 0; margin: 0; }}
.tablewrap {{ break-inside: avoid; margin: 0; }}
/* A lead-in paragraph and the display formula it introduces ("…由下式给出：")
   are wrapped together by prepare._pair_displays so a page break cannot leave
   the colon dangling at the foot of a page. */
.pair {{ break-inside: avoid; margin: 0; }}
/* A table with four or more columns of prose cannot fit the body column at the
   body size; prepare._clamp_table_markers tags it "dense".  Dense tables also
   get tighter side padding: without it a five-column table leaves ~11pt per
   cell and Chinese text wraps to one glyph per line. */
table.dense {{ font-size: 8.8pt; }}
table.dense thead th {{ font-size: 8.8pt; }}
table.dense th, table.dense td {{ padding: 2pt 2.5pt; }}

.tabcap {{ font-size: 9pt; color: #23272e; margin: 9pt 0 3pt 0;
           text-align: center; text-indent: 0; break-after: avoid; }}

img {{ max-width: 100%; }}

.figwrap {{ break-inside: avoid; page-break-inside: avoid; margin: 9pt 0 10pt 0; }}
.figure {{ text-align: center; margin: 0; break-inside: avoid; text-indent: 0; }}
.figure img {{ max-width: 100%; }}
.caption {{ font-size: 9pt; color: #333333; margin: 4pt 0 0 0;
            text-align: center; line-height: 1.45; text-indent: 0;
            break-inside: avoid; }}

blockquote {{ margin: 6pt 0 8pt 0; padding: 3pt 0 3pt 8pt;
              border-left: 2pt solid #d0d0d0; color: #333333; }}
blockquote p {{ text-indent: 0; }}

/* 定义 / 定理 / 注 / 算法 等提示块：只用描边，不用底色填充。 */
.box {{ border-left: 2.6pt solid #b9c0c9;
        border-top: 0.4pt solid #e3e6ea;
        border-bottom: 0.4pt solid #e3e6ea;
        border-right: 0.4pt solid #e3e6ea;
        padding: 5pt 8pt; margin: 8pt 0 9pt 0; break-inside: avoid; }}
.box-title {{ font-family: hei; font-size: 10.5pt; margin: 0 0 4pt 0;
              text-indent: 0; color: #23272e; break-after: avoid; }}
.box p {{ text-indent: 0; margin: 0 0 4pt 0; text-align: {_ALIGN}; }}
.box p:last-child {{ margin-bottom: 0; }}
.box pre {{ margin: 2pt 0 0 0; }}

.def     {{ border-left-color: #7d9b6a; }}
.def     .box-title {{ color: #4d6b3f; }}
.thm     {{ border-left-color: #7d93b2; }}
.thm     .box-title {{ color: #3f5773; }}
.prop    {{ border-left-color: #7d93b2; }}
.prop    .box-title {{ color: #3f5773; }}
.example {{ border-left-color: #b9c0c9; }}
.note    {{ border-left-color: #b9c0c9; }}
.warn    {{ border-left-color: #c9a227; }}
.warn    .box-title {{ color: #8a6d00; }}

/* 算法框：上下粗线夹住伪代码，中间不加竖线，接近纸面论文的算法环境。 */
.algorithm {{ border: none;
              border-top: 1.1pt solid #23272e;
              border-bottom: 1.1pt solid #23272e;
              padding: 4pt 1pt 4pt 0; margin: 9pt 0 10pt 0;
              break-inside: avoid; }}
.algorithm .box-title {{ font-size: 10pt; margin: 0 0 3pt 0; }}
/* 伪代码不是源码：它含中文，不能落进 Consolas（无 CJK 字形会变成方框）。
   正文宋体承载中文，Latin 由 .latin 段切换到 Times New Roman。 */
.algorithm pre, .box pre {{ font-family: song; font-size: 10.2pt; line-height: 1.55;
                            border: none; padding: 1pt 0; margin: 2pt 0; }}

hr {{ border: none; border-top: 0.5pt solid #dddddd; margin: 10pt 0; }}

/* syntax highlighting (pandoc skylighting classes, GitHub-like palette) */
.kw, .dt, .cf, .cn, .bu {{ color: #8250df; }}
.at, .do, .an {{ color: #8250df; font-style: italic; }}
.st, .ch, .ss, .vs {{ color: #0a3069; }}
.co, .cm {{ color: #6e7781; font-style: italic; }}
.dv, .bn, .fl, .m, .mi, .mf {{ color: #0550ae; }}
.fu, .nf, .fm {{ color: #6639ba; }}
.op, .ot, .pp, .ex {{ color: #24292f; }}
.im, .va, .al, .sc, .re, .cv, .in, .wa, .er {{ color: #cf222e; }}
"""
