# 第 8 章证据化审计：八条高风险断言的裁定记录

审计对象：`content/ch08.md`（477 行，21 页）。审计方式：逐条对照本库一手 PDF，页码为
**PDF 物理页**（`source/library/<key>/meta.yaml` 的 `pages` 范围）。本文件记录"无误"与
"无法核实"的条目；"有问题"的条目不在这里重复，见 `review/cards/CH08-*.yaml`。

| # | 断言 | 裁定 | 证据位置 |
|---|---|---|---|
| 1 | 离线 RL 与"off-policy 可继续采样"的区分 / 覆盖假设是否可检验 | **无误** | `2005.01643_offline-rl-tutorial` p.2、p.18 |
| 2 | CQL 正则项符号与方向、α 的作用与量纲 | **符号无误**（α 与定理条件另有卡） | `2006.04779_cql` p.3 Eq (2)、p.4 Eq (4) |
| 3 | IQL 的 expectile 是否被误称"τ 分位数" | **有问题 → CH08-ALG-001** | `2110.06169_iql` p.4、p.5 |
| 4 | BCQ 是否被写成"完全不能取新动作" | **措辞有问题 → CH08-ALG-002** | `1812.02900_bcq` p.6 |
| 5 | DAgger 是否被写成"数据增强" | **无误（来源已补齐，见下 §5）** | `1011.0686_dagger` p.3、p.4 |
| 6 | DT 是否被写成"离线 RL 新算法" | **无误** | `2106.01345_decision-transformer` p.1 |
| 7 | IPS 是否被写成"无偏且可用" | **不完整 → CH08-ALG-003** | `RLbook2020` p.127、p.128 |
| 8 | 是否有"某算法在所有任务上最好"的排名断言 | **无误（无此类断言）** | 全文检索 |
| 附 | 定理 8.2 证明梗概的求和算术 | **有问题 → CH08-DER-001** | 推导 `CH08-DER-001.md` |

## 1 离线设定与覆盖假设（无误）

正文第 21 行（定义 8.1）明确"训练期间不允许调用环境，也不允许向专家查询新状态上的动作"，
第 24 行明说与第 4 章离策略学习不同（"那里可以继续采样修正"）；覆盖写成
\(\operatorname{supp}\pi\subseteq\operatorname{supp}\mu\)（第 35 行），松弛成集中系数
\(C_{\pi,\mu}\)（式 8.1），第 45 行承认它"能否被估计……构成循环，工程上只做定性检查"。

`2005.01643_offline-rl-tutorial` p.2 的三分法把这一点写得更清楚：

> In the classic off-policy setting (b), the agent's experience is appended to a data buffer … and each new policy πk collects additional data … In contrast, offline reinforcement learning employs a dataset D collected by some (potentially unknown) behavior policy πβ. The dataset is collected once, and is not altered during training. The training process does not interact with the MDP at all, and the policy is only deployed after being fully trained.

同页还有一句正好对应正文第 24 行：

> many commonly used reinforcement learning methods can learn from off-policy data, but such methods often cannot learn effectively from entire offline data, without any additional on-policy interaction.

关于"覆盖假设是不是可检验的条件"，p.18 的表述与正文第 45 行的谨慎态度一致：

> This bound is very loose in practice, but nonetheless suggests that the effects of state distribution shift can potentially be mitigated by bounding how much the learned policy can deviate from the behavior policy that collected the offline training data.

**未改动建议**：仅可加一句"支撑集关系是测度为零的集合条件，有限样本下无法直接检验，只能
用数据是否覆盖策略实际访问状态做定性检查"——这已经在第 45 行说了，故判无误。

## 2 CQL 的符号与方向（符号无误）

`2006.04779_cql` p.3 Eq (2)：

> arg min Q α · (Es∼D,a∼µ(a|s) [Q(s, a)] −Es∼D,a∼ˆπβ(a|s) [Q(s, a)]) + 1/2 Es,a,s′∼D [(Q(s, a) −ˆBπ ˆQk(s, a))2]

与正文式 (8.5) 第 112–113 行逐项一致；p.4 Eq (4) 的 CQL(H) 与式 (8.6) 第 123–124 行一致。
方向（压数据外、抬数据内）与正文第 117 行的解读一致，**没有把符号写反**。

α 的语义与定理条件的归属另有卡（CH08-ALG-004），因为原文 p.4 的
"as more data becomes available and |D(s, a)| increases, the theoretical value of α that is
needed to guarantee a lower bound decreases" 与正文"量纲与奖励相同"的表述不完全对齐。

## 5 DAgger（无误，来源已补齐）

正文第 255–257 行"让策略先跑，把它访问到的状态拿给专家标注，再把这些新样本并入数据集。这就是
DAgger（Ross、Gordon 与 Bagnell, 2011，算法 3.1）"，第 271 行"DAgger 不是数据增强：数据增强在
已有样本上做变换、分布不变；DAgger 改变数据分布，且需要能查询专家，不是纯离线算法"。

一手文献 **`1011.0686_dagger`（9 页，level S）** 已入库，p.4 的 Algorithm 3.1 逐行对应：

> Initialize D ←∅. Initialize ˆπ1 to any policy in Π. for i = 1 to N do Let πi = βiπ∗+ (1 −βi)ˆπi.
> Sample T-step trajectories using πi. Get dataset Di = {(s, π∗(s))} of visited states by πi and
> actions given by expert. Aggregate datasets: D ←D S Di. Train classiﬁer ˆπi+1 on D. end for
> Return best ˆπi on validation.

同页的动机句也直接支撑"改变数据分布而非样本数量"的论断：

> The intuition behind this algorithm is that over the iterations, we are building up the set of
> inputs that the learned policy is likely to encounter during its execution based on previous
> experience (training iterations).

p.3 另有本书记载的 \(T^{2}arepsilon\) 常数的一手例子（见 `CH08-DER-001` 的新增来源）：

> Ross and Bagnell (2010) provided an imitation learning example where J(ˆπsup) = (1 −ϵT)J(π∗) + T 2ϵ.
> Hence the traditional supervised learning approach has poor performance guarantees due to the
> quadratic growth in T.

**结论**：表述正确，此前的"无法核实"只是文献缺口，现已按 lead 指示补入
`scripts/fetch_sources.py` 的 P1 组、跑 `fetch_sources.py --group P1` 与 `build_library.py --all`
结案；正文引注同步落到算法级（算法 3.1）。

## 6 Decision Transformer（无误）

正文第 194 行"把强化学习写成**条件序列建模**"、第 210 行"式 (8.12) 里没有任何贝尔曼方程：
没有 \(Q\)，没有自举，没有 \(\max\)"、第 214 行明确"'Decision Transformer 不需要强化学习'
是一个误读"。`2106.01345_decision-transformer` p.1：

> we present Decision Transformer, an architecture that casts the problem of RL as conditional sequence modeling. Unlike prior approaches to RL that fit value functions or compute policy gradients, Decision Transformer simply outputs the optimal actions by leveraging a causally masked Transformer.

第 212 行还写了它的边界（条件回报是插值、不能超出数据回报支撑），与原文的实验结论不冲突。

## 8 排名式断言（无误）

全文检索 `最好|最优|全面优于|所有任务|显著优于|SOTA` 无命中；表 8-1 的说明反而强调三种
方法"压制位置不同、失效方式不同"，第 189 行还提醒"把三者笼统称为保守算法会掩盖这一差别"。
不存在"CQL 在所有 D4RL 任务上最好"一类断言，无需改。

## 附：其余观察（不单独开卡）

1. 图 8-4 的实测后悔值在 \(T=56\) 时约 45，而 \(T^{2}\varepsilon=313.6\)，正文"与界 (8.14)
   形状一致"偏强；已在 CH08-DER-001 的 planned_fix 里一并处理。
2. 定理 8.1 的标签写"[精确，表格或线性、策略慢变]"，原文 §3.2 的理论分析确实先做无采样误差、
   后扩到线性/NTK（p.4、p.5），标签不必改；要改的是条件归属（CH08-ALG-004）。

## 施工记录（2026-10-20）

六张卡的 `planned_fix` 已按 lead 授权落到正文，**只改 `content/ch08.md`**，未动引擎与其他章：

| 卡 | 落点 | 改法 |
|---|---|---|
| CH08-DER-001 | 第 243–251 行 | 证明梗概换成"逐步出错求和"，显示式改为 $\sum_t t\varepsilon=\varepsilon T(T+1)/2\le T^{2}\varepsilon$；补一句"不要把 $(T-t)$ 丢成 $T$"；图 8-4 的说明改成"慢于二次上界（T=56 时 47.6，T≥16 的 log-log 斜率 1.27）" |
| CH08-ALG-001 | 第 148、159–161、279、400、473 行 | 四处"分位数"改成"上期望值/expectile"；式 (8.8) 后补两行区分（$\ell_2$ vs $\ell_1$、两点分布 {0,1} 上 0.9 vs 1） |
| CH08-ALG-002 | 第 93、102、183 行 | "不让贪婪操作看到它们"改成"在远离数据的动作上做选择"；补 $-\Phi\le\xi_\phi\le\Phi$ 与两个端点极限（$\Phi=0,n=1$→BC；$\Phi$ 全长、$n\to\infty$→Q-learning）；表 8-1 的 BCQ 行同步 |
| CH08-ALG-003 | 第 290、311、320、339、382 行 | "无偏但方差大"→"方差可能无穷"；节标题改为"无偏，但方差可以无穷"；补 $\kappa$ 存在的前提与含环轨迹的反例；补 WIS 的"权重压在 ≤1"机制；表 8-2 后补"本节权重有界，测不出无穷方差" |
| CH08-ALG-004 | 第 128、132、142 行 | 定理 8.1 拆成两条、条件分开（间隙扩张要 $\alpha$ 足够大；价值下界要慢变 + 期望不等式）；"α 量纲与奖励相同"改为"与奖励尺度相乘"，并补"所需 α 随数据量下降" |
| CH08-ALG-005 | 第 257 行 | 引注补到算法级"（Ross、Gordon 与 Bagnell, 2011，算法 3.1）" |

附带两处正文修正：
1. 图 8-4 图注原来把"点线（T² 参考）"写成"虚线"、把"带方块的虚线（DAgger）"写成"点划线"——已按实际线型改正。
2. 8.4.3 节补一段"三条路线的理论地位"（BC [精确] / DAgger [渐近] / 离线悲观 [近似] 或 [经验规律]），
   并给出"能不能为策略自己访问到的状态拿到标签或奖励"这一判别句，同时把末页留白填到约 45%。

施工后自检：`python main.py --only 8` → **21 页、6 图、309 个公式（21 个编号 8.1–8.21）、1.50 MB**，
构建无 `!!` 警告；`python check_content.py --only 8` → `OK ch08.md 21924 字 0 问题`；
`python verify.py` → 08 行 `21 1.50 25 0 0 0 0 0 0`，`total pages 497 | problems 0`；
PDF 文本层里 21 个 `(8.k)` 全部在。
