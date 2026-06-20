# fetch — STATE（层积日志）

> 写法：**新在上、老在下、不删**，每条标题带日期+时间戳。最顶一条 = 此刻状态/卡在哪；往下翻 = 历史。
> README.md 是定型设计（覆盖更新）；这里是带细节的过程账。
> 局部改动记这里；跨模块/全局改动记 `../../../claude_log.md`，这里只留一行指针。

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
