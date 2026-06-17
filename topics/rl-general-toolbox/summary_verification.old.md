# Summary verification — rl-general-toolbox
_generated: 2026-06-10T23:55:32.044Z  checked: 49/49  pass: 10  minor: 39  major: 0  errors: 0_

核查员=Codex(跨模型,不共享撰写者的幻觉模式)。只核数字与论断依据,不评文笔。
本报告由 escalate_verify 汇总(多轮升级抽检,major 自动修正+复核;标注"需人工分诊"的为修正 2 次仍未通过)。

## 🟠 [minor] CVaR-Constrained Policy Optimization for Safe Reinforcement Learning
`10.1109/tnnls.2023.3331304` v2  (quality: ok)
- **[minor]** “CVaR(条件风险价值,即上尾 α 部分的条件期望)” — 按原文公式，α-level CVaR 是 VaRα 以上尾部的条件期望，尾部质量对应 1−α；写成“上尾 α 部分”容易把尾部比例说反。
- **[minor]** “正文 Fig.3 学习曲线展示的是 5 个随机种子的均值±方差(图注口径)” — Fig.3 图注说阴影表示 standard deviations（标准差），不是方差；总结其他位置写“标准差”才与原文一致。

## 🟠 [minor] Reproducibility of Benchmarked Deep Reinforcement Learning Tasks for Continuous Control
`10.48550/arxiv.1708.04133` v1  (quality: ok)
- **[minor]** “Half-Cheetah 上 (400,300) 显著优于更小的网络（TRPO/DDPG 都是，t 检验显著）” — 原文确实说(400,300)对TRPO和DDPG都更好，但给出t检验数值的脚注只针对TRPO，未提供DDPG的t检验证据。
- **[minor]** “状态≤20维” — 原文给出Hopper和Half-Cheetah均为S⊆R²⁰，即状态维度为20；“≤20维”表述不准确。

## 🟠 [minor] On the Emergence of Whole-Body Strategies From Humanoid Robot Push-Recovery Learning
`10.1109/lra.2021.3076955` v1  (quality: trusted)
- **[minor]** “评测分四组: 1. 确定性水平面力... 2. 基座随机球面力... 3. 胸部/肘部随机力...” — 原文结果部分只有三类主要量化评测，另有高速物体撞击用于展示涌现行为；总结称“四组”但只列三组，数字不符。
- **[minor]** “奖励多达近十项” — 若按原文 Table II 的奖励分量计数为 10 项，称“近十项”略不精确但不影响主要判断。

## 🟠 [minor] PPG Reloaded: An Empirical Study on What Matters in Phasic Policy Gradient
`title:9cc1357c09c7e8e7` v1  (quality: trusted)
- **[minor]** “研究数据多样性时固定缓冲区/环境数” — 原文研究数据多样性时是改变 Toff，另一个实验固定 Toff=1 后改变 Nenv；并非同时固定缓冲区和环境数。
- **[minor]** “小 minibatch 还显著缩短训练时间——MV×1/8 把每次迭代耗时砍半” — 原文结论是训练时间约减半，但表2数值显示相对默认 PPG 的 MV×1/8 为 20.4→13.0、6.2→4.6、20.7→13.4，并非严格砍半；“砍半”表述偏强。

## 🟠 [minor] Secrets of RLHF in Large Language Models Part I: PPO
`10.48550/arxiv.2307.04964` v2  (quality: ok)
- **[minor]** “并与 SFT、ChatGPT 做人类+GPT-4 偏好评测” — 原文中与 ChatGPT 的比较只在 harmless 维度用 GPT-4 自动评测，没有对 ChatGPT 做人类偏好评测。
- **[minor]** “中文 Helpful 上优势不明显（RLHF 胜 46%、负 23%、平 31%）” — 原文正文称人工评测在所有中英文问题类型上都强烈偏好 RLHF，图10a的46%胜/23%负也不支持“不明显”这一转述。
- **[minor]** “只在 7B（论文称评测含 13B，但主分析与训练设置在 7B）上做” — 作者局限写的是研究主要聚焦7B，而非严格“只在7B”，且引言明确声称评测了7B和13B SFT模型。

## 🟠 [minor] Distributional Soft Actor-Critic with Three Refinements
`10.48550/arxiv.2310.05858` v1  (quality: ok)
- **[minor]** “每任务 5 个随机种子各独立训练 5 次，取均值与 95% 置信区间” — 原文是每个实验共5次独立训练、使用5个随机种子；学习曲线给95%置信区间，但表2最终回报给的是均值±标准差，不全是95%置信区间。
- **[minor]** “Humanoid 每千步 35.51s” — 原文写的是每1000 iterations 的平均耗时，不是每1000环境步/训练步，单位被转述得不准确。

## 🟠 [minor] Constrained Variational Policy Optimization for Safe Reinforcement Learning
`10.48550/arxiv.2201.11927` v1  (quality: ok)
- **[minor]** “所有方法用相同网络结构/大小、相同安全 critic 更新规则与折扣因子” — 原文只说所有方法网络大小相同；安全 critic 更新规则和折扣因子相同限定为所有 off-policy 方法，不是所有方法。
- **[minor]** “① 训练不稳定（primal 与 dual 的学习率难以平衡，λ 在可行/不可行时分别趋向 0 和 +∞，学习率极难调）” — 原文在第3.1节说 primal-dual 中当 Jc(π)>ε1 时最优 λ=+∞、Jc(π)<ε1 时 λ=0；总结把这直接表述为训练中 λ 在可行/不可行时趋向这些值，语气略强。
- **[minor]** “M 步即使更新很糟，下一步仍能恢复到可行域；高斯策略下还可证两步鲁棒” — 该鲁棒性结论在原文中依赖旧策略可行、M/E 步 KL 阈值关系 ε<ε2，以及高斯两步情形还要求 ε<ε2/8 且足够小；总结此处省略关键前提，表述偏绝对。

## 🟠 [minor] What Matters for On-Policy Deep Actor-Critic Methods? A Large-Scale Study
`title:887fdc52a50a14c1` v1  (quality: trusted)
- **[minor]** “PG 和 V-trace 较差(无法处理一次迭代内变成 off-policy 的数据)” — 原文只是说这“可能”是由其无法处理一次迭代内变成 off-policy 的数据导致，摘要把推测性原因写成了确定结论。
- **[minor]** “作者自己也承认这会系统性偏袒 PPO 这种鲁棒损失” — 原文只说这种分析“可能偏好”对超参不敏感的选择，并未明确说“系统性偏袒 PPO”。
- **[minor]** “首次大规模量化这些“隐藏选择”的影响” — 原文称进行了大规模实验研究，但没有明确声称这是“首次”。

## 🟠 [minor] What Matters In On-Policy Reinforcement Learning? A Large-Scale Empirical Study
`10.48550/arxiv.2006.05990` v1  (quality: ok)
- **[minor]** “把策略 MLP 最后一层权重初始化为 100× 更小(让初始动作分布近似与观测无关、均值居中 0、标准差较小)” — 原文说最后一层缩小主要使初始动作分布近似与观测无关并居中，较小标准差还需要通过 C61 的标准差偏置实现；总结把“标准差较小”也归因于最后一层缩放。

## 🟠 [minor] Decoupled Policy Actor-Critic: Bridging Pessimism and Risk Awareness in Reinforcement Lear
`10.1609/aaai.v39i18.34162` v1  (quality: trusted)
- **[minor]** “证明它们等价于指数效用下的风险感知优化” — 原文多处表述为“can be interpreted”和“approximately align”，不是严格等价证明，表述略过强。
- **[minor]** “悲观修正项 V^σ(critic 集成的标准差/分歧)恰好等于风险溢价(risk premium)” — 原文是在 Taylor 展开和高斯假设下作近似解释，且风险溢价表达涉及 β、方差和高阶项；“恰好等于”过强。
- **[minor]** “确定性等价价值 V^c(s) = E[U^{-1}(E U(V_i(s)))]” — 原文 Eq.5 没有这个外层期望，写法与原公式不一致。

## 🟠 [minor] A graph-based safe reinforcement learning method for multi-agent cooperation
`10.1016/j.neunet.2026.108693` v1  (quality: ok)
- **[minor]** “保持安全(硬约束式避碰)” — 原文的安全约束是累计折扣 cost 的期望上界，并非逐轨迹/瞬时避碰的硬保证，表述偏强。
- **[minor]** “n=9 时其他算法几乎都拿不到正奖励” — Table 5 中 n=9 的 InforMARL 奖励为 3160.61、GS-MARL(NPS) 为 1471.68，均为正；该概括容易误导。

## 🟠 [minor] An Algorithmic Perspective on Imitation Learning
`10.1561/2300000053` v1  (quality: ok)
- **[minor]** “DAGGER 可视作隐含逼近 I-投影目标的方法” — 原文只说 DAGGER 的解可能比普通监督学习在 I-projection KL 下更小，并未说它是在逼近 I-projection 目标。
- **[minor]** “欠驱动机器人打乒乓（DMP）” — 原文中 DMP 用于打球/ball-paddling 示例，欠驱动机器人打球示例则是 Englert et al. 的模型式方法，并非 DMP；这里混合了不同案例。
- **[minor]** “提供了一张清晰的二维分类表（BC/IRL × model-free/model-based × 任务级/轨迹级/动作-状态级）” — 原文是多个分类表分别讨论 BC/IRL、model-free/model-based 和抽象层级，并没有这样一张同时含这些维度的“二维分类表”。

## 🟠 [minor] From Reward Shaping to Q-Shaping: Achieving Unbiased Learning with LLM-Guided Knowledge
`arxiv:2410.01458` v1  (quality: flag)
- **[minor]** “定理 1 证明塑形后的 Q 函数仍是同一采样 MDP 上的收缩映射，收敛到与未塑形相同的局部最优 Q*” — 原文定理表述为在采样 MDP D 上 q̂ 和 q 更新并得到 q̂*_D = q*_D，但并未严格证明“塑形后的 Q 函数仍是收缩映射”这一因果说法，表述略强。
- **[minor]** “作者称奖励塑形为提成功率牺牲了最优性，Q-shaping 两者兼得” — 原文说 LLM 奖励塑形方法 often sacrifice optimality，而非必然“为提高成功率牺牲最优性”；总结把概率性表述写得更绝对。
- **[minor]** “再加 agent 选择略有改善（→215000 步）” — 表 2 中加入 agent selection 后 window-close 为 215000，但 sweep-into 从 860000 到 790000也改善，drawer-open 275000 到 265000，door-close 30000 到 25000；该例子本身正确，只是“略有改善”概括可接受但不精确。

## 🟠 [minor] Transformer-based human-motion forecasting coupled with safe reinforcement learning for te
`10.3389/fnbot.2025.1697518` v1  (quality: ok)
- **[minor]** “数据/代码:Zenodo 10.5281/zenodo.17034737” — 原文数据可用性声明只说数据集在 Zenodo，未声明代码也可用。
- **[minor]** “约束是 CBF 松弛率/近失率/撞墙率” — 原文写的是 CBF slack rate、near-miss rate 和 wall proximity breaches，不是明确的“撞墙率”。

## 🟠 [minor] Automatic Intrinsic Reward Shaping for Exploration in Deep Reinforcement Learning
`10.48550/arxiv.2301.10886` v1  (quality: trusted)
- **[minor]** “首次把内在奖励“选择”建模成多臂老虎机” — 原文只是将其列为第一项贡献并称“We formulate”，没有明确声称这是领域首次。

## 🟠 [minor] Challenges of real-world reinforcement learning: definitions, benchmarks and analysis
`10.1007/s10994-021-05961-4` v1  (quality: ok)
- **[minor]** “每条在 MDP/CMDP/POMDP/Robust MDP 框架下给出形式化定义” — 原文明确说除可解释性外才提供形式化定义/实验；把9条都说成逐条形式化略过强。
- **[minor]** “DMPO(分布式 MPO,EM 式策略迭代)” — DMPO 在原文中是 Distributional MPO，不是“分布式 MPO”。
- **[minor]** “最后把上述挑战(除安全和多目标外)组合成 Easy/Medium/Hard 三档叠加环境” — 组合挑战除安全和多目标外，也没有包含可解释性；原文列出的组合项是延迟、扰动、维度、噪声、卡死/丢失传感器等。
- **[minor]** “humanoid:walk 的 Medium/Hard 档回报掉到接近 1(满分约 1000),Easy 档也只剩百来分” — Easy 档“百来分”只符合 D4PG，DMPO 的 humanoid Easy 约为 1.33；表述容易误导为两个算法都如此。

## 🟠 [minor] Learning to Walk Via Deep Reinforcement Learning
`10.15607/rss.2019.xv.011` v1  (quality: ok)
- **[minor]** “实现真机从零学步” — 原文说从零在真机学习，但并未报告多次真机训练重复或“实现”稳定复现；该表述略强但核心有依据。
- **[minor]** “对偶梯度法在训练中自动调整——目标熵设为"每个动作维度 -1"即可,几乎免调参” — 原文只说明仿真基准中采用每动作维度 -1，且认为调参负担显著降低；“即可、几乎免调参”比原文更概括、更强。
- **[minor]** “在仿真基准上用单一超参达到 SOTA” — 原文称达到 state-of-the-art performance 且同一超参，但图3描述为与其他算法相似或更好；“达到 SOTA”可接受但略省略了相当/接近的限定。

## 🟠 [minor] Broad Critic Deep Actor Reinforcement Learning for Continuous Control
`10.1109/tnnls.2025.3554082` v2  (quality: ok)
- **[minor]** “提出 BCDA——首个把 BLS（critic）与 DNN（actor）混合的 actor-critic 框架” — 原文表述是“To our best knowledge/no prior research”，只支持作者自称首创，摘要写成客观“首个”略强。

## 🟠 [minor] Mirror Descent Safe Policy Optimization for Reinforcement Learning Agents.
`10.1109/tpami.2026.3674995` v1  (quality: trusted)
- **[minor]** “一阶法(FOCOPS/CUP/P3O)在实现时偷偷套用了 PPO 的 clip” — 原文明确批评 CUP 和 P3O 实现中使用/改写为 PPO clipping 相关目标，但没有明确说 FOCOPS 实现也套用了 PPO clip。

## 🟠 [minor] Hierarchical deep reinforcement learning: integrating temporal abstraction and intrinsic m
`title:ef3200782950c96e` v1  (quality: ok)
- **[minor]** “首批把分层时间抽象（options/SMDP）与内在动机整合进深度 RL、并在像素级 ATARI 上跑通的框架之一” — 原文只说作者提出 h-DQN 并在 Montezuma 上实验，没有声称这是“首批之一”。
- **[minor]** “成为后续分层 RL / 探索研究的标杆基线” — 这是后续领域影响判断，原文没有依据或相关表述。

## 🟠 [minor] Reward-Adaptive Reinforcement Learning: Dynamic Policy Gradient Optimization for Bipedal L
`10.1109/tpami.2022.3223407` v1  (quality: trusted)
- **[minor]** “上 12° 斜坡 HDPG 成功率比另两者高近 20%。” — 原文说12°时HDPG成功率比另两种RL算法高近20%，但未包括ZMP；总结句中的“另两者”在同一条前文比较了ZMP/DDPG/MHDDPG，指代略不清，可能扩大比较对象。
- **[minor]** “发布 3 个挑战(推力恢复/障碍/斜坡)” — 原文说“release 3 challenges”，但同时说明AIDA仿真器和HDPG代码是“will release later”；总结写“发布”容易把尚未发布/承诺发布写成已发布。

## 🟠 [minor] A survey of preference-based reinforcement learning methods
`10.5445/ir/1000118270` v1  (quality: ok)
- **[minor]** “沿七条设计原则横向切分并比较所有已知算法” — 原文第3节实际按6个设计原则小节组织，摘要这里的“七条”与其后列举也只对应6类，数字无原文依据。
- **[minor]** “把约 16 组算法按这些维度对齐” — 表2列出的算法/方法组为15组，不是约16组；属于小的数量偏差。
- **[minor]** “是后续(尤其 RLHF 时代)的奠基性参考” — 原文没有讨论RLHF时代，也没有声称自身是后续RLHF的奠基性参考，这是总结者加入的外部影响判断。

## 🟠 [minor] Recursively Feasible Probabilistic Safe Online Learning with Control Barrier Functions
`arxiv:2208.10733` v1  (quality: flag)
- **[minor]** “首次为动力学未知的系统给出 CBF 安全滤波器的递归可行性保证” — 原文是作者以“To our knowledge”限定的领先性宣称，且范围限定为“CBF应用于不确定动力学、在线采数据并提供递归可行性保证”，总结略去限定并写成既定事实。

## 🟠 [minor] JuggleRL: Mastering Ball Juggling with a Quadrotor via Deep Reinforcement Learning
`10.48550/arxiv.2509.24892` v1  (quality: ok)
- **[minor]** “基线:Müller 等人的开源基于模型预测规划器(MBPP)” — 原文只称采用 Müller 等人的 open-source model-based juggling baseline，并未明确说这是 Müller 方法本身的“开源预测规划器”；“开源”归属和表述略有强化。
- **[minor]** “MBPP 被迫用固定 apex 这一不利设定” — 原文说 MBPP requires a fixed target apex height to compute a feasible trajectory，但未将其评价为“不利设定”；这是总结者推断，若作为事实转述略强。

## 🟠 [minor] Scaling data-driven robotics with reward sketching and batch reinforcement learning
`arxiv:1909.12200` v1  (quality: flag)
- **[minor]** “非分布式 RL → 大幅劣于分布式（确认分布式价值函数对 batch RL 是 essential）” — 原文消融的是 non-distributional RL 与 distributional value functions，不是“分布式”训练/系统架构；中文术语容易误导。

## 🟠 [minor] Variational Dynamic for Self-Supervised Exploration in Deep Reinforcement Learning
`10.1109/tnnls.2021.3129160` v2  (quality: ok)
- **[minor]** “Theorem 1 证明它是 r^i = −log p(s′|s,a) 的上界，k 越大界越紧，且 k→∞ 时收敛到真值” — 原文的收敛结论带有条件“if w_i is bounded”，总结省略了该条件，表述略强。
- **[minor]** “Atari/Mario 用 5 个随机种子画均值±标准差” — 原文明确说明 5 个随机种子和均值±标准差的是 Atari 结果，未说明 Super Mario 也使用同样口径。

## 🟠 [minor] Sim-to-Real: Learning Agile Locomotion For Quadruped Robots
`10.15607/rss.2018.xiv.010` v1  (quality: ok)
- **[minor]** “用深度强化学习（PPO）在改进过的物理仿真里从零学出四足机器人 Minitaur 的敏捷步态（小跑 trotting、奔驰 galloping）” — 原文中 galloping 是从零学习，trotting 是用用户提供的开环参考信号引导学习，不是从零学出。
- **[minor]** “如何把仿真里学到的策略迁移到真实物理系统而不退化” — 原文主张可成功迁移/缩小 reality gap，但并未声称迁移后“不退化”，且 galloping 真实速度低于仿真速度。

## 🟠 [minor] Online Meta-Critic Learning for Off-Policy Actor-Critic Methods
`10.48550/arxiv.2003.05334` v1  (quality: ok)
- **[minor]** “元评论家额外开销约 15–30% 算力、10% 参数。” — 原文说训练时增加15–30%计算成本和10%参数量，但同时明确测试时无开销；总结未说明该开销仅限训练时，容易被理解为总体/测试也有开销。
- **[minor]** “引入可学习损失/奖励增加了复杂度与风险，自承学到的"奖励"可解释性/安全性是个待解问题。” — 原文 Broader Impact 讨论的是learnable reward functions及奖励函数分析风险，但本文方法实际是元评论家学习辅助loss；总结把作者自述局限转述为“可学习损失/奖励”和“学到的奖励”，有一定概念混用。

## 🟠 [minor] Mixture of Autoencoder Experts Guidance using Unlabeled and Incomplete Data for Exploratio
`10.48550/arxiv.2507.15287` v1  (quality: ok)
- **[minor]** “RND/ICM 在此几乎为 0 甚至负” — 表17中该说法只部分成立：Ant 为负、Walker2d 的 ICM 接近0，但 HalfCheetah 的 RND/ICM 为 52.79/56.64，Walker2d 的 RND 为 14.16，并非都“几乎为0甚至负”。
- **[minor]** “过高(0.3)把太多态当专家式→外在奖励崩(−1812)” — −1812.56 在表15对应的是 Lmin=0.03；原文正文/图注提到0.3，但这个数值与−1812的对应关系缺乏表格依据。

## 🟠 [minor] What Matters in RL-Based Methods for Object-Goal Navigation? An Empirical Study and A Unif
`10.48550/arxiv.2510.01830` v1  (quality: ok)
- **[minor]** “仿真器：Habitat；数据集：Gibson(检测器有 Gibson 微调权重)/MP3D(RedNet 微调)。” — 原文的导航实验和SotA对比是在Gibson benchmark上；MP3D只用于RedNet的微调数据，不是本文导航评测数据集，表述容易误导。
- **[minor]** “最后把每个模块的最优组件拼成 4 个定制策略” — 原文说四个策略采用各模块最佳配置，但表4中最高SPL是Continuous Action Policy 48.2%，而摘要后文把85.3% SR对应的Discrete Action Policy写成总体系统的47.5% SPL/85.3% SR，未说明这是不同指标下不同策略。
- **[minor]** “用各模块最优组件拼出的系统达到 47.5% SPL / 85.3% SR” — 表4中85.3% SR对应Discrete Action Policy且SPL为47.5%，但最高SPL是Continuous Action Policy的48.2%；若称总体最优系统，数字选择不完整且略有误导。

## 🟠 [minor] Safe Reinforcement Learning With Stability Guarantee for Motion Planning of Autonomous Veh
`10.1109/tnnls.2021.3084685` v1  (quality: ok)
- **[minor]** “输入近 l 步的稀疏激光雷达读数和历史动作” — 原文式(13)的碰撞概率模型输入包含当前激光读数和当前动作，以及历史读数/动作；总结表述成仅用历史动作，略有遗漏。
- **[minor]** “碰撞概率网络用 DDPG 策略生成的数据训练” — 原文说训练数据由随机动作生成，DDPG 策略生成的 100000 个 tuple 只用于测试准确率。

## 🟠 [minor] Safe Learning in Robotics: From Learning-Based Control to Safe Reinforcement Learning
`10.1146/annurev-control-042920-020211` v1  (quality: ok)
- **[minor]** “用同一开源基准证明三类方法可在统一接口下评估、并都能在保安全/约束的前提下提升控制性能” — 原文只说这些方法在追求约束满足的同时改进性能并展示基准支持，尤其3.2方法只是减少违规而非保证“保安全/约束”，表述偏强。
- **[minor]** “绝大多数方法只在抽象数值例/玩具问题验证,真实高维机器人迁移困难” — 原文说“many approaches”只在小型玩具问题验证且高维机器人应用不平凡，未说“绝大多数”，程度被加强。
- **[minor]** “各方法还各自经过离线超参优化(GP-MPC 80s 数据、安全探索调松弛变量、PPO 9 小时数据)” — 原文只明确GP-MPC离线超参优化用80秒数据；PPO相关方法是用超过9小时仿真数据训练，safe exploration需调松弛变量，未说这些都是离线超参优化。

## 🟠 [minor] Game-Theoretic Constrained Policy Optimization for Safe Reinforcement Learning
`10.1109/tnnls.2025.3586603` v1  (quality: ok)
- **[minor]** “GCPPO 在所有基准上都满足约束并取得最佳性能” — 表述过强；原文明确说 DoggoGoal1 中 CPO 的任务回报高于 GCPPO，只能说 GCPPO 在满足约束的方法中表现最好或整体安全性能最好。

## 🟠 [minor] Model-based Reinforcement Learning: A Survey
`10.1561/2200000086` v1  (quality: ok)
- **[minor]** “第 4 章把动力学模型学习当作监督学习问题,沿八个挑战展开” — 原文第4章是3个基本考虑加7个挑战，并未列出“八个挑战”。
- **[minor]** “给出模型基 RL 的清晰定义与三分类(已知模型 / 学得模型 / 仅在学得模型上规划)” — 原文把这三类称为planning-learning integration的三类，并明确“仅在学得模型上规划”不算model-based RL。
- **[minor]** “后续每个算法都被映射到这张图的子集上” — 原文只说多数算法实现这些连接的子集，并示例性映射部分算法，没有说每个后续算法都被映射。

## 🟠 [minor] Reinforcement Learning with Stochastic Reward Machines
`10.1609/aaai.v36i6.20594` v1  (quality: ok)
- **[minor]** “随机奖励函数与随机奖励机一一对应” — 原文只说随机奖励函数与建模它的SRM有“direct correspondence”以便叙述，并未证明或声称严格的一一对应关系；且同一奖励函数可由不同机器表示。
- **[minor]** “作者自述局限——噪声模型很窄” — 原文确实给出有界连续分布、已知ϵc和Assumption 1等假设，也提到相关工作噪声模型更丰富，但没有把这些自称为“局限”或“很窄”。

## 🟠 [minor] Safe Reinforcement Learning for Autonomous Vehicles through Parallel Constrained Policy Op
`10.1109/itsc45102.2020.9294262` v1  (quality: ok)
- **[minor]** “样本集 τᵢ 可行当且仅当 cᵢ>0 且 eᵢ=δ−bᵀH⁻¹b·cᵢ²<0” — 原文中的 eᵢ 公式是 δ−cᵢ²/(bᵀH⁻¹b)，总结把除法/分式误写成了乘法，且“当且仅当”比原文 only when 表述更强。

## 🟠 [minor] Safe Control Synthesis via Input Constrained Control Barrier Functions
`10.1109/cdc45484.2021.9682938` v1  (quality: ok)
- **[minor]** “若 C* 是 C_N 的严格子集,则 C* 内任意 Lipschitz 控制器(无需安全干预)都守得住” — 原文限定为取值满足 u(x)∈U 的 Lipschitz 控制器，并要求闭环解唯一；总结省略输入约束条件，表述略过强。
- **[minor]** “验证 b_N 是否为合法 ICCBF 要解一个全局非凸优化(min sup),本身可能困难、不保证全局最优” — 原文只说该优化一般是 nonlinear and non-convex，可用标准非线性优化软件求解；“全局”“可能困难”“不保证全局最优”不是作者明说的自述局限。

## 🟠 [minor] Input-to-State Safety for Reinforcement Learning.
`10.1109/tnnls.2026.3688045` v2  (quality: ok)
- **[minor]** “在数学上严格保证全程不越界” — 原文探索阶段的形式化证明是扩张集 C_{ξ,T} 前向不变，而不是真实安全集 C 在噪声下严格不越界；该表述把保证说得过强。

## 🟠 [minor] Value Bonuses using Ensemble Errors for Exploration in Reinforcement Learning
`arxiv:2602.12375` v1  (quality: flag)
- **[minor]** “Bootstrap DQN(BDQN)、Epinets 虽有首次访问乐观性” — 原文明确说 BDQN 通过固定先验提供 first-visit optimism，但对 Epinets 只说可匹配 BDQN 且更难实现，未明确声称其具备首次访问乐观性。
- **[minor]** “扫描集成规模 k∈{1,2,8,20}、bonus 缩放 c∈{1,3,10}” — 该超参数扫描主要对应经典控制/Deepsea设置；Atari 实验使用固定设置如 VBE/BDQN ensemble=10、c=10，把它写在总实验设置下略易误导。

## ✅ pass (10)
- End-To-End Robotic Reinforcement Learning without Reward Engineering (v2)
- Safe Reinforcement Learning with Probabilistic Control Barrier Functions for Ramp Merging (v2)
- VCSAP: Online reinforcement learning exploration method based on visitation count of state (v2)
- Improved Learning of Robot Manipulation Tasks Via Tactile Intrinsic Motivation (v1)
- Reinforcement Learning for Robust Parameterized Locomotion Control of Bipedal Robots (v2)
- Offline constrained policy optimization with safe anchoring. (v1)
- Causal-Paced Deep Reinforcement Learning (v1)
- Temporal Logic Guided Safe Reinforcement Learning Using Control Barrier Functions (v1)
- Comparing Deep Reinforcement Learning and Evolutionary Methods in Continuous Control (v1)
- Safe Off-Policy Deep Reinforcement Learning Algorithm for Volt-VAR Control in Power Distri (v2)
