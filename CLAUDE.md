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
# = discover → score → commit → fetch → recover → tierb → worklist → sum → finalize
```
全程唯一需要人:**`tierb` 阶段遇 Cloudflare/Duo 验证时会暂停 + Telegram 喊你,你在 Chrome 里点一下即自动续跑**。也可单跑某阶段调试:
```bash
python3 pipeline/run.py <id> discover    # discover.py: 多源搜 → candidates.json
python3 pipeline/run.py <id> score       # score_auto.py: claude -p 逐批打分 → scores/batch_*.json
python3 pipeline/run.py <id> commit      # commit.py: 选篇写库（首跑 TopN / 增量追加 + 重算rank）
python3 pipeline/run.py <id> fetch       # fetch_oa.py: OA 全文（含 arXiv 回退）
python3 pipeline/run.py <id> recover     # recover_oa.py: Unpaywall(repository优先)+arXiv 免费兜底
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
- 下载先吃 OA，再 `recover_oa.py`（Unpaywall repository优先 + arXiv 兜底，免费），最后才 Tier B 付费墙。
- 批量下载要**限速**，别刷崩用户学校的访问 / 触发出版商风控。
- `claude -p` 偶尔撞 Max 限流失败 → 重跑该阶段即可（已总结/已打分的自动跳过;sum/score 幂等）。撞限流就调小并发：`python3 pipeline/summarize_auto.py <id> 1`。

## 数据模型（db/papers.sqlite，5 表）
- `papers` 全局论文库：主键=规范化DOI；`slug`=文件名；`status`=discovered/pdf_downloaded/pdf_failed/summarized
- `topics` 研究主题（idea + 生成的 queries）
- `paper_topic` 论文×主题（relevance 分 + 理由 + rank）
- `summary_versions` 总结版本历史（version/path/based_on/note）
- `citations` 库内论文相互引用边

## 脚本清单（pipeline/，全 Python）
init, discover, **score_auto**, commit, fetch_oa, recover_oa, **fetch_tierb**, build_worklist,
**summarize_auto**, register_summaries, render_topic, migrate_slugs, cross_topic,
prepare_update, **update_auto**, register_updates, suggest_updates, notify, run.py, run.sh(薄壳)
lib/: db, **log**(一等公民日志), http, sources, merge, store, slug, notify, **claude**(claude -p 调用器+并发池)
> `score_auto`/`summarize_auto`/`update_auto` 用 `claude -p` 取代了旧的 Workflow agent。
> `fetch_tierb` = 方法④付费墙抓取（自启 Chrome→OpenAthens→人点验证→混合 B/A 抓 PDF）。
> 日志:每个脚本写 `logs/run.log`(机器日志,一行一事件) + `logs/pipeline-<date>.log`(详细);tierb 另有 `logs/tierb-<date>.log`。

其它命令：
```bash
python3 pipeline/recover_oa.py <id>        # 免费补全(Unpaywall repository优先 + arXiv)
python3 pipeline/suggest_updates.py <id>   # (5b)建议哪些老总结该更新
python3 pipeline/prepare_update.py <doi>   # (5a)备更新 → python3 update_auto.py → register_updates.py
python3 pipeline/cross_topic.py            # (6)跨主题（需≥2主题）
```

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
- **2026-06-09 大改造②：整套从 Node/JS 迁移到 Python**(用户要长期维护、Python 生态更适合论文/PDF/未来语义过滤)。20 个 JS + run.sh 全部重写为 `pipeline/*.py`,JS 已删净;DB(`db/papers.sqlite`)原样复用。lib 加了 `log.py`(一等公民日志)。各阶段已逐个测过;真端到端(discover→score→commit→render)在临时库验证通过。**唯一没在 Python 形态下端到端实跑的是 `fetch_tierb` 的浏览器抓取**(本主题已无付费墙篇;零件都验证过,下个付费墙主题盯一次)。

## Tier B 取全文（方法④，已验证可用 2026-06-09）
分工：**用户人在机器旁手点人工关卡（Cloudflare Turnstile / Duo）；其余全自动。** 远程桌面方案已放弃（太复杂）。每周跑约 1 次。
- **自启 Chrome**（照 Stock_agent `ensure_chrome`）：`opencli doctor` 没含 "Extension: connected" 就 `DISPLAY=:1 setsid google-chrome --user-data-dir=~/.config/google-chrome-scrape --profile-directory="Profile 2" --no-restore-session &`，轮询 doctor ~60s（profile 别名 `8fnbkdfj`，~3s 连上；偶发断开重启即可）。
- **NYU 访问路径**：⚠️ NYU 已弃 EZProxy 迁 **OpenAthens**，旧 `proxy.library.nyu.edu/login?url=` 废。新路径 = **`https://go.openathens.net/redirector/nyu.edu?url=<doi/landing>`**。profile 已有有效 NYU 会话（暂不弹 Duo；会话过期才弹）。
- **取 PDF（混合 B 优先 + A 兜底）**：`fetch_tierb.py` 自启 Chrome 时写 profile 偏好 `always_open_pdf_externally=true` + 下载目录 `store/dl_tmp`，使 PDF **直接下载**(像人点下载)。
  - **方法 B(优先)**：open PDF 链 → 盯 `store/dl_tmp` 等新的、稳定的 `.pdf`(无 `.crdownload` 伴随)→ 搬到 `store/pdfs/`。
  - **方法 A(兜底)**：B 在 ~20s 内没出文件(如在阅读器打开/pref 未生效)→ 页面内 `fetch(location.href,{credentials:'include'})`→`btoa`(8192 分块、**同一次 eval**)→分块读出→`base64 -d` 落盘。
  - ⚠️ **B 只在 fetch_tierb 自己启动 Chrome 时才生效**(关着才能改 pref);若 Chrome 已开着连上,则只用 A。两者都过 `%PDF`+pdfinfo 校验。
  - ScienceDirect 导航 pdfft 链→浏览器自动跳签名 S3；ACM 自动过 Cloudflare 无需登录；ScienceDirect/Elsevier 每篇都弹 Turnstile。

## 待办 / 下一步
- ✅ **(2026-06-09 完成)** 4 篇全文+总结;`fetch_tierb` 固化;`score_auto`/`summarize_auto`(claude -p);`run auto` 一条龙;**整套迁移到 Python**;**修了 recover_oa**(arxiv/repository 优先 + 用 ext_ids.arxiv 不只靠标题)。
1. **端到端实跑验证 `fetch_tierb.py`**：本主题已无待抓篇,脚本只测过"无事可做"+语法+各零件(手动验证过)。下个有付费墙的主题要盯一次完整 tierb 跑(尤其 findPdfUrl 跨出版商、challenge 检测、混合 B/A 抓取)。
2. **文章评价/筛选体系**（放大到 200 前要做）：score_auto 已加"来源质量"提示词,但还需更硬的信号（掠夺刊名单/是否同行评审/venue 白名单）从源头挡。
   - **(构想,未动手)跨模型评审团**：把单次打分升级成小评审团,成员**混编模型**(Claude+Codex 平级),靠不同训练分布互补盲点。最小版 2 席:相关性审(Claude)+ 魔鬼代言人(Codex,专挑"该拒"理由)；来源质量别用 LLM,用硬名单。Codex 走 ChatGPT 订阅(对称 claude -p 蹭 Max,零额外花费;需先装 `npm i -g @openai/codex` + `codex login`,本机暂未装)。落地=加 `pipeline/lib/codex.py`(照抄 lib/claude.py 换命令)+ score_auto 路由。**先做硬信号,panel 是补充层**;参考库在 `ref/academic-research-skills/`(跨模型机制见 `shared/cross_model_verification.md`)。
3. **放大到 200**（topic.json target 改 200，`python3 pipeline/run.py <id> auto`；commit 增量追加）。
4. 跨主题比较需要先有第 2 个主题。
5. (小) claude -p 并发撞 Max 限流就调小 `sum`/`score` 的 concurrency 参数（默认 3/4）。
6. **🌟 大计划:把论文库变成"遇到问题就来查的知识库"(RAG over corpus)** —— 用户在别的 project 卡住时,让 agent 来这个库里检索答案。结论:**可行**(curated 语料+总结+全文+引用图,RAG 底子好);**数据库大小不是瓶颈**(sqlite 只存元数据/摘要,全文在 store/text;真正难点是"检索准不准")。
   - **落地路径(按性价比,分阶段)**:① 先做 **FTS5 全文搜 + `ask.py "<问题>"` 入口**(sqlite 内置,零依赖,curated 库里够用)→ ② 不够再上**语义向量**(嵌入总结,sentence-transformers 本地 或 嵌入 API + sqlite-vec)→ ③ **混合+claude -p 重排** → ④ **引用图扩展**(命中后顺 citations 拉邻居)→ ⑤ **两段式**(先总结层快筛、再对最相关几篇拉全文深读)。**别一上来堆向量,先 FTS5。**
   - **"持续学习"的正确理解**:不是微调模型(贵+脆+不值,RAG 完胜),而是三层让"语料变聪明":(a)语料每周增长;(b)**合成知识层**——定期 claude -p 把跨论文的方法/共识/矛盾/趋势蒸馏成主题笔记,= 一份活的文献综述(cross_topic.py 有雏形);(c)问答记忆,存过往结论别重推。检索时取用这三层。
   - 状态:**只记录,未动手**。下次从 ①(FTS5 + ask.py)开始。

详见 `logs/SESSION-*.md`（操作记录）和 `logs/run.log`（机器日志）。
