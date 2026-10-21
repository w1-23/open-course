# CH11-GRPO-001 独立复核

- 复核者：author-ch04（独立复核；未参与该卡写作，仅依据工作区原始文献与自行推导）
- 复核日期：2026-10-20
- 对象：`review/cards/CH11-GRPO-001.yaml`、`review/derivations/CH11-GRPO-001.md`、`review/reproductions/CH11-GRPO-001_mc.py`
- 复核方式：逐页打开 `source/pages/` 原文对照；独立重算（不参考推导文件的中间步骤）；实跑复现脚本；查 `content/ch11.md` 原文落点

## 结论

**PASS_WITH_FIXES**：卡片的四条实质主张（c1–c4）都成立，我独立推出与复现出同样的 \((1-1/G)\) 缩放，并确认"再除以 \(s_r\) 后不再等于该缩放"；但**引文元数据有确证错误、`current_text.excerpt` 不是原文、复现数字依赖未声明的约定、`planned_fix` 指向不存在的小节**——这四项会让下游按卡施工时改错位置或误判证据等级，必须先修。

## 逐项核对表

| claim | 卡片陈述 | 我的核对结果 | 依据（文件:页/行 或 推导步骤） |
|:--|:--|:--|:--|
| c1 | 基线恒等式要求 \(b\) 不依赖被采样的动作/输出 | **成立**。但卡片 `sources[0].printed_page` 标成 §13.4 是**错的**（引文在 §13.8），note 说"紧接着"也**不成立**（隔 8 页） | 引文本身：`source/pages/RLbook2020/p0359.txt`（§13.8 Summary，印刷页 337）；"不随动作变化"的原话在 `p0351.txt`（§13.4，印刷页 329）："The baseline can be any function, even a random variable, as long as it does not vary with a" |
| c2 | 组均值基线把期望梯度精确缩放 \((1-1/G)\)，不是零效应 | **成立**（我的推导见下；脚本误差 ≤1.7e-16）。但**前提不完整**：推导 §1 写的是 \(o_i\sim\pi_{\text{old}}\)，而恒等式里 \(\mathbb E[\nabla\log\pi_\theta]=0\) 要求 \(o_i\sim\pi_\theta\) | 推导步骤见"细节 B"；`review/derivations/CH11-GRPO-001.md:14`（"从旧策略采样"）与 `:38`（用 \(\nabla\sum_o\pi=0\)）冲突 |
| c3 | 有限 \(G\) 下归一化优势不是无偏优势，而是"重加权版本" | **成立**。但证据取自 **Figure 4 的题注**而非正文；卡片给 `level: S`，推导却自称"P2 研究材料，只进研究框，不作定理依据"——分级自相矛盾 | `source/pages/2503.20783_dr-grpo/p0006.txt`（Figure 4 caption："the effective advantage of GRPO â_{i,t} is equivalent to a reweighted version of the unbiased advantage Ã_{i,t}=R(q,o_i)−mean(R)"；正文同页有 Response-level length bias / Question-level difficulty bias 两条命名） |
| c4 | 官方实现按组均值与组标准差归一化整条输出奖励，并广播到所有 token | **成立**，逐字命中 | `source/pages/2402.03300_deepseekmath-grpo/p0014.txt`（§4.1.2：normalized by subtracting the group average and dividing by the group standard deviation … sets the advantages Â_{i,t} of all tokens … i.e. Â_{i,t}=r̃_i=(r_i−mean(r))/std(r)）；Algorithm 1 第 9 行与第 11 行（Equation 21）同页 |
| —（current_text） | excerpt："其中 r̄ 是同一提示下 G 个输出的平均奖励，作为与当前动作无关的基线，减去它不改变期望梯度……" | **不成立**：这句在 `content/ch11.md` 里**不存在**（全文检索无"与当前动作无关"字样）。实际错误陈述是另一种写法 | `content/ch11.md:169`："只要 b 不依赖 o_i。式 (11.12) 是习题 1 要证的结论，它说明'减组均值'不是启发式，而是标准的方差缩减；组均值恰好是一个不需要额外网络的基线。减基线只改变方差" |

## 细节 A：引文核对（逐页）

1. **RLbook2020 p359**：引文逐字存在——"Adding a state-value function as a baseline reduces REINFORCE's variance without introducing bias." 该页页眉为 `13.8. Summary / 337`，故**印刷页是 337、小节是 §13.8**；卡片 `printed_page: "§13.4"` 错误（§13.4 在 `p0351.txt`，印刷页 329）。
2. **RLbook2020 p351**：c1 真正需要的那句在 §13.4——"The baseline can be any function, even a random variable, as long as it does not vary with a; … \(\sum_a b(s)\nabla\pi=\dots=0\)"。卡片 note 写"原书紧接着说明 b(s) 必须只依赖状态"不准确：p359 紧接着讲的是 actor–critic，条件句在 8 页之前，且原文措辞是"不随动作变化"（还允许基线是随机变量）。
3. **2402.03300 p14**：正文命中，但卡片引文**丢了 \(\hat A\) 的帽号**（写成 `A_i,t`），且删掉了 "i.e., \(\hat A_{i,t}=\tilde r_i=(r_i-\text{mean}(r))/\text{std}(r)\)" 这一段而**没有省略号**。这是"引文被改写"，按复核规则应记为需修。
4. **2503.20783 p6**：句子在 **Figure 4 题注**里，不是正文；卡片未注明出处位置。题注里的符号是 \(\hat a_{i,t}\)（小写 a）与 \(\tilde A_{i,t}\)，卡片写作 `â_i,t`、`Ã_i,t`，属于同一句的符号转写，可接受但应注明"题注"。

## 细节 B：推导重算（我的写法，与卡片的中间步骤无关）

设固定 prompt \(q\)，\(o_1,\dots,o_G\sim\pi_\theta(\cdot\mid q)\) **i.i.d.**（on-policy），\(r_i=r(q,o_i)\) 是确定性打分，\(\bar r=\frac1G\sum_j r_j\)（**含** \(r_i\)），记 \(f_i=\nabla_\theta\log\pi_\theta(o_i\mid q)\)、\(g_i=\mathbb E[r_if_i]\)。

\[
\mathbb E\bigl[(r_i-\bar r)f_i\bigr]
=\mathbb E[r_if_i]-\frac1G\sum_{j=1}^{G}\mathbb E[r_jf_i].
\]

- \(j=i\)：\(\mathbb E[r_if_i]=g_i\)。
- \(j\ne i\)：\(r_j\) 与 \(o_i\) 独立，且 \(\mathbb E_{\pi_\theta}[f_i]=\sum_o\pi_\theta(o)\nabla\log\pi_\theta(o)=\nabla\sum_o\pi_\theta(o)=0\)，故该项为 \(\mathbb E[r_j]\cdot 0=0\)。

所以

\[
\mathbb E\bigl[(r_i-\bar r)f_i\bigr]=\Bigl(1-\frac1G\Bigr)g_i .
\]

**系数、求和范围、\(i\ne j\) 项为零的理由都正确**；G=1 时退化为 0，与"单样本的组内相对优势恒为 0"一致。符号与"方向不变"（\(1-1/G>0\)）也正确。

**必须补的前提**：上式用到了 \(\mathbb E_{\pi_\theta}[f_i]=0\)。推导 §1 却写"从旧策略采样 \(o_i\sim\pi_{\text{old}}\)"。当 \(\pi_{\text{old}}\ne\pi_\theta\) 时 \(\mathbb E_{\pi_{\text{old}}}[f_i]=\sum_a\pi_{\text{old}}(a)(e_a-\pi_\theta)=\pi_{\text{old}}-\pi_\theta\ne0\)（取 \(\pi_\theta=[.5,.3,.2]\)、\(\pi_{\text{old}}=[.2,.5,.3]\) 即得 \([.3,-.2,-.1]\) 的非零向量），此时 \(j\ne i\) 项不为零：
\[
\mathbb E\bigl[(r_i-\bar r)f_i\bigr]=\Bigl(1-\frac1G\Bigr)\mathbb E_{\pi_{\text{old}}}[r_if_i]-\frac{G-1}{G}\mathbb E_{\pi_{\text{old}}}[r]\bigl(\pi_{\text{old}}-\pi_\theta\bigr).
\]
因此 \((1-1/G)\) 是 **on-policy（或单步、\(\pi_{\text{old}}=\pi_\theta\)）** 的精确结论；GRPO 用重要性比率时它是"一阶近似"。卡片 c2 的前提"组内独立同分布、G≥2"应改写为"on-policy（\(\pi_{\text{old}}=\pi_\theta\)）、组内 iid"。

## 细节 C：数值复现（实跑结果）

`python review/reproductions/CH11-GRPO-001_mc.py` 输出（与卡片 `reproduction_result` 完全一致）：

| G | ‖B‖/‖A‖ | 1−1/G | 相对误差 | ‖C‖/‖A‖ | 有效组质量 |
|:--|:--|:--|:--|:--|:--|
| 2 | 0.500000 | 0.5 | 0.00e+00 | 0.696684 | 0.6200 |
| 3 | 0.666667 | 0.6667 | 1.67e-16 | 0.951592 | 0.8400 |
| 5 | 0.800000 | 0.8 | 1.39e-16 | 1.124487 | 0.9660 |

G=3 的差向量：`C − (1−1/G)A = [0.108852, −0.067279, −0.041573]`，与卡片一致。

**脚本审查**：

1. **确实穷举**：`itertools.product(range(K), repeat=G)`，对每个元组按 \(\prod\pi\) 加权求和，\(\sum p=1\)，因此算的是**精确期望**而非单次采样。元组数为 \(K^G\)（3²=9、3³=27、3⁵=243）——卡片 `reproduction_result.setup` 写的"穷举全部 **G^G** 组样本"是**记号错误**。
2. **无随机性**：纯枚举，不存在"种子未固定"问题。
3. **只算 i=0 是合法的**：组内可交换（iid），各 \(i\) 的边缘期望相同。
4. **\(s_r=0\) 的处理需要声明**：脚本 `if s > 1e-12` 跳过全同奖励组，即令其贡献为 0——这与实现中"组内方差为 0 → 优势置 0"的惯例等价（因为此时分子恒为 0）。但卡片没有写这个约定，而被跳过的概率质量是 0.62/0.84/0.966（G=2/3/5）。**若改成"剔除后条件期望"（重归一化），C 变为约 1.1237 / 1.1328 / 1.1639**（我用 C÷n_valid 估算），数值差异很大；定性结论（≠(1−1/G)、随 G 上升、越过 1）不变，但卡片把 C 的数字当作"实测期望"而不提约定，复现性上不够严谨。
5. **‖C‖/‖A‖ 不是"缩放倍数"**：除以 \(s_r\) 后向量方向也变了，范数比只是启发式指标；真正的证据是 `C−(1−1/G)A` 与 A 不共线（G=3 的差向量即可证）。
6. 死代码：`return B / 1.0`、`if p == 0.0: continue`（π 全正，永不触发）——不影响结果，可清理。

## 细节 D：正文核对（错误陈述的真实落点）

`content/ch11.md` 中把 \(\bar r\) 当作"动作无关基线"的地方共 **4 处**，卡片只覆盖了其中 1 处：

| 行号 | 原文 | 问题 |
|:--|:--|:--|
| 10 | "组内标准化作为基线的合法性是 [精确] 的（任何与动作无关的基线都不改变期望梯度）" | 把 \(\bar r\) 归入"与动作无关的基线"，与 c2 冲突 |
| 162–171 | "只要 \(b\) 不依赖 \(o_i\)。式 (11.12) 是习题 1 要证的结论，它说明'减组均值'不是启发式……减基线只改变方差" | ①(11.12) 本身对（b 与 \(o_i\) 无关时成立）；②从它推出"减组均值合法"是**无效推理**；③"只改变方差"错 |
| 370 | "GRPO 用同一提示的 \(G\) 条样本互为基线：组内标准化（式 (11.7)）减组均值是合法的方差缩减（式 (11.12)）……" | 同错，且"合法的方差缩减"把 \((1-1/G)\) 缩放漏掉 |
| 428 | 习题 1："再说明为什么'组均值 \(\bar r\) 作为基线'是合法的" | 题目要求证明一个假命题，需重写为"说明为什么不能主张无偏" |

另外 414 行关键公式"减基线不改变期望梯度，式 (11.12)"本身对，但紧接着若被用来支持 \(\bar r\) 需加限定。

## 过度断言与口径问题

1. 卡片 summary（第 6–10 行）把正文概括为"把 \(\bar r\) 说成'与当前动作无关的基线'，据此宣称'减去组均值不改变期望梯度'"——**结论方向对，但不是原话**；`excerpt` 字段必须放原文，概括应写在 summary 并标注"转述"。
2. c2 的"精确"只在 on-policy 一步成立（见细节 B），卡片未写前提。
3. c3 的"重加权版本"是 Dr.GRPO 题注的转述；把它当"独立分析"可以，但**不能当定理依据**，与卡片 `level: S` 冲突（按 `source/source_map.yaml` 头注释，S = 原始论文正式版/公认教材，是"定理与定义的唯一依据"）。
4. `reproduction_result.conclusion` 说"比值随 G 单调上升并越过 1"——依赖细节 C-4 的 \(s_r=0\) 约定；建议同时报告条件期望版本，或明确写"按'方差为 0 的组优势记 0'的惯例"。

## 必须修改项

1. **`review/cards/CH11-GRPO-001.yaml:15-17`（`current_text.excerpt`）**：替换为逐字原文，例如第 169 行"只要 \(b\) 不依赖 \(o_i\)。式 (11.12) 是习题 1 要证的结论，它说明'减组均值'不是启发式，而是标准的方差缩减；组均值恰好是一个不需要额外网络的基线。减基线只改变方差，这正是 GRPO 想省掉的 critic 的替代品。"若想保留概括，另设 `paraphrase:` 字段。
2. **同文件 `current_text.lines`**：由 `"162-171"` 扩为 `"10, 162-171, 370, 414, 428"`（四处落点，见细节 D），否则施工只改一段、其余三处仍留错。
3. **同文件 `sources[0].printed_page`（第 24 行）**：`"§13.4"` → `"§13.8（印刷页 337）"`；`sources[0].note`（第 28 行）把"原书紧接着说明"改为"§13.4（pdf p.351，印刷页 329）另有原话：*The baseline can be any function, even a random variable, as long as it does not vary with a*"，并把 c1 的证据同时指向 p.351 与 p.359。
4. **同文件 `sources[1].quote`（第 34-38 行）**：补回 \(\hat A_{i,t}\) 的帽号；在 "…as the normalized reward" 后加 "…" 或补上 "i.e., \(\hat A_{i,t}=\tilde r_i=(r_i-\mathrm{mean}(r))/\mathrm{std}(r)\)"，不得省略而不标记。
5. **同文件 `sources[2]`（第 41 行 `level: S`、第 45-49 行 quote）**：①`level` 与 `review/derivations/CH11-GRPO-001.md:105` 的"P2 研究材料，不作定理依据"对齐；②注明该句出自 **Figure 4 题注**（同页正文另有 Response-level length bias / Question-level difficulty bias 两条命名，也可一并引）。
6. **同文件 `reproduction_result.setup`（第 58 行）**："穷举全部 **G^G** 组样本" → "穷举全部 **K^G** 组样本（K=3 个动作，G=2/3/5 时分别为 9/27/243 组）"。
7. **同文件 `reproduction_result.claim_3_after_std`（第 63-66 行）**：补一行约定说明——"\(s_r=0\) 的组按惯例记 \(\hat A=0\)（脚本跳过、贡献 0）；被跳过概率质量 G=2/3/5 为 0.62/0.84/0.966；若改为条件期望，C≈1.1237/1.1328/1.1639"。并把"比值越过 1"与"向量非共线"分开陈述（后者才是主证据）。
8. **同文件 `claims.c2.evidence`（第 79 行）**：补前提"on-policy（\(\pi_{\text{old}}=\pi_\theta\)）"。**`review/derivations/CH11-GRPO-001.md:14-19`** 同步把"从旧策略采样"改为"从当前策略采样（on-policy，单步）"，或加一段 \(\pi_{\text{old}}\ne\pi_\theta\) 的交叉项修正（见细节 B 的第二式）。
9. **同文件 `planned_fix`（第 91-95 行）**：①第 95 行"11.6 的稳定性讨论"——`content/ch11.md` **没有 11.6**（只有 11.1–11.5，本章小结在 362 行），应改为"11.4 稳定性与工程（257–299 行）与本章小结（362 行起，含 370 行）"；②补上第 10 行（章首）、414 行（关键公式）与 428 行（习题 1）三处；③第 92 行的 (★) 建议直接写成 \(\mathbb E[(r_i-\bar r)\nabla\log\pi_\theta(o_i)]=(1-1/G)\,g_i\)，不要用"\(\bar r_{\text{indep}}\)"（读者会误以为是对另一组样本取均值）。
10. **`review/derivations/CH11-GRPO-001.md:94-96`**：文中说"取 \(G=8\)、\(r\sim\mathrm{Bernoulli}(p)\) 的玩具模型……（待写）"，与实际脚本（3 臂 bandit、确定性奖励、G=2/3/5、精确枚举）不一致；改为描述真实脚本，并删"（待写）"。

## 我无法核实的项

- **无**（三篇文献的原文页均已打开逐字核对；复现脚本已实跑；推导已独立重算）。
- 附注：卡片引用 Dr.GRPO 的"COLM 2025"会议身份，`source/pages/2503.20783_dr-grpo/p0006.txt` 页眉"Published as a conference paper at COLM 2025"可佐证 ✓，但该文的**接收/评审状态**属出版信息，不在本工作区可核范围内。
