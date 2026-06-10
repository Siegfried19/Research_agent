# Summary verification — rl-general-toolbox
_generated: 2026-06-10T22:17:51.799Z  checked: 7/7  pass: 3  minor: 4  major: 0  errors: 0_

核查员=Codex(跨模型,不共享撰写者的幻觉模式)。只核数字与论断依据,不评文笔。
本报告由 escalate_verify 汇总(多轮升级抽检,major 自动修正+复核;标注"需人工分诊"的为修正 2 次仍未通过)。

## 🟠 [minor] Constraint-Conditioned Policy Optimization for Versatile Safe Reinforcement Learning
`10.48550/arxiv.2310.03718` v2  (quality: trusted)
- **[minor]** “定理 1 给出 Q 估计误差上界 ∝ `z_{α/2}·B(p)/(N·β(p)) · √(σ²K_f²M)`” — 原文中衰减项是随 `N^{β(p)}` 变化，β(p) 是 N 的指数，不是分母里的 `N·β(p)`。

## 🟠 [minor] AFU: Actor-Free critic Updates in off-policy RL for continuous control
`10.48550/arxiv.2404.16159` v3  (quality: ok)
- **[minor]** “却是第一个真正脱离 actor-critic 范式的有竞争力的 model-free 离策略算法” — 原文把“第一个”表述为“to the best of our knowledge/as far as we know”的作者认知性声明，摘要此处写成了确定事实。

## 🟠 [minor] ReLU to the Rescue: Improve Your On-Policy Actor-Critic with Positive Advantages
`10.48550/arxiv.2306.01460` v2  (quality: ok)
- **[minor]** “Gymnax/Brax/MinAtar/Classic Control 等用贝叶斯优化...在固定的几个环境上搜参后用于该套环境” — 原文只明确说 Brax-MuJoCo 只在 Humanoid、Hopper、Reacher 上调参；对 MinAtar 和 Classic Control 并未说明是在“固定的几个环境”上搜参。
- **[minor]** “说明谱归一化只在低线程数有利” — 原文说谱归一化在低线程/无法大量并行时有益、在高度并行设置中有害；“只在低线程数有利”表述略绝对。
- **[minor]** “逐环境(Brax,9 个环境...); 与 DPO 整体相当(平均 rank DPO 1.44 < VSOP 1.76 < PPO 1.83 < A3C 2.50)” — 这些 rank 数字来自 Table 9 的跨 Brax-MuJoCo、MinAtar、Classic Control 的总体 Avg. Rank，不是 Brax 9 个环境单独的平均 rank。

## 🟠 [minor] Humanoid Manipulation Interface: Humanoid Whole-Body Manipulation from Robot-Free Demonstr
`arxiv:2602.06643` v1  (quality: flag)
- **[minor]** “低层 RL 引入...“变速增强”（episode 内随机放慢回放速度，给策略时间纠正小误差）” — 原文说速度缩放因子在区间内随机采样，附录给出约为0.25到1.25的采样范围，不只是“放慢”回放速度。
- **[minor]** “每任务一般 20 次 rollout 评测主结果，消融多为 10 次。” — 原文能力实验的4个主任务确为20次，消融多为10次，但“每任务”会误覆盖泛化任务；泛化是4个测试环境各5次共20次，非每个任务一般20次。
- **[minor]** “...所有任务还都在 in-domain 同一环境同一初始配置下评测...” — 原文只说能力实验在与数据采集相同的环境和初始机器人-物体配置下评测；但清洁任务明确初始距离1–2m、yaw在[-45°,45°]采样，不能概括为所有任务同一初始配置。

## ✅ pass (3)
- Multimodal bipedal locomotion generation with passive dynamics via deep reinforcement lear (v2)
- Learning Complex Dexterous Manipulation with Deep Reinforcement Learning and Demonstration (v2)
- The Role of Domain Randomization in Training Diffusion Policies for Whole-Body Humanoid Co (v2)
