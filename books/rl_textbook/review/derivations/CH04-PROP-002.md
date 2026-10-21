# CH04-PROP-002：GTD 的收敛条件与正文的一句话压缩

对象：`content/ch04.md` 第 292–299 行「梯度 TD（GTD）系列的动机」。

## 1. 覆盖假设能给出什么

第 4.2.3 节已经写明：覆盖假设 \(\operatorname{supp}(\pi)\subseteq\operatorname{supp}(\mu)\) 只保证重要性比率 \(\rho_t=\pi(a\mid s)/\mu(a\mid s)\) 有定义，从而"该看见的动作都看得见"。它不约束更新算子的谱，因此既不排除 Baird 型发散，也不保证 GTD 的迭代收敛。

## 2. 双时间尺度条件

GTD(0)/GTD2/TDC 各有两个参数：主参数 \(w\)（被估计的价值权重）与副参数 \(v\)（最小二乘辅助向量）。更新写成

\[
v_{t+1}=v_t+\beta\rho_t\bigl(\delta_t-v_t^\top x_t\bigr)x_t,\qquad
w_{t+1}=w_t+\alpha\rho_t\bigl(x_t-\gamma x_{t+1}\bigr)x_t^\top v_t .
\]

收敛证明把 \(v\) 当作"快"变量、\(w\) 当作"慢"变量，要求极限下

\[
\beta\to0,\qquad \alpha/\beta\to0 ,
\]

即副过程比主过程快一个数量级。S&B p.281 对此的表述是"这些收敛证明通常显式假设这一点"，并称之为 two-time-scale proofs（`source/pages/RLbook2020/p0303.txt` 第 14–20 行）。

除此之外还需要：\(\Phi\) 满列秩（否则 \(C=\Phi^\top D\Phi\) 不可逆，(4.21) 无定义）、采样链遍历、两个步长都满足 Robbins–Monro 条件。

## 3. 与正文的差距

正文第 299 行的断言是"在覆盖假设下**离策略也收敛**"。对照第 2 节的条件，它漏掉了：双时间尺度（\(\beta\to0,\ \alpha/\beta\to0\)）、满列秩、遍历性、步长的 Robbins–Monro 条件。其中"覆盖假设"恰恰是唯一**不是**收敛条件的那一项——它是可辨识性条件。因此这句话不仅是省略，而是把必要条件当成了充分条件。

## 4. 修正建议

1. 第 299 行改为："在覆盖假设、\(\Phi\) 满列秩与双时间尺度步长（\(\beta\to0\)、\(\alpha/\beta\to0\)）下，GTD(0)/TDC 可以证明离策略收敛 [渐近]。"
2. 补一句与第 4.2.3 节的呼应："覆盖假设是必要条件而非收敛条件，GTD 把真梯度引进来的代价正是这组步长条件。"
3. 若篇幅允许，给出 \(\beta\) 与 \(\alpha\) 的量级建议（\(\beta=\eta\alpha\)，\(\eta\ll1\)），并注明这是实现经验而非定理条件。
