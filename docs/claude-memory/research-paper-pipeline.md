---
name: research-paper-pipeline
description: The recurring multi-source paper discovery + summarization pipeline built in Research_agent
metadata: 
  node_type: memory
  type: project
  originSessionId: ef8f900e-36bb-40cf-9d06-c2d00c1e7dce
---

用户要的核心系统：给一段研究思路 → 多源批量搜论文 → 下全文 → 每篇一个子 agent 写中文总结 → 存入 SQLite 库。每周跑 1–2 次，增量不重复。

**关键设计决策（已和用户确认）：**
- 发现：多源混合 OpenAlex + Semantic Scholar + arXiv + PubMed，按规范化 DOI 去重。**不用 Google Scholar 批量**（无 API、强反爬）。
- 选篇：API 排序会把高引但跑题的论文顶上来，所以必须经**agent 相关性打分关卡**（读摘要打 0-100 分+中文理由）才选 Top-N。这一步同时填 `paper_topic.relevance_reason`。
- 全文：先 OA 免费源（全自动，`fetch_oa.js`，含 arXiv 回退）；付费墙走 **opencli + 用户登录的 Chrome** 图书馆代理（Tier B，**暂缓未做**）。opencli 已装好(@jackwener/opencli)，driver 复用用户已登录会话，不碰其凭证。
- 总结：中文，三段置顶（一句话/解决什么问题/什么方法），含"局限与我的质疑"批判段；每篇 `store/summaries/<id>/vN.md`，支持**版本化更新**（旧版保留，新版记 based_on）。
- 数据库：全局论文库 + 主题视图（论文只存一份多主题共享）。5 表：papers/topics/paper_topic/summary_versions/citations。库内相互引用记入 citations。
- 首跑 Top200、窗口滚动近20年；增量拉窗口内所有未见过的；英语为主收日语；偏好高引但保留边角文(is_edge 标记 🪨)。

**技术栈（2026-06-09 起 = Python）：** Python 3.10,stdlib sqlite3,唯一三方依赖 `requests`(requirements.txt);pdftotext/pdfinfo 可用。打分/总结/更新走 `claude -p`(lib/claude.py)。**早期是 Node(`node:sqlite`)+ Workflow agent,已全量迁移到 Python 并删净 JS**(见下"大改造②")。

**⚠️ 2026-06-09 大改造②——整套 Node/JS → Python(用户决定,要长期维护;Python 生态更适合论文/PDF/未来语义过滤;用户本人 Python 研究者,姊妹项目 Stock_agent 也是 Python):** 20 个 JS + run.sh 全部重写为 `pipeline/*.py`,JS 删净;`db/papers.sqlite` 原样复用(sqlite 文件跨语言通用)。新增 `lib/log.py`(一等公民日志:run.log 机器日志 + pipeline-<date>.log 详细)。`lib/db.py` 支持 `RESEARCH_DB` 环境变量指向临时库(测试隔离)。run.sh 变成调 run.py 的薄壳。**已验证**:lib 冒烟、4 个数据源对真实 API、run.py 编排、render/register/worklist 对真实库、完整 discover→score→commit→render 在临时库跑通。**唯一没在 Python 形态端到端实跑**:fetch_tierb 浏览器抓取(本主题无付费墙篇了;零件都验证过,下个付费墙主题盯一次)。**顺手修了 recover_oa 的 bug**:候选 URL 把 arxiv/repository 排在出版商前(出版商 PDF 常 403)+ 用 ext_ids.arxiv 不只靠标题匹配。新文件名: score_auto/summarize_auto/update_auto/fetch_tierb/run.py + lib/{db,log,http,sources,merge,store,slug,notify,claude}.py。

**首测状态（2026-06-07）：** 主题 rl-digital-human-interaction（强化学习训练可与环境交互的数字人），小规模 target=40 跑通：发现1760→去重1328→池80→打分选40→下载27篇OA全文→27篇中文总结，13条引用边。质量验证 OK（PADL 总结读了全文、批判紧扣主题）。13 篇未取全文(5 个 403 仅 openalex 源 + 8 个非OA) 归 Tier B。

**已完成（2026-06-08）：** Phase 0-6 全部建完并验证。文件名改用论文标题 slug（papers.slug，DOI 仍为主键）。增量跑＝commit 追加式+重算rank。Phase 5 版本化更新验证通过（v1保留、v2记 based_on）。一键编排＝`pipeline/run.sh <topicId> <stage>`（stage: discover/scoreargs/commit/fetch/worklist/sumargs/finalize），两个 agent-workflow（score/summarize）由 Claude 在 scoreargs→commit、sumargs→finalize 之间调用（args 须为 JSON，workflow 内 `JSON.parse(args)`）。

**脚本清单（pipeline/）：** init, discover, score.workflow, commit, fetch_oa, build_worklist, summarize.workflow, register_summaries, render_topic, migrate_slugs, cross_topic, prepare_update, update.workflow, register_updates, suggest_updates, run.sh。`node --experimental-sqlite` 跑。

**2026-06-08 续：** recover_oa.js 免费补全（Unpaywall+arXiv，零登录）捞回 3 篇 → 现 30/40 已总结。Telegram bot @research_agentffbot 配好（轻量非常驻：notify 一次性推送 + waitForReply 仅运行卡住时轮询；config/telegram.json 不入库）。git 已初始化推到 github.com/Siegfried19/Research_agent。**仓库根有 CLAUDE.md 作跨机器交接文档**（记忆不跨机器，认准它）。

**2026-06-09：** 库清洗——删掉 6 篇垃圾/跑题（IJISRT 掠夺刊 #29；跑题 #36/#33；错配 #38/#32/#39），rank 重算 → **现 34 篇（30 已总结）**。免费 recover_oa 对剩 4 篇全失败 → **Tier B 待取 4 篇：ASE/AMP/WalkThisWay(ACM)+plrev 物理角色动画综述(Elsevier)**。Tier B 设计与用户敲定为**全自动**（非手动登录）：opencli 用常驻 profile `8fnbkdfj` 开代理 URL → 探到 Duo/登录页 → Telegram notify 喊用户过 Duo → waitForReply("go") → 会话活着时一口气抓完 → 结束 notify 报告。取 PDF **不碰 cookie**（NYU 会话 httpOnly），让 Chrome 自己下：①`opencli browser <s> network --detail <key> --raw` 抠响应体 或 ②`browser wait download` 下到目录再搬，**在 ASE 上实测定**，跑通固化为 `pipeline/fetch_tierb.js`（自带日志 run.log+logs/tierb-<date>.log）。opencli v1.8.3 doctor 全绿。

**2026-06-09 续（Tier B 全部打通，积压清零）：** 4 篇全拿到 → 现 **34 篇全有全文（30 已总结 + 4 待总结 ASE/AMP/WalkThisWay/plrev）**。
- **方法③ arXiv 直取**：ASE←arxiv 2205.01906、AMP←arxiv 2104.02180（之前误判付费墙，实为 OA；recover_oa bug：出版商 PDF 排在 arxiv 前 + 缩写标题"ASE"/"AMP"匹配失败，待修）。
- **方法④ 浏览器（已验证可用）**：照 Stock_agent 的 ensure_chrome 模式**自启** OpenCLI Chrome——`DISPLAY=:1 setsid google-chrome --user-data-dir=~/.config/google-chrome-scrape --profile-directory="Profile 2" --no-restore-session`，轮询 `opencli doctor` 含 "Extension: connected"（profile 别名 `8fnbkdfj`，~3s 连上；偶发断开，重启即可）。取 PDF：**页面内 `fetch(url,{credentials:'include'})`→`btoa`(8192 分块 fromCharCode)→存 window.__pdf→分块 eval 读出→`base64 -d` 落盘→pdftotext**。绕过 cookie/Cloudflare/下载目录。固化时 **fetch+encode 要在同一次 eval**（分两次 fetch 签名链字节会差几百字节）。WalkThisWay（ACM OA 但 Cloudflare）真浏览器自动过、无需登录。
- **关键：NYU 已从 EZProxy 迁到 OpenAthens！** 旧 `proxy.library.nyu.edu/login?url=` 彻底废（config 占位是错的）。**新访问路径 = `https://go.openathens.net/redirector/nyu.edu?url=<doi>`** → 落到出版商页。plrev(ScienceDirect) 就这么走通：redirector→SD 文章页（**用户手点 Cloudflare Turnstile，无 Duo——profile 已有有效 NYU 会话**）→"Full text access"→导航 pdfft 链→浏览器自动跳到签名 S3 真链→in-page fetch 抓下（30 页完整）。**ScienceDirect/Elsevier 每篇都弹 Turnstile 人机验证**（ACM 不弹），放大时是人工瓶颈。

**与用户敲定的分工（2026-06-09）：** 远程桌面方案（VNC/Tailscale/CRD）**放弃，太复杂**。改为：**用户人在机器旁、亲手点人工关卡（Turnstile/Duo）；我全自动其余（拉 Chrome/导航/抓取/落库）**。每周跑约 1 次。

**2026-06-09 大改造——流水线全自动化（用户核心诉求：要可全自动跑的 pipeline，别让 Claude 当运行时一篇篇手动下）：** 关键钥匙=本机 `claude` CLI(2.1.169)。新建 `lib/claude.js`(runClaude=`claude -p --model opus`，prompt 走 stdin、结果 stdout，并发池 pool；照 Stock_agent 写法，走 Max 订阅不花 API)。
- **`score_auto.js`** 取代 score.workflow：逐批 claude -p 打分→写 `scores/batch_*.json`（commit.js 消费）。提示词已加"来源质量/掠夺刊压分"。已验证。
- **`summarize_auto.js`** 取代 summarize.workflow：逐篇把全文(text_path，截 120k)inline 进 prompt→claude -p→stdout 即 md→写 `summary_path`。幂等(summary 存在则跳)。已对 4 篇实跑通过、质量好。
- **`fetch_tierb.js`** 固化方法④：ensureChrome(自启+轮询 doctor+detectAlias)→逐篇 OpenAthens redirector→isChallenge 检测(标题/URL)→撞验证则 notify+轮询等用户点→findPdfUrl(citation_pdf_url/pdfft//doi/pdf/ 兜底构造)→open 跟跳转→grabPdf(同一次 eval fetch+base64,再 chunk 读出)→verifyPdf(%PDF+pdfinfo)→pdftotext→落库。本主题已无待抓,只测了"无事可做"+语法+各零件手动验证;**下个有付费墙主题要盯一次完整实跑**。
- **`run.sh` 新增** stages: score/recover/tierb/sum + **`auto`**(discover→score→commit→fetch→recover→tierb→worklist→sum→finalize 一条龙)。旧 scoreargs/sumargs+手调 Workflow 弃用(留作 debug)。
- **现 34 篇全部已总结**(1 篇 v2)、topic.md 渲染。本主题完成。

**与用户敲定的工作方式（重要）：** 用户要的是**能自动跑的系统**，不是让我当 agent 一直在旁边跑/手动操作。我的角色=**搭建和调试 pipeline**，跑起来后我退出，用户每周 `run.sh <id> auto`、只在 tierb 撞验证时手点一下。

**2026-06-15 现状：** 已**放量到两主题**——`rl-digital-human-interaction`(129 篇全总结，首测 34 后扩大) + `rl-general-toolbox`(100 篇全总结)，全库 221 篇有总结(约 8 篇两主题重叠)。**目录分层重构**(2026-06-15)：`pipeline/` 根只留入口/公共 API(run.py/ask.py)，主链 14 脚本进 `stages/`，旁路 11 脚本进 `tools/`，共享库 `lib/`；stages/tools 每文件顶部有 path shim 三行让 `from lib...` 解析到 pipeline/lib(见 `pipeline/ARCHITECTURE.md`)。知识库出口①已落地、出口②半成品：`ask.py`(FTS5 全文搜，`--answer` claude -p 综合，`--json` 给别的项目 agent 用)；⚠️ **出口②的全局发现机制指针 2026-06-16 已从 `~/.claude/CLAUDE.md` 撤回(ask.py 还没修好,不放半成品给外部 agent)，待就绪再加回。**verify 升级见 [[cross-model-codex-panel]]。

**待办：** ① 下个付费墙主题盯一次 `fetch_tierb.js` 完整实跑(findPdfUrl 跨出版商/challenge 检测/chunk 读出);② 修 recover_oa(arxiv 优先 + 缩写标题);③ 更硬的来源质量过滤(掠夺刊名单/venue 白名单);④ 放大到 200(`run.sh auto`);⑤ 跨主题需≥2 主题;⑥ claude -p 撞限流就调小 sum/score 并发。
