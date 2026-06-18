# MIGRATION.md — 记忆分布地图 + 换机器清单

> 用户关切(2026-06-10):"你的记忆在哪?换机器了怎么办?" 本文件是权威答案。
> 原则:**一切要紧上下文必须在仓库里**(CLAUDE.md 为主),仓库外的东西要么可重建、要么在下面清单里。

## 一、记忆分布地图(什么在哪)

| 层 | 位置 | 跨机器? | 说明 |
|---|---|---|---|
| **项目交接文档** | `CLAUDE.md`(本仓库) | ✅ 随 git | **唯一权威**。蓝图/约定/坑/状态全在这。新机器开会话第一件事就是读它 |
| 会话操作记录 | `logs/SESSION-*.md`(本仓库) | ✅ 随 git | 每条会话线一份,出问题回溯用 |
| 机器日志 | `logs/run.log`(本仓库) | ✅ 随 git | 一行一事件;**起长任务前先看它,确认没有别的实例在干同一件事** |
| Claude 项目记忆 | `~/.claude/projects/-home-siegfried-Projects-Research_agent/memory/`* | ❌ 不同步 | agent 的跨会话记忆(蓝图/用户偏好/工作模式)。**只是 CLAUDE.md 的影子**——任何只存在于记忆里的要紧事都该提升进 CLAUDE.md |
| 全局 agent 提示 | `~/.claude/CLAUDE.md` | ❌ 不同步 | 知识库发现机制(让别的项目的 agent 知道 ask.py)。内容见下方附录,换机器照抄重建 |
| 元数据/引用图 | `db/papers.sqlite` | ✅ 随 git(已跟踪) | 论文元数据/状态/引用图。换机器前 commit 才带最新;否则只到上次 push |
| 中文总结全文 | `store/summaries/` | ⚠️ **当前未跟踪**(2026-06-17 核实:git 跟踪 0 文件) | **不随 git!** 整盘拷(rsync -a/cp -a)会带;**clone 式迁移必须单独拷**,否则只剩元数据没总结。老基线 `logs/wipe-summaries-20260617/`(gitignored)同理 |
| 全文/PDF | `store/pdfs/` | ❌ gitignored(版权) | 不随 git。整盘拷会带;clone 式可对缺全文论文重跑 `fetch/recover/hunt/tierb` 按 DB 元数据重建 |
| 检索索引 | `db/fts.sqlite` | ❌ gitignored | 可重建:`python3 pipeline/ask.py --reindex` |

\* 实际路径 slug 为 `-home-siegfried-Projects-Research-agent`。

## 二、换机器清单(按顺序)

1. **克隆仓库**,读 `CLAUDE.md`。
2. **系统依赖**:Python 3.10+、`pip install requests`、`poppler-utils`(pdftotext)、Google Chrome。
3. **登录两个 CLI**(打分/总结/核查全靠它们,零 API 费):
   - `claude` (Claude Code, Max 订阅) — `claude` 登录;
   - `npm i -g @openai/codex && codex login` (ChatGPT 订阅)。
4. **Telegram**(可选,通知/对话 bot):`python3 pipeline/tools/notify.py settoken` + `chatid`(`config/telegram.json` 是密钥,不在 git)。
5. **Tier B 浏览器**(可选,付费墙抓取):装 opencli + 浏览器扩展;Chrome 抓取 profile = **独立目录 `~/.config/google-chrome-scrape-nyu` "Profile 2"**(2026-06-17 起,与 Stock_agent 的 `google-chrome-scrape` 物理隔离,可同跑不互杀)。需重建并**登录一次 NYU**:在该 profile 里开 `https://library.nyu.edu` 用 NetID+Duo 登主图书馆(**别走 `go.openathens.net/redirector/nyu.edu` 默认入口——会跳医学院 Langone 独立 SSO,常规 NYU 账号登不了**;shibboleth 会话建好后 tierb 首次走 OpenAthens redirector 会自动复用)。还要在该 profile 登一下以启用 OpenCLI 扩展。`opencli doctor` 见 "Extension: connected" 即成。
6. **重建全局发现机制**:`~/.claude/CLAUDE.md` ← 照本文附录 A 抄。
7. **重建可重建物**:`python3 pipeline/ask.py --reindex`(FTS 索引);缺全文的话按主题重跑下载各阶段。
8. **(出口③用到再做)** `git clone https://github.com/Imbad0202/academic-research-skills ref/academic-research-skills`(gitignored,CC BY-NC)。
9. **封存件(默认不装)**:手机过验证 remote_view 需要 x11vnc/websockify/`vendor/novnc` + 密钥重新生成——见 CLAUDE.md"手机过验证"节。
10. **(常开机器自动跑)夜间 cron 部署**:整套要在一台常开机器上半夜自动跑(白天留 token 给用户),部署步骤 + cron 行 + 干净环境的 PATH 坑 → 见 **`docs/nightly-cron-deploy.md`**(`run.py` 的 `auto-pull` 白天有人那半 / `auto-sum` 夜间无人那半)。

## 附录 A — `~/.claude/CLAUDE.md` 全文(全局发现机制,照抄)

```markdown
# 全机器共享提示

## 论文知识库（卡住了先来查）
本机有一个持续维护的研究论文库（~230 篇 RL/数字人/安全RL/奖励设计等主题，中文结构化总结+英文全文，每周增长）。
**做任务遇到算法/方法/文献问题时，先查它再上网搜**：

​```bash
python3 ~/Projects/Research_agent/pipeline/ask.py "<问题或关键词>" --json -n 5
​```

- 返回 JSON：每条带 `summary_path`（中文总结，先读这个）和 `text_path`（英文全文，要细节再读）。
- `quality_tier` 字段：`suspect`=可疑来源慎引用；`flag`=预印本未经同行评审。
- 中英文混合查询都行；没命中会返回空 `hits`，再换关键词或上网搜。
```
