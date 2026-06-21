# 整体框架（系统地图）

> 全局的 README——整个系统现状设计与模块如何拼接。**给 AI agent 当地图用**：模块细节都指过去（`modules/<x>/README.md`），本文只画全貌与接缝。
> 流水线的逐 stage / 目录布局 / import 机制另见 `../pipeline/ARCHITECTURE.md`（代码层视角）。

## 1. 这个项目是什么
给一段研究思路 → 多源批量搜论文 → 下载全文 → 每篇用 `claude -p` 写**中文**结构化总结 → 存进 SQLite 库。
支持：每周增量跑、总结版本化更新、跨主题比较、库内引用图、付费墙取全文（Tier B）、Telegram 通知、知识库检索（RAG）。
用户 = NYU 研究者（中文交流，有学校图书馆订阅，每周跑 1–2 次）。

## 2. 流水线全貌
**一条命令跑完全程**，打分/总结/核查走本机 CLI 无头模式（claude/codex 都走订阅，不花 API 钱）：

```
run auto = discover → score → commit → fetch → recover → hunt → tierb → worklist → sum → finalize → verify
           └──── find ────┘   └──────── fetch ────────┘   └──── summarize ────┘   verify
```
归纳成四职能段：**有什么 → 拿到全文 → 读懂写成中文 → 换个模型再校一遍**。`run.py` 是唯一入口/总指挥，把每个 stage 当独立子进程 spawn。

**夜间自动化拆分**（按 token 消耗 + 要不要人切两半）：
- `auto-pull` = discover→…→tierb→worklist：**白天有人手动跑**（tierb 唯一要人点付费墙验证），只花小量 token。
- `auto-sum [N]` = sum→finalize：**夜间 cron 无人值守**，token 大户；队列模式 `auto-sum-next` 按 `topics.priority` 串行挑下一主题、撞限流不中断、幂等续做。
- **verify 已从夜间链摘出**（2026-06-19）：核查不绑 cron，改由**全天候守护进程 `tools/verify_daemon.py`** 单独啃积压——避免 cron 与 daemon 抢同一个 codex 配额窗口。夜间 cron 只 sum+finalize，verify 全天候交给 daemon。

## 3. 五个模块 + 边界（只给地图，详情指过去）
| 模块 | 职责（一句话） | 详情 |
|---|---|---|
| **find** 🔍 | 多源召回 → claude 相关性打分 → 选篇写库（只决定哪些论文进主题，不取全文/不写总结） | `modules/find/README.md` |
| **fetch** 📥 | 四级降级取全文 PDF（OA→规则兜底→agent 猎源→付费墙 Tier B；撞墙就固化新渠道） | `modules/fetch/README.md` |
| **summarize** ✍️ | claude 直读 PDF 写中文结构化总结，落盘 + 注册版本 + 渲染主题视图 | `modules/summarize/README.md` |
| **verify** ✅ | Codex 跨模型核查幻觉（report-only，无否决权）；major 回 summarize 整篇重做 | `modules/verify/README.md` |
| **retrieve** 🔎 | 知识库出口（**旁路，不在主链**）；现行=**库地图 `map.py` + 消费者(agent)拥有调查循环**；旧问答引擎(召回→精挑→回答)已降级为大库备用 | `modules/retrieve/README.md` |
横切子系统 **quality**（硬信号质量四档，非模块）见 `design/quality.md`。

## 4. ★ 模块间连接 / 数据流（接缝）
> 模块间靠 **DB 状态机 + 文件产物**解耦，不直接互调——唯一例外是 verify→summarize 的回路（见下）。

- **find → fetch → summarize 靠 `papers.status` 推进**：
  `discovered`（find commit 入库）→ fetch 取到 PDF 置 `pdf_downloaded` → summarize 写完总结置 `summarized`。
  每段只认上一段留下的 status：fetch 处理 `discovered`、summarize 的 `build_worklist` 只挑 `pdf_downloaded`、verify 只核 `summarized`。中间产物落 `topics/<id>/`（candidates/scores/selected/worklist + verify 状态文件 verified/verify_status/verify_skip）；论文实体落 `storage/papers/<slug>/`（**一篇一个家**：`paper.pdf` + `vN.md` 各版本总结 + `verify.json` 核查详情）。路径由 `lib/store.py` 的 `paper_dir/pdf_file/summary_file/verify_file` 统一构造（2026-06-20 起，原 `store/pdfs` + `storage/papers` 两处分离布局已合并）。
- **verify ↔ summarize 回路（唯一跨段 import）**：verify 判出 **major** → `escalate_verify.py` 调 `from summarize.summarize_auto import resummarize` → **从 PDF 整篇重新总结**出 vN+1（不是打补丁）。核查清单只当"避坑提示"喂进去，重做端**无裁决权**（不许据清单反推原文、不许照搬旧版、不许伪造"已核对"背书）。verify 本身 report-only，只写报告/状态文件。
- **quality 横切三段**：discover/commit 打质量标（block 永不入库；suspect/flag 入库带标记，写 `papers.quality_tier`）→ summarize 见 suspect 切**质疑模式**（批判指令、strength 封顶）→ retrieve **出口认标记**（suspect 降权+⚠️、flag 注"未同行评审"）。设计哲学：**污染不发生在存进去、发生在用的时候忘了它是什么**，所以标记持久化、每个下游出口都认它。
- **retrieve 是旁路出口层（2026-06-21 重构）**：现行设计 = **消费者(一个 agent)拥有调查循环**。库经 SSH 挂载到主力机 → agent 看到的是**本地文件**（不需远程 API）。库这边只交付：①现拼的**库地图** `retrieve/map.py`（读 `papers.sqlite` + `topics/*/verify_status.json` + `topics/*/selected.json`，按 主题→facet 分组带标记 → stdout + `data-base/INDEX.md`，**纯 stdlib、不碰 conda、访问前现拼**）②整齐原件 `storage/sources/` ③调查指南 `instruction-for-other-agent.md`(项目根,对外前门)。agent 读地图→自读总结/原件→得结论；纪律由用户写进记忆。**不写生产库。** 旧问答引擎（`ask.py` 理解→召回→精排→回答 + `db/{fts,vec}.sqlite` 索引）**降级为大库备用工具**，留盘不删。

## 5. 数据模型（data-base/papers.sqlite，5 表）

> **四类数据落点（命名约定，别混着叫，2026-06-21 定）**
> - **数据库 / 库** = `data-base/*.sqlite`（papers/fts/vec）——可查询的结构化账本，存**指针和关系**（谁是谁、在哪、什么状态），很多字段就是指向磁盘文件的路径。
> - **主题状态档** = `topics/<id>/`（topic.json + candidates/selected/worklist/verify 状态 json）——每主题跑流水线的中间产物 + 进度。**它是单一真相源；在这存好的信息不必再复制进数据库**（facet 即一例，2026-06-21 撤回了它的 paper_topic 列，见 claude_log）。
> - **原件库** = `storage/sources/<slug>/`（paper.pdf 或 web 的 source.md + v*.md 总结 + verify.json）——每篇的实际正文/原件（一篇一个家）。
> - **日志** = `logs/`——机器跑的流水，可删、不入库。
> 口诀：**数据库存"指针和关系"，主题状态档和原件库存"实际内容"。**

- **sources**（原名 papers，2026-06-21 改）— 全局论文/资料库：主键 = 规范化 DOI（web 源 = 规范化 URL）；`slug` = 文件夹名（`storage/sources/<slug>/`）；`source_path` = 原文落点（论文 `paper.pdf` / web `source.md`，原名 pdf_path）；`kind` = 类型 `paper`/`web`（入库即定，worklist/检索按它分流）；`status` = discovered/source_ready/source_failed/summarized；`quality_tier`/`quality_signals` = 质量标记。
- **topics** — 研究主题（idea + 生成的 queries + target + 可选 score_anchors）。
- **source_topic**（原名 paper_topic）— 资料×主题（relevance 分 + 理由 + rank；主键 = topic+paper_id）。
- **summary_versions** — 总结版本历史（version/path/based_on/note）。
- **citations** — 库内论文相互引用边（主题内边 commit 建，全库边由 `tools/cross_topic.py` 重建）。

## 6. 代码组织 / 脚本清单
> 完整目录布局 + path shim + 加新脚本规矩见 `../pipeline/ARCHITECTURE.md`，此处只给骨架。

```
pipeline/
├─ run.py        ★唯一入口/总指挥（run auto 按序 spawn 各段，cwd=仓库根）
├─ ask.py        ★retrieve 入口/出口①②公共 API（路径冻结，全局 CLAUDE.md 引它）
├─ find/         🔍 discover, score_auto, commit, discover_web(web源入库 kind='web'), drive(orchestrator)
├─ fetch/        📥 fetch_oa, recover_oa, recover_agent, fetch_tierb
├─ summarize/    ✍️ build_worklist, summarize_auto, register_summaries, render_topic
├─ verify/       ✅ verify_summaries, escalate_verify
├─ retrieve/     🔎 understand, search, rerank, answer, readall, index, freshness
├─ tools/        旁路（手动跑，不在 run auto）：bot, notify, verify_daemon,
│                cross_topic, export_corpus, similar, eval_retrieval, audit_quality,
│                suggest_updates/prepare_update/update_auto/register_updates, init…
└─ lib/          共享工具箱：db, sources, merge, quality, store, slug, http, log, notify,
                 claude（写引擎）, codex（查引擎）, embed（坐标引擎，非 LLM）, envguard, error_classify
```
- **path shim 约定**：段/tools 里每个脚本顶部三行把 `pipeline/` 插进 `sys.path`，使 `from lib.xxx` 在任何子目录解析得到；同段 sibling import 靠 `sys.path[0]`，跨段走包路径（各段有 `__init__.py`）。
- **加新脚本**：进主链 → 放对应段文件夹（没有就新建段+空 `__init__.py`）+ 复制 shim 三行 + 在 `run.py` 的 `steps()`/`AUTO` 注册；旁路 → `tools/`；公共 API/入口 → 根目录（根目录脚本被外部引用，路径不可随意搬）。
- **运行环境**：统一 conda `research-agent`（GPU torch + 嵌入；`environment.yml` 重建）。`run.py`/`ask.py` 顶部 `envguard.ensure_env()` 自动 re-exec 到对环境；找不到不拦着（主链回退 base，retrieve 回退纯 FTS）。

## 6.5 用 agent 的方式（贯穿全局的分工，2026-06-21 用户定为纲领）
**尽量让 agent 来工作；人负责①提供管道和工具 ②调教 prompt ③设计整个 high-level 流程。** 这是本项目用 agent 的基本姿势，设计任何新东西都按它分工：
- **agent** = 判断 + 编排 + 干具体活（看情况自己决定怎么做）。
- **脚本/管道** = 确定性的力气活：IO、进程/Chrome 生命周期、锁、校验、入库出口——**不交给 agent**。
- **人** = 写 prompt 引导、设计流程骨架、把工具箱摆出来。

例（都是这个模式）：`discover_web` 抓取（脚本管 Chrome 起停/独占锁，工具箱 WebFetch/真 Chrome/Read 给 agent 自己挑怎么抓）、find orchestrator（`find/drive.py`）、hunt（`fetch/recover_agent.py`）。
**铁律**：别替 agent 写死它本该自己判断的逻辑（如"静态走 X、动态走 Y"这种硬分支）——摆出工具让它自己挑。

## 7. 🌟 总蓝图（三层 + 三出口）
三层架构，下层喂上层；做任何决策先对齐这个：
1. **论文自动下载+总结流水线**（已建成）：每周 `run auto`——发现→打分→四级取全文→中文总结→质量标记→Codex 核查重做。
2. **相互关联、有方便接口的知识库**（建设中）：SQLite 库 + 引用图 + 检索接口（FTS5 + 向量混合召回已有；合成知识层/引用图扩展按需再上）。
3. **知识库的三个出口（按近→远）**：
   - ① **用户本人查** —— `ask.py "<问题>" --answer`（带引用中文回答）。
   - ② **别项目里的 agent 卡住来查** —— `ask.py --json`（机器可读，给绝对路径自己深读 PDF）。**主用户就是它**；全局发现机制指针待 ask.py 完全就绪后加回 `~/.claude/CLAUDE.md`。
   - ③ **idea→论文流水线（ARS 桥）** —— `tools/export_corpus.py` 导 ARS Material-Passport YAML，喂 academic-research-skills 从 idea 走到论文稿。**还没跑过一次真实 idea 全流程**（终极验收，待与用户一起试）。

---
> 防过期：与近期 `claude_log.md` / 代码冲突时信新的。模块内部细节恕不在此重复，按表中链接下钻。
