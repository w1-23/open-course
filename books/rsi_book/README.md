# 递归自我改进：概念、方法与证据

本目录保存作者稿、原创图表、配套实验、构建代码、来源登记和最终可编辑 DOCX。合订 PDF 位于仓库根目录。

## 目录

- `author/`：章节 HTML 作者稿。
- `source/diagrams/`：原创 SVG 图；`source/labs/`：可运行教学实验；`source/registry/`：来源和许可元数据。
- `source/img/`：作者稿实际引用的论文图像。来源与适用许可见仓库根目录 `THIRD_PARTY_NOTICES.md`。
- `vendor/mathjax/`：MathJax 离线排版依赖，许可为 Apache 2.0。
- `output/docx/合订本/`：可编辑合订 DOCX。构建生成的 PDF 和缓存由仓库 `.gitignore` 排除。

## 构建

在此目录运行 `python mathjax.py` 和 `python main.py --all` 构建 PDF；运行 `python tools/build_docx.py` 构建 DOCX。需要 Python 3、Node.js、Pandoc、PyMuPDF、Pillow、BeautifulSoup、lxml，以及可用的中文和西文字体。Pandoc 可通过 `PANDOC` 环境变量指定，Python 子进程使用当前解释器。

第三方论文原文不随仓库分发；引用和许可信息保留在 `source/registry/`。

## 公开版审阅与实测记录

当前公开稿由 GPT 辅助审阅，尚未经过逐条人工审校。完整 PDF 构建报告记录 206 个公式排版实例且 `math_failed=0`；这表示公式渲染未失败，不等同于全部数学结论已获证明。`source/labs/coverage_demo.py` 和 `selection_overfit_demo.py` 已运行，分别展示候选覆盖率及反复筛选带来的留出误差变化。章节中的其他代码示例未作逐段运行验证。