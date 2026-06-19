# Claude Log — Research_agent

> Claude 在本项目所做改动的时间线总账（最新在最上面）。每条带日期时间。
> 约定见全局 `~/.claude/CLAUDE.md`：做了实质改动就记，不等人催。
> 更丰富的来龙去脉见 `logs/SESSION-*.md`；机器流水账见 `logs/run.log`。本文件 = 雷打不动的改动账本。

## 2026-06-18 19:45 EDT — 实现方案A：claude 问题理解层（治 P-A/P-B 分词 bug）
- 新文件 `pipeline/retrieve/understand.py` → `understand_query(q)`：claude -p 把问题 → `{en_terms, zh_terms, hyde}`（展开缩写 + 中英双语词 + 2-4句 HyDE 假想答案）。失败/解析不出返回 None，调用方自动回退老的 parse_query。
- `search.py`：新增 `terms_to_fts()`（claude 的干净词当原子短语，≥3字进 MATCH、<3字进 instr 兜底，**不再回炉 parse_query**）；`fts_rank`/`vec_rank`/`hybrid` 各加 `understanding` 形参——FTS 那路用干净词、向量那路嵌 **HyDE 文本**（而非光问题）。
- `ask.py`：默认对所有查询先过理解层；加 `--no-understand` 逃生口；`--json` 输出带 `understanding`（外部 agent 可看自己问题被理解成啥）。
- **实测 A/B（隔离 FTS 那路）**：机械分词 vs 理解层命中——`RL` 0→194、`AI ML 的应用` 0→179、`通用工具箱` 22→182；端到端 ask.py 命中全是高相关篇（48–96分）；`--no-understand` 老路+回退均正常。
- ⚠️ **遗留待办（用户 2026-06-18 明确「先不担心、但要记下」）**：每次 deep 查询都多 1 次 claude（几秒+token）；外部 agent 若高频轮询本库会偏重。**当前决定：默认全开、不加节流/缓存**。日后若 agent 用量大，再考虑（缓存 understanding / 给 agent 路径加节流 / 让简单查询跳过）。详见 `logs/SESSION-2026-06-18-kb-retrieval.md` 第四段。

## 2026-06-18 19:31 EDT — 检索第1步审查结论 + 拍板上方案A（commit 7709438，交接日志）
- 逐段审查问答 pipeline：第1步混合召回（`search.hybrid`）结构对/无截断/不调 claude，但坐实 `parse_query` 两个真分词 bug——P-A（2字母英文缩写如 "RL" 被正则丢弃）、P-B（单字停用词子串替换把中文复合词如"通用/应用"劈碎）。
- 用户拍板：上**方案A = 检索前加 claude 问题理解层**（展开缩写 + 中英双语词 + HyDE），根治 P-A/P-B；Qwen/FTS 保留当工具。agentic 方案B（④引用图/⑤两段式）留后面，A 是 B 的零件不浪费。
- 方案A 完整待实现设计 + 路线图 + 后续 P1/P2 → `logs/SESSION-2026-06-18-kb-retrieval.md` 第三段。本条为漏记补登。

## 2026-06-18 19:16 EDT — 检索第0步（建索引）优化（commit 35bfb2c）
- 嵌入上限 16384→24576（实测显存峰值留余量 + `expandable_segments` 防碎片 + CPU 兜底；问答零影响，坐标不变）。
- 索引增量改**两段钥匙**（新 `retrieve/freshness.py`，fts+vec 共用）：便宜钥匙 md5(title+abstract+path+mtime) 不读文件秒跳，vec 钥匙变了才读全文算 body_hash 精确确认；+busy_timeout + 孤儿回收 + 旧 meta schema 自动迁移。全验证过。本条为漏记补登。

## 2026-06-18 19:11 EDT — 定 claude_log 用单文件（不做文件夹）
- 决定：claude_log 用单个 `.md`，不做成文件夹——append-only 时间线单文件最好扫/grep，纯文本几千条也才几百 KB；只有单文件真臃肿了才按年归档进 `claude_log/<年>.md`（YAGNI，现在不做）。
- 文件：全局 `~/.claude/CLAUDE.md` 补了这条说明。

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
