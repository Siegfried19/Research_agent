# 换机器迁移 — 记忆分布地图 + 迁移清单

> 整合自 `change-device/MIGRATION.md` + `change-device/README.md`（2026-06-20 搬进 ops/）。
> 用户关切（2026-06-10）："你的记忆在哪？换机器了怎么办？" 本文件是权威答案。
> **定档迁移方式（2026-06-17）：本地跑、整目录搬。** 以后每次换机器都按本文走。

## 原则：要紧上下文都在仓库里

**项目文件夹是自包含的。** 代码、PDF 全文、密钥、SQLite 库、检索索引、以及 agent 记忆快照都在 `Research_agent/` 这个目录里。换机器 = **把整个目录拷过去**，仓库外只剩"软件环境 + CLI 登录"要单独装。

> 记忆/文档的新分层（2026-06-20 重构）：项目知识全归 **`claude-memory/`**（`CLAUDE.md`=导航+铁律、`claude-memory/ARCHITECTURE.md`=全局框架、`claude-memory/modules-modification/<x>/`=各模块设计+状态、`claude-memory/Prompt-structure-design/`=横切深度长文、`claude-memory/operation-maintenance/`=运维、`claude_log.md`=改动时间线），随 git、跨机器。**不再是"CLAUDE.md 唯一权威"的旧说法。** harness 的 agent 记忆（`~/.claude/projects/.../memory/`）只管"怎么跟用户协作"（工作风格/评审节奏等），不存项目知识，不跨机器。

## 一、记忆分布地图（什么在哪）

| 层 | 位置 | 跨机器? | 说明 |
|---|---|---|---|
| **项目知识/文档** | `claude-memory/` + `CLAUDE.md`（本仓库） | ✅ 随 git | 蓝图/约定/坑/各模块状态。新机器开会话先读 `CLAUDE.md`（导航），再循图进 `claude-memory/` |
| 改动时间线 | `claude_log.md`（本仓库） | ✅ 随 git | append-only 总账，回溯"何时动了什么" |
| 各模块状态/历史 | `claude-memory/modules-modification/<x>/STATE.md`（本仓库） | ✅ 随 git | 层积日志：顶=现状、往下翻=历史（取代旧 `logs/SESSION-*.md`，已并入）|
| 机器日志 | `logs/run.log`（本仓库） | ✅ 随 git | 一行一事件；**起长任务前先看它，确认没有别的实例在干同一件事** |
| harness agent 记忆 | `~/.claude/projects/-home-siegfried-Projects-Research-agent/memory/` | ❌ 不同步 | 只管"怎么跟用户协作"（工作风格/评审节奏）。机器本地、可重建，**不再在仓库存快照**（项目知识已全在 `claude-memory/`）|
| 全局 agent 提示 | `~/.claude/CLAUDE.md` | ❌ 不同步 | 知识库发现机制（让别的项目/机器的 agent 知道 ask.py）。当前用户选择**不弄**（见远程访问 `remote-access.md`） |
| 元数据/引用图 | `data-base/papers.sqlite` | ✅ 随 git（已跟踪） | 论文元数据/状态/引用图。换机器前 commit 才带最新 |
| 论文实体（一篇一个家） | `storage/papers/<slug>/`（~1.3GB，含 `paper.pdf` + `vN.md` 各版本总结 + `verify.json` 核查详情） | ❌ 大头 PDF gitignored（版权） | 不随 git。整目录拷（cp -a / tar）会带全部；clone 式只拿代码骨架，全文要对缺 PDF 论文重跑 `fetch/recover/hunt/tierb` 按 DB 元数据重建 |
| 检索索引 | `data-base/fts.sqlite` + `data-base/vec.sqlite` | ❌ gitignored | 可重建：`python3 pipeline/ask.py --reindex`（FTS）/ `run <id> index`（向量增量） |
| 大依赖 | `dependencies/`（模型 ~1.2GB + noVNC） | ❌ gitignored | `models/` 嵌入模型缓存（`lib/embed.py` 经 HF_HOME 钉好，首次自动下载）；`novnc/` 远程看屏前端 |

> ⚠️ 实际记忆目录的 slug 是 `-home-siegfried-Projects-Research-agent`（`/` 和 `_` 都换成 `-`）。

## ⚠️ 三条铁律（整目录搬）

1. **整目录拷，别 `git clone`。** clone 会漏掉所有 gitignore 的东西：`storage/papers/`（PDF 全文）、`data-base/fts.sqlite`/`data-base/vec.sqlite`（索引）、`dependencies/`（嵌入模型 + noVNC）、`ref/`、`config/*.json`（密钥）。整目录 `cp -a` / `tar` 不会漏。
2. **新机器文件系统用 ext4**（别用 exFAT/NTFS）：项目重度用 SQLite+WAL，非 Linux 文件系统上会锁不住、写坏库；密钥的 `-rw-------` 权限也会丢。
3. **拷之前确认没人在写**（cron 没在跑、没有正在跑的总结/核查、verify_daemon 已停），否则 SQLite 拷到一半会坏。

## 二、迁移步骤

### A. 老机器（搬出前）

1. **停写**：确认 cron 没在跑、没有正在跑的 pipeline、verify_daemon 已停（`kill $(cat logs/verify_daemon.pid)`）；看一眼 `logs/run.log` 确认没别的实例。
2. **（可选）记关键工作偏好**：harness agent 记忆只是工作风格偏好、机器本地不随仓库；要紧的话开会话时口头补给新机器、或让它重新积累（项目知识本就全在 `claude-memory/`，不依赖它）。
3. **打包整目录**：
   ```bash
   cd ~/Projects
   tar -czf research_agent.tar.gz Research_agent/
   # 或拷到移动硬盘： cp -a Research_agent /media/<盘>/
   ```
4. **（可选）云端备份**：`git add -A && git commit && git push`（代码+总结+记忆快照进 GitHub；PDF 因版权不入 git，只在本地/硬盘）。⚠️ push 由用户做。

### B. 新机器（落地）

1. **解包到新位置**（路径**可以变**——仓库内 0 处写死 `/home/siegfried` 绝对路径，代码用相对路径 + `~` + 按环境名探测）。落在 **ext4** 分区上。
   ```bash
   tar -xzf research_agent.tar.gz -C ~/Projects/
   ```
2. **装软件环境**：
   - **conda 环境 `research-agent`**：`conda env create -f environment.yml`（一键重建，含 GPU torch / sentence-transformers / sqlite-vec + requests）。检索向量路必须 GPU（CPU 慢 ~100×）。
   - `poppler-utils`（`pdftotext` / `pdfinfo`，总结/手动加 PDF 用）、Google Chrome（Tier B）。
   - **Node 22+**（codex CLI / Tier B opencli 用；本机基线 v24.16）。
3. **登录 CLI**（打分/总结/核查全靠它们，零 API 费）：
   - `claude`（Claude Code, Max 订阅）登录
   - `npm i -g @openai/codex && codex login`（ChatGPT 订阅）
   - `npm i -g @jackwener/opencli`（Tier B 抓取用，可选）
4. **agent 记忆**：无需回灌——项目知识全在 `claude-memory/`（随目录已带）。harness 记忆只是工作风格偏好、机器本地，新机器上自然重新积累即可。
5. **密钥**：随目录过来（`config/telegram.json`、`config/x11vnc.*`），不用动。确认权限仍是 `-rw-------`（ext4 才保得住）。telegram 若要重配见 `telegram.md`。
6. **数据库 + 索引**：随目录过来，**不用 reindex**。万一索引坏了：`python3 pipeline/ask.py --reindex`。
7. **Tier B 浏览器**（可选，付费墙抓取）：装 opencli + 浏览器扩展；Chrome 抓取 profile = **独立目录 `~/.config/google-chrome-scrape-nyu` 的 "Profile 2"**（2026-06-17 起，与 Stock_agent 的 `google-chrome-scrape` 物理隔离，可同跑不互杀）。需**登录一次 NYU**：在该 profile 里开 `https://library.nyu.edu` 用 NetID+Duo 登主图书馆（**别走 `go.openathens.net/redirector/nyu.edu` 默认入口——会跳医学院 Langone 独立 SSO，常规 NYU 账号登不了**；shibboleth 会话建好后 tierb 首次走 OpenAthens redirector 会自动复用）。再在该 profile 登一下启用 OpenCLI 扩展。`opencli doctor` 见 "Extension: connected" 即成。
8. **重建 cron（如需夜间自动跑）**：crontab **不在仓库里、写死了路径**，必须在新机器重写。步骤 + cron 行 + 干净环境 PATH 坑 → `nightly-cron.md`，注意把路径和 `PATH=` 里的 node 目录改成新机器的。
9. **（出口③用到再做）** `git clone https://github.com/Imbad0202/academic-research-skills reference/academic-research-skills`（gitignored，CC BY-NC）。
10. **封存件（默认不装）**：手机过验证 remote_view 需要 x11vnc/websockify/`dependencies/novnc` + 密钥重新生成——见 `remote-access.md`。

### C. 明确不迁移 / 按需

- **全局钩子** `~/.claude/CLAUDE.md`（知识库发现机制）：用户选择**不弄**（跳过）。代价：别的项目卡住时不会自动来查论文库，得手动跑 `ask.py`。要启用见 `remote-access.md`。
- **Tier B 浏览器抓取、手机过验证（remote_view）** 等封存件：按需再装。

### D. 落地后自检

```bash
python3 pipeline/ask.py "测试一个关键词" --json -n 3   # 知识库能查 = 库+索引+环境 OK
# 抽查一篇总结能打开；storage/papers/*/paper.pdf 的数量与 db 元数据大致对得上
```

## 相关文件

- `claude-memory/operation-maintenance/nightly-cron.md` —— 换机器后夜间自动跑的部署。
- `claude-memory/operation-maintenance/telegram.md` —— Telegram 通知/对话 bot 重配。
- `claude-memory/operation-maintenance/remote-access.md` —— 让别的机器/项目来查库（SSH 远程）+ 手机过验证封存件。
- `CLAUDE.md` / `claude-memory/README.md` —— 文档地图入口。
</content>
