"""Central configuration for the reinforcement-learning textbook build.

Everything that is book-specific, layout-specific or path-specific lives here
so the rest of the pipeline stays declarative.  This project reuses the
CS336-notes renderer (PyMuPDF Story + MathJax vector formulas + Cornell grid);
only the paths, the chapter list, the furniture text and a few typographic
switches differ.
"""

import os

# ---------------------------------------------------------------- paths
BUILD_DIR = os.path.dirname(os.path.abspath(__file__))

CACHE_DIR = os.path.join(BUILD_DIR, "cache")
SOURCE_DIR = os.path.join(BUILD_DIR, "source")
CONTENT_DIR = os.path.join(BUILD_DIR, "content")
FIG_DIR = os.path.join(BUILD_DIR, "figures")
FIG_OUT = os.path.join(FIG_DIR, "out")
OUTPUT_DIR = os.path.join(BUILD_DIR, "output")
REPORT_PATH = os.path.join(OUTPUT_DIR, "构建报告.json")
MATHJAX_DIR = os.path.join(BUILD_DIR, "vendor", "mathjax")

# ---------------------------------------------------------------- fonts
# Thesis type stack: Times New Roman for Latin letters and digits, SimSun for
# Chinese, SimHei for headings, Consolas for code.  MuPDF Story accepts only one
# family name per element (a CSS list collapses to its built-in default), so the
# Latin/Chinese mixture is expressed with per-run spans -- see prepare._split_fonts.
FONT_CJK = r"C:\Windows\Fonts\simsun.ttc"          # 宋体
FONT_CJK_BOLD = r"C:\Windows\Fonts\simhei.ttf"     # 黑体
FONT_LATIN = r"C:\Windows\Fonts\times.ttf"         # Times New Roman
FONT_LATIN_BOLD = r"C:\Windows\Fonts\timesbd.ttf"  # Times New Roman Bold
FONT_MONO = r"C:\Windows\Fonts\consola.ttf"

# Furniture text (header / footer / summary label) is measured and drawn in the
# CJK face, which also carries Times-like Latin glyphs.
FONT_BODY = FONT_CJK

# ---------------------------------------------------------------- page geometry (points)
PAGE_W, PAGE_H = 595.0, 842.0          # A4
MARGIN_LEFT = 34.0
MARGIN_RIGHT = 34.0

HEADER_Y = 40.0                         # top rule of the note grid
FOOTER_Y = 826.0                        # page-number baseline

# The writing column sits on the RIGHT of the page: body on the left, a blank
# cue column on the right, and the summary band across the bottom.
CUE_X0 = 447.0                          # cue column left edge
CUE_X1 = MARGIN_LEFT + (PAGE_W - 2 * MARGIN_LEFT)   # cue column right edge (561)
RULE_X = 441.0                          # vertical Cornell rule
RULE_TOP = 40.0
RULE_BOTTOM = 806.0

BODY_X0 = MARGIN_LEFT                   # body text left edge (34)
BODY_X1 = 433.0                         # body text right edge
BODY_Y0 = 58.0                          # body text top
BODY_Y1 = 694.0                         # body text bottom (summary rule below)

SUMMARY_RULE_Y = 706.0
SUMMARY_X0 = MARGIN_LEFT
SUMMARY_X1 = 561.0

RULE_GREY = (0.72, 0.72, 0.72)
LABEL_GREY = (0.55, 0.55, 0.55)

# ---------------------------------------------------------------- typography
# 毕业论文正文规格：小四（12pt）宋体，1.5 倍行距，首行缩进两字符，两端对齐。
BODY_FONT_SIZE = 12.0
BODY_LINE_HEIGHT = 1.5
JUSTIFY = True
# 1ex of the body face; MathJax reports SVG sizes in ex units.
# MathJax SVG: 1ex = 0.442em.  Keep formulas slightly below the 12pt body
# height so dense notation remains readable without visually overpowering prose.
# Inline 4.9 -> em 11.1pt; display 5.1 -> 11.5pt.
EX_PT = 4.9
DISPLAY_SCALE = 5.1
DISPLAY_MAX_WIDTH = 392.0
# An "inline" formula wider than this cannot flow inside a line of the 399pt
# column: with the preceding text the line is already full, so it drops to a new
# line and the following words continue after it.  Such formulas belong in a
# display block; prepare.py reports them so the source can be corrected.
INLINE_MAX_WIDTH = 220.0
# A numbered display is centred in the column while the number is flush right at
# BODY_X1, so the image may only reach 2*(eqno_x0 - column_centre).  At 392pt a
# centred formula spans 50.5..416.5 and the number starts around 409: the two
# overlap.  340 keeps every numbered formula clear of its number.
DISPLAY_MAX_NUMBERED = 340.0

# ---------------------------------------------------------------- chapters
# Four parts, twelve chapters (frozen; see content/_CONVENTIONS.md).
# "pages" is the centre of the per-chapter budget, used only for reporting.
CHAPTERS = [
    {"slug": "ch01", "no": 1, "title": "Bandit 与探索",
     "stem": "01_Bandit与探索", "pages": 16, "budget": (15, 17)},
    {"slug": "ch02", "no": 2, "title": "MDP 与 Bellman 理论",
     "stem": "02_MDP与Bellman理论", "pages": 20, "budget": (19, 22)},
    {"slug": "ch03", "no": 3, "title": "动态规划、蒙特卡洛与时序差分",
     "stem": "03_DP与TD", "pages": 19, "budget": (18, 20)},
    {"slug": "ch04", "no": 4, "title": "函数逼近与离策略学习",
     "stem": "04_函数逼近与离策略", "pages": 21, "budget": (20, 23)},
    {"slug": "ch05", "no": 5, "title": "策略梯度、信赖域与 PPO",
     "stem": "05_策略梯度与PPO", "pages": 21, "budget": (20, 22)},
    {"slug": "ch06", "no": 6, "title": "深度强化学习：从 DQN 家族到连续控制",
     "stem": "06_深度强化学习", "pages": 20, "budget": (19, 21)},
    {"slug": "ch07", "no": 7, "title": "模型、规划与搜索",
     "stem": "07_模型与规划", "pages": 19, "budget": (18, 21)},
    {"slug": "ch08", "no": 8, "title": "离线强化学习与策略评估",
     "stem": "08_离线RL与评估", "pages": 20, "budget": (19, 22)},
    {"slug": "ch09", "no": 9, "title": "层次、多智能体与安全约束",
     "stem": "09_层次与多智能体", "pages": 18, "budget": (17, 19)},
    {"slug": "ch10", "no": 10, "title": "RLHF 与偏好优化",
     "stem": "10_RLHF与偏好优化", "pages": 20, "budget": (19, 22)},
    {"slug": "ch11", "no": 11, "title": "RLVR 与推理强化学习",
     "stem": "11_RLVR与GRPO", "pages": 20, "budget": (19, 22)},
    {"slug": "ch12", "no": 12, "title": "Agentic RL 与持续学习",
     "stem": "12_AgenticRL与持续学习", "pages": 17, "budget": (16, 18)},
    {"slug": "ch00", "no": 0, "title": "全书导论：核心问题、结构与理论边界",
     "stem": "00_全书导航", "pages": 14, "budget": (12, 16), "front": True},
    {"slug": "ch13prep", "no": 95, "title": "语言模型作为策略",
     "stem": "预备_语言模型作为策略", "pages": 13, "budget": (11, 14),
     "label": "预备", "prefix": "P"},
]

# Four parts; each part gets a divider page carrying its own bookmark.
PARTS = [
    {"no": 1, "title": "数学与决策基础", "chapters": (1, 2, 3)},
    {"no": 2, "title": "经典与深度强化学习", "chapters": (4, 5, 6)},
    {"no": 3, "title": "规划与进阶决策", "chapters": (7, 8, 9)},
    {"no": 4, "title": "语言模型与自主智能体", "chapters": (95, 10, 11, 12)},
]

COMBINED_STEM = "强化学习教材_合订本"

BOOK_TITLE = "强 化 学 习"
BOOK_TITLE_HEADER = "强化学习"
BOOK_SUBTITLE = "从 Bandit 到 RLHF、RLVR 与 Agentic RL"
BOOK_AUTHOR = "王自强整理"
BOOK_EDITION = "合订本"
BOOK_DATE = "2026 年 10 月"

LICENSE_NOTE = (
    "本书由王自强整理，供个人学习与非商业交流使用。正文依据公开课程、公开论文与公开教材整理改写；"
    "公式、图表和具体论述的来源见正文标注及附录。相关材料的著作权与使用条件归各自权利人所有；"
    "Sutton & Barto《Reinforcement Learning: An Introduction》由 MIT Press 免费公开，"
    "arXiv 论文按各自许可发布，Spinning Up 文档为 CC BY-SA 4.0。"
    "本文件仅供个人非商业学习使用。"
)


# ---------------------------------------------------------------- path helpers
def chapter_by_no(no: int) -> dict:
    """Look a chapter up by its number (not by list position)."""
    for ch in CHAPTERS:
        if ch["no"] == no:
            return ch
    raise KeyError(f"no chapter {no}")


def chapter_prefix(ch: dict) -> str:
    """编号前缀：普通章用章号，预备章用字母（如 P）。"""
    return str(ch.get("prefix") or ch["no"])


def no_of_prefix(tok: str) -> int | None:
    """把编号前缀（"7" 或 "P"）还原成章号；认不出返回 None。"""
    tok = str(tok).strip()
    if tok.isdigit():
        return int(tok)
    for ch in CHAPTERS:
        if ch.get("prefix") and str(ch["prefix"]).upper() == tok.upper():
            return ch["no"]
    return None


def chapter_by_index(index: int) -> dict:
    """0-based index -> chapter record (a copy, so callers cannot mutate config)."""
    return dict(CHAPTERS[index])


def chapter_by_slug(slug: str) -> dict:
    for ch in CHAPTERS:
        if ch["slug"] == slug:
            return dict(ch)
    raise KeyError(slug)


def cache_dir(slug: str) -> str:
    return os.path.join(CACHE_DIR, slug)


def page_html(slug: str) -> str:
    """The HTML the layout stage consumes (written by md2html.py)."""
    return os.path.join(cache_dir(slug), "page.html")


def math_json(slug: str) -> str:
    return os.path.join(cache_dir(slug), "math.json")


def work_dir(slug: str) -> str:
    return os.path.join(cache_dir(slug), "work")


def chapter_md(slug: str) -> str:
    return os.path.join(CONTENT_DIR, f"{slug}.md")


def out_pdf(stem: str) -> str:
    return os.path.join(OUTPUT_DIR, f"{stem}.pdf")
