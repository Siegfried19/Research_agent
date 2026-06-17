# Summary verification — rl-digital-human-interaction
_generated: 2026-06-10T18:26:46.364Z  checked: 13/13  pass: 2  minor: 4  major: 7  errors: 0_

核查员=Codex(跨模型,不共享撰写者的幻觉模式)。只核数字与论断依据,不评文笔。

## 🔴 [major] Simulating User Agents for Embodied Conversational-AI
`10.48550/arxiv.2410.23535`  (quality: ok)
- **[major]** “RoBERTa-B 微调 62.48%（最高，但只能分类不能生成回复，且仍低于 Gella 2022 全量微调的 59.26%）” — 62.48%不可能低于59.26%，总结把数字关系写反了；原文表2给RoBERTa为62.48%，并提到Gella为59.26%。
- **[minor]** “DA Accuracy 在去 move 后 FS 从 40.82% 升至 54.06%” — 原文中40.82%是无move的zero-shot DA Accuracy，54.06%是无move的few-shot；不是few-shot自身从40.82%升至54.06%。

## 🟠 [minor] Reinforced Imitation in Heterogeneous Action Space
`arxiv:1904.03438`  (quality: flag)
- **[minor]** “状态编码器为 5 层 CNN（kernel 3，残差连接）...判别器...2 层 MLP（256 隐元）” — 这些网络数字只适用于网格世界部分；ViZDoom 的判别器是 3 层 CNN、MLP 隐元为 64，原文并未把 5 层 CNN/256 隐元作为全部实验的统一设置。
- **[minor]** “目标/agent/陷阱每个 episode 随机布置” — 原文主文这样概括，但附录说明 P grid world 的陷阱是固定成 4 个房间、通道随机；该句若覆盖两个网格世界则过强。
- **[minor]** “清单中也标注 relevance=38” — 原文没有 relevance 指标，也没有 38 这个数字。
- **[minor]** “引用数为 0” — 原文没有引用数信息；该数字不属于论文正文依据。

## 🟠 [minor] Human pose, hand and mesh estimation using deep learning: a survey
`10.1007/s11227-021-04184-7`  (quality: ok)
- **[minor]** “DetectNet（Mask R-CNN）出框，RootNet...PoseNet...；均用 L1 损失” — 原文中 RootNet 和 PoseNet 用 L1 损失，但 DetectNet/Mask R-CNN 使用分类、框和 mask 损失，不是均为 L1。
- **[minor]** “首次把 3D 人手姿态与人体网格估计纳入 HPE 综述” — 原文只说区别于其列举的既有综述、previous ones 未包含这些内容，未严格证明或明确宣称整个领域“首次”。
- **[minor]** “疑似为投稿该刊凑引用” — 原文可见参考文献中有不少 J Supercomput/非 HPE 论文，但“为投稿该刊凑引用”的动机没有原文依据。
- **[minor]** “相关性评分 30 是合理的” — 原文没有任何相关性评分或与该研究主题打分的依据。

## 🔴 [major] Goal-conditioned Batch Reinforcement Learning for Rotation Invariant Locomotion
`arxiv:2004.08356`  (quality: flag)
- **[major]** “增强类方法用 1M on-policy + 1M 等价样本凑齐。” — 原文只明确 Ant 是 1M 原始+1M 增强；Minitaur 总预算为 4M，按“same as Ant”应为 2M+2M，不能概括为所有增强类方法都是 1M+1M。
- **[minor]** “指标在 10 个随机种子 × 每种子 1000(正文写 100 runs)回合上取均值/标准差” — 原文正文写 averaged over 100 runs on 10 random seeds，附录写每个随机种子 1000 episodes；总结把两种口径并列可以，但“正文写100 runs”不是“每种子100”，且实际总数存在未消解矛盾。
- **[minor]** “标准差还很大(如 Humanoid 0.98),三法名次是否稳健难说。” — 原文没有显著性检验或名次稳健性的讨论，这是总结作者的质疑而非论文依据；若作为事实核查应标明为评论推断。
- **[major]** “正文 0.5、A.7 又出现 2–5 单位的目标距离” — 0.5 出现在附录定性实验的达成阈值，不是正文；2–5 是测试目标初始距离，不是“到达阈值口径”，这里混淆了两个不同量。
- **[minor]** “目标空间被极度简化,夸大了"任意方向":测试目标只在 ±45° 扇区、2–5 单位近距” — ±45°测试设定有原文依据，但“夸大任意方向”“本质是短程、近似正前方”是总结作者的批评推断，不是作者在原文中的结论。
- **[minor]** “没有任何与环境/物体的真实交互、操作、接触控制” — 论文讨论 locomotion 中的 contact costs，称“没有任何接触控制”表述过强；原文确实没有物体操作或人交互，但不能说没有接触相关控制。
- **[minor]** “缺乏更大规模、更长训练、与更强离线 RL(如 BCQ/CQL)对照的验证” — 原文没有讨论 CQL，且 CQL 不是本文发表时已有的对照；这是外部评价，不是论文内容依据。

## 🔴 [major] Human-in-the-Loop Reinforcement Learning: A Survey and Position on Requirements, Challenge
`10.1613/jair.1.15348`  (quality: trusted)
- **[minor]** “Table 2 给出 12 类 xAI 技术” — 原文 Table 2 实际列出 10 类 xAI 技术，不是 12 类。
- **[minor]** “可解释性(explainability,主动生成决策相关解释)vs 可解释性/可读性(interpretability,模型本身被动可懂)” — 原文区分的是 explainability 与 interpretability；总结中文把两者都写成“可解释性”，容易造成概念错配，但核心含义大体有据。
- **[minor]** “Habibian 等研究机器人提问如何影响信任” — 原文说 Habibian 等研究机器人提问如何影响训练者对机器人的感知、偏好、可回答性和任务不确定性聚焦，未明确表述为“影响信任”。
- **[major]** “PGExplainer 聚焦相关子图” — 所给原文中未出现 PGExplainer；只提到图解释/PGM/GNN 等相关方法，把具体技术名写成作者推荐缺乏原文依据。
- **[minor]** “整篇没有一个真实系统按此框架走完并量化收益,"性能显著提升"这类断言因此是被过度延伸的。” — 总结中批评“性能显著提升”这类断言，但论文原文并未对四阶段框架本身声称有真实系统量化出性能显著提升。
- **[major]** “相关性评分 26 是合理的” — 论文原文没有“相关性评分 26”这一数字或评分依据，属于总结外加内容。

## 🟠 [minor] Mobile-TeleVision: Predictive Motion Priors for Humanoid Whole-Body Control
`10.1109/icra55743.2025.11128652`  (quality: trusted)
- **[minor]** “上下半身各 12 个下肢关节” — 原文只说 H1 和 GR1 两个平台的下半身各有 12 个关节；总结表述容易误导为上、下半身各 12 个。

## 🔴 [major] Noise-conditioned Energy-based Annealed Rewards (NEAR): A Generative Framework for Imitati
`10.48550/arxiv.2501.14856`  (quality: ok)
- **[minor]** “RL 从最低噪声等级（实为最大 σ，奖励覆盖最广）开始” — 原文算法初始化为 σ1，且文中定义 σ1 是最大噪声、σL 是最小噪声；把它称为“最低噪声等级”会混淆原文表述。
- **[minor]** “每次取 20 个 episode 的均值” — 原文说评估取 20 个最高奖励轨迹/环境，并非普通的 20 个 episode 均值。
- **[minor]** “给出能量函数平滑性的理论证明（Appendix A，基于高斯卷积平滑性与万能逼近定理）” — Appendix A 证明的是在扰动样本流形内平滑，并依赖假设与近似；总结表述成一般“能量函数平滑性证明”略强。
- **[minor]** “只对比单一基线 AMP” — 原文主实验确实只实测对比 AMP，但总结中的“只对比单一基线”作为批判成立；无问题。
- **[major]** “相比 AMP/CALM 这类能驱动角色与场景物体交互的工作” — 原文只把 CALM列为相关对抗式方法引用，并未讨论 CALM 能驱动角色与场景物体交互，这一比较属于总结作者外加内容，缺乏本文依据。

## 🟠 [minor] Physics-based character animation and human motor control.
`10.1016/j.plrev.2023.06.012`  (quality: ok)
- **[minor]** “首次系统性地把 PBCA 与运动神经科学并置对照” — 原文说明两领域交叉引用少并提出本综述，但没有声称这是“首次”。
- **[minor]** “GAIL/判别器([103,142])免奖励设计” — 原文中“无需奖励设计”明确对应[142]，而[103]主要是用判别器模仿多种参考动作，概括到两者略过强。
- **[minor]** “引用 0 次、2023 年发表” — “引用0次”不在论文原文中，出现在非元信息正文里没有原文依据。
- **[minor]** “2023 后的物理角色+扩散/大模型路线” — 原文没有讨论扩散模型或大模型路线，这是外部时效性评论而非论文内容。

## 🔴 [major] A GAN-Like Approach for Physics-Based Imitation Learning and Interactive Control
`10.1145/3480148`  (quality: ok)
- **[minor]** “动作空间：每个关节的目标姿态作为 PD 伺服控制信号；旋转关节 1 维角度，球关节 4 维轴角” — 原文说球关节目标姿态是4维轴-角格式，但实验设置又明确将球关节控制信号建模为四元数；总结写成“4维轴角”不准确。
- **[minor]** “抗扰动只与单一基线 DeepMimic 比，立方体初速仅 0.2m/s 且面向躯干，扰动设置偏温和” — 原文说立方体初始速度是0.2m/s，但质量在5、10、15、20kg变化且每帧发射，不能仅凭原文推出“扰动设置偏温和”，这是总结者的主观评价。
- **[major]** “还得靠 motion matching 在预处理阶段挑选可组合的片段” — 原文只是说motion matching技术可用于预处理阶段检查两段动作相似性，并非本文实验“还得靠”它或实际使用了它。
- **[minor]** “模仿误差用全局位置 L2，但作者承认无相位同步会导致早期小误差累积放大，于是“按一个运动周期计算并多初始姿态试验”——这种度量口径有自我有利之嫌” — 前半句有原文依据，但“自我有利之嫌”是总结者的推断，不是作者论断或实验事实。
- **[minor]** “所有数据来自单一数据集 LAFAN1、单一 45kg 角色，没有不同体型/不同环境/sim-to-real 的验证” — LAFAN1和45kg角色有依据，但“没有不同体型/不同环境/sim-to-real验证”是从论文未报告中推断，原文没有将其列为结果或局限。

## 🔴 [major] Robot Skill Learning: From Reinforcement Learning to Evolution Strategies
`10.2478/pjbr-2013-0003`  (quality: trusted)
- **[major]** “复用 Theodorou 等人 [36] 的同一套 5 个任务” — 原文附录明确说 Task 3 未被 Theodorou 等人 [36] 评估，是本文作者新增的任务，因此不是完全复用同一套 5 个任务。
- **[minor]** “最终代价更低” — 原文表述是 final costs similar or lower / lower or same，部分任务相同或无显著差异，概括为“更低”过强。
- **[minor]** “全部结论建立在 5 个低维、纯仿真、运动学（非动力学）的玩具任务上” — 原文说明 Task 4/5 是运动学模拟手臂，但没有把全部 5 个任务概括为“纯仿真、运动学、玩具任务”，该评价性外推缺少直接原文依据。

## 🔴 [major] Humanoid Whole-Body Manipulation via Active Spatial Brain and Generalizable Action Cerebel
`arxiv:2605.21133`  (quality: flag)
- **[minor]** “Easy 设置本方法在 Task1/3/4/5 上领先” — Table 1 中 Easy Task4 本方法为 80.0，与 CaP 的 80.0 持平，并非领先所有基线。
- **[major]** “TrajBooster(40/20/10/0/20)、Ψ0(60/35/25/0/30)、CaP(65/50/35/30/35)” — Hard 设置基线数字多处抄错；原文 Table 1 分别是 TrajBooster 20/40/10/0/20，Ψ0 35/45/25/0/30，CaP 50/55/35/30/35。
- **[major]** “去掉主动感知(AP)Task3 类性能大跌(高度+位置 18.8 vs 完整 67.5); 去掉 EES 也明显下降(避障 33.4 vs 70.0)” — Table 3 的消融归因写反/写错：18.8 是 AP 和 EES 都去掉；仅去掉 AP 是 24.9/33.4，仅去掉 EES 是 55.6/16.7。
- **[minor]** “成功率以 5/10 的粒度跳动” — 原文只说每设置 10–30 次试验，并未说明成功率必然按 5 或 10 个百分点跳动；且 Table 3 出现 55.6、18.8、24.9、33.4、16.7 等非 5/10 粒度数字。

## ✅ pass (2)
- Embodiment-Aware Generalist Specialist Distillation for Unified Humanoid Whole-Body Contro
- Learning Agile Robotic Locomotion Skills by Imitating Animals
