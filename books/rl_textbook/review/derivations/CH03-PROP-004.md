# CH03-PROP-004：\(\varepsilon\)-软最优策略的价值差为什么不能只写 \(O(\varepsilon)\)

对象：`content/ch03.md` 第 147–154 行「3.2.3 覆盖」，第 154 行末句：

```
称满足式 (3.10) 的策略为 \(\varepsilon\)-软策略：它把覆盖变成策略自身的性质，代价是最终学到的只是最优的 \(\varepsilon\)-软策略，价值与最优值相差 \(O(\varepsilon)\)。
```

## 1. 问题

\(O(\varepsilon)\) 里的隐含常数必须带 \(1/(1-\gamma)\)。折扣越小（\(\gamma\to1\)），同样的探索率造成的价值损失越大；把差距写成纯 \(O(\varepsilon)\) 会让读者以为误差与折扣无关，也与本章反复强调的"折扣决定有效视野"矛盾。

## 2. 推导（界，不是阶）

记 \(\pi_{\varepsilon}\) 为相对 \(Q^*\) 的 \(\varepsilon\)-贪心策略，\(\pi^*_\varepsilon\) 为 \(\varepsilon\)-软策略集中的最优者。对任意状态 \(s\)：

\[
V^{\pi_{\varepsilon}}(s)=\sum_a\pi_{\varepsilon}(a\mid s)Q^*(s,a)
=(1-\varepsilon)\max_aQ^*(s,a)+\frac{\varepsilon}{|\mathcal{A}|}\sum_aQ^*(s,a),
\]

于是

\[
V^*(s)-V^{\pi_{\varepsilon}}(s)
=\varepsilon\Bigl[\max_aQ^*(s,a)-\frac{1}{|\mathcal{A}|}\sum_aQ^*(s,a)\Bigr]
\le\varepsilon\Bigl[\max_aQ^*(s,a)-\min_aQ^*(s,a)\Bigr].
\]

若 \(|R|\le R_{\max}\)（奖励有界），则 \(Q^*\in[-R_{\max}/(1-\gamma),\,R_{\max}/(1-\gamma)]\)，故 \(\max_aQ^*-\min_aQ^*\le 2R_{\max}/(1-\gamma)\)。

更紧的一步：对任意 \((s,a)\)，

\[
V^*(s)-Q^*(s,a)\le\max_{a'}Q^*(s,a')-Q^*(s,a)\le\frac{R_{\max}-R_{\min}}{1-\gamma},
\]

（用 \(Q^*(s,a)\ge R_{\min}+\gamma\min_{s'}V^*(s')\)、\(V^*\le R_{\max}/(1-\gamma)\) 夹逼），因此

\[
V^*(s)-V^{\pi_{\varepsilon}}(s)\ \le\ \varepsilon\cdot\frac{R_{\max}-R_{\min}}{1-\gamma}.
\]

又因为 \(\pi^*_\varepsilon\) 在 \(\varepsilon\)-软策略集中不劣于 \(\pi_{\varepsilon}\)，\(V^{\pi^*_\varepsilon}\ge V^{\pi_{\varepsilon}}\)，故

\[
V^*(s)-V^{\pi^*_\varepsilon}(s)\ \le\ \frac{\varepsilon\,(R_{\max}-R_{\min})}{1-\gamma}.
\]

取 \(R\in[0,1]\) 时就是 \(\varepsilon/(1-\gamma)\)。**结论：差距是 \(O\bigl(\varepsilon/(1-\gamma)\bigr)\)，不是 \(O(\varepsilon)\)。**

## 3. 数值示意（\(\gamma=0.9\) 与 \(\gamma=0.99\)）

取 \(R\in[0,1]\)、\(\varepsilon=0.1\)：界分别为 \(0.1/0.1=1.0\) 与 \(0.1/0.01=10.0\)。数量级差 10 倍——这正是"折扣越接近 1，探索的代价越大"的量化版本，也解释了为什么 \(\varepsilon\) 在长视野任务上必须随训练衰减（3.2.4 节与 3.5.2 节的 GLIE 讨论）。

## 4. 与文献的关系

S&B p.122 只给出 \(\varepsilon\)-软的定义（\(\pi(a\mid s)\ge\varepsilon/|\mathcal{A}(s)|\)），p.125 只说明"we only achieve the best policy among the \(\varepsilon\)-soft policies"，**没有给 \(O(\varepsilon)\) 的界**。所以正文这句是作者自己加的量化表述，不是引文；既然是自己给的界，就必须把 \(1/(1-\gamma)\) 写出来，否则容易被判为"量纲/常数缺失"。

## 5. 修正建议

1. 第 154 行改为："价值与最优值之差不超过 \(\varepsilon(R_{\max}-R_{\min})/(1-\gamma)\)（\(R\in[0,1]\) 时为 \(\varepsilon/(1-\gamma)\)），即 \(O(\varepsilon/(1-\gamma))\)"，并标 [精确]（界由上式给出）。
2. 在该句后补一句"界对 \(\varepsilon\) 是线性的，但对 \(\gamma\) 是 \(1/(1-\gamma)\) 的——折扣越接近 1，探索的固定成本越大"，与 3.5.2 节的 GLIE 讨论呼应。
3. 若不想给常数，退而写"价值损失随 \(\varepsilon\) 线性、随 \(1/(1-\gamma)\) 放大"，不要只留 \(O(\varepsilon)\)。
