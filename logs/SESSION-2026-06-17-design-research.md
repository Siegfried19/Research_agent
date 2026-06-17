# SESSION 2026-06-17 — 总结层设计 deep-research 调研结论

> deep-research(104 agent / 22 源 / 101 claim 抽取 / 25 条对抗核验,3 杀)对"总结=方法分诊层、数字让位 PDF、只守语义方向"取向的外部验证。
> 一句话:**大方向被强力支持,但"数字不必守"这条被校准为"数字精度让位 PDF、但语义级核查仍会顺带守住要命的数字(misattribution/矛盾)"。**
> 服务于 `docs/summary-design-principles.md`(据本调研升 v1)。

## 一、强力支持的(我们对的部分)
1. **两段式科学 RAG 是主流,PaperQA2 最可抄**:检索块先经 LLM 产出 `{summary, relevance_score}` JSON 再进答案上下文(RCS=Reranking & Contextual Summarization);摘要 200-400 token vs 原块 2250(~5-6x 压缩,不降效)。OpenScholar(检索→合成→自反馈迭代)、SciRAG(outline→plan-critic-solve)同模式。→ `github.com/Future-House/paper-qa`、`github.com/AkariAsai/OpenScholar`。
2. **PaperTrail(CHI 2026)= 与我们架构最贴近的原型**:离线预抽每篇 claim+evidence 成**可版本化 JSON 知识库当 ground truth**,昂贵的相关性判断延后到查询时——正是"摘要/claim 层即真相、原文延后、算力前移到离线"。溯源单位=**claim**(非引文/数字),三分类:**Supported / Unsupported / Omitted**。arXiv 2602.21045。
3. **核查要下沉到 claim/原子级,不做整体二元打分**(FActScore,EMNLP2023):"生成混合了被支持与不被支持的信息,二元判断不充分";拆原子事实算被支持占比;作者明说可推广到科学文献。
4. **词面指标(ROUGE/BLEU)对事实错不敏感 → 必须语义级核查**(QAGS,ACL2020:语义一致性与人工相关性 ~3x 于 ROUGE)。直接支持"守语义不守 token/数字面"。
5. **便宜语义核查工程上可行(关键!解 codex 额度)**:**MiniCheck**(770M,**~400x 便宜于 GPT-4 却达 GPT-4 级**事实核查,逐句对证据核;EMNLP2024,`arxiv 2404.10774`)、**SummaC**(轻量 NLI,切句+聚合句对 NLI,74.4% bal-acc;`AlignScore` 同类 `github.com/yuh-zha/AlignScore`)。
6. **结构化、机器可消费的总结已成熟**:Dagdelen(Nature Comm 2024,抽成 JSON 对象列表填库)、CS-PaperSum(91919 篇固定字段:Key Takeaways/Method/Performance/Future Work)、Paper2Agent(论文方法→可执行 MCP Tools 供下游 agent 调,`github.com/jmiao24/Paper2Agent`)。

## 二、被校准/反对的(我们要收的部分)
- **"具体数字不重要、可让位 PDF"只得部分支持 + 有明确反例**:压缩摘要快筛省 token(PaperQA2)、抽象总结牺牲逐条可归因(SciRAG 自陈)支持"摘要层适合快筛";**但 FActScore 把数字当原子事实去核、CS-PaperSum 专设数字字段——没有任何一手来源主张"总结里可放过数字"。**
- **可辩护立场(改这条)**:**"语义/方向忠实最致命、数字精度让位 PDF 检索"**,而非"数字不必守"。
- **3 条被对抗性否决(0-3,别过度引用)**:① FActScore 不能宣称"误差<2%替代人工";② 引文/grounding 忠实重要但**不是"唯一决定性失败模式"**;③ SciRAG 的 Correctness Score 不是"方向+相关性替代数字精确"。
- **工具契合度 caveat**:MiniCheck/SummaC 做二元 entailment grounding,**擅抓"无据 over-claim / misattribution"(含数字张冠李戴),但未为"结论说反"方向反转专门调优** → 抓方向反转要额外配一个 LLM-as-judge 提示。

## 三、对设计的净启示(落进 v1)
1. **架构对**:沿用"总结层分诊 → PDF 按需",可抄 PaperQA2 的 `{summary, relevance_score}` 与 PaperTrail 的"claim 级离线 JSON + Supported/Unsupported/Omitted 三分类"。
2. **数字立场收一格**:**保留数字**(它们是原子事实),但**数字精度的权威在 PDF**;总结不装精确、不堆假精度。
3. **核查重做(解 codex 额度 + 解危险修正环节)**:
   - 用**便宜的 claim 级语义核查**(MiniCheck/SummaC/AlignScore 这类小模型 或 便宜 LLM-judge)拆 claim → 逐条判 entailed?——**顺带就抓住了要命的数字错(misattribution/与原文矛盾),无需 codex 逐字渲染 PDF**。
   - 另配一个**针对"结论说反"的 LLM-judge 提示**(NLI 工具不擅长方向反转)。
   - 输出走 PaperTrail 的 **Supported/Unsupported/Omitted 三分类(report-only)**,**不自动重写** → 根除"修正环节反向裁决+伪造背书"那个致命 bug。
4. **结构化**:总结可往"claim 级可抽取"靠(每条方法论断成原子单元),便于核查 + 便于 agent 提取。

## 四、可抄清单(GitHub/论文)
| 用途 | 项目/论文 | 抄什么 |
|---|---|---|
| 两段式 RAG + 上下文摘要 | PaperQA2 (Future-House/paper-qa) | `{summary, relevance_score}` 逐块、Gather-Evidence 早筛 |
| claim 级离线 KB + 三分类溯源 | PaperTrail (arXiv 2602.21045) | Supported/Unsupported/Omitted、版本化 JSON ground truth |
| 原子事实核查范式 | FActScore (arXiv 2305.14251) | 拆原子事实、按单元核非二元 |
| 便宜语义核查 | MiniCheck (2404.10774) / SummaC / AlignScore | 770M~小模型逐句对证据 entailment,替 codex |
| 结构化方法级总结 | CS-PaperSum (2502.20582) / Dagdelen (Nat Comm 2024) | 固定字段 + JSON 对象 |
| 方法→agent 接口 | Paper2Agent (2509.06917) | 方法转 MCP tools(远期出口③可借) |
