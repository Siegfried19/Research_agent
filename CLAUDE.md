# CLAUDE.md — 研究论文流水线（给 Claude Code 的项目上下文）

> 换机器 / 新会话打开本仓库时**先读这个文件**，再看 `README.md`。
> 本机的对话记忆不会跨机器同步，所有要紧上下文都在仓库里。
> **记忆分布地图 + 换机器完整清单 → `MIGRATION.md`**（2026-06-10 建，回答"记忆在哪/换机器怎么办"）。

## 这个项目是什么
给一段研究思路 → 多源批量搜论文 → 下载全文 → 每篇用一个子 agent 写**中文**结构化总结 → 存进 SQLite 库。
支持：每周增量跑、总结版本化更新、跨主题比较、库内引用关系、付费墙取全文(Tier B)、Telegram 通知。

用户：NYU 研究者（中文交流）。有学校图书馆订阅。每周想跑 1–2 次。

## 怎么跑一个主题（全自动，Python，2026-06-09 起）
> ⚠️ **整条流水线已从 Node/JS 迁移到 Python**（2026-06-09）。脚本都是 `pipeline/*.py`，唯一第三方依赖是 `requests`（见 requirements.txt）。`run.sh` 现在只是个调 `run.py` 的薄壳。

**一条命令跑完全程**，打分/总结用本机 `claude -p` 无头模式（走 Max 订阅，不需 agent 在场、不花 API 钱）：

```bash
python3 pipeline/run.py <id> auto      # 或 bash pipeline/run.sh <id> auto（等价薄壳）
# = discover → score → commit → fetch → recover → hunt → tierb → worklist → sum → finalize → verify
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
python3 pipeline/run.py <id> verify      # escalate_verify.py --start-pct 100: Codex 全量核查新总结+自动修正 major,再 render
```
> `claude` CLI 必须已登录。测试可设 `RESEARCH_DB=/tmp/x.sqlite` 用临时库,不碰生产 `db/papers.sqlite`。

**夜间自动化拆分（2026-06-16）**：为"常开机器半夜自动跑、白天把 token 留给用户",`auto` 按 token 消耗+要不要人切成两半:
- `python3 pipeline/run.py <id> auto-pull` = discover→score→commit→fetch→recover→hunt→**tierb**→worklist。**白天/有人时手动跑**(tierb 要点付费墙验证),只花小量 token(score/hunt)。
- `python3 pipeline/run.py <id> auto-sum [N]` = sum→finalize→verify。**夜间 cron 无人值守**,token 大户;continue-on-error(撞限流不中断、次晚幂等补齐)+ 起跑/收尾发 Telegram。第三参 `N`=本批最多总结 N 篇(`summarize_auto --limit`,按 rank 取,幂等续做)。**节奏(用户 2026-06-16 定,2026-06-17 把批量从 10 提到 20):一晚跑两批、各 20 篇、相隔 ~5.5h**(踩 token 滚动窗口重置;两条 cron 行 2:00/7:30。**2026-06-17 从 4.5h 调到 5.5h**:实测 codex 额度窗口只够 ~20 次重型核查、且小时级恢复,4.5h 第二批常落进未恢复的窗口仍全挂——见 `logs/SESSION-2026-06-17-codex-quota.md`)。提量依据:10 篇用量校准实测单篇 summarize ~$3.36 等效/Max 实付$0、verify codex ~131s/篇。
> **2026-06-17 起 cron 用队列模式 `auto-sum-next [N]`**(取代写死单主题的 `auto-sum <id> [N]`,后者保留可手动用):每批从 `topics` 表按 `priority DESC, 建立序` 挑**第一个还有可做篇的主题**做 ≤N 篇,做完自动顺到下一主题——加新主题自动进队、不改 cron;一次只跑一个主题=串行不抢额度。插队=调 `topics.priority`(可经 Telegram bot 让我改,当晚生效)。收尾 Telegram 发 本主题燃尽(🎉/⚠️/✅)+**全队列各主题剩余**;全清发🎉;0进展(疑似坏PDF)发⚠️。`run_auto_sum` chain 头部加了 worklist(切主题自洽)。**cron 已真装并冒烟验证过(PATH 含 ~/.local/bin + nvm codex 目录),队列 priority:gt=1 先做、dhi=0。** 实现见 run.py 的 `select_next_topic/queue_report/burn_down_msg/topic_progress`。
- 切点理由:tierb(唯一要人)卡链子中间,sum/verify(token 大户)在后半段——前半白天连人带验证搞定,后半烧 token 的丢夜里。`auto`(全程)保留不动。**部署到常开机器的完整 runbook(cron 行/干净环境 PATH 坑/前提)→ `docs/nightly-cron-deploy.md`。**

新主题：建 `topics/<id>/topic.json`（字段：id/title/idea/queries/window_years/target；**可选 `score_anchors`**=3张已定分参照样本[高~95/边界~45/低~10]，治打分跨批次漂移，见下）。
**检索词(queries)由你根据用户给的研究思路生成**（多组英文关键词，覆盖不同侧面）。

**打分跨批次校准漂移修法（2026-06-17，未提交）**：`score_auto` 每批独立 claude -p 会让"几分算相关"逐批微漂，落截断线附近翻转去留。改了 4 处：rubric 通用骨架(替掉原写死在 digital-human 的例子)＋`topic.json.score_anchors` 注入每批固定头部钉死刻度＋reason 须引原文(证据接地)；batch 10→20＋批内洗牌(对冲位置偏置)；`boundary_rerank` 对去留线 ±8 分窄带×5次取均值复称(首跑=target截断线/增量=资格闸rel≥30·flag_min)，写 `scores/zz_boundary.json` 靠文件名排序让 commit 合并覆盖(commit.py 没动)。**调研依据+方案 → `docs/score-drift-research-findings.md`。** 新主题**冷启动全自动自举**:`score` 阶段发现 topic.json 无 `score_anchors` 就自动裸跑整遍→从整遍分布挑高/边界/低3张写回 topic.json(`autopick_anchors`,非阻塞推TG告知可事后改)→带锚重打;冻好后增量复用不再自举。`run auto` 一条龙无需人介入。想改自举挑的锚点→直接编辑 topic.json 的 `score_anchors` 后重跑 score。gt/dhi 已手挑锚点填好(比自动准),不会触发自举。

## 关键约定 / 坑（务必遵守）
- **Python 3.10+,stdlib sqlite3**(不再需要 node)。**目录分层(2026-06-15)**：入口/公共API 在 `pipeline/` 根(run.py/ask.py)，主链脚本在 `pipeline/stages/`，旁路在 `pipeline/tools/`，共享库 `pipeline/lib/`。stages/tools 里每个脚本顶部有 **path shim 三行**(把 `pipeline/` 加进 `sys.path`)，所以 `from lib.xxx import` 在任何子目录都解析得到 + sibling import(如 `from summarize_auto import`)靠脚本自身目录在 `sys.path[0]`。直接 `python3 pipeline/stages/<x>.py` 或经 run.py 调都成立。
- **打分/总结靠 `claude -p` 无头**(lib/claude.py;prompt 走 stdin、结果 stdout、脚本自己读写文件)。要加第二个模型(Codex 评审团)就照 `lib/claude.py` 复制成 `lib/codex.py`。
- 文件名用**论文标题 slug**（`papers.slug`），不是 DOI。DOI 仍是 `papers.id` 主键。
- **选篇靠 claude -p 相关性打分，不靠 API 排序**（OpenAlex 的相关性把引用量混进去了，会把高引但跑题的论文顶上来）。
- **不用 Google Scholar 批量**（无 API、强反爬）。
- 下载四级：先吃 OA → `recover_oa.py` 规则免费兜底（Unpaywall repository优先 + arXiv 版本枚举 + **DBLP 反查会议自营OA站** PMLR/ACL Anthology/OpenReview，2026-06-10 加,via=dblp-oa）→ `recover_agent.py` **agent 兜底**（claude -p 开 WebSearch/WebFetch 联网找合法免费 PDF，脚本负责下载校验落库；prompt 明令禁 Sci-Hub 类盗版源）→ 最后才 Tier B 付费墙。兜底层设计哲学：**撞到一类拉不下来的就固化一个新渠道**（同 tierb 的 findPdfUrl 出版商适配）。
- 批量下载要**限速**，别刷崩用户学校的访问 / 触发出版商风控。
- `claude -p` 偶尔撞 Max 限流失败 → 重跑该阶段即可（已总结/已打分的自动跳过;sum/score 幂等）。撞限流就调小并发：`python3 pipeline/stages/summarize_auto.py <id> 1`。

## 数据模型（db/papers.sqlite，5 表）
- `papers` 全局论文库：主键=规范化DOI；`slug`=文件名；`status`=discovered/pdf_downloaded/pdf_failed/summarized
- `topics` 研究主题（idea + 生成的 queries）
- `paper_topic` 论文×主题（relevance 分 + 理由 + rank）
- `summary_versions` 总结版本历史（version/path/based_on/note）
- `citations` 库内论文相互引用边

## 脚本清单（pipeline/，全 Python — 2026-06-15 起按职责分文件夹，见 `pipeline/ARCHITECTURE.md`）
**目录结构**（前门留根 / 主链进 stages / 旁路进 tools / 工具箱 lib）：
```
pipeline/
├─ run.py            ★唯一入口/总指挥(run auto 按序调 stages/)
├─ ask.py            ★出口①②公共API(全局 ~/.claude/CLAUDE.md 引它,路径不可动)
├─ run.sh / remote_view.sh
├─ stages/   主链 14 脚本(只被 run.py 调；每个文件顶部有 path shim 让 from lib 解析到 pipeline/lib)
│    discover, **score_auto**, commit, fetch_oa, recover_oa, **recover_agent**(hunt,agent联网猎免费源),
│    **fetch_tierb**, build_worklist, **summarize_auto**, register_summaries, render_topic,
│    **verify_summaries**(Codex 核查幻觉), **correct_summaries**(修正出 vN+1), **escalate_verify**(verify阶段驱动)
├─ tools/    旁路 11 脚本(手动跑,不在 run auto 链上)
│    init, migrate_slugs, notify, cross_topic, **audit_quality**, suggest_updates,
│    prepare_update, **update_auto**, register_updates, **export_corpus**(出口③:导ARS YAML), bot(Telegram对话bot)
└─ lib/      共享工具箱(不动)
     db, **log**(一等公民日志), http, sources, merge, store, slug, notify,
     **claude**(claude -p 调用器+并发池), **quality**(硬信号质量评估), **codex**(codex 调用器,跨模型第二引擎)
```
> ⚠️ 加新脚本：放 `stages/`(进主链,记得在 run.py 注册) 或 `tools/`(旁路)，从根目录复制 path shim 三行；公共/入口才放根目录。
> `score_auto`/`summarize_auto`/`update_auto` 用 `claude -p` 取代了旧的 Workflow agent。
> `fetch_tierb` = 方法④付费墙抓取（自启 Chrome→OpenAthens→人点验证→混合 B/A 抓 PDF）。
> 日志:每个脚本写 `logs/run.log`(机器日志,一行一事件) + `logs/pipeline-<date>.log`(详细);tierb 另有 `logs/tierb-<date>.log`。

其它命令：
```bash
python3 pipeline/stages/recover_oa.py <id>     # 免费补全(Unpaywall repository优先 + arXiv)
python3 pipeline/tools/suggest_updates.py <id> # (5b)建议哪些老总结该更新
python3 pipeline/tools/prepare_update.py <doi> # (5a)备更新 → python3 pipeline/tools/update_auto.py → register_updates.py
python3 pipeline/tools/cross_topic.py          # (6)跨主题（需≥2主题;自带全库引用边重建——commit 只建主题内的边）
python3 pipeline/tools/audit_quality.py <id>   # 质量审计:回查已入库论文(拉OpenAlex最新撤稿/DOAJ);--apply 移除block级
```

## 质量评价体系（硬信号，2026-06-09 上线；2026-06-10 改"标记优先"）
**不用 LLM，纯代码硬信号**（`lib/quality.py` + `config/quality/` 名单文件，可手工编辑追加）。**设计哲学（用户定）：能标记就不 ban——污染不发生在存进去，发生在用的时候忘了它是什么**，所以 verdict 持久化在 `papers.quality_tier/quality_signals`，每个下游出口都认标记：
- **block**（OpenAlex撤稿 / DOI前缀黑名单=亲手确认过的水刊）→ 死刑信号，discover 丢弃 + commit 双保险，**永不入库**。
- **suspect**（掠夺刊/出版商**名单命中**）→ **入库但带标记**（Beall's 有争议条目，全等匹配也可能偶撞）：commit 需 relevance≥45；**总结自动切"质疑模式"**（summarize_auto 注入批判指令：开头加警示行、结果写"作者声称"、≥5条质疑、主动找硬伤）；topic.md 表格标 ⚠️ + 单独"低可信来源"节；未来 RAG 默认过滤/降权；评审团重点审查对象。
- **trusted**（venue 白名单 / DOAJ 收录）→ 白名单 venue 免疫名单误杀。
- **flag**（纯预印本 / 无venue）→ commit 需 relevance≥`quality.flag_min_relevance`(默认45)；总结注一句"未经同行评审"。有正式 DOI(非10.48550)的不算预印本——OpenAlex 常把已发表论文 venue 标成 arXiv。
- 名单来源：Beall's 衍生 stop-predatory-journals（1309刊+1161出版商，**2017年停更，新水刊靠 `local_blocklist.txt`/`doi_prefix_blocklist.txt` 手工补**，IJISRT=10.38124 已收录）。
- 回溯审计：`audit_quality.py <id>` 拉 OpenAlex 最新撤稿/DOAJ → 出报告 `topics/<id>/quality_audit.md` + **verdict 回写 DB**（dry-run 也回写）；`--apply` 只删 block 级+重算 rank。2026-06-10 对 129 篇跑过：block=0 / suspect=0 / flag=34(全是真预印本) / trusted=36 / ok=59，标记已落库。

## 跨模型评审团（Codex，2026-06-10 上线；同日升级为质量闭环）
Codex CLI 已装并登录（ChatGPT 订阅,零 API 费;`lib/codex.py` = `codex exec --output-last-message`,镜像 lib/claude.py）。**Codex 永远没有否决权,只提异议/出报告**：
- **打分魔鬼代言人**（`quality.codex_panel`,**默认 false**）：score 阶段 Codex 专找"该拒"理由,异议进 `panel_objection`；commit 合议:边界分(<60)+异议=挡下。实测 3 篇试金石全对。**用户已拍板(2026-06-10):打分侧异议保持关,异议火力集中在总结侧。**
- **质量闭环（总结侧,已集成进 run auto 的 `verify` 阶段）**——核心:写的人(claude)和查的人(Codex)不是同一个模型:
  1. **核查** `verify_summaries.py <id> [pct] [并发] [--limit N]`:必核=suspect+修正过的(v≥2 未复核),其余按 pct 抽;Codex 对照原文(上限40万字符,截断时"核不到≠编造")核数字/论断;豁免元信息行+总结者评注("局限与我的质疑"里的判断)。**只出报告** → `summary_verification.md`;`topics/<id>/verified.json` 记"每篇核到哪个版本"。
  2. **修正** `correct_summaries.py [并发]`(读 `store/correction_worklist.json`):claude -p 拿**全文+当前总结+问题清单**重写 → vN+1 注册入 summary_versions,版本史保留;幂等。
  3. **升级阶梯** `escalate_verify.py <id> [--start-pct 10] [--threshold 10] [--max-rounds 6] [--max-attempts 2]`:抽样→fresh major率≥阈值→**自动修正 major+抽样翻倍**→循环至收敛/全量;修正过的下轮自动必复核;修 2 次仍 major 标"需人工分诊"。`--start-pct 100`=全量模式,即 run.py `verify` 阶段(新总结入库即全量核查)。
- **实测(topic2,2026-06-10)**:真实幻觉率 **~25% major**(两轮 32 篇抽出 8 篇:梯度方向写反/消融结论说反/"全部任务大幅超越"夸大等);修正闭环有效——9 篇修正后复核全部脱离 major(TD3/DAPG/Multimodal 等 pass;AFU 修 2 次到 v3)。minor 级("表述略强")不自动修,留报告存档。
- Codex 偶发限流/超时:panel 失败自动跳过;verify/escalate 重跑即可(verified.json 按轮落盘,进度不丢)。换机器需重新 `npm i -g @openai/codex` + `codex login`。

## Telegram 通知 + 对话 bot
- bot @research_agentffbot；配置在 `config/telegram.json`（**gitignore，不入库**；token 是密钥）。
- 基础层：`notify()` 一次性推送；`wait_for_reply()` 仅在一次运行卡住等用户时轮询。
- 用途：Tier B 登录/Duo 提醒、进度、报错。CLI：`python3 pipeline/tools/notify.py settoken|chatid|test`。
- **对话 bot（2026-06-10 临时升级，照 Stock_agent/daily-digest/bot.py 移植）**：`pipeline/tools/bot.py` 常驻长轮询，用户在 Telegram 上发任何话 → 转本机 `claude -p --resume`（opus、`--dangerously-skip-permissions`、cwd=仓库根，多轮记忆存 `logs/bot_session.txt`）；命令 `help`/`new`(清会话)/`log [N]`(看 run.log)。只认配置里的 chat_id。
  - 启动：`cd ~/Projects/Research_agent && setsid nohup python3 -u pipeline/tools/bot.py >> logs/bot.log 2>&1 &`；停：`kill $(cat logs/bot.pid)`。单例（bot.pid 活着就拒启）。**不随开机自启**——机器重启后要手动拉起。
  - ⚠️ 与 tierb 协作：bot 常驻时独占 getUpdates，所以每条消息落一份 `logs/bot_inbox.jsonl`；`wait_for_reply()` 检测到 bot 在跑（logs/bot.pid 进程活着）就改读 inbox 并写 `logs/bot_wait.json` 声明关键词，bot 对命中关键词的消息只转交不回 claude。bot 死了自动回退老的 getUpdates 轮询。
- 若换机器：`config/telegram.json` 不在仓库里，需要用户重新 `settoken` + `chatid`。

## 当前状态（截至 2026-06-15）
- **两个主题已建成**（跨主题比较的前提已具备）：
  - `rl-digital-human-interaction`（RL 训练可与环境交互的数字人）：**129 篇全已总结**（首测 34 篇后已放量）。
  - `rl-general-toolbox`（RL 通用工具箱）：**100 篇全已总结**。
  - 全库共 **221 篇**有总结（两主题约 8 篇重叠），summary_versions 分布：v1=202 篇 / v2=18 / v3=1。
- **总结核查流程刚升级（本会话重点）**：verify/correct 统一**以 PDF 为唯一原文来源**（commit 0d0ce64）、Codex **自渲染 PDF 看公式/图表**（26c3bb8），hunt/sum 加"张冠李戴"防线（b5dafc1/145c94a）。
  - 本会话正在**用新流程重跑两主题核查、与旧流程逐篇对比质量**（先备份旧产物+重置 verified.json→抽样验证 OK→待全量）。详见下文"跨模型评审团"节 + `logs/verify-baseline-20260615/`（旧核查 baseline 快照）。
  - 抽样实测：v2（旧流程已修正过的篇）仍被新流程揪出 major（"张冠李戴"型——把被引文献的数字论断安到本篇头上），说明新流程确有增量。
- **2026-06-09 大改造①：流水线全自动化**——打分/总结改 `claude -p`、付费墙固化成 `fetch_tierb`、`run auto` 一条龙。我(Claude)不再是运行时,只在搭建/调试时介入。
- **工作模式（用户 2026-06-10 定）：对话驱动，不解耦**。开新主题=用户来聊研究思路→讨论边界→我生成检索词**给用户过目确认**→建 topic.json→我起 `run auto` 后台跑+挂监控（盯日志、出问题修、汇报漏斗数据）。每周增量=用户说一句,我跑同一条命令盯完汇报。`claude -p` 是我调度的执行层,不是替代我。
- **2026-06-09 大改造②：整套从 Node/JS 迁移到 Python**(用户要长期维护、Python 生态更适合论文/PDF/未来语义过滤)。20 个 JS + run.sh 全部重写为 `pipeline/*.py`,JS 已删净;DB(`db/papers.sqlite`)原样复用。lib 加了 `log.py`(一等公民日志)。**唯一没在 Python 形态下端到端实跑的是 `fetch_tierb` 的浏览器抓取**(零件都验证过,下个付费墙主题盯一次)。
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

## 🌟 总蓝图（最 high level 的 idea，用户 2026-06-10 定稿）
三层架构，下层喂上层；做任何决策先对齐这个：
1. **论文自动下载+总结流水线**（已建成）：每周 `run auto`——多源发现→打分→四级取全文→中文总结→质量标记→Codex 核查修正。
2. **相互关联、有方便接口的知识库**（建设中）：SQLite 库 + 引用图 + 检索接口（`ask.py` FTS5 已有；向量/引用图扩展/合成知识层按需再上）。
3. **知识库的三个出口（按近→远）**：
   - ① **用户本人来查答案**——`ask.py "<问题>" --answer`（已有）。
   - ② **别的项目里的 agent 做任务卡住时来查**——`ask.py --json` 已有；但**全局 `~/.claude/CLAUDE.md` 发现机制指针 2026-06-16 已撤回**（ask.py 还没修好，先别让外部 agent 用上半成品），待就绪再把那节加回全局。
   - ③ **🎯 idea→论文流水线**——用 academic agent（`ref/academic-research-skills`，ARS，CC BY-NC）吃这个库，从研究想法走到论文成稿。**桥已建好(2026-06-10)**：`pipeline/tools/export_corpus.py <topicId|all> [--min-relevance N]` 导出 ARS Material-Passport `literature_corpus[]` YAML（严格对 schema：CSL 作者名、bibtex 风格 citation_key、无 year 拒绝不硬凑；quality_tier 走 tags+user_notes 出口标记；source_pointer 指本地 PDF；topic2 100 条实测过 schema 校验）。**设想流程**：用户给 idea → 流水线建主题攒语料(`run auto`) → `export_corpus` → ARS `academic-pipeline`(corpus-first,先吃我们的库、外搜补缺) → 研究报告/论文稿 → 引用的新论文回灌进库。**还没跑过一次真实 idea 全流程——那是终极验收,等用户回来一起试。** 注意:导出文件含摘要(版权),仅本地用勿外发。

## 待办 / 下一步
- ✅ **(2026-06-09 完成)** 4 篇全文+总结;`fetch_tierb` 固化;`score_auto`/`summarize_auto`(claude -p);`run auto` 一条龙;**整套迁移到 Python**;**修了 recover_oa**(arxiv/repository 优先 + 用 ext_ids.arxiv 不只靠标题)。
1. **端到端实跑验证 `fetch_tierb.py`**：本主题已无待抓篇,脚本只测过"无事可做"+语法+各零件(手动验证过)。下个有付费墙的主题要盯一次完整 tierb 跑(尤其 findPdfUrl 跨出版商、challenge 检测、混合 B/A 抓取)。
2. ✅ **(2026-06-09 完成,06-10 改"标记优先")文章评价/筛选体系——硬信号层**：`lib/quality.py` + `config/quality/` 名单 + discover/commit 双闸 + suspect 标记贯穿总结(质疑模式)/渲染(⚠️) + `audit_quality.py` 回溯审计（见上文"质量评价体系"节）。对 129 篇审计:block=0/suspect=0,标记已落库。
   - ✅ **(2026-06-10 完成,06-15 升级)跨模型评审团**：`lib/codex.py` + score 魔鬼代言人(`quality.codex_panel`,**用户 06-10 拍板保持关**,异议火力集中总结侧) + 总结核查闭环(`verify_summaries`→`correct_summaries`→`escalate_verify`)。**06-15 升级**:verify/correct 统一以 PDF 为唯一原文来源 + Codex 自渲染 PDF 看公式图表，见上文"跨模型评审团"节。
3. **继续放大主题规模**（两主题已各 129/100 篇；增量追加：topic.json 调 target → `python3 pipeline/run.py <id> auto`，commit 自动增量+重算 rank）。
4. ✅ **跨主题比较前提已具备**（现有 2 主题）：`python3 pipeline/tools/cross_topic.py`（自带全库引用边重建）。还没实跑过一次跨主题分析——待跑。
5. (小) claude -p 并发撞 Max 限流就调小 `sum`/`score` 的 concurrency 参数（默认 3/4）。
6. **🌟 大计划:把论文库变成"遇到问题就来查的知识库"(RAG over corpus)** —— 用户在别的 project 卡住时,让 agent 来这个库里检索答案。结论:**可行**(curated 语料+总结+PDF+引用图,RAG 底子好);**数据库大小不是瓶颈**(sqlite 只存元数据/摘要,原文在 store/pdfs 的 PDF;真正难点是"检索准不准")。
   - ⚠️ 检索层必须认 `papers.quality_tier`:suspect 默认过滤或降权+答案中显式标注来源可疑(质量体系 2026-06-10 起是"标记进库"不是"拒之门外",出口不过滤=污染答案)。
   - **落地路径(按性价比,分阶段)**:① 先做 **FTS5 全文搜 + `ask.py "<问题>"` 入口**(sqlite 内置,零依赖,curated 库里够用)→ ② 不够再上**语义向量**(嵌入总结,sentence-transformers 本地 或 嵌入 API + sqlite-vec)→ ③ **混合+claude -p 重排** → ④ **引用图扩展**(命中后顺 citations 拉邻居)→ ⑤ **两段式**(先总结层快筛、再对最相关几篇拉全文深读)。**别一上来堆向量,先 FTS5。**
   - **"持续学习"的正确理解**:不是微调模型(贵+脆+不值,RAG 完胜),而是三层让"语料变聪明":(a)语料每周增长;(b)**合成知识层**——定期 claude -p 把跨论文的方法/共识/矛盾/趋势蒸馏成主题笔记,= 一份活的文献综述(cross_topic.py 有雏形);(c)问答记忆,存过往结论别重推。检索时取用这三层。
   - 状态:**① 已落地(2026-06-10)**——`pipeline/ask.py "<问题>" [-n N] [--answer] [--reindex]`。索引=独立 `db/fts.sqlite`(gitignored,可随时重建,不碰生产库):fts_sum(trigram,标题+摘要+中文总结),按 mtime 增量。**(2026-06-16:英文全文索引 fts_text + store/text 已移除——总结都从 PDF 写,英文全文不再维护;检索只覆盖标题/摘要/中文总结,要原文细节直读 store/pdfs 的 PDF。)** 查询:英文取词+中文按停用词切段(≤4字精确短语,长段拆滑窗trigram,2字词 instr 全扫兜底——**FTS5 虚拟表上 LIKE 静默返回0,必须用 instr**)。出口认 quality_tier:suspect 减半+⚠️标注,flag 注"预印本"。`--answer`=claude -p 综合前5命中出带引用中文回答(实测会老实说"库里没有")。下一步看使用反馈再决定要不要 ②向量/④引用图。**主要用户是别的项目里的 agent**(用户定):他们做任务卡住时来查——`--json` 给机器可读结果(绝对路径,拿 summary_path/pdf_path 自己深读);发现机制=`~/.claude/CLAUDE.md`(全局,每个项目的会话都会载入)——⚠️ **2026-06-16 已撤回该指针节(ask.py 没修好,不放半成品给外部 agent),全局现只剩光头;ask.py 就绪后再加回。**
   - 顺带发现:Bipedal Robots(Reinforcement Learning for Robust Parameterized Locomotion Control)以两个 id 重复入库(slug `..._Bipedal_Robots` 和 `..._2`,两主题各自发现、merge 没合上),待去重。

详见 `logs/SESSION-*.md`（操作记录）和 `logs/run.log`（机器日志）。
