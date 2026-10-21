# CH05-PROP-001：式 (5.13) 缺的不只是一个 γ^t

被审对象：`content/ch05.md` 第 174–182 行，式 (5.13) 与第 182 行的结论。

## 1. 结论

式 (5.13) 左边是**第 t 步**的贡献，右边是整条轨迹目标的梯度，两者相差一个 γ^t 因子与一个 Σ_t：

\[
\mathbb{E}\bigl[\bigl(G_t-V_\phi(s_t)\bigr)\nabla_\theta\log\pi_\theta(a_t\mid s_t)\bigr]\neq\nabla_\theta J(\theta),
\qquad
\gamma^{t}\,\mathbb{E}\bigl[\bigl(G_t-V_\phi(s_t)\bigr)\nabla_\theta\log\pi_\theta(a_t\mid s_t)\bigr]=\nabla J_t .
\]

补全后的正确写法就是本章式 (5.11)；把 b 取成 V_φ 不改变形式，只改变每步内部的减数。

## 2. γ^t 从哪来

由策略梯度定理的轨迹形式（式 5.8）：

\[
\nabla_\theta J(\theta)=\mathbb{E}_{\tau}\Bigl[\sum_{t\ge0}\gamma^{t}G_t\,\nabla_\theta\log\pi_\theta(a_t\mid s_t)\Bigr].
\]

γ^t 属于“第 t 步这个事件”——它是把“t 时刻被访问”折算回轨迹概率的因子，
与基线取什么无关。把 t 固定、只看一步：

\[
\nabla J_t:=\gamma^{t}\,\mathbb{E}\bigl[\bigl(G_t-b(s_t)\bigr)\nabla_\theta\log\pi_\theta(a_t\mid s_t)\bigr],
\qquad
\nabla_\theta J(\theta)=\sum_{t\ge0}\nabla J_t .
\]

于是式 (5.13) 的左边等于 γ^{-t}∇J_t。只有 t=0 时两者巧合相等。

## 3. 量级示例

γ=0.99、t=100 时 γ^t≈0.366；把式 (5.13) 当作“每步都等于 ∇J”再对 t 求和，等于把梯度乘以 Σ_t γ^{-t}，
在长回合里是几十倍量级（截断长度为 T 时约为 (1−γ^{-T})/(1−γ^{-1})）。

反过来看，为什么这个错长期没被抓住：不少实现按时间步均匀取平均、并且用 γ^t 折算过采样权重，
两者恰好抵消。**抵消是实现的约定，不是等式成立**，一旦换实现（例如按回合长度加权）就会暴露。

## 4. 与本章其他位置的一致性

- 式 (5.9)：\(\theta\leftarrow\theta+\alpha\,\gamma^{t}G_t\nabla\log\pi\)，带 γ^t；
- 算法 5-1 第 6 行：`θ ← θ + α γ^t (G_t - b(s_t)) grad log π`，带 γ^t；
- 第 93 行：明确写“其中 γ^t 这个权重不能省”。

S&B (13.11)（p.330 的算法框）同样是 \(\theta\leftarrow\theta+\alpha_\theta\gamma^{t}\delta\nabla\ln\pi(A_t|S_t,\theta)\)。
所以漏 γ^t 的是式 (5.13) 一处，其余各处的写法是对的。

## 5. 与命题 B 的关系

命题 B 依赖式 (5.10) 的恒等式

\[
\mathbb{E}_{a\sim\pi}\bigl[\nabla_\theta\log\pi_\theta(a\mid s)b(s)\bigr]
=b(s)\nabla_\theta\sum_a\pi_\theta(a\mid s)=0,
\]

与 γ^t 无关。补上 γ^t 不削弱命题 B：只要 V_φ 只依赖状态，
\(\gamma^{t}\mathbb{E}[(G_t-V_\phi)\nabla\log\pi]=\nabla J_t\) 依然成立，求和即 ∇J。
本条修的是等式的书写，不是无偏性结论。

## 6. 修正建议

1. 第 176–180 行的式 (5.13) 改成对 t 的求和形式；或保留单步形式，但左侧补 γ^t、右侧写 ∇J_t。
2. 第 182 行“这就是命题 B”之后补一句：单步形式必须带 γ^t，与式 (5.11) 的求和形式等价。
3. 第 152 行“所有轨迹等长时可以省 γ^t”限定为“目标本来就是未折扣”，否则与第 93 行冲突。
