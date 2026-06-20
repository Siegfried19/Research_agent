# find — STATE（层积日志）

> 写法：**新在上、老在下、不删**，每条标题带日期+时间戳。最顶一条 = 此刻状态/卡在哪；往下翻 = 历史。
> README.md 是定型设计（覆盖更新）；这里是带细节的过程账（含旧 SESSION 的"为什么"）。
> 局部改动记这里；跨模块/全局改动记 `../../../claude_log.md`，这里只留一行指针。

## 2026-06-20 02:16 EDT · 重构首条（当前状态快照）

> 文档模块化重构建立本日志。以下为当日现状；以后变化在本条**之上**叠新条。

### 现在能跑
- 三步（discover / score / commit）端到端可用，`run auto` 串起。两个老主题（rl-digital-human-interaction 129 篇、rl-general-toolbox 100 篇）就是这条链建的。
- **跨批次校准漂移修法已全部落码 + 三层验证通过**（2026-06-17）：锚点注入 + 证据接地 + batch 20+批内洗牌 + `boundary_rerank` 边界复称 + 冷启动自举（`autopick_anchors`）。实测 claude -p 烟测返回合法 JSON、reason 引原文、分数合理。
  - ⚠️ **这批改动当时记为"未提交/在工作区"**（备份 `/tmp/score_auto.py.bak`）。现 `pipeline/find/score_auto.py` 已是新版且在 git 跟踪下——是否已 commit 入库**待核实**（查 git log）。
- gt/dhi 的 `score_anchors` 已手挑填好（gt=SAC95/泛连续控制DRL45/金星探测8；dhi=物理角色交互96/行人避障DRL46/量子active-learning10），增量复用、不触发自举。
- Codex 魔鬼代言人（`quality.codex_panel`）实现完整但**默认关**（用户 2026-06-10 拍板，异议火力集中总结侧）。

### 已知 bug / 坑
- **`first_run_target` 两处默认不一致**：config.json=200 vs score_auto.py fallback=100。低危（实跑靠 topic.json.target），但该统一。
- **重复入库残留**：`Reinforcement Learning for Robust Parameterized Locomotion Control`（Bipedal Robots）以两个 id 重复入库（slug `..._Bipedal_Robots` 和 `..._2`，两主题各自发现、merge 没合上），待去重。另 `tools/similar.py` 抓出过 2103.14295 重复。

### 未决 / 设计在动（重要）
- **🔶 「找」段大方向暂定改写（2026-06-20，纯设计对齐、未动代码）**：用户发现"一个主题其实是好多组论文（facets）"，现行"一把尺子全局 Top-N"有三病——**小簇饿死**（冷门 facet 被论文多的 facet 挤掉名额）、**一把尺子量五件事**、**丢结构**。
  - 暂定钉死的核心原则：**Claude 智能负责"判断与编排"、现有管道负责"力气与确定性执行"；管道脚本从焊死一条龙变成"我手里的工具"，在每个决策点介入**。这是对 2026-06-09"把 Claude 移出 runtime"的**精修不是推翻**（仅限 find + fetch 两段；summarize/verify 那段继续无人黑箱）。
  - 逐阶段分工：discover=管道召回 / 我拆 facet 定词判够不够；score=管道打分 / 我定 per-facet 尺子 + 配额 + 看边界；commit=管道写库 / **我定稿，增量新篇直接 commit、事后 Telegram 回报**（用户"信我判断"，不每篇等点头）。
  - facet 配额倾向"保底 M 篇 + 剩余全局按分填"（治饿死又不过度限制富矿），facet=1 时优雅退化成现状。
  - **未落地、刻意推迟**：文件保存架构（topic.json 升级成"装得下判断的存档"：facets+命中标准+取舍偏好+score_anchors+覆盖状态+拐弯种子）用户说"后面整体改一遍再定"；"叫醒后的编排逻辑"同。当前 topic.json 仍是旧形态。
- **召回漏洞教训（2026-06-19，新主题 agentic-knowledge-synthesis 首轮废弃）**：`prefilter_rank` 纯词法取前 N，把领域奠基作（GraphRAG/RAPTOR/PaperQA2 等）切掉 → 召回不足 + 生物医学 bleed。该主题已删首轮全部产物（生产库未触碰，commit 没跑），topic.json 保留待"补 ~7 条精准检索词 +（可选）按 id 播种原语 → 重搜 → commit"。**这是上面"facet 改写"的现实触发器之一**。

### 上次卡在哪 / 下一步
- find 段代码本身稳定可跑；**真正在动的是设计层**：等用户定"存档（升级版 topic.json）长什么样" + "叫醒编排逻辑"，再落 facet 配额 / per-facet 打分 / 按 id 播种 / 增量召回编排。
- 小活：① 核实 score 漂移修法是否已 git commit；② 统一 first_run_target 默认；③ Bipedal Robots 去重；④ agentic-knowledge-synthesis 补检索词重搜。

---

## 2026-06-19 · 新主题 agentic-knowledge-synthesis 设计 + 首轮搜索（已废弃重来）

> 缘由：讨论"知识库该怎么被 agent 消费、能否发现跨论文关联"时，意识到这本身是个值得做的研究主题，决定用本项目自己的流水线攒这方面语料（dogfooding：用论文库研究"论文库该怎么用"）。本会话**只到搜索一轮、未入生产库**；首轮因召回不佳被叫停并删除，主题定义保留待重搜。

**主题怎么来的（讨论脉络）**：从"问答层五方案"（`claude-memory/Prompt-structure-design/qa-layer-design.md` §10）聊到——⑤合成层/金字塔在**质量**上并不更准（GraphRAG C0≈TS 平手、赢成本）；而**"跨论文综合/关联发现"恰是领域里最没被解决的格子**（单篇 QA 已被 PaperQA2 打穿，但"把多篇想到一起产生新论断"没有架构稳定赢）。用户由此提出：这是真空里的研究点。

**主题定稿（边界）**：
- id=`agentic-knowledge-synthesis`；标题=Agent 消费知识库与跨论文综合（长上下文时代）。
- **三个内置前提**（区别于泛 RAG 研究）：①长上下文是给定条件（Opus 时代，"几十篇直读进去综合"可行，不预设激进检索；翻转了 lost-in-the-middle 等多在弱模型上测的旧证据）；②消费方=agent 为主、人为次（agent 要机器可读/可追溯，人要可解释可信）；③已有库内引用图资产（`citations` 表，跨论文关联不是从零）。
- **收（脊柱→外围）**：⭐跨论文综合+关联发现（综述生成、矛盾/共识、LBD 假设生成、**"如何构建跨论文关系结构"的方法学**——引用图之外更好的结构，用户特别点名要去论文里找答案）；agent 主动求知（检索/工具增强、何时检索、结果接回任务）；长上下文 vs 检索（强模型档，只收与综合相关的）；库上科学问答（agent+人 双消费、可追溯）。
- **不收**：通用 RAG 工程 / 向量库调优 / 切块·embedding 选型；纯单篇 QA；通用 agent 记忆 / 通用 KG 构建。
- **配置**：`window_years=3`（2023 起）、`target=35` 起步、`score_anchors` 不手填（冷启动自举）。
- **关键澄清**：跨论文**综合**不砍（它是脊柱），砍的只是"通用 RAG 工程"；且"该用什么跨论文关系结构（引用图偏薄：稀疏+引用≠思想关联；语义相似图/概念图/论断关系图更厚）"本身列为一个检索侧面，让语料用论文证据反哺我们怎么建，不拍脑袋。

**首轮搜索 + 为什么废弃（重要教训）**：
- 跑了 discover（raw 3003 → 去重 2135 → **池只取 70**；有摘要 49；偏新）+ score（冷启动自举）。脊柱覆盖到了：Literature Meets Data(95)、LBD(80)、Lost in the Middle(78)、RAG-or-Long-Context(75)、Unifying LLMs+KGs(65)、Agentic RAG Survey(58) 都落顶。
- **❌ 病① 召回漏洞（致命，叫停主因）**：discover 的 `prefilter_rank` **纯词法**按各源排位取 `papers[:70]`，不认领域奠基作 → 我们自己 evidence 文档钦定的 **GraphRAG / RAPTOR / PaperQA2 / OpenScholar / Chain-of-Agents / MAST 一篇都没进池**（它们在 2135 里但被 70 这刀切了）。这几篇恰是"跨论文综合结构"最核心的（RAPTOR/GraphRAG=合成层原始论文）。
- **❌ 病② 生物医学 bleed（中度）**：`literature-based discovery` / `knowledge graph from scientific papers` 本是生物医学术语，pubmed 灌回大量临床文献（FoodAtlas 82、PubMed KG 60、medical QA 一堆）——方法沾边、领域跑偏。
- **用户决定**：删掉这轮全部产物、先把讨论入库，补搜方案下次再拍。

**下次接着做（待办）**：
1. **补召回再重搜**（commit 前必做）：(a) 加 ~7 条精准检索词把奠基作捞进各自 query 前排（graph-based RAG / query-focused summarization → GraphRAG；recursive abstractive tree retrieval → RAPTOR；language agents superhuman synthesis → PaperQA2/OpenScholar；self-reflective RAG → Self-RAG；multi-agent LLM failure modes → MAST 等）；(b) **可选**建"按 DOI/arXiv id 点名播种入池"小原语（保证 evidence 文档那 8 篇钻石必进；且是 add_url/搁置 add_paper 的同一块地基，一鱼三吃）。`sources` 目前缺"按 id 单查元数据"，需补。
2. 重跑 discover→score→看分布→commit（commit 截断时连同打分理由收紧生物医学 bleed）。
3. 建 `add_url.py` + 策展博客清单（详见下"副轨"）。
4. **教训**：discover 的 70 池上限对"已知有奠基作"的主题召回不足——纯词法排位会切掉低词频高地位的经典。对这类主题应先播种已知必备，或加精准 query。

**副轨：非论文内容（博客/技术报告）—— `add_url` 工具（计划，未建）** ⚠️ 偏 fetch/ingest 段，记在此处仅因与本主题重搜捆绑：
- **发现**：agent/长上下文/agentic RAG 这摊，最前沿一大半不在 arXiv，在 Anthropic/OpenAI research blog、Lilian Weng、FutureHouse、distill 等。只搜 arXiv 会系统性漏半个领域。
- **决定**：暂时方案 A——工具我（Claude）建、博客我策展（锁 2024–2026）。
- **`tools/add_url.py` 实现计划（已与用户过，待拍 3 决定后建）**：①`lib.http` 拉 HTML → 抽正文为 markdown（抽取器待定：推荐 trafilatura 进 conda 超集，主链仍只 requests）→ 存 `store/web/<slug>.md`，路径写 `papers.text_path`；②**关键利好**：papers 表本就有 `text_path` 字段、新版 summarize 把文件路径喂 claude 让它直接 Read（不止认 PDF）→ 博客不用伪造 PDF、不用改表结构，直接走现有 sum→verify；③身份/去重：`id=规范化URL`（剥 utm/fragment），按 URL+标题归一判重，无 DOI 没关系（papers.id 是 TEXT 主键）；④质量档：新建 `config/quality/url_allowlist.txt`（域名白名单），命中→trusted、否则→flag「非同行评审网络来源」；⑤入库+关联：upsert papers(status=pdf_downloaded, text_path)、paper_topic 强制入选。
- **待拍 3 决定**：①抽取器(trafilatura vs BS4)；②质量档命名(复用 trusted+signal 标 web-authoritative vs 独立新档)；③手挑博客是否跳过相关性/质量闸强制入选。

**状态**：主题定义 `topics/agentic-knowledge-synthesis/topic.json` 保留（已清掉自举锚点，待重搜）；首轮 candidates.json/scores/两 .out 日志已删；**生产库未被触碰**（该主题 topics/paper_topic 均 0 行）。

---

## 2026-06-17 · 打分跨批次校准漂移：调研 → 落码 → 自举（实现会话）

> 接同日"分析出方案"会话（见下条）。本会话：deep-research 调研 → 落码核心修法 + 全自动自举，全程在工作区（**未提交**），未碰生产库。配套：`claude-memory/Prompt-structure-design/score-drift-research-findings.md`（调研+方案+落码状态，最全）。

**做了什么（时间线）**：
1. **外部调研**（deep-research，22 源 / 100 claim→25 核查→19 确认）。要点：漂移学名=**rubric execution drift**（RULERS 2601.08654）；缓解三件套=锁死固定 rubric（含 score anchors）+ 证据接地 + 截断线事后校准。**保留 0-100 pointwise 是对的**（"Likert or Not" 2505.19334：大有序刻度让 pointwise≈listwise；换 pairwise 在边界反放大 style 噪声 2504.14716）。边界复称用**批量自一致+取分数分布均值**（2505.12570 / 2503.03064）。**z-norm 禁令被佐证**；**打分步不该上 reranker**（reranker 属粗筛门/检索层，打分步被 ≤500 cap 锁死、scale-proof）。
2. **逐项落码到 `score_auto.py`**（原版备份 `/tmp/score_auto.py.bak`）：
   - ② rubric 通用骨架（替掉**写死在 digital-human 主题**的旧例子——潜在 bug）+ `topic.json.score_anchors` 注入每批固定头部 + 证据接地（reason 须引原文片段）。
   - ① batch 默认 10→20 + 批内按 `Random(start)` 洗牌（幂等）对冲位置偏置。
   - ④ `boundary_rerank`：去留线 ±8 分窄带 → 同一次调用 ×5 采样取均值 → 写 `scores/zz_boundary.json`，靠文件名排序让 commit 的 sorted-glob 合并自动覆盖（**commit.py 没动**）。开 DB 认首跑（去留线=第 target 名截断线）/增量（去留线=资格闸 rel≥30·flag_min，已入库篇跳过）。
3. **全自动自举**（用户拍板"没必要我介入"）：`score_auto.main()` 发现 topic.json 无 score_anchors 时——裸跑整遍 → `autopick_anchors` 从**整遍分布**挑高/边界/低 3 张写回 topic.json（非阻塞推 TG）→ 带锚重打。冻好后增量复用、不再自举。**关键设计**：标尺取自"整遍"而非"第一批"——候选池预排序，第一批全高相关、给不出低/边界样本。
4. **gt/dhi 锚点手填**（已有打分库，手挑比自动准；已推 TG 供审）：gt=SAC 95 / 泛连续控制 DRL 45 / 金星探测（"exploration"误撞）8；dhi=物理角色×场景交互 96 / 行人密集避障 DRL 46 / 量子 active-learning（"agents"误撞）10。
5. **删掉人工工具**（用户要求）：原建的 `pipeline/tools/pick_anchors.py` 已删——自举全自动，想改锚点直接编辑 topic.json 重跑 score 即可。引用都清理干净。

**本会话定的决定**：范围=**(a) 只保截断线去留正确**（内部 rank stakes 低 + 下游评分/核查兜底）；锚点=3 张真论文（高~95/边界~45/低~10，偏经典不易过时）；④ band=±8 / k=5（默认可调）；冷启动=**全自动自举两遍**（裸跑→挑→重打），人工降为"直接改 topic.json"。

**改动文件（均未提交，工作区）**：`pipeline/stages/score_auto.py`（漂移修法 ②①④ + 自举 + autopick_anchors）；`topics/{rl-general-toolbox,rl-digital-human-interaction}/topic.json`（加 score_anchors）；`claude-memory/Prompt-structure-design/score-drift-research-findings.md`（新建）；`CLAUDE.md`（topic.json 字段 + 漂移修法节 + 工具表）；`pipeline/tools/pick_anchors.py`（建后又删，净增 0）。

**验证到哪**：编译 ✓；隔离逻辑 ✓（prompt 注入 / anchor_block / 洗牌确定性 / boundary cutoff·band·取均值·zz 覆盖 / 首跑·增量两路）；真实 claude -p 单批烟测 ✓（合法 JSON、reason 真引原文、分 15/56/92）；自举两遍流程 stub 测 ✓。**还没做**：临时库（`RESEARCH_DB=/tmp`）完整端到端（discover→score 带自举→commit，确认 zz_boundary 真被合并覆盖、自举真写 topic.json）。

**下一步（待用户定）**：a) 跑临时库端到端验证；b) 提交这批改动；c) 暂停。增量跑 ④ 的 band/采样次数若实跑后想调，在 `boundary_rerank` 默认参数处改。

---

## 2026-06-17 · 打分「跨批次校准漂移」问题定位 + 修法方案（分析会话）

> 目标：定位并准备修复 `score_auto` 逐批独立打分带来的**跨批次校准漂移**。本会话只做**分析+出方案+落 log**，**未碰任何 pipeline 代码、未动生产库**。（同日另有实现会话，见上条。）

**怎么聊到这里（上下文链）**：
1. 先确认架构判断：**改库层包含知识库全部内容，但不含"检索这种访问模式"**——改库层的读全是 lookup（按主键/状态/外键取已知行），`ask.py` 是 retrieval（自然语言问题找未知 ID 的最相关篇）。分界是 **lookup vs retrieval**，不是"写 vs 读"。
2. 讨论"打分要不要像 summary 那样加 verify→correct 闭环"。**结论：不要照搬**——summary 值得是因为它(a)是终端产品(b)有 PDF 当 ground truth 可收敛(c)错误静默+终端；打分三条全不占（是闸门、相关性无客观正解、错误多可见可恢复）。现有 Codex 魔鬼代言人默认关，是对的。
3. 纯从**错误形态**看打分：**几乎所有出错收敛成"论文拿 relevance=0/偏低 → 被静默丢"，系统结构性偏向假阴性**；唯一"放垃圾进来"的是模型真把跑题论文打高分（可见、会被下游 verify/topic.md 撞到）。**唯独"跨批次校准漂移"是召回冗余兜不住的**——多 query 能补回被漏的论文，补不回被打歪的分 → 用户拍板：这个要解决。

**`discover → score → commit` 流程速记**：
- **discover.py**：4 源（OpenAlex/SemanticScholar/arXiv/PubMed）×多 query 捞 → `merge_all` 去重（规范化 DOI 主键，记 relRankBySource/sources）→ 硬信号质量闸（block 当场丢，suspect 带标记入池）→ `prefilter_rank`（**召回导向：各源最好名次+多源加成，故意不用引用量**）→ 截 `pool_size=min(500,max(target*2,60))` → 写 candidates.json。**不写库。**
- **score_auto.py**：候选池切批（默认 10），**并发 4** 个 `claude -p`；每批 prompt=idea+该批 title/venue/abstract，按 0-100 打 relevance + edge_insight 布尔；强制纯 JSON → `scores/batch_<start>.json`。幂等（开跑清空 scores/）；可选 Codex 魔鬼代言人（默认关）。
- **commit.py**：合分 → 选篇闸（block 双保险丢 / rel<30 且非 edge 丢 / flag·suspect 需 rel≥flag_min(45) / Codex 异议合议:边界分<60+异议=挡）→ 选篇（首跑 eligible[:target]；增量只追新、cap=target*3）→ 写 papers+paper_topic → **全主题按 relevance DESC, citation DESC 重算 rank** → 建主题内引用边 → 落 selected.json。

**问题：跨批次校准漂移**：
- **病因**：每批是独立 `claude -p`，批间无共享参照系。现状已被 prompt 里带绝对锚点的 rubric 压成"几分校准噪声"，但几分噪声落在**截断线附近**就翻转去留、打乱 rank。
- **为什么必须单独治**：召回冗余能补"被漏的论文"，**补不回"分被打歪的论文"**——漂移动的是相对次序+截断线，冗余对它无效。
- **⚠️ 陷阱（务必避开）**：**绝不能做"逐批 z-score 归一化"**。池子被 `prefilter_rank` 预排序过，靠前的批本就更相关；逐批统计归一化假设各批分布相同，会把"批0确实比批20相关"的真信号抹平，越治越糟。**任何按批做统计标准化的方案在这条流水线上都是错的。**

**修法方案（核心洞察：校准只需在"会改变决策"处紧——95 分和 10 分不需要跨批校准，只有截断线附近窄带需要）**，三步按性价比叠加：① **加大批量**（10→25~30，批内自归一化，接缝数降~3×，context 吃得下）；② **共享锚点**（每批塞同一组已定分参照论文如 3 篇铁定 95/50/15，把所有接缝钉到同一把标尺）；③ **边界重排一遍**（首跑后取 target 截断线 ±N 分窄带，在一次调用里一起重打，绕开 z-norm 陷阱）。建议 ①+② 先上（便宜预防）、③ 作真正校正层。

**待拍决定**：①范围（只保截断线去留正确 vs 连选中集内部 rank 次序也稳）；②batch_size 调多少；③锚点真论文 vs 描述型、怎么挑存哪；④③ 的 ±N 带宽、是否也用于增量跑。（次日实现会话已逐一定，见上条。）
