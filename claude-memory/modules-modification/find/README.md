# find — 发现 + 打分 + 入库

> 流水线第 1 段（discover → score → commit）。把"一段研究思路 + 检索词"变成"入库的 source_topic 关联 + 选篇清单"，**只决定哪些论文进这个主题，不取全文、不写总结**。
> 代码：`pipeline/find/{discover,score_auto,commit}.py`。质量闸调横切子系统 `lib/quality`（设计见 `../../design/quality.md`）。

## 边界（这段管什么 / 不管什么）
- 管：多源召回 → claude -p 相关性打分 → 选篇写库（sources / source_topic / citations 表）。产物：`topics/<id>/{candidates.json, scores/, selected.json}` + DB 行。
- 不管：取 PDF（→ fetch 段）、写总结（→ summarize 段）、核查（→ verify 段）。
- 入口：`run.py <id> {discover,score,commit}`，或 `run auto` 串起。

## 三步与关键脚本
1. **discover.py**（`topic.json` → `candidates.json`，**不写库**）：四源并发召回（OpenAlex / Semantic Scholar / arXiv / PubMed，按 `config.sources` 开关）→ `merge_all` 去重 → 语言过滤 → **block 级质量直接丢弃**（撤稿/水刊，不浪费打分 token，suspect 入池带标记）→ `prefilter_rank` 召回向预排序 → 截池 `pool_size = min(500, max(target*2, 60))`。
2. **score_auto.py**（`candidates.json` → `scores/batch_*.json`）：逐批 `claude -p` 打 0–100 相关分。核心是**跨批次校准漂移修法**（见下）。可选 Codex 魔鬼代言人（`quality.codex_panel`，默认关）。
3. **commit.py**（`scores/` + `candidates.json` → DB + `selected.json`）：合并分数 → 过质量闸 + 相关性门槛 → 选篇 → upsert sources/source_topic → 重算全主题 rank → 重建主题内引用边。

> **web 源旁路（2026-06-21）**：非论文的优质 blog/技术报告走 `discover_web.py`（agent 联网搜 → prompt 软判①相关性②内容质量 → 抓正文：**工具箱交给 agent 自己挑**——静态页 WebFetch / 动态·X·登录墙用真 Chrome（opencli `open`+`screenshot`，再 Read 截图）/ `extract` 抓 DOM → `upsert_paper(kind='web')`+`set_paper_topic`）。套**同一入库出口**、URL 规范化去重、跳过打分、不进总结（worklist 排除 `kind='web'`）。Chrome 起停/锁归脚本（复用 fetch_tierb），起不来降级纯静态。opt-in：`run.py <id> web`。详见 STATE（2026-06-21 条）。

## 设计原则与关键决策（为什么这么做）
- **选篇靠 LLM 相关性打分，不靠 API 排序**：OpenAlex 等的相关性把引用量混进去，会把"高引但跑题"的经典论文顶上来。`prefilter_rank` 只用各源名次 + 多源一致加成、**故意不用引用数**，且只是召回向粗筛（决定谁进 ≤500 池），真正去留由 LLM 打分决定。
- **打分步是 scale-proof 的**：工作量取决于"每次喂 LLM 多少篇"（池硬截 ≤500，每周增量实际几十篇），与库总篇数无关。所以漂移修法是打分步终局方案，**打分里永不需要 reranker**（reranker 真要上，落点是上游粗筛门或检索层，不在这段）。
- **跨批次校准漂移修法**（治"每批独立 claude -p 让'几分算相关'逐批微漂、落截断线附近翻转去留"，学名 rubric execution drift；调研详见 `../../design/`/`../../score-drift-research-findings.md`）。四个零件：
  - **锚点钉刻度（头号主力）**：`topic.json.score_anchors`（3 张已定分参照样本：高~95 / 边界~45 / 低~10）渲染成固定头部，**每批 prompt 一字不差地带**，把所有批对齐到同一把标尺。rubric 档位用主题无关的 `GENERIC_BANDS`（替掉旧的写死在 digital-human 的例子）。
  - **证据接地**：`reason` 必须引用 title/abstract 原文片段，禁泛泛而谈。
  - **批量 + 批内洗牌**：batch 默认 20（减接缝），`Random(start)` 洗牌对冲位置偏置（幂等可复现）。
  - **边界复称** `boundary_rerank`：对去留决策线 ±8 分窄带，塞进同一次调用 × 5 次采样**取均值**复称，写 `scores/zz_boundary.json`——文件名排在 `batch_*.json` 之后，commit 的 sorted-glob 合并时按 id 覆盖（**故 commit.py 无需改动**）。
- **冷启动全自动自举**：无 `score_anchors` 时，score 自动**裸跑整遍 → 从整遍分布挑高/边界/低 3 张写回 topic.json（`autopick_anchors`，非阻塞推 Telegram）→ 带锚重打**。标尺取自整遍而非第一批（候选池预排序，第一批全高相关，给不出低/边界样本）。冻好后增量复用、不再自举。想改：编辑 topic.json 的 `score_anchors` 后重跑 score。
- **质量"标记优先、出口认标记"**（详见 design/quality.md）：commit 不是简单丢弃——block 永不入库；flag（预印本/无 venue）和 suspect（掠夺名单命中）**入库但带标记**，需 `relevance >= flag_min_relevance`（默认 45，`edge_insight` 可豁免）；其余需 `relevance >= 30 或 edge_insight`。
- **首跑 vs 增量**：首跑选 `eligible[:target]`；增量只挑新篇 `fresh[:target*3]`（cap 极少触顶），已入库篇去留已定。**commit 对全主题重算 rank**（增量追加后名次重排），引用边只建主题内的（全库边由 `tools/cross_topic.py` 重建）。
- **Codex 评审团无否决权**（panel 默认关，用户拍板异议火力集中总结侧）：开启时只提异议——边界分（<60）+ 异议 = 挡下；高分 + 异议 = 入库但把异议记进理由。

## 重要的坑
- **`first_run_target` 默认值不一致（待核实）**：`pipeline/config.json` = 200，但 `score_auto.py` 取不到时回退 `100`。实际跑都靠 `topic.json.target`（dhi/gt 用的 129/100），fallback 罕用，但两处不一致。
- **边界复称只在有明确去留线时有效**：增量跑去留线 = 资格闸（rel≥30 / flag_min），首跑 = 第 target 名截断线；边界带 < 2 篇会 SKIP。
- **撞 Max 限流**：score 幂等（已打分的批跳过），重跑该阶段即可；并发太高就调小 `score_auto.py <id> <batchSize> <concurrency>`（默认 20/4）。
- **gt/dhi 锚点是手挑的**（比自动准），不会触发自举；改这俩主题的标尺要直接编 topic.json。
