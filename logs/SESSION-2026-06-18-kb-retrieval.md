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
