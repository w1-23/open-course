"""Front matter (title, credits, how-to-read, contents) and the bound volume.

The chapters are typeset as separate PDFs; this module builds the pages that
come before them and merges everything into one file with a two-level bookmark
tree.  Front matter is drawn directly with PyMuPDF rather than through Story:
the contents page needs the page numbers of every section, which are known only
after all chapters exist, and a dot-leader table of contents is easier to place
by measuring text than by coaxing a layout engine into it.
"""

from __future__ import annotations

import json
import os
import sys

import fitz

import config

CJK = "cjk"
LAT = "latin"
LATB = "latinb"

_FONT_CACHE: dict[str, fitz.Font] = {}


def _font(kind: str) -> fitz.Font:
    if kind not in _FONT_CACHE:
        path = {CJK: config.FONT_CJK, LAT: config.FONT_LATIN,
                LATB: config.FONT_LATIN_BOLD}[kind]
        _FONT_CACHE[kind] = fitz.Font(fontfile=path)
    return _FONT_CACHE[kind]


def _measure(text: str, size: float, kind: str = CJK) -> float:
    return _font(kind).text_length(text, fontsize=size)


def _is_ascii(ch: str) -> bool:
    return ord(ch) < 128


def segments(text: str):
    """Split text into (run, is_ascii) so Latin can use Times New Roman."""
    out: list[list] = []
    for ch in text:
        a = _is_ascii(ch)
        if out and out[-1][1] == a:
            out[-1][0] += ch
        else:
            out.append([ch, a])
    return [(run, a) for run, a in out]


def rich_width(text: str, size: float, bold: bool = False) -> float:
    w = 0.0
    for run, a in segments(text):
        w += _measure(run, size, (LATB if bold else LAT) if a else CJK)
    return w


def draw_rich(page, x: float, y: float, text: str, size: float,
              color=(0.07, 0.07, 0.07), bold: bool = False, align: str = "left",
              right_edge: float | None = None) -> float:
    """Draw a mixed Chinese/Latin line, returning the x just past its end."""
    w = rich_width(text, size, bold)
    if align == "center" and right_edge is not None:
        x = (x + right_edge) / 2 - w / 2
    elif align == "right" and right_edge is not None:
        x = right_edge - w
    for run, a in segments(text):
        fn = (LATB if bold else LAT) if a else CJK
        page.insert_text(fitz.Point(x, y), run, fontsize=size, fontname=fn, color=color)
        x += _measure(run, size, fn)
    return x


def wrap(text: str, width: float, size: float) -> list[str]:
    """Greedy wrap that keeps CJK characters (no spaces) breakable.

    A Latin run (word, number, URL) is moved to the next line as a whole
    instead of being cut in the middle: "SVG" must never come out as "SV" /
    "G" at a line end. Only a run wider than the column is hard-split.
    """
    lines: list[str] = []
    cur = ""
    for run, is_ascii in segments(text):
        if not is_ascii:
            for ch in run:
                if cur and rich_width(cur + ch, size) > width:
                    lines.append(cur)
                    cur = ch
                else:
                    cur += ch
            continue
        if not cur:
            cur = run.lstrip()
            while rich_width(cur, size) > width and len(cur) > 1:
                cut = len(cur) - 1
                while cut > 1 and rich_width(cur[:cut], size) > width:
                    cut -= 1
                lines.append(cur[:cut])
                cur = cur[cut:]
            continue
        if rich_width(cur + run, size) <= width:
            cur += run
            continue
        lines.append(cur.rstrip())
        cur = run.lstrip()
        while rich_width(cur, size) > width and len(cur) > 1:
            cut = len(cur) - 1
            while cut > 1 and rich_width(cur[:cut], size) > width:
                cut -= 1
            lines.append(cur[:cut])
            cur = cur[cut:]
    if cur:
        lines.append(cur)
    return lines


def _new_page(doc: fitz.Document):
    page = doc.new_page(width=config.PAGE_W, height=config.PAGE_H)
    page.insert_font(fontname=CJK, fontfile=config.FONT_CJK)
    page.insert_font(fontname=LAT, fontfile=config.FONT_LATIN)
    page.insert_font(fontname=LATB, fontfile=config.FONT_LATIN_BOLD)
    return page


LEFT = config.MARGIN_LEFT
RIGHT = config.SUMMARY_X1


def _footer(page, label: str, page_no: int) -> None:
    """Appendix pages live in the body, so they carry a page number like chapters.

    Without this the two appendix pages were the only numbered entries in the
    contents that a reader could not locate by flipping.
    """
    draw_rich(page, LEFT, config.FOOTER_Y, label, 7, color=config.LABEL_GREY)
    draw_rich(page, LEFT, config.FOOTER_Y, str(page_no), 8, align="right",
              right_edge=RIGHT)


# ------------------------------------------------------------------ pages
def title_page(doc: fitz.Document) -> None:
    page = _new_page(doc)
    draw_rich(page, LEFT, 258, config.BOOK_TITLE, 27, color=(0.13, 0.18, 0.24), align="center", right_edge=RIGHT)
    page.draw_line(fitz.Point(190, 286), fitz.Point(RIGHT - 156, 286),
                   color=(0.15, 0.15, 0.15), width=0.9)
    draw_rich(page, LEFT, 322, config.BOOK_SUBTITLE, 13,
              color=(0.25, 0.25, 0.25), align="center", right_edge=RIGHT)
    # Author line: the byline belongs on the title page, set in the body face
    # with a little tracking so three Han characters do not read as a label.
    draw_rich(page, LEFT, 360, config.BOOK_AUTHOR, 12,
              align="center", right_edge=RIGHT)
    draw_rich(page, LEFT, 396, config.BOOK_EDITION, 11,
              color=(0.35, 0.35, 0.35), align="center", right_edge=RIGHT)
    draw_rich(page, LEFT, 420, config.BOOK_DATE, 11,
              color=(0.35, 0.35, 0.35), align="center", right_edge=RIGHT)

    draw_rich(page, LEFT, 760, "仅供个人非商业学习使用", 9,
              color=config.LABEL_GREY, align="center", right_edge=RIGHT)


def credits_page(doc: fitz.Document) -> None:
    page = _new_page(doc)
    y = 90
    draw_rich(page, LEFT, y, "版权与出处说明", 14)
    y += 26
    for line in wrap(config.LICENSE_NOTE, RIGHT - LEFT, 10):
        draw_rich(page, LEFT, y, line, 10, color=(0.18, 0.18, 0.18))
        y += 17

    y += 12
    draw_rich(page, LEFT, y, "主要参考来源", 11.5)
    y += 20
    # GB/T 7714 式的简化条目：文献类型标识 + 出版信息，正文各章末尾的
    # 「延伸阅读」给出更细的对应关系。
    sources = [
        "Sutton R S, Barto A G. Reinforcement Learning: An Introduction[M]. "
        "2nd ed. Cambridge: MIT Press, 2018.（作者免费公开版）",
        "OpenAI. Spinning Up in Deep Reinforcement Learning[EB/OL]. "
        "https://spinningup.openai.com（CC BY-SA 4.0）",
        "Stanford University. CS224R: Deep Reinforcement Learning[EB/OL]；"
        "UC Berkeley. CS285: Deep Reinforcement Learning[EB/OL].",
        "Wang Z, et al. Reinforcement Learning for LLM Post-Training: "
        "A Survey[J]. arXiv:2407.16216",
        "Ouyang L, et al. Training Language Models to Follow Instructions "
        "with Human Feedback[J]. arXiv:2203.02155",
        "Schulman J, et al. Proximal Policy Optimization Algorithms[J]. "
        "arXiv:1707.06347",
        "Christiano P, et al. Deep Reinforcement Learning from Human "
        "Preferences[J]. arXiv:1706.03741",
        "Rafailov R, et al. Direct Preference Optimization: Your Language "
        "Model is Secretly a Reward Model[J]. arXiv:2305.18290",
        "Shao Z, et al. DeepSeekMath: Pushing the Limits of Mathematical "
        "Reasoning in Open Language Models[J]. arXiv:2402.03300",
    ]
    for s in sources:
        lines = wrap(s, RIGHT - LEFT - 14, 9.2)
        for i, line in enumerate(lines):
            if i == 0:
                draw_rich(page, LEFT + 2, y, "·", 9.2, color=(0.22, 0.22, 0.22))
            draw_rich(page, LEFT + 12, y, line, 9.2, color=(0.22, 0.22, 0.22))
            y += 14.5
        y += 3.0

    y += 10
    draw_rich(page, LEFT, y, "排版与工具", 11.5)
    y += 20
    tools = ("本书由 PyMuPDF 排版生成：正文为宋体与 Times New Roman，标题为黑体，"
             "公式经 MathJax 转为矢量图形后插入，插图为矢量 SVG。康奈尔版式、"
             "页眉页脚、公式编号与书签均由构建脚本自动生成。")
    for line in wrap(tools, RIGHT - LEFT, 9.2):
        draw_rich(page, LEFT, y, line, 9.2, color=(0.22, 0.22, 0.22))
        y += 14.5


def howto_page(doc: fitz.Document) -> None:
    page = _new_page(doc)
    y = 90
    draw_rich(page, LEFT, y, "使用说明", 14)
    y += 28

    blocks = [
        ("公式与编号",
         "公式统一用 LaTeX 录入并经 MathJax 渲染为矢量图形，因此任意放大都不失真。"
         "需要引用的公式在右侧标注章内编号，例如第 2 章第 7 式写作 (2.7)；"
         "书中引用写作「式 (2.7)」。重要结论以定义、定理、命题框给出，"
         "算法以带上下粗线的算法框给出，步骤编号形如 1:、2:。"
         "每个定理与误差界后面标注 [精确]、[渐近]、[近似] 或 [经验规律]，"
         "说明它的理论地位；没有定理支持时，正文不使用无条件的「收敛」「稳定」。"),
        ("图表",
         "图与表按章编号（图 1-2 表示第 1 章第 2 图），图题在图下方居中，"
         "表题在表上方居中，表格使用三线表。插图全部为矢量图，"
         "由本书配套脚本按数据重新绘制，不使用截图；数据图的图注给出种子、"
         "样本量与评估协议。"),
        ("全书结构",
         "全书分四部分十二章。第一部分（第 1–3 章）建立共同语言：多臂老虎机与探索、"
         "马尔可夫决策过程与贝尔曼理论、动态规划与蒙特卡洛、时序差分。"
         "第二部分（第 4–6 章）是经典与深度强化学习：函数逼近与离策略学习、"
         "策略梯度与 PPO、DQN 家族与连续控制。第三部分（第 7–9 章）讨论规划与"
         "进阶决策：模型与搜索、离线强化学习与策略评估、层次方法与多智能体、"
         "安全约束。第四部分（第 10–12 章）把这些工具用到语言模型与智能体："
         "RLHF 与偏好优化、RLVR 与推理强化学习、Agentic RL 与持续学习。"),
        ("三条阅读路线",
         "速查路线：只关心大模型后训练的读者读 2.1–2.4、5.1–5.3、第 10 章与第 11 章，"
         "遇到符号回查附录 A。系统路线：按章顺序读，四部分的桥梁节"
         "（2.4、3.2、4.3、5.1、5.6、10.3）不要跳过，它们是把前后章节缝起来的地方。"
         "研究路线：先读 4.3（投影贝尔曼与三类误差）、8.5（离策略评估）、"
         "10.3–10.5（KL 正则到 DPO）、11.2（GRPO），这些是当前讨论最活跃的节点。"),
        ("符号约定",
         "状态 s、动作 a、奖励 r、折扣 γ、策略 π、行为策略 μ、价值函数 V 与 Q、"
         "优势 A、参数 θ（策略）与 φ（价值或奖励模型）。期望的下标写明分布，"
         "例如 E_π[·] 表示按策略 π 采样求期望；上标 * 表示最优量，"
         "下标 t 表示时刻，k 表示迭代轮次。完整符号表与禁用写法见附录 A。"),
    ]
    for title, body in blocks:
        draw_rich(page, LEFT, y, title, 11.5)
        y += 19
        for line in wrap(body, RIGHT - LEFT, 10):
            draw_rich(page, LEFT, y, line, 10, color=(0.18, 0.18, 0.18))
            y += 17
        y += 10


def part_page(doc: fitz.Document, part: dict) -> None:
    """Divider page that opens each of the four parts."""
    page = _new_page(doc)
    draw_rich(page, LEFT, 300, f"第 {part['no']} 部分", 20,
              color=(0.25, 0.25, 0.25), align="center", right_edge=RIGHT)
    draw_rich(page, LEFT, 344, part["title"], 24, align="center", right_edge=RIGHT)
    page.draw_line(fitz.Point(200, 372), fitz.Point(RIGHT - 166, 372),
                   color=(0.55, 0.55, 0.55), width=0.7)
    y = 404
    for no in part["chapters"]:
        ch = config.chapter_by_no(no)
        draw_rich(page, LEFT, y, f"{_chap_label(ch)}　{ch['title']}", 11,
                  color=(0.3, 0.3, 0.3), align="center", right_edge=RIGHT)
        y += 22


# ------------------------------------------------------------------ contents
PER_PAGE = 44


def _chap_label(ch: dict) -> str:
    """「第 N 章」或者一个显式标签（预备章之类没有章号）。"""
    return ch.get("label") or f"第 {ch['no']} 章"


def _toc_lines(chapters: list[dict]) -> list[dict]:
    """Flatten parts, chapters and sections into rows for the contents list."""
    rows: list[dict] = []
    by_no = {ch["no"]: ch for ch in chapters}
    in_part = {n for prt in config.PARTS for n in prt["chapters"]}
    # 不属于任何部分的章（"全书导航"）排在最前，与合订顺序一致
    for ch in chapters:
        if ch["no"] in in_part:
            continue
        rows.append({"level": 1, "text": f"{_chap_label(ch)}　{ch['title']}",
                     "file": ch["file"], "page": 1})
        for lvl, text, page in ch.get("toc", []):
            if lvl == 1 or not text:
                continue
            rows.append({"level": 2 if lvl == 2 else 3, "text": text,
                         "file": ch["file"], "page": page})
    for part in config.PARTS:
        rows.append({"level": 0,
                     "text": f"第 {part['no']} 部分　{part['title']}",
                     "file": None, "page": 0})
        for no in part["chapters"]:
            ch = by_no.get(no)
            if not ch:
                continue
            rows.append({"level": 1, "text": f"{_chap_label(ch)}　{ch['title']}",
                         "file": ch["file"], "page": 1})
            for lvl, text, page in ch.get("toc", []):
                if lvl == 1 or not text:
                    continue
                rows.append({"level": 2 if lvl == 2 else 3, "text": text,
                             "file": ch["file"], "page": page})
    return rows


def _contents_page_count(n_rows: int) -> int:
    return max(1, -(-n_rows // PER_PAGE))


def contents_pages(doc: fitz.Document, rows: list[dict], front_pages: int,
                   offsets: dict[str, int]) -> int:
    """Draw the contents; page numbers already include the front matter offset."""
    if not rows:
        chunks = [[]]
    else:
        # Spread the rows evenly instead of filling 44 per page and leaving a
        # widow of one or two lines on the last page.
        n_pages = _contents_page_count(len(rows))
        per = -(-len(rows) // n_pages)
        chunks = [rows[i:i + per] for i in range(0, len(rows), per)]
    for pno, chunk in enumerate(chunks):
        page = _new_page(doc)
        y = 86 if pno else 104
        if pno == 0:
            draw_rich(page, LEFT, y - 44, "目　录", 16, align="center", right_edge=RIGHT)
            draw_rich(page, LEFT, y - 22, config.BOOK_AUTHOR, 9,
                      color=config.LABEL_GREY, align="center", right_edge=RIGHT)
        for row in chunk:
            lvl = row["level"]
            if lvl == 0:
                y += 10
                size = 11.5
                x = LEFT
            elif lvl == 1:
                y += 4
                size = 11.0
                x = LEFT + 14
            elif lvl == 2:
                size = 9.8
                x = LEFT + 28
            else:
                size = 9.0
                x = LEFT + 44
            end = draw_rich(page, x, y, row["text"], size,
                            color=(0.07, 0.07, 0.07) if lvl <= 1 else (0.2, 0.2, 0.2))
            if lvl == 0:
                # A part row carries no page number: it points at a divider
                # page, and a number there would compete with the chapters.
                y += 24
                continue
            # offsets[file] is the absolute 1-based page of the chapter's first
            # page, so a section's page is offset + (its own page - 1).
            number = str(row["abs_page"]) if row.get("abs_page") else str(
                offsets[row["file"]] + row["page"] - 1)
            numw = _measure(number, size, LAT)
            gap = RIGHT - numw - 4 - end
            if gap > 12:
                page.draw_line(fitz.Point(end + 4, y - 2.2),
                               fitz.Point(RIGHT - numw - 4, y - 2.2),
                               color=(0.62, 0.62, 0.62), width=0.45,
                               dashes="[0.5 2.6] 0")
            draw_rich(page, RIGHT - numw, y, number, size, color=(0.2, 0.2, 0.2))
            y += 20 if lvl == 1 else (17.5 if lvl == 2 else 16.0)
    return len(chunks)


def build_front(chapters: list[dict], front_pages: int, offsets: dict[str, int],
                path: str) -> None:
    doc = fitz.open()
    title_page(doc)
    credits_page(doc)
    howto_page(doc)
    contents_pages(doc, _toc_lines(chapters), front_pages, offsets)
    doc.set_toc([])
    doc.save(path, garbage=4, deflate=True, clean=True)
    doc.close()


def _build_parts(path: str) -> None:
    doc = fitz.open()
    for part in config.PARTS:
        part_page(doc, part)
    doc.set_toc([])
    doc.save(path, garbage=4, deflate=True, clean=True)
    doc.close()


# ------------------------------------------------------------------ appendix
# Symbols are drawn with insert_text, so the notation here is plain unicode:
# superscripts are written inline (V^π) rather than typeset.  A formula index
# typeset by MathJax would double the page count for no reading benefit.
SYMBOLS = [
    ("γ", "折扣因子，0 ≤ γ < 1；不是学习率"),
    ("λ", "资格迹／GAE 的迹参数；安全章的概率水平用 η"),
    ("τ", "轨迹 (s_0,a_0,r_1,…)；时间下标 t 是步"),
    ("μ", "行为策略（采样策略）；不表示均值"),
    ("π", "目标策略；π_old 是 PPO 的采样策略"),
    ("π_ref", "参考策略，KL 正则的中心"),
    ("α", "学习率；熵温度写作 α_ent，不与之共用"),
    ("β_KL", "KL 正则系数；1/β_KL 是逆温度"),
    ("α_ent", "最大熵 RL 的温度（SAC）"),
    ("ε_greedy", "ε-贪心的探索概率"),
    ("ε_clip", "PPO 的裁剪半径"),
    ("ε_num", "数值保护小量，不是算法参数"),
    ("ρ_t", "重要性比率 π(a_t|s_t)/μ(a_t|s_t)"),
    ("δ_t", "TD 误差 r_t + γV(s_{t+1}) - V(s_t)"),
    ("G_t", "从 t 起的折扣回报"),
    ("G^λ", "λ-回报 (1-λ)Σλ^{n-1}G^(n)"),
    ("V^π(s)", "策略 π 下的状态价值（真值）"),
    ("Q^π(s,a)", "策略 π 下的动作价值（真值）"),
    ("A^π(s,a)", "优势 Q^π - V^π"),
    ("V_φ, Q_φ", "参数化的价值估计，不得当真值"),
    ("Â_t", "估计的优势；帽号必须写"),
    ("V*, Q*", "最优价值函数"),
    ("d^π_γ(s)", "折扣占用测度，总质量 1/(1-γ)"),
    ("d_bar^π_γ(s)", "归一化占用测度，总质量 1"),
    ("T^π, T*", "贝尔曼算子／最优贝尔曼算子"),
    ("Φ", "特征矩阵（满列秩）；V_θ = Φθ"),
    ("D", "加权分布矩阵（对角）；数据集写作 D_data"),
    ("Π_D", "D-内积下的投影 Φ(Φ^TDΦ)^{-1}Φ^TD"),
    ("θ, φ", "策略参数／价值参数"),
    ("MSBE", "未投影的均方贝尔曼误差"),
    ("MSPBE", "投影后的均方贝尔曼误差"),
    ("TV", "总变差距离"),
    ("KL(p‖q)", "KL 散度，方向必须写明"),
    ("H(π)", "策略熵"),
    ("Z(x)", "DPO 的配分函数 Σ_y π_ref(y|x)e^{r(x,y)/β}"),
    ("r_φ(x,y)", "奖励模型的输出"),
    ("B", "经验回放缓冲区；老虎机的臂数用 K"),
    ("K", "臂数（第 1 章）；状态数用 |S|"),
    ("Regret(T)", "T 步累积遗憾"),
    ("UCB", "置信上界索引"),
    ("N(s), N(s,a)", "访问计数"),
    ("P(s'|s,a)", "转移概率"),
    ("r(s,a)", "期望奖励"),
    ("p(s'|s,a)", "环境动力学（连续情形）"),
    ("|S|, |A|", "状态数／动作数"),
    ("E", "期望；下标写明所服从的分布"),
    ("Var", "方差"),
    ("CVaR_α", "条件风险价值（损失的上尾）"),
    ("VaR_α", "风险价值（分位数）"),
    ("η", "CVaR 的优化变量；也是安全章的概率水平"),
    ("Q_tot", "多智能体的联合动作价值"),
    ("f(·)", "QMIX 的混合网络"),
    ("o_i", "第 i 个智能体的局部观测"),
    ("β_o", "Option 的终止函数"),
    ("I_o, π_o", "Option 的初始集与内部策略"),
    ("R_to", "Decision Transformer 的回报条件（return-to-go）"),
    ("ε", "扰动／噪声，含义按上下文写明"),
    ("σ²", "方差；σ_r 是奖励标准差"),
    ("Δθ", "参数增量"),
    ("grad", "梯度"),
]


def appendix_a(doc: fitz.Document, first_page: int = 0) -> int:
    """Symbol table: one entry per row, meaning wrapped inside the text column."""
    per_page = 33
    pages = max(1, -(-len(SYMBOLS) // per_page))
    for pno in range(pages):
        page = _new_page(doc)
        _footer(page, "附录 A　符号表", first_page + pno)
        if pno == 0:
            draw_rich(page, LEFT, 74, "附录 A　符号表", 16, align="center",
                      right_edge=RIGHT)
            draw_rich(page, LEFT, 94,
                      "上标写作 ^、下标写作 _；估计量一律带帽号或下标 φ，以示与真值不同",
                      9, color=config.LABEL_GREY, align="center", right_edge=RIGHT)
        chunk = SYMBOLS[pno * per_page:(pno + 1) * per_page]
        for i, (sym, meaning) in enumerate(chunk):
            # Rows must stay inside the body band: anything that reaches the
            # summary band is reserved for handwriting and verify.py flags it.
            y = 112 + i * 18.0
            draw_rich(page, LEFT + 4, y, sym, 9.6)
            lines = wrap(meaning, RIGHT - (LEFT + 96) - 4, 9.6)
            draw_rich(page, LEFT + 96, y, lines[0], 9.6, color=(0.22, 0.22, 0.22))
            if len(lines) > 1:
                draw_rich(page, LEFT + 96, y + 10.6, lines[1], 9.6,
                          color=(0.22, 0.22, 0.22))
    return pages


def appendix_b(doc: fitz.Document, by_slug: dict[str, int], front_pages: int,
               first_page: int = 0) -> int:
    """Formula index: (N.k) and the page it was printed on, three columns."""
    rows: list[tuple[str, int]] = []
    # 阅读顺序：不属于任何部分的章（第 0 章）在最前，然后按 PARTS 的排列
    # （预备章 95 在 10 之前），而不是 config.CHAPTERS 的定义顺序。
    in_part = {n for prt in config.PARTS for n in prt["chapters"]}
    order = [ch for ch in config.CHAPTERS if ch["no"] not in in_part]
    for prt in config.PARTS:
        for n in prt["chapters"]:
            try:
                order.append(config.chapter_by_no(n))
            except KeyError:
                pass
    for ch in order:
        path = os.path.join(config.cache_dir(ch["slug"]), "eqno.json")
        if not os.path.exists(path) or ch["slug"] not in by_slug:
            continue
        data = json.load(open(path, encoding="utf-8"))
        # by_slug holds the absolute page of the chapter's first page; the
        # formula pages stored in eqno.json are chapter-relative.
        base = by_slug[ch["slug"]] - 1
        for item in data.get("eqnos", []):
            rows.append((f"({item['eqno']})", base + item["page"]))
    if not rows:
        return 0
    # 42 rows x 3 columns per page.  Fill 42/42/rest and the last page ends up
    # with five entries on it, so first split the rows evenly over the pages,
    # then balance the three columns inside each page.
    cap = 42 * 3
    pages = max(1, -(-len(rows) // cap))
    per_page = -(-len(rows) // pages)
    for pno in range(pages):
        page = _new_page(doc)
        _footer(page, "附录 B　公式索引", first_page + pno)
        if pno == 0:
            draw_rich(page, LEFT, 74, "附录 B　公式索引", 16, align="center",
                      right_edge=RIGHT)
            draw_rich(page, LEFT, 96, "按章编号排列，数字为该公式所在页",
                      9, color=config.LABEL_GREY, align="center", right_edge=RIGHT)
        else:
            draw_rich(page, LEFT, 60, "附录 B　公式索引（续）", 9,
                      color=config.LABEL_GREY, align="center", right_edge=RIGHT)
        chunk = rows[pno * per_page:(pno + 1) * per_page]
        ncol = max(1, -(-len(chunk) // 42))
        per_col = max(1, -(-len(chunk) // ncol))
        for i, (label, pageno) in enumerate(chunk):
            col, row = divmod(i, per_col)
            x = LEFT + 2 + col * 133
            y = 120 + row * 13.6
            draw_rich(page, x, y, label, 8.8)
            num = str(pageno)
            w = _measure(num, 8.8, LAT)
            draw_rich(page, x + 126 - w, y, num, 8.8, color=(0.3, 0.3, 0.3))
    return pages


def build_appendix(by_slug: dict[str, int], front_pages: int, path: str,
                   first_page: int = 0) -> tuple[int, int]:
    doc = fitz.open()
    a_pages = appendix_a(doc, first_page)
    b_pages = appendix_b(doc, by_slug, front_pages, first_page + a_pages)
    pages = doc.page_count
    doc.set_toc([])
    doc.save(path, garbage=4, deflate=True, clean=True)
    doc.close()
    return a_pages, b_pages



# ------------------------------------------------------------------ assemble
def assemble(results: list[dict], allow_missing: bool = False) -> dict:
    """Merge front matter, four part dividers and the chapters into one volume."""
    by_no = {r["no"]: r for r in results}
    chapters: list[dict] = []
    missing: list[int] = []
    for ch in config.CHAPTERS:
        r = by_no.get(ch["no"])
        if r is None:
            missing.append(ch["no"])
            continue
        doc = fitz.open(os.path.join(config.OUTPUT_DIR, r["file"]))
        chapters.append({"no": r["no"], "title": r["title"], "file": r["file"],
                         "label": ch.get("label"),
                         "pages": doc.page_count,
                         "toc": r.get("toc") or doc.get_toc()})
        doc.close()
    if missing and not allow_missing:
        raise SystemExit(f"缺少章节 PDF：{missing}（如需预览版请用 --preview）")

    known = {ch["no"]: ch for ch in chapters}
    # 不属于任何部分的章（"全书导航"这类前置章）排在目录之后、第一部分之前；
    # 这里先算出来，下面的目录行排序要用到它。
    in_part = {n for prt in config.PARTS for n in prt["chapters"]}
    front_chs = [ch for ch in chapters if ch["no"] not in in_part]
    rows = _toc_lines(chapters)
    if front_chs:
        key0 = front_chs[0]["file"]
        rows.sort(key=lambda r: 0 if r.get("file") == key0 else 1)
    # Two appendix rows join the contents; their page numbers are resolved after
    # the chapter offsets are known (see abs_page below).
    rows.append({"level": 1, "text": "附录 A　符号表", "file": None, "page": 0,
                 "abs_page": 0})
    rows.append({"level": 1, "text": "附录 B　公式索引", "file": None, "page": 0,
                 "abs_page": 0})

    # 3 text pages (title / credits / how-to) + the contents pages, which depend
    # on how many rows there are and whose numbering depends on the front page
    # count: solve the fixed point by iterating.
    n_text = 3
    front_pages = n_text + _contents_page_count(len(rows))
    for _ in range(6):
        guess = n_text + _contents_page_count(len(rows))
        if guess == front_pages:
            break
        front_pages = guess

    # Chapter offsets are ABSOLUTE 1-based pages.  Part dividers are interleaved
    # with the chapters (divider, its chapters, next divider, ...), so the old
    # "all dividers sit before chapter 1" assumption put every bookmark and
    # every contents page number off by the number of dividers that follow.
    offsets: dict[str, int] = {}
    part_abs: dict[int, int] = {}
    pos = front_pages + 1                 # page of the first part divider

    # 前置章（no==0，例如"全书导航"）不属于任何部分，排在目录之后、第一部分之前。
    in_part = {n for prt in config.PARTS for n in prt["chapters"]}
    front_chs = [ch for ch in chapters if ch["no"] not in in_part]
    for ch in front_chs:
        offsets[ch["file"]] = pos
        pos += ch["pages"]

    for part in config.PARTS:
        part_abs[part["no"]] = pos
        pos += 1
        for no in part["chapters"]:
            ch = known.get(no)
            if ch is None:
                continue
            offsets[ch["file"]] = pos
            pos += ch["pages"]
    body_end = pos - 1
    body_start = (offsets[front_chs[0]['file']] if front_chs
                  else front_pages + 2)   # 第一个正文页的绝对页码
    by_slug = {ch["slug"]: offsets[known[ch["no"]]["file"]]
               for ch in config.CHAPTERS if ch["no"] in known}

    app_path = os.path.join(config.CACHE_DIR, "_appendix.pdf")
    n_app_a, n_app_b = build_appendix(by_slug, body_start, app_path, body_end + 1)
    if len(rows) >= 2:
        rows[-2]["abs_page"] = body_end + 1
        rows[-1]["abs_page"] = body_end + 1 + n_app_a

    front_path = os.path.join(config.CACHE_DIR, "_front.pdf")
    parts_path = os.path.join(config.CACHE_DIR, "_parts.pdf")
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    build_front(chapters, body_start, offsets, front_path)
    _build_parts(parts_path)

    out = fitz.open(front_path)
    for ch in front_chs:
        src = fitz.open(os.path.join(config.OUTPUT_DIR, ch["file"]))
        out.insert_pdf(src)
        src.close()
    pdoc = fitz.open(parts_path)
    for pi, part in enumerate(config.PARTS):
        out.insert_pdf(pdoc, from_page=pi, to_page=pi)
        for no in part["chapters"]:
            ch = known.get(no)
            if ch is None:
                continue
            src = fitz.open(os.path.join(config.OUTPUT_DIR, ch["file"]))
            out.insert_pdf(src)
            src.close()
    pdoc.close()
    if n_app_a or n_app_b:
        adoc = fitz.open(app_path)
        out.insert_pdf(adoc)
        adoc.close()

    # Bookmark tree: part (1) -> chapter (2) -> section (3).  Subsections stay
    # out of the bound volume so the tree stays readable; they are still present
    # in each single-chapter PDF.
    toc: list[list] = [[1, "目　录", 4]]
    for ch in front_chs:
        toc.append([1, f"{_chap_label(ch)}　{ch['title']}", offsets[ch["file"]]])
        base = offsets[ch["file"]] - 1
        for lvl, text, page in ch["toc"]:
            if lvl != 2 or not text:
                continue
            # 前置章本身是 level 1，它的节必须是 level 2（跳跃层级会被 set_toc 拒绝）
            toc.append([2, text, base + max(1, page)])
    for pi, part in enumerate(config.PARTS):
        toc.append([1, f"第 {part['no']} 部分　{part['title']}", part_abs[part["no"]]])
        for no in part["chapters"]:
            ch = known.get(no)
            if ch is None:
                continue
            base = offsets[ch["file"]] - 1     # so base + page == absolute page
            toc.append([2, f"{_chap_label(ch)}　{ch['title']}", base + 1])
            for lvl, text, page in ch["toc"]:
                if lvl != 2 or not text:
                    continue
                toc.append([3, text, base + max(1, page)])
    if n_app_a:
        toc.append([1, "附录 A　符号表", body_end + 1])
    if n_app_b:
        toc.append([1, "附录 B　公式索引", body_end + 1 + n_app_a])
    out.set_toc(toc)

    out_path = os.path.join(config.OUTPUT_DIR, f"{config.COMBINED_STEM}.pdf")
    out.subset_fonts()
    # A reader holding the previous volume open makes MuPDF's save fail with
    # "cannot remove file ...: Permission denied" (it writes a temp file and
    # renames).  Fall back to a versioned name instead of losing the build.
    try:
        out.save(out_path, garbage=4, deflate=True, clean=True)
    except Exception as exc:                       # noqa: BLE001 - mupdf error
        alt = out_path.replace(".pdf", "_新.pdf")
        out.save(alt, garbage=4, deflate=True, clean=True)
        print(f"  [warn] 无法写入 {os.path.basename(out_path)}（{exc}），"
              f"已改写为 {os.path.basename(alt)}；请关闭阅读器后重命名为正式名",
              file=sys.stderr)
        out_path = alt
    pages = out.page_count
    out.close()

    return {"file": os.path.basename(out_path), "pages": pages,
            "size_bytes": os.path.getsize(out_path),
            "bookmarks": len(toc), "front_pages": front_pages,
            "parts": len(config.PARTS), "missing": missing}
