# 大语言模型从 0 构建

本目录包含当前合订正文 Markdown、打印就绪 HTML/CSS、正文插图、审校证据、出处登记和历史自有章节源稿。公开版 PDF 位于仓库根目录；康奈尔版 PDF 位于仓库 `editions/`。

## 构建

在此目录运行 `scripts/build_final.ps1`。Microsoft Edge 使用无头打印功能从 `manuscript/final/book_print.html` 与 `cornell.html` 生成 PDF。脚本默认将公开版写到仓库根目录、康奈尔版写到仓库 `editions/`；可用 `-OutputDir` 指定临时输出位置。

修改 Markdown 后需同步更新打印 HTML。CS336 官方课程讲义、作业原件和旧课程 HTML 快照未随仓库分发；引用登记保留在 `registry/`。
