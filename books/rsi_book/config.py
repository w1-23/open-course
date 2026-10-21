"""Central configuration for the RSI (Recursive Self-Improvement) textbook build.

Adapted from the proven cs336_build pipeline: same Cornell geometry and MuPDF
formula-overlay machinery, new content model (authored Chinese chapters instead
of scraped lecture pages) and new source tree (arXiv HTML/PDF, course site,
awesome lists) under source/.
"""

import os

# ---------------------------------------------------------------- paths
BUILD_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.dirname(BUILD_DIR)

SOURCE_DIR = os.path.join(BUILD_DIR, "source")          # all downloaded material
AUTHOR_DIR = os.path.join(BUILD_DIR, "author")          # chapter .html sources
PAGE_DIR = os.path.join(SOURCE_DIR, "html")             # scraped/reference html + authored staging
REF_DIR = os.path.join(SOURCE_DIR, "reference")         # scraped reference text
SRC_IMG_DIR = os.path.join(SOURCE_DIR, "img")           # downloaded figures (arXiv etc.)
SRC_PDF_DIR = os.path.join(SOURCE_DIR, "pdf")           # paper PDFs kept for reference
DIAG_DIR = os.path.join(SOURCE_DIR, "diagrams")         # generated SVG diagrams (audit trail)

CACHE_DIR = os.path.join(BUILD_DIR, "cache")
IMG_DIR = os.path.join(CACHE_DIR, "imgs")               # per-chapter resolved image dir
MATH_JSON = os.path.join(CACHE_DIR, "math.json")
MATHJAX_DIR = os.path.join(BUILD_DIR, "vendor", "mathjax")

OUTPUT_DIR = os.path.join(BUILD_DIR, "output")
PDF_CHAPTER_DIR = os.path.join(OUTPUT_DIR, "pdf", "分章")
PDF_COMBINED_DIR = os.path.join(OUTPUT_DIR, "pdf", "合订本")
DOCX_CHAPTER_DIR = os.path.join(OUTPUT_DIR, "docx", "分章")
DOCX_COMBINED_DIR = os.path.join(OUTPUT_DIR, "docx", "合订本")
OUTPUT_NOTES_DIR = os.path.join(OUTPUT_DIR, "说明")
REPORT_PATH = os.path.join(OUTPUT_NOTES_DIR, "构建报告.json")

# ---------------------------------------------------------------- source sites
CS329A_URL = "https://cs329a.stanford.edu/"
ARXIV_ABS = "https://arxiv.org/abs/{aid}"
ARXIV_HTML = "https://arxiv.org/html/{aid}v{v}"
ARXIV_PDF = "https://arxiv.org/pdf/{aid}"
WENG_INDEX = "https://lilianweng.github.io/"
AWESOME_RSI_ZH = ("https://raw.githubusercontent.com/Picrew/awesome-rsi/main/"
                  "README_zh.md")
AWESOME_RSI_D2I_ZH = ("https://raw.githubusercontent.com/D2I-ai/"
                      "awesome-recursive-self-improving-agents/main/README.zh-CN.md")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
HTTP_TIMEOUT = 60
HTTP_RETRIES = 3
DOWNLOAD_WORKERS = 8

# ---------------------------------------------------------------- fonts
# Thesis type stack: Times New Roman for Latin letters and digits, SimSun for
# Chinese, SimHei for headings, Consolas for code.  MuPDF Story accepts only one
# family name per element, so the mixture is expressed with per-run spans
# (prepare._split_fonts).
FONT_CJK = r"C:\Windows\Fonts\simsun.ttc"          # 宋体
FONT_CJK_BOLD = r"C:\Windows\Fonts\simhei.ttf"     # 黑体
FONT_LATIN = r"C:\Windows\Fonts\times.ttf"         # Times New Roman
FONT_LATIN_BOLD = r"C:\Windows\Fonts\timesbd.ttf"  # Times New Roman Bold
FONT_MONO = r"C:\Windows\Fonts\consola.ttf"
FONT_BODY = FONT_CJK

# ---------------------------------------------------------------- page geometry (points)
PAGE_W, PAGE_H = 595.0, 842.0          # A4
MARGIN_LEFT = 34.0
MARGIN_RIGHT = 34.0

HEADER_Y = 40.0                         # running-header baseline reference
FOOTER_Y = 826.0                        # page-number baseline

CUE_X0 = 447.0                          # cue column left edge
CUE_X1 = MARGIN_LEFT + (PAGE_W - 2 * MARGIN_LEFT)   # cue column right edge (561)
RULE_X = 441.0                          # vertical Cornell rule
RULE_TOP = 40.0
RULE_BOTTOM = 806.0

BODY_X0 = MARGIN_LEFT                   # body text left edge (34)
BODY_X1 = 433.0                         # body text right edge
BODY_Y0 = 52.0                          # body text top, one line below running header
BODY_Y1 = 694.0                         # body text bottom (summary rule below)

SUMMARY_RULE_Y = 706.0
SUMMARY_X0 = MARGIN_LEFT
SUMMARY_X1 = 561.0

RULE_GREY = (0.72, 0.72, 0.72)
LABEL_GREY = (0.55, 0.55, 0.55)

# ---------------------------------------------------------------- typography
# 毕业论文正文规格：小四（12pt）宋体，1.5 倍行距，首行缩进两字符。
BODY_FONT_SIZE = 12.0
BODY_LINE_HEIGHT = 1.5
EX_PT = BODY_FONT_SIZE * 0.35
DISPLAY_SCALE = 4.2
DISPLAY_MAX_WIDTH = 392.0

# ---------------------------------------------------------------- chapters
# (slug, Chinese title, output file stem) -- authored content, see author/*.md
LECTURES = [
    ("ch00", "导论：递归自我改进的概念与分析框架", "00_导论_概念与方法"),
    ("ch01", "引言与动机：从智能爆炸到递归自我改进", "01_引言与动机"),
    ("ch02", "框架与分类：自我改进代理的形式化", "02_框架与分类"),
    ("ch03", "模型侧自改进：自训练、RLAIF与可验证奖励", "03_模型侧自改进"),
    ("ch04", "测试时扩展与验证器", "04_测试时扩展与验证器"),
    ("ch05", "脚手架进化：工具、代码与记忆", "05_脚手架进化"),
    ("ch06", "开放式进化与自我修改：从哥德尔机到达尔文哥德尔机", "06_开放式进化"),
    ("ch07", "评估、安全与极限", "07_评估安全与极限"),
    ("ch08", "前沿研究与后续阅读", "08_前沿研究与后续阅读"),
    ("appx", "参考文献与资源总表", "90_附录_参考文献"),
]

COMBINED_STEM = "RSI递归自我改进_合订本"

COURSE_TITLE = "递归自我改进（RSI）：概念、方法与证据"
COURSE_SUBTITLE = "合订本"
BOOK_SHORT = "RSI"

LICENSE_NOTE = (
    "本书由王自强整理，供个人学习与非商业交流使用。正文依据公开论文、课程"
    "和技术资料整理改写；引用的论文、图表及其他材料按正文标注和附录所列来源识别。"
    "相关内容的著作权及使用条件以原作者、出版方或原始来源的许可为准。整理日期：2026-10。"
)


def lecture_url(slug: str) -> str:
    return f"local://{slug}"


def lecture_no(index: int) -> str:
    """Visible chapter number; the introduction remains chapter 0."""
    return str(index)
