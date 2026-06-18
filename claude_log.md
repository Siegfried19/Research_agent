# Claude Log — Research_agent

> Claude 在本项目所做改动的时间线总账（最新在最上面）。每条带日期时间。
> 约定见全局 `~/.claude/CLAUDE.md`：做了实质改动就记，不等人催。
> 更丰富的来龙去脉见 `logs/SESSION-*.md`；机器流水账见 `logs/run.log`。本文件 = 雷打不动的改动账本。

## 2026-06-18 19:06 EDT — 立 claude_log 约定 + 补记今日改动
- 用户拍板：所有项目都要有 `claude_log.md`，做改动就记、带日期时间。落约定到全局 `~/.claude/CLAUDE.md`，本项目建此文件并补记今天三件事（下方）。
- 文件：新建 `~/.claude/CLAUDE.md`（全局约定）、本 `claude_log.md`；另存一条本项目 feedback 记忆。

## 2026-06-18 18:53 EDT — 建 prompt 总账 + 修过期文档 + 移 MIGRATION.md（commit b5713f4）
- 新增 `docs/prompts.md`：prompt「导航地图 + 演变史」，定位 map+changelog 而非镜像（代码为准，防漂移）。覆盖打分/总结/核查三件套当前写法 + 演变史，链到 SESSION/commit。
- `docs/summary-prompt-rewrite-plan.md`：状态头「待执行」→「✅已落地」，标注内嵌 prompt 是历史草稿、现行以代码为准。消除误导源。
- `git mv MIGRATION.md → change-device/MIGRATION.md`，同步更新 6 处引用。

## 2026-06-18 18:44 EDT — 清死代码 + 扔核查实验残留目录（commit f570799）
- `cross_topic.py`：去掉 `new_edges` 死赋值（pyflakes 揪出的唯一真死代码）。
- 删 06-15/06-17「新旧核查流程对比」实验残留：`git rm logs/verify-baseline-20260615`（1.1M）+ `rm` 3 个本地 untracked 实验目录（~7.6M）。
- 体检结论：其余可疑项（codex re-export、注释里已删模块名、db.text_path 列、remote_view 封存、tools/ 手动入口）均查证为有意保留。

## 2026-06-18 18:13 EDT — 全流程统一跑 research-agent 环境（envguard 自动纠偏；commit 8b6c0de 代码 + 257c928 文档）
- 新增 `pipeline/lib/envguard.py`，`run.py`/`ask.py` 顶部调 `ensure_env()`：不在 research-agent 环境就用其 python 自动 re-exec 自己（bash/python3/cron/bot 任意方式起都自纠偏；按环境名探测不写死路径；逃生口 `RESEARCH_NO_REEXEC=1`）。主链 13 脚本未动（经 sys.executable 继承）。
- 实测：base 强制 re-exec 通过 + 逃生口生效 + ask.py 落地真走向量检索。
- `CLAUDE.md` 运行环境节同步（去掉冗余 HF_HOME 前缀，标注自动纠偏）；run.log 补 ENV-UNIFY 里程碑。
