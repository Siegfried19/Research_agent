# SESSION 2026-06-17 — 当日总状态(capstone / 入口)

> 今天一天有多条线并行,这份是**单一入口**:串起各 detail 文件 + 当前决策 + 在跑什么 + 下一步。
> ⚠️ 本会话(总结层设计线)**全程只写 markdown(logs/docs/记忆),没碰 `db/papers.sqlite`、没跑 pipeline、没改代码/CLAUDE.md** —— 因为另有 agent 在并发拉论文。

## 一、今天发生了什么(按线)
1. **架构辨析**:改库层 vs 检索层(lookup vs retrieval);打分要不要 verify 闭环(结论:不照搬 summary 那套)。
2. **打分跨批次漂移**(`SESSION-2026-06-17-score-drift.md`)→ **另一 agent 已实现并在跑**(CLAUDE.md 已加该节:rubric 通用化 + `topic.json.score_anchors` + batch 20+洗牌 + `boundary_rerank` + `pick_anchors.py`;`docs/score-drift-research-findings.md`)。
3. **codex 额度烧穿 + verify 全盲**(`SESSION-2026-06-17-codex-quota.md`):连挂三班;根因=外部额度 + 4 代码缺陷(抓不到真错误→熔断失灵);cron 间隔已调 4.5h→5.5h(2:00/7:30)。
4. **新旧总结逐篇对照**(`SESSION-2026-06-17-summary-version-comparison.md`):6 agent 核 16 篇三版;发现修正环节会**推翻 codex 正确认定+伪造核对背书**、旁白串正文、v2 危险中间态。
5. **初衷重对齐 → 总结层设计转向**(`docs/summary-design-principles.md` v1):总结=方法/直觉分诊层,不是数字库;两段式(读总结判值不值得→PDF 看细节);只守语义/方向忠实。
6. **deep-research 验证**(`SESSION-2026-06-17-design-research.md`):大方向强力支持;"数字不必守"校准为"数字精度让位 PDF,但 claim 级语义核查顺带守 misattribution"。

## 二、已定决策(用户 2026-06-17)
- ✅ **核查保留**,但走**便宜 claim 级语义版**(MiniCheck/SummaC/AlignScore 或便宜 LLM-judge),codex 逐字核数字退役。
- ✅ 核查**改 report-only 三分类**(Supported/Unsupported/Omitted,PaperTrail 式),**取消自动修正环节的裁决权**——根治"反向裁决+伪造背书"致命 bug。
- ✅ **数字保留**(不删),但精度权威在 PDF,总结不装精确。
- ✅ **老 221 篇先全不动**(备份 `logs/wipe-summaries-20260617/`,完好)。
- ⏸️ **cron 暂停**(两行注释),今晚不跑总结。
- 🔄 今天重跑的 ~40 篇新总结:**可能整个去掉重做**(未执行)。

## 三、当前在跑什么(只读快照,17:08)
- **另一 agent 在拉新主题 `cold` 的论文**:run.log 见 `cold score_auto: 6 scored, anchors=3`(在用打分漂移新修法)。当下无 pipeline 进程(批次刚跑完),它可能续跑 discover/commit/fetch。
- **我不介入**:不碰 DB/pipeline/CLAUDE.md。总结层设计线与拉论文线互不冲突(我只动 docs/logs/记忆)。

## 四、下一步(等用户拍)
1. **总结产出结构**:回到"讲解散文+诚实局限"(老总结气质) vs 往 **PaperTrail 式 claim 级结构化**(每条方法论断成原子单元,好核查+好被 agent 提取)。→ 我可拿同一篇论文各出一个**样例**对比再定。
2. 据此定型 summarize prompt + 便宜语义核查怎么落(claude 自查 vs codex 只判方向 vs MiniCheck 类小模型)。
3. 再决定:**重做今天 40 篇 vs 直接用老 221 篇当基线、只补未总结的**。
4. (并行线,另一 agent)打分漂移修法跑完 `cold` 主题后看效果。

## 关键文件地图
- 总结层设计:`docs/summary-design-principles.md`(v1) + `logs/SESSION-2026-06-17-design-research.md`(调研)
- 对照证据:`logs/SESSION-2026-06-17-summary-version-comparison.md`
- codex 问题:`logs/SESSION-2026-06-17-codex-quota.md`
- 打分漂移:`logs/SESSION-2026-06-17-score-drift.md` + `docs/score-drift-research-findings.md`(另一 agent)
- 旧总结备份:`logs/wipe-summaries-20260617/`(221 篇 + papers.sqlite.bak)
