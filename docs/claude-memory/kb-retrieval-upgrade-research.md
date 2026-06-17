---
name: kb-retrieval-upgrade-research
description: "知识库检索升级调研(2026-06-17):PaperQA2/RAPTOR/GraphRAG 三个参考+用户待解的一堆问题;目标是服务\"RL训练监控agent带症状来问\""
metadata: 
  node_type: memory
  type: project
  originSessionId: a7dff52b-aa40-4c85-b0e4-3c26d9484dfa
---

2026-06-17 调研:用户觉得现在的 ask.py 纯 trigram 全文索引太简单,要升级知识库检索层。**真实用户=另一个监控 RL 训练的 agent,发现问题时带症状描述来库里找答案**(如"PPO reward 崩塌+KL 飙升怎么回事")。这种 query 关键词对不上论文用词 → 必须语义召回;agent 要"答案+出处"不是文件路径 → 必须 rerank+情境总结+强制引用。关联 [[corpus-as-knowledge-base-rag]](那条是更早的可行性分析,这条是具体参考+待办)。

## 三个要 mark 的参考(用户说"还不太懂,有很多问题要问")
1. **PaperQA2** `github.com/Future-House/paper-qa`(~8.7k★)——最贴用户场景:本地论文库 agentic RAG+引用。核心是 **RCS(Re-ranking + Contextual Summarization)**:粗召回 top-k → LLM 按问题把每块情境化总结 → LLM 重排(不信向量距离) → 带 in-text 引用合成。agent 有 SearchPapers/GatherEvidence/GenerateAnswer 三工具可多轮迭代。**用户最该精读的源码(尤其 GatherEvidence 的 RCS)。**
2. **RAPTOR** (arxiv 2401.18059)——文档块 聚类→LLM总结→再聚类→再总结 建"越上越抽象"的树,按问题从不同层取。**对应 CLAUDE.md 里"合成知识层/活的文献综述"设想的成熟做法。**
3. **GraphRAG** (Awesome-GraphRAG / cognee)——抽方法/问题/结论实体连图,查询顺图找邻居。**用户已有 citations 引用图雏形,这是用起来的方向。**

## 建议的三步落地路线(和 CLAUDE.md "先FTS5再向量"一致,补具体了)
- ① 加语义召回:FTS 外加向量索引(嵌"标题+摘要+中文总结",sqlite-vec 或本地 sentence-transformers),与 trigram 混合。
- ② 加 rerank+情境总结:召回后 claude -p 按问题重打分+情境化,再合成带引用答案(=PaperQA2 RCS,核心)。
- ③ 包成 agent 多轮工具 + 顺 citations 拉邻居 + 可疑来源(quality_tier)带标记进答案。
用户已具备最难的前置(curated库+质量标记+引用图+claude/codex双模型),缺的就是这三层。

## 第二波方法(2026-06-17 补搜,近且引用高)——给上面三骨架补的四块肉
- **Anthropic Contextual Retrieval**(2024,Claude Cookbook):切块前让 LLM 给每块加"这块在整篇讲啥"的小帽子再索引,治"切块丢上下文";主张向量+BM25混合(语义抓意思、关键词抓 PPO/TD3 这类缩写)。检索失败-49%,配 rerank -67%。**注:用户的索引单位本来就是整段中文总结不是碎块,天然较少丢上下文——这是优势;但"向量+关键词混合"该抄。**
- **CRAG/Self-RAG**(对 agent 场景最关键):召回后自评"证据够不够",不够就自动再搜/别硬编。Self-RAG 幻觉率 5.8% vs 普通 agentic 12-14%。**为什么致命:卡在RL训练里的 agent 拿到自信的错诊断会越改越糟,"宁说库里没有也别编"对 agent 比对人重要。ask.py 已会老实说没有,这是把它做扎实的范式。**
- **HippoRAG/HippoRAG2**(NeurIPS'24,OSU-NLP-Group/hipporag):知识图当长期记忆,PageRank 多跳;比迭代检索便宜10-20x快6-13x。**对应用户"语料每周增长+持续学习",是 citations 引用图的进阶版。**
- **LightRAG**(EMNLP'25,HKUDS/lightrag):GraphRAG 轻量替代,向量+图双层,**支持增量更新**(不用重建全图)——正对用户每周增量节奏(微软 GraphRAG 建图贵、要重建)。
- ⚠️ 上述性能数字均来自搜索片段未逐篇核进原文(=项目自己说的"张冠李戴"风险);只有 PaperQA2 我 WebFetch 真读了架构。要用前得 git clone 进 ref/ 真读源码核实。

## ⚠️ 规模前提(用户 2026-06-17 强调,很重要):别按"现在221篇"设计
20篇/天 → 一年7000+、两年几万篇、几十万片段。**之前想砍的重武器(ANN近似索引/reranker/图/RAPTOR摘要树)在那量级都变刚需,不能因当前量少就丢。** 检索层从 day1 就要为规模设计。

## 第三波(2026-06-17,为规模 + 召回增强)——已下载 ref/
- **OpenScholar**(Ai2,Nature'26,arXiv 2411.14199;repo ref/OpenScholar)=**规模化全开源蓝图**:45M论文/236M段向量,两段检索(retriever→reranker)+自反馈生成,胜 PaperQA2 5.5%,引用准确比肩人类专家。**我们的目标形态参考。**
- **HyDE**(arXiv 2212.10496)=**症状型 query 的解药**:先让 LLM 把"训练崩了"扩成假想答案再嵌入→文档-文档比对,补召回。对"agent带症状来问"直接对症。
- 选型(规模视角):
  - 嵌入:**Qwen3-Embedding**(MTEB榜首70.6,Matryoshka可调维度=省存储) 或 **bge-m3**(多语言100+)。本地。中文总结+英文query靠多语言模型跨语言召回。
  - 向量库:**sqlite-vec**(<10万,暴力,起步够) → 规模路径 **LanceDB**(嵌入式/列存/百万级,免迁移可考虑直接上)。pgvector/Qdrant=server,不符本地哲学。
  - **reranker**(两段检索第二段,规模下刚需):**bge-reranker**(本地多语言开源) 或 **ColBERT**(后期交互,23ms快);比"claude -p 重排"更快更便宜,大候选集更划算。
- 两段范式已成业界标准:**快召回(向量+BM25混合) → 精排(reranker)**;生产架构=离线索引管线 + 在线查询管线分离 + 增量索引+偶尔全量重建(正合现有 ask.py --reindex 增量思路)。

## 🔑 关键设计结论(用户 2026-06-17 自己推出来的,很重要)
**地基是"召回"不是"提炼"。** 因为消费者是会读书的 agent:
- 病C(提炼/重排)→ **可降级**:agent 自己读总结就把这步干了(ask.py --json 已返回 PDF 绝对路径让 agent 自己深读)。对 agent 消费者,RCS 不是正确性必需,而是"让你能少甩还甩得准"的省上下文/省钱优化,可晚做。
- 病A/B(召回/对意思)→ **必须修,无人能兜底**:没递到 agent 手里的书,它再会读也碰不到。trigram"对字不对意思"最常见的病不是提炼差,是对的书根本没从架上抽出来。
- 量的陷阱:召回越差越得多甩→撑爆上下文/又慢又贵。
- **行动优先级:把精力从"提炼答案"挪到"召回从对字→对意思(语义)"。** 语义召回做好 + 甩书让 agent 读 = 对本场景成立。

## 已下载到本地(2026-06-17,全在 gitignored 的 ref/,索引见 ref/papers/INDEX.md)
- 代码库:ref/paper-qa(早先已有) + ref/HippoRAG + ref/LightRAG(本次 clone)。
- 论文 10 篇在 ref/papers/:PaperQA2/PaperQA_v1/RAPTOR/GraphRAG/HippoRAG/HippoRAG2/LightRAG/Self-RAG/CRAG/Agentic_RAG_survey,均核过首页标题无张冠李戴。Contextual Retrieval 是 Anthropic 博客无 PDF(URL 记在 INDEX.md)。
- 用户明确说"暂时不用治你的病"(指我没逐篇精读),先收齐即可。

## 状态/下一步
- **2026-06-17 收尾:材料攒齐,会话日志 logs/SESSION-2026-06-17-retrieval-layer.md,用户说"明天跟你讨论"。** 明天接着聊。
- 明天要拍:①向量库 LanceDB(倾向)vs sqlite-vec ②嵌入 bge-m3 vs Qwen3 ③reranker bge-reranker vs ColBERT ④是否落 docs ⑤清库重跑范围+对齐另一agent。
- **用户现在处于"先搞懂、提问"阶段,还没决定动手。别急着写代码。** 用户明确说"有很多问题要问"。
- 改库时全程用 RESEARCH_DB=/tmp/x.sqlite 临时库,避开正在测总结的另一个 agent(它在写 db/papers.sqlite + store/summaries/)。
- 待用户问完/拍板后,可选下一步:精读 PaperQA2 RCS 源码 → 出"对应 ask.py 哪行该改"对照表;或先定技术选型(sqlite-vec vs chroma、嵌入本地 vs API)。
