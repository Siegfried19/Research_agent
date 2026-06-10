# CLAUDE.md — 研究论文流水线（给 Claude Code 的项目上下文）

> 换机器 / 新会话打开本仓库时**先读这个文件**，再看 `README.md`。
> 本机的对话记忆不会跨机器同步，所有要紧上下文都在仓库里。

## 这个项目是什么
给一段研究思路 → 多源批量搜论文 → 下载全文 → 每篇用一个子 agent 写**中文**结构化总结 → 存进 SQLite 库。
支持：每周增量跑、总结版本化更新、跨主题比较、库内引用关系、付费墙取全文(Tier B)、Telegram 通知。

用户：NYU 研究者（中文交流）。有学校图书馆订阅。每周想跑 1–2 次。

## 怎么跑一个主题（全自动，Python，2026-06-09 起）
> ⚠️ **整条流水线已从 Node/JS 迁移到 Python**（2026-06-09）。脚本都是 `pipeline/*.py`，唯一第三方依赖是 `requests`（见 requirements.txt）。`run.sh` 现在只是个调 `run.py` 的薄壳。

**一条命令跑完全程**，打分/总结用本机 `claude -p` 无头模式（走 Max 订阅，不需 agent 在场、不花 API 钱）：

```bash
python3 pipeline/run.py <id> auto      # 或 bash pipeline/run.sh <id> auto（等价薄壳）
# = discover → score → commit → fetch → recover → hunt → tierb → worklist → sum → finalize
```
全程唯一需要人:**`tierb` 阶段遇 Cloudflare/Duo 验证时会暂停 + Telegram 喊你,你在 Chrome 里点一下即自动续跑**。也可单跑某阶段调试:
```bash
python3 pipeline/run.py <id> discover    # discover.py: 多源搜 → candidates.json
python3 pipeline/run.py <id> score       # score_auto.py: claude -p 逐批打分 → scores/batch_*.json
python3 pipeline/run.py <id> commit      # commit.py: 选篇写库（首跑 TopN / 增量追加 + 重算rank）
python3 pipeline/run.py <id> fetch       # fetch_oa.py: OA 全文（含 arXiv 回退）
python3 pipeline/run.py <id> recover     # recover_oa.py: Unpaywall(repository优先)+arXiv+DBLP会议OA(PMLR/ACL/OpenReview) 免费兜底
python3 pipeline/run.py <id> hunt        # recover_agent.py: claude -p 联网猎免费源(规则渠道全空才轮到它)
python3 pipeline/run.py <id> tierb       # fetch_tierb.py: 浏览器+OpenAthens 取付费墙（人点验证）
python3 pipeline/run.py <id> worklist    # build_worklist.py: 建总结清单（status=pdf_downloaded 的）
python3 pipeline/run.py <id> sum         # summarize_auto.py: claude -p 逐篇写 v1.md
python3 pipeline/run.py <id> finalize    # register_summaries.py + render_topic.py
```
> `claude` CLI 必须已登录。测试可设 `RESEARCH_DB=/tmp/x.sqlite` 用临时库,不碰生产 `db/papers.sqlite`。

新主题：建 `topics/<id>/topic.json`（字段：id/title/idea/queries/window_years/target）。
**检索词(queries)由你根据用户给的研究思路生成**（多组英文关键词，覆盖不同侧面）。

## 关键约定 / 坑（务必遵守）
- **Python 3.10+,stdlib sqlite3**(不再需要 node)。脚本作为模块跑：`python3 pipeline/<x>.py`(脚本内 `from lib.xxx import` 依赖 cwd=pipeline 的 sys.path,run.py 已处理)。
- **打分/总结靠 `claude -p` 无头**(lib/claude.py;prompt 走 stdin、结果 stdout、脚本自己读写文件)。要加第二个模型(Codex 评审团)就照 `lib/claude.py` 复制成 `lib/codex.py`。
- 文件名用**论文标题 slug**（`papers.slug`），不是 DOI。DOI 仍是 `papers.id` 主键。
- **选篇靠 claude -p 相关性打分，不靠 API 排序**（OpenAlex 的相关性把引用量混进去了，会把高引但跑题的论文顶上来）。
- **不用 Google Scholar 批量**（无 API、强反爬）。
- 下载四级：先吃 OA → `recover_oa.py` 规则免费兜底（Unpaywall repository优先 + arXiv 版本枚举 + **DBLP 反查会议自营OA站** PMLR/ACL Anthology/OpenReview，2026-06-10 加,via=dblp-oa）→ `recover_agent.py` **agent 兜底**（claude -p 开 WebSearch/WebFetch 联网找合法免费 PDF，脚本负责下载校验落库；prompt 明令禁 Sci-Hub 类盗版源）→ 最后才 Tier B 付费墙。兜底层设计哲学：**撞到一类拉不下来的就固化一个新渠道**（同 tierb 的 findPdfUrl 出版商适配）。
- 批量下载要**限速**，别刷崩用户学校的访问 / 触发出版商风控。
- `claude -p` 偶尔撞 Max 限流失败 → 重跑该阶段即可（已总结/已打分的自动跳过;sum/score 幂等）。撞限流就调小并发：`python3 pipeline/summarize_auto.py <id> 1`。

## 数据模型（db/papers.sqlite，5 表）
- `papers` 全局论文库：主键=规范化DOI；`slug`=文件名；`status`=discovered/pdf_downloaded/pdf_failed/summarized
- `topics` 研究主题（idea + 生成的 queries）
- `paper_topic` 论文×主题（relevance 分 + 理由 + rank）
- `summary_versions` 总结版本历史（version/path/based_on/note）
- `citations` 库内论文相互引用边

## 脚本清单（pipeline/，全 Python）
init, discover, **score_auto**, commit, fetch_oa, recover_oa, **recover_agent**(hunt,agent联网猎免费源), **fetch_tierb**, build_worklist,
**summarize_auto**, register_summaries, render_topic, migrate_slugs, cross_topic,
prepare_update, **update_auto**, register_updates, suggest_updates, notify, **audit_quality**,
**verify_summaries**(Codex 核查总结幻觉), run.py, run.sh(薄壳)
lib/: db, **log**(一等公民日志), http, sources, merge, store, slug, notify, **claude**(claude -p 调用器+并发池), **quality**(硬信号质量评估), **codex**(codex exec 调用器,跨模型第二引擎)
> `score_auto`/`summarize_auto`/`update_auto` 用 `claude -p` 取代了旧的 Workflow agent。
> `fetch_tierb` = 方法④付费墙抓取（自启 Chrome→OpenAthens→人点验证→混合 B/A 抓 PDF）。
> 日志:每个脚本写 `logs/run.log`(机器日志,一行一事件) + `logs/pipeline-<date>.log`(详细);tierb 另有 `logs/tierb-<date>.log`。

其它命令：
```bash
python3 pipeline/recover_oa.py <id>        # 免费补全(Unpaywall repository优先 + arXiv)
python3 pipeline/suggest_updates.py <id>   # (5b)建议哪些老总结该更新
python3 pipeline/prepare_update.py <doi>   # (5a)备更新 → python3 update_auto.py → register_updates.py
python3 pipeline/cross_topic.py            # (6)跨主题（需≥2主题）
python3 pipeline/audit_quality.py <id>     # 质量审计:回查已入库论文(拉OpenAlex最新撤稿/DOAJ);--apply 移除block级
```

## 质量评价体系（硬信号，2026-06-09 上线；2026-06-10 改"标记优先"）
**不用 LLM，纯代码硬信号**（`lib/quality.py` + `config/quality/` 名单文件，可手工编辑追加）。**设计哲学（用户定）：能标记就不 ban——污染不发生在存进去，发生在用的时候忘了它是什么**，所以 verdict 持久化在 `papers.quality_tier/quality_signals`，每个下游出口都认标记：
- **block**（OpenAlex撤稿 / DOI前缀黑名单=亲手确认过的水刊）→ 死刑信号，discover 丢弃 + commit 双保险，**永不入库**。
- **suspect**（掠夺刊/出版商**名单命中**）→ **入库但带标记**（Beall's 有争议条目，全等匹配也可能偶撞）：commit 需 relevance≥45；**总结自动切"质疑模式"**（summarize_auto 注入批判指令：开头加警示行、结果写"作者声称"、≥5条质疑、主动找硬伤）；topic.md 表格标 ⚠️ + 单独"低可信来源"节；未来 RAG 默认过滤/降权；评审团重点审查对象。
- **trusted**（venue 白名单 / DOAJ 收录）→ 白名单 venue 免疫名单误杀。
- **flag**（纯预印本 / 无venue）→ commit 需 relevance≥`quality.flag_min_relevance`(默认45)；总结注一句"未经同行评审"。有正式 DOI(非10.48550)的不算预印本——OpenAlex 常把已发表论文 venue 标成 arXiv。
- 名单来源：Beall's 衍生 stop-predatory-journals（1309刊+1161出版商，**2017年停更，新水刊靠 `local_blocklist.txt`/`doi_prefix_blocklist.txt` 手工补**，IJISRT=10.38124 已收录）。
- 回溯审计：`audit_quality.py <id>` 拉 OpenAlex 最新撤稿/DOAJ → 出报告 `topics/<id>/quality_audit.md` + **verdict 回写 DB**（dry-run 也回写）；`--apply` 只删 block 级+重算 rank。2026-06-10 对 129 篇跑过：block=0 / suspect=0 / flag=34(全是真预印本) / trusted=36 / ok=59，标记已落库。

## 跨模型评审团（Codex，2026-06-10 上线）
Codex CLI 已装并登录（ChatGPT 订阅,零 API 费;`lib/codex.py` = `codex exec --output-last-message`,镜像 lib/claude.py）。**Codex 永远没有否决权,只提异议/出报告**：
- **打分魔鬼代言人**（`quality.codex_panel`,**默认 false**,开了才生效）：score 阶段 Codex 拿同批论文专找"该拒"理由(跑题/水文/无方法),异议写进 scores/batch_*.json 的 `panel_objection`；commit 合议：**边界分(<60)+异议=挡下;高分+异议=入库但异议追进 relevance_reason**。实测 3 篇试金石全对(放过 DeepMimic,咬掉关键词碰瓷的土木论文和 metaverse 水文)。
- **总结核查** `verify_summaries.py <id> [pct] [并发] [--limit N]`：suspect 必核 + 随机抽 10%,Codex 对照原文核数字/论断,**只出报告不改总结** → `topics/<id>/summary_verification.md`。首测 2 篇即抓到 1 个 major(总结把"行为未预先指定"写成"下坡训练中未见")——幻觉率不是零,抽检值得保留。注入的元信息行(引用数等)已在 prompt 里豁免。
- Codex 偶发限流/超时:panel 失败自动跳过不挡打分;verify 重跑即可。换机器需重新 `npm i -g @openai/codex` + `codex login`。

## Telegram 通知（轻量、非常驻）
- bot @research_agentffbot；配置在 `config/telegram.json`（**gitignore，不入库**；token 是密钥）。
- 设计：`notify()` 一次性推送；`waitForReply()` 仅在一次运行卡住等用户时轮询。**没有守护进程**，跑完就停。
- 用途：Tier B 登录/Duo 提醒、进度、报错。CLI：`python3 pipeline/notify.py settoken|chatid|test`。
- 若换机器：`config/telegram.json` 不在仓库里，需要用户重新 `settoken` + `chatid`。

## 当前状态（截至 2026-06-09）
- 主题 `rl-digital-human-interaction`（强化学习训练可与环境交互的数字人），首测 target=40。
- **2026-06-09 清掉 6 篇垃圾/跑题**（IJISRT 掠夺刊 #29、跑题的 #36/#33、错配的 #38/#32/#39），rank 已重算 → **34 篇**。
- **Tier B 积压清零**：ASE/AMP（其实是 OA，arXiv 直取）、Walk This Way（ACM OA 过 Cloudflare）、plrev（ScienceDirect，OpenAthens 全文）全部拿到。
- **现 34 篇全部已总结**（1 篇有 v2）/ 13 条引用边。topic.md 已渲染。
- **2026-06-09 大改造①：流水线全自动化**——打分/总结改 `claude -p`、付费墙固化成 `fetch_tierb`、`run auto` 一条龙。我(Claude)不再是运行时,只在搭建/调试时介入。
- **工作模式（用户 2026-06-10 定）：对话驱动，不解耦**。开新主题=用户来聊研究思路→讨论边界→我生成检索词**给用户过目确认**→建 topic.json→我起 `run auto` 后台跑+挂监控（盯日志、出问题修、汇报漏斗数据）。每周增量=用户说一句,我跑同一条命令盯完汇报。`claude -p` 是我调度的执行层,不是替代我。
- **2026-06-09 大改造②：整套从 Node/JS 迁移到 Python**(用户要长期维护、Python 生态更适合论文/PDF/未来语义过滤)。20 个 JS + run.sh 全部重写为 `pipeline/*.py`,JS 已删净;DB(`db/papers.sqlite`)原样复用。lib 加了 `log.py`(一等公民日志)。各阶段已逐个测过;真端到端(discover→score→commit→render)在临时库验证通过。**唯一没在 Python 形态下端到端实跑的是 `fetch_tierb` 的浏览器抓取**(本主题已无付费墙篇;零件都验证过,下个付费墙主题盯一次)。

## Tier B 取全文（方法④，已验证可用 2026-06-09）
分工：**用户人在机器旁手点人工关卡（Cloudflare Turnstile / Duo）；其余全自动。** 远程桌面方案已放弃（太复杂）。每周跑约 1 次。
- **自启 Chrome**（照 Stock_agent `ensure_chrome`）：`opencli doctor` 没含 "Extension: connected" 就 `DISPLAY=:1 setsid google-chrome --user-data-dir=~/.config/google-chrome-scrape --profile-directory="Profile 2" --no-restore-session &`，轮询 doctor ~60s（profile 别名 `8fnbkdfj`，~3s 连上；偶发断开重启即可）。
- **Chrome 生命周期（2026-06-10 照 Stock_agent 补齐,根治"越开越多"）**：跑前 flock 独占（锁=`~/.config/google-chrome-scrape/scrape.lock`,共用该实例的任务同一把锁）→ 跑完 **finally 无条件 `pkill -f "user-data-dir=<UDD>"` 整关**（独立目录绝不误伤日常 Chrome;复用来的实例也关）。副产物:每次都是 fresh launch → PDF 下载 pref 必生效 → 方法 B 始终可用。⚠️ Stock_agent 的锁还是它项目本地的 `chrome.lock`,两项目极端撞车时 tierb 收尾会关掉它在用的实例（低概率,要根治就把 Stock_agent 的锁也迁到 UDD 里这把）。
- **NYU 访问路径**：⚠️ NYU 已弃 EZProxy 迁 **OpenAthens**，旧 `proxy.library.nyu.edu/login?url=` 废。新路径 = **`https://go.openathens.net/redirector/nyu.edu?url=<doi/landing>`**。profile 已有有效 NYU 会话（暂不弹 Duo；会话过期才弹）。
- **取 PDF（混合 B 优先 + A 兜底）**：`fetch_tierb.py` 自启 Chrome 时写 profile 偏好 `always_open_pdf_externally=true` + 下载目录 `store/dl_tmp`，使 PDF **直接下载**(像人点下载)。
  - **方法 B(优先)**：open PDF 链 → 盯 `store/dl_tmp` 等新的、稳定的 `.pdf`(无 `.crdownload` 伴随)→ 搬到 `store/pdfs/`。
  - **方法 A(兜底)**：B 在 ~20s 内没出文件(如在阅读器打开/pref 未生效)→ 页面内 `fetch(location.href,{credentials:'include'})`→`btoa`(8192 分块、**同一次 eval**)→分块读出→`base64 -d` 落盘。
  - ⚠️ **B 只在 fetch_tierb 自己启动 Chrome 时才生效**(关着才能改 pref);若 Chrome 已开着连上,则只用 A。两者都过 `%PDF`+pdfinfo 校验。
  - ScienceDirect 导航 pdfft 链→浏览器自动跳签名 S3；ACM 自动过 Cloudflare 无需登录；ScienceDirect/Elsevier 每篇都弹 Turnstile。
- **findPdfUrl 出版商适配（2026-06-10 扩充）**：IEEE Xplore（SPA 抓不到 DOM 链→从 URL 取 document 号构造 `stampPDF/getPDF.jsp?arnumber=`）、DSpace 机构库（选择器加 `a[href*="/bitstream"]`、`.pdf?`）、Wiley（`/doi/pdf/` 是 HTML 拦截页→直返 `/doi/pdfdirect/{doi}?download=true`）、SPA 首轮没找到等 5s 重试。
- **手机过验证（远程看屏）—— ⚠️ 已封存(MOTHBALLED 2026-06-10,用户觉得有风险)**：代码保留但**默认关**,不自动启动、不广播。`fetch_tierb` 的 `ensure_remote_view()` 默认返回空串,除非显式开 `config tier_b.remote_view=true` 或 `RESEARCH_REMOTE_VIEW=1`。关着时 tierb 行为如旧(在机器旁点验证)。
  - 机制(留档备用):`pipeline/remote_view.sh` 把 `:1` 经 **x11vnc(仅 localhost) + websockify/noVNC(绑 Tailscale IP `100.83.75.76:6080`,VNC 密码,不开 Funnel)** 暴露成网页;开启时 tierb 弹验证会 Telegram 带 noVNC 链接,手机点链接→看机器 Chrome→点掉验证→续跑。密钥 `config/x11vnc.{pass,plain}` gitignored;新版 noVNC 在 `vendor/novnc`(1.4.0,带双指缩放) gitignored。
  - 验证必须点在机器那个 Chrome 上(cf_clearance 绑指纹+IP),只能远程看屏、不能手机本地解。
  - **遗留问题**(若日后解封要先解决):①手机端双指缩放用户反馈仍放不大(noVNC 1.4.0 已装,URL `resize=scale`,待查 viewport/手势);②用户安全顾虑(虽已 localhost-only+tailnet+2FA)。

## 待办 / 下一步
- ✅ **(2026-06-09 完成)** 4 篇全文+总结;`fetch_tierb` 固化;`score_auto`/`summarize_auto`(claude -p);`run auto` 一条龙;**整套迁移到 Python**;**修了 recover_oa**(arxiv/repository 优先 + 用 ext_ids.arxiv 不只靠标题)。
1. **端到端实跑验证 `fetch_tierb.py`**：本主题已无待抓篇,脚本只测过"无事可做"+语法+各零件(手动验证过)。下个有付费墙的主题要盯一次完整 tierb 跑(尤其 findPdfUrl 跨出版商、challenge 检测、混合 B/A 抓取)。
2. ✅ **(2026-06-09 完成,06-10 改"标记优先")文章评价/筛选体系——硬信号层**：`lib/quality.py` + `config/quality/` 名单 + discover/commit 双闸 + suspect 标记贯穿总结(质疑模式)/渲染(⚠️) + `audit_quality.py` 回溯审计（见上文"质量评价体系"节）。对 129 篇审计:block=0/suspect=0,标记已落库。
   - ✅ **(2026-06-10 完成)跨模型评审团**：`lib/codex.py` + score 魔鬼代言人(`quality.codex_panel`,默认关) + `verify_summaries.py` 总结核查(suspect 必核+10%抽检),见上文"跨模型评审团"节。**待用户决定**:下轮跑时把 `codex_panel` 打开试真池子。
3. **放大到 200**（topic.json target 改 200，`python3 pipeline/run.py <id> auto`；commit 增量追加）。
4. 跨主题比较需要先有第 2 个主题。
5. (小) claude -p 并发撞 Max 限流就调小 `sum`/`score` 的 concurrency 参数（默认 3/4）。
6. **🌟 大计划:把论文库变成"遇到问题就来查的知识库"(RAG over corpus)** —— 用户在别的 project 卡住时,让 agent 来这个库里检索答案。结论:**可行**(curated 语料+总结+全文+引用图,RAG 底子好);**数据库大小不是瓶颈**(sqlite 只存元数据/摘要,全文在 store/text;真正难点是"检索准不准")。
   - ⚠️ 检索层必须认 `papers.quality_tier`:suspect 默认过滤或降权+答案中显式标注来源可疑(质量体系 2026-06-10 起是"标记进库"不是"拒之门外",出口不过滤=污染答案)。
   - **落地路径(按性价比,分阶段)**:① 先做 **FTS5 全文搜 + `ask.py "<问题>"` 入口**(sqlite 内置,零依赖,curated 库里够用)→ ② 不够再上**语义向量**(嵌入总结,sentence-transformers 本地 或 嵌入 API + sqlite-vec)→ ③ **混合+claude -p 重排** → ④ **引用图扩展**(命中后顺 citations 拉邻居)→ ⑤ **两段式**(先总结层快筛、再对最相关几篇拉全文深读)。**别一上来堆向量,先 FTS5。**
   - **"持续学习"的正确理解**:不是微调模型(贵+脆+不值,RAG 完胜),而是三层让"语料变聪明":(a)语料每周增长;(b)**合成知识层**——定期 claude -p 把跨论文的方法/共识/矛盾/趋势蒸馏成主题笔记,= 一份活的文献综述(cross_topic.py 有雏形);(c)问答记忆,存过往结论别重推。检索时取用这三层。
   - 状态:**只记录,未动手**。下次从 ①(FTS5 + ask.py)开始。

详见 `logs/SESSION-*.md`（操作记录）和 `logs/run.log`（机器日志）。
