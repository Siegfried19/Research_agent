# change-device —— 换机器迁移流程（整目录文件迁移）

> 定档(2026-06-17)：**本地跑、整目录搬**。以后每次换机器都按本文走。
> 更详细的背景/记忆分布地图见 `MIGRATION.md`（注意其中"总结未入 git"一条**已过时**——总结现已随 git）。

## 一句话原理
**项目文件夹是自包含的。** 要紧的东西全在 `Research_agent/` 这个目录里——代码、PDF 全文、密钥、SQLite 库、检索索引、以及 agent 记忆快照（`docs/claude-memory/`）。所以换机器＝**把整个目录拷过去**就行；仓库外只剩"软件环境 + CLI 登录"要单独装。

## ⚠️ 三条铁律（先记住）
1. **整目录拷，别 `git clone`。** clone 会漏掉所有被 gitignore 的东西：`store/pdfs/`(1.3GB 全文)、`db/fts.sqlite`(索引)、`ref/`、`vendor/`。整目录 `cp -a` / `tar` 不会漏。
2. **新机器文件系统用 ext4**（别用 exFAT/NTFS）：项目重度用 SQLite+WAL，非 Linux 文件系统上会锁不住、写坏库；密钥的 `-rw-------` 权限也会丢。
3. **拷之前确认没人在写**（cron 没在跑、没有正在跑的总结），否则 SQLite 拷到一半会坏。

---

## A. 老机器（搬出前）
1. **停写**：确认 cron 没在跑、没有正在跑的 pipeline；看一眼 `logs/run.log` 确认没别的实例。
2. **刷新记忆快照**（重要，快照是手动的、不会自动同步最新）：
   ```bash
   cp -a ~/.claude/projects/-home-siegfried-Projects-Research-agent/memory/*.md \
         docs/claude-memory/
   ```
   （`docs/claude-memory/README.md` 是说明文件，别被覆盖。）
3. **打包整目录**：
   ```bash
   cd ~/Projects
   tar -czf research_agent.tar.gz Research_agent/
   # 或直接拷到移动硬盘： cp -a Research_agent /media/<盘>/
   ```
4. **(可选) 云端备份**：`git add -A && git commit && git push`（代码+总结+记忆快照进 GitHub；PDF 因版权不入 git，只在本地/硬盘）。

## B. 新机器（落地）
1. **解包到新位置**（路径**可以变**——已确认仓库内 0 处写死 `/home/siegfried` 绝对路径，代码用相对路径+`~`）。落在 **ext4** 分区上。
   ```bash
   tar -xzf research_agent.tar.gz -C ~/Projects/
   ```
2. **装软件环境**：
   - Python 3.10+，`pip install requests`
   - **Node 22+**（脚本用 `node --experimental-sqlite`，本机基线 v24.16）
   - `poppler-utils`（`pdftotext`/`pdfinfo`）、Google Chrome
3. **登录两个/三个 CLI**（打分/总结/核查全靠它们，零 API 费）：
   - `claude`（Claude Code, Max 订阅）登录
   - `codex login`（ChatGPT 订阅，`npm i -g @openai/codex`）
   - `opencli`（`npm i -g @jackwener/opencli`，Tier B 抓取用，可选）
4. **回灌 agent 记忆**（让新机器 agent 不"失忆"）：
   ```bash
   # 先在项目目录里开一次 claude，让它在 ~/.claude/projects/ 下生成本机的 slug 目录
   # slug = 新项目绝对路径把 / 和 _ 都换成 -
   NEWSLUG=$(pwd | sed 's#/#-#g; s#_#-#g')   # 在项目根目录执行
   mkdir -p ~/.claude/projects/$NEWSLUG/memory
   cp -a docs/claude-memory/*.md ~/.claude/projects/$NEWSLUG/memory/
   rm -f ~/.claude/projects/$NEWSLUG/memory/README.md   # 这是说明，不是记忆条目
   ```
   （或者干脆不回灌，靠 `CLAUDE.md`＋这份快照当文档读也行。）
5. **密钥**：已随目录过来（`config/telegram.json`、`config/x11vnc.*`），不用动。确认权限仍是 `-rw-------`（ext4 才保得住）。
6. **数据库 + 索引**：随目录过来，**不用 reindex**。（万一索引坏了：`python3 pipeline/ask.py --reindex` 可重建。）
7. **重建 cron（如需夜间自动跑）**：crontab **不在仓库里、且写死了路径和 nvm 的 node 路径**，必须在新机器重写。步骤见 `../docs/nightly-cron-deploy.md`，注意把路径和 `PATH=` 里的 node 路径改成新机器的。

## C. 明确不迁移 / 按需的东西
- **全局钩子** `~/.claude/CLAUDE.md`：用户选择**不弄**（跳过）。代价：别的项目卡住时不会自动来查论文库，得手动跑 `ask.py`。
- **Tier B 浏览器抓取、手机过验证(remote_view)** 等封存件：见 `MIGRATION.md` / `../CLAUDE.md`，按需再装。

## D. 落地后自检
```bash
python3 pipeline/ask.py "测试一个关键词" --json -n 3   # 知识库能查 = 库+索引 OK
# 抽查一篇总结能打开、store/pdfs 里 PDF 数量与 db 元数据大致对得上
```
