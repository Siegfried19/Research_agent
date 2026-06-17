---
name: corpus-as-knowledge-base-rag
description: "用户的大计划——把论文库变成\"遇到问题就来查\"的 RAG 知识库；可行性、检索路径、持续学习的正确理解"
metadata: 
  node_type: memory
  type: project
  originSessionId: 6f3b0e2d-e126-4630-9e01-0aab36164ce3
---

用户在 [[research-paper-pipeline]] 之上的**大计划**(2026-06-09 提出,只记录、未动手):在别的 project 卡住时,让 agent 来这个论文库里**检索答案**(RAG over curated corpus)。后续还想"持续在论文库里学习"。

**Why:** 这是该项目最有价值的延伸——把"每周攒论文+总结"的库,变成一个能主动查询的知识后端。

**可行性结论(已和用户讨论过):**
- **可行,且底子好**:语料已 curated(打过分/删过垃圾)、有两个粒度(中文总结+全文)、有结构(相关性分/主题/引用图)。比一般 RAG 强。
- **数据库大小不是瓶颈**:`papers.sqlite` 只存元数据+摘要(原文是 `store/pdfs/` 的 PDF),上千篇也就几十 MB,sqlite 扛 GB 无压力。**真正的难点是"检索准不准",不是存储。**
- ⚠️ **(2026-06-16 改)`store/text/` 英文全文已整条移除**(commit 3f9bf71):总结/核查/修正都直读 PDF,text 对流水线是死重,知识库也决定不再用它(总结不从 text 写、text 不维护)。连带:4 个抓取阶段不再抽 text、`ask.py` 拆掉 `fts_text` 索引(检索只剩"标题+摘要+中文总结"的 `fts_sum`)、`--json` 输出把 `text_path` 换 `pdf_path`、`papers.text_path` 列保留但恒 NULL(没 DROP COLUMN)。**要英文全文细节=直读 store/pdfs 的 PDF**;若日后想恢复英文全文检索,从 PDF 跑 pdftotext 可随时重建。

**硬约束(2026-06-10 定):检索层必须认 `papers.quality_tier`** —— 质量体系改成了"标记进库不拒之门外"([[cross-model-codex-panel]] 硬信号层),suspect(掠夺刊名单命中)论文在库里、总结是质疑模式写的。RAG 出口必须默认过滤/降权 suspect,且答案里显式标注来源可疑;出口不过滤=污染答案(用户原话逻辑:污染不发生在存,发生在用的时候忘了它是什么)。

**How to apply(落地路径,按性价比分阶段,从①开始):**
1. **FTS5 全文搜 + `ask.py "<问题>"` 入口** —— sqlite 内置全文索引(标题+摘要+总结),零依赖,curated 库里够用。**先做这个,别一上来堆向量。**
2. **语义向量搜** —— 嵌入每篇总结(信噪比高),sentence-transformers 本地 或 嵌入 API + sqlite-vec;捕捉关键词搜不到的概念匹配。库长大后再上。
3. **混合 + claude -p 重排** —— FTS+向量各取候选,再让 claude 对 top-K 按当前问题重排。质量最高。
4. **引用图扩展** —— 命中一篇后顺 `citations` 拉邻居(找相关工作)。
5. **两段式** —— 先在总结层快筛 → 对最相关几篇再拉全文深读(省上下文、答得深)。

**"持续学习"的正确理解(重要,避免误区):** 不是微调模型(贵+脆+语料太小,RAG 完胜,不做)。真正可行=让**语料变聪明**的三层:(a)语料每周 `run auto` 增长;(b)**合成知识层**——定期 `claude -p` 把跨论文的方法/共识/矛盾/趋势蒸馏成主题笔记(= 活的文献综述,`cross_topic.py` 有雏形);(c)问答记忆——存过往结论别重推。检索时取用这三层。

## paper-qa / PaperQA2 = 阶段③④⑤的现成参考蓝图(2026-06-16,用户认可"确实不错",明天接着弄)
FutureHouse 的 agentic RAG 论文问答,**完整源码克隆在 `ref/paper-qa`**(2026-06-15 拉的)。用户看完判断:**对当前的 summarize/verify prompt 工作无关**(它是问答系统不是深读写笔记),但**对 `ask.py` 这条 RAG 线价值很高**——它把上面路线图 ③④⑤ 都实现并跑过 benchmark 了。**借设计、不引库**(litellm/嵌入栈/async/51KB settings.py 太重,违背"唯一依赖 requests";且它查询时重做摄入分块嵌入,而我们已有 curated 总结层这个它假设你没有的优势)。三条要抄进 `ask.py`:
1. **RCS(上下文摘要+打分重排)= 阶段③**:对每个召回 chunk 先跑一次 LLM gist 成"只针对该问题的摘要 + 1–10 相关分",按分重排再喂答案模型。**这是它战胜朴素 RAG 的招牌一招**(`ref/paper-qa/src/paperqa/prompts.py` 的 `summary_prompt`)。我们 `ask.py --answer` 现在是 top-5 FTS 直接喂 claude,中间缺这层。
2. **强制带引用 key 的 map-reduce + cannot-answer 哨兵**(`qa_prompt`+`CANNOT_ANSWER_PHRASE`+`CITATION_KEY_CONSTRAINTS`):每句挂 context 引用 key、证据不够回"I cannot answer"。治硬答。
3. **agentic 检索回路**(搜→收证据→答,带预算/状态)= 路线图最远端⑤。
- 顺带:它的 `individual_media_enrichment_prompt_template` 有一条图表级"张冠李戴"防线("图表周围文字未必在说这张图,别盲目引用"),印证 [[prompt-improvement-reference-study]] 里 summarize 加知识隔离+出处锚的方向。

详见 CLAUDE.md「待办」第 6 条。
