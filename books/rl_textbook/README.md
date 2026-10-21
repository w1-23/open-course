# 强化学习教材

本目录保存第 0—12 章及预备章的源稿、图表、构建代码、审校证据和引用元数据。合订 PDF 位于仓库根目录。

## 目录

- `content/`：教材正文与写作规范。
- `figures/`：图表源脚本和正文 SVG。
- `review/`：数学审校、推导、证据卡、复现实验与来源复核。
- `source/library/`：来源元数据；第三方论文、教材、网页全文和提取文本未随仓库分发。
- `vendor/mathjax/`：MathJax 离线公式依赖，Apache 2.0。
- 根目录 Python 模块与 `scripts/`：构建及校验程序。

## 构建与校验

在此目录运行 `python main.py --all`、`python verify.py`、`python status.py`。转换 Markdown 需要 Python 3.13、Node.js、Pandoc 和项目依赖；Pandoc 通过 `PANDOC` 环境变量或 `PATH` 查找。字体按 Windows 宋体、黑体、Times New Roman 与 Consolas 配置。

构建缓存和逐章 PDF 由仓库 `.gitignore` 排除。来源书目元数据保留在 `source/library/`。

## 公开版审阅与实测记录

当前公开稿由 GPT 辅助审阅，尚未经过逐条人工审校。公式经构建流程渲染，最近一次构建未报告 MathJax 渲染失败。`verify.py` 对章节 PDF 与合订本进行结构检查，结果 `problems=0`；另提示 6 个正文较短页用于排版复核。`review/reproductions/` 中 7 个复现实验脚本已运行完成。以上检查有明确范围，不表示全书每条公式和代码片段均经过独立证明或执行。