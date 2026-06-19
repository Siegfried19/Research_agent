# SESSION 2026-06-18 — 知识库出口/检索层升级（第一步：找得准）

> 目标：把出口 `ask.py` 从"纯关键词、对字不对意思"升级到"语义召回 + 精排 + 会说不知道"。
> 方案依据：`ref/papers/` 那批 RAG 论文的综合调研（RAPTOR/PaperQA2/GraphRAG/LightRAG/HippoRAG/Self-RAG/CRAG/HyDE/OpenScholar）。
> 用户决定：上嵌入（本地小模型，非 LLM）；分簇用 claude -p；先做第一步（任务 #1–#9）。

## 架构落点
- 出口检索层独立成段文件夹 `pipeline/retrieve/`（不在 run auto 主链上）：index/search/rerank/answer。
- `ask.py` 留根（公共API路径冻结），瘦身成入口/总指挥，内脏搬进 retrieve/。
- 嵌入引擎 `lib/embed.py`（跟 claude.py/codex.py 并列的第三个引擎，但不是 LLM）。
- 模型缓存 `pipeline/retrieve/models/`（gitignored，HF_HOME 指向）；坐标库 `db/vec.sqlite`（gitignored，可重建）。

## 环境（方便迁移）
- 新建 conda 环境 **`research-agent`**（conda-forge 渠道 + python 3.12）——顺带根治 anaconda base 的 libstdc++ CXXABI 报错。
- 装：GPU torch 2.12.1+cu130 + sentence-transformers 5.6.0 + sqlite-vec 0.1.9 + requests。
- 验证：CUDA 可用=True，认出 RTX 3060 Laptop（5.65GiB）。
- ⚠️ 6GB 显存放不下长序列大 batch → embed.py 用 fp16 + max_seq=2048 + batch=8，并带 OOM 自动减半重试。
- 迁移抓手：待生成 `environment.yml`（TODO）。

## 关键发现
- ⚠️ **这台机器只有 39 篇被总结**（库里 221 篇论文，但 status=summarized=39，磁盘总结文件=39）。CLAUDE.md 写的"221篇全已总结"在此机不成立——疑似迁移/清库后总结没全带过来。用户已知会"可能删总结重做"。不阻塞检索搭建（有几篇嵌几篇，自动随总结增长）。

## 速度实测(用户关心)
- 模型 Qwen3-Embedding-0.6B，1024维，fp16，max_seq=2048。
- **GPU(3060,batch8)：215 ms/篇** | **CPU(batch4)：21,000 ms/篇** → GPU 快约 100×。
- 全库 221 篇建索引 GPU 实际 ~47s。结论:**必须用 GPU**(长总结 O(L²) 注意力 CPU 上不现实)。

## 进度 —— 第一步(任务#1–9)全部完成,端到端跑通
- [x] #1 装嵌入+计时:见上。
- [x] #2 坐标索引 db/vec.sqlite(retrieve/index.py):全库 221 篇量坐标(没总结的用标题+摘要),增量靠 body md5,OOM 自动减半重试。
- [x] #3/#4 混合召回(retrieve/search.py):FTS5(对字)+向量(对意思)RRF 融合。中文概念问题混合比纯FTS多召回相关篇。
- [x] #5 RCS 精挑(retrieve/rerank.py):claude -p 逐候选按问题打分(0丢)+抽证据,实测打分准、证据对题。
- [x] #6 --answer(retrieve/answer.py):闭集引用[n]+quality_tier透传+**会说不知道**(量子纠错问题→"库里没有相关内容"哨兵,确定性短路)。实测跨4篇综合+自列局限,质量高。
- [x] #7 --json:{answerable, answer, sources[{doi,quality_tier,rcs_score,summary_path,pdf_path}]},纯stdout干净JSON(日志走stderr)。
- [x] #8 验收harness(tools/eval_retrieval.py)+种子gold(store/eval_gold.json):**纯FTS Recall@10=0.67/MRR=0.500 → 混合=1.00/0.548**,向量把FTS漏的捞回。⚠️真30–50条gold待用户手标,且最好总结重做定稿后再跑。
- [x] #9 找相似/揪重复(tools/similar.py,读坐标不调GPU):dup **实战抓出已知重复入库**(RL Robust Parameterized Locomotion 以 10.48550/.. 和 arxiv:.. 两 id 入库,余弦1.000)。

## 入口/迁移
- ask.py 瘦身成总指挥(混合召回→RCS精挑→带引用回答/会说不知道);保留公共参数,加 --no-rerank。
- ask.py 在 **base 环境自动回退纯FTS**(无torch时),research-agent 环境用全功能。
- environment.yml 写好(conda env create -f 一键重建)。

## 待办/缺口(给下一步)
- ⚠️ **运行环境**:向量功能需 `research-agent` 环境;若要 ask.py 默认全功能,整个项目(含 cron)应切到该环境跑(用户已倾向"整个项目搬进去"的A方案,尚未改 cron/PATH)。
- #6 的 Self-RAG 式逐句自检(ISSUP)未加(当前靠闭集引用+cannot-answer兜底,够用;自检是增强项)。
- 真 gold 集(#8)+ 第二步合成层(#10)/增量(#11)/引用图(#12) 留后续。
- 这台机器只 39 篇有总结,等用户总结重做后重跑 index 即可(增量自动)。

## 文件清单(本会话新增)
- lib/embed.py — 嵌入引擎(非LLM,Qwen3-Embedding-0.6B,fp16/GPU,OOM自适应)
- retrieve/index.py — 坐标索引(vec.sqlite,增量,knn)
- retrieve/search.py — 混合召回(FTS5+向量+RRF)
- retrieve/rerank.py — RCS 精挑(claude -p)
- retrieve/__init__.py、retrieve/models/(模型缓存)

## 续(2026-06-18 第二段):质量收口 + 与 summary-verify 对齐
> 已提交 `8b6c0de`(第一步全部)。本段修两类问题:嵌入质量妥协 + 多版本/核查态对齐。

### 嵌入质量(用户要"保证质量")
- **embed.py 改质量优先**(原为迁就 6GB 显存的妥协):fp16→**fp32 满精度**;max_seq 2048→**16384(实质不截断**,最长嵌入体~13k字符<1万token,<模型原生32768);GPU_batch 8→**1**;OOM 兜底升级=batch=1 仍爆就**整批退 CPU**(满精度必完成)。
- 实测全量重嵌 221 篇:**28.6s / 显存峰值 2790MiB**(6144 总量,富余一半)。反直觉更快=多数论文只标题+摘要序列短,batch=1 省了大批量 padding。已 `index --force` 全量重建。

### 对齐修复(发现 answer.py 漏对齐:故意 vs 忘记 → 判定为忘记)
- **answer.py 取总结路径改读 DB** `summary_versions ORDER BY version DESC`(与 index/search/rerank 统一);删原 `sorted(glob("v*.md"))[-1]`——会在 v10+ 字符串排序误取 v9,且可能与 DB 不一致。

### A 组(与 summary-verify 多版本对齐,本段重点)
- **A1 检索层认 verify 核查态**:`verify_summaries.write_report` 多落结构化 `verify_status.json`(`{id:{verdict,version}}`,跨轮合并保留旧篇);`answer.py` 读全库聚合(`load_verify_status`,同篇多 topic 取最高版)+ `resolve_verify`(无记录=`unverified` / 记录版本<当前=`stale` / 否则=verdict)→ 透传进 `--json`(`verify_status`+`summary_version`)+ 答案对 **major/stale 加 ⚠️**(其余 pass/minor/unverifiable/unverified 不打扰回答)。**只标注不过滤**,合"标记进库、出口认标记"哲学。
- **A2 index 自动刷新**:`run.py` 加 `refresh_index()`(best-effort,无 torch 时吞错不打断主链)+ 独立 `reindex` 阶段;挂到 `auto`/`auto-sum`/`auto-sum-next` 收尾 + 单跑 `sum`/`finalize`/`verify` 后。消除"resummarize 出新版、检索还用旧版"窗口(vec 不像 fts 那样查询时自增量,必须显式重建)。
- 单测全过:resolve_verify 5态、load 跨topic取高版、write_report 落盘+合并、reindex 入口增量跳过。
- ⚠️ **旧 topic 的 verify_status.json 待下次 verify 生成**——没从旧 .md 回填(.md 只覆盖最后一轮、pass 仅按标题、易错标);在那之前老篇一律显示 `unverified`(诚实未知,不误标)。

### 仍待办(B/C/D 组,见对话清单)
- B: 真 gold 集 / Self-RAG 逐句自检(ISSUP) / rerank max_chars=12000 截断(最长11119已逼近)。
- C: 合成知识层 / 引用图扩展 / 两段式。
- D: 39篇总结待重做后重跑 index;cron/PATH 切环境(envguard 已能自动 re-exec,未在 cron 实跑验证)。

## 续(2026-06-18 第三段):逐步审查问答 pipeline + 决定上 claude 问题理解层
> 用户在**逐段严谨审查**整条问答管道(plan→确认→实现→验证→log→commit;见 memory `working-style-review-pace`)。

### 已提交
- **第0步(建索引)优化** `35bfb2c`:嵌入上限 16384→**24576**(实测fp32/batch1单篇峰值8k=2.3G/16k=3.4G/24k=4.5G,留~1.2G;+`expandable_segments`防碎片+CPU兜底;生产221篇实测峰值仅2671MiB;问答零影响,坐标不变)。索引增量改**两段钥匙**(新 `retrieve/freshness.py`,fts+vec共用):便宜钥匙=md5(title+abstract+path+mtime)不读文件→秒跳(治P3),fts/vec判据统一(治A:abstract改动fts也抓得到),每查询reindex近免费(治B);vec钥匙变了才读全文算body_hash精确确认(零问答风险);+busy_timeout(C)+孤儿回收(D)+旧meta schema自动迁移。全验证过。

### 第1步(混合召回 search.hybrid)审查结论
- 结构对、防御足、**无文本截断**(只k=50/topn=20召回宽度)。**不调 claude**;向量那路用嵌入模型 Qwen3(非LLM),查询侧带内置前缀 `"Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery:"`,文档侧空。
- **实测坐实两个真 bug(都在 `parse_query` 机械分词)**:
  - **P-A**:2字母英文缩写被丢(正则要≥3字符)→ "RL"在RL库里关键词召回零贡献;且英文2字符无instr兜底。
  - **P-B**:单字停用词(用/做/是/和/或/及/在)子串替换把中文复合词劈碎 →"通用"→丢、"应用"→丢;"AI ML 的应用"→FTS完全空手。
  - 缓解:向量那路部分救场;但base环境(无torch)向量关→这些查询真零命中。
- 低优先:vec_rank连接没close;fts bm25与cjk2的+1.0量纲不一致(只影响FTS内部序,RRF取名次,影响小);hybrid的except太宽会静默吞向量错误。

### 决定(用户拍板):上**方案A = claude 问题理解层**(token充足,要强的);agentic(方案B)留后面
- **方案A**(现在做):检索**前**加一层 claude 把问题→更好的检索输入,根治 P-A/P-B(比补正则彻底)。Qwen+FTS 保留当工具。
- **方案B**(后面=路线图④引用图/⑤两段式/PaperQA2 agentic):claude 自己驱动搜索循环、多跳、顺引用。**A 是 B 的零件,不浪费**(agent 也要复用问题理解+这些工具)。

### 方案A 待实现的具体设计(下个会话照这个写)
1. **新文件** `pipeline/retrieve/understand.py`,`understand_query(question)`:claude -p(lib/claude.py,强模型)→输出 JSON
   `{"en_terms":[...], "zh_terms":[...], "hyde":"一段假想中文答案"}`。
   prompt 要点:展开缩写(RL→reinforcement learning)、关键概念**中英双语**词(标题/摘要英文+总结中文两边都要)、补同义词、写2-4句 HyDE 假想答案(中文,论文总结口吻)。
2. **接进 `search.hybrid`**(加参数如 `understanding=None`):
   - FTS那路:不再用易错正则,直接用 claude 给的干净词,每词当**原子短语**(≥3字trigram/2字instr/英文2字instr带大小写)→ 绕开 P-A/P-B。需写个 `terms_to_fts(en,zh)` 格式化器(**不要**把claude的词再喂回 parse_query,否则"通用"又被劈)。
   - 向量那路:嵌入 **HyDE 文本**(而非光问题)→ 召回更准。
   - RRF 融合照旧。
3. **接进 `ask.py`**:仅 `--answer`/`--json`(deep)走理解层;默认快速列表 + claude/torch不可用 → 回退 `parse_query`(所以**顺手把 P-A/P-B 在 parse_query 里也小修一下当兜底**)。
4. 代价:每次 deep 查询多 1 次 claude(可接受)。
5. 验证:RL/通用/AI ML 等原来失败的查询现在能召回;base环境回退正常;log+commit。

### 后续(未做,按路线图)
- 第2步 P2:`rerank.py:52 max_chars=12000` 截断只留头,新长总结尾部(适用边界/批判)会被砍——重做总结后必咬。修法:抬上限/掐头留尾。
- 第3步 P1:`--no-rerank`+`--answer` 没evidence必瞎答(`answer.py:70`)——禁该组合或no-rerank时用总结摘录当证据。
- 路线图 ④引用图 / ⑤两段式 / 合成知识层 / 问答记忆 / Self-RAG自检。

## 续(2026-06-18 第四段):方案A 已实现 + 实测 + 遗留成本问题
> 接第三段。方案A(claude 问题理解层)落地、测过、commit。

### 改了什么
- **新 `pipeline/retrieve/understand.py`** `understand_query(q)`:claude -p(opus)→ JSON `{en_terms, zh_terms, hyde}`。
  prompt 见文件内 `PROMPT`(展开缩写/中英双语/同义词/HyDE 2-4句论文口吻/没把握别硬编)。
  claude 失败或解析不出 → 返回 None,调用方回退 parse_query(不阻断检索)。
- **`search.py`**:`terms_to_fts(terms)` 把 claude 的干净词切成 (MATCH≥3字短语, instr<3字兜底),
  **关键:不再把词回炉 parse_query**(否则"通用"又被劈)——这是绕开 P-A/P-B 的核心。
  `fts_rank(fts,q,understanding=None)` / `vec_rank(query,k,embed_text=None)` / `hybrid(...,understanding=None)`
  全加形参:有理解层就用干净词喂 FTS + 嵌 **HyDE 文本**(而非光问题);没有就回退原始查询。
- **`ask.py`**:默认对所有查询先 `understand_query`(用户 2026-06-18 拍板"默认全开,先不担心成本");
  加 `--no-understand` 逃生口;`--json` 输出多带 `understanding` 字段(外部 agent 调试用)。
  parse_query 的 P-A/P-B 没去补——它只当 claude 失败时的兜底,正常路径不走它。

### 实测(research-agent 环境,GPU)
- **隔离 FTS 那路 A/B**(`fts_rank` 带/不带 understanding,看命中数):
  `RL` 0→194、`AI ML 的应用` 0→179、`通用工具箱` 22→182 —— P-A/P-B 坐实治好。
- **端到端** `ask.py "RL 在数字人交互里的应用" -n 5`:5 命中全是 rl-digital-human-interaction 主题、relevance 48–96,排序合理。
- **`--no-understand`**:不调 claude(无"理解:"日志),老路 + 向量仍出结果 —— 逃生口/回退健全。
- 理解层产出示例:`RL` → en 含 reinforcement learning / policy gradient / MDP…,zh 含 强化学习/策略梯度/马尔可夫决策过程…,hyde ~100字论文口吻假想答案。

### ⚠️ 遗留成本问题(用户明确"先不担心、但要记下来",待日后用量大再说)
- **每次 deep 查询多 1 次 claude 调用**(几秒 + token)。你自己用无所谓;**外部 agent 出口②若卡住时高频轮询本库,每次都点一炮 claude,会偏重**。
- **当前决定**:默认全开、不加节流/缓存(YAGNI,先观察真实用量)。
- **日后若需优化**(按性价比):① 缓存 understanding(同问题不重算,LRU/落盘);② 给 `--json` agent 路径单独节流/配额;③ 让"明显简单"的查询跳过理解层。**别现在做。**
- 这条也是为何之前(2026-06-16)撤回了全局 `~/.claude/CLAUDE.md` 的出口②指针——ask.py 还在改;理解层是让它够格重新对外开放的前提,但对外开放前要先想清楚这个成本敞口。

### 仍未做(顺位不变)
- 第2步 P2(rerank max_chars=12000 截断长总结尾部)、第3步 P1(`--no-rerank`+`--answer` 必瞎答)。
- 路线图 ④引用图 / ⑤两段式 / 合成层 / 问答记忆 / Self-RAG。
