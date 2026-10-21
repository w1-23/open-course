"""把一章 Markdown 导出为可编辑的 Word 文档（.docx）。

设计取舍（与 PDF 版不同）：
* 公式走 pandoc 的 OMML 转换（`tex_math_single_backslash` 扩展是必需的，否则
  `\\(..\\)` 会被当成转义括号，公式整段变成普通文本）；
* 图片必须是位图：Word 不能直接嵌 SVG，而本机没有 cairosvg/LibreOffice，
  所以用 PyMuPDF 把 SVG 先转 PDF 再栅格化成 300 dpi 的 PNG；
* `\\tag{3.7}` 这种公式编号 OMML 里没有对应结构，导出时从公式体内摘掉，
  在公式下方另起一行右对齐写「(3.7)」，保证编号在 Word 里仍可编辑、可搜索；
* 版面按“论文样式 + 康奈尔留白”设置：A4，左 3.0 cm、右 4.2 cm（右侧留白供手写），
  上 2.4 cm、下 2.6 cm，正文宋体小四、行距 1.5、首行缩进两字。
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile

import fitz
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

import config  # noqa: E402

PANDOC = os.environ.get("PANDOC") or shutil.which("pandoc") or "pandoc"
OUT_DIR = os.path.join(ROOT, "output", "docx")
IMG_CACHE = os.path.join(ROOT, "cache", "docximg")
REFERENCE = os.path.join(ROOT, "cache", "reference.docx")

BODY_EA = "宋体"
BODY_LATIN = "Times New Roman"
HEAD_EA = "黑体"


# --------------------------------------------------------------------------- #
# 参考样式文档
# --------------------------------------------------------------------------- #
def _set_east_asia(style_or_run, ea: str, latin: str) -> None:
    el = style_or_run.element if hasattr(style_or_run, "element") else style_or_run._element
    rpr = el.find(qn("w:rPr"))
    if rpr is None:
        rpr = el.makeelement(qn("w:rPr"), {})
        el.insert(0, rpr)
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(fonts)
    fonts.set(qn("w:ascii"), latin)
    fonts.set(qn("w:hAnsi"), latin)
    fonts.set(qn("w:eastAsia"), ea)


def build_reference(path: str) -> str:
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin, sec.right_margin = Cm(3.0), Cm(4.2)
    sec.top_margin, sec.bottom_margin = Cm(2.4), Cm(2.6)

    normal = doc.styles["Normal"]
    normal.font.size = Pt(12)
    normal.font.name = BODY_LATIN
    _set_east_asia(normal, BODY_EA, BODY_LATIN)
    pf = normal.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    pf.space_before = Pt(0)
    pf.space_after = Pt(6)
    pf.first_line_indent = Pt(24)          # 两字缩进
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    sizes = {"Heading 1": 18, "Heading 2": 15, "Heading 3": 13, "Heading 4": 12}
    for name, size in sizes.items():
        st = doc.styles[name]
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.name = BODY_LATIN
        st.font.color.rgb = RGBColor(0, 0, 0)
        _set_east_asia(st, HEAD_EA, BODY_LATIN)
        st.paragraph_format.first_line_indent = Pt(0)
        st.paragraph_format.space_before = Pt(12 if name != "Heading 1" else 0)
        st.paragraph_format.space_after = Pt(8 if name != "Heading 1" else 14)
        st.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        if name == "Heading 1":
            st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER

    cap = doc.styles["Caption"]
    cap.font.size = Pt(9)
    cap.font.bold = False
    cap.font.name = BODY_LATIN
    _set_east_asia(cap, BODY_EA, BODY_LATIN)
    cap.paragraph_format.first_line_indent = Pt(0)
    cap.paragraph_format.space_after = Pt(8)

    for name in ("Source Code", "Verbatim Char"):
        try:
            st = doc.styles[name]
        except KeyError:
            continue
        st.font.size = Pt(9)
        st.font.name = "Consolas"
        _set_east_asia(st, BODY_EA, "Consolas")

    doc.save(path)
    return path


# --------------------------------------------------------------------------- #
# 图片：SVG -> 300dpi PNG
# --------------------------------------------------------------------------- #
def svg_to_png(svg_path: str, png_path: str, scale: float = 4.0) -> tuple[int, int]:
    data = fitz.open(svg_path).convert_to_pdf()
    doc = fitz.open("pdf", data)
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    pix.save(png_path)
    size = (pix.width, pix.height)
    doc.close()
    return size


def rewrite_images(md_text: str, slug: str) -> tuple[str, int]:
    """把 `](figures/out/x.svg)` 换成 300dpi PNG 的绝对路径，返回 (新文本, 张数)。"""
    os.makedirs(IMG_CACHE, exist_ok=True)
    count = 0
    dims: dict[str, tuple[int, int]] = {}

    def repl(m: re.Match) -> str:
        nonlocal count
        target = m.group(1)
        path = os.path.join(ROOT, target.replace("/", os.sep))
        if not os.path.exists(path):
            print(f"  ! 图片缺失：{target}", file=sys.stderr)
            return m.group(0)
        if path.lower().endswith(".svg"):
            png = os.path.join(IMG_CACHE, f"{slug}_{os.path.basename(path)[:-4]}.png")
            if not os.path.exists(png):
                svg_to_png(path, png)
            count += 1
            dims[png] = (0, 0)
            return f"]({png})"
        count += 1
        return f"]({path})"

    new = re.sub(r"\]\((figures/out/[^)]+)\)", repl, md_text)
    return new, count


# --------------------------------------------------------------------------- #
# 公式编号：从公式体里摘出 \tag，改成公式下方的右对齐编号
# --------------------------------------------------------------------------- #
TAG_RE = re.compile(r"\\tag\*?\s*\{([^{}]*)\}")
DISPLAY_RE = re.compile(r"\\\[[\s\S]*?\\\]")


def strip_tags(md_text: str) -> tuple[str, int]:
    out = []
    pos = 0
    count = 0
    for m in DISPLAY_RE.finditer(md_text):
        out.append(md_text[pos:m.start()])
        block = m.group(0)
        tags = TAG_RE.findall(block)
        if not tags:
            out.append(block)
            pos = m.end()
            continue
        count += 1
        label = tags[-1].strip()
        body = TAG_RE.sub("", block)
        out.append(body.rstrip() + "\n\n")
        # 编号单独一行、右对齐；用一个可识别的占位段落，导出后再设对齐，
        # 因为 pandoc 会丢掉内联 CSS。
        out.append(f"EQNO::{label}\n\n")
        pos = m.end()
    out.append(md_text[pos:])
    return "".join(out), count


BOX_OPEN_RE = re.compile(r"^:::\s*([A-Za-z]+)\s*(.*)$")
CLOSING_RE = re.compile(r"^:::\s*$")


def flatten_boxes(md_text: str) -> tuple[str, int]:
    """把 `::: kind 标题` 栅栏展开成"加粗标题段落 + 正文"。

    pandoc 的 docx 输出不认识我们的栅栏简写（`::: def 定义 3.1（…）` 会被当成
    类名），标题会整段消失；展开成普通段落才能保住"定义/定理/算法"这些标签。
    """
    lines = md_text.splitlines()
    out: list[str] = []
    count = 0
    for line in lines:
        m = BOX_OPEN_RE.match(line)
        if m and not CLOSING_RE.match(line):
            title = (m.group(2) or "").strip()
            if title:
                out.append(f"<p><strong>{title}</strong></p>")
                count += 1
            out.append("")
            continue
        if CLOSING_RE.match(line):
            out.append("")
            continue
        out.append(line)
    return "\n".join(out), count


# --------------------------------------------------------------------------- #
# 版式后处理
# --------------------------------------------------------------------------- #
def add_page_field(paragraph) -> None:
    run = paragraph.add_run()
    fld = run._r.makeelement(qn("w:fldSimple"), {qn("w:instr"): "PAGE"})
    run._r.append(fld)


def style_document(path: str, chapter_no: int, title: str) -> None:
    doc = Document(path)
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin, sec.right_margin = Cm(3.0), Cm(4.2)
    sec.top_margin, sec.bottom_margin = Cm(2.4), Cm(2.6)
    sec.header_distance = Cm(1.4)
    sec.footer_distance = Cm(1.5)

    # 章标题：pandoc 丢掉 front matter，正文开头没有 H1，这里补一行
    first = doc.paragraphs[0] if doc.paragraphs else None
    heading = doc.add_paragraph(style="Heading 1")
    heading.paragraph_format.first_line_indent = Pt(0)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = heading.add_run(f"第 {chapter_no} 章　{title}")
    run.font.size = Pt(18)
    run.font.bold = True
    _set_east_asia(run, HEAD_EA, BODY_LATIN)
    if first is not None:
        first._p.addprevious(heading._p)

    # 公式编号段落：EQNO::7.3 -> （7.3），右对齐、无缩进
    for para in doc.paragraphs:
        text = para.text.strip()
        if text.startswith("EQNO::"):
            label = text.split("EQNO::", 1)[1].strip()
            for r in list(para.runs):
                r._r.getparent().remove(r._r)
            para.add_run(f"（{label}）")
            para.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            para.paragraph_format.first_line_indent = Pt(0)
            para.paragraph_format.space_before = Pt(0)
            para.paragraph_format.space_after = Pt(8)
            for r in para.runs:
                r.font.size = Pt(10)
                _set_east_asia(r, BODY_EA, BODY_LATIN)

    header = sec.header.paragraphs[0]
    header.text = ""
    header.paragraph_format.first_line_indent = Pt(0)
    header.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = header.add_run(f"强化学习 · 第 {chapter_no} 章 · {title}")
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    run.font.name = BODY_LATIN
    _set_east_asia(run, BODY_EA, BODY_LATIN)

    footer = sec.footer.paragraphs[0]
    footer.text = ""
    footer.paragraph_format.first_line_indent = Pt(0)
    footer.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_page_field(footer)

    doc.save(path)


# --------------------------------------------------------------------------- #
def export(chapter: dict) -> dict:
    slug = chapter["slug"]
    md_path = os.path.join(ROOT, "content", f"{slug}.md")
    if not os.path.exists(md_path):
        raise SystemExit(f"缺少正文：{md_path}")
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(IMG_CACHE, exist_ok=True)

    with open(md_path, encoding="utf-8") as fh:
        raw = fh.read()

    body = raw
    if body.startswith("---"):
        end = body.find("\n---", 3)
        if end > 0:
            body = body[end + 4 :]

    img_text, n_img = rewrite_images(body, slug)
    box_text, n_box = flatten_boxes(img_text)
    tag_text, n_tag = strip_tags(box_text)

    tmp_md = os.path.join(IMG_CACHE, f"{slug}.md")
    with open(tmp_md, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(tag_text)

    out = os.path.join(OUT_DIR, f"{chapter['stem']}.docx")
    cmd = [
        PANDOC, tmp_md,
        "-f", "markdown+east_asian_line_breaks+tex_math_single_backslash",
        "-t", "docx",
        "--reference-doc", REFERENCE,
        "--resource-path", ROOT,
        "-o", out,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        print(proc.stderr[-1500:], file=sys.stderr)
        raise SystemExit(f"pandoc 失败：{chapter['stem']}")
    if proc.stderr.strip():
        print("  pandoc:", proc.stderr.strip()[:400])

    style_document(out, chapter["no"], chapter["title"])
    size = os.path.getsize(out)
    print(f"  {chapter['stem']}.docx: {size/1024:.0f} KB, 图 {n_img}，编号公式 {n_tag}")
    return {"no": chapter["no"], "file": out, "bytes": size,
            "images": n_img, "eqno": n_tag}


def main() -> int:
    args = sys.argv[1:]
    build_reference(REFERENCE)
    if args and args[0] in ("--only", "-o"):
        picks = [config.chapter_by_no(int(args[1]))]
    else:
        picks = list(config.CHAPTERS)
    results = []
    for ch in picks:
        print(f"[{ch['no']}] {ch['title']}")
        results.append(export(ch))
    total = sum(r["bytes"] for r in results)
    print(f"done: {len(results)} chapters, {total/1024/1024:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
