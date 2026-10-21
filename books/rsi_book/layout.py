"""Page geometry and the CSS used for the Cornell three-zone layout.

Layout (A4, points) — the writing column is on the RIGHT:

    y=40   ┌───────────────────────────────────────────────┐
           │ body column (399pt)      │ writing column     │
    y=694  │                          │ (114pt, blank)     │
    y=706  ├──────────────────────────┴────────────────────┤
           │ SUMMARY / 总结   (blank writing band)         │
    y=806  └───────────────────────────────────────────────┘
"""

import fitz

import config

BODY_RECT = fitz.Rect(config.BODY_X0, config.BODY_Y0, config.BODY_X1, config.BODY_Y1)
PAGE_RECT = fitz.paper_rect("a4")


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

p {{ margin: 0 0 6pt 0; text-align: left; text-indent: 2em; }}
ul, ol {{ margin: 0 0 6pt 0; padding-left: 18pt; }}
li {{ margin: 0 0 2.5pt 0; text-align: left; text-indent: 0; }}
li p {{ text-indent: 0; }}

h1 {{ font-family: hei; font-size: 16pt; line-height: 1.3;
      margin: 0 0 16pt 0; text-align: center; text-indent: 0;
      break-after: avoid; }}
h2 {{ font-family: hei; font-size: 14pt; line-height: 1.35;
      margin: 0 0 10pt 0; text-indent: 0; break-after: avoid; }}
h3 {{ font-family: hei; font-size: 12.5pt; line-height: 1.4;
      margin: 14pt 0 6pt 0; text-indent: 0; break-after: avoid; }}
h4 {{ font-family: hei; font-size: 12pt; line-height: 1.4;
      margin: 10pt 0 4pt 0; text-indent: 0; break-after: avoid; }}

/* Section headings begin a fresh page without divider rules or a blank band. */
h2.section-start {{ break-before: page; page-break-before: always; }}
h2.section-start-first {{ break-before: auto; page-break-before: auto; }}

strong, b {{ font-family: hei; }}
em, i {{ font-style: italic; }}

a {{ color: #1a4f8a; text-decoration: none; }}

code {{ font-family: mono; font-size: 9.4pt; background-color: #f2f4f7;
        padding: 0 1pt; }}
/* No background-color on block boxes: MuPDF Story re-paints an interrupted
   block's background as a 10pt sliver in the top margin of the next page.
   Borders and edges are painted correctly, so all block decoration here is
   done with borders only. */
pre {{ font-family: mono; font-size: 8.6pt; line-height: 1.4; text-indent: 0;
       border-left: 2pt solid #b8bfc8;
       border-top: 0.5pt solid #dadde2;
       border-bottom: 0.5pt solid #dadde2;
       border-right: 0.5pt solid #dadde2;
       padding: 5pt 6pt; margin: 6pt 0 8pt 0;
       white-space: pre-wrap; break-inside: avoid; }}
pre code {{ background: none; padding: 0; font-size: 8.6pt; }}

table {{ border-collapse: collapse; width: 100%; table-layout: fixed;
         font-size: 9.5pt; margin: 5pt 0 7pt 0; break-inside: auto;
         border-top: 0.9pt solid #222222; border-bottom: 0.9pt solid #222222; }}
th, td {{ border: 0; padding: 2pt 3.5pt;
          vertical-align: middle; word-wrap: break-word; overflow-wrap: anywhere;
          line-height: 1.3; text-indent: 0; text-align: left; }}
tr {{ break-inside: avoid; page-break-inside: avoid; }}
tr:first-child th, tr:first-child td {{ border-bottom: 0.6pt solid #222222; }}
th {{ font-family: hei; font-size: 9.5pt; text-align: center; }}
/* A table with four or more columns of prose cannot fit the body column at the
   body size; prepare._clamp_table_markers tags it "dense". */
table.dense {{ font-size: 9pt; }}
table.dense th {{ font-size: 9pt; }}
table.dense th, table.dense td {{ padding: 1.8pt 3pt; }}

img {{ max-width: 100%; }}

.figwrap {{ break-inside: avoid; page-break-inside: avoid; margin: 9pt 0 10pt 0; }}
.figure {{ text-align: center; margin: 0; break-inside: avoid; text-indent: 0; }}
.figure img {{ max-width: 100%; }}
.caption {{ font-size: 9pt; color: #444444; margin: 4pt 0 0 0;
            text-align: center; line-height: 1.45; text-indent: 0; }}

blockquote {{ margin: 6pt 0 8pt 0; padding: 3pt 0 3pt 8pt;
              border-left: 2pt solid #d0d0d0; color: #333333; }}

.admonition {{ border-left: 3pt solid #d9a400;
               border-top: 0.5pt solid #f0e2b8;
               border-bottom: 0.5pt solid #f0e2b8;
               border-right: 0.5pt solid #f0e2b8;
               padding: 5pt 7pt; margin: 7pt 0 9pt 0; break-inside: avoid; }}
.admonition-title {{ font-family: hei; font-size: 11pt; margin: 0 0 4pt 0;
                     color: #8a6d00; text-indent: 0; }}
.admonition p {{ margin: 0 0 4pt 0; text-indent: 0; }}
.admonition p:last-child {{ margin-bottom: 0; }}

hr {{ border: none; border-top: 0.5pt solid #dddddd; margin: 10pt 0; }}

.srcnote {{ font-size: 9pt; color: #555555; border-left: 2pt solid #cccccc;
            padding: 2pt 0 2pt 8pt; margin: 6pt 0 9pt 0; text-indent: 0;
            break-inside: avoid; }}
.srcnote code {{ font-family: mono; font-size: 8.5pt; }}
.srcid {{ font-family: mono; font-size: 8pt; color: #777777; }}

/* syntax highlighting (GitHub-like) */
.k, .kd, .kn, .kr, .kt {{ color: #cf222e; }}
.o, .ow {{ color: #cf222e; }}
.s, .s1, .s2, .sb, .sc, .sd, .se, .sh, .si, .sr, .ss, .sx {{ color: #0a3069; }}
.c, .c1, .cm, .cs, .ch {{ color: #6e7781; font-style: italic; }}
.nb, .bp {{ color: #0550ae; }}
.m, .mi, .mf, .mh, .mo {{ color: #0550ae; }}
.nf, .fm {{ color: #8250df; }}
.nc, .nn {{ color: #8250df; font-family: hei; }}
.nd {{ color: #8250df; }}
.na {{ color: #0550ae; }}
.nt {{ color: #116329; }}
.err {{ color: #cf222e; }}
"""
