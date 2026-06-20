# 问答层框架——实证依据汇总（论文 + 对比 + 数字，一处可查）

> **用途**：把"为什么这么设计"的所有外部证据（论文、基准、对比数字）拢到**一个地方**，免得散在 SESSION 日志里到处翻。
> **怎么来的（时间线/讨论全程）**：SESSION `claude-memory/modules-modification/retrieve/STATE.md` 第五段（第一批实证）+ 第七段（第二批 + 纠偏）。
> **设计本体（该建成什么）**：`claude-memory/Prompt-structure-design/qa-layer-design.md`（框架 v1，§8=两种模式）。
> **状态**：2026-06-19 汇总。证据**只定方向，不证明"我们这套在 RL 库上必然准"**——确切答案要自建 gold 集实测（design 文档薄弱点 #2/#6）。
> ⚠️ 领域迁移保留：下列基准多为生物/通用 QA，**不是** RL/中文总结库，结论是"架构方向强证据"非"我们必然超人"。

---

## 0. 三种打法（一切对比的坐标系）

把"一次问答怎么消化多篇论文"拆成三种基本打法，**所有论文都是在比其中两个**：

| 代号 | 打法 | 一句话 |
|---|---|---|
| **①** | 一个 agent 单上下文全塞 | full-context / long-context，把料全丢进一个窗口 |
| **②** | 并发多个小 agent 各读一段，再汇总 | fan-out / map-reduce / Chain-of-Agents |
| **③** | 用检索工具只挑相关篇喂进去 | RAG / agentic retrieval |

> **两个轴别混**（2026-06-19 澄清）：上面是"**读**"的打法；最后"**合成**"那步是另一回事——相关料能否进**一个 agent 单上下文**推理（design 文档"装得下/装不下"指的是这个合成轴）。fan-out（②，读）≠ 装不下（合成轴）。

---

## 1. 论文清单（主表，按对比维度归类）

| 论文 | 出处 / 年 | 比的是 | 关键结论 / 数字 |
|---|---|---|---|
| **Chain of Agents** | arXiv 2406.02818 · Google · NeurIPS'24 | **② vs ①/③/其它multiagent** | 长内容时 **② 高最多 10%**（短上下文聚焦、避 lost-in-middle）|
| **Long Context vs RAG: An Evaluation and Revisits** | arXiv 2501.01880 · ACL'25 | **① vs ③** | **装得下时 ①(全读) 反比 agentic RAG +4.4%、比朴素 RAG +10.9%**；但 **agentic RAG > 朴素 RAG**；数值推理任务偏向 RAG |
| **PaperQA2 / Language Agents Achieve Superhuman Synthesis** | arXiv 2409.13740 · FutureHouse · 2024-09 | **③+agentic vs 人类/消融** | 见 §2（超人 + 消融）|
| **Why Do Multi-Agent LLM Systems Fail? (MAST)** | arXiv 2503.13657 · NeurIPS'25 · 1600+轨迹/7框架 | 多 agent 失败解剖 | 失败率 **41–87%**；规格 41.8% / **协调 36.9%** / 验证 21.3%；**无结构放大错误 17×** → 合并必单线程+结构化+核验 |
| **Lost in the Middle** | arXiv 2307.03172 · TACL'24 | ① 单长上下文的毛病 | **U 形曲线，中段掉 >30%**；首因/近因偏置 |
| **Haystack Engineering** | arXiv 2510.07414 · 2025-10 | agentic 长上下文 + distractor 评测 | agentic 长上下文评测框架（PDF 未取到具体数字，方向参考）|
| map-reduce 摘要信息损失 | Galileo / Google Cloud（工程博客）| ② 的"写摘要再合"变体 | reduce 依赖中间摘要 → **掉实体/数字、串味** → fan-out 要"**抽证据**"不"写小作文" |

---

## 2. PaperQA2 的"超人"——讲准（含必须说的保留）

**论文**：*Language Agents Achieve Superhuman Synthesis of Scientific Knowledge*（arXiv 2409.13740）。基准 LitQA2，248 道科学文献多选题。**领域=生物。**

**正面 PK（人类对照=有生物/相关博士学位或在读，且全程联网+工具+不限时）：**

| | 精确率 precision | 准确率 accuracy |
|---|---|---|
| **PaperQA2** | **85.2% ± 1.1%** | 66.0% ± 1.2% |
| **博士级人类** | 73.8% ± 9.6% | 67.7% ± 11.9% |

- **"超人"主要在 precision**（85.2 > 73.8，统计显著）；**accuracy 是打平**（人类名义略高，在误差内）。
- 另：写的维基式综述比现有人写词条更准；每篇揪 2.34±1.99 个矛盾、70% 被人类确认。

**消融（"用工具 vs 不用"的硬证据）：**
- 去掉 **RCS**（重排+情境摘要工具）→ 检索准确率显著掉（t=9.29, **p<0.001**）。
- 去掉 **agentic**（不让它迭代调工具/改写查询）→ 准确率显著掉（t(3.7)=3.41, **p=0.015**）。

**⚠️ 关键保留（2026-06-19 纠偏，防再被误用）**：
PaperQA2 的超人是在**几百万篇、② 根本不可能**的区间拿的（③+agentic 是唯一可行）。**它不构成我们 41/1000 篇小库搭建的依据**——此前用它背书=过度推销，已退回。

---

## 3. ②③ 不是二选一，是"按库大小交接的接力"

实证看似打架（CoA：②>③；PaperQA2：③超人），其实**从没在同一库大小比过**：

- **读得完 → 用 ②（更强）**：CoA 证明（长内容里 ② 比 ③ 高 10%，全读覆盖 100% 不漏）。
- **读不完 → 只能 ③（仍超人）**：PaperQA2 证明（几百万篇，② 不可能）。
- **没有"明明能 ② 却被迫用更差的 ③"的场景**——所以不存在"选了差的"。
- **真实大系统是 ②+③ 叠用**：③ 先筛 → ② 读活下来的（Anthropic 多 agent = ②+③；PaperQA2 = ③+agentic）。

---

## 4. 新旧之辨（用户质疑"研究太旧、模型变强"，2026 补查）

| 维度 | 结论 |
|---|---|
| lost-in-middle 还在吗 | **2026 仍真**（LongBench v2 / HELMET 复现；Sonnet 4.5 喂 200 chunk 中段塌），但**变弱**；且**对推理比对找事实更狠**（综合/找矛盾正是推理）|
| 选择性检索 vs 全塞 | 查询类任务**选择性检索仍常胜全塞**（弱模型 Mistral 例：35.5%→66.7%，强模型证据弱）|
| 趋势 | "**上下文窗口不再是差异点、agent 层更重要**"；Anthropic 长上下文可靠性更好（Claude 在超大输入下更稳）|
| 净结论 | 退化变弱**没消失**；工具价值从"补容量"→"**注意力卫生**"；**41 篇小库增益有限、规模越大越值** |

---

## 5. 证据 → 我们的设计（落点对照）

| 设计选择 | 支持的证据 |
|---|---|
| 小库 fan-out/全读放开（方案B 默认） | LongCtx-vs-RAG：装得下时 ① +4.4% > agentic RAG（§1）|
| 大库切"检索预筛 + agentic" | PaperQA2 消融：去 agentic p=0.015、去 RCS p<0.001（§2）|
| fan-out 抽**证据**不写**总结** | map-reduce 掉实体/数字（§1）|
| 合并**单线程 + 结构化 + 核验** | MAST：协调崩溃 37%、无结构放大 17×（§1）|
| 索引(③)不删、当工具/兜底 | PaperQA2 整套 = ③+agentic 达专家级（§2）|
| 合成层 = 比 ③ 更聪明的语义路由 | （内生推论，无直接基准；雏形 `tools/cross_topic.py`）|

**三档规模**（与 design §8 一致）：
- **~41 篇（现在）**：① 一个 Opus 全读 / 顶多 ②；③=可选聚焦+找重复，不当闸。
- **~1000 篇**：总结 ~3M token **塞不进 1M** → **③ 筛(→30-50) → ②/① 读 → 合成**；③ 转正成召回闸；**合成层接管导航**。**切换临界落在几百~1000，不是 2000。**
- **几百万（PaperQA2 区间）**：只能 ③ agentic 多轮检索。

---

## 7. 深挖第三批（2026-06-19，本地 6 篇原文精读 + 2026 新论文）

> 缘由：用户好奇"合成层/全读 vs 检索 到底哪个质量好，有没有研究直接对比"。派 3 个 agent 把 `ref/papers/` 里 6 篇逐节读了 + web 扒了 2 篇 2026 新论文。**核心收获：直接对比不存在，但找到最接近的一个数据点（GraphRAG C0-vs-TS）。**

### 7.1 头条结论
- **"小库全读" vs "选择性/agentic 检索"的直接质量对比——不存在。** 整个领域都在"几百万篇、不可能全读"的区间工作；PaperQA2 每题只摸 ~14.5 篇、OpenScholar 在 45M 篇里召回 5–10 段。**它们的"超人"成绩不能给"小库必须检索"背书**（与 §2 纠偏一致）。
- **最接近的真数据 = GraphRAG C0 vs TS**：C0=预蒸馏社区摘要（≈合成层），TS=临时把所有源文本 map-reduce 全摘（≈fan-out 全读再合并）。**质量基本打平（小幅提升或根级略降），合成层赢在 token 成本省 97%（C0 2.6万 vs TS 101万 token）。→ 合成层是"省/快/覆盖更全"的工具，不是"答得更准"的工具。** 可信度：高。

### 7.2 一致印证"顶层导航 + 下钻原文"（=我们既定的"总结=地图、数字让位PDF"）
- **RAPTOR 自己的数据：不能只用顶层**——单叶层 57.9 vs 含原文的三层 73.68（Table 8）；且 ~4% 摘要有轻微幻觉。它靠保留叶层原文兜底。
- **GraphRAG 在 empowerment/directness（具体例子/引文/精确细节）上反而输**——摘要把细节稀释。
- ⚠️ **RAPTOR 赢的是"扁平分块检索"，不是"读全文"**——从没跟"读整篇"做过受控对照。别拿它当"合成层赢过读原文"的证据。可信度：高。

### 7.3 "全读"不是免费质量增益（弱反对信号，小库基本不触发）
- **塞越多越差**：OpenScholar top-N 消融，段落 5→25 时未训练模型 correctness+引用准确率**双降**（§4.3）。但测的是 5–25 段、非"全读 40 篇"。
- **lost-in-the-middle 2026 仍真**：1M 模型、Sonnet 4.5 在 200 块中段照掉，**对推理/聚合比对找事实更狠**（正打在"跨论文综合"上）。
- **矛盾材料一起喂→拉锯/确认偏置**，"too many passages overwhelm the model"（RAG 综述 §7.1）。

### 7.4 领域的真建议在另一个轴（与我们 6/17"召回是地基"撞上）
- **Agentic RAG 综述 §10.3**："agentic 推理救不了烂检索。**先把检索/索引质量做好，再谈 agentic 复杂度**。" 可信度：高（最该听的一条）。
- **§10.1**："agentic 不是默认更优"——简单/窄/开放域任务用确定性管道就够，agentic 收益要复杂任务+结构化领域才兑现。
- 多 agent fan-out 失败模式=合并非平凡+级联失败+无收敛保证；最佳实践=**有界步数/工具白名单/显式停止**。

### 7.5 一篇 2026 新论文，少数直接偏"检索"
- **Revisiting Text Ranking in Deep Research（SIGIR 2026, 2602.21456）**：deep-research agent 下 **rerank+段落级 比 处理整篇文档 更有效更高效**；**BM25+reranker 打平贵神经系统**；**把关键词式查询翻成自然语言问题显著提升排序**（=我们 understand 层在做的事）。⚠️ web 规模、上下文受限，不完全等于"40 篇进 1M 窗口"。

### 7.6 所有论文都没解决的真空：增量更新
- **RAPTOR / GraphRAG 都是"离线全量建、查询时只读"，增量更新完全空白**。GraphRAG 全量建图 281 分钟/1M token（可作重建成本上界）。**"活的合成层/每周增量"是我们要自己啃的硬骨头。**

### 7.7 净结论（给下游决策）
1. 3-vs-4 直接对比不存在；最接近的 GraphRAG C0-vs-TS = **合成层≈全读 质量平手、赢成本**。
2. **顶层永远要能下钻原文**（多篇一致），精确论断别信蒸馏层。
3. 你小库这体量**质量上是平局**——反对全读的信号都是大上下文毛病，40 篇不触发。选 ③/④ **不是质量决定的，是"简单 vs 未来扩展"决定的**。
4. **"活的合成层"是真空地带**，增量更新没人解决。

---

## 6. 原始链接

- [Chain of Agents (arXiv 2406.02818)](https://arxiv.org/abs/2406.02818) · [Google blog](https://research.google/blog/chain-of-agents-large-language-models-collaborating-on-long-context-tasks/)
- [Long Context vs. RAG for LLMs (arXiv 2501.01880)](https://arxiv.org/abs/2501.01880)
- [PaperQA2 / Superhuman Synthesis (arXiv 2409.13740)](https://arxiv.org/abs/2409.13740) · [FutureHouse blog](https://www.futurehouse.org/research-announcements/engineering-blog-journey-to-superhuman-performance-on-scientific-tasks)
- [Why Do Multi-Agent LLM Systems Fail? / MAST (arXiv 2503.13657)](https://arxiv.org/abs/2503.13657)
- [Lost in the Middle (arXiv 2307.03172)](https://arxiv.org/abs/2307.03172) · [2026 复现讨论(LongBench v2/HELMET)](https://dev.to/gabrielanhaia/lost-in-the-middle-is-still-real-in-2026-even-on-1m-token-models-2ehj)
- [Haystack Engineering (arXiv 2510.07414)](https://arxiv.org/abs/2510.07414)
- map-reduce 信息损失：[Galileo](https://galileo.ai/blog/llm-summarization-strategies) · [Google Cloud](https://cloud.google.com/blog/products/ai-machine-learning/long-document-summarization-with-workflows-and-gemini-models)
- 2026 前沿趋势：[Atlan: context window limitations 2026](https://atlan.com/know/llm-context-window-limitations/) · [Opus 4.8 vs GPT-5.5 agentic](https://www.mindstudio.ai/blog/claude-opus-4-8-vs-gpt-5-5-agentic-tasks)
- 深挖第三批（§7）本地原文：[RAPTOR 2401.18059](https://arxiv.org/abs/2401.18059) · [GraphRAG 2404.16130](https://arxiv.org/abs/2404.16130) · [OpenScholar 2411.14199](https://arxiv.org/abs/2411.14199) · [Agentic RAG 综述 2501.09136](https://arxiv.org/abs/2501.09136) · [RAG 系统综述 2507.18910](https://arxiv.org/abs/2507.18910)
- 深挖第三批（§7）2026 新论文：[Revisiting Text Ranking in Deep Research (SIGIR 2026) 2602.21456](https://arxiv.org/abs/2602.21456) · [SAGE: Retrieval for Deep Research 2602.05975](https://arxiv.org/abs/2602.05975) · [lost-in-the-middle 2026 emergent property](https://openreview.net/forum?id=XSHP62BCXN)
