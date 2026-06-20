# retrieve — STATE（层积日志）

> 写法：**新在上、老在下、不删**，每条标题带日期+时间戳。最顶一条 = 此刻状态/卡在哪；往下翻 = 历史。
> README.md 是定型设计（覆盖更新）；这里是带细节的过程账。
> 局部改动记这里；跨模块/全局改动记 `../../../claude_log.md`，这里只留一行指针。

## 2026-06-20 02:16 EDT · 重构首条（当前状态快照）

> 文档模块化重构建立本日志。以下为当日现状；以后变化在本条**之上**叠新条。

### 已落地
- **①FTS5 全文搜 + `ask.py` 入口**（2026-06-10）。
- **②③ 检索管道**（2026-06-18，`8b6c0de`）：理解层(understand) → 混合召回(FTS5+Qwen向量 RRF, search) → RCS 精挑(rerank) → 闭集引用/会说不知道(answer)。坐标库 `db/vec.sqlite` + 嵌入引擎 `lib/embed.py`（fp32 满精度/不截断/GPU batch=1）。
  - 实测：GPU 215ms/篇（CPU 慢 ~100×，必须 GPU）；种子 gold 纯 FTS Recall@10 0.67 → 混合 1.00；cannot-answer 哨兵生效。
- **理解层**（2026-06-18，`14fa88f`/`a48b24a`）：claude 展开缩写+中英双语+HyDE，治机械分词 P-A/P-B bug；失败直接报错（不静默回退）。
- **④全读模式 readall.py**（2026-06-19，`--mode readall` 成 `--answer/--json` 默认；现规模库小，唯一料薄也能跑的路）：清单+按需 Read/Task，DOI 程序回填零幻觉。`ask.py` 模式分发器 + `answer.py` 共享契约层（readall/pipeline 共用质量态/DOI 回填口径）；检索路（understand/search/rerank/index）退役留盘当大库工具。
- **运行环境自动纠偏**（2026-06-18，`lib/envguard.py`）：conda `research-agent` 环境，入口自动 re-exec；找不到回退纯 FTS。
- **旁路工具**：`tools/similar.py`（已实战抓出重复入库，见下）、`tools/eval_retrieval.py`（A/B harness + 种子 gold）、`tools/cross_topic.py`、`tools/export_corpus.py`（topic2 100 条实测过 ARS schema 校验）。

### 未决 / TODO
- **本机仅 ~39 篇有总结**（库里 221 篇，但 status=summarized=39，磁盘总结=39）——旧 CLAUDE.md 写的"221 篇全已总结"在此机不成立（疑迁移/清库后总结没全带过来）。用户拟**删总结重做**；重做后重跑 `python3 pipeline/retrieve/index.py`（增量自动跟上 fts+vec）。检索质量验收最好等总结定稿后。（注：summarize STATE 实测当前已重建到 ~60 篇，是动态值。）
- **真 30–50 条 gold 集**未做：`store/eval_gold.json` 只是种子+harness，真 gold 该由用户按真实使用场景手标，且在总结重做定稿后再跑。
- **Self-RAG 式逐句自检（ISSUP）未加**：当前靠闭集引用 + cannot-answer 哨兵兜底（够用，自检是增强项）。
- **合成层（⑤蒸馏 / ④引用图扩展 / 两段式深读）未做**：cross_topic.py 有跨主题雏形，但"金字塔"中枢的⑤合成层（按簇蒸馏/矛盾显式存/精确回 PDF）尚未落代码。设计主干在 `claude-memory/Prompt-structure-design/qa-layer-design.md` §9；实证对比在 `claude-memory/Prompt-structure-design/qa-layer-evidence.md` §7（结论：合成层是"省/快/覆盖全"工具而非"更准"；先把检索做好，agentic 救不了烂检索）。
- **Bipedal 重复入库待去重**：`Reinforcement Learning for Robust Parameterized Locomotion Control`（Bipedal Robots）以两 id 重复入库（slug `..._Bipedal_Robots` 和 `..._2`，两主题各发现、merge 没合上），similar.py dup 已揪出（余弦 1.000）。还有 `tools/similar.py` 另抓出 `2103.14295` 重复。
- **大库切换点**未定：`readall`→`pipeline` 的切换目前靠手动 `--mode`，没有自动按篇数/上下文体量切。
- **②③ 全功能依赖 research-agent 环境**：cron/PATH 已切到该环境（envguard 自动纠偏），但向量功能在 base 环境仍回退纯 FTS。

### 上次卡在哪
- 出口"问答层"实现方案在 2026-06-19 收敛成「金字塔 + 模式分发」，先落了 ④全读（`claude-memory/Prompt-structure-design/qa-layer-design.md` §8-§10）；落地次序定为：现在④临时路 → 总结铺开后蒸⑤ → 库到几百+再切②召回闸+⑤导航。
- **代码均未提交**（readall 等待用户 push；检索段 ②③ 已 commit）。真端到端全读未跑过（慢+烧配额+库重建中），等用户要再跑。

---

## 2026-06-18 · 知识库出口/检索层升级——从「找得准」到「金字塔/全读」的完整来龙去脉

> 来源：旧 `logs/SESSION-2026-06-18-kb-retrieval.md`（一个文件含九段，时间跨 06-18→06-19，忠实迁入）。
> 目标起点：把出口 `ask.py` 从"纯关键词、对字不对意思"升级到"语义召回 + 精排 + 会说不知道"。
> 方案依据：`ref/papers/` 那批 RAG 论文综合调研（RAPTOR/PaperQA2/GraphRAG/LightRAG/HippoRAG/Self-RAG/CRAG/HyDE/OpenScholar）。
> 用户决定：上嵌入（本地小模型，非 LLM）；分簇用 claude -p；先做第一步（任务 #1–#9）。

### 第一段（06-18）：第一步「找得准」全部落地并跑通

**架构落点**
- 出口检索层独立成段文件夹 `pipeline/retrieve/`（不在 run auto 主链上）：index/search/rerank/answer。
- `ask.py` 留根（公共 API 路径冻结），瘦身成入口/总指挥，内脏搬进 retrieve/。
- 嵌入引擎 `lib/embed.py`（跟 claude.py/codex.py 并列的第三个引擎，但不是 LLM）。
- 模型缓存 `pipeline/retrieve/models/`（gitignored，HF_HOME 指向）；坐标库 `db/vec.sqlite`（gitignored，可重建）。

**环境（方便迁移）**
- 新建 conda 环境 `research-agent`（conda-forge 渠道 + python 3.12）——顺带根治 anaconda base 的 libstdc++ CXXABI 报错。
- 装：GPU torch 2.12.1+cu130 + sentence-transformers 5.6.0 + sqlite-vec 0.1.9 + requests。验证：CUDA 可用=True，认出 RTX 3060 Laptop（5.65GiB）。
- ⚠️ 6GB 显存放不下长序列大 batch → embed.py 第一版用 fp16 + max_seq=2048 + batch=8，带 OOM 自动减半重试（注：第二段改成 fp32 满精度，见下）。迁移抓手：`environment.yml`。

**关键发现**
- ⚠️ 这台机器只有 39 篇被总结（库里 221 篇论文，但 status=summarized=39，磁盘总结文件=39）。CLAUDE.md 写的"221 篇全已总结"在此机不成立——疑似迁移/清库后总结没全带过来。用户已知会"可能删总结重做"。不阻塞检索搭建（有几篇嵌几篇，自动随总结增长）。

**速度实测（用户关心）**
- 模型 Qwen3-Embedding-0.6B，1024 维，fp16，max_seq=2048。**GPU(3060,batch8)：215 ms/篇** ｜ **CPU(batch4)：21,000 ms/篇** → GPU 快约 100×。
- 全库 221 篇建索引 GPU 实际 ~47s。结论：**必须用 GPU**（长总结 O(L²) 注意力 CPU 上不现实）。

**进度——第一步（任务 #1–9）全部完成，端到端跑通**
- #1 装嵌入+计时（见上）。
- #2 坐标索引 db/vec.sqlite（retrieve/index.py）：全库 221 篇量坐标（没总结的用标题+摘要），增量靠 body md5，OOM 自动减半重试。
- #3/#4 混合召回（retrieve/search.py）：FTS5（对字）+ 向量（对意思）RRF 融合。中文概念问题混合比纯 FTS 多召回相关篇。
- #5 RCS 精挑（retrieve/rerank.py）：claude -p 逐候选按问题打分（0 丢）+ 抽证据，实测打分准、证据对题。
- #6 --answer（retrieve/answer.py）：闭集引用 [n] + quality_tier 透传 + **会说不知道**（量子纠错问题→"库里没有相关内容"哨兵，确定性短路）。实测跨 4 篇综合 + 自列局限，质量高。
- #7 --json：`{answerable, answer, sources[{doi,quality_tier,rcs_score,summary_path,pdf_path}]}`，纯 stdout 干净 JSON（日志走 stderr）。
- #8 验收 harness（tools/eval_retrieval.py）+ 种子 gold（store/eval_gold.json）：**纯 FTS Recall@10=0.67/MRR=0.500 → 混合=1.00/0.548**，向量把 FTS 漏的捞回。⚠️ 真 30–50 条 gold 待用户手标，且最好总结重做定稿后再跑。
- #9 找相似/揪重复（tools/similar.py，读坐标不调 GPU）：dup **实战抓出已知重复入库**（RL Robust Parameterized Locomotion 以 10.48550/.. 和 arxiv:.. 两 id 入库，余弦 1.000）。

**入口/迁移**
- ask.py 瘦身成总指挥（混合召回→RCS 精挑→带引用回答/会说不知道）；保留公共参数，加 --no-rerank。
- ask.py 在 base 环境自动回退纯 FTS（无 torch 时），research-agent 环境用全功能。environment.yml 写好（`conda env create -f` 一键重建）。
- 本会话新增文件：lib/embed.py、retrieve/index.py、retrieve/search.py、retrieve/rerank.py、retrieve/__init__.py、retrieve/models/。

### 第二段（06-18）：质量收口 + 与 summary-verify 对齐（已提交 `8b6c0de`=第一步全部）

**嵌入质量（用户要"保证质量"）**
- embed.py 改质量优先（原为迁就 6GB 显存的妥协）：fp16→**fp32 满精度**；max_seq 2048→**16384（实质不截断**，最长嵌入体 ~13k 字符 <1 万 token，< 模型原生 32768）；GPU_batch 8→**1**；OOM 兜底升级=batch=1 仍爆就**整批退 CPU**（满精度必完成）。
- 实测全量重嵌 221 篇：**28.6s / 显存峰值 2790MiB**（6144 总量，富余一半）。反直觉更快=多数论文只标题+摘要序列短，batch=1 省了大批量 padding。已 `index --force` 全量重建。

**对齐修复（发现 answer.py 漏对齐：判定为忘记非故意）**
- answer.py 取总结路径改读 DB `summary_versions ORDER BY version DESC`（与 index/search/rerank 统一）；删原 `sorted(glob("v*.md"))[-1]`——会在 v10+ 字符串排序误取 v9，且可能与 DB 不一致。

**A 组（与 summary-verify 多版本对齐，本段重点）**
- A1 检索层认 verify 核查态：`verify_summaries.write_report` 多落结构化 `verify_status.json`（`{id:{verdict,version}}`，跨轮合并保留旧篇）；answer.py 读全库聚合（`load_verify_status`，同篇多 topic 取最高版）+ `resolve_verify`（无记录=`unverified` / 记录版本<当前=`stale` / 否则=verdict）→ 透传进 --json（verify_status+summary_version）+ 答案对 **major/stale 加 ⚠️**（其余 pass/minor/unverifiable/unverified 不打扰回答）。**只标注不过滤**，合"标记进库、出口认标记"哲学。
- A2 index 自动刷新：run.py 加 `refresh_index()`（best-effort，无 torch 时吞错不打断主链）+ 独立 `reindex` 阶段；挂到 auto/auto-sum/auto-sum-next 收尾 + 单跑 sum/finalize/verify 后。消除"resummarize 出新版、检索还用旧版"窗口（vec 不像 fts 那样查询时自增量，必须显式重建）。
- 单测全过：resolve_verify 5 态、load 跨 topic 取高版、write_report 落盘+合并、reindex 入口增量跳过。
- ⚠️ 旧 topic 的 verify_status.json 待下次 verify 生成——没从旧 .md 回填（.md 只覆盖最后一轮、pass 仅按标题、易错标）；在那之前老篇一律显示 unverified（诚实未知，不误标）。
- 仍待办（B/C/D）：B=真 gold 集 / Self-RAG 逐句自检(ISSUP) / rerank max_chars=12000 截断（最长 11119 已逼近）；C=合成知识层 / 引用图扩展 / 两段式；D=39 篇总结待重做后重跑 index、cron/PATH 切环境（envguard 已能自动 re-exec，未在 cron 实跑验证）。

### 第三段（06-18）：逐步审查问答 pipeline + 决定上 claude 问题理解层

> 用户在逐段严谨审查整条问答管道（plan→确认→实现→验证→log→commit；见 memory `working-style-review-pace`）。

**已提交——第 0 步（建索引）优化 `35bfb2c`**
- 嵌入上限 16384→**24576**（实测 fp32/batch1 单篇峰值 8k=2.3G/16k=3.4G/24k=4.5G，留 ~1.2G；+`expandable_segments` 防碎片 + CPU 兜底；生产 221 篇实测峰值仅 2671MiB；问答零影响，坐标不变）。
- 索引增量改**两段钥匙**（新 retrieve/freshness.py，fts+vec 共用）：便宜钥匙=md5(title+abstract+path+mtime) 不读文件→秒跳（治 P3），fts/vec 判据统一（治 A：abstract 改动 fts 也抓得到），每查询 reindex 近免费（治 B）；vec 钥匙变了才读全文算 body_hash 精确确认（零问答风险）；+busy_timeout(C)+孤儿回收(D)+旧 meta schema 自动迁移。全验证过。

**第 1 步（混合召回 search.hybrid）审查结论**
- 结构对、防御足、无文本截断（只 k=50/topn=20 召回宽度）。不调 claude；向量那路用嵌入模型 Qwen3（非 LLM），查询侧带内置前缀 `"Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery:"`，文档侧空。
- **实测坐实两个真 bug（都在 `parse_query` 机械分词）**：
  - **P-A**：2 字母英文缩写被丢（正则要 ≥3 字符）→ "RL"在 RL 库里关键词召回零贡献；且英文 2 字符无 instr 兜底。
  - **P-B**：单字停用词（用/做/是/和/或/及/在）子串替换把中文复合词劈碎→"通用"丢、"应用"丢；"AI ML 的应用"→FTS 完全空手。
  - 缓解：向量那路部分救场；但 base 环境（无 torch）向量关→这些查询真零命中。
- 低优先：vec_rank 连接没 close；fts bm25 与 cjk2 的 +1.0 量纲不一致（只影响 FTS 内部序，RRF 取名次，影响小）；hybrid 的 except 太宽会静默吞向量错误。

**决定（用户拍板）：上方案 A = claude 问题理解层（token 充足，要强的）；agentic（方案 B）留后面**
- **方案 A**（现在做）：检索**前**加一层 claude 把问题→更好的检索输入，根治 P-A/P-B（比补正则彻底）。Qwen+FTS 保留当工具。
- **方案 B**（后面=路线图 ④引用图/⑤两段式/PaperQA2 agentic）：claude 自己驱动搜索循环、多跳、顺引用。**A 是 B 的零件，不浪费**（agent 也要复用问题理解+这些工具）。

**方案 A 待实现的具体设计（下个会话照写）**
1. 新文件 `pipeline/retrieve/understand.py`，`understand_query(question)`：claude -p（lib/claude.py，强模型）→ JSON `{"en_terms":[...],"zh_terms":[...],"hyde":"一段假想中文答案"}`。prompt 要点：展开缩写(RL→reinforcement learning)、关键概念中英双语词（标题/摘要英文+总结中文两边都要）、补同义词、写 2-4 句 HyDE 假想答案（中文，论文总结口吻）。
2. 接进 `search.hybrid`（加参数 `understanding=None`）：FTS 那路不再用易错正则，直接用 claude 给的干净词，每词当**原子短语**（≥3 字 trigram/2 字 instr/英文 2 字 instr 带大小写）→ 绕开 P-A/P-B。需写个 `terms_to_fts(en,zh)` 格式化器（**不要**把 claude 的词再喂回 parse_query，否则"通用"又被劈）。向量那路：嵌入 **HyDE 文本**（而非光问题）→ 召回更准。RRF 融合照旧。
3. 接进 ask.py：仅 --answer/--json(deep) 走理解层；默认快速列表 + claude/torch 不可用 → 回退 parse_query（顺手把 P-A/P-B 在 parse_query 里也小修当兜底）。
4. 代价：每次 deep 查询多 1 次 claude（可接受）。
5. 验证：RL/通用/AI ML 等原来失败的查询现在能召回；base 环境回退正常；log+commit。

### 第四段（06-18）：方案 A 已实现 + 实测 + 遗留成本问题

**改了什么**
- 新 `pipeline/retrieve/understand.py` `understand_query(q)`：claude -p(opus)→ JSON `{en_terms, zh_terms, hyde}`。prompt 见文件内 PROMPT（展开缩写/中英双语/同义词/HyDE 2-4 句论文口吻/没把握别硬编）。claude 失败或解析不出 → 返回 None，调用方回退 parse_query（不阻断检索）。
- search.py：`terms_to_fts(terms)` 把 claude 的干净词切成 (MATCH≥3 字短语, instr<3 字兜底)，**关键：不再把词回炉 parse_query**（否则"通用"又被劈）——这是绕开 P-A/P-B 的核心。`fts_rank/vec_rank/hybrid` 全加形参：有理解层就用干净词喂 FTS + 嵌 HyDE 文本（而非光问题）；没有就回退原始查询。
- ask.py：默认对所有查询先 `understand_query`（用户 2026-06-18 拍板"默认全开，先不担心成本"）；加 --no-understand 逃生口；--json 输出多带 understanding 字段（外部 agent 调试用）。parse_query 的 P-A/P-B 没去补——它只当 claude 失败时的兜底，正常路径不走它。

**实测（research-agent 环境，GPU）**
- 隔离 FTS 那路 A/B（fts_rank 带/不带 understanding，看命中数）：`RL` 0→194、`AI ML 的应用` 0→179、`通用工具箱` 22→182 —— P-A/P-B 坐实治好。
- 端到端 `ask.py "RL 在数字人交互里的应用" -n 5`：5 命中全是 rl-digital-human-interaction 主题、relevance 48–96，排序合理。
- --no-understand：不调 claude（无"理解："日志），老路 + 向量仍出结果——逃生口/回退健全。
- 理解层产出示例：`RL` → en 含 reinforcement learning / policy gradient / MDP…，zh 含 强化学习/策略梯度/马尔可夫决策过程…，hyde ~100 字论文口吻假想答案。

**⚠️ 遗留成本问题（用户明确"先不担心、但要记下来"，待日后用量大再说）**
- 每次 deep 查询多 1 次 claude 调用（几秒 + token）。你自己用无所谓；**外部 agent 出口②若卡住时高频轮询本库，每次都点一炮 claude，会偏重**。
- 当前决定：默认全开、不加节流/缓存（YAGNI，先观察真实用量）。
- 日后若需优化（按性价比）：① 缓存 understanding（同问题不重算，LRU/落盘）；② 给 --json agent 路径单独节流/配额；③ 让"明显简单"的查询跳过理解层。**别现在做。**
- 这条也是为何之前（2026-06-16）撤回了全局 `~/.claude/CLAUDE.md` 的出口②指针——ask.py 还在改；理解层是让它够格重新对外开放的前提，但对外开放前要先想清楚这个成本敞口。

### 第五段（06-19）：问答层框架大讨论——推理过程 + web 实证 + 收敛成 v1

> 用户逐段审查到第 2 步（rerank）时，从"这步怎么做"一路追问，把整个**问答出口的架构**重新想了一遍。框架成品 → `claude-memory/Prompt-structure-design/qa-layer-design.md`（v1 草稿）。本段记**怎么想到那儿的**（有用的是这条思路链）。

**推理链（每一步是用户的一个追问把设计往前顶）**
1. 起点：审 rerank(RCS) 发现两个问题——P2 的 `max_chars=12000` 截断只留头；"只抽证据喂下游"。
2. 用户质疑：Opus 上下文这么大、为什么截断?为什么只给证据不给整篇/PDF?而且**我们当初故意把数字从总结里拿掉（总结=分诊层，数字让位 PDF）——就是赌"要细节去读 PDF"**。→ 醒悟：现有问答层（从"故意没数字"的总结里抽截断证据答细节）**和总结哲学自相矛盾**。→ 收敛：**总结=地图（检索/分诊/缓存的 fan-out），PDF=实地（按需深读）**。答案要细节就读 PDF。
3. 用户：真正 consumer 是**卡在自己项目里来问的另一个 agent**，不是我。→ 出口契约：蒸馏答案+指针+诚实哨兵；理解层要搭"工程问题语→学术概念"的桥；**深读留给有上下文的它**（我们深读是上下文盲）。
4. 用户：不要快，**质量第一**（能等）。→ 把默认从"轻"拨回"重"：默认就深读 PDF、fan-out over 短名单、加核验趟。**召回率变成质量天花板**（漏一篇后面救不回）。
5. 用户：multiagent 直接开几百个小 agent 读论文汇报好吗?→ 去 web 查实证。→ 结论：fan-out 读（独立）好，合并（协调）是雷区。且**别 fan-out 全库**（成本+扔缓存），只 over 检索筛过的短名单。
6. 用户：最后那几篇，Opus 直接读 vs 子 agent 各自总结再汇总，哪个好?→ 再查实证。→ 结论：**装得下→直接读（总结再汇总会掉数字+串味=张冠李戴）；装不下才 fan-out 且"抽证据不写总结"**。
7. 用户：不该只用那几篇，**跨文章内容（合成层+引用图）也该用**。→ 纳入：合成层（可直接答+当脚手架）+引用图（补召回），当二手地图、精确回一手。
8. → 收敛成 `claude-memory/Prompt-structure-design/qa-layer-design.md` 框架 v1。

**web 实证（2026-06-19 搜的，据此定的设计）**
- Chain of Agents（arXiv 2406.02818）：多 agent 各读一段+manager 综合，比 RAG/full-context/其它 multiagent 高最多 10%；因长窗口"抓不住相关信息"，拆开让每个短上下文聚焦。**但这是 LONG 内容的场景**。
- lost-in-the-middle：长上下文过 ~32K 准确率明显掉（Redis/InventiveHQ）。
- Anthropic 多 agent 研究系统：Opus 主管+Sonnet 子 agent 比单 Opus +90.2%，擅长**广度优先独立探索**；但 15× token、且"需共享上下文/强依赖的场景不适合多 agent"。
- Cognition《Don't Build Multi-Agents》：并行子 agent 上下文隔离→冲突决策（Flappy Bird 例）；解法**写入单线程**、共享完整轨迹。
- MAST 失败学（NeurIPS2025，1600+ 轨迹）：多 agent 生产失败率 41–86.7%，协调崩溃占 36.9%，**无结构放大错误 17.2×**，有依赖任务过 ~4 agent 见顶。
- 装得下时 直接读 > 总结再汇总：压缩式普遍不如 full-context、迭代管道"灾难性信息丢失"（arXiv 2502.06617）；层级总结掉实体/数字（Springer）；分块独立处理串味/误 attribution（Galileo）。
- full-context 跨文档推理优势 + 能发现非显然连接（Redis/Meilisearch）；混合（检索+长上下文综合）8 场景 7 胜；约 60% 问题两法答案相同。

**关键洞见（值得记住的三条）**
- **总结=已缓存的 fan-out**：贵的阅读建库时做一次存下来，查询别重做。
- **fan-out 的位置在"读"（独立），不在"合并"（协调）**：读尽管并行，合并必须单线程+结构化+核验。证据一致。
- **装得下/装不下是分界**：装得下直接读（保细节+跨文章+不串味）；装不下才拆，且抽证据非总结。两条上一轮看似矛盾的结论，按"内容是否在聚焦区内"统一了。
- 状态：框架 v1 写进 `claude-memory/Prompt-structure-design/qa-layer-design.md`，未落代码。用户要先诊断（末尾列了 6 个薄弱点/待定）。现实约束：221 篇仅 ~41 篇有总结（用户在并行重做），框架落地要等料铺开。

### 第六段（06-19）：检索定两套模式 + 决定先搭并默认 agentic（方案 B）

> 用户逐步审到第②步（混合召回）时，质疑"为什么不让 claude 直接进文件夹找、并发开小 agent，token 又不是问题，中间加索引层不是加摩擦?"——把"索引 vs agentic"岔路口摆开了。

**讨论收敛**
- 承认用户直觉对（当前规模）：本机仅 ~41 篇有总结。"让 claude 暴力全读判断"= 并发 agent 各读一篇总结判相关 → **召回 100%（全看了不会漏）、更简单、少摩擦**。索引此刻**对召回无增量**（全读本就满分）。
- 索引此刻真正的价值（不在召回）：①地图能力——vec.sqlite 还用于找重复（已抓出 1 篇重复入库）/找相似/将来顺引用图拉邻居，"全读"给不了这种关系；②低延迟（~200ms vs 开几十个 agent 分波跑几秒-几十秒）；③能活到库长大——蓝图是"每周增量永远长"，2000/1 万篇时暴力全读（就算 token 免费）latency/并发也扛不住，索引是"读一次建坐标、以后查询近免费"。
- 关键澄清：用户说的"让 claude 自己找"= 之前记的**方案 B（agentic 检索，PaperQA2 式）**，我们没否决、只往后排了。而且**就算上 agentic，那个 claude 也不闭眼全读，而是调检索工具**——索引是 agent 的工具，不是对立面。"A 是 B 的零件，不浪费。"

**用户拍板（2026-06-19）**
1. 把方案 B 搭起来，目前先默认用方案 B：库小时让 claude 自驱探索，减少摩擦；配合往上蒸馏的合成层，agent 先读高层笔记再钻论文，越长大越好使。
2. 方案 A（索引）不删：留作大库模式兜底 + agentic 随手能调的工具。
3. mark 成两套模式：小库 agentic / 大库索引，按总结篇数切换；2000 篇不会很快到，真撞到全读吃力再切——**别现在为大库过度设计**。
- token 免费是把 agentic 提前的主因（原先排后主因之一=怕高频探索烧 token，顾虑消）。
- 落档：两套模式写进 `claude-memory/Prompt-structure-design/qa-layer-design.md`「## 8. 检索的两种模式」。方案 B 未落代码。

### 第七段（06-19）：方案 B 设计深挖 + web 实证逐条核 + 三处认错纠偏（未落代码）

> 接第六段。用户没让动代码，而是逐层追问把方案 B 的实证地基夯实，过程中我犯了几个含糊/过度推销，被用户一一抓出纠正。这段记**讨论结论 + 我纠了哪几条**，比记"搭了什么"更有用。

**先定的实现岔路：方案 B 用"claude 真·自驱(A)"不用"python 编排 fan-out(B)"**
- 用户拍板 A：ask.py 起 claude -p（开文件权限、cwd=仓库根，照 bot.py 路子），给它库地图（store/summaries 地图 / store/pdfs 实地 / db 元数据）+ 工具（search.hybrid 可调）+ 纪律（多看/顺引用/深读 PDF/闭集引用/诚实哨兵/蒸馏），让它自己决定读哪些。理由：摩擦最小，最贴"让它自己探索"。代价：输出松，闭集引用/哨兵/--json 格式要在 prompt 里硬钉。
- 用户要求：prompt 最后写时给他过目；**诚实哨兵**这次靠"它真探索过才说没有"，不再是"候选空了机械短路"——agentic 之后哨兵才真正有分量。
- 新文件（待写）：`pipeline/retrieve/explore.py`（agentic 探索引擎）+ ask.py 加模式开关（默认 agentic，大库回退方案 A 管道）。复用①理解层/②search 当工具/⑦answer 的 quality_tier+verify_status 透传+闭集引用。

**web 实证（06-19 第二批，逐条查证）——把"fan-out 分读"拆三种打法对比**
- ① 一个 agent 单上下文全塞 / ② 并发多 agent 各读一段再合 / ③ 用检索工具只挑相关篇。
- ①② 之争（一个 vs 一堆）：Chain of Agents（Google,NeurIPS'24,2406.02818）——长内容时 ② 比 ①/③/其它 multiagent 高最多 10%（短上下文聚焦、避 lost-in-middle）。
- ①③ 之争（自己全读 vs 用工具）：Long Context vs RAG（2501.01880,ACL'25）——**装得下时 ①（全读）反比 agentic RAG +4.4%、比朴素 RAG +10.9%**；但 agentic RAG > 朴素 RAG。
- ②③ 之争：也在 CoA 里——②(CoA)>③(RAG) 最多 10%；但二者**非对手、可叠**（③先筛→②读活下来的；Anthropic 多 agent=②+③；PaperQA2=③+agentic）。
- 合并是雷区：MAST(2503.13657,NeurIPS'25,1600+ 轨迹) 失败率 41–87%、协调崩溃 37%、无结构放大错误 17×→**合并必单线程+结构化+核验**；map-reduce 摘要掉实体/数字（Galileo/GoogleCloud）→**fan-out 要"抽证据"不"写小作文"**。
- 新旧之辨（用户质疑研究太旧/模型变强）：补查 2025-26——lost-in-middle 2026 仍真（LongBench v2/HELMET；Sonnet4.5 200chunk 中段塌，且对推理比对找事实更狠）；选择性检索仍常胜"全塞"（查询类）；但"上下文不再是差异点、agent 层更重要"、Claude 长上下文可靠性更好。结论：退化变弱没消失，工具价值从"补容量"转成"注意力卫生"，**41 篇小库增益有限、规模越大越值**。

**三处认错/纠偏（用户抓的，记下防再犯）**
1. "装得下"含糊：我混用了。澄清=**两个独立轴**——轴 1（读：一个 agent 全读 vs fan-out）、轴 2（合成：相关料能否进**一个 agent 单上下文**推理）。设计文档"装得下/装不下"指轴 2，但我写成"Opus 直接读 K 篇 PDF"把读+推理塞一个 agent，才显得像轴 1。41 篇：两轴容量都几乎不触发（全总结 ~10-20 万 token、连 41 篇 PDF~60 万都进 1M），所以 fan-out 此刻只为"读得干净"非"容量逼"，小库增益有限。
2. 拿 PaperQA2"超人"背书我们的搭建=过度推销：超人（85.2%precision>博士 73.8%，2409.13740）是在**几百万篇、②根本不可能**的区间拿的（③+agentic）；对 41 甚至 1000 篇不构成搭建依据。已退回。研究本身**不矛盾**：②③从没在同一库大小比过——**读得完用②（更强）、读不完只能③（仍超人），没有"被迫选更差"的场景**。②③是**按库大小交接的接力，不是二选一比赛**。
3. 漏了合成知识层（用户点"净化语料库"找回）：整段②③对账只拿"总结+PDF"算，漏了第三种料=合成层（跨论文蒸馏的方法族/共识/矛盾，§4）。加回后图变顺：**合成层=②的离线缓存版+③的语义升级版**——大意级问题它当场答（零 fan-out 零检索）、细节级当**比向量更聪明的路由**（已推理过的语义目录，指"去哪簇钻"）。它才是让 agentic 活到库长大的关键：库越大蒸馏越厚、地图越全（与③"库越大筛越狠"逻辑相反）。代价：吃总结（41/221 料薄，排总结铺开后）、二手会过期（精确回 PDF/定期重蒸/矛盾别抹平）、维护成本没算（薄弱点#3）。

**三个规模的对照（本段收敛）**
- ~41 篇（现在）：① 一个 Opus 全读 / 顶多②；③索引=可选聚焦+找重复，不当闸。
- ~1000 篇：总结 ~3M token 塞不进 1M→必须 ③筛（1000→~30-50）→②/①读→合成；③转正成召回闸；合成层在此真正接管导航（比③向量更聪明）。切换临界落在**几百~1000，不是 2000**。
- 几百万（PaperQA2）：只能③ agentic 多轮检索（超人即此区间）。
- 实证出处（第七段）：CoA 2406.02818 · LongContext-vs-RAG 2501.01880 · MAST 2503.13657 · PaperQA2 2409.13740 · lost-in-middle 2307.03172（+2026 LongBench v2/HELMET 复现） · Haystack Engineering 2510.07414。
- ★ 论文/对比/数字两批已合并汇总 → `claude-memory/Prompt-structure-design/qa-layer-evidence.md`（一处可查）。SESSION 这两段保留当"怎么想到的"时间线。

### 第八段（06-19）：实证深挖第三批 + 出口落地计划收敛（全读模式，待开工）

**实证深挖第三批（已汇总进 `claude-memory/Prompt-structure-design/qa-layer-evidence.md` §7，这里只记结论）**
派 3 个 agent 精读本地 ref/papers/ 6 篇（RAG 综述 2507.18910/Agentic 综述 2501.09136/PaperQA2/OpenScholar/RAPTOR/GraphRAG）+web 扒 2 篇 2026 新论文。核心：
- "小库全读 vs 选择性检索"直接对比不存在（领域都在百万篇区间）。最接近=GraphRAG **C0(预蒸馏层) vs TS(临时全摘)：质量打平、合成层赢成本省 97%** → 合成层是"省/快/覆盖全"工具，非"更准"。
- 多篇一致印证"顶层导航+下钻原文"（RAPTOR 必须保叶层；GraphRAG 细节被稀释）。RAPTOR 赢的是扁平分块检索，**不是读全文**——别拿它当"合成层赢过读原文"的证据。
- 领域真建议=**"先把检索质量做好，agentic 救不了烂检索"**（Agentic 综述§10.3，撞上我们 6/17"召回是地基"）。
- 增量更新是所有论文的真空（GraphRAG 全量建图 281min/1M token）——"活的合成层"得我们自己啃。

**出口实现方案：收敛成「纯全读 + 模式分发」（用户拍板，本段最重要）**
逐步澄清后定下（覆盖了第七段的"claude 真自驱"——自驱是为用工具，现在不用工具就退成更简单的全读）：
- 现规模（库小）默认=「全读」模式：python 把**全部论文总结塞进一个 prompt**（召回地板：一篇都不漏），一个 Opus 答。
  - 唯一工具=Read：总结塞 context 保召回；**给 Read 权限能开 store/pdfs/ 按需读 PDF 一手**（精度）。不给 search/Task/自主搜索——论文全列在 context 里，不需要"找"。
  - ⚠️ PDF 必须可读（用户明确纠正我一版过度限制）："不用工具"指不给 search/Task/自主发现，**不是禁读 PDF**。读（总结+PDF）本就不是工具。
  - 答案纪律：闭集引用 [n]、诚实哨兵（撑不起就"库里没有"）、quality_tier/verify_status 标记透传、蒸馏+给 pdf_path 让来问的 agent 自己深钻。
- 代码结构=「ask.py 模式分发器 + answer.py 共享契约层 + 每方案一个模块」（用户要求：其他方案也要写进去别写死；沿用 retrieve/ 段文件夹+path shim+ask.py 留根约定）：
  - `ask.py` 出口总指挥，按【模式】分发（像 run.py 之于主链）；可按库大小自动选+--mode 覆盖。
  - `retrieve/readall.py` 🆕 模式①全读（现在默认）：塞全总结+能读 PDF，一个 Opus。
  - `retrieve/search/rerank/index/understand.py` ♻️ 保留=模式②索引管道（方案 A）的零件 + 大库工具。
  - `retrieve/answer.py` 🔧 升格"共享契约层"：所有模式都用它出 [n] 引用/哨兵/标记/--json（格式统一）。
  - `retrieve/（将来）agentic.py / synthesis.py` ← 大库 agentic / 合成层，留好槽。
  - 模式：readall（默认）/ pipeline（方案 A，保留）/ 将来 agentic（大库，带 search/Task）/ synthesis（合成层）。
  - 退役不硬删（用户选）：rerank 退出默认但留盘；understand 默认不跑（全喂就不用路由），留大库用；search/index 留作工具/找重复。
- 交互（出口②契约）：别的 agent 调 `ask.py "<q>" --json`（本机或经 remote-access/ SSH wrapper）→拿 `{answerable,answer(带[n]),sources:[{doi,quality_tier,verify_status,summary_path,pdf_path}]}`→它读蒸馏答案、要精确自己拿 pdf_path 深读；answerable=false=诚实"库里没有"。一问一答、非实时对话。

**prompt 草稿（已给用户看过两版，最终版待写）**
全读模式 prompt 要点（写时给用户过目）：①只用下面给的总结答、每句末标 [n]；②闭集引用绝不编库外 DOI；③诚实哨兵；④**总结=地图有意略数字，要精确就自己开 [n] 的 PDF 读一手 + 把 pdf_path 给来问的人**；⑤suspect/flag/major/stale 源 ⚠️ 标注；⑥蒸馏交付别倒原文。末尾输出可解析 JSON 块（answerable/sources/），ask.py 解析失败→机械兜底"无法确定"不瞎编。
- 状态：未落任何代码。现实约束没变：库现在 0 篇总结（用户在重做），这套搭好只能单元自测，真答案等总结回来几篇。

### 第九段（06-19）：金字塔架构收口 + 五方案校准 + 方案④全读已落代码

> 用户逐段把出口实现敲定并**真写了代码**。本段=①定金字塔主干（§9）；②校准五方案速查（§10）；③实现全读模式 readall.py；④全 log。

**讨论收口（怎么从"全读"想到"金字塔"）**
- 用户连环追问把方案④从"查询时全读"拨正到**金字塔**：贵的"读"建库时做一次缓存成层（总结=每篇缓存、⑤合成层=跨篇缓存），查询只读缓存层、为精确才下钻 PDF。两条约束逼出唯一解：①会长到不止 100 篇→查询时全读成本 ∝N 活不过增长蓝图；②框架后面有⑤蒸馏层="把贵的 fan-out 缓存成地图"的成品。→ 写进 `claude-memory/Prompt-structure-design/qa-layer-design.md` §9（只追加，§4/§8 既有"为什么做合成层"原因保留）。
- fan-out 的两种讨论清楚：A=给主 Opus Task 工具自己 spawn（用户选这个）；B=python `claude.pool` 编排。结论：**合并永远单线程**（MAST 17×），子 agent 只回证据不下结论；现规模其实连 fan-out 都用不上（装得下）。
- 五方案速查（用户校准的权威版）拢成 §10：①FTS 淘汰 / ②方案 A 索引管道（降级成工具+大库召回闸）/ ③方案 B agentic（大库槽未写）/ ④全读（现默认）/ ⑤合成层（未建）。按库大小接力，非二选一。

**验证（动代码前先验机制，headless 真跑）**
- `claude -p --allowedTools "Read,Task"` 能 spawn 子 agent + 子 agent 能 Read 开 PDF——实测让子 agent 读 MARL 综述 PDF，回出标题/作者/页眉/页码，`num_turns:2 is_error:False`。**不需要 `--dangerously-skip-permissions`**，Read 权限传到了子 agent。底层支持坐实。

**实现（清单版全读）**
- 设计选择（逐步讨论定的）：清单进 prompt（短）、**总结正文不进**——给 Read+Task 让 Opus 自己把总结读全（召回地板：篇数少能读全=不漏）、相关再 Read PDF、多了可 Task 并发。比"总结全文贴进 prompt"省（prompt 不每次重发几十万字）+不稀释注意力；代价=召回靠模型读全（库大了变只挑读，那时再上检索筛）。清单**带 ⚠️ 质量/核查标记+DOI**（只在 DB 里，不在总结文件夹/那几个残缺 json 里）=为什么要 python 拼而非直接丢 store/summaries 文件夹。
- 🆕 `pipeline/retrieve/readall.py`：`load_papers`（默认全库跨主题/`--topic` 限定）→`build_catalog`（每篇=[n] 标题+⚠️ 标记+slug+总结路径+pdf 路径，正文不放）→`run_claude(tools=["Read","Task"])`→`_extract_json`（围栏+平衡括号兜底）→cited[n/slug]→`answer.make_source` 回填。**模型只吐 `{answerable,cited:[{n,slug}]}`，DOI/路径 python 据 n 回填=零 DOI 幻觉**；解析失败→机械兜底 answerable=false 不瞎编；空范围→哨兵。
- 🔧 `ask.py`：加 `--mode {readall,pipeline}`（默认 readall）+`--topic`；deep（--answer/--json）走 readall 分支、**不碰 fts/vec 索引**（全读不检索）；pipeline=老路（理解→混合召回→精排）留着；非 deep 命中列表仍走 search。understand/rerank/search/index 从默认路退役，留盘当大库/agentic 工具。
- 🔧 `answer.py`：抽出 `make_source(main,status_map,paper,rcs=None)` 共享契约助手（readall/pipeline 共用，⚠️ 标记+verify 态+DOI/路径回填口径统一）。
- 自测全过（monkeypatch run_claude，不烧配额）：真库 20 篇拼清单→解析→回填（tier=flag/trusted、verify=pass/stale 正确透传、无 DOI 篇 doi=null）、slug 对不上以 n 为准并记日志、解析失败兜底、空范围哨兵、_extract_json 三变体、ask.py --help 接线。未做真端到端（会起 claude 读 20 篇总结、慢+烧配额；库还在重建中，等用户要再真跑）。
- 状态：代码已落（readall.py 新增 + ask.py/answer.py 改），自测过，未提交（等用户 push）。库现 20 篇有总结（cron 重建中，曾 0），真答案质量等总结铺开再真跑端到端验收。留槽未做：②pipeline 已存可用、③agentic explore.py、⑤合成层、prompt 缓存（验 claude -p 跨次缓不缓存）、真 gold 集。

---

## 2026-06-17 · 检索层（知识库出口②）方案调研

> 来源：旧 `logs/SESSION-2026-06-17-retrieval-layer.md`（忠实迁入）。
> 目标：把当时 `ask.py` 的纯 trigram 全文索引升级成能服务"**监控 RL 训练的 agent 带症状来查答案**"的检索层。
> 本会话只做**调研 + 攒参考 + 出方案**，没碰任何 pipeline 代码、没动生产库。配套记忆：`memory/kb-retrieval-upgrade-research.md`（最全）。

### 一、本会话产出（都在 gitignored 的 ref/）
- 代码库（clone）：`ref/paper-qa`（早先已有）、`ref/HippoRAG`、`ref/LightRAG`、`ref/OpenScholar`。
- 论文 13 篇 `ref/papers/`：PaperQA2/PaperQA_v1/RAPTOR/GraphRAG/HippoRAG/HippoRAG2/LightRAG/Self-RAG/CRAG/Agentic_RAG_survey + 第二批 OpenScholar/HyDE/RAG_systems_review。均核过首页标题无张冠李戴。
- 索引 `ref/papers/INDEX.md`（什么/为什么下/重复项）。

### 二、关键结论（讨论中达成的共识）
1. **数据来源澄清**：生产库 `db/papers.sqlite`（5 表，元数据+引用图+路径）是流水线**边跑边写**的、和总结**耦合**；正文（PDF/总结）是磁盘文件，库里只存路径。检索层（fts.sqlite / 未来 index）是**事后扫描、解耦、可重建**的旁路。
2. **清库重跑 summary 不影响检索层方案**——因为它解耦可重建；只影响"实现时机"（重跑稳定后再索引，且切片对齐新总结结构）。
3. **地基是召回（对意思），不是提炼（RCS）**——消费者是会读的 agent，RCS 可降级；召回（语义）无人能兜底，必须先做。
4. **⚠️ 必须为规模设计**（用户强调）：20 篇/天→两年几万篇/几十万片段。reranker/ANN/图/RAPTOR 在那量级都是刚需，不能因现在 221 篇就砍。

### 三、当时方案（为规模 baked-in，分期）
- 借鉴：PaperQA2（混合召回+RCS）+ OpenScholar（两段检索+自反馈，规模蓝图）+ HyDE（症状 query 扩写）+ Anthropic Contextual（切片贴上下文）+ CRAG/Self-RAG（可靠性门）+ citations/RAPTOR（进阶）。
- 架构：离线索引管线（扫总结→切片→嵌入→向量库+FTS，增量）‖ 在线查询（〔HyDE〕→向量+BM25 混合召回→reranker 精排→quality_tier 过滤+可靠性门→--json 指针/RCS 答案）。
- 分期：P0 切片+嵌入+混合召回+reranker+--json ｜ P1 HyDE+可靠性门 ｜ P2 RCS/agent 多轮工具 ｜ P3 citations 邻居/RAPTOR。

### 四、当时待拍的决定 / 待办
1. 向量库：LanceDB（倾向，认准扩容免迁移）vs sqlite-vec（最简，同 fts 生态）← 唯一需要现在定的。（注：后续实际选了 sqlite-vec。）
2. 嵌入模型：bge-m3 vs Qwen3-Embedding（可调维度）。（注：后续选 Qwen3-Embedding-0.6B。）
3. reranker：bge-reranker（本地）vs ColBERT。（注：后续 RCS 用 claude -p，没用本地 reranker。）
4. 是否现在就把方案落成 `claude-memory/retrieval-layer-plan.md`。
5. 前置：用户计划清库 + 全量重跑 summary（范围待定：只删库 / 删库+删总结+重跑 / PDF 保留）；和正在测 summary 的另一 agent 对齐别撞车。实现检索层放在重跑之后、对齐新总结结构。

---

## 2026-06-10 · RAG 第一步：ask.py + FTS5 落地

> 来源：旧 `logs/SESSION-2026-06-10-recover-rag.md`（混合文件，recover/取全文部分已迁入 fetch 模块；这里只忠实迁入 retrieve 相关的 RAG①/ask.py + ARS 回顾两段）。
> 这是出口①「用户本人来查答案」+ 知识库 RAG 的最早一版落地，后续 06-17 方案调研、06-18 混合召回/理解层、06-19 金字塔/全读都建在它之上。

### ④ RAG 第一步落地：`ask.py`（FTS5 库内问答）
- **索引** = 独立 `db/fts.sqlite`（gitignored、可重建，不碰生产库）：
  - `fts_sum`（trigram，索引 标题+摘要+中文总结）
  - `fts_text`（porter，英文全文）⚠️ **当时的 fts_text 英文全文索引后于 2026-06-16 移除**（总结都从 PDF 写、英文全文不再维护；检索只覆盖标题/摘要/中文总结，要原文细节直读 store/pdfs 的 PDF）——此处保留是历史记录，别按它现状理解。
  - mtime 增量；当时 221 篇唯一论文。
- **查询切词**：英文取词；中文按停用词切段——≤4 字精确短语、长段拆滑窗 trigram、2 字词 instr 全扫兜底。
  - ⚠️ **踩的坑：FTS5 虚拟表上 LIKE 静默返回 0 行，必须用 `instr()`**。（这条坑后续 06-18 审查时又牵出 parse_query 机械分词的 P-A/P-B bug，治法见上方 06-18 第三/四段的理解层。）
- **出口认 quality_tier（硬约束）**：suspect 减半 + ⚠️ 标注；flag 注"预印本"。合"标记进库、出口认标记"哲学。
- **`--answer`**：claude -p 综合前 5 命中，带 [编号] 引用；实测会老实说"库里没有"不编造（诚实哨兵的最早形态）。

### ⑤ 同期发现 / ARS 接口回顾（retrieve 相关）
- **Bipedal Robots 重复入库**：以两个 id 重复入库（slug `..._Bipedal_Robots` / `..._2`，跨主题 merge 没合上），待去重。（后续 06-18 由 `tools/similar.py` 余弦 1.000 坐实，仍在 TODO。）
- **ARS deep-research / corpus-first 与 RAG 接口的回顾**（只记录、当时未动手）：`ref/academic-research-skills`（ARS）的 deep-research 默认联网现搜、不基于本地库；但其 **corpus-first 模式可吃我们导出的 `literature_corpus[]`**，与 RAG 计划有接口——即出口③「idea→论文流水线」用 ARS 吃本库语料的那条桥（后由 `tools/export_corpus.py` 实现）。
