# Summary verification — rl-general-toolbox
_generated: 2026-06-16T01:58:51.109Z  checked: 13/97  pass: 5  minor: 8  major: 0  errors: 84_

核查员=Codex(跨模型,不共享撰写者的幻觉模式)。只核数字与论断依据,不评文笔。

## 🟠 [minor] Constraint-Conditioned Policy Optimization for Versatile Safe Reinforcement Learning
`10.48550/arxiv.2310.03718` v2  (quality: trusted)
- **[minor]** “定理 1 给出 Q 估计误差上界 ∝ `z_{α/2}·B(p)/(N·β(p)) · √(σ²K_f²M)`” — 原文公式的分母是 `N^{β(p)}` 而不是 `N·β(p)`，误差随 N 的下降形式被写错。

## 🟠 [minor] Secrets of RLHF in Large Language Models Part I: PPO
`10.48550/arxiv.2307.04964` v2  (quality: ok)
- **[minor]** “中文 Harmless 上 RLHF 也明显占优；但中文 Helpful 上优势不明显（RLHF 胜 46%、负 23%、平 31%）” — 图10a显示中文 Helpful 为胜46%、平23%、负31%，总结把平/负写反；且中文 Harmless 为胜39%、平29%、负32%，优势反而弱于中文 Helpful，'Harmless明显占优、Helpful优势不明显'这一对比不符合图中数据。

## 🟠 [minor] Multimodal bipedal locomotion generation with passive dynamics via deep reinforcement lear
`10.3389/fnbot.2022.1054239` v2  (quality: trusted)
- **[minor]** “Table 3,7 个观测各加噪、每条件 10 次试验” — Figure 6 和 Table 3 实际列出 8 类加噪观测量（ẋ、θ、θ̇、ϕ、ϕ̇、h、ḣ、ḋ），不是 7 类；每条件 10 次试验有依据。
- **[minor]** “去 1/(1+ωv) 后期崩溃(约 6M 步后变不稳、8M 步后立刻摔)” — 原文说奖励在 6M 后逐渐降到 0、约 7M 步变不稳定、8M 后立刻摔；把“不稳定”提前到约 6M 步略有偏差。

## 🟠 [minor] Input-to-State Safety for Reinforcement Learning.
`10.1109/tnnls.2026.3688045` v2  (quality: ok)
- **[minor]** “在数学上严格保证全程不越界” — 原文探索阶段的 Theorem 1 形式化保证的是扩张集 C_{ξ,T} 在有界探测噪声下前向不变，而不是严格证明轨迹始终不越过原始安全集 C 的边界；“全程不越界”表述过强。

## 🟠 [minor] Learning Complex Dexterous Manipulation with Deep Reinforcement Learning and Demonstration
`10.15607/rss.2018.xiv.049` v2  (quality: ok)
- **[minor]** “搬运任务 DAPG 比从零快约 30 倍” — 表 I 中搬运任务是 5.77h vs 98h，约 17 倍；论文正文虽有 almost 30 times 的说法，但与表格数据不符，总结不应把它作为表 I 支持的事实。

## 🟠 [minor] AFU: Actor-Free critic Updates in off-policy RL for continuous control
`10.48550/arxiv.2404.16159` v3  (quality: ok)
- **[minor]** “却是第一个真正脱离 actor-critic 范式的有竞争力的 model-free 离策略算法” — 原文只说“据作者所知/As far as we know”是第一个，且限定为与 SOTA 在样本效率上 competitive；总结这里省略了作者知识范围限定，表述略强。

## 🟠 [minor] CVaR-Constrained Policy Optimization for Safe Reinforcement Learning
`10.1109/tnnls.2023.3331304` v2  (quality: ok)
- **[minor]** “正文 Fig.3 学习曲线展示的是 5 个随机种子的均值±方差(图注口径)” — 原文 Fig.3 图注写的是 5 个随机种子的均值和标准差，不是方差。
- **[minor]** “Table II 只列了 TRC 与 CVaR-CPO 两个方法,且列的是 reward / cost / CVaR-cost 三类指标” — 原文 Table II 只列 TRC 与 CVaR-CPO 的 Score 和 Cost 两类列；前文说明该 Cost 是 CVaR metric，并没有单独的 reward/cost/CVaR-cost 三类指标。

## 🟠 [minor] Deep Reinforcement Learning That Matters
`10.1609/aaai.v32i1.11694` v1  (quality: trusted)
- **[minor]** “论文给出了策略梯度定理与各方法的优化目标公式” — 原文给出通用策略梯度公式以及TRPO/PPO的优化形式，但没有分别给出DDPG和ACKTR的优化目标公式，表述略过强。
- **[minor]** “成为后续 RL 实证方法学(如多种子评测、报告标准)的奠基性参考” — 这是对论文后续历史影响的外部评价，原文中没有依据。

## ✅ pass (5)
- Safe Reinforcement Learning with Probabilistic Control Barrier Functions for Ramp Merging (v2)
- Reinforcement Learning for Robust Parameterized Locomotion Control of Bipedal Robots (v2)
- The Role of Domain Randomization in Training Diffusion Policies for Whole-Body Humanoid Co (v2)
- Safe Off-Policy Deep Reinforcement Learning Algorithm for Volt-VAR Control in Power Distri (v2)
- VCSAP: Online reinforcement learning exploration method based on visitation count of state (v2)

## ⚙️ 未能核查 (84)
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_xzy10w59\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_t285cbmd\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_kux_a6rq\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_bp1tomsz\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_xup8hc4u\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_j5l26iv7\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_r423p9ec\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_v4tyr6mg\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_6h2rugnd\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_vi2vuf2n\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_4pic4s4w\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_i_eds6tx\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_65ug7332\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx__7wm6x3d\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_b0n1n510\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_5_xife8e\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_z1syq3m8\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_izwu3tnb\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_x1_hsztk\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_0_9c7rio\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_nzhe7u9q\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_7euck9yx\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_rhjwzdnm\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_eaqnz5gr\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_h00c5ur7\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_5wjt5hgt\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_wlzrdxns\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_n9kheor9\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_wrhwtgdo\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_08945ido\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_go2m06o5\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_8rldmrpm\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_c5ljava_\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_v7vawvcl\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_x8p63gs0\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_s11pkwgm\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_46nzh7v_\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_wiqt_hlm\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_sbak816p\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_j9o4uvm7\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_bf9_1d4_\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_szhflxlq\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_vlh2kitu\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_wi7ueno_\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_l2f7ns8e\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_0ubzl65h\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx__ryrrxus\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_0u67_bei\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_whuz_5al\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_n4ne0x7p\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_9qjrk12s\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_f63qz45y\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_rld4abur\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_5mq3zd3d\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_loh9ov9c\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_0y4ihwhx\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_9tb_9yn8\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_p7c6wrxl\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_6u52r3nm\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_o1bocn6a\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_mto1s9r3\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_junhtzux\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_urmsuxk4\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_72y2paym\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_g7xulu3d\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_0clrmdoh\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_952955ml\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_sm_vht5p\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_6akpfow_\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_fqvout7s\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_q_bal_gy\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_f27q0r6b\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_5n6q5nqw\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_8c7rjl1w\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_b3illq35\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_rcxw9fgk\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_iw5xx8x2\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_5u4vkqlp\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_fbuiqat9\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_ba4l918p\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_k24k2vdj\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_q3lvjisy\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_3cje4cl0\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
- {"error": "codex exec exit 1: OpenAI Codex v0.139.0\n--------\nworkdir: /tmp/vfy_cdx_9dt1npt0\nmodel: gpt-5.5\nprovider: openai\napproval: never\nsand
