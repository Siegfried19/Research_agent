# Summary verification — rl-general-toolbox
_generated: 2026-06-20T18:11:05.203Z  checked: 3/15  pass: 0  minor: 3  major: 0  unverifiable: 0  errors: 12_

核查员=Codex(跨模型,不共享撰写者的幻觉模式)。只核数字与论断依据,不评文笔。
⚠️ **本轮因 codex 侧问题（quota_exhausted）中止**,部分篇未核(已发 Telegram)——待恢复后重跑 verify 即从断点续核。
本主题尚有 **16** 篇待核查。本报告由 escalate_verify 汇总(多轮升级抽检,major 自动整篇重新总结+复核;标注"需人工分诊"的为重做 2 次仍 major)。

## 🟠 [minor] Scaling data-driven robotics with reward sketching and batch reinforcement learning
`arxiv:1909.12200` v2  (quality: flag)
- **[minor]** “消融三:分布式值函数是必需的。换成非分布式 RL 后大幅变差” — 原文说的是 distributional value functions / non-distributional RL（价值分布建模）而不是 distributed/非分布式并行 RL；结果方向正确，但术语容易把消融对象说错。

## 🟠 [minor] Lazy Agents: A New Perspective on Solving Sparse Reward Problem in Multi-agent Reinforceme
`title:4767e85b9c83c66b` v2  (quality: trusted)
- **[minor]** “规模:实验最多约 8–9 个智能体” — 原文表1的SMAC任务包含MMM/MMM2，己方单位为1 Medivac+2 Marauders+7 Marines，即10个智能体；“最多约8–9个”低估了实验规模。

## 🟠 [minor] Variational Dynamic for Self-Supervised Exploration in Deep Reinforcement Learning
`10.1109/tnnls.2021.3129160` v2  (quality: ok)
- **[minor]** “内在奖励与优势都做了 batch 归一化(均值0方差1)以稳定训练” — 原文只明确说优势在 batch 内归一化到均值0、标准差1；内在奖励是用折扣奖励和的运行标准差做平滑/缩放，不是同样的 batch 均值0方差1归一化。


## ⚙️ 未能核查 (12)
- {"id": "10.1561/2300000053", "version": 2, "title": "An Algorithmic Perspective on Imitation Learning", "slug": "An_Algorithmic_Perspective_on_Imitati
- {"id": "10.1609/aaai.v34i04.6144", "version": 1, "title": "Mastering Complex Control in MOBA Games with Deep Reinforcement Learning", "slug": "Masteri
- {"id": "10.1016/j.neucom.2024.128033", "version": 1, "title": "Self-supervised network distillation: An effective approach to exploration in sparse re
- {"id": "10.1016/j.neunet.2026.108865", "version": 1, "title": "Offline constrained policy optimization with safe anchoring.", "slug": "Offline_constra
- {"id": "10.1016/j.apenergy.2021.117164", "version": 1, "title": "Experimental evaluation of model-free reinforcement learning algorithms for continuou
- {"id": "10.1038/s41598-026-44517-1", "version": 1, "title": "Self-Organizing Dual-Buffer Adaptive Clustering Experience Replay (SODACER) for safe rein
- {"id": "10.48550/arxiv.2310.05858", "version": 1, "title": "Distributional Soft Actor-Critic with Three Refinements", "slug": "Distributional_Soft_Act
- {"id": "10.48550/arxiv.2307.04964", "version": 1, "title": "Secrets of RLHF in Large Language Models Part I: PPO", "slug": "Secrets_of_RLHF_in_Large_L
- {"id": "10.48550/arxiv.2505.08078", "version": 1, "title": "What Matters for Batch Online Reinforcement Learning in Robotics?", "slug": "What_Matters_
- {"id": "10.3389/fnbot.2022.1054239", "version": 1, "title": "Multimodal bipedal locomotion generation with passive dynamics via deep reinforcement lea
- {"id": "10.48550/arxiv.2601.12008", "version": 1, "title": "Extreme Value Policy Optimization for Safe Reinforcement Learning", "slug": "Extreme_Value
- {"id": "10.1016/j.automatica.2022.110684", "version": 1, "title": "Safe exploration in model-based reinforcement learning using control barrier functi
