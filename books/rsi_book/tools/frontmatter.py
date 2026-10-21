"""Create the cover, imprint, use note, and contents pages for the combined PDF."""
import os

import fitz

import config


def _font(page, name, path):
    page.insert_font(fontname=name, fontfile=path)


def _center(page, text, y, size, font="cjk", color=(0.12, 0.12, 0.12)):
    path = {"cjk": config.FONT_CJK, "hei": config.FONT_CJK_BOLD,
            "latin": config.FONT_LATIN}[font]
    width = fitz.Font(fontfile=path).text_length(text, fontsize=size)
    page.insert_text(fitz.Point((config.PAGE_W - width) / 2, y), text,
                     fontsize=size, fontname=font, color=color)


def _body(page, text, rect, size=11, lineheight=1.6, font="cjk"):
    page.insert_textbox(fitz.Rect(rect), text, fontsize=size, fontname=font,
                        lineheight=lineheight, color=(0.18, 0.18, 0.18),
                        align=fitz.TEXT_ALIGN_LEFT)


def make_frontmatter(body_toc, output_path):
    """Build three unnumbered front pages and a paginated, hierarchical contents."""
    doc = fitz.open()
    toc_rows_per_page = 40
    toc_pages = max(1, (len(body_toc) + toc_rows_per_page - 1) // toc_rows_per_page)
    for _ in range(3 + toc_pages):
        page = doc.new_page(width=config.PAGE_W, height=config.PAGE_H)
        _font(page, "cjk", config.FONT_CJK)
        _font(page, "hei", config.FONT_CJK_BOLD)
        _font(page, "latin", config.FONT_LATIN)

    # Cover
    p = doc[0]
    _center(p, "递归自我改进", 250, 27, "hei")
    p.draw_line(fitz.Point(155, 278), fitz.Point(440, 278), color=(0.35, 0.35, 0.35), width=0.8)
    _center(p, "概念、方法与证据", 317, 14, "cjk", (0.38, 0.38, 0.38))
    _center(p, "RSI：Recursive Self-Improvement", 358, 10, "latin", (0.38, 0.38, 0.38))
    _center(p, "个人学习教材", 408, 12, "cjk")
    _center(p, "2026 年 10 月", 440, 10, "cjk", (0.38, 0.38, 0.38))
    _center(p, "供个人学习使用", 790, 8, "cjk", (0.58, 0.58, 0.58))

    # Imprint and sources statement
    p = doc[1]
    p.insert_text((72, 92), "版权与出处说明", fontsize=18, fontname="hei")
    _body(p,
          "本书为个人学习教材。正文围绕递归自我改进相关概念、方法与证据进行整理和说明。\n\n"
          "引用的论文、数据、图表及其他材料按正文标注和附录所列来源识别。相关内容的著作权及使用条件以原作者、出版方或原始来源的许可为准。\n\n"
          "本书不构成对任何系统能力、安全性或未来发展的保证。引用实验结果时，应结合原研究的任务、基线、数据、评估协议和适用范围理解。",
          (72, 125, 523, 340), 11, 1.7)
    p.insert_text((72, 390), "主要资料", fontsize=13, fontname="hei")
    _body(p,
          "本书的论文来源、数据集、软件项目和补充资源集中列于书末附录。具体论断以对应研究原文及其公开版本为依据；转述内容不替代原始论文。",
          (72, 420, 523, 505), 10.5, 1.65)

    # How to use this textbook
    p = doc[2]
    p.insert_text((72, 92), "使用说明", fontsize=18, fontname="hei")
    p.insert_text((72, 145), "预备知识", fontsize=12, fontname="hei")
    _body(p,
          "阅读本书需要高中代数、基本概率、函数图像，以及运行和修改短小 Python 程序的能力。机器学习与强化学习基础有助于理解模型训练章节；相关符号和概念会在正文首次使用时说明。",
          (72, 165, 523, 245), 10.5, 1.6)
    p.insert_text((72, 275), "全书结构", fontsize=12, fontname="hei")
    _body(p,
          "第 0 章　导论：递归自我改进的概念与分析框架\n"
          "第 1 章　引言与动机：从智能爆炸到递归自我改进\n"
          "第 2 章　框架与分类：自我改进代理的形式化\n"
          "第 3 章　模型侧自改进：自训练、RLAIF 与可验证奖励\n"
          "第 4 章　测试时扩展与验证器\n"
          "第 5 章　脚手架进化：工具、代码与记忆\n"
          "第 6 章　开放式进化与自我修改\n"
          "第 7 章　评估、安全与极限\n"
          "第 8 章　前沿研究与后续阅读\n"
          "附录　参考文献与资源总表",
          (72, 295, 523, 455), 9.5, 1.35)
    p.insert_text((72, 447), "建议学习方式", fontsize=12, fontname="hei")
    _body(p,
          "先读第 0—2 章，掌握系统表示、更新对象和分类维度；再按研究问题阅读第 3—6 章。阅读每种方法时，记录更新对象、反馈来源、候选或参数如何改变、改动保存在哪里，以及评估证据支持什么结论。最后结合第 7 章检查评估独立性、安全边界和外推条件，并用附录中的符号表与实验材料复习。",
          (72, 467, 523, 620), 10.5, 1.6)

    # Contents: chapter headings and section headings follow the PDF outline.
    cjk = fitz.Font(fontfile=config.FONT_CJK)
    latin = fitz.Font(fontfile=config.FONT_LATIN)
    start = 0
    for page_idx in range(toc_pages):
        p = doc[3 + page_idx]
        heading = "目录" if page_idx == 0 else "目录（续）"
        _center(p, heading, 48, 17, "hei")
        _center(p, "递归自我改进 · 个人学习教材", 68, 8, "cjk", (0.5, 0.5, 0.5))
        y = 101
        rows = body_toc[start:start + toc_rows_per_page]
        for level, title, page_no in rows:
            indent = 0 if level == 1 else 18
            size = 9.5 if level == 1 else 9.0
            font_name = "hei" if level == 1 else "cjk"
            font = fitz.Font(fontfile=config.FONT_CJK_BOLD if level == 1 else config.FONT_CJK)
            x = 54 + indent
            right = 538
            num = str(page_no)
            nw = latin.text_length(num, fontsize=size)
            num_x = right - nw
            max_title_w = num_x - x - 18
            shown = title
            while shown and font.text_length(shown, fontsize=size) > max_title_w:
                shown = shown[:-2] + "…" if len(shown) > 2 else shown[:-1]
            title_w = font.text_length(shown, fontsize=size)
            p.insert_text((x, y), shown, fontsize=size, fontname=font_name,
                          color=(0.15, 0.15, 0.15))
            dot_start = x + title_w + 7
            dot_end = num_x - 7
            if dot_end > dot_start:
                dot_count = max(0, int((dot_end - dot_start) / 2.7))
                if dot_count:
                    p.insert_text((dot_start, y), "." * dot_count, fontsize=6.5,
                                  fontname="latin", color=(0.68, 0.68, 0.68))
            p.insert_text((num_x, y), num, fontsize=size, fontname="latin",
                          color=(0.15, 0.15, 0.15))
            y += 16.8
        start += len(rows)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    return 3 + toc_pages

