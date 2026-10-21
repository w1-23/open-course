# 《大语言模型从 0 构建》工作区

本目录保存教材源稿、审校资料、构建入口和可复用图表。封面署名为“王自强整理”，公开版和康奈尔批注版均使用“_合订本”文件名；两版分别存放在最终成品目录与其 `editions/` 子目录。

## 目录

- `manuscript/final/book_print.md`：正文 Markdown 源稿。
- `manuscript/final/book_print.html`、`cornell.html`：公开版与康奈尔版的打印就绪输入。
- `manuscript/final/*.css`、`manuscript/final/images/`：版式样式与正文插图。
- `sources/`：课程与作业来源、来源登记、审校材料、归并的历史讲义来源。
- `assets/`、`figures/`、`registry/`、`evidence/`、`reports/`：素材、引用登记、证据与审校记录。
- `scripts/build_final.ps1`：通过 Microsoft Edge 构建两份合订 PDF。
- `deliverables/final/`：当前最终成品；原版存档在 `deliverables/archive/before_compiler_credit/`。

## 构建

```powershell
.\scripts\build_final.ps1
```

默认输出公开版 `deliverables/final/大语言模型从0构建_合订本.pdf`，康奈尔版输出到 `deliverables/final/editions/大语言模型从0构建_合订本.pdf`。可用 `-OutputDir` 指定输出目录。修改 Markdown 后需同步更新打印就绪 HTML；公式需在页面渲染中核验后才能作为 PDF 输入。