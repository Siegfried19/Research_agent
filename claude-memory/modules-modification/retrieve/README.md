# retrieve — 知识库出口（库地图 + 消费者拥有调查循环）

把 curated 论文库变成"卡住就来查"的知识库。不在 `run auto` 主链上——这是知识库的**出口**。

## ★ 现行设计（2026-06-21 重构，覆盖下方旧"问答引擎"设计）

**消费者永远是一个 agent**：人查也是开 agent 进库调查；别项目里卡住的 agent 直接来查。库经
**SSH 挂载到主力机**，agent 看到的就是**本地文件**（不需要远程 API/JSON 契约）。

**消费者拥有调查循环**：来查的 agent 自己驱动调查——读地图 → 自己决定读哪些总结/原件 →
得有据结论。我们**不写问答管道替它决定怎么查**（合"让 agent 自己判断"纲领）。它"怎么干"的
指令由**用户写进记忆**；库这边只负责把"地盘"摆好。

库这边交付三样（确定性力气活，纯 stdlib）：
1. **一张现拼的库地图** —— `pipeline/retrieve/map.py`（**新主入口**）。DB join + 主题档 merge →
   按 主题→facet 分组、带大白话标记的目录。输出 stdout + 写 `data-base/INDEX.md`（gitignored，
   派生可重建，与 fts/vec 同类）。**不走 envguard/不碰 conda**，挂载点裸 `python3` 可跑、只读挂载也行。
   **访问前现拼**（不挂任何 pipeline 阶段，与运维节奏解耦）。
2. **整齐的原件** —— `storage/sources/<slug>/`（vN.md 总结 + paper.pdf/source.md 原件，一篇一个家）。
3. **一份调查指南** —— `instruction-for-other-agent.md`（**项目根**,对外前门;目录布局/标记含义/引用纪律;map 头部有指针）。

地图字段/标记口径见 `map.py` 文件头 + STATE 2026-06-21 条。质量体系"标记进库、出口认标记"
的哲学不变（见下"出口必须认 quality_tier / verify 态"）。

> 下面是**降级为大库备用工具**的旧"问答引擎"设计（理解→召回→精排→生成答案，入口 `ask.py`）：
> 库大到 agent 一个上下文读不完地图/总结时才回退用，**留盘不删、不再是默认**。`ask.py` 路径仍冻结。

---

## （已降级）旧问答引擎设计 — 入口 `pipeline/ask.py`（公共 API，路径冻结勿移）

## 它服务谁（蓝图三出口，按近→远）
- **① 用户本人查** —— `ask.py "<问题>" --answer`，带引用的中文回答。
- **② 别项目里的 agent 卡住来查** —— `ask.py "<问题>" --json`，机器可读 `{answerable, answer, sources:[{doi,quality_tier,verify_status,summary_path,source_path,...}]}`，agent 拿绝对路径自己深读 PDF。**主用户就是它**（用户定）。
- **③ idea→论文流水线（ARS 桥）** —— `tools/export_corpus.py` 导出 ARS Material-Passport `literature_corpus[]` YAML，喂 academic-research-skills 从 idea 走到论文稿。

## 两种回答模式（`--answer/--json` 时，2026-06-19）
- **`--mode readall`（默认，库小）** = 全读，内脏 `retrieve/readall.py`。python 把【全部带总结的论文清单】（标题+⚠️标记+slug+总结路径+pdf路径，**正文不进 prompt**）塞给一个 Opus，给它 `Read`+`Task`：它自己把总结读全（篇数少=召回地板、一篇不漏）、相关的再 `Read` PDF 取一手、要深读多了可 `Task` 并行（子 agent 只回证据，合并由主 Opus 单线程收口）。**不检索、不碰索引。**
- **`--mode pipeline`（大库）** = 检索管道（方案 A）：见下"检索管道"。库大到一个上下文读不全时才切。
- 无 `--answer/--json` = 人看的命中列表（快，纯混合召回，不调 claude）。

> 设计哲学（`claude-memory/Prompt-structure-design/qa-layer-design.md`「金字塔」）：**贵的"读"建库时做一次、缓存成层（总结=每篇缓存，未来⑤合成层=跨篇缓存），查询只读缓存层、为精确才下钻 PDF。** 总结=地图（有意略去精确数字，判"值不值得深入"），PDF=实地（要精确论断回一手）。

## 检索管道（`--mode pipeline`，retrieve/）
```
问题
 ① 理解层  understand.py   claude 把问题→干净检索输入(展开缩写+中英双语词+HyDE假想答案)
 ② 混合召回 search.py       FTS5 关键词(对字) + Qwen 向量(对意思) → RRF 融合
 ③ RCS 精挑 rerank.py       claude -p 逐候选按问题重打分(0丢)+抽证据(借 PaperQA2)
 ④ 回答     answer.py       闭集引用[n] + quality_tier/verify 态透传 + 会说不知道
```
- **① 理解层**：根治旧机械分词的 P-A（2字母缩写如 "RL" 被正则丢）/P-B（中文复合词被单字停用词劈碎）两 bug。**claude 失败直接报错**，不静默回退老分词（悄悄退=给坏结果还不吭声）；唯一绕过 = `--no-understand`（debug）。
- **② 混合召回**：FTS5（`data-base/fts.sqlite`，trigram 索标题+摘要+最新中文总结；<3字词走 instr 全扫，**FTS5 上 LIKE 静默返0**）＋向量（`data-base/vec.sqlite`，Qwen knn）。RRF（`1/(K+rank)` 相加）取长补短、免调权重，统一在 paper_id 空间融合。向量那路无 torch 环境自动跳过（回退纯 FTS）。
- **③ RCS**：summary-first，候选已是 curated 总结，只做"按问题重打分+抽证据"半步（PaperQA2 消融证明这半步关键，去掉准确率显著掉）。`--no-rerank` 可跳。
- **④ 回答**：闭集引用（只能引召回里的 `[n]`，**DOI/路径由程序据 DB 回填=零幻觉**）；空候选不调 LLM、确定性短路出哨兵"库里没有相关内容。"

## 出口必须认 quality_tier / verify 态（标记不过滤）
质量体系是"标记进库"不是"拒之门外"——**出口不认标记 = 污染答案**。两条出口（readall/pipeline）共用 `answer.py` 的契约层（`make_source`/`TIER_NOTE`/`VERIFY_NOTE`），口径统一：
- `quality_tier`：`suspect`（掠夺刊嫌疑）→ ⚠️低可信、引用须核实；`flag`（预印本）→ 注"未同行评审"。
- `verify_status`（透传 `topics/*/verify_status.json`）：`major`（核查发现重大问题）/`stale`（总结已更新但新版未核）→ 答案里 ⚠️ 标出；其余（pass/minor/unverifiable/unverified）只进 `--json` 不打扰回答。
- 这些标记在 readall 进清单、在 pipeline 进证据块；`--json` 全态给 agent 自决。

## 嵌入引擎（lib/embed.py，非 LLM）
跟 claude.py/codex.py 并列的第三引擎，但**只把文字变坐标、不生成文字**。模型 **Qwen/Qwen3-Embedding-0.6B**（多语言中英都强，1024维）。**质量优先**（用户定）：fp32 满精度、`max_seq=24576`（实质不截断，真实总结才 ~7k token）、GPU batch=1；OOM 自动减半→单篇仍爆退 CPU（必完成不降精度）。查询侧带 instruct 前缀。模型缓存钉在 `dependencies/models/`（HF_HOME，gitignored，不污染家目录；2026-06-20 从 `pipeline/retrieve/models/` 移入大依赖统一目录）。

## 关键脚本 / 坐标库
- 入口：`ask.py`（**降级备用**总指挥，模式分发；现行主入口是 `map.py`，见顶部★节）。
- 管道：`retrieve/{understand,search,rerank,answer,readall,index,freshness}.py`。
- 旁路工具（归本模块）：`tools/similar.py`（找相似/揪重复，读坐标 numpy 余弦不调 GPU）、`tools/eval_retrieval.py`（A/B 验收 Recall@k/MRR，确定性零 LLM）、`tools/cross_topic.py`（跨主题共享篇+引用桥，自带全库引用边重建）、`tools/export_corpus.py`（出口③ 导 ARS YAML）。
- 索引库（均 **gitignored、可重建、不碰生产 `data-base/papers.sqlite`**）：`data-base/fts.sqlite`（FTS5）、`data-base/vec.sqlite`（sqlite-vec 坐标）。增量靠 `freshness.py` 两段钥匙（便宜指纹 stale_key 不读文件 → 变了再读全文算 body_hash 精确确认才重嵌）；含孤儿回收。没总结的论文也嵌（用标题+摘要），所以 similar/dup 对全库生效。

## 运行环境（要紧）
整条流水线统一跑在 conda 环境 **`research-agent`**（GPU torch/sentence-transformers/sqlite-vec；`environment.yml` 一键重建，是超集——主链只要 requests 也在内）。
- **入口自动纠偏**：`ask.py`/`run.py` 顶部调 `lib/envguard.ensure_env()`——不在该环境就用它的 python **自动 re-exec 自己**（bash/python3/cron/bot 哪种起法都落到对环境；按环境名探测不写死路径；逃生口 `RESEARCH_NO_REEXEC=1`）。找不到环境不拦着 → ask.py 自动回退纯 FTS。
- **向量必须 GPU**：实测 GPU(3060) 215 ms/篇，CPU 慢 ~100×（长总结 O(L²) 注意力 CPU 上不现实）。
- 跑法直接 `python3 pipeline/ask.py "..." --answer`，**不再需要** `HF_HOME=... conda run` 前缀。

## 坑
- FTS5 虚拟表上 `LIKE` 静默返 0 → <3字词必须用 `instr` 全扫兜底。
- 理解层 claude 失败 = 直接报错，别静默回退老分词（P-A/P-B bug）。
- `_latest_version` 用 DB `summary_versions` 取最高版，**别扫磁盘 glob**（v10+ 字符串排序会误取 v9）。
- export_corpus 输出含摘要（版权）+ 是 PRIVATE 字段，**仅本地 ARS 用，勿外发**；无 year 的条目按 schema 拒收不硬凑。
