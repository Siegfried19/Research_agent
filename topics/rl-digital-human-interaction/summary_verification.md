# Summary verification — rl-digital-human-interaction
_generated: 2026-06-10T04:31:50.265Z  checked: 2/2  pass: 0  minor: 1  major: 1  errors: 0_

核查员=Codex(跨模型,不共享撰写者的幻觉模式)。只核数字与论断依据,不评文笔。

## 🔴 [major] Real-World Humanoid Locomotion with Reinforcement Learning
`arxiv:2303.03381`  (quality: flag)
- **[major]** “面对训练中未见的下坡会自动切换为小碎步、再恢复正常行走” — 原文的训练域随机化包含 smooth slopes，不能说下坡在训练中未见；原文只说这种行为变化未被预先指定。
- **[minor]** “引用数 0(条目记录) · DOI 无” — 原文没有提供引用数或 DOI 信息，引用数 0 不是论文原文可核验的数字。

## 🟠 [minor] Beyond Words: Infusing Conversational Agents with Human-like Typing Behaviors
`10.1145/3640794.3665560`  (quality: ok)
- **[minor]** “Jijie Zhou, Yuhan Hu · 2025 · arXiv · 引用 0” — “引用 0”在原文中没有依据，属于外部元数据或编入内容。
- **[minor]** “发现同时具备这两种行为的 agent 被用户感觉更自然、更像人、更可信” — 原文摘要提到 trustworthiness，但实验量表和结果未报告可信度指标；把实验发现表述为“更可信”依据不足。
- **[minor]** “Red(犹豫+自editing)在自然度...上略高于 Blue, 方向上支持 H3、H4” — H3/H4分别对应 human-likeness 和 competence，不包括自然度、友好度；把这些指标统称为支持 H3/H4 表述略混。
- **[minor]** “量化指标自定义改编” — 原文说量表改编自 UEQ 和 HRIES，并非完全自定义；该说法略有歪曲。

