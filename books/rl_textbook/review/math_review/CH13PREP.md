# 预备章 数学审校（`content/ch13prep.md`，编号前缀 P）

审校人：author-ch6（独立审校）　日期：2026-10-21　结论：**reviewed**（首轮 blocked，lead 施工后复审通过）

范围：`content/ch13prep.md` 全部 9 个编号式（`\tag{P.1}`–`(P.9)`）、定义 P.1，以及它与第 10–12 章的接口一致性。判定口径见 `review/_MATH_REVIEW_PROTOCOL.md` 第 2 节：P 前提 / S 符号 / L 标签 / D 推导 / U 用途。

## 1 逐式判定

| 式号 | P | S | L | D | U | 备注 |
|:--|:-:|:-:|:-:|:-:|:-:|:--|
| P.1 | ✓ | ✓ | ✓ | ✓ | ✓ | 自回归分解是**结构性假设**而非定理，L34 已明说"第 t 步只依赖前缀"；\(y_{<t}\) 在式内已定义 |
| P.2 | ✓ | ✓ | ✓ | ✓ | ✓ | 固定数据集上的极大似然；L56 明确它不属于 RL，标签未误用 |
| P.3 | ✓ | ✓ | ✓ | ✓ | ✓ | 已用 \(\mathbb{E}_{x\sim\mathcal{D}}\) 包住两项，目标成标量；关键公式同改 |
| P.4 | ✓ | ✓ | ✓ | ✓ | ✓ | Gibbs 解逐 \(x\) 成立；\(Z(x)\) 紧随其后在 L88 定义，且写明"只依赖 \(x\)、与 \(y\) 无关、作用是把右端归一化成分布"——表述正确，没有说成"原理不可计算" |
| P.5 | ✓ | ✓ | ✓ | ✓ | ✓ | 指示函数齐全；关键公式的 \(r_t^{\text{task}}\) 已在 L207 定义为 token 级奖励（除末尾外为零），记号不再悬空 |
| P.6 | ✓ | ✓ | ✓ | ✓ | ✓ | \(\kappa_t\) 的定义式，\(\pi_\theta\) 与 \(\pi_{\text{ref}}\) 均已声明 |
| P.7 | ✓ | ✓ | ✓ | ✓ | ✓ | 序列 KL 的链式分解，[精确]；前缀分布取 \(\pi_\theta\) 是正确的（取 \(\pi_{\text{ref}}\) 才有偏）；L122 对"无偏 / 方差随长度增长"的说明与式相符 |
| P.8 | ✓ | ✓ | ✓ | ✓ | ✓ | \(s_r\)、\(\varepsilon_{\text{num}}\)、\(G\) 均在 L149 定义，\(s_r=0\) 整组跳过的约定也写了；L149 明确它不等于无偏地估出 \(A^\pi\) |
| P.9 | ✓ | ✓ | ✓ | ✓ | ✓ | 逐 token 重要性比率；L162 已点明"分子分母对应同一 token 位置"，不能拿序列级比率顶替 |

统计：9 式**全部五项 ✓**。首轮记下的三处 ✗（P.3 的 S 与 D、P.5 的 S）已由 lead 施工修掉并在本节逐条确认；没有一处曾改变本章的数学结论。

## 2 与文献比对

| 式号 | 文献 | 页 | 原文片段 | 判定 |
|:--|:--|:--|:--|:--|
| P.5 | 2203.02155_instructgpt | 9 | the prompt and response, it produces a reward determined by the reward model and ends the episode. In addition, we add a per-token KL penalty from the SFT model at each token to mitigate over- | 等价（本章把"回合末给一个标量奖励 + 每 token 一项 KL 惩罚"写成式 (P.5)，指示函数 \(\mathbb{1}\{t=\|y\|\}\) 正是"ends the episode"的书面化） |
| P.8 | 2402.03300_deepseekmath-grpo | 14 | these rewards are normalized by subtracting the group average and dividing by the group standard deviation. | 一致（式 (P.8) 的 \((r-\bar r)/(s_r+\varepsilon_{\text{num}})\) 即该句，\(\varepsilon_{\text{num}}\) 是书稿补的数值保护并已声明"不是理论定义"） |
| P.4 | 2305.18290_dpo | 15 | Note that the partition function is a function of only x and the reference policy πref, but does not depend on the policy π. | 等价（本章 L88 的表述与原文逐字对应，且补了"巨大输出空间上通常难以直接精确求和"这一实现性说明，方向正确） |
| P.3 | 2305.18290_dpo | 4 | it is straightforward to show that the optimal solution to the KL-constrained reward maximization objective in Eq. 3 takes the form | 不一致处仅在**外层期望**：原文 Eq. 3 是 \(\mathbb{E}_{x\sim\mathcal{D}}\) 包住整个括号，本章 (P.3) 只包住第一项（见第 3 节缺陷 1） |

## 3 缺陷清单

首轮列 4 条，**全部已施工**，逐条确认如下（行号为施工后的当前行号）：

1. 式 (P.3) 缺外层期望 → 已改为 \(\max_{\pi_\theta}\mathbb{E}_{x\sim\mathcal{D}}\bigl[\mathbb{E}_{y\sim\pi_\theta(\cdot\mid x)}[r(x,y)]-\beta_{KL}D_{KL}(\pi_\theta(\cdot\mid x)\|\pi_{\mathrm{ref}}(\cdot\mid x))\bigr]\)（L75-76），关键公式 L198 同步包进 \(\mathbb{E}_{x\sim\mathcal{D}}\)。目标现在是标量，(P.4) 可由它按上下文分解得到。**确认修复**。
2. L105「累计惩罚恰好等于序列 KL」→ 已改为「在**期望意义下**等于序列 KL」（L105），与同节 L122 的"无偏/方差"说明一致。**确认修复**。
3. 注框与第 0 章口径冲突 → 已改为「读成『温度为 \(\beta_{KL}\) 的 softmax』**不算错**，但容易把 \(\beta_{KL}\) 与采样温度混为一谈……\(1/\beta_{KL}\) 才叫逆温度」（L93），与 `content/ch00.md:145`「\(\beta_{KL}\) 本身是这一族的温度」相容。**确认修复**。
4. 关键公式用未定义的 \(r_t^{\text{task}}\) → 已在 L207 补定义："除末尾 \(t=|y|\) 之外都为零，末尾取值等于整条序列的 \(r(x,y)\)"。记号不再悬空。**确认修复**。

仍存两条**不影响判定**的写法建议（未计入缺陷）：

- L105 的括注"逐点相等只在每条轨迹上成立，取期望后才是 KL"表述略绕：真正逐条轨迹成立的是"累计惩罚等于 \(\beta_{KL}\log\frac{\pi_\theta(y\mid x)}{\pi_{\mathrm{ref}}(y\mid x)}\)"，不是"等于 KL"。可改为"单条轨迹上它等于对数比之和，取期望才是 KL"。
- 关键公式（L204）写 \(\mathbb{1}\{t=|y|\}\,r_t^{\text{task}}\)，而正文 (P.5)（L99）写 \(\mathbb{1}\{t=|y|\}\,r^{\text{task}}(x,y)\)。两者数值等价（\(r_t^{\text{task}}\) 本身已按末尾置零，再乘指示函数是双重屏蔽），但同一章出现两个记号，建议统一为一个。

## 4 无法核实项

- `content/ch13prep.md:103` 的"工程上常把最后一步的 token KL 换成 k3 估计器 \(\log(\pi_{\mathrm{ref}}/\pi_\theta)\) 的无偏形式"：k3 的正确形式是 \(\pi_{\mathrm{ref}}/\pi_\theta-\log(\pi_{\mathrm{ref}}/\pi_\theta)-1\)（非负、无偏），本章只写了其中的对数项。DeepSeekMath p.14 只写"the following unbiased estimator"，没有给出式子，无法逐字核对；建议至少写成 \(\hat D_{KL}=\pi_{\mathrm{ref}}/\pi_\theta-\log(\pi_{\mathrm{ref}}/\pi_\theta)-1\)，或明说"这里只写对数项，完整形式见第 10 章 (10.8)"。未计入缺陷。
- 本章没有编号式的部分（三个模型的角色、两种 KL 位置、奖励四类来源）属接口约定，不在逐式判定范围内，但已在第 5 节按 lead 给的核对点逐条核对，未发现与第 10–12 章冲突之处。

## 5 接口一致性核对（lead 指定的七个点）

| 核对点 | 本章位置 | 判定 |
|:--|:--|:--|
| \(\pi_\theta/\pi_{\mathrm{ref}}/\pi_{\text{old}}\) 三个角色 | L60-68 | ✓ 分工、混用的两种后果、\(\pi_{\text{old}}\) 是数据复用产物，三处都写对了；与第 10 章一致 |
| KL 进奖励还是进损失 | L96-105 | ✓ "折进奖励则进入优势估计，写进损失则不参与优势"的分野正确 |
| 序列 KL 与逐 token KL 的链式关系 | (P.6)(P.7)、L122 | ✓ 分解式正确；无偏/方差的因果方向已对（这是 `CH95-FORM-002` 修过的地方） |
| \(\beta_{KL}\) 系数与 \(1/\beta_{KL}\) 逆温度 | L90、L92-94 | ✓ L90 与注框（L93）已一致，且与第 0 章 L145 相容 |
| 序列奖励广播到 token | L142-153、(P.8) | ✓ 指示函数、粗信用分配的代价、\(\hat A\) 不是 \(A^\pi\) 的限定齐全 |
| \(\hat A_i\) 是相对奖励 | L149、L162 | ✓ 明写"不是学出来的 \(A^\pi(s,a)\)"，并说明 \((1-1/G)\) 缩放 |
| \(Z(x)\) 的表述 | L88 | ✓ "只依赖 \(x\)、与 \(y\) 无关……在巨大输出空间上通常难以直接精确求和"——不是"原理不可计算"，方向正确 |
