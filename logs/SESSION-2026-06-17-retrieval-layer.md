# SESSION 2026-06-17 — 检索层（知识库出口②）方案调研

> 目标：把现在 `ask.py` 的纯 trigram 全文索引升级成能服务"**监控 RL 训练的 agent 带症状来查答案**"的检索层。
> 本会话只做**调研 + 攒参考 + 出方案**，**没碰任何 pipeline 代码、没动生产库**。明天继续讨论。
> 配套记忆：`memory/kb-retrieval-upgrade-research.md`（最全）。

## 一、本会话产出（都在 gitignored 的 ref/）
- **代码库**（clone）：`ref/paper-qa`（早先已有）、`ref/HippoRAG`、`ref/LightRAG`、`ref/OpenScholar`。
- **论文 13 篇** `ref/papers/`：PaperQA2/PaperQA_v1/RAPTOR/GraphRAG/HippoRAG/HippoRAG2/LightRAG/Self-RAG/CRAG/Agentic_RAG_survey + 第二批 OpenScholar/HyDE/RAG_systems_review。均核过首页标题无张冠李戴。
- **索引** `ref/papers/INDEX.md`（什么/为什么下/重复项）。

## 二、关键结论（讨论中达成的共识）
1. **数据来源澄清**：生产库 `db/papers.sqlite`（5表，元数据+引用图+路径）是流水线**边跑边写**的、和总结**耦合**；正文(PDF/总结)是磁盘文件，库里只存路径。检索层(fts.sqlite / 未来 index)是**事后扫描、解耦、可重建**的旁路。
2. **清库重跑 summary 不影响检索层方案**——因为它解耦可重建；只影响"实现时机"（重跑稳定后再索引，且切片对齐新总结结构）。
3. **地基是召回(对意思)，不是提炼(RCS)**——消费者是会读的 agent，RCS 可降级；召回(语义)无人能兜底，必须先做。
4. **⚠️ 必须为规模设计**（用户强调）：20篇/天→两年几万篇/几十万片段。reranker/ANN/图/RAPTOR 在那量级都是刚需，不能因现在221篇就砍。

## 三、当前方案（为规模 baked-in，分期）
- 借鉴：PaperQA2(混合召回+RCS) + OpenScholar(两段检索+自反馈，规模蓝图) + HyDE(症状query扩写) + Anthropic Contextual(切片贴上下文) + CRAG/Self-RAG(可靠性门) + citations/RAPTOR(进阶)。
- 架构：离线索引管线(扫总结→切片→嵌入→向量库+FTS，增量) ‖ 在线查询(〔HyDE〕→向量+BM25混合召回→reranker精排→quality_tier过滤+可靠性门→--json指针/RCS答案)。
- 分期：P0 切片+嵌入+混合召回+reranker+--json ｜ P1 HyDE+可靠性门 ｜ P2 RCS/agent多轮工具 ｜ P3 citations邻居/RAPTOR。

## 四、明天要拍的决定 / 待办
1. **向量库：LanceDB（倾向，认准扩容免迁移）vs sqlite-vec（最简，同 fts 生态）** ← 唯一需要现在定的。
2. 嵌入模型：bge-m3 vs Qwen3-Embedding（可调维度）。
3. reranker：bge-reranker（本地）vs ColBERT。
4. 是否现在就把方案落成 `docs/retrieval-layer-plan.md`。
5. 前置：用户计划**清库 + 全量重跑 summary**（范围待定：只删库 / 删库+删总结+重跑 / PDF保留）；和正在测 summary 的另一 agent 对齐别撞车。实现检索层放在重跑之后、对齐新总结结构。
