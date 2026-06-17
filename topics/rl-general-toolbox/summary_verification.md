# Summary verification — rl-general-toolbox
_generated: 2026-06-17T14:52:33.448Z  checked: 19/77  pass: 1  minor: 14  major: 4  unverifiable: 0  errors: 58_

核查员=Codex(跨模型,不共享撰写者的幻觉模式)。只核数字与论断依据,不评文笔。
本报告由 escalate_verify 汇总(多轮升级抽检,major 自动修正+复核;标注"需人工分诊"的为修正 2 次仍未通过)。

## 🟠 [minor] Soft Actor-Critic: Off-Policy Maximum Entropy Deep Reinforcement Learning with a Stochasti
`arxiv:1801.01290` v2  (quality: trusted)
- **[minor]** “on-policy 方法（举 TRPO/PPO/A3C 为例）因“每步梯度都要重新采样”而样本复杂度差” — note_plan 无对应锚点，疑未接地；原文可支持该背景论断。
- **[minor]** “off-policy 的 DDPG 虽样本高效，但“确定性 actor 与 Q 函数的相互作用使其极难稳定、对超参设置脆弱”” — note_plan 无对应锚点，疑未接地；原文可支持该 DDPG 背景论断。
- **[minor]** “作者声称这是据其所知最大熵 RL 框架下首个 off-policy actor-critic 方法” — note_plan 无对应锚点，疑未接地；原文可支持且总结保留了“据其所知”限定。

## 🟠 [minor] End-to-End Safe Reinforcement Learning through Barrier Functions for Safety-Critical Conti
`10.1609/aaai.v33i01.33013387` v2  (quality: trusted)
- **[minor]** “RL 在真实物理系统上落地的最大障碍是学习期没有安全保证” — 原文摘要只说学习期缺乏安全保证是“one main reason”，总结写成“最大障碍”略强；note_plan 也无对应锚点。
- **[minor]** “现有 model-free 安全 RL(reward-shaping、带约束的策略优化、teacher advice)"不能保证学习期的安全……"” — 该背景论断原文有依据，但 note_plan 无对应锚点，疑未接地。
- **[minor]** “已有 model-based / 备份控制器方法要么不管探索与性能优化,要么(切换备份控制器)"过度约束了策略探索"” — 该 related-work 论断原文有依据，但 note_plan 无对应锚点，疑未接地。
- **[minor]** “原文称"只要 K 足够大,优化对 K 不敏感(例如 10¹²),以重罚安全约束违反"” — 10¹² 与 K 不敏感的说法原文有依据，但 note_plan 对应 QP 锚点未覆盖该具体数字与论断。
- **[minor]** “满足不了(如力矩受限)时给出"优雅退化"(略微偏离安全集)” — graceful degradation 原文有依据，但 note_plan 无对应锚点，疑未接地。
- **[minor]** “若 ϵ_max>0……则扩张后的集合 Cϵ(原文定义 `Cϵ : {s: h(s) ≥ −ϵ/η}`)以概率 (1−δ) 前向不变” — Lemma 1/Theorem 2 的扩张安全集结论原文有依据，但 note_plan 的 Theorem 2 锚点未覆盖该具体分支与公式。
- **[minor]** “图3–5……未给出汇总的数值表格” — 本轮检查原文确认没有汇总数值表格，但 note_plan 无对应锚点，疑未接地。
- **[minor]** “并通过隐式学习他车行为提升油耗” — 跟车实验中隐式学习其他驾驶者行为以提升燃油效率的说法原文有依据，但 note_plan 无对应锚点，疑未接地。
- **[minor]** “η∈[0,1](原文 Definition 1:η=0 时屏障条件退化为 Lyapunov 条件,p.3)” — η=0 退化为 Lyapunov 条件原文有依据，但 note_plan 无对应锚点，疑未接地。
- **[minor]** “完整性能界证明在作者附录(链接 https://rcheng805.github.io/files/aaai2019.pdf)” — 附录链接与性能界证明位置原文有依据，但 note_plan 无对应锚点，疑未接地。

## 🟠 [minor] Safe Reinforcement Learning Using Robust Control Barrier Functions
`10.1109/lra.2022.3216996` v2  (quality: trusted)
- **[minor]** “两组自建仿真实验(代码 github.com/yemam3/Mod-RL-RCBF,见原文第 5 页脚注 1)” — note_plan 无对应锚点,疑未接地；本轮在原文中核到代码脚注和实验描述。
- **[minor]** “基线1=model-free SAC + 非可微 RCBF-QP;基线2=再加 [9] 的 compensator 神经网” — note_plan 无对应锚点,疑未接地；本轮在原文中核到该基线设定。
- **[minor]** “Unicycle:独轮车去目标点避障,扰动 ud=−0.1cos(θ)[1 0]ᵀ 模拟斜面;避障 RCBF hₒ=‖p(x)−pₒ‖²−δ²” — note_plan 无对应锚点,疑未接地；本轮在原文第6页核到该扰动和RCBF公式。
- **[minor]** “PVTOL(2D 四旋翼)避障 RCBF 相对度为 3,并加“与安全操作员保持距离”的约束 hₕ=δ²−(x₁−xₕ)²” — note_plan 无对应锚点,疑未接地；本轮在原文第7页核到相对度3和该操作员约束公式。

## 🟠 [minor] Deep Reinforcement Learning That Matters
`10.1609/aaai.v32i1.11694` v2  (quality: trusted)
- **[minor]** “作者把不可复现性的来源分为外在因素(超参、代码库)和内在因素(随机种子、环境特性)” — note_plan 无对应锚点,疑未接地；原文可核到该分类，未发现歪曲。
- **[minor]** “并引入机器学习/统计学里的显著性工具(bootstrap、t 检验、KS 检验、功效分析 power analysis——论文专设 "Power Analysis" 一节...)” — note_plan 无对应锚点,疑未接地；其中 bootstrap/t/KS 有相关锚点，但 Power Analysis 相关论断未在 note_plan 中单列。
- **[minor]** “RL 因在机器人、围棋、Atari、竞技游戏等领域的成果而备受关注” — note_plan 无对应锚点,疑未接地；原文引言可核到这些例子。
- **[minor]** “它们都优化带折扣的期望回报 ρ(θ,s₀)=E...[...]，并用策略梯度定理更新” — note_plan 无对应锚点,疑未接地；原文技术背景中有对应公式和说明。
- **[minor]** “新基线实现应匹配原始码库结果” — note_plan 无对应锚点,疑未接地；原文结论有对应建议。
- **[minor]** “作者自己也承认 "While there can be no specific number of trials specified as a recommendation"” — note_plan 无对应锚点,疑未接地；原文随机种子一节可核到该句。

## 🟠 [minor] What Matters In On-Policy Reinforcement Learning? A Large-Scale Empirical Study
`10.48550/arxiv.2006.05990` v2  (quality: ok)
- **[minor]** “Adam learning rate（C24）不属于“其余固定”项——作者刻意把它加入所有主题组一起随机采样” — 原文可核实该说法属实，但 note_plan 无对应锚点,疑未接地。
- **[minor]** “基线选 PPO，因为它“probably the most commonly used on-policy RL algorithm at moment”；实验用 MuJoCo 2.0” — 这些原文事实属实，但 note_plan 无对应锚点,疑未接地。
- **[minor]** “该基线默认值表见附录 C 的 Table 2，如 num_envs=256、iteration_size=2048、num_epochs=10、batch_size=64、γ=0.99、tanh 激活、Orthogonal gain 1.4” — 这些默认值在 Table 2 中可核实，但 note_plan 无对应锚点,疑未接地。
- **[minor]** “即信赖域式优化（防止策略偏离行为策略太远）对样本效率关键” — 原文相邻段落确有该解释，但 note_plan 无对应锚点,疑未接地。
- **[minor]** “作者自己强调研究目标 is not to provide a general statement that one of the losses is better” — 原文确有该限定，但 note_plan 无对应锚点,疑未接地。

## 🟠 [minor] What Matters for On-Policy Deep Actor-Critic Methods? A Large-Scale Study
`title:887fdc52a50a14c1` v2  (quality: trusted)
- **[minor]** “所有开关设成 OpenAI baselines 的 PPO 实现时能复现相近性能” — 原文支持该说法，但 note_plan 无对应锚点，疑未接地。
- **[minor]** “关键损失/估计器公式（PG、V-trace、PPO、AWR...）” — 这些公式原文基本支持，但除 RPA 外 note_plan 无对应锚点，疑未接地。
- **[minor]** “动作分布参数化...Tᵤ(N(x_μ, Tₚ(x_ρ+c_ρ)+ε_ρ))” — 页面图像核对显示公式与解释正确，但 note_plan 无对应锚点，疑未接地。
- **[minor]** “用 Mujoco 2.0（p.2 脚注1）” — 原文脚注支持该数字/设定，但 note_plan 无对应锚点，疑未接地。
- **[minor]** “推荐 λ=0.9” — 原文 §3.4 支持该推荐，但 note_plan 无对应锚点，疑未接地。
- **[minor]** “每遍打散到 minibatch 前重算优势” — 原文 §3.5 Recommendation 支持该建议，但 note_plan 无对应锚点，疑未接地。

## 🟠 [minor] Temporal Logic Guided Safe Reinforcement Learning Using Control Barrier Functions
`10.48550/arxiv.1903.09885` v2  (quality: ok)
- **[minor]** “作者针对当前 RL 的两个痛点:(1)复杂任务的规范/奖励难以手工设计... (2)在物理系统上学习时的安全探索” — 原文可核到，但 note_plan 无对应锚点，疑未接地。
- **[minor]** “论文将自己定位为:相对前人方法实现简单、能处理连续状态/动作空间与非线性约束、可高效执行” — 原文可核到，但 note_plan 无对应锚点，疑未接地。
- **[minor]** “任务公式 φ(式 19)在原文中明确表述为:'最终访问 g1 或 g2、最终访问 g3...'” — 原文可核到，但 note_plan 无对应锚点，疑未接地。
- **[minor]** “训练时允许智能体走出安全通道并与移动障碍碰撞(以受罚),但评估时不允许” — 原文可核到，但 note_plan 无对应锚点，疑未接地。
- **[minor]** “结论(§VII):在已知智能体动力学、未知环境动力学的仿真任务上,系统'能学到一个完成逻辑公式所述任务、同时在学习全程保证安全的策略'” — 原文可核到，但 note_plan 无对应锚点，疑未接地。
- **[minor]** “目标选择(式 12)需在状态空间上解最大鲁棒度优化,作者承认'状态空间大时第一个优化问题会困难'” — 原文可核到，但 note_plan 无对应锚点，疑未接地。

## 🟠 [minor] Reproducibility of Benchmarked Deep Reinforcement Learning Tasks for Continuous Control
`10.48550/arxiv.1708.04133` v2  (quality: ok)
- **[minor]** “代码开源(p.2 脚注5给出 GitHub 链接:github.com/Breakend/ReproducibilityInContinuousPolicyGradientMethods)” — note_plan 无对应锚点,疑未接地；原文脚注5确有该链接。
- **[minor]** “Table 1、Table 2 还在不同迭代数(500/1000/2500/5000)下列出 Average Return / Max Average Return / Std” — note_plan 无对应锚点,疑未接地；表格内容本身与原文一致。
- **[minor]** “显著性用双样本 t 检验报告(注:仅对部分超参报告了 t 检验...DDPG 的 reward scale 与 actor-critic 学习率只给学习曲线、未见对应 t 检验)” — note_plan 无对应锚点,疑未接地；该归纳与原文可见内容一致。
- **[minor]** “作者给出机制直觉:TRPO 用带 KL 约束的共轭梯度优化,小 batch 在高方差环境下步间梯度差异大、训练更不稳定。” — note_plan 无对应锚点,疑未接地；原文 p.4 有相应机制解释。
- **[minor]** “作者自己也承认"需要进一步确定多少次试验 N 才能保证公平比较"(p.8 脚注13)” — note_plan 无对应锚点,疑未接地；原文脚注13确有该自述。

## 🔴 [major] Reward-Adaptive Reinforcement Learning: Dynamic Policy Gradient Optimization for Bipedal L
`10.1109/tpami.2022.3223407` v2  (quality: trusted)
- **[major]** “Walker2d 上 HDPG 的标准差很大(±528.0)、DDPG/MHDDPG 标准差更达 ±1000 量级” — 表 I 中 ±528.1 是 HalfCheetah-v3 上 HDPG 的标准差；Walker2d-v3 上 HDPG 是 3217.5±1144.8，属于数字张冠李戴。
- **[minor]** “actor 为 3 层全连接……critic 末端两层 (256,256) 与 (256,6)” — 原文有依据，但 note_plan 无对应锚点,疑未接地。
- **[minor]** “障碍高度 0.6–1.4cm;斜坡角 3–15 度。抗扰动任务每个测试做 100 次试验……障碍与斜坡任务原文未给出试验次数” — 原文有依据或可由图注核实，但这些具体数字/存在性判断在 note_plan 无对应锚点,疑未接地。

## 🟠 [minor] STRIDE: Automating Reward Design, Deep Reinforcement Learning Training and Feedback Optimi
`arxiv:2502.04692` v2  (quality: flag)
- **[minor]** “附录 prompt 的 TorchScript、髋前摆 60–80°、步长 2.5–3 m、躯干前倾 20–25°” — 这些内容在 PDF 中可核到，但 note_plan 无对应锚点，疑未接地。
- **[minor]** “反思 prompt(Prompt 3)则指导 LLM 分析各奖励分量随 epoch 的最大/均值/最小、与成功率的相关性、低方差/主导分量诊断” — 该附录 Prompt 3 细节在 PDF 中可核到，但 note_plan 无对应锚点，疑未接地。
- **[minor]** “从箱线图读出,STRIDE 在平地约 3.5、波浪约 1.75、随机均匀约 2.5(EUREKA 对应约 0.2/0.35/0.9)” — 这些近似值来自图中目测且 note_plan 无对应锚点；原文未给精确数值表，将其写成对应数值略强。

## 🟠 [minor] Safe Learning in Robotics: From Learning-Based Control to Safe Reinforcement Learning
`10.1146/annurev-control-042920-020211` v2  (quality: ok)
- **[minor]** “此前综述要么只覆盖控制论、要么只覆盖RL，没有打通的框架” — note_plan 无对应锚点，疑未接地；该论断可在原文 p.412 核到。
- **[minor]** “目标读者是有控制或RL背景、想要一个简洁整体视角的研究者” — note_plan 无对应锚点，疑未接地；该论断可在原文 p.413 核到。
- **[minor]** “Figure 5 把已有评估环境分三档……大量工作仍停留在抽象例子、且只有少数开源” — note_plan 无对应锚点，疑未接地；该图表解读可在原文 Figure 5 与 §4 核到。
- **[minor]** “扩展传统 gym API，同时支持控制社区……和安全鲁棒评估……” — note_plan 无对应锚点，疑未接地；该实现细节可在原文 p.434 核到。

## 🔴 [major] Learning to Walk Via Deep Reinforcement Learning
`10.15607/rss.2019.xv.011` v2  (quality: ok)
- **[major]** “权重设为 1.0、0.05、0.5、1.0,角度阈值设为 0.3 弧度” — 原文页面图像写的是 maximum angle threshold q̄ is set to -0.3 radians，总结把阈值符号写反。
- **[minor]** “算法 1(p.5)给出完整伪代码:每次迭代先对各环境步采样转移入 replay buffer...并用软更新的延迟目标网络” — note_plan 无对应锚点,疑未接地。
- **[minor]** “数据采集 job runs on an on-board computer...训练 job runs on a workstation...可单独暂停/重启以应对硬件与通信错误” — note_plan 无对应锚点,疑未接地。
- **[minor]** “真机 Minitaur:八直驱执行器四足...动作为各腿的摆角与伸展...经 PD 控制器跟踪” — note_plan 无对应锚点,疑未接地。
- **[minor]** “图3图注明确限定:只有本方法没调参,其它算法都经过密集调参才得到这些曲线” — note_plan 无对应锚点,疑未接地。

## 🟠 [minor] Addressing Function Approximation Error in Actor-Critic Methods
`title:7f327668611a45e6` v2  (quality: ok)
- **[minor]** “TD3 的数值如 HalfCheetah 9636.95 ± 859.065、Hopper 3564.07 ± 114.74、Walker2d 4682.82 ± 539.64、Ant 4372.44 ± 1000.33” — 数字可在表1核到，但 note_plan 无对应锚点，疑未接地。
- **[minor]** “目标网络以 θ′ ← τθ + (1−τ)θ′ 软更新” — 公式可在原文式3附近核到，但 note_plan 无对应锚点，疑未接地。
- **[minor]** “we run our experiments across a fair number of seeds ... and open source both our code and learning curves (https://gith” — 开源代码与学习曲线可在原文核到，但 note_plan 无对应锚点，疑未接地。
- **[minor]** “具体七个 MuJoCo 任务可在 Table 1（p.9）与 Figure 5（p.9）逐项核到：HalfCheetah / Hopper / Walker2d / Ant / Reacher / InvertedPendulum / In” — 七个任务名称可由图5和表1核到，但 note_plan 只锚定“seven continuous control domains”，未锚定具体任务列表。
- **[minor]** “快更新（τ=1）目标网络导致发散” — 表述略不严谨：图3图注中 τ=1 对应 without target networks，而不是一个“τ=1 目标网络”。

## 🔴 [major] High-Dimensional Continuous Control Using Generalized Advantage Estimation
`10.48550/arxiv.1506.02438` v2  (quality: ok)
- **[major]** “PDF p.9 table — 3D biped: `v_fwd − 10⁻⁵‖u‖² − 10⁻³‖f_impact‖² + 0.2`... The checker's proposed "fix" (impact = 10⁻⁵) is ” — 原文表格和页面图像均显示 3D biped 的 impact-force 系数是 10⁻⁵，不是 10⁻³；总结把错误数字当作纠错结论。
- **[major]** “3D 双足 = v_fwd − 10⁻⁵‖u‖² − 10⁻³‖f_impact‖² + 0.2... 双足与四足的 f_impact 系数同为 10⁻³” — 原文奖励表中 3D 双足的 ‖f_impact‖² 系数为 10⁻⁵，四足为 10⁻³；总结数字错误并错误声称二者相同。
- **[minor]** “策略梯度有形如 g = E[Σ Ψ_t ∇_θ log π_θ(a_t|s_t)] 的统一形式... Ψ_t 可取总回报、Q、优势 A 或 TD 残差等” — note_plan 无对应锚点,疑未接地。
- **[minor]** “作者定义了“γ-just”估计器(代入策略梯度不引入偏差,Definition 1 / Proposition 1,p.3,证明见附录 B)作为分析框架” — note_plan 无对应锚点,疑未接地。
- **[minor]** “配合“响应函数”χ 的分析,作者论证:用 V≈V^{π,γ} 整形可压缩奖励的时间扩散,再用更陡的折扣 γλ 砍掉长延迟带来的噪声” — note_plan 无对应锚点,疑未接地。

## 🟠 [minor] Safe reinforcement learning: A control barrier function optimization approach
`10.1002/rnc.5132` v2  (quality: ok)
- **[minor]** “传统 CBF 方法需要系统动力学信息、把 CBF 作为不等式约束、需检查其导数条件...且因需要模型而不易与 RL 框架结合；MPC 类方法...既依赖模型又短视” — 原文支持这些背景论断，但 note_plan 无对应锚点，疑未接地。
- **[minor]** “从而无需像传统 CBF 那样显式施加导数不等式约束(也就免去了对动力学信息的需求)” — Remark 3 只明确说新公式不施加 Bγ 导数条件；“免去了对动力学信息的需求”需结合后续 off-policy 算法才成立，此处表述略强。
- **[minor]** “状态为 [横向位移 y、其速度 v、误差偏航角 φ、偏航角速度 ψ̇]” — 原文状态写作 x=[y,v,φ,ψ]^T，并说明 ψ 是 φ 的导数；总结把状态变量写成 ψ̇，符号不够忠实。
- **[minor]** “纯数值仿真,无外部真实数据集” — 原文内容支持该判断，但 note_plan 无对应锚点，疑未接地。
- **[minor]** “前/后轮到质心距离 a=1.11 m、b=1.59 m” — 数字与表 1 一致，但 note_plan 的仿真参数锚点未覆盖这两个数字，疑未接地。
- **[minor]** “off-policy Bellman 方程(35)与原 Bellman 方程(30)等价、共享同一更新律(34)” — 原文 Lemma 4 支持该论断，但 note_plan 无对应 point 锚点，疑未接地。
- **[minor]** “必须先有一个安全(保守)的初始策略才能保证学习期间安全” — 原文支持行为策略需安全且可用先验动力学知识构造，但 note_plan 无对应锚点，疑未接地。

## 🟠 [minor] Penalized Proximal Policy Optimization for Safe Reinforcement Learning
`10.24963/ijcai.2022/520` v2  (quality: trusted)
- **[minor]** “直接把不安全交互罚进 reward 不可行：原文引言明言...不同罚强度等于不同 MDP；且...缺乏“策略提升↔安全满足”的显式理论。CMDP（Altman, 1999）是更实用的形式化...” — note_plan 无对应锚点,疑未接地；该背景论断和公式本轮可在原文核到，但未在锚点表中覆盖。
- **[minor]** “基线为论文所称 SOTA：CPO、PPO-Lagrangian、FOCOPS，并以忽略约束的标准 PPO 作 reward 上界参照...P3O 与 FOCOPS...以相同规则/技巧实现” — note_plan 无对应锚点,疑未接地；实验设置论断本轮可在原文核到，但未在锚点表中覆盖。
- **[minor]** “FOCOPS 较好但其拉格朗日乘子的学习率/初值很敏感。” — note_plan 无对应锚点,疑未接地；该作者解读本轮可在原文核到，但未在锚点表中覆盖。
- **[minor]** “同时观察到训练初期违反 hazard 约束但几乎不撞 pillar（初始化机制所致），说明 P3O 对可行/不可行初始策略都能收到满足约束的解。” — note_plan 无对应锚点,疑未接地；该多约束现象与解释本轮可在原文核到，但未在锚点表中覆盖。
- **[minor]** “作者在结论中把未来工作明确指向端到端视觉任务” — note_plan 无对应锚点,疑未接地；该未来工作表述本轮可在原文核到，但未在锚点表中覆盖。

## 🔴 [major] Automatic Intrinsic Reward Shaping for Exploration in Deep Reinforcement Learning
`10.48550/arxiv.2301.10886` v2  (quality: trusted)
- **[major]** “它无法超越候选集合里最好的那个在该任务上的潜力” — 原文只说预定义奖励集及模块质量会影响最终性能，并未声称 AIRS 不能超过候选集合中最好的单个奖励模块；论文还说 AIRS 可通过多内在奖励选择 assemble advantages。
- **[minor]** “探索强度随训练衰减,早期多探索、后期收敛到纯任务奖励” — 原文只给出 β_t=β_0(1-κ)^t 并说明 κ 是衰减率；“后期收敛到纯任务奖励”是额外推断，且 MiniGrid 最佳 κ=0 时并不衰减。
- **[minor]** “消融(候选集合越大越好的初步证据)” — 原文消融只比较 RE3+ID 两模块池并称可从多个内在奖励中组装优势，不能推出候选集合越大越好这一一般性结论。
- **[minor]** “MiniGrid...7×7×3；Procgen...15 个离散动作、64×64×3 RGB；DMC 训练 1M 帧、每 10K 帧评估一次；Table 8 列了 PseudoCounts/ICM/RND/GIRM/NGU/RIDE/RE” — 这些具体设置数字或模块清单虽可在原文核到，但 note_plan 无对应锚点，疑未接地。

## 🟠 [minor] Challenges of real-world reinforcement learning: definitions, benchmarks and analysis
`10.1007/s10994-021-05961-4` v2  (quality: ok)
- **[minor]** “Table 1 obs dims are 5/18/78/67 ... action dims 1/6/12/21” — note_plan 无对应锚点,疑未接地；本轮核对原文 Table 1 数字本身无误。
- **[minor]** “动作/观测延迟扫 0→20 步,奖励延迟扫 0→100 步” — note_plan 无对应锚点,疑未接地；原文 Fig.2 caption 可支持该范围。
- **[minor]** “扫 0/10/20/50/100 ... 加高斯动作噪声 ... 高斯观测噪声 ... 各自单独施加” — note_plan 无对应锚点,疑未接地；原文 Fig.4/Fig.5/Table 11 可支持。
- **[minor]** “cartpole 三条:`slider_pos`/`slider_accel`/`balance_velocity`,全表见 Table 2” — note_plan 无对应锚点,疑未接地；原文 Table 2 可支持。
- **[minor]** “用 Robust MDP(最坏情形价值,公式 (2),p.2435)框架;实验加卡住/丢失传感器...按 Table 3 扫物理参数扰动、跑 uniform/cyclic 两种非平稳调度” — note_plan 无对应锚点,疑未接地；原文相应章节、Table 3、Fig.10-11 可支持。
- **[minor]** “用三档数据集(small/medium/large,规模见 Table 5,如 walker 1000/2000/5000 episodes),行为策略取 DMPO 训到约 75% 收敛性能的快照” — note_plan 无对应锚点,疑未接地；原文 Table 5 和 p.2446 可支持。
- **[minor]** “动作重复扫至 20 步(Fig.13)” — note_plan 无对应锚点,疑未接地；原文 Table 11/Fig.13 可支持。
- **[minor]** “humanoid:walk 上 D4PG 从无挑战的 934.0 掉到 medium 档 1.28,DMPO 从 788.49 掉到 1.27” — note_plan 无对应锚点,疑未接地；原文 Table 7/8 数字可支持。
- **[minor]** “作者自己说本可以加 SAC、PPO,但出于算力成本没加...baseline "is with a naive learner that is not designed to answer these challenges"” — note_plan 无对应锚点,疑未接地；原文 p.2424 和 p.2451 可支持。
- **[minor]** “MuJoCo 有内部动力学状态,而 agent 只拿得到预处理后的 observation” — note_plan 无对应锚点,疑未接地；原文 p.2423/p.2453 可支持。

## ✅ pass (1)
- Safe Reinforcement Learning via Shielding (v2)

## ⚙️ 未能核查 (58)
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_w9yea9lx\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_ap1vlpah\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_yz2gp259\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_c6_brqjw\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_emvnared\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_v10ag9nj\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_3pr2_6ba\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_3u_jub9v\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx__zt1tdsw\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_qbunaoc1\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_iwglqzq9\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_hjd3wyfu\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_fd3h3hxn\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_1_qsvc0e\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_fut27xt0\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_rv3_xepv\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_o3ab646h\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_i0o3n1r8\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_daeoksml\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_yxro39bk\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_k8sjcrjs\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_o8y0_mdm\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_3sdu2r0w\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_67i86m5x\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_u2qcz1dn\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_62jsly0s\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_ywy28joj\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_9jup37c5\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_bcx9q1w5\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_v9lyhytl\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_68fdsbhz\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_h7scppon\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_5vzv1tz3\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_aj6dar3x\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_7_6xti8n\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_edbupbyn\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_itwzwjm5\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_eujrwukc\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_g1655ywd\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_eupyoyok\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_jem0yiof\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_mevmmdr_\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_xyi9s3d2\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_kel1fa9e\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_p0wf99h9\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_fr8r_948\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_6xo7cyaq\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_k5y4apmv\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_o4b7fag7\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_38kg2dri\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_exg1e_14\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_o2jztuqe\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_90d27bpf\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_3mur6ugs\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_hf69fovd\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_4ne58bmw\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_denpbv9c\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.140.0\n--------\nworkdir: /tmp/vfy_cdx_xk2o6d51\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
