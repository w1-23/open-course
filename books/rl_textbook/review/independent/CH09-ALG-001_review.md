# CH09-ALG-001 独立复核

- 复核者：author-ch04（独立复核；未参与该卡写作）
- 复核日期：2026-10-20
- 对象：`review/cards/CH09-ALG-001.yaml`、`review/derivations/CH09-ALG-001.md`（卡片 `reproduction_file: null`，无脚本可跑）
- 复核方式：打开 `source/pages/1609.05140_option-critic/p0003.txt`（Theorem 1/2 原文）、`p0002.txt`（\(V_\Omega,Q_\Omega\) 定义）；自己重算式 (9.3)(9.4)；对照 `content/ch09.md:64-95` 与伪代码框

## 结论

**FAIL**：c1、c2、c4 成立，但 **c3 是错的**——式 (9.4) 的符号反了：对 (9.3) 求偏导得 \(\partial Q/\partial\beta_o(s')=P(s'\mid s,o)\,\gamma\,[V(s')-Q(s',o)]\)，是书上所写 \([Q(s',o)-V(s')]\) 的相反数。因此卡片"撤回前一轮'方向错误'判断"这一动作**本身不成立，必须再撤回**；伪代码第 7 行的符号也随之为错（卡片没写这一点）。另外 c4 的 note 把"用 \(Q_\Omega(s,o)\) 替代 \(Q_U(s,\omega,a)\)"说成"可互替"，实际会让期望梯度**恒为零**，不是近似问题。

## 逐项核对表

| claim | 卡片陈述 | 我的核对结果 | 依据（文件:页/行 或 推导步骤） |
|:--|:--|:--|:--|
| c1 | 终止梯度定理中优势两项都在 \(s'\) | **成立** | `p0003.txt` Theorem 2：\(-\sum_{s',\omega}\mu_\Omega(s',\omega\mid s_1,\omega_0)\,\partial\beta_{\omega,\vartheta}(s')/\partial\vartheta\,A_\Omega(s',\omega)\)；同页 "\(A_\Omega(s',\omega)=Q_\Omega(s',\omega)-V_\Omega(s')\)" |
| c2 | 定理 2 不含显式 \(\gamma\) 乘子（\(\gamma\) 在 \(\mu_\Omega\) 内） | **成立** | 同页定理 2 公式无独立 \(\gamma\) 因子；\(\mu_\Omega(s,\omega\mid s_1,\omega_0)=\sum_{t=0}^{\infty}\gamma^t P(s_{t+1}=s,\omega_t=\omega\mid s_1,\omega_0)\)。另：同页式 (5) \(\partial U(\omega,s')/\partial\vartheta=-\partial\beta\,A_\Omega+\gamma\sum_{\omega'}\sum_{s''}P\,\partial U(\omega',s'')/\partial\vartheta\) 显示 \(\gamma\) 乘的是**递归项**，不是 \(A\) |
| c3 | 本书式 (9.4) 的 \(\partial Q/\partial\beta_o(s')=P\cdot\gamma\cdot[Q(s',o)-V(s')]\) **正确**；撤回前一轮"方向错误"的判断 | **不成立（符号错）**。正确结果是 \(P\gamma[V(s')-Q(s',o)]=-P\gamma A_\Omega(s',o)\)。书上 (9.4) 与它自己的第 76 行解释、与定理 2、与论文"负优势→提高终止概率"的文字说明**全都矛盾** | 推导见"细节 B"；`p0003.txt`："when the option choice is suboptimal …, the advantage function is negative and it drives the gradient corrections up, which increases the odds of terminating" |
| c4 | 定理 1 的权重是 \(Q_U(s,\omega,a)\)，用 \(Q_\Omega(s,o)\) 替代需要条件 | **成立**（权重确实是 \(Q_U\)）；但卡片 note 说的"可互替"条件**错**：\(Q_\Omega(s,o)\) 与采样动作 \(a\) 无关，代入后 \(\mathbb E[\nabla\log\pi_\omega(a\mid s)\,Q_\Omega]=Q_\Omega\sum_a\nabla\pi_\omega(a\mid s)=0\)，期望梯度恒为零 | `p0003.txt` Theorem 1：\(\sum_{s,\omega}\mu_\Omega(s,\omega\mid s_0,\omega_0)\sum_a\partial\pi_{\omega,\theta}(a\mid s)/\partial\theta\,Q_U(s,\omega,a)\)；`content/ch09.md:88` 第 6 行用的是 \(Q(s,o;w)\)，而 `:65` 的 \(Q(s,o)\) 是动作无关的选项价值 |
| —（summary 第 7–10 行） | "该行多写了一个 \(\gamma\) 乘子……第 6 行用 \(Q_\Omega\) 代替 \(Q_U\) 也未给条件" | 两条都对，但**漏了最要紧的符号错**；且"未给条件"应为"该替代会使梯度消失" | 同上 |

## 细节 A：原文核对（定理逐符号）

- **Theorem 1（Intra-Option Policy Gradient Theorem）**：\(\sum_{s,\omega}\mu_\Omega(s,\omega\mid s_0,\omega_0)\sum_a\frac{\partial\pi_{\omega,\theta}(a\mid s)}{\partial\theta}Q_U(s,\omega,a)\) ✓ 卡片 c4 引述正确。
- **Theorem 2（Termination Gradient Theorem）**：\(-\sum_{s',\omega}\mu_\Omega(s',\omega\mid s_1,\omega_0)\frac{\partial\beta_{\omega,\vartheta}(s')}{\partial\vartheta}A_\Omega(s',\omega)\) ✓ 卡片引文逐字命中（省略号处是 \(\mu_\Omega\) 的定义，属正常省略）。
- 同页指出 \(\mu_\Omega\) 的权重是"**shifted by one time step**"的马尔可夫链：\(\mu_\Omega(s,\omega\mid s_1,\omega_0)=\sum_t\gamma^tP(s_{t+1}=s,\omega_t=\omega\mid s_1,\omega_0)\) —— 这支持卡片"评估状态由 \(s\) 移到 \(s'\)"的判断 ✓。
- **RLbook2020 p500 引文**：逐字命中，页眉 `478 Chapter 17: Frontiers`，§17.2 文献注记 ✓（"An important limitation of these early works is that they did not treat the off-policy case…"，原文 `o↵-policy` 是连字符抽取问题）。
- `source/library/PENDING.yaml` 确有 `precup2000_between-mdps-smdps` 条目 ✓，卡片"Precup 2000 一手 PDF 未取得"的说法可核实。

## 细节 B：式 (9.4) 的符号（核心发现）

书上式 (9.3)（`content/ch09.md:65`）：

\[
Q(s,o)=\sum_{s'}P(s'\mid s,o)\Bigl[r+\gamma\bigl[(1-\beta_o(s'))Q(s',o)+\beta_o(s')V(s')\bigr]\Bigr].
\]

对 \(\beta_o(s')\) 求偏导（\(V(s')\) 与 \(Q(s',o)\) 不依赖 \(\beta_o(s')\)，求和只剩 \(s''=s'\) 一项）：

\[
\frac{\partial Q(s,o)}{\partial\beta_o(s')}
=P(s'\mid s,o)\,\gamma\,\bigl[-Q(s',o)+V(s')\bigr]
=-P(s'\mid s,o)\,\gamma\,A_\Omega(s',o).
\]

书上 (9.4)（`content/ch09.md:72`）写的是 \(+P(s'\mid s,o)\gamma[Q(s',o)-V(s')]\)，**符号相反**。

三条独立交叉验证：

1. **书上自己的文字**（`content/ch09.md:76`）："若在 \(s'\) 处'继续这个选项'比'换一个最优选项'更好（\(Q(s',o)>V(s')\)），提高终止概率会**降低**价值，梯度为负" —— 这与 \(V-Q\) 一致，与 (9.4) 的 \(Q-V\) 矛盾。**文字对、公式错**。
2. **定理 2**：\(\partial J/\partial\vartheta=-\sum\mu\,\partial\beta\,A_\Omega\)，做梯度上升是 \(\vartheta\leftarrow\vartheta-\eta\,A_\Omega\,\partial\beta\)：\(A_\Omega<0\) 时增大终止概率 ✓，与 \(V-Q\) 一致。
3. **论文原话**（`p0003.txt`）："when the option choice is suboptimal …, the advantage function is negative and it drives the gradient corrections up, which increases the odds of terminating" ✓。
4. **有限差分**：取 \(P=1,\gamma=0.9,Q(s',o)=10,V(s')=0\)，\(\beta\) 从 0.5 改到 0.6，式 (9.3) 的值从 \(r+4.5\) 变为 \(r+3.6\)，差 \(-0.9\)，即 \(\partial Q/\partial\beta=-9=\gamma(V-Q)\)；按 (9.4) 会得 \(+9\)。

**推论（对卡片而言）**：前一轮审查把 (9.4) 列为"方向错误"是**对的**；卡片 c3 的"撤回"是**误撤**，必须撤销这次撤回（台账里要记一条"撤回撤回"）。同时伪代码第 7 行 `beta <- beta + eta_beta * gamma * (Q(s,o;w) - V(s';w)) * grad_beta beta_o(s')` 的符号也错：按定理 2 的上升方向应为 \(\beta\leftarrow\beta-\eta\,A\,\partial\beta\)。有意思的是，卡片 `planned_fix` 给出的修法 `beta <- beta - eta_beta * (Q(s',o;w) - V(s';w)) * grad_beta` **符号是对的**——与它自己的 c3 直接矛盾，正好说明 c3 是错的。

## 细节 C：第 6 行用 \(Q_\Omega\) 的后果

Theorem 1 的权重是 \(Q_U(s,\omega,a)\)（原始动作级）。书上第 6 行用 \(Q(s,o;w)\)——由式 (9.3) 的用法可知这是**动作无关**的选项价值 \(Q_\Omega(s,\omega)\)。作为单样本估计量：

\[
\mathbb E_{a\sim\pi_\omega(\cdot\mid s)}\bigl[\nabla_\theta\log\pi_\omega(a\mid s)\,Q_\Omega(s,\omega)\bigr]
=Q_\Omega(s,\omega)\sum_a\nabla_\theta\pi_\omega(a\mid s)
=Q_\Omega(s,\omega)\,\nabla_\theta 1=0 .
\]

也就是说它不是"差一个条件"的近似，而是**期望梯度为零**（\(\theta\) 收不到任何信号，只剩零均值噪声）。若内部策略确定，则 \(\nabla\log\pi\equiv0\)，同样没有信号。正确写法是权重为逐动作的 \(Q_U(s,o,a)\)（卡片 `planned_fix` 第 2 条写对了），但卡片 note 里"仅在'选项内策略固定、以 state-option 对为更新单位'时可互替""若坚持用 \(Q_\Omega\)，加一句属 [近似]"这两句必须删掉，改成"用 \(Q_\Omega\) 会使该项期望为 0"。

## 细节 D：`content/ch09.md:64-95` 的差异描述是否准确

| 位置 | 书上的说法 | 我的判断 |
|:--|:--|:--|
| `:72` 式 (9.4) | \(+P\gamma[Q(s',o)-V(s')]\) | **错（符号）**，应为 \(P\gamma[V-Q]\) |
| `:76` 解释 | "\(Q>V\) → 提高终止降低价值，梯度为负" | **对**，但与 (9.4) 矛盾 |
| `:78` 多步推广 | "把单步的 \(\gamma\) 换成 \(\gamma^{\tau}\) 并对 \(\tau\) 的分布取期望" | 方向对但表述**不精确**：定理 2 的精确形式是乘 state-option 占用测度 \(\mu_\Omega\)（\(\gamma^t\) 沿轨迹加权），不是逐选项的 \(\gamma^\tau\) |
| `:88` 第 6 行 | \(\nabla\log\pi_o(a\mid s)\cdot Q(s,o;w)\) | **错**：权重与动作无关，期望梯度为 0（见细节 C）；应为 \(Q_U(s,o,a)\) |
| `:89` 第 7 行 | \(+\eta_\beta\gamma[Q(s,o)-V(s')]\nabla\beta\) | **两处错**：①\(Q(s,o)\) 与 \(Q(s',o)\) 评估状态不一致；②整体符号与定理 2 相反；③多出的 \(\gamma\) 只是步长尺度（可保留但须说明） |
| `:95` 解释 | "它用的是当前的 \(Q(s,o)\) 而不是式 (9.4) 里的 \(Q(s',o)\)……选项很短时近似相等" | **半对**：状态不一致这半句对；"选项很短时近似"也合理；但把 (9.4) 当正确基准是错的，且完全没提符号与 \(\gamma\) |

## 过度断言与口径问题

1. c3 把"由式 (9.3) 直接求偏导"当作已核，但推导文件 §1（`review/derivations/CH09-ALG-001.md:13-17`）那句"两项合并恰好得到 \([Q-V]\)"本身就是错的（合并得 \(V-Q\)）。这是**证据链的根节点错误**，不是笔误级别的排版问题。
2. summary 与 c3 都以"原审查报告将其列为方向错误，此处撤回"为前提，一旦错了，下游会按"式 (9.4) 没问题"去改伪代码，把错误固化。
3. c4 的 note（"可互替"）把"梯度消失"降级成"近似"，是过度乐观的断言。
4. 卡片 `sources[0].printed_page: "§4 Theorem 1 & 2"`：抽取文本里没有节编号（AAAI 排版），我**无法核实"§4"**；建议改为"pdf p.3 / 印刷 p.3"。

## 必须修改项

1. **`review/cards/CH09-ALG-001.yaml:66-70`（c3）**：整条重写。正确表述：式 (9.4) 的**符号错误**，应为
   \(\partial Q(s,o)/\partial\beta_o(s')=P(s'\mid s,o)\gamma[V(s')-Q(s',o)]=-P\gamma A_\Omega(s',o)\)；"方向错误"的原判断成立，**撤回无效**；`note` 里"须在台账中同时登记撤回"改为"登记撤回的撤回"。
2. **`review/derivations/CH09-ALG-001.md:13-17`**：把"两项合并恰好得到 \([Q(s',o)-V(s')]\)"改为"合并得 \(V(s')-Q(s',o)\)"，并把结论句"式 (9.4) 的系数、符号与括号内两项都是正确的"改为"符号需翻转，其余（\(P\) 因子、\(\gamma\) 因子、括号内两项）正确"；同时删去/改写第 19–20 行的"予以撤回"。
3. **同文件 `:54-58`（表格第 7 行两行）与 `:63-68`（修正后伪代码）**：补一行问题"…且符号与定理 2 相反（应为 \(-\eta\,A_\Omega\partial\beta\)）"；`:65` 的修正版符号已对，但要在备注里点明"这不是风格选择，是定理 2 的符号"。
4. **`review/cards/CH09-ALG-001.yaml:32-34`（`sources[0].note`）**：删掉"二者可互替"的说法，改为"\(Q_\Omega(s,o)\) 与采样动作无关，代入第 6 行会使期望梯度恒为 0；必须用 \(Q_U(s,o,a)\)"。
5. **同文件 `planned_fix` 第 78 条**（第 78 行）："若坚持用 \(Q_\Omega\)，加一句属 [近似]"改为"禁止用 \(Q_\Omega\) 作第 6 行权重；若要保留选项级 value，只能作为基线（减基线不改变期望）而不能再乘 \(\nabla\log\pi\)"。
6. **同文件 `summary`（第 7–11 行）**：补一句"并且该行与式 (9.4) 的符号都与定理 2 相反"；把"两项的评估状态不一致"保留。
7. **`content/ch09.md` 的施工清单（卡片 `planned_fix` 需扩写）**：`:72` 式 (9.4) 符号、`:78` 的 \(\gamma^\tau\) 表述、`:89` 第 7 行（状态 + 符号 + \(\gamma\)）、`:95` 的解释（不能再说"式 (9.4) 是对的，只是取错了状态"）。
8. **`sources[0].printed_page`（第 25 行）**：改为可核的页码（pdf p.3）。

## 我无法核实的项

- **Precup, Sutton & Singh (2000) 的一手 PDF**：`source/library/PENDING.yaml` 已列出 `precup2000_between-mdps-smdps`，按项目规定凡依赖该文的论断不得声称"依据原始论文"。本卡的 c1–c4 不依赖它，故不影响结论；但若后续要加"SMDP 收敛性"论断，须标注「待核验」。
- **卡片 `sources[0].printed_page` 的"§4"**：`p0003.txt` 中无节编号，无法核实是第 4 节；已列入必须修改项。
- 该卡 `reproduction_file: null`，其理由（"判据是逐符号对照，不需要数值实验"）我认同；但既然发现了符号问题，建议按卡片自己写的条件补一个二状态选项 MDP 的有限差分对照（这正是发现符号错的最短路径）。
