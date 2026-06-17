---
name: score-drift-external-research
description: 2026-06-17 起的 deep-research 调研：LLM 打分跨批次校准漂移的成熟解法 + 用 LLM 做文献筛选的更 general 范式
metadata: 
  node_type: memory
  type: project
  originSessionId: ea62bf0a-79ea-433d-8eeb-c29d95f72f4e
---

2026-06-17：在落码修打分漂移前，用户要求先做外部调研（"最好顺便调研让 LLM 找文献这种，一个更 general 的方法"）。用 deep-research workflow 拉带引用报告，两个核心问题：

① 具体：每批独立 pointwise 打绝对分 → 跨批次校准漂移的成熟缓解法。覆盖 anchored rubric/few-shot 锚点、pairwise/listwise vs pointwise 的稳定性证据、批内位置/顺序偏置、边界重排/两段式、以及"绝不逐批 z-norm"这类校准陷阱。
② general：用 LLM 做文献发现+筛选+排序构建语料库的当前最佳范式——LLM-as-screener 在系统综述自动化里的可靠性、embedding+cross-encoder reranker 检索式范式、有没有比"pointwise 打分再截断"更好的整体架构。
要求标出哪些方法适合"curated 小语料/每周增量/每天~20篇/两年后几万篇"的规模演进。

**调研已完成（2026-06-17），结论 + 方案修订落在 `docs/score-drift-research-findings.md`（durable，/tmp 报告会清）。** 核心：
- 漂移学名 = **rubric execution drift**（RULERS 2601.08654）；缓解三件套 = 锁死固定 rubric(含 score anchors) + 证据接地 + 截断线事后校准。
- **保留 0-100 pointwise 是对的**（"Likert or Not" 2505.19334：大有序刻度让 pointwise≈listwise；换 pairwise 在边界反而放大 style 噪声 2504.14716）。
- 三步修法侧重调整：**②锚点升为头号主力**（顺手修 rubric 硬编码 bug + 固定头部塞3锚点 + 加证据接地）；①加批量降为次要(好处是减接缝非提质、且增位置偏置→批内洗牌)；**③边界重排升级**=同一次调用+多次自一致采样+**取分数均值**(2505.12570/2503.03064)。
- **z-norm 禁令被佐证**；**现在别为打分上 reranker/换 pairwise**（reranker 是几万篇规模才需要，与检索层那条线汇合）。
- 落码前待拍**已全定**(2026-06-17)：范围=**(a) 只保截断线去留**(内部rank stakes低+下游评分系统兜底)；锚点=**3张真论文**(高95/边界45/低10,偏经典)；③ band=±8 / k=5；冷启动=裸跑→提名→**Telegram+终端**确认→重打整池([[human-gate-telegram]])。

**第一步核心修法已实现+三层验证通过(2026-06-17,未提交,在工作区;备份/tmp/score_auto.py.bak)**：改 `score_auto.py`——②prompt重写(GENERIC_BANDS主题无关骨架替掉硬编码+anchor_block注入topic.json.score_anchors+证据接地reason引原文)、①batch 10→20+worker批内Random(start)洗牌、④boundary_rerank(截断线±8窄带→同一次调用×5取均值→写zz_boundary.json靠文件名排序覆盖,commit.py没动,scored<target自动SKIP)。验证:编译/隔离逻辑(cutoff/band/取均值/覆盖)/真实claude-p烟测(reason确实引原文,分15/56/92)全过。详见 `docs/score-drift-research-findings.md` 落码状态节。
**第二步也完成(2026-06-17,未提交)**：①gt/dhi锚点手挑已填topic.json.score_anchors(gt:SAC95/泛连续控制DRL45/金星探测8;dhi:物理角色场景交互96/行人避障DRL46/量子active-learning10;低分边界从"打过分被拒"候选挑,因入库篇只到rel64)+已推TG审；②**冷启动改全自动自举(用户拍板"没必要介入")**:`score_auto.main()`无score_anchors时自动 裸跑整遍→`autopick_anchors`从整遍分布挑高/边界/低3张写回topic.json(非阻塞推TG告知可事后改)→带锚重打;冻好后增量复用不自举。安全性:从不需绝对分"对",只需各批一致+截断线去留对,一致偏>>乱飘,且④边界复称兜底去留。想改自举挑的锚点=直接编辑topic.json的score_anchors重跑score(**原pick_anchors.py已按用户要求删除**,不再有专门工具)。测过:首跑bare+anchored两遍、二次运行单遍不自举。标尺取"整遍"非第一批(池预排序、首批全高相关给不出低/边界样本)。③boundary_rerank开DB认首跑(去留线=target截断)/增量(资格闸rel≥30/flag_min,已入库篇跳过),两路测过。**全部未提交,在工作区。改的文件:score_auto.py + 新pick_anchors.py + 两topic.json + docs。**

**落码前发现的现状 bug**（grounding 时查到）：`score_auto.py:34-37` 的 rubric 档位例子**硬编码在 digital-human 主题**上（"训练数字人/虚拟人/仿真角色…"），只有 idea 按主题注入、rubric 例子不是。所以"带绝对锚点压住漂移"对 rl-general-toolbox 等其它主题是**错的标尺**——②（共享锚点）顺手能修这个 bug。score_auto.py 自 2026-06-15 只动过目录重构，打分逻辑没碰过；昨晚漂移讨论是纯分析、零代码改动。
