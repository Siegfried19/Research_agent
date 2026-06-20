# CLAUDE.md — 研究论文流水线（项目上下文 / 导航页）

> 换机器 / 新会话先读本文件（速查 + 铁律），详细内容按需跳 `claude-memory/`。
> 本机对话记忆不跨机器，要紧上下文全在仓库里（随 git）。

## 这个项目是什么
给一段研究思路 → 多源搜论文 → 下载全文 → 每篇 `claude -p` 写**中文**结构化总结 → 存进 SQLite 库。
支持每周增量、版本化更新、跨主题、引用图、付费墙(Tier B)、Telegram、知识库检索(RAG)。
用户 = NYU 研究者（中文交流，有图书馆订阅，每周跑 1–2 次）。全貌见 `claude-memory/ARCHITECTURE.md`。

## 怎么跑
全自动一条命令（打分/总结/核查走本机 claude/codex 无头，走订阅不花 API 钱）：
```bash
python3 pipeline/run.py <id> auto
# = discover→score→commit→fetch→recover→hunt→tierb→worklist→sum→finalize→verify
```
唯一需要人：tierb 遇 Cloudflare/Duo 验证会暂停 + Telegram 喊你点一下。
单跑某阶段调试：把 `auto` 换成上面任一阶段名。
- 夜间拆分：`auto-pull`（白天有人，含 tierb）/ `auto-sum-next [N]`（夜间 cron 无人，队列串行）；verify 由全天候 `tools/verify_daemon.py` 独啃。详见 `claude-memory/operation-maintenance/nightly-cron.md`。
- 新主题：建 `topics/<id>/topic.json`（id/title/idea/queries/window_years/target，可选 score_anchors）；检索词由你按用户思路生成、先给用户过目。
- 测试设 `RESEARCH_DB=/tmp/x.sqlite` 用临时库，不碰生产 `data-base/papers.sqlite`。

## 关键约定 / 坑（务必遵守）
- **运行环境** conda `research-agent`（入口 envguard 自动 re-exec；找不到回退 base/纯 FTS）。Python 3.10+ / stdlib sqlite3。
- **目录分层**：入口 run.py/ask.py 在 `pipeline/` 根；主链按段 `pipeline/{find,fetch,summarize,verify,retrieve}/`；旁路 `tools/`；共享库 `lib/`。每脚本顶部 path shim 三行。加新脚本规矩见 `claude-memory/ARCHITECTURE.md`。
- **打分/总结/核查靠无头 CLI**：`lib/claude.py`（写）+ `lib/codex.py`（查）。
- **选篇靠 claude 相关性打分，不靠 API 排序**（OpenAlex 把引用量混进相关性，高引跑题会被顶上来）。
- 文件名用 `papers.slug`，不是 DOI（DOI 是 `papers.id` 主键）。
- **不用 Google Scholar 批量**（无 API、强反爬）。下载四级、撞墙就固化新渠道；批量下载**限速**别刷崩学校访问。
- `claude -p`/codex 偶撞限流 → 重跑该阶段即可（幂等，已做的跳过）；撞限流调小并发。
- **git push 只用户来**（我只 commit、不 push）。

## 📌 文档落盘铁律（改完收尾必做，不等人催 —— 同全局口径）
做了实质改动就由 Claude 自己落盘：
- **改一个模块** → 把"改了啥/为什么/现在到哪/卡哪"写进 `claude-memory/modules-modification/<模块>/STATE.md` **顶部**（带日期+时间戳，**新在上、不删旧条**）。
- **改跨模块连接 / 全局** → 写 `claude_log.md`；在涉及的模块 STATE 顶部各留一行指针；连接设计沉淀到 `claude-memory/ARCHITECTURE.md` + 两边 README。
- **里程碑级改动** 照旧记 `claude_log.md`（全局铁律）。详细规矩见 `claude-memory/README.md`。

## 文档地图
| 要什么 | 去哪 |
|---|---|
| 整体框架 / 数据模型 / 脚本清单 / 模块连接 / 总蓝图 | `claude-memory/ARCHITECTURE.md` |
| 某模块设计（是什么/边界/为什么）| `claude-memory/modules-modification/<x>/README.md` |
| 某模块当前状态 / 在查的 bug / 历史 | `claude-memory/modules-modification/<x>/STATE.md` |
| 质量四档体系等横切设计 | `claude-memory/Prompt-structure-design/` |
| 运维：cron / 换机器 / 远程 / Telegram | `claude-memory/operation-maintenance/` |
| 改动时间线 | `claude_log.md` |

5 模块：find · fetch · summarize · verify · retrieve。
