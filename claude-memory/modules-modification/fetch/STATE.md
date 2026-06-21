# fetch — STATE（层积日志）

> 写法：**新在上、老在下、不删**，每条标题带日期+时间戳。最顶一条 = 此刻状态/卡在哪；往下翻 = 历史。
> README.md 是定型设计（覆盖更新）；这里是带细节的过程账。
> 局部改动记这里；跨模块/全局改动记 `../../../claude_log.md`，这里只留一行指针。

## 2026-06-21 03:18 EDT · 指针：拉取改版后全链接口对齐（跨模块，详见 claude_log）
- 大改名(papers→sources / pdf_path→source_path / 状态 pdf_*→source_*)+ 新增 `kind`(paper/web) 已传导完整,实时链零旧名残留、生产库已迁、py_compile 过。**新增 web 源排除谓词** `(kind IS NULL OR kind!='web')` 之前只在 build_worklist,本轮补到 `run.py:topic_progress`(夜间队列大脑,漏了会卡死队列)+`register_summaries`。详见 `../../../claude_log.md`(03:18 条),summarize STATE 同留指针。

## 2026-06-21 01:11 EDT · 撤回 facet 入库（改回主题状态档单一真相源）
- 接下一条（00:39）：facet **不再入库**。用户拍板"信息在主题状态档存好就够，别复制进数据库；数据库他自己主导"。`db.py` 的 facet 列 / `store.py` 的写入 / 生产库 267 行全撤；`ALTER TABLE paper_topic DROP COLUMN facet`（备份 `/tmp/papers.bak-before-facet-drop.sqlite`）。`failed` 子命令保留不动。命名+原则详见 `../../../claude_log.md`（01:11 条）、`ARCHITECTURE.md` §5（四类数据：数据库/主题状态档/原件库/日志）。

## 2026-06-21 00:39 EDT · fetch 失败兜底定稿落地：`failed` 报失败 + facet 入库（跨模块）

> 与用户逐步敲定 fetch 失败处理并落码。**结论：fetch 几乎不失败（生产库当前 `pdf_failed=0`，历史仅 PPG/Lazy Agents 那 1 次已修），不值当建诊断/分类 agent。** 砍掉早先设想的"diagnose 失败分类层"，只留两件极小的事 + 为 retrieve 备料的 facet 入库。

**做了什么（代码）：**
- **⑤ 报失败** — `run.py` 加 `failed` 子命令（`report_failed(tid)`）：一句 SQL 查本主题 `pdf_path IS NULL AND status IN ('pdf_failed','discovered')`，打印 `标题/id/slug/DOI/落地页`。**只报"是哪篇"**，失败类型不展示不入库（需要时处理的 agent 临场判）。全拿到则输出 `✅`，平时零噪音。实测：agentic（38 篇无全文）正确列出、rl-general-toolbox 输出 ✅。
- **⑥ 手动挂回库** — **不写工具**（用户决定）。失败篇的 `papers`/`paper_topic` 行 find 阶段已 commit，挂载=拷 PDF 到 `storage/papers/<slug>/paper.pdf` + `UPDATE status='pdf_downloaded'`（即 `fetch_oa.py` 末尾三行）。需要时叫 agent 现场用 SQL 办。
- **facet 入库**（跨 find/retrieve，用户："先加进来，可能和后面查询有关"）：`paper_topic` 加 `facet TEXT`（经 `lib/db.py` 的 `ADD_COLUMNS` 自动迁移，无需手敲 ALTER）；`lib/store.py:set_paper_topic` 从 `p.get('facet') or '_all'` 落盘 + ON CONFLICT 更新；`commit.py` 调用处无需改（传的 `p` 本就带 discover 打的 facet）。**回填**：agentic 38 行从 `candidates.json`（77 候选全带 facet、orchestrator 修正过）回填、全 38 匹配；两个老非-faceted 主题 229 行归一 `_all`。**全库 267 行无 NULL facet**。

**红线（沿用）**：不接盗版源；付费墙只走 NYU 合法订阅；orchestrator 永不直接开浏览器（Chrome 生命周期锁死 tierb 内）。

**验证**：py_compile（db/store/run）过；临时库端到端（facet 写入 / 缺省 `_all` / ON CONFLICT 更新）过；`failed` 双场景实测过。**未 push（待用户）。** 跨模块账见 `../../../claude_log.md`（00:39 条），find/retrieve STATE 各留指针。

## 2026-06-20 04:19 EDT · 指针：存储布局改版（跨模块，详见 claude_log）
- PDF 落点 `store/pdfs/<slug>.pdf` → `store/papers/<slug>/paper.pdf`（一篇一个家）。fetch_oa/recover_oa/recover_agent/fetch_tierb 已改走 `lib/store.py:pdf_file(slug)` 统一出口，不再用 `config.paths.pdfs`/`PDF_DIR`。全局账见 `../../../claude_log.md`（04:19 条）。

## 2026-06-20 02:16 EDT · 重构首条（当前状态快照）

> 文档模块化重构建立本日志。以下为当日现状；以后变化在本条**之上**叠新条。

### 能跑的
- 四级链 OA → recover_oa → hunt → tierb 全部已实测可用，在 `run auto` / `auto-pull` 链上（tierb 在 `auto-pull` 末段，要人点验证，白天手动跑）。
- recover_oa 的四渠道（arXiv-id 枚举 / Unpaywall repository优先 / arXiv-title / dblp-oa）+ hunt 的张冠李戴防线均有误伤测试或 e2e 实跑过。
- 两个生产主题（rl-digital-human-interaction / rl-general-toolbox）当前**无积压 pdf_failed**——下载链对这两主题已跑通。

### 上次卡在哪 / 已知待办
- ⚠️ **fetch_tierb 在 Python 形态下未做端到端实跑验证**（自 2026-06-09 迁 Python 起就挂着）：各零件（ensure_chrome/find_pdf_url/混合B+A/校验/Chrome生命周期）都手动验证过，但**整篇付费墙抓取没在 Python 版完整跑过一次**——前两主题恰好已无付费墙待抓篇。**下个有付费墙的主题要盯一次完整 tierb 跑**（重点：findPdfUrl 跨出版商、challenge 检测、混合 B/A）。
- **远程看屏（手机过验证）已封存**（MOTHBALLED 2026-06-10，用户觉得有风险）：代码保留、默认关，除非 `config tier_b.remote_view=true` 或 `RESEARCH_REMOTE_VIEW=1`。日后若解封要先解决：①手机端双指缩放放不大（noVNC 1.4.0）；②用户安全顾虑。验证只能远程看屏点机器那台 Chrome（cf_clearance 绑指纹+IP），不能手机本地解。运维细节见 `../../ops/remote-access.md`。

### 已知 bug / 数据问题
- **Bipedal Robots 重复入库**（`Reinforcement_Learning_for_Robust_Parameterized_Locomotion_Control...`）：以两个 id 落库（slug `..._Bipedal_Robots` 和 `..._2`），两主题各自发现、merge 没合上，**待去重**。

### 方向性变化（设计层，可能影响本模块跑法）
- **2026-06-20 暂定（未落代码）**：「找」+「取PDF」两段拟改"Claude 智能监督 + 现有管道执行"。对 fetch 的影响：**fetch/recover 仍纯执行（我只看漏斗），hunt 本就 agentic 归 Claude，tierb 由 Claude 定哪些值得走、验证关卡仍要人点**。脚本不变，只是从"焊死一条龙"变成"决策点可介入"。文件保存架构待用户整体定后再动。(待核实——纯设计对齐，尚无代码改动)

### 手动加 PDF 旁路（待办，搁置 2026-06-18）
用户常自己找到论文、直接给 PDF。计划做 `tools/add_paper.py <主题id> 论文.pdf...`：识别身份（pdftotext 抠 DOI/arXiv → OpenAlex 标题模糊配 → 裸入库）→ 规范化 DOI 去重 → 跳过整条下载链直接落库跑 sum。**最大好处=有全文，跳过 fetch/recover/hunt/tierb。** 三个待拍决定（相关性分强制入选 / 标题匹配要不要停下确认 / 纯无id退化路径）见旧 CLAUDE.md 末节。

---

## 2026-06-10 · 救回失败篇 + 下载链三级→四级 + tierb Chrome 生命周期根治
（迁自 `logs/SESSION-2026-06-10-recover-rag.md` 的 recover/取全文部分；该 SESSION 同时含 RAG①(ask.py) 内容，属 retrieve 模块，未迁。）

### 救回 topic2 最后 2 篇 pdf_failed → 100/100
- PPG Reloaded / Lazy Agents，昨晚结论"无免费版"是错的：都是 ICML 2023，PMLR 官网免费。
- **根因**：当时的 recover 渠道（Unpaywall 要 DOI + arXiv 反查）覆盖不到 PMLR 这类**会议自营 OA 站**。
- 临时手动拉 PDF→pdftotext→落库，走标准 worklist→sum→finalize 补总结；并由此固化两层新兜底（下面两条）。

### 由此固化两层新兜底（下载链三级→四级，均已实测）
- **dblp-oa 渠道**（加进 `recover_oa.py`）：DBLP 标题反查（**全等才认**）→ 若 ee 落在 PMLR / ACL Anthology / OpenReview 就构造 PDF 直链。误伤测试：不存在的标题、ee 在别处的论文，均正确返回 None。
- **新阶段 hunt**（`recover_agent.py`，**插在 recover 与 tierb 之间**）：规则渠道全空的论文，无头 `claude -p` 开 WebSearch/WebFetch 联网找合法免费 PDF（prompt **明令禁盗版源**）；agent **只给链接**，下载 / %PDF 校验 / 落库全由脚本做。临时库 e2e：agent 自己搜到 PMLR、10MB 下载校验入库通过。
- 配套：`lib/claude.py` 的 `run_claude` 加 `tools` 参数（透传 `--allowedTools`）。

### tierb Chrome"越开越多"根治（照 Stock_agent 补齐缺的后半截）
- **病根**：fetch_tierb 当初只抄了 `ensure_chrome`（启动），**没有关闭逻辑**。
- **修法**：跑前 flock 独占（锁=`<UDD>/scrape.lock`，共用同一实例的任务天然同一把锁）→ finally **无条件** `pkill -f "user-data-dir=<UDD>"` 整关（独立目录绝不误伤日常 Chrome；复用来的残留也一并关）。
- **副产物**：每次都 fresh launch → PDF 下载 pref 必生效 → 方法 B 始终可用。
- **当时残余风险**：Stock_agent 的锁还在它项目本地，两项目极端撞车时 tierb 收尾会关掉它在用的实例。（注：此隐患后于 2026-06-17 用独立 user-data-dir 消除，见首条/README。）

### 顺带发现
- **Bipedal Robots 以两个 id 重复入库**（`..._Bipedal_Robots` / `..._2`，跨主题 merge 没合上），待去重。（已在首条"已知 bug"重申。）

### 状态（当日）
- 两主题 229 篇全部 summarized，零积压；hunt 阶段已进 run auto。
- 前半段（救回+兜底+Chrome 生命周期）由并行实例 13:55 commit aa3ea8b。
