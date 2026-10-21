# 开源课程与教材合集

三本教材的合订版 PDF 放在仓库根目录，便于直接阅读和下载。书稿源文件、图表、实验与构建材料位于 `books/`。

## 教材

1. **递归自我改进：概念、方法与证据** — [下载合订版 PDF](./递归自我改进_合订本.pdf)（86 页）。源稿与实验：[`books/rsi_book/`](./books/rsi_book/)；构建说明见该目录 README。
2. **强化学习：从 Bandit 到 RLHF、RLVR 与 Agentic RL** — [下载合订版 PDF](./强化学习教材_合订本.pdf)（289 页）。源稿与审校材料：[`books/rl_textbook/`](./books/rl_textbook/)；构建说明见该目录 README。
3. **大语言模型从 0 构建** — [公开版 PDF](./大语言模型从0构建-王自强_公开版.pdf)（143 页）。源稿与版式文件：[`books/cs336_book/`](./books/cs336_book/)；[康奈尔批注版](./editions/大语言模型从0构建-王自强_康奈尔批注版.pdf)（153 页）。

## 复现构建

各书在自己的目录中提供构建入口。项目使用 Python、Pandoc、PyMuPDF、MathJax 和 Microsoft Edge 等工具；版本与字体要求见各自 README。构建生成的逐章 PDF、缓存和临时文件由 `.gitignore` 排除，根目录 PDF 是公开发行版。

## 许可

- 原创书稿与原创图表：CC BY-NC-SA 4.0，见 [`LICENSE`](./LICENSE)。
- 项目代码：MIT，见 [`LICENSE-CODE`](./LICENSE-CODE)。
- MathJax 与第三方图像等材料遵循各自许可，不受上述许可证自动覆盖；见 [`THIRD_PARTY_NOTICES.md`](./THIRD_PARTY_NOTICES.md)。
- 仓库仅保留第三方材料的书目信息与链接，不分发论文和教材原文 PDF。
