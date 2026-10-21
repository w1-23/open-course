# CH05-PROP-004 TRPO 的三步求解：目标一阶、KL 二阶

被审对象：`content/ch05.md` 第 312 行（"第一步，把约束线性化、把目标二次化，得到自然梯度方向 F^{-1}g"）。

## 1. 结论

顺序写反了。TRPO 的做法是：**对代理目标取一阶（线性）近似、对 KL 约束取二阶（二次）近似**，
解出来才是 F^{-1}g；反过来（目标二次化、约束线性化）得到的是牛顿型方向。

## 2. 推导要点

在 θ_old 附近展开：

$$
\hat L(\theta)\approx \hat L(\theta_{\text{old}})+g^{\top}(\theta-\theta_{\text{old}}),
\qquad
\bar D_{\mathrm{KL}}(\theta_{\text{old}},\theta)\approx\tfrac12(\theta-\theta_{\text{old}})^{\top}F(\theta-\theta_{\text{old}}),
$$

其中 g=∇_θ L̂(θ_old)，F 是平均 Fisher 信息矩阵（KL 在 θ_old 处的 Hessian）。

于是子问题变成 max_x g^T x s.t. ½x^T F x ≤ δ，拉格朗日条件给出

$$
x^{\star}=\sqrt{\frac{2\delta}{g^{\top}F^{-1}g}}\;F^{-1}g,
$$

即"方向是 F^{-1}g、步长由 δ 定"——这正是第 312–316 行的算法。

## 3. 反过来的情形

若把目标二次化（Hessian H）而把约束线性化（c^T x ≤ δ），则解为

$$
x^{\star}=\frac{\delta}{c^{\top}H^{-1}c}\,H^{-1}g,
$$

是牛顿方向 H^{-1}g 而不是 F^{-1}g。两者只有在 H=F（且常数对齐）时才一致，而一般不等。
这也说明第 315 行的解释（"用 Fisher 而不用 Hessian，因为它只依赖策略分布"）只有在
F 确实来自约束 KL 时才自洽。

## 4. 修法（正文待改，本轮不动正文）

第 312 行改为"对代理目标取一阶近似、对 KL 约束取二阶近似，得到自然梯度方向 F^{-1}g"，
并可补一句对照："反过来把目标二次化、约束线性化，得到的是牛顿方向"。
