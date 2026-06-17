# Summary verification — rl-digital-human-interaction
_generated: 2026-06-16T00:35:40.301Z  checked: 3/3  pass: 2  minor: 0  major: 1  errors: 0_

核查员=Codex(跨模型,不共享撰写者的幻觉模式)。只核数字与论断依据,不评文笔。

## 🔴 [major] Synthesizing Diverse Human Motions in 3D Indoor Scenes
`10.1109/iccv51070.2023.01354` v2  (quality: trusted)
- **[major]** “Hassan et al. 用物体位置/朝向/包围盒，PADL 用目标物体状态。三者都属于把场景作为特权信息直接喂给策略” — 原文只描述本文使用可行走性地图和 SDF 特征，未说明 Hassan et al. 或 PADL 的状态设计，也未提出“特权信息”这一三方归纳。
- **[major]** “Hassan et al. ... 仅用 7 个物体的少量示范泛化到约 350 个物体” — 原文仅在相关工作中简短提到 Hassan et al. [16] 可生成搬箱/坐椅交互，没有 7 个物体或约 350 个物体等数字。
- **[major]** “其报告坐 90.4%、躺 90.2% 成功率、约 6.7/13.4 cm 精度，并对外力扰动鲁棒” — 这些 Hassan et al. 的成功率、精度和扰动鲁棒性数字完全不在本文 PDF 中。
- **[major]** “本文与 Hassan et al. 都用 SAMP 的坐/躺数据、都在 ShapeNet 物体上做泛化评测（本文 10 个未见物体，Hassan et al. 约 350 个、16/5 个未见物体测试）” — 本文的 10 个未见 ShapeNet 物体有依据，但关于 Hassan et al. 使用 SAMP、约 350 个物体和 16/5 个未见物体测试均无原文依据。
- **[major]** “PADL 的高层任务实为 BERT 多选、技能为 CLIP 最近邻条件化” — 原文只在相关工作和参考文献中提到 PADL/语言选择，没有 BERT、CLIP、最近邻条件化等细节。

## ✅ pass (2)
- The Role of Domain Randomization in Training Diffusion Policies for Whole-Body Humanoid Co (v2)
- Learning Complex Dexterous Manipulation with Deep Reinforcement Learning and Demonstration (v2)
