# CH95-FORM-002：单条序列的 token KL 之和是无偏还是高方差？

## 问题

`content/ch13prep.md` 第 117 行（2026-10-20 22:12 版）写：

> 其一，**期望**意义上的相等，不保证**单条样本**上的估计相等：用一条采样序列算出的
> token KL 之和，是对序列 KL 的一个有偏（因为前缀分布来自 \(\pi_\theta\) 而非
> \(\pi_{\text{ref}}\)）或至少高方差的估计。

同一节第 100 行还写：逐 token 扣 KL 之后"整条序列的累计惩罚**恰好等于**序列 KL"。

这两处都把"期望相等"说成了"逐条不等/有偏"。本节给出：**按式 (13.7) 的采样方式，
单条序列的 token KL 之和是序列 KL 的无偏估计**；错的是"有偏"，对的是"高方差"；
第 100 行"恰好等于"应改为"期望等于"。

## 记号

序列概率按式 (13.1) 分解：\(\pi_\theta(y\mid x)=\prod_{t=1}^{T}\pi_\theta(y_t\mid x,y_{<t})\)，
\(\pi_{\text{ref}}\) 同理。逐位置 KL 记作
\(\kappa_t=\kappa_t(x,y_{<t})=D_{\mathrm{KL}}\!\bigl(\pi_\theta(\cdot\mid x,y_{<t})\,\big\|\,\pi_{\text{ref}}(\cdot\mid x,y_{<t})\bigr)\)
（式 (13.6)）。对一条采样序列 \(y=(y_1,\dots,y_T)\)，逐 token 的对数比记
\(\ell_t=\log\frac{\pi_\theta(y_t\mid x,y_{<t})}{\pi_{\text{ref}}(y_t\mid x,y_{<t})}\)，
单样本估计量 \(\hat E(y)=\sum_{t=1}^{T}\ell_t\)。

## 第一步：链式分解（式 (13.7)）

对 \(y\sim\pi_\theta(\cdot\mid x)\)，

\[
\mathbb{E}_{y\sim\pi_\theta}\Bigl[\log\frac{\pi_\theta(y\mid x)}{\pi_{\text{ref}}(y\mid x)}\Bigr]
=\mathbb{E}_{y\sim\pi_\theta}\Bigl[\sum_{t=1}^{T}\ell_t\Bigr]
\]

而左端按 KL 定义就是 \(D_{\mathrm{KL}}\!\bigl(\pi_\theta(\cdot\mid x)\,\big\|\,\pi_{\text{ref}}(\cdot\mid x)\bigr)\)。
于是

\[
D_{\mathrm{KL}}\bigl(\pi_\theta(\cdot\mid x)\,\big\|\,\pi_{\text{ref}}(\cdot\mid x)\bigr)
=\sum_{t=1}^{T}\mathbb{E}_{y_{<t}\sim\pi_\theta}\bigl[\kappa_t(x,y_{<t})\bigr],
\]

即式 (13.7)。这一步只用自回归分解，没有引入近似，正文标 `[精确]` 是对的。

## 第二步：单样本估计无偏

\[
\mathbb{E}_{y\sim\pi_\theta}\bigl[\hat E(y)\bigr]
=\mathbb{E}\Bigl[\sum_{t=1}^{T}\ell_t\Bigr]
=\sum_{t=1}^{T}\mathbb{E}_{y_{<t}\sim\pi_\theta}\Bigl[\mathbb{E}_{y_t\sim\pi_\theta(\cdot\mid x,y_{<t})}[\ell_t]\Bigr]
=\sum_{t=1}^{T}\mathbb{E}_{y_{<t}\sim\pi_\theta}[\kappa_t]
=D_{\mathrm{KL}}(\pi_\theta\|\pi_{\text{ref}}).
\]

内层期望 \(\mathbb{E}_{y_t\sim\pi_\theta}[\ell_t]\) 恰好是 \(\kappa_t\)：
\(D_{\mathrm{KL}}(p\|q)=\mathbb{E}_{a\sim p}[\log p(a)-\log q(a)]\)。

**关键点**：前缀必须从 \(\pi_\theta\) 抽，才使内层期望落在 \(\pi_\theta\) 上、从而等于 \(\kappa_t\)。
正文把"前缀分布来自 \(\pi_\theta\) 而非 \(\pi_{\text{ref}}\)"当成偏差来源，方向恰好反了——
若前缀改从 \(\pi_{\text{ref}}\) 抽（例如对参考策略的输出做 teacher forcing），
内层期望才变成
\(\mathbb{E}_{y_{<t}\sim\pi_{\text{ref}}}[\kappa_t]\)
而不再等于 \(\sum_t \mathbb{E}_{\pi_\theta}[\kappa_t]\)，那时才引入偏差。
所以：**off-policy 前缀是有偏的来源，on-policy 前缀是无偏的来源。**

## 第三步：真正的问题是方差

\(\hat E\) 是随机变量，其方差不是零：

\[
\operatorname{Var}(\hat E)
=\mathbb{E}\Bigl[\Bigl(\sum_{t=1}^{T}\ell_t\Bigr)^{2}\Bigr]-D_{\mathrm{KL}}^{2}
=\sum_{t=1}^{T}\operatorname{Var}_{y_{<t}}(\kappa_t)+\sum_{t=1}^{T}\mathbb{E}_{y_{<t}}\bigl[\operatorname{Var}_{y_t}(\ell_t)\bigr]+2\sum_{s<t}\operatorname{Cov}(\ell_s,\ell_t).
\]

在 \(T\) 项都同阶时，方差随 \(T\) 线性增长（\(\Theta(T)\)），标准差随 \(\sqrt T\) 增长；
用一条序列估计长回答的 KL，相对误差不随长度消失。这才是"单条样本不可靠"的正确说法，
也是工程上改用 k3 估计器的动机——k3 逐 token 非负、方差更小，且同样无偏：

\[
k_3=\frac{\pi_{\text{ref}}}{\pi_\theta}-\log\frac{\pi_{\text{ref}}}{\pi_\theta}-1,
\qquad
\mathbb{E}_{\pi_\theta}[k_3]=\mathbb{E}_{\pi_\theta}\Bigl[\frac{q}{p}\Bigr]-\mathbb{E}_{\pi_\theta}\Bigl[\log\frac{q}{p}\Bigr]-1=1-\bigl(-D_{\mathrm{KL}}(p\|q)\bigr)-1=D_{\mathrm{KL}}.
\]

（第 10 章式 (10.8)、第 11 章式 (11.11) 用的就是它，DeepSeekMath 式 (4) 明确称其为
"unbiased estimator (Schulman, 2020)"。）

## 第四条：第 100 行的"恰好等于"

逐 token 扣除 \(\beta_{KL}\ell_t\) 后，整条序列的累计惩罚是
\(\beta_{KL}\sum_t \ell_t=\beta_{KL}\log\frac{\pi_\theta(y\mid x)}{\pi_{\text{ref}}(y\mid x)}\)，
它是**一个样本上的对数比**，不是 \(D_{\mathrm{KL}}\)。只有当整个训练分布下取期望，
它才等于 \(\beta_{KL}D_{\mathrm{KL}}\)。所以"恰好等于序列 KL"应写成
"其期望等于序列 KL"，否则与第 117 行的错误同源。

## 结论与建议改法

1. 第 117 行"有偏……或至少高方差"→ 改为"**无偏但高方差**：前缀从 \(\pi_\theta\) 抽正是无偏的原因；
   若改用 \(\pi_{\text{ref}}\) 前缀则会引入偏差。方差随序列长度线性增长，这是改用 k3 估计器的动机"。
2. 第 100 行"恰好等于序列 KL"→ 改为"其期望等于序列 KL（式 (13.7)）"。
3. 保持 (13.6)/(13.7) 的 `[精确]` 标注不变：链式分解本身没有问题，问题只在对估计量的描述。
