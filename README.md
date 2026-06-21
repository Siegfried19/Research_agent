<div align="center">

# 📚 Research Agent · 研究论文流水线

**从一段研究思路，到一座可检索、自核查的中文论文知识库。**
*From a single research idea to a searchable, self-verifying knowledge base of papers.*

[![python](https://img.shields.io/badge/python-3.12-blue.svg)](environment.yml)
[![engine](https://img.shields.io/badge/engine-claude%20%2B%20codex%20(headless)-8A2BE2.svg)](#-为什么走本机-cli--why-headless-cli)
[![storage](https://img.shields.io/badge/storage-SQLite-003B57.svg)](data-base/)
[![status](https://img.shields.io/badge/status-running%20weekly-success.svg)](#-todo--路线图)

</div>

---

## 🌐 English (short version)

Give it a research idea, and Research Agent will:

1. **Discover** papers across multiple scholarly sources (OpenAlex / Semantic Scholar / arXiv / PubMed), plus optional web sources (quality blogs & tech reports).
2. **Score** every hit for *relevance* with a headless Claude — not by citation count, so highly-cited-but-off-topic papers don't float to the top.
3. **Fetch** full-text PDFs through a four-tier fallback ladder (open-access → rule-based → agent hunting → paywall via your library proxy).
4. **Summarize** each paper by having Claude read the PDF directly and write a **structured Chinese summary** (top-3 takeaways + a critical "limitations & my doubts" section), versioned over time.
5. **Verify** every summary with a *different* model (Codex) as a cross-model hallucination check — major issues trigger a full re-summarization from the PDF.
6. **Serve** the corpus through a retrieval layer: a library map for consuming agents, hybrid FTS+vector search, and a citation graph.

Everything runs through local headless CLIs (Claude/Codex on subscription) — **no per-token API cost**. One command runs the whole pipeline:

```bash
python3 pipeline/run.py <topic-id> auto
```

> The rest of this README is in Chinese (the project's working language). The architecture map lives in [`claude-memory/ARCHITECTURE.md`](claude-memory/ARCHITECTURE.md).

---

## 🎯 这个项目是什么

给一段研究思路 → 多源批量搜论文 → 下载全文 → 每篇用 `claude -p` 写**中文**结构化总结 → 存进 SQLite 库 → 换个模型（Codex）再交叉核查一遍。

支持：每周增量跑、总结版本化更新、跨主题比较、库内引用图、付费墙取全文（Tier B）、Telegram 通知、知识库检索（RAG）。

> 用户 = NYU 研究者（中文交流，有学校图书馆订阅，每周跑 1–2 次）。
> 设计哲学、模块边界、数据流接缝全在 [`claude-memory/ARCHITECTURE.md`](claude-memory/ARCHITECTURE.md)。

**当前库存**（随每周跑增长）：3 个主题、约 320 篇资料、约 130 篇已完成中文总结、近 180 个总结版本、约 100 条库内引用边。

---

## 🔭 全貌：一条流水线，五个模块

```
run auto = discover → score → commit → fetch → recover → hunt → tierb → worklist → sum → finalize → verify
           └──────── find ────────┘   └──────────── fetch ─────────────┘   └──── summarize ────┘   verify
                有什么            →            拿到全文              →         读懂写成中文        →   换模型再校
```

| 模块 | 职责（一句话） | 详情 |
|---|---|---|
| 🔍 **find** | 多源召回 → Claude 相关性打分 → 选篇写库 | [`modules/find`](claude-memory/modules-modification/find) |
| 📥 **fetch** | 四级降级取全文（OA → 规则兜底 → agent 猎源 → 付费墙 Tier B） | [`modules/fetch`](claude-memory/modules-modification/fetch) |
| ✍️ **summarize** | Claude 直读 PDF 写中文结构化总结，落盘 + 版本化 + 渲染主题视图 | [`modules/summarize`](claude-memory/modules-modification/summarize) |
| ✅ **verify** | Codex 跨模型核查幻觉（report-only）；major 回 summarize 整篇重做 | [`modules/verify`](claude-memory/modules-modification/verify) |
| 🔎 **retrieve** | 知识库出口（旁路）：库地图 + 消费者 agent 的调查循环；FTS+向量混合检索备用 | [`modules/retrieve`](claude-memory/modules-modification/retrieve) |

模块间靠 **DB 状态机 + 文件产物**解耦（`sources.status`: discovered → source_ready → summarized），不直接互调。唯一例外是 verify→summarize 的整篇重做回路。

---

## 🚀 怎么跑

**全自动一条命令**（打分/总结/核查全走本机 CLI 无头模式，不花 API 钱）：

```bash
python3 pipeline/run.py <topic-id> auto
```

唯一需要人手的地方：tierb 遇 Cloudflare / Duo 验证时会暂停，并通过 Telegram 喊你点一下。

**调试单个阶段**：把 `auto` 换成任一阶段名（`find` / `fetch` / `sum` / `verify` …），幂等，已做的会跳过。

**夜间拆分**（按 token 消耗 + 要不要人值守切两半）：

```bash
python3 pipeline/run.py <id> auto-pull        # 白天有人:discover..tierb..worklist(含付费墙验证),小量 token
python3 pipeline/run.py <id> auto-sum [N]     # 夜间 cron 无人:sum+finalize,token 大户;可选上限 N
python3 pipeline/run.py <id> auto-sum-next [N] # 夜间队列:按 priority 自动挑下一主题,撞限流不中断
# verify 不绑 cron,由全天候守护进程独啃:
python3 pipeline/tools/verify_daemon.py
```

**新建主题**：建 `topics/<id>/topic.json`（`id` / `title` / `idea` / `queries` / `window_years` / `target`，可选 `score_anchors`）。检索词由 Claude 按用户思路生成、先给用户过目。

**测试**：设 `RESEARCH_DB=/tmp/x.sqlite` 用临时库，不碰生产 `data-base/papers.sqlite`。

---

## 🗄️ 数据落点（四类，别混着叫）

| 类别 | 位置 | 存什么 |
|---|---|---|
| **数据库 / 库** | `data-base/*.sqlite` | 可查询的结构化账本——**指针和关系**（谁是谁、在哪、什么状态）|
| **主题状态档** | `topics/<id>/` | 每主题跑流水线的中间产物 + 进度（**单一真相源**）|
| **原件库** | `storage/sources/<slug>/` | 每篇实际正文/原件（`paper.pdf` 或 web 的 `source.md` + `vN.md` 各版本总结 + `verify.json`）|
| **日志** | `logs/` | 机器跑的流水，可删、不入库 |

> 口诀：**数据库存"指针和关系"，主题状态档和原件库存"实际内容"。**

数据库 5 张表：`sources`（全局资料库，主键＝规范化 DOI/URL）、`topics`、`source_topic`（资料×主题，含相关性分+理由+rank）、`summary_versions`、`citations`。

---

## 🧩 为什么走本机 CLI · Why headless CLI

打分、总结、核查全靠本机 `claude -p`（写引擎）+ `codex`（查引擎）无头模式——**两者都走订阅，不花 API 钱**。配合幂等设计，撞限流时重跑对应阶段即可，已完成的自动跳过。

**用 agent 的姿势**（贯穿全局）：尽量让 agent 判断+编排+干活；脚本/管道只管确定性力气活（IO、进程生命周期、锁、校验、入库）；人负责调 prompt、设计流程骨架、把工具箱摆出来。

---

## 📂 目录骨架

```
Research_agent/
├─ pipeline/          ★ 全部代码
│  ├─ run.py          唯一入口/总指挥(run auto 按序 spawn 各段)
│  ├─ ask.py          retrieve 入口/出口公共 API
│  ├─ find/ fetch/ summarize/ verify/ retrieve/   五个模块
│  ├─ tools/          旁路工具(手动跑,不在 run auto):bot,verify_daemon,cross_topic…
│  └─ lib/            共享工具箱:db,sources,quality,store,claude,codex,embed…
├─ data-base/         SQLite 库(papers/fts/vec)
├─ topics/<id>/       主题状态档
├─ storage/sources/   原件库(一篇一个家)
├─ claude-memory/     设计文档(ARCHITECTURE.md + 各模块 README/STATE)
├─ logs/              运行日志
└─ environment.yml    conda research-agent 环境(换机器:conda env create -f environment.yml)
```

运行环境：conda `research-agent`（Python 3.12 + GPU torch/嵌入；入口 `envguard` 自动 re-exec，找不到回退 base / 纯 FTS）。

---

## ✅ TODO · 路线图

> 三层架构，下层喂上层；做任何决策先对齐这个。

### 第 1 层 — 论文自动下载+总结流水线 ✅ 已建成
- [x] 多源发现 + Claude 相关性打分选篇（不靠引用量排序）
- [x] 四级降级取全文（OA → 规则兜底 → agent 猎源 → 付费墙 Tier B）
- [x] Claude 直读 PDF 写中文结构化总结 + 版本化更新
- [x] 硬信号质量四档标记（block/suspect/flag 持久化，每个下游出口都认）
- [x] Codex 跨模型核查幻觉，major 回流整篇重做
- [x] 每周增量跑 + 夜间 cron 拆分（auto-pull / auto-sum / verify daemon）
- [x] Telegram 通知（付费墙验证暂停喊人、夜跑进度）
- [x] web 源接入（优质 blog/技术报告，`kind='web'`）

### 第 2 层 — 相互关联、有方便接口的知识库 🚧 建设中
- [x] SQLite 库 + 库内引用图（主题内边 + 跨主题边重建）
- [x] FTS5 + 向量混合召回索引
- [x] 库地图 `retrieve/map.py`（主题→facet 分组带标记 → `data-base/INDEX.md`）
- [ ] 合成知识层（跨论文综述/对比，按需再上）
- [ ] 引用图扩展 + 可视化

### 第 3 层 — 知识库的三个出口 🚧 推进中
- [x] ① 用户本人查：`ask.py "<问题>" --answer`（带引用中文回答）
- [x] ② 别项目 agent 卡住来查：库经 SSH 挂载 → agent 读本地库地图+原件自调查（[`instruction-for-other-agent.md`](instruction-for-other-agent.md)）
- [ ] ②+ ask.py 完全就绪后，把全局发现机制指针加回 `~/.claude/CLAUDE.md`
- [ ] ③ idea→论文流水线（ARS 桥）：`tools/export_corpus.py` 导 Material-Passport 喂 academic-research-skills —— **终极验收，待与用户一起跑一次真实 idea 全流程**

### 体验 / 运维
- [ ] 检索质量评测（`tools/eval_retrieval.py`）跑出基线数字
- [ ] 换机器迁移文档收尾（远程查看 / cron / Telegram，详见 `claude-memory/operation-maintenance/`）

---

## 📖 更多文档

| 要什么 | 去哪 |
|---|---|
| 整体框架 / 数据模型 / 模块连接 / 总蓝图 | [`claude-memory/ARCHITECTURE.md`](claude-memory/ARCHITECTURE.md) |
| 代码层视角（逐 stage / 目录 / import） | [`pipeline/ARCHITECTURE.md`](pipeline/ARCHITECTURE.md) |
| 某模块设计 / 当前状态 | `claude-memory/modules-modification/<x>/{README,STATE}.md` |
| 运维：cron / 换机器 / 远程 / Telegram | `claude-memory/operation-maintenance/` |
| 改动时间线 | [`claude_log.md`](claude_log.md) |
| 给外部 agent 的调查指南 | [`instruction-for-other-agent.md`](instruction-for-other-agent.md) |

---

<div align="center">
<sub>给 NYU 研究者每周用 · 走订阅不花 API 钱 · 中文优先 · 自核查</sub>
</div>
