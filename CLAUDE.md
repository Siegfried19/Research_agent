# CLAUDE.md — 研究论文流水线（给 Claude Code 的项目上下文）

> 换机器 / 新会话打开本仓库时**先读这个文件**，再看 `README.md`。
> 本机的对话记忆不会跨机器同步，所有要紧上下文都在仓库里。

## 这个项目是什么
给一段研究思路 → 多源批量搜论文 → 下载全文 → 每篇用一个子 agent 写**中文**结构化总结 → 存进 SQLite 库。
支持：每周增量跑、总结版本化更新、跨主题比较、库内引用关系、付费墙取全文(Tier B)、Telegram 通知。

用户：NYU 研究者（中文交流）。有学校图书馆订阅。每周想跑 1–2 次。

## 怎么跑一个主题（一键编排）
确定性阶段走 `pipeline/run.sh`，两个 **agent-workflow 步骤由 Claude（你）在阶段之间调用**：

```bash
bash pipeline/run.sh <id> discover     # 多源搜 → topics/<id>/candidates.json
bash pipeline/run.sh <id> scoreargs    # 清 scores、打印 score.workflow.js 的 args(JSON)
#   → 你调 Workflow(score.workflow.js, args=上面那串)  —— 相关性打分，滤掉高引但跑题的
bash pipeline/run.sh <id> commit       # 选篇写库（首跑 TopN / 增量追加 + 重算rank）
bash pipeline/run.sh <id> fetch        # 下载 OA 全文（含 arXiv 回退）
bash pipeline/run.sh <id> worklist     # 建总结清单
bash pipeline/run.sh <id> sumargs      # 打印 summarize.workflow.js 的 args(JSON)
#   → 你调 Workflow(summarize.workflow.js, args=上面那串)  —— 每篇一个 agent 写 v1.md
bash pipeline/run.sh <id> finalize     # 回写库 + 渲染 topics/<id>/topic.md
```

新主题：建 `topics/<id>/topic.json`（字段：id/title/idea/queries/window_years/target）。
**检索词(queries)由你根据用户给的研究思路生成**（多组英文关键词，覆盖不同侧面）。

## 关键约定 / 坑（务必遵守）
- 所有 node 脚本要加 **`node --experimental-sqlite`**（用内置 node:sqlite）。
- **Workflow 的 `args` 会以 JSON 字符串传入**，workflow 脚本里要 `JSON.parse(args)`（脚本顶部已处理）。直接 `args.x` 会拿到 undefined。
- 文件名用**论文标题 slug**（`papers.slug`），不是 DOI。DOI 仍是 `papers.id` 主键。
- **选篇靠 agent 相关性打分，不靠 API 排序**（OpenAlex 的相关性把引用量混进去了，会把高引但跑题的论文顶上来）。
- **不用 Google Scholar 批量**（无 API、强反爬）。
- 下载先吃 OA，再 `recover_oa.js`（Unpaywall+arXiv 兜底，免费），最后才 Tier B 付费墙。
- 批量下载要**限速**，别刷崩用户学校的访问 / 触发出版商风控。
- Workflow agent 偶尔遇 API 限流失败 → 重建 worklist 补跑即可（已总结的自动跳过）。

## 数据模型（db/papers.sqlite，5 表）
- `papers` 全局论文库：主键=规范化DOI；`slug`=文件名；`status`=discovered/pdf_downloaded/pdf_failed/summarized
- `topics` 研究主题（idea + 生成的 queries）
- `paper_topic` 论文×主题（relevance 分 + 理由 + rank）
- `summary_versions` 总结版本历史（version/path/based_on/note）
- `citations` 库内论文相互引用边

## 脚本清单（pipeline/）
init, discover, score.workflow, commit, fetch_oa, recover_oa, build_worklist,
summarize.workflow, register_summaries, render_topic, migrate_slugs, cross_topic,
prepare_update, update.workflow, register_updates, suggest_updates, notify, run.sh
lib/: db, http, sources, merge, store, slug, notify

其它命令：
```bash
node --experimental-sqlite pipeline/recover_oa.js <id>        # 免费补全(Unpaywall+arXiv)
node --experimental-sqlite pipeline/suggest_updates.js <id>   # (5b)建议哪些老总结该更新
node --experimental-sqlite pipeline/prepare_update.js <doi>   # (5a)备更新 → 你调 update.workflow.js → register_updates.js
node --experimental-sqlite pipeline/cross_topic.js            # (6)跨主题（需≥2主题）
```

## Telegram 通知（轻量、非常驻）
- bot @research_agentffbot；配置在 `config/telegram.json`（**gitignore，不入库**；token 是密钥）。
- 设计：`notify()` 一次性推送；`waitForReply()` 仅在一次运行卡住等用户时轮询。**没有守护进程**，跑完就停。
- 用途：Tier B 登录/Duo 提醒、进度、报错。CLI：`node pipeline/notify.js settoken|chatid|test`。
- 若换机器：`config/telegram.json` 不在仓库里，需要用户重新 `settoken` + `chatid`。

## 当前状态（截至 2026-06-08）
- 主题 `rl-digital-human-interaction`（强化学习训练可与环境交互的数字人），首测停在 target=40。
- **40 篇命中 / 30 篇已总结**（1 篇有 v2）/ 13 条引用边。
- **剩 10 篇付费墙待取**（5 篇 403含AMP/ASE/Walk This Way + 5 篇非OA）→ Tier B。

## 待办 / 下一步
1. **Tier B 付费墙取全文**（最优先，需和用户一起实操建）：
   - 用 opencli(@jackwener/opencli，已装) 驱动用户**登录好的 NYU Chrome**（专用 profile、存密码、Duo 用户自己点）。
   - 流程：你启动→Telegram 通知用户→用户处理 Duo→会话探测+断点续传取 PDF。
   - 取 PDF 的具体手段（opencli 拿 cookie 后 node 直下，还是页内下载）**要拿一篇真实 NYU 付费论文边试边定**——别盲写。
   - 需用户给：NYU 代理前缀格式（config.json 的 `tier_b.proxy_login_template` 占位，待确认）；`opencli doctor` 扩展连上。
   - AMP/ASE 的 `papers.title` 被 OpenAlex 缩成了"AMP"/"ASE"，恢复/匹配时注意。
2. **放大到 200**（把 topic.json 的 target 改 200，重跑 run.sh 全流程；commit 增量追加）。
3. 跨主题比较需要先有第 2 个主题。

详见 `logs/SESSION-*.md`（操作记录）和 `logs/run.log`（机器日志）。
