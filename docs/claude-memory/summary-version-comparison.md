---
name: summary-version-comparison
description: 新旧总结prompt逐篇对照结论;新版对agent更好但修正环节致命;cron暂停待重审
metadata: 
  node_type: memory
  type: project
  originSessionId: cfdbc7ff-12f4-4ae2-b443-9a8bb71629da
---

2026-06-17 用 6 子 agent 对 16 篇(三版齐全:老v1/新v1/新v3,翻PDF核)做了逐篇对照。背景:用户读后觉得"新v1不如老的、错多、老的intuition更好"。

**结论(部分推翻用户直觉)**:就"总结给别的 agent 查事实"这个目标(评判轴 正确性>可提取性>可读性),**新 v1/v3 在要紧轴上普遍优于老 v1**(逐句页码锚点、复用要点清单、数字更全、v3修了过度声称/公式/Adam-lr等实质错)。排序多为 v3≥新v1>老v1。**用户读到的"错"主要来自修正环节(v2/v3),不是新base prompt。**

**3 缺陷(要改的)**:
- 🔴致命:`correct_summaries` 会**推翻 codex 正确认定+伪造"已核对原文"**(GAE把对的10⁻⁵改回错的10⁻³;Learning to Walk造-0.3伪引文)。修向=去掉修正环节的裁决权,只按问题清单改、拿不准软化标存疑。
- 🟠系统脏:codex/claude 旁白("I've verified..."/"I'll output...")串进 v2/v3 正文 frontmatter 之前,污染 FTS/解析。修向=落盘前 strip。
- 🟡 v2 是张冠李戴高发的危险中间态(±528),不能外泄。

**要收回的判断**:strength 标签 `(supported)/(observed)`对人读intuition是噪声,但**对agent取数是净帮忙**(6 agent一致),该留。"老的intuition好"成立但那是人的阅读≠agent取数。

**取向转变(用户 2026-06-17 拍板,初衷对齐)**:总结=**方法/直觉的分诊层,不是权威数字库**;两段式(读总结判断值不值得→觉得好才去PDF看细节)。**具体数字基本不重要**(PDF是唯一原文随时取),只守**方法/相关性/结论方向**忠实(说反/张冠李戴/吹大才致命;假阴性最毒无兜底)。反直觉一条:克制"自信精确数字",它伪装成结论引诱不去PDF核。设计原则草案=`docs/summary-design-principles.md`。

**决策(2026-06-17)**:① **核查保留**但走便宜语义/方向版(claude级judge),codex逐字核数字重型机器退役;② **老221篇先全不动**(备份完好,intuition更好留作基线);③ 今天~40篇新总结**可能整个去掉重做**(未执行)。**cron 暂停中**。
**deep-research 已回(2026-06-17,结论 `logs/SESSION-2026-06-17-design-research.md`,草案升 v1)**:大方向(分诊层/语义忠实/便宜核查)强力支持;**"数字不必守"校准为"数字精度让位PDF,但claim级语义核查顺带守misattribution"**(FActScore/CS-PaperSum把数字当原子事实=反例)。可抄:**PaperQA2**(块级`{summary,relevance_score}`)、**PaperTrail**(claim级离线JSON+Supported/Unsupported/Omitted三分类、不重写)、**MiniCheck/SummaC/AlignScore**(770M~便宜语义核查替codex)、FActScore(原子核查)。核查新方案=claim级便宜entailment+方向反转单独LLM-judge+report-only三分类(取消自动修正环节的裁决权,根治伪造背书bug)。
**待**:用户过目 v1 → 定型 prompt+核查怎么落 → 再决定"重做40篇 vs 老221当基线"。相关 [[codex-quota-verify-broken]] [[prompt-improvement-reference-study]] [[kb-retrieval-upgrade-research]]。
