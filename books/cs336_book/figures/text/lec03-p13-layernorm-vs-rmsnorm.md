# 图政策示例 1：PPT 页 → 文字（`lecture_03.pdf` p13）

原页是「LayerNorm vs RMSNorm」的左右对照幻灯片，只有两行说明文字与两个公式。这种页面的截图进教材有三个问题：分辨率低、公式不可检索、左右两栏在窄版面上会挤成一行。因此按政策 `text` 处理：把版面改写成表格，内容不外扩。

| | LayerNorm（原版 Transformer） | RMSNorm（多数现代模型） |
| --- | --- | --- |
| 归一化范围 | 对 $d_{\text{model}}$ 维做**减去均值、除以标准差** | **不减均值、不加 bias**，只除以均方根 |
| 公式 | $\mathrm{LN}(x)=\dfrac{x-\mu}{\sqrt{\sigma^{2}+\varepsilon}}\odot\gamma+\beta$ | $\mathrm{RMSNorm}(x)=\dfrac{x}{\sqrt{\frac{1}{d}\sum_{i}x_{i}^{2}+\varepsilon}}\odot\gamma$ |
| 代表模型（原页列出） | GPT-3 / GPT-2 / GPT-1、OPT、GPT-J、BLOOM | LLaMA 系列、PaLM、Chinchilla、T5 |

> 排版说明：原页的 RMSNorm 公式在 PDF 里是图片化文字（文字层为乱序的 `𝑦= 𝑥 𝑥 2 2 + 𝜀 ∗𝛾`），上表按数学含义重新排版，**公式本身与原页一致**，未增补推导。
>
> 后续（原页 p14–p16）才讨论「为什么用 RMSNorm」：少一次均值计算、少一组 bias 参数，但真正的收益来自数据搬运而不是 FLOPs——这段属于正文叙述，不需要配图。

- 源文件：`sources/official_course/lectures@<commit>/lecture_03.pdf`，第 13 页
- 政策：`text`（纯文字/对照页 → 表格转写，不保留截图）
- 溯源：`evidence/chapter03/U04-*.yaml`
