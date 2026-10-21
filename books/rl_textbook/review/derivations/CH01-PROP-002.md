# CH01-PROP-002：常数步长被写成"非平稳分布唯一正确的选择"

对象：`content/ch01.md` 第 71 行

```
于是步长可从 1/n 换成一般的 α_n——1/n 是样本平均（平稳分布最优），
α 是指数遗忘（非平稳分布唯一正确的选择）。
```

## 1. 这句话说了三件事，其中两件有问题

1. "`1/n` 是样本平均" —— 对，且与式 (1.4) 一致；
2. "（平稳分布最优）" —— 措辞错位：应为"平稳**奖励分布**下（就均方误差而言）合适"；
   "平稳分布"在 MDP 里另有含义（状态分布），与这里不是一件事；
3. "`α` 是指数遗忘（非平稳分布**唯一正确的选择**）" —— **断言过强**，与文献和本章
   自己的口径都不一致。

## 2. 权威表述：只是"最常用的方式之一"，而且它不收敛

`RLbook2020` p.55（印 p.33）§2.5 开头：

> One of the most popular ways of doing this is to use a constant step-size parameter.

——"one of the most popular ways"，没有"唯一"的意思。紧接的同一节又明确说常数步长的估计
**不会收敛**：

> In the latter case, the second condition is not met, indicating that the estimates never
> completely converge but continue to vary in response to the most recently received rewards.
> As we mentioned above, this is actually desirable in a nonstationary environment …

即：常数步长的价值是"能跟住漂移"，代价是"永远不收敛、只在真值附近抖动"。把它称作
"唯一**正确**的选择"，恰好把代价那一半抹掉了。

S&B 同节（与习题 2.7）还给出至少两种同样成立的做法：

- **滑窗平均**（§2.5：只对最近若干次奖励取平均），同样能跟踪漂移；
- **无偏常数步长**：习题 2.7 的 `β_n = α/ō_n`（式 (2.8)(2.9)），"an exponential
  recency-weighted average **without initial bias**"——它依然是常数型步长，却消掉了初值偏差。

因此"非平稳 ⇒ 只能用常数步长"和"常数步长是唯一正确选择"都不成立。

## 3. 与本章 1.2.4 自相矛盾

第 136 行（1.2.4 节）说：

> 三，不适用于非平稳目标——目标漂移时 Σα_n²<∞ 使步长趋零，而跟踪漂移必须用常数步长，
> 恰好违反第二条：**跟踪与收敛不可兼得**。

同一章先说常数步长是"唯一正确的选择"，后说它违反收敛条件、只能跟踪，读者会得到相反的
印象。两处口径应当统一为："非平稳时需要**让步长不趋于零**（常数步长、滑窗、或自适应
步长族），代价是放弃收敛保证"。

## 4. 建议改法

> 于是步长可从 `1/n` 换成一般的 `α_n`：`1/n` 对应样本平均，在平稳奖励下给出无偏、方差
> 按 `1/n` 收缩的估计；常数 `α` 给出指数遗忘的平均——它**不收敛**（式 (1.8) 的第二条不
> 满足），但在非平稳环境下正是想要的跟踪行为。滑窗平均与无偏常数步长技巧是同一诉求的
> 另两种实现。

## 5. 来源

- `RLbook2020` p.54（印 p.32）：§2.5 开头"one of the most popular ways … constant step-size
  parameter"，以及增量式伪代码 `Q(A) ← Q(A) + (1/N(A))[R − Q(A)]`；
- `RLbook2020` p.55（印 p.33）：式 (2.7) 两条件、"never completely converge … actually
  desirable in a nonstationary environment"；
- 同页与习题 2.7 的 `β_n = α/ō_n`（式 (2.8)(2.9)）为"无偏常数步长"的存在性证据。
