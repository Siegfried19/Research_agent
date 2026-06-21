# Claude Log — Research_agent

> Claude 在本项目所做改动的时间线总账（最新在最上面）。每条带日期时间。
> 约定见全局 `~/.claude/CLAUDE.md`：做了实质改动就记，不等人催。
> 更丰富的来龙去脉见 `claude_memory/modules-modification/<x>/STATE.md`（各模块层积日志，取代旧 logs/SESSION-*.md）；机器流水账见 `logs/run.log`。本文件 = 雷打不动的改动账本。

## 2026-06-21 00:39 EDT — fetch 失败兜底定稿 + facet 入库（跨 db/find/fetch/retrieve）
- **缘由**：和用户逐步对齐 fetch 失败处理。先评估出 **fetch 几乎不失败**（生产库 `pdf_failed=0`，历史只 PPG/Lazy Agents 1 次已修），于是把早先设想的"diagnose 失败分类 agent"整个砍掉，只留极简兜底；另按用户要求把 facet 落库供 retrieve 用。
- **做了什么**：
  - `lib/db.py`：`paper_topic` 加 `facet TEXT`（写进 CREATE TABLE + `ADD_COLUMNS`，`open_db` 自动迁移生产库，无需手敲 ALTER）。
  - `lib/store.py`：`set_paper_topic` 从 `p.get('facet') or '_all'` 落 facet + ON CONFLICT 更新。`commit.py` 调用处未改（传的 `p` 本就带 discover 标的 facet）。
  - `pipeline/run.py`：加 `failed` 子命令（`report_failed`）——SQL 列出没拿到全文的篇（标题/id/slug/DOI/落地页），只报"是哪篇"，全拿到输出 ✅。
  - **手动挂 PDF（⑥）不写工具**：失败篇的库行已在，挂载=拷文件+翻 status，需要时叫 agent 用 SQL 现办。
  - **回填**：agentic-knowledge-synthesis 38 行从 `candidates.json` 回填 facet（全匹配，5 facet 分布）；两老主题 229 行归一 `_all`；全库 267 行无 NULL。
- **验证**：py_compile（db/store/run）过；临时库端到端（facet 写/缺省/ON CONFLICT）过；`failed` 双场景实测过。
- **文件**：`pipeline/lib/{db,store}.py`、`pipeline/run.py`、生产库 `data-base/papers.sqlite`（迁移+回填）；文档 fetch README/STATE、find/retrieve STATE 指针。**未 push（待用户）。**

## 2026-06-20 22:48 EDT — TODO-6 验证收口:修两个 bug(orchestrator挂后台 / commit不豁免seed)+ 清 3 偏题
- 接上一条(orchestrator 自报的 19:54 实跑)。验证**成功**——6 奠基作全回库(GraphRAG 首轮被切、这次 rel=95 回来),但抓出两个 bug,均已修。
- **Bug 1(orchestrator 行为)**:首次拉起时 orchestrator 把 score_auto 挂后台 +"等唤醒"就停了,无头 `claude -p` 没唤醒机制→commit 没跑、库 0 篇。**修**:`drive.py` prompt 加【无头运行】铁条(前台同步、绝不挂后台、走完 discover→score→commit 再回报)。重跑即 41 篇入库。
- **Bug 2(commit 设计缺口)**:`--keep N` 纯 top-N 不认 `seeded`,标"重点"的 MAST(rel24)只能 keep=16 全留、拖 3 偏题。**修** `commit.py`:seeded 篇强制入库(资格闸绕过 rel/flag/panel + 选篇后强制并入;block 仍挡)——seed 机制最后一环。实测 keep=1+seeded rel20 → 强制带上。
- **清理**:删掉被过度 keep 拖进的 3 篇(Ego-R1/Generative Agents/Securing the Agent),生产库 41→**38 篇**,6 奠基作仍在。
- 顺带:`seed.py` 加 `--facet`(种子落正确 facet,运行中改的,保留)。
- 改动(commit.py / drive.py / seed.py + DB 删 3)在工作区,**未 push**。详见 find STATE 22:48 条。

## 2026-06-20 19:54 EDT — find 实跑:主题 agentic-knowledge-synthesis 冷启动选篇入库 41 篇
- **做了什么**:作为 orchestrator 跑完整 find 一轮(discover→seed→score_auto→commit --plan→--keep)。discover 四源召回 2476 去重→候选池 75(+seed);score_auto faceted×5 自举锚点打分;首轮 --keep 写库 39,增量补 longctx 2 篇 → **库内 41 篇**(target 35)。
- **关键判断**:① 6 个 facet seed 全入,含特意保的 MAST(rel=24 facet 垫底,`--keep` 是纯 top-N 不豁免 seed → 只能 agentic-retrieval=16 全留兑现 MUST-include,代价 3 个偏题 Ego-R1/Generative Agents/Securing-the-Agent 入库待删);② longctx-vs-retrieval 关键词只召回 3 篇(饿),按 id 补播 arxiv:2310.03025 / 2409.01666(命中后 rel 95/92),发现二者被 discover 误标 `_all` → 手改 candidates.json 的 facet 再重打分入库;③ cross-paper-structure 偏生物医学 LBD。
- **文件**:写 `topics/agentic-knowledge-synthesis/{candidates.json,scores/,selected.json,topic_state.json}` + 生产库 `data-base/papers.sqlite`(paper_topic +41)。**未改 find 模块代码**(纯实跑+一次性 candidates 数据纠偏)。下轮起点见 topic_state.json 的 turning_seeds。

## 2026-06-20 18:48 EDT — 收尾:去新旧并行(全主题归一走新路)+ orchestrator 转 AUTO 默认 + 停 verify_daemon
- **做了什么**:按用户"都用新的、不要新旧并行"收口。① `run.py` AUTO/AUTO_PULL 的 discover+score+commit → 换成 `find`(orchestrator 转默认);② `score_auto` 删掉非-faceted 单尺分支 + `autopick_anchors`,**永远走 facet 路**(无 facets 的老主题=1 隐式 `_all`),`boundary_rerank` 去留线只剩资格闸 {30,flag_min}(删 target 线);③ 应用户要求 `kill` 了 `tools/verify_daemon.py`(全天候核查守护,与 find 无关)——**核查暂停,需手动 `python3 pipeline/tools/verify_daemon.py` 重启**。
- **老主题影响(获准)**:rl-general-toolbox / rl-digital-human-interaction 走 `_all` 新路——边界去留线从"第 target 名"变"资格闸 30/45"、冷启动自举改 in-memory 不回写 topic.json;已入库的不动。**用户说暂不拆它们成 facet,后续自己用对话处理。**
- **实测**:faceted(2 facet)+ 老主题归一(`single(_all)`)两路 score→commit 端到端过(临时 DB);全量 compile OK,无 autopick/target 残留。
- 详细见 find STATE 顶部两条(18:20 / 18:48)。**改动仍在工作区,git push 等用户。**

## 2026-06-20 18:08 EDT — find 段「facet 改写」整套落码完成(1→5 代码全落 + 自测;6 验证场就绪待用户跑)
- **做了什么**:把 16:44 定稿的设计按 TODO 1→5 全部落代码并自测,TODO-6 验证场备好。find 段从"焊死 discover→score→commit 一条龙"变成"orchestrator claude 全权驱动 + 脚本当工具"。
- **新增**:`pipeline/lib/pool.py`(候选池存储层:candidate_entry/record_to_candidate/去重键/读写)、`pipeline/lib/topic.py`(意图+状态存档层:load_topic 归一成永远带 facets、向后兼容退化、topic_state 读写)、`pipeline/find/seed.py`(按 id 播种 CLI)、`pipeline/find/drive.py`(拉起 orchestrator + §5 prompt)、`pipeline/tools/notify_cli.py`。
- **改**:`lib/sources.py`(抽 per-record 规范化器 + by-id 单查 + fetch_by_id 调度:DOI→OpenAlex/arxiv→官方API/SS兜底)、`find/discover.py`(facet 标签 + --facet 合并)、`find/score_auto.py`(非faceted原样、faceted 新分支 per-facet anchors+hit_criteria)、`find/commit.py`(--plan 摆分布 / --keep 按facet留N / 无flag=auto老行为)、`run.py`(加 `find` 阶段=drive.py;**18:20 修正**:AUTO/AUTO_PULL 的 discover+score+commit 直接换成 `find`,orchestrator 转为默认——用户"搭建阶段直接用新的")。
- **方案 A(用户拍板)**:单 candidates.json + 每条候选带 facet 标签,不拆多文件。
- **测过**:fetch_by_id 三篇真论文 OK;seed.py 端到端(播入/去重/失败);topic 层向后兼容(gt 退化1隐式facet);score_auto faceted(假run_claude:自举锚点/per-facet批文件)+ 非faceted back-compat;commit --plan/--keep(临时DB:精确 2A+1B);drive --dry-run(gt 非faceted/agentic faceted 都渲染对);全量 compile OK。**未碰生产库、未烧真 claude(除 by-id 元数据查)。**
- **6 验证场**:`topics/agentic-knowledge-synthesis/topic.json` 改 faceted(5 facets/15q/6 奠基作 seed_ids,arxiv id 全核对:GraphRAG 2404.16130 等)。**实跑交用户(billed,写生产库)**:`python3 pipeline/run.py agentic-knowledge-synthesis find`。
- **7(gt 拆 6 facet)**:老主题 opt-in,按用户决定留用户后续自改,本次不动。
- 详细过程账见 find STATE 顶部五条(17:14→18:08)。**git push 仍等用户。**

## 2026-06-20 16:44 EDT — find 段「facet 改写」整套设计定稿 + 成品落档(纯设计,未落码)
- **做了什么**:把 02:16 顶条挂的「🔶 找段大方向改写」从悬而未决推到**可落代码的定稿**——地基①存档格式 + 地基②编排模型 + 治理/通知模型全敲定。
- **成品文档**:`claude-memory/Prompt-structure-design/find-facet-rewrite-design.md`(存档 schema 说明 + orchestrator prompt 初稿 + 实现 TODO),新会话照此实现。过程账详记 find STATE 三条(16:16/16:30/16:44)。
- **核心决定**:①存档拆两文件(topic.json 意图手定 / topic_state.json 状态 pipeline 写),facets[] 带 hit_criteria/anchors/seed_ids/queries,配额=claude 判断不存数字;②编排=拉起一个 claude 全权驱动(cron/对话共用),python 只拉起+收尾,脚本当它 Bash 调的工具,prompt 只给情况/工具/项目契约/通知规则不教怎么找;③fan-out 在 find 是甜区(一 facet 一子agent),拐弯不设界(它判断),通知三档(例行留痕/新发现TG/回报照旧)。
- **前置零件**:「按 id 播种」(lib/sources 缺按 id 单查元数据,seed_ids/add_url 共用)。
- **下一步**:按 TODO 落码,验证场=agentic-knowledge-synthesis 重搜捞回被切的奠基作。

## 2026-06-20 16:16 EDT — 博客/网络源扩展(add_url)架构敲定 + 推翻旧 text_path 支点(纯设计,未落码)
- **做了什么**:把 2026-06-19「add_url 副轨」计划重审一遍,敲定可落代码的最终架构,并揪出旧计划一个**死支点**。跨 find/fetch/summarize 三段设计,详记 `claude-memory/modules-modification/find/STATE.md` 顶条(2026-06-20 16:16)。
- **⚠️ 旧计划 text_path 支点作废**:`lib/db.py:38` text_path 已 DEPRECATED(2026-06-16,恒 NULL,留列免动 prod),summarize 只读 pdf_path——「写 text_path 自动流过 summarize」不成立。
- **敲定**:①抓取分级=静态博客 claude WebFetch 自抓(替 trafilatura) / X·硬页 opencli 真 Chrome(复用 fetch_tierb 那套,图多截图喂 claude);②落盘路线B(用户拍板)=博客 md/截图占 `pdf_path` 位、存 `storage/papers/<slug>/`;③质量砍硬档(废 url_allowlist 白名单)→软约束=查找+总结两道 claude 判可信度;④blog 标记三重(id=URL / sources=web+域名 / quality_signals 加不参与过滤的 web tag),全不改库表。
- **defer(用户)**:summarize 接口统一(DB→worklist→prompt 焊死 PDF 假设,方案已想好:抽象成 source_kind 分支,本轮未动)。
- **为什么**:agent/长上下文前沿一大半不在 arXiv(在 Anthropic/Lilian Weng/X 等),只搜 arXiv 系统性漏半领域;且与 facet 改写「按 id 播种捞奠基作」共「按外部标识入库」地基。

## 2026-06-20 05:25 EDT — 顶层目录大改名全链路收口(用户改名,代码/DB/gitignore/文档全跟上)
- **用户把顶层目录改名(保留)**:`db`→`data-base`、`store`→`storage`、`ref`→`reference`、`review`→`for-human-review`、`docs/claude_memory`→`claude-memory`、`vendor`→`dependencies`(后两个本会话早先已处理)。其中 **`db`/`store` 是代码+DB 硬编码依赖**,改名一度让整套跑挂——本次全链路改对。
- **代码(功能性)**:`ROOT/"db"`→`"data-base"`(lib/db.py DB_PATH、retrieve/index.py VEC_PATH、search.py FTS_PATH);`ROOT/"store"`→`"storage"`(lib/store.py paper_dir、fetch_tierb DL_DIR、cross_topic、prepare_update、register_updates、update_auto、export_corpus、eval_retrieval、init.py DIRS、render_topic、ask 提示)。**关键纰漏**:export_corpus.py:72 是**单引号** `ROOT/'store'/'summaries'`,首轮双引号扫描漏掉,二次单+双引号穷扫才揪出修掉。
- **数据库**:`data-base/papers.sqlite` 里 322 条路径 `store/papers/`→`storage/papers/`(papers.pdf_path 221 + summary_versions.path 101),0 悬空。
- **gitignore**:store→storage、db→data-base、`For-human-review/`→`for-human-review/`(大小写);折叠后 `git add --dry-run` 零吞 pdf/索引/大依赖。
- **文档**:`claude_memory/`→`claude-memory/` 全仓 19 文件;当前设计文档(CLAUDE.md/README/ARCHITECTURE/ops/模块README)23 个的 db/store 路径更新;代码注释同步。**STATE.md append-only 历史正文不改写**(只修死链接 claude_memory→claude-memory)。`ref/academic`→`reference/academic`。
- **区分(没误改)**:`lib/db.py`/`lib/store.py` 是**模块名**(不动)、`from lib.db`/`from lib.store` 不动、ARCHITECTURE 列的 lib 模块 `db`/`store` 不动。migrate_store_layout.py 是历史一次性脚本(已跑完不会再跑)留原样。
- **验证(全过)**:25 模块导入 OK;`open_db` 读 data-base 真库 221 篇;`ask.py` 真检索端到端通(读 data-base + 建 data-base/{fts,vec}.sqlite + GPU 嵌入 dependencies/models + 命中显示 storage/papers/ 路径);全程无误建空 db//store/。
- **daemon**:改前先 kill(旧 PID 3462179),改完+验证后**已重启**(新 PID 4064361,日志确认读到真库 100 papers、正常起核查批;codex 额度窗口外它会自己睡)。

## 2026-06-20 04:57 EDT — logs/ 大扫除 + 临时日志归 temporary-log/ + gitignore 折叠
- **新约定**:临时/可重建日志统一进 `logs/temporary-log/`(方便整体删)。代码改 `lib/log.py`(`get_logger` 的 `pipeline-<date>.log` → `TEMP_LOG_DIR`)、`fetch_tierb.py`(`tierb-<date>.log` 同移)。`run.log`(机器总账)留 `logs/` 根、入库不变。
- **gitignore 折叠**:原来一堆零散 logs 规则(pipeline-*/tierb-*/bot*/redo-*/wipe-*/cron-*) → **一条 `logs/`(整个目录忽略)**。用户拍板连 `run.log` 也不入库(它只是记录、与重建无关)→ `git rm --cached logs/run.log`(留盘、移出追踪)。至此 logs/ 下 git 一个文件都不追踪。
- **删**:老 `pipeline-2026-06-*.log`/`tierb-*.log`/`trial-*.log` + 两个小快照(`summaries-baseline-20260618`、`summaries-wipe-20260619`)。**git rm**:6 个过时 verify 实验日志 + 18 个已被 claude-memory STATE 取代的 `SESSION-*.md`(盘上早删、本次提交删除)。
- **留**(都在盘上、都不入库):`run.log`(机器总账)、`verify_daemon.log`+`.pid`(daemon **PID 3462179 正活着**、quota-stop 在睡,别动)、`cron-sum.log`(crontab shell 重定向,操作性)、`bot*`(运行时)。`logs/temporary-log/` 现装着 1.3G 的 `redo-store-migrate-...` 迁移备份(留作回滚,确认新布局没问题后可删回收 1.3G)。
- 注:`cron-sum.log`/`verify_daemon.log` 由 crontab `>>` 重定向写,不是代码;路径要改得动 crontab(用户的),本次未动,仍在 `logs/` 根。

## 2026-06-20 04:39 EDT — 大依赖统一进 dependencies/(noVNC + Qwen 模型)
- 用户定:比较大的外部依赖统一放仓库根 `dependencies/`,不再散在模块内。搬:`vendor/novnc` → `dependencies/novnc`(删空 `vendor/`);`pipeline/retrieve/models`(Qwen 嵌入缓存 ~1.2G,HF `hub/` 结构) → `dependencies/models`。
- 配套改路径:`lib/embed.py`(`_MODELS_DIR` → `parents[2]/"dependencies"/"models"`,即 HF_HOME)、`pipeline/remote_view.sh`(`NOVNC_WEB` → `dependencies/novnc`)。
- `.gitignore`:`vendor/` + `pipeline/retrieve/models/*` 段 → 合并成 `dependencies/*` 忽略 + `!dependencies/README.md` 保留;新建 `dependencies/README.md`(说明里面该有啥/怎么重建)。docs 同步:migration.md(迁移表+clone-misses 清单+封存件)、remote-access.md、retrieve/README.md(retrieve/STATE 是 append-only 历史,不改)。
- **验证**:`conda run -n research-agent` 跑 `embed_query` —— `HF_HOME=dependencies/models`,模型从新位置加载、出 1024 维、**不重下**;`git add --dry-run` 确认 `dependencies/` 只进 README、`store/papers/` 0 个 paper.pdf。
- 另:用户手动删了空目录 `runs/`(死目录,只有 init.py 建、无人写);已从 `pipeline/tools/init.py` 的 `DIRS` 去掉 `"runs"`(免得 init 重建)。

## 2026-06-20 04:19 EDT — 文件结构重构【落地完成】:论文一篇一个家 store/papers/<slug>/
- **搬运已 apply**:`migrate_store_layout.py --apply` 执行。221 篇 PDF+总结迁入 `store/papers/<slug>/`(`paper.pdf` + `vN.md`);旧 `store/pdfs`/`store/summaries` 清空删除;DB `papers.pdf_path`+`summary_versions.path` 共 322 行改写;一致性 0 悬空(221 pdf + 101 总结全部落地)。**备份**:整盘 db+store+topics 冷拷在 `logs/redo-store-migrate-20260620-041623/`(1.3G,gitignore)。
- **代码读写口全部改到新布局**,收口到 `lib/store.py` 的 `paper_dir/pdf_file/summary_file/verify_file`(唯一路径出口,以后别再写死旧路径):fetch_oa/recover_oa/recover_agent/fetch_tierb(下 PDF)、build_worklist/register_summaries/summarize_auto/render_topic(总结)、prepare_update/export_corpus/ask/init.py、config.json `paths`。14 个改过的模块真导入冒烟全过。
- **verify 新能力**:核完每篇把 codex 详情**按版本累积**写 `store/papers/<slug>/verify.json`(`{versions:{N:{verdict,issues,checked_at,backend}}}`,永不覆盖旧版,留全程问题历史);`verify_summaries.record_verify_detail` + `escalate_verify` 都接上。**不动** verify 状态文件(verified/verify_status/verify_skip)与 daemon——状态/详情彻底分家(状态在 `topics/<id>/` 喂 daemon,详情在论文文件夹)。历史详情已丢失、不回填(原因见 03:51 条)。
- **验证**:render_topic(读 100 篇/已总结 80)、build_worklist(summary_dir 指向 store/papers)、record_verify_detail(v2→v3 累积不覆盖)全过。
- **`.gitignore` 已补**(防 `git add` 误吞版权 PDF):`store/pdfs/` → `store/papers/*/paper.pdf`(同目录 .md/verify.json 仍可入库);用户改名连带修 `ref/`→`reference/`、新增 `For-human-review/`(原 review/,含版权 PDF)。删掉搬空的 `store/pdfs`、`store/summaries` 空目录。
- **未做(待用户单独发话)**:git 把 `db/store/topics` 移出追踪 + 清历史(`git filter-repo`)+ `force-push`(push 由用户)。改名连带的 **CLAUDE.md 12 处 `claude_memory/`→`claude-memory/` 断链 + claude-memory 内部交叉链接**由用户处理(我未碰)。

## 2026-06-20 03:51 EDT — 文件结构重构·第1步:论文 PDF+总结归并脚本(dry-run 就绪,未 apply)
- 新增 `pipeline/tools/migrate_store_layout.py`(默认 dry-run，`--apply` 才动盘）。目标布局：一篇一个家 `store/papers/<slug>/`，内含 `paper.pdf`(原 `store/pdfs/<slug>.pdf`) + `v*.md`(原 `store/summaries/<slug>/`)。
- 改写 DB 路径列 `papers.pdf_path`、`summary_versions.path`；幂等。dry-run 实测：221 论文夹 / 搬 221 PDF + 101 总结 / 改 322 DB 行。
- **范围澄清(重要)**:脚本【只搬 PDF+总结、改 DB】，**完全不碰 verify**——用户明确不动 verify 全局状态(`topics/*/verified.json`/`verify_status.json`/`verify_skip.json`、daemon、续核一律原样)。用户对 verify 的真实诉求仅是"把 codex 判断的文字也存进论文文件夹"——这是 verify 代码往后跑时**额外写一份** `store/papers/<slug>/verify.json`(verdict+issues)的小新增,与状态模型无关,**另行实现,不在本脚本**。(我一度把方案做大到"拆 verify 状态进每篇/或进 DB",已纠回。)
- 待办:① 改写死旧路径的写入点(fetch_oa/recover_agent 下 PDF、summarize_auto/build_worklist/register_summaries/render_topic 写读总结、ask/init)+ `lib/store.py` 加 `paper_dir(slug)` 统一出口;② **新增能力**:verify 核完每篇时把 codex 详情按版本累积写进 `store/papers/<slug>/verify.json`(形如 `{versions:{"1":{verdict,issues,checked_at,backend},...}}`,永不覆盖旧版,留全程问题历史);不动 `verify_status.json`/daemon。
- 历史核查详情:**确认已丢失、不回填**。原因:issues 仅渲染进 `summary_verification.md` 且每轮整file覆盖,当前两 topic 的报告都是失败轮(checked 0)产物,旧详情已被盖;git 历史里虽有成功轮(如 `8ee86bb` topic2 100/100),但其后有过"清空总结层重做"(`0cd67bf`),旧 issues 对应的是重做前的总结版本,贴回当前版本会张冠李戴。故历史详情作废,待 ② 落地后重核生成与当前版本匹配的新详情。
- 背景决策(本次会话定)：git 只入库"流程骨架"(代码+claude_memory+config/quality)，db/store/topics 等数据不入库、换机器走硬盘拷贝；旧数据待从 git 历史清理(git filter-repo，后续单独做、force-push 由用户)。store 采"论文全局平铺 + topic 只当名单/检索配方"，不按 topic 套论文(避免跨主题重复/漂移)。

## 2026-06-20 03:50 EDT — 文档目录改名 docs/ → claude_memory/，修全仓断链
- 用户把 `docs/` 整个挪到根目录改名 `claude_memory/`，子目录也重命名：`modules/`→`modules-modification/`、`ops/`→`operation-maintenance/`、`design/`→`Prompt-structure-design/`（`ARCHITECTURE.md`/`README.md` 平移）。
- 影响：运行不受影响（无代码 import/open 这些路径，全是文档/注释里的"设计见…"）；但 85 处链接断。已批量按 old→new 有序替换修好：`CLAUDE.md` 12 处（导航入口）、`claude_memory/**` 内部交叉链接 ~70 处、代码注释 3 处（`pipeline/ask.py`、`pipeline/retrieve/readall.py`、`pipeline/config.json` 的 `_comment`）、本文件顶部活指针 1 处。
- append-only：02:54 那条历史记录保留原文（写于改名前，故仍称 `docs/`），不改写历史。`reference/LightRAG/**` 第三方仓库未动。

## 2026-06-20 02:54 EDT — 文档/记忆大重构完成：模块化 docs/ + 三套记忆收口成两套
- 背景：原结构乱——三套记忆并存（harness 记忆 / `docs/claude-memory` 影子快照 / CLAUDE.md 正文）、CLAUDE.md 201 行臃肿有重复段+过期状态、docs 一锅烩、顶层目录碎片化、历史散在 24 个 logs/SESSION-*.md 里找不着。用户工作方式=按模块改+跨对话接力+多 agent 并行，要"模块为单位、并行不撞车、跨对话循图可查"的结构（也作复用到其他项目的方法论）。
- **新架构（一件事一个家）**：
  - `CLAUDE.md` 瘦身 201→~55 行 = 导航页（项目是什么/命令速查/铁律坑/**文档地图**/落盘铁律）。删了重复的"大改造①②"段 + 过期"当前状态截至06-15"。
  - `docs/ARCHITECTURE.md` = 全局框架（流水线全貌+模块边界+**模块间接缝**+数据模型5表+脚本清单+总蓝图）。
  - `docs/modules/{find,fetch,summarize,verify,retrieve}/` 每模块两文件：`README.md`=定型设计（覆盖更新）、`STATE.md`=**层积日志**（新在上、老在下、不删，带日期+时间戳；顶=现状、下=历史）。
  - `docs/design/` = 横切深度长文（quality 新建 + 迁入 summary-design-principles/qa-layer-design/qa-layer-evidence/score-drift-research-findings/summary-prompt-rewrite-plan/prompts/skill-工作原理与调用）。
  - `docs/ops/` = 运维（nightly-cron/migration/remote-access/telegram，整合自旧 docs/nightly-cron-deploy.md + change-device/ + remote-access/ + CLAUDE.md 相关节）。
  - `docs/README.md` = 文档地图 + 三条分工规矩（局部进 STATE / 跨模块·全局进 claude_log+模块留指针 / 一 agent 一模块）。
- **记忆收口 3→2**：① harness 记忆（机器本地）只管"怎么跟用户协作"，不存项目知识（现有 6 条本就是这类，未动）；② 随 git 的 `docs/`+`claude_log` 装项目知识。**删 `docs/claude-memory/` 影子快照（16条过期）**——其角色被随 git 的 docs/modules 取代。**不碰**全局 `~/.claude/CLAUDE.md` 与 harness 记忆现有条目。
- **19 个 logs/SESSION-*.md 全部吸收后删除**：13 个忠实搬进对应模块 STATE 历史层（find3/fetch1/summarize4/verify3/retrieve2，recover-rag 拆 fetch+retrieve）；6 个早期/跨模块（06-08/09/10/10-runs/17-STATE/18-folder-refactor）回填到本 claude_log 底部（06-18 前历史空白，本文件 06-18 才建）。保留决策/为什么/教训，只删操作噪音。
- **碎片清理**：删 `change-device/`、`remote-access/`、`docs/nightly-cron-deploy.md`（内容已并入 ops/）；`pipeline/ARCHITECTURE.md` 保留作代码层视角（docs/ARCHITECTURE 指它）。移文件后用 sed 修全 docs/ 引用 + 把 design/ops 里指向已删 SESSION 的死链重指到吸收它的模块 STATE；grep 验证无死链残留。
  - ⚠️ **失误+补救**：`remote-access/` **未被 git 跟踪**（含一个 wrapper 脚本 `ask-research-kb`），`rm -rf` 后不可经 git 恢复——删前没检查它有非文档文件，是疏忽。补救：全局 snippet 正文从 git 的 `change-device/MIGRATION.md` 附录捞回、wrapper 照文档行为重建，二者已**内联进 `docs/ops/remote-access.md`**（自包含），功能无损；唯一真丢的是那个 wrapper 的原始文件。该远程查库本就"已备未启用"。
- **落盘铁律（写进 CLAUDE.md，同全局口径）**：改一模块→记该模块 STATE 顶部；跨模块/全局→记 claude_log+模块留指针；不等人催由 Claude 自己落盘。
- 怎么做的：主体用并行子 agent（5 模块各一个起草 README/STATE、再各一个吸收 SESSION；ARCHITECTURE/quality/ops 各一个），Claude 把关+收口+修死链。**全程未 commit/push（用户负责 push）。** 顺带挖出多处 CLAUDE.md 过期点（retrieve 实为只标注不过滤/tier 五值含 ok/verify 已摘出夜间链/note_plan 已删/总结篇数 39-60 动态），均以代码为准写进新文档。
- 关联记忆：[[working-style-review-pace]]（计划先行、按模块、并行 agent）、[[claude-log-convention]]。

## 2026-06-20 02:31 EDT — 迁移 SESSION-2026-06-10 的 RAG①/ask.py 部分进 retrieve/STATE.md
- 做了什么：把 `logs/SESSION-2026-06-10-recover-rag.md`（混合文件）里属 retrieve 的两段（④RAG 第一步 ask.py + ⑤ARS/corpus-first 接口回顾 + Bipedal 重复入库）忠实搬成历史条 `## 2026-06-10 · RAG 第一步：ask.py + FTS5 落地`，追加到 `docs/modules/retrieve/STATE.md` 末尾（比现有 06-17/06-18 都旧，放最下）。recover/取全文部分（①②③）不搬——已在 fetch 模块。
- 为什么：文档模块化重构——清空 SESSION 混合文件，retrieve 内容归位 retrieve 模块。
- 保留的细节/坑：FTS5 上 LIKE 静默返回 0 行必须用 instr；fts_sum trigram + fts_text porter（注明 fts_text 后于 2026-06-16 移除避免误导）；中文切段/instr 兜底；出口认 quality_tier；--answer claude -p 综合问答。
- 文件：`docs/modules/retrieve/STATE.md`（追加一条）。SESSION 原文件由用户统一删（我没删）。

## 2026-06-20 02:07 EDT — 写 docs/design/quality.md（质量四档横切子系统设计）
- 做了什么：新建 `docs/design/quality.md`，中文设计长文。覆盖设计哲学（能标记就不删/verdict 持久化在 papers.quality_tier，各出口都认）、四档（block/suspect/trusted/flag + ok）命中与处置、名单来源（Beall's 衍生停更名单 + local/doi_prefix/venue 白名单 + DOAJ）、各出口认标记表、audit_quality 回溯审计、关键文件。
- 为什么：把横切质量体系从 CLAUDE.md 抽成独立设计文档（文档模块化重构的一环）。
- 怎么写：逐字核对了 `pipeline/lib/quality.py` 与各出口（discover/commit/summarize/render/ask/answer），不照抄 CLAUDE.md。
- 发现的过期/矛盾：① CLAUDE.md 说 retrieve「默认过滤/降权」，实际 `retrieve/answer.py` 是**只标注不过滤**——doc 以代码为准并注明。② tier 实为五值（含 `ok`），CLAUDE.md 只列四档。③ 名单为停更（2017）的 Beall's 衍生，无独立 DOAJ 本地文件（DOAJ 走 OpenAlex `is_in_doaj`）。
- 文件：`docs/design/quality.md`（新建）。

## 2026-06-20 01:10 EDT — 文档/记忆重构：搭 docs/ 模块化骨架（只建架子，未迁内容）
- 做了什么：与用户敲定"模块为单位"的记忆/文档新架构，建 `docs/` 骨架——`README.md`(文档地图/导航)、`ARCHITECTURE.md`(整体框架占位)、`modules/{find,fetch,summarize,verify,retrieve}/{README,STATE}.md`(每模块 README=定型设计、STATE=当前进度/未决/在查bug)、`design/`+`ops/` 占位。均为占位说明，未填真内容。
- 为什么：原架构乱——三套记忆并存(harness记忆 / docs/claude-memory影子快照 / CLAUDE.md正文)、CLAUDE.md 201行臃肿有重复段、docs一锅烩、顶层目录碎片化。用户工作方式=按模块改+跨对话接力+多agent并行，需要模块化、并行不撞车、跨对话可循图查找的结构。这也是用户要复用到其他项目的方法论，且本项目尚早、搬迁成本最低。
- 待办(下一步，未做)：①把现有9个docs+24个SESSION笔记内容归位到对应模块；②quality写成 design/quality.md(横切子系统，非模块)；③瘦身 CLAUDE.md 成"导航+铁律"并加"文档地图"节(命门)；④删/冷藏 docs/claude-memory 影子快照；⑤拟一条"改完更新模块STATE"的铁律草稿**给用户过目后再写**。
- 决策依据详见本次会话；架构要点：harness记忆(机器本地)只管"怎么跟用户协作"，项目知识全归 docs/modules(随git、跨机器)。**不碰**全局 ~/.claude/CLAUDE.md 与 harness 记忆现有条目。

## 2026-06-20 00:46 EDT — 标记 Input-to-State Safety 篇为"待用户手动修改"（撤回后又按用户要求重标）
- 经过：先 record_skip 标记(00:36)→ 用户说"标记不用,去掉"→ 删了(且确认删v5回退v4后该篇 seen==current 本就不会被daemon挑)→ 用户改口"先标记一下,我后面来修改"→ **重新 record_skip**。
- 当前标记：`verify_skip.json` 钉版 **v4**,理由"【待用户手动修改】v5乱码已删回退v4;v4遗留1处major + codex核v5反复崩,标记搁置,daemon勿动"。审阅副本在 `review/Input_to_State_Safety_for_RL/`(PDF+v1~v5+README)。
- 含义：daemon 不再碰这篇;用户日后手动核/改 v4 或重做出新版(新版≠钉版v4→自动复活,重进核查队列)。
- 系统性补丁(连崩封顶/重做全局闸)仍待做,见 00:36 条 + 用户"细节后议"。

## 2026-06-20 00:36 EDT — 【问题记录】verify churn 病例:Input-to-State Safety 篇 v5 损坏 + codex 反复崩 + 重做无全局闸
- **病例**：`10.1109/tnnls.2026.3688045`（Input-to-State Safety for RL，控制理论密集）被核查 churn 到 v5。序列(daemon 日志)：v1 MAJOR(2)→v2 MAJOR(3)→v3 MAJOR(3)→v4 MAJOR(1)→v5；**v5 起 codex 核查反复 exec exit 1 崩、从没核成**(真实判决停在 v4=major)。实跑复现:崩的报错尾部全是 codex 自己的分析文字、真实崩因没干净捕获(跑一大段后 exit 1,疑被超长/乱码噎住)。
- **三病叠加**：①真·硬论文 churn(v1–v4 codex 每轮揪真 major,多半"放大安全集 vs 真安全集"形式保证落差)；②**v5 被 claude 重写时注入 11 处阿拉伯乱码 `ISالسf`(应 ISSf)**——v1–v4 全 0 处,仅 v5 坏=claude 输出抽风,垃圾版本；③v5 核查反复崩。
- **暴露的系统性缺陷(待补,用户说细节后议)**：(a)**重做次数跨 daemon 批次不封顶**——escalate 的 `--max-attempts 2` 是每次 `run.py verify` 进程内计数,daemon 反复调→每次清零→无全局刹车,才 churn 到 v5;(b)**codex 反复崩的篇没封顶**——会被无限重试/重做。用户已拍:**codex 崩之后要上标记**(具体后议)。拟修:跨运行重做总闸(≥3 次仍 major→标人工) + verify 连崩 N 次→标人工。
- **本次处理**：①把该篇 PDF+v1–v5 总结+README 复制到 `review/Input_to_State_Safety_for_RL/` 供用户审；②删损坏的 v5(文件+summary_versions 行),当前版本回退干净的 **v4**;③`record_skip` 钉版 v4 标"需人工分诊"(daemon 不再 churn/烧 codex);④重渲染 topic.md。
- **顺带验证(好消息)**：本次撞 codex 真额度耗尽时,**新分类器+daemon 正确判 quota_exhausted 并长睡到 04:08(~4h)**——0619 重构的 LLM 失败分类在真额度事件上端到端跑通了。
- ⚠️ review/ 含 PDF 副本(版权,本地审阅用,勿提交/外发)。

## 2026-06-20 00:32 EDT — 【设计决策·暂定钉死】「找」+「取PDF」两段改"Claude 智能监督 + 现有管道执行"
- **缘由**：用户发现一个研究主题其实是「好多组论文」(以 `agentic-knowledge-synthesis` 为例,idea 里自列 5 个侧面:跨论文综合/关系结构方法学/agent主动求知/长上下文vs检索/库上QA)。现行"一个主题一把尺子打分→全局 Top-N"有三病:**小簇饿死**(冷门 facet 被论文多的 facet 挤掉名额,而那恰是用户最看重的)、**一把尺子量五件事**(完美命中单一 facet 的尖货被"哪个都沾点"的平庸货压分)、**丢结构**(入库成一锅炖平表,看不出每个子问题覆盖够没够)。
- **现场验证过我手搜的真实表现**(WebSearch/WebFetch 跑了 `矛盾/共识检测` 这个 facet):一次搜~10条、信噪比低(9条里1-2条对题,其余关键词撞上但领域跑偏)、无批量摘要只能肉眼筛标题、再 fetch 验证、串行慢。结论:**召回是 API 的强项(一次拉200带摘要)、不是我的;我的价值在"拆方向/精筛/拐弯(顺引用网挖邻居、看覆盖补缺)"**。
- **暂定钉死的核心原则(仅限「找」discover→score→commit + 「取PDF」fetch/recover/hunt/tierb 两段)**：**我的智能负责"判断与编排",现有管道负责"力气与确定性执行";管道脚本从焊死的一条龙变成"我手里的工具",我在每个决策点介入。** 这是对 2026-06-09"把 Claude 移出 runtime"的**精修不是推翻**——「啃」(总结/核查)那段是批量苦力,继续无人黑箱;用户用"至少这两段",留口子日后可扩。
- **分工(逐阶段)**:discover=管道批量召回/我拆facet定词判够不够;score=管道批量打分/我定per-facet尺子+配额+看边界;commit=管道写库/**我定稿,且增量拉来的新篇我直接commit、事后Telegram回报**(用户明确"信我的判断",不每篇等点头);fetch/recover=纯执行我只看漏斗;hunt=本就agentic归我;tierb=我定哪些值得走、验证关卡仍要人点。
- **"无人"的正确含义被用户澄清**:无人=**无"用户"**不是无"我";cron 不替代我,是"把我(agent)叫醒"的闹钟。目标流程=每次聊定一个 topic→把判断**结晶成一份存档**(facets+命中标准+取舍偏好+score_anchors+覆盖状态+拐弯种子)→定时叫醒我、照存档跑增量(逐facet增量召回→打分→覆盖体检→拐弯补→commit→TG回报)。机器已有先例:hunt/bot 证明 claude -p 能被定时叫起来联网干活;增量召回/cron队列/commit增量追加都已存在,**要补的核心=把 topic.json 升级成"装得下判断的存档" + 叫醒后的编排逻辑**。
- **本次未动代码/未落地**:① 文件保存架构用户说"后面来定、要整体改一遍",故存档放哪、覆盖状态怎么存/怎么算"薄"**全部推迟**,我不设计不动手;② facet 配额倾向"保底M篇+剩余全局按分填"(治饿死又不过度限制富矿),facet 数=1 时优雅退化成现状;③ 下一步待用户定文件架构后,再落"存档长什么样"+"叫醒编排"。**纯设计对齐,无文件改动**(本条仅 log)。

## 2026-06-20 00:09 EDT — verify 失败处理系统性重构：LLM 失败分类器取代关键词匹配（治"出一个修一个"）
- **缘由**：接 06-19 18:10 那个补丁。审计(派 agent 通读 verify_summaries/escalate/daemon/codex/claude)发现"靠关键词猜失败类型"是一类隐患:`_is_quota_err` 关键词清单脆、超时(`TimeoutExpired`)谁都不认、claude 应急后端在体系外、报错被截断(codex 400/claude 300)、daemon"无进展→坏PDF"是瞎猜。用户拍:**删关键词快速通道,全交 claude 判;额度耗尽别十几分钟硬敲**。
- **新增 `lib/error_classify.py`**:`classify_failures()`(一批去重→一次 claude 判类别+恢复时长,任何失败→回退 unknown=短重试,绝不抛) + `classify_batch()`(聚合批级裁决)。六类:quota_exhausted/transient/bad_input/malformed_output/real_error/unknown。**无关键词清单**。
- **`lib/codex.py`+`claude.py`**:超时归一成 `RuntimeError("...timed out...")`(不再漏裸 TimeoutExpired);报错截断 400/300→**保留尾部 2000**(横幅不被切)。
- **`verify_summaries.py`**:删 `_is_quota_err/quota_hit/parse_retry_until/note_quota/is_codex_fail/mark_codex_backoff` 六个关键词函数 → 换 `write_signal(category)` + `classify_and_signal()`(分类→停轮写信号/逐篇跳过) + `record_skip/load_skip`(新 `verify_skip.json` **钉版**跳过坏输入篇,免每轮白核成配额黑洞;重做出新版自动重新合格)。熔断改**计数**(失败累计 CIRCUIT_TRIP=4 跳余下,不靠关键词);`verify_batch` 的 failed 现每条带 id/version;`parse_obj` 移进 try(畸形输出也计入)。`split_must` 加 skip 参数排除;`load_candidates` 返回三元组。
- **`escalate_verify.py`**:quota_hit/if-not-ok/is_codex_fail 三段 → 一个 `classify_and_signal`(quota/transient/real_error→写信号+停轮;bad_input/malformed→record_skip)。删 TRANSIENT_BACKOFF_MIN。
- **`verify_daemon.py`**:`read_quota_state` 返回 category;**砍掉"无进展→坏PDF"瞎猜**→按类睡:quota 睡到 until(无则默认 `QUOTA_DEFAULT_MIN`=2h,治"十几分钟硬敲")/transient 递增退避 `[15,30,60]`/real_error 报警跳主题;无信号无进展连 `MAX_NOPROGRESS`=2 次才跳(诚实"原因未明",不断言坏PDF)。`unverified_count` 排除 verify_skip。`run.py` 燃尽 unverified_count 同步排除。
- **验证**:全 py_compile 过;桩掉 claude 的单元测试(分类六类对、批级聚合优先级对)+集成测试(写信号/坏PDF逐篇跳/record_skip 钉版/split_must 排除/重做重新合格/daemon 读类别即删)全过;env python 真实导入冒烟过。**重起 daemon(pid 3462179)实核中**。未提交(待用户 push)。
- 关联记忆:[[prefer-llm-judge-and-agents]](用户定:别 whack-a-mole,优先 LLM 判,放手用 agent)。

## 2026-06-19 23:50 EDT — 新主题 `agentic-knowledge-synthesis` 定稿入库 + 首轮搜索废弃重来
- **做了什么**：与用户讨论收敛出一个新研究主题"Agent 消费知识库与跨论文综合（长上下文时代）"，建 `topics/agentic-knowledge-synthesis/topic.json`（15 检索词/2023起/target35）。跑了 discover(池70)+score(冷启动自举)。
- **为什么废弃首轮**：score 后发现 discover 的 `prefilter_rank` 纯词法取前 70，把领域奠基作（GraphRAG/RAPTOR/PaperQA2/OpenScholar/Chain-of-Agents/MAST，全在我们自己 evidence 文档里）全切掉了 → 召回不足；外加生物医学 bleed。用户拍：删本轮全部产物、先把讨论入库。
- **删了**：`topics/agentic-knowledge-synthesis/{candidates.json,scores/}`、`logs/{discover,score}-aks.out`；topic.json 清掉自举的 score_anchors（来自坏池）。**生产库未触碰**（该主题 topics/paper_topic 均 0 行，discover/score 本就不写库、commit 没跑）。
- **入库的讨论**：主题边界/前提/`add_url` 博客工具计划/召回漏洞教训 → 全文记入 `logs/SESSION-2026-06-19-agentic-knowledge-synthesis.md`；主题定义保留在 topic.json 待补召回后重搜。
- **下次接**：补 ~7 条精准检索词(+可选"按id播种"原语) → 重搜 → commit；建 add_url。

## 2026-06-19 18:10 EDT — 修 daemon 把"codex 瞬时限流"误判成"坏PDF→跳过"的 bug
- 现象：用户收到 verify daemon 发的「可核的都核完了，剩余核不动(多半坏/缺PDF)需人工看」——实为误报。真相：daemon 实际已核 ~23 篇/重做 7 篇（v2/v3），之后 codex 一阵**瞬时限流**(报错 `codex exec exit 1`，**不含** usage limit/429/quota 关键词)→ `escalate` 走 `if not ok: break`(非配额分支)→ daemon 见"无进展"→ 当坏PDF skip→ 退出。codex 实测随后即恢复(直接跑回 OK)。
- 修：`verify_summaries.py` 加 `is_codex_fail()`(失败是否多为 codex 调用挂，区别于坏PDF) + `mark_codex_backoff(minutes)`(写**短退避** codex_quota.json：hit+短 until+transient 标记)。`escalate_verify.py` 的 `if not ok:` 分支：若 `is_codex_fail` → 写 15min 短退避 + 诚实 Telegram「疑似瞬时限流，约 X 后自动重试」+ break。daemon 读到该信号即睡 15min **重试**(走既有 `if hit:` 分支)，不再误判跳过。常量 `TRANSIENT_BACKOFF_MIN=15`。
- 验证：py_compile 过；is_codex_fail({codex exec})→True、({no pdf})→False；重起 daemon 后实跑(7 个 codex 进程并发核 rl-general-toolbox 待核42)。
- 注：本会话跨整天(凌晨建 cron→傍晚)，9:00 cron 那趟 daemon 也跑过(日志"第二次启动"来源)。当前 daemon pid 2719161 活着、正常核查中。

## 2026-06-19 04:43 EDT — 方案④「全读模式」落代码(readall.py) + 五方案速查表 + 验明 claude -p 能 spawn 子 agent
- **机制验证**(动代码前先验,headless 真跑):`claude -p --allowedTools "Read,Task"` **能 spawn 子 agent、且子 agent 能 Read 开 PDF**(让它读 MARL 综述 PDF 回出标题/页眉/页码,num_turns:2)。**不用 `--dangerously-skip-permissions`**。
- **🆕 `pipeline/retrieve/readall.py`** = 方案④全读(清单版/方案B):`load_papers`(默认全库跨主题/`--topic`)→`build_catalog`(每篇一行=[n]标题+⚠️质量&核查标记+slug+总结路径+pdf路径,**总结正文不进prompt**)→`run_claude(tools=["Read","Task"])`(Opus自己把总结读全=召回地板、相关再Read PDF、多了可Task并发、合并单线程)→`_extract_json`→cited[n/slug]回填。**模型只吐`{answerable,cited}`,DOI/路径由python据DB回填=零DOI幻觉**;解析失败机械兜底、空范围哨兵。
- **🔧 `ask.py`**:加 `--mode {readall(默认),pipeline}`+`--topic`;`--answer/--json` 默认走全读、**不碰索引**;pipeline=老检索路保留;understand/rerank/search/index 从默认退役留盘当大库工具。**🔧 `answer.py`**:抽 `make_source()` 共享契约助手(readall/pipeline 共用,标记/DOI回填口径统一)。
- **为什么"清单+按需Read"不是"总结全文贴进prompt"**:prompt短(不每次重发几十万字)+不稀释注意力;代价=召回靠模型读全(现20篇能读全不漏,库大了再上检索筛)。清单带⚠️标记+DOI(只在DB里)=为何要python拼而非直接丢store/summaries文件夹。
- **自测全过**(monkeypatch run_claude不烧配额):真库20篇拼清单→解析→回填(tier/verify/无DOI篇都对)→slug防串号→兜底→哨兵→ask.py接线。**未做真端到端**(慢+烧配额,库重建中,等用户要再跑)。
- **📋 五方案速查表**(用户校准)拢进 `docs/qa-layer-design.md` **§10**;金字塔主干在 §9;讨论全程→SESSION 第九段。**代码未提交(等用户 push)**;库现20篇有总结(cron重建中)。

## 2026-06-19 04:00 EDT — 问答层定「金字塔」架构主干 + 决定先实现④(全读) → qa-layer-design.md §9
- 做了什么：用户审到"④现在能用、但会长到不止100篇、后面还有蒸馏层⑤，怎么搭不推倒重建"。讨论收口成**金字塔主干**写进 `docs/qa-layer-design.md` **新增 §9**（只追加，§4/§8 既有的"为什么做合成层/金字塔"原因保留不删，互为表里）。
- 定下的：①**贵的"读"建库时做一次缓存成层**（总结=每篇缓存、⑤合成层=跨篇缓存），**查询只读缓存层、为精确才下钻 PDF**——金字塔查询成本≈恒定（治"会长到不止100篇"），⑤是中枢非附加件（治"后面蒸馏"）。②**④ fan-out 全读的两个正当岗位**：(a)建⑤的离线工序(用户"总结+原文一起小agent处理"放这里对)、(b)`exhaustive`穷尽兜底模式；都不是查询默认。③合并永远单线程(MAST 17×)；⑤增量更新是领域真空→按簇蒸/矛盾显式存/精确回PDF。
- **用户拍板先实现④**（全读，现在能用、料薄时唯一可跑的）：落地次序=现在④临时路 → 总结铺开蒸⑤ → 几百+切②召回闸+⑤导航。④搭的 answer.py 契约层/ask.py 模式分发 ②③⑤ 全共用。
- 只动文档（design.md §9 + 本 log）。**下一步**：给用户过 ④ 实现计划 → 写 `retrieve/readall.py` + ask.py 模式分发 + answer.py 抽共享契约层。

## 2026-06-19 03:40 EDT — 出口落地计划收敛「纯全读 + 模式分发」(交接,未落代码)
- 做了什么：把知识库出口(问答层)的实现方案讨论收敛定稿，写进 `logs/SESSION-2026-06-18-kb-retrieval.md` 第八段。**无代码改动**，纯交接(用户嫌上下文长、要新开会话)。
- 定下的：①现规模默认=**「全读」模式**——python 把全部总结塞进一个 prompt、一个 Opus 答；**唯一工具=Read**(总结塞 context 保召回 + 给 Read 权限按需开 PDF 读一手保精度)，**不给 search/Task/自主搜索**。②**PDF 必须可读**(纠正一版过度限制:"不用工具"指不给 search/Task，非禁读 PDF)。③代码结构=**ask.py 模式分发器 + answer.py 共享契约层 + 每方案一个模块**(readall/pipeline/将来agentic/synthesis 各占模式槽，其他方案别写死掉)；退役不硬删(rerank 退默认留盘、understand 默认不跑留大库用)。
- 下一步(新会话接)：敲定全读 prompt 终版给用户过目 → 写 `retrieve/readall.py` + ask.py 改模式分发 + answer.py 抽共享契约层 → 单元自测 → log/commit。**约束**:库现 0 篇总结，搭好只能自测，真答案等总结回来。

## 2026-06-19 03:19 EDT — 问答框架实证深挖第三批 → 汇总进 qa-layer-evidence.md §7
- 做了什么：用户好奇"合成层/全读 vs 检索 哪个质量好、有无直接对比研究"。派 3 个 agent 把 `ref/papers/` 6 篇逐节精读（RAG综述2507.18910 / Agentic综述2501.09136 / PaperQA2 / OpenScholar / RAPTOR / GraphRAG）+ web 扒 2 篇 2026 新论文（SIGIR'26 Text Ranking in Deep Research 2602.21456 / lost-in-middle 2026）。发现+出处+可信度汇总进 `docs/qa-layer-evidence.md` 新增 §7（含新链接）。
- 关键结论：①"小库全读 vs 选择性检索"**直接对比不存在**（领域都在百万篇区间）；②最接近的真数据=GraphRAG **C0(预蒸馏层) vs TS(临时全摘)：质量打平、合成层赢成本省97%** → 合成层是"省/快/覆盖全"工具非"更准"；③多篇一致印证"顶层导航+下钻原文"（RAPTOR 必须保叶层、GraphRAG 细节被稀释）；④领域真建议="先把检索质量做好，agentic 救不了烂检索"（撞上我们6/17"召回是地基"）；⑤增量更新是所有论文的真空（GraphRAG 全量建图281min/1M token）。
- 只动文档（evidence.md + 本 log），无代码改动。框架仍 v1 草稿待用户诊断。

## 2026-06-19 03:09 EDT — 新建 remote-access/：让别的机器的 agent 能来查库（发现机制+SSH 远程执行）
- 做了什么：建文件夹 `remote-access/`（4 文件）放"如何让其他机器找到并查这个库"的全部材料：`README.md`(拓扑+原理:本机=常开服务机/主力机=客户端，走 SSH 远程执行而非 sshfs 挂载——计算+GPU+库留服务机)、`MEMORY-SNIPPET.md`(★要粘进主力机全局 `~/.claude/CLAUDE.md` 的指针节，附本机版)、`SETUP.md`(主力机侧步骤:SSH 免密+Host 别名 research-kb→测连通→装 wrapper→贴记忆→冒烟)、`ask-research-kb`(薄 wrapper，把参数安全转发给远程 ask.py)。
- 为什么：用户问"怎么让其他机器的 agent 来查库"。结论=本机当服务端、主力机 SSH 进来跑 `ask.py`（客户端零安装）；纠正了"sshfs 挂文件夹"想法（挂的是文件不是 GPU 算力+SQLite 网络 fs 写不安全）。这是 2.3②出口"别项目 agent 来查"的发现机制落地（6-16 撤回的全局指针，这次重新备好）。
- 状态：**已备好、尚未启用**。两点未做(留给用户):①主力机侧配 SSH+贴记忆(SETUP.md);②建议等库填实再启用——当前库已清空(见下条)、总结 0 篇，cron 正夜间重建中，查也查不出东西。服务机本身零代码改动。

## 2026-06-19 03:00 EDT — 清库残留视图修正：重渲染 topic.md + 删陈旧 ARS 导出
- 问题：用户发现其他 agent 仍看到"已总结文章"。排查=DB/总结文件/索引都真清了（0/0/0），但**渲染产物**没更新——`topics/*/topic.md`（旧总结表，43 处引用）和 `literature_corpus.yaml` 是清库遗留（只在 finalize/verify 跑时才重渲染，清库后没跑过）。
- 修：`render_topic.py` 重渲染两主题 topic.md（现 `已总结：0`、0 个 store/summaries 链接）；删 `topics/*/literature_corpus.yaml`（要用时重导）。
- 教训：以后清库要连派生产物（topic.md / literature_corpus.yaml）一起处理，别只清源数据。

## 2026-06-19 02:54 EDT — 实装 crontab：夜间 sum 两批 + 上午 verify_daemon（用户拍板挂上）
- 做了什么：本机 crontab 从空 → 装 3 行（PATH 头含 ~/.local/bin[claude]+nvm[codex]，python 直接用 `~/anaconda3/envs/research-agent/bin/python` 免 envguard re-exec）：① `0 2` ② `30 7` 各跑 `queue auto-sum-next 20`（夜间写总结，sum+finalize，相隔 5.5h）；③ `0 9` 起 `verify_daemon`（setsid nohup &，啃当晚核查积压）。
- 为什么：用户确认大方向对，让把"夜间 sum + 全天候 verify"两条自动化都挂上。daemon 不现在裸启的原因：刚清空库（0 总结），现在启会立刻发误导性「🎉已核完」即退；改挂 9:00（在 7:30 批之后），靠单例锁防重开。
- 验证：`crontab -l` 回读对；env python + claude + codex 三路径都在；cron 服务 active；冒烟（不烧 token）：select_next_topic→rl-general-toolbox(可做100)、daemon topics_with_unverified→[]（符合清库后预期）。
- 同步文档：`docs/nightly-cron-deploy.md`（auto-sum 去 verify、加 verify_daemon 行、换成本机实装的 env-python cron）。
- ⚠️ 时序：今天 2:00 已过，**首批 sum 在今天 7:30**，首次 daemon 9:00。想立刻见效可手动 `python pipeline/run.py <id> auto-sum-next 5`。

## 2026-06-19 02:12 EDT — 问答层实证两批合并成参考文档 `docs/qa-layer-evidence.md`（好找）
- 做了什么：把散在 SESSION 第五段(第一批 web 实证)+第七段(第二批+纠偏)里的**所有论文/对比/数字**拢成一份参考文档 `docs/qa-layer-evidence.md`：三种打法坐标系(①单上下文/②fan-out/③检索工具)、论文主表(CoA/LongCtx-vs-RAG/PaperQA2/MAST/lost-in-middle/Haystack/map-reduce)、PaperQA2 超人数字+消融+保留、②③接力非比赛、新旧之辨(2026仍真)、证据→设计落点对照、三档规模、原始链接。
- 为什么：用户反映框架的对比/论文证据被劈成两批夹在叙事里、不好找,要"放一起好找一点"。
- 接线：`docs/qa-layer-design.md` 顶部改"配套三件套"(设计/证据/时间线)+§3 实证支撑指向 evidence 文档;SESSION 第七段末加指针。SESSION 第五/七段保留当"怎么想到的"时间线,不删。
- 全是文档,无代码。⚠️ 领域迁移保留已写进 evidence 文档头(基准多为生物/通用 QA,非我们 RL 库,只定方向)。
- 做了什么：①完整备份到 `logs/summaries-wipe-20260619-0206/`（整库 papers.sqlite + 41 篇 store/summaries + 11 个标记文件，3.2M）。②DB：`DELETE FROM summary_versions`（84→0）、`status='summarized'→'pdf_downloaded'`（41→0，221 篇全回可重做、PDF 0 丢失）、`summarized_at=NULL`。③文件：删 store/summaries/*、删所有标记（verified*.json / verify_status*.json / summary_verification*.md / summarize_worklist.json 含 .old 变体）、删失效索引 db/vec.sqlite + db/fts.sqlite（重做后重建）。
- 保留未动：**quality_tier/quality_signals**（来源质量，flag47/ok117/trusted57，与总结无关、重做复用）；topics/*/topic.md 与 literature_corpus.yaml（派生产物，重做后自动重渲染/重导）。
- 为什么：用户要用新流程重写总结。⚠️ 我已核实并指出这 41 篇其实是 2026-06-18 新流程产物（新模板含「适用边界」、经 report-only 核查+整篇重做到 v2-v4），用户看过证据后仍决定清。
- 未挂起：cron + verify_daemon 都没启，等用户先复查总结流程/prompt。

## 2026-06-19 02:03 EDT — 方案B 实证夯实 + 三处认错纠偏 + 合成层升格（全是讨论/文档,未落代码）
- **背景**：接 01:23 那条(定两套模式后)。用户没让动代码,而是逐层追问把方案B的实证地基夯实;过程中我犯了三处含糊/过度推销,被用户抓出纠正。本条记纠偏,详见 SESSION 第七段。
- **实现岔路定**：方案B 用"claude 真·自驱(A)"——`ask.py` 起 `claude -p`(开权限/cwd=仓库根,照 bot.py)给地图+工具(search可调)+纪律,让它自己探索;不用"python 编排 fan-out(B)"。用户要 prompt 写时先过目;诚实哨兵改"真探索过才说没有"(非机械短路)。新文件待写 `retrieve/explore.py`。
- **web 实证(第二批,逐条核)**：把"fan-out"拆成 ①单上下文全塞/②并发多agent分读/③用检索工具 三打法。①②=CoA(2406.02818)②高10%;①③=LongCtx-vs-RAG(2501.01880)装得下时①反+4.4%;②③=CoA里②>③但可叠;合并是雷区=MAST(2503.13657)+map-reduce掉数字→单线程+抽证据;新旧之辨=lost-in-middle(2307.03172)2026仍真(LongBench v2/HELMET)但变弱、工具价值转"注意力卫生"。
- **三处认错(防再犯)**：①**"装得下"含糊**→澄清两个轴(轴1读/轴2合成单上下文),文档指轴2,41篇两轴都不触发;②**拿PaperQA2"超人"背书我们搭建=过度推销**→超人(85.2%>博士73.8%)是几百万篇区间,对41/1000篇不构成依据,已退回;②③是"按库大小接力非二选一比赛"(读得完用②/读不完用③,无被迫选差);③**漏了合成知识层**(用户点"净化语料库"找回)→升格为"比③更聪明的语义路由/索引",是让agentic活到库长大的关键。
- **规模临界修正**：切大库模式落在**几百~1000篇**(1000篇总结~3M token塞不进1M),非原写的2000。
- **改的文件(全文档)**：`docs/qa-layer-design.md` §8(切换信号/②③接力/两个轴/合成层升格 四条纠偏回写)、`logs/SESSION-2026-06-18-kb-retrieval.md`(第七段:全程讨论+实证出处)、本 claude_log。**无代码改动。**
- **下一步**：写 explore.py(prompt 先过目) / 合成层专门摊开(排总结铺开后)。

## 2026-06-19 01:40 EDT — verify 从夜间 auto-sum 链摘出，全交给 verify_daemon（治 cron×daemon 抢 codex 配额）
- 做了什么：`AUTO_SUM = ["sum","finalize"]`（去掉 verify）；`run_auto_sum` chain 删掉 verify 那行；run.py 的 usage/注释/docstring 三处 + CLAUDE.md auto-sum 说明同步改成"夜间只 sum+finalize / verify 全天候交给 tools/verify_daemon.py"。`verify` 阶段本身保留（daemon 调用 + 手动 `run <id> verify`）；燃尽报告 `📋待核N` 不动。
- 为什么：之前 verify 还绑在夜间 auto-sum 里跑，而新建的 verify_daemon（2026-06-18）也整天敲 codex——两边抢同一个 ~20次/窗的配额。用户拍板拆开：夜间纯 sum、verify 由 daemon 独占。
- 文件：pipeline/run.py、CLAUDE.md。py_compile 通过。
- ⚠️ 运维待办：现在夜间 cron 跑完不再 verify，**daemon 必须单独拉起才会核**（不随开机自启）；`docs/nightly-cron-deploy.md` 若提到 verify 需同步（本次未改该 runbook）。

## 2026-06-19 01:26 EDT — escalate_verify 拆清"capped vs sampling"两模式（治 --start-pct 100 + 上限的冗余）
- 做了什么：escalate_verify.py 引入 `capped_mode = max_papers is not None`。capped（run auto，传 --max-papers）= 不抽样/不翻倍，所有未核都合格、最近优先，由 --max-papers 定量，--start-pct 在此模式忽略；sampling（手动，不传 --max-papers）= 抽 pct% + 命中翻倍扩面（escalate 本名由来）。抽样翻倍分支加 `not capped_mode` 门，fresh 选取按模式分叉，日志显示 fresh[capped]。
- 为什么：run auto 路径已有"最近优先 + 上限15"后，`--start-pct 100` 的抽样/翻倍逻辑休眠（pct=100 翻不动=死代码）。用户要求把"一般手动才用的抽样逻辑"独立出来、夜间路径只认 --max-papers。
- 文件：pipeline/verify/escalate_verify.py（docstring 两模式 + capped_mode 分支）、pipeline/run.py（verify 阶段去掉冗余 `--start-pct 100`，只传 --max-papers）。py_compile 通过。

## 2026-06-19 01:23 EDT — 检索定两套模式(小库agentic/大库索引)+ 决定先搭并默认用方案B(未落代码)
- **背景**：用户问"为什么不让 claude 直接进文件夹找、并发开小 agent、token 又不是问题,中间加索引层不是加摩擦?" 讨论后判定:当前 ~41 篇规模下用户直觉对——暴力全读召回100%、更简单。索引此刻价值不在召回,在"地图能力(找重复/相似/引用邻居)+低延迟+能活到库长大"。
- **用户拍板**：①把方案B(agentic 检索)搭起来,**目前先默认用方案B**;②方案A(索引)不删,留作**大库模式兜底** + agentic 随手调的工具("A是B的零件");③**mark 成两套模式**:小库 agentic / 大库索引,按总结篇数切换,2000篇不会很快到、真撞到全读吃力再切。token免费是这次把agentic提前的主因(原先怕高频探索烧token,顾虑消)。
- **mark 落档** → `docs/qa-layer-design.md` 新增「## 8. 检索的两种模式」(对照表+切换信号+与合成层协同) + SESSION 2026-06-18 第六段(讨论全程)。
- **状态**：决策已记;方案B **未落代码**,下一步给用户过设计计划(working-style:plan→确认→实现)。
- **背景**：逐段审查问答管道审到第2步(rerank)，用户从"这步怎么做"一路追问，把整个**问答出口架构**重想了一遍。结论写成正式设计文档。
- **新增 `docs/qa-layer-design.md`(v1 草稿)**：问答层框架——总纲(贵的阅读只做一次/离线缓存)、地图(总结/合成层/引用图)vs实地(PDF)、consumer=卡壳来问的agent+质量第一+诚实哨兵、主管道7步(理解→召回→引用图放大→分诊→**装得下直接读PDF/装不下fan-out抽证据**→核验→蒸馏交付)、跨文章内容一等公民、三档查询、agent出口契约、与现有代码delta、6条待定薄弱点。
- **web 实证支撑**(2026-06-19 搜的)：Chain of Agents(分读长文+10%)、lost-in-the-middle(~32K劣化)、Anthropic多agent(+90.2%但15×token/需共享上下文不适合)、Cognition+MAST(无结构放大错误17×/写入单线程)、压缩vs全文(装得下直接读胜/总结再汇总掉数字+串味)、混合8场7胜。出处列在 SESSION 第五段。
- **关键洞见**：总结=已缓存的fan-out;fan-out位置在"读"(独立)不在"合并"(协调);装得下/装不下是直接读vs拆分的分界。
- **讨论全程 + 推理链 + 实证出处** → `logs/SESSION-2026-06-18-kb-retrieval.md` 第五段。
- **状态**：框架未落代码;用户下次先诊断6个薄弱点→定稿→才改 rerank/answer。会话到此结束。

## 2026-06-19 00:10 EDT — 确认 claude 模型 + 定"先用默认"(无代码改动,记决定)
- **排查**：流水线所有 `claude -p`(打分/总结/重做/claude应急核查/猎源hunt/重排rerank/问答answer/理解understand/更新update + bot.py)统一走 `lib/claude.py` 的默认 `SUMMARY_MODEL=opus`,**无任何一处传 model= 覆盖**。最小 probe(`--model opus --output-format json`)确认 `opus` 别名 → **`claude-opus-4-8`(Opus 4.8,1M 上下文,max out 64k)**;JSON 里另有少量 `claude-haiku-4-5` = Claude Code 后台辅助小活,非主力。
- **决定(用户 2026-06-19)**：**先全用默认 Opus 4.8,不分档**。已知省 Max 额度的最划算做法=把"轻判断"阶段(score / understand / rerank)降到 Sonnet、Opus 只留给 summarize/resummarize——**记下,暂不做**(要做需在对应调用处传 `model=`,SUMMARY_MODEL 只是全局默认)。
- **关于 telegram 额度上报**：查实 `claude` CLI **无** usage/limit 命令(`/usage` 仅交互 TUI),Max 限额不公开 → "还剩 session/周 多少"**拿不到**;只能事后汇总"花了多少"(`--output-format json` 的 token+等效$,`LLM_USAGE_LOG` 默认关)或撞限流反应式报重置时刻。**用户:那就算了,不做。**
- **本会话待定(未做,供下次接手)**：①把 verify 从夜间 auto-sum 链摘掉 + Telegram 报告拆成"总结线/核查线"两套(已讨论+举例,方向定,未实现);②真正挂起 verify_daemon(用户说挂再挂);③试跑越界改的 5 篇旧总结(还原/保留未定);④清理 35 篇旧总结+全库铺开;⑤本会话整批代码改动是否提交(push 仍用户来)。

## 2026-06-18 23:29 EDT — 建 verify 全天候排空守护进程(verify_daemon,未挂起)
- **缘由(用户)**：codex 平时闲着,想让 verify 整天后台啃核查积压;撞配额别停死、睡到窗口恢复再续;啃完报告一声自停;喊停能停。**用户要求:建好但先别挂起,说挂再挂。**
- **配额窗口认知纠正**：此 ChatGPT 订阅是几小时级滚动窗口(实测 2am 满→3.5h 仍0→8h 才恢复),非 1 小时。所以退避要睡到窗口重置,且吞吐天花板 ~20次/窗口×4-5窗口/天≈80-100篇/天(排空221约2-3天)。
- **新增 `pipeline/tools/verify_daemon.py`**(单例 pidfile,不随开机自启同 bot.py):循环挑队列里有待核的最高优先主题 → 跑 `run.py <tid> verify`(带 --max-papers 上限+最近优先+render+reindex)→ 撞配额则解析"try again at X"睡到点自动醒(解不出睡默认 ~5.5h,`VERIFY_WINDOW_SLEEP` 可调)+发TG;有进展接着吃窗口;无进展又非配额(坏/缺PDF)跳过该主题免空转;全清发🎉自退;`touch logs/verify_daemon.stop` 或 kill 即停。起停命令见脚本头注。
- **配套(verify_summaries.py)**：`parse_retry_until()` 解析配额报错里的重试时刻(at H:MM AM/PM 或 in Xh Ym)+ `note_quota()` 写 `logs/codex_quota.json` 给 daemon 读;escalate/main 的配额分支调它、Telegram 带"约 X 后恢复"。
- 验证(全程未调 codex):5 文件 py_compile;parse_retry_until 三类样本解析对;daemon 只读 helper(unverified_count/topics_with_unverified/skip过滤/read_quota_state)全对;note_quota→read_quota_state IPC round-trip(写2:30AM→读到→读完即清)过。**确认无 daemon 进程、无 pidfile=未挂起。未提交。**
- **未做(等用户)**：①真正挂起 daemon(用户说挂再挂);②是否把 verify 从夜间 auto-sum 链摘掉(daemon 独占 codex 免双花)——暂留,等挂 daemon 时再定。

## 2026-06-18 23:13 EDT — verify 限量(每次≤N篇)+ 报剩余待核 + 修 codex 配额检测根因(Bug A)
- **缘由(用户)**：夜间核查不该每次扫全部未核(积压一多就把 codex 配额灌穿,r1还行→r2复核全挂);要(a)夜间只核当晚那批、有硬上限"最多N篇",(b)核查完报告还剩多少没核。依据 `logs/SESSION-2026-06-17-codex-quota.md`:此订阅一个配额窗口只够 ~20 次重型核查。
- **修根因 Bug A**(`lib/codex.py`)：报错原只抓 stderr,但"usage limit"横幅在 **stdout**→`str(e)` 永不含该串→熔断/告警从不触发。改为异常带 stdout 尾部。**这是 23:02 那条 Telegram 告警能真正生效的前提**(否则形同虚设)。
- **硬上限 `--max-papers M`**(`escalate_verify.py`)：封顶本次核查总篇数(含 major 复核),到顶即停、剩余报为待核(`verified.json` 按轮落盘=断点续核);**篇序改"最近总结优先"**(`load_candidates` 加 `summary_created`,取代随机抽样)=夜间先核当晚批。复核轮自然顺延到下次/下窗口(治"r2 必撞穿")。移除不再用的 `random` import。
- **报剩余待核**：escalate 收尾算"已总结但没核到当前版本"的篇数 → 进报告头 + run.log;run.py 加 `unverified_count(tid)`,夜间 `burn_down_msg`(📋待核N篇)+ `queue_report`(每主题"待核N")都带上。
- **接线**(`run.py`)：`steps('verify')` 默认 `--max-papers VERIFY_MAX_PER_RUN`(顶部常量=**15**,window~20留margin)→ 夜间/手动/全量 verify 一律有界;积压靠多跑几次安全排空。配套建议:夜间 sum 批量 20→~10-12 让 verify 跟上(用户那条 cron 的 N,自己定)。
- 验证(只读/干跑,未调 codex):4 文件 py_compile 过;max_papers 解析 15/None;steps(verify) 带 --max-papers 15;unverified_count 实测 gt=19/dhi=1;燃尽报告含"📋待核19篇"、队列报告含"待核19/待核1"。**未提交**。
- CLAUDE.md 核查节同步(escalate 签名加 --max-papers + 上限/篇序/剩余报告 + Bug A/熔断说明)。

## 2026-06-18 23:02 EDT — verify 撞 codex 配额:加 Telegram 告警 + 干净停止
- **缘由**：原本 codex 撞 ChatGPT 用量/限流上限时，verify 只在日志里静悄悄 abort、退出码仍 0，外层 auto-sum 照常收尾——配额截断看起来跟正常跑完一样，用户无感知。用户要求加报错停止机制并 Telegram 通知。
- `verify_summaries.py`：新增 `_is_quota_err()`(认 usage limit/429/rate limit/quota)+ `quota_hit(failed)`；原熔断器(`tripped`)改用 `_is_quota_err` 统一判据；`main()` 撞配额 → `notify()` 发 Telegram + run.log 标 `[codex配额中止]`。
- `escalate_verify.py`：每轮 `verify_batch` 后先查 `quota_hit(failed)` → 命中则发 Telegram(带 topic + 本轮已核/累计已核/约 N 篇待核 + "重跑即从断点续核") + 干净 break(不再升级抽样去烧枯竭额度)；报告 note 顶部标 `⚠️本轮因 codex 配额中止`。
- 设计选择：verify 仍属 advisory，**退出码保持 0**(不改流水线语义)，靠 Telegram + 日志 + 报告三处显式告知；verified.json 按轮落盘，额度恢复重跑即续核。
- 验证：py_compile 过；`_is_quota_err`/`quota_hit` 单测(usage limit/429/quota=True，普通 parse 错=False)；escalate 同段 import quota_hit 成功、共享同一份；真发了一条测试 Telegram(notify ok=True，用户已收到)。**未提交**。
- 顺带答疑(无代码改动)：①核查非每次全核——靠 `verified.json` 增量，只核"版本对不上/没核过"的；这次扫 40 是本机 verified.json 基本空。②major/minor 一直是四态(pass/minor/major/unverifiable)没去掉，06-18 改的是命中后动作(report-only + major 整篇重做，不再 correct_summaries 打补丁)。

## 2026-06-18 22:49 EDT — 理解层:claude 失败改"直接报错"(关掉静默回退)+ --no-understand 标 debug 专用
- 改 19:45 那条的行为(用户拍板)：`understand_query` 不再 claude 失败/解析失败就返回 None 让调用方静默回退老分词——**老路有 P-A/P-B bug,悄悄退回去=给坏结果还不吭声**。现在 claude 失败让异常抛上去、解析不出抛 RuntimeError，**查询响亮地失败**。
- `--no-understand` 留着但**标成 `[debug专用]`**(help + docstring + ask.py 头注)，明说正常跑别用——它是绕过理解层的唯一明路。
- 实测：`CLAUDE_BIN=__nope__` 模拟 claude 挂 → 默认路径直接报错 exit 1(不回退)；`--no-understand` 仍跳过 claude 走老路 exit 0。
- 文件：`pipeline/retrieve/understand.py`、`pipeline/ask.py`。**未提交**(等用户确认后随下次一起 commit)。

## 2026-06-18 22:43 EDT — 新 summarize/verify 流程小批试跑(2篇)+ 旧总结全量备份
- **背景**：summarize/verify 层 06-18 大改后(d5b58a7：边读边写去 note_plan、核查 report-only、major→整篇重做)，首次拿真实库端到端试跑。用户定：全库 221 篇都用新流程重做，但先小批试 2-3 篇验证。
- **备份(回滚锚点)** → `logs/summaries-baseline-20260618/`：`store/summaries` 全量(77 md)+ `db/papers.sqlite` 快照 + 两主题 verify/worklist 产物。
- **试跑** `run rl-general-toolbox auto-sum 2`：2 篇净新论文写出新流程 v1(Augmented PPO / Safe RL w/ Probabilistic CBF)，质量符合设计(原子句+内联 strength、讲直觉、数字让位 PDF、新增"适用边界"段、不脑补附录)。
- **意外**：auto-sum 的 verify = `escalate_verify --start-pct 100` **核查全主题、非只新篇**——扫了 40 篇旧总结，揪出 5 篇 MAJOR(GAE 数字+张冠李戴、Penalized PPO 残留"伪造核对背书"、End-to-End Safe RL 定理条件写窄、What-Matters V-trace 设定写错、Tiered Reward 过度声称)，**已就地整篇重做成 v4/v2**。原件在备份里可对比。新核查抓得准、且根治了旧 correct_summaries 伪造背书 bug。
- **已知坑**：verify round2(剩 19 篇)codex 全失败(限流/用量到顶)，脚本干净中止、进度按轮落盘。r1 的 26 篇核查有效。
- DB：gt summarized 39→41，summary_versions 77→84。待用户看过产出后再清理那 40 篇旧总结、全库铺开(夜间 cron 用户自挂)。

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

## ——— 以下为 2026-06-18 建 claude_log 之前的历史回填（迁自旧 SESSION 笔记，新在上、老在下）———

## 2026-06-18 — 主链脚本按功能段分文件夹（重构，commit c93bb51）
- 做了什么：主链 14 脚本从 `pipeline/stages/` 一锅堆 → 拆进 4 个功能段文件夹 `find/`(discover/score_auto/commit) `fetch/`(fetch_oa/recover_oa/recover_agent/fetch_tierb) `summarize/`(build_worklist/summarize_auto/register_summaries/render_topic) `verify/`(verify_summaries/correct_summaries/escalate_verify)。用 `git mv` 挪（14 个全识别为 rename、历史保留），各段加空 `__init__.py`。
- 为什么：14 脚本堆一处难维护——改"找论文"要在 14 个里翻出 3 个、心里装不下全貌。用户要按功能分文件夹、文件仍各自分开（不合并）。
- 关键判断：agent 调用不受影响——`lib/claude.py`/`lib/codex.py` 是**跨进程**调外部 CLI（which 找 + stdin 进 + stdout 出），与 Python 文件夹/import 结构无关。真正要小心的只两点：① run.py 写死的 13 处调度路径跟着改；② 保持 `cwd=仓库根`（claude -p 按 cwd 读 CLAUDE.md）。摸查耦合：**唯一跨段 import = `verify_summaries.py` → `from summarize.summarize_auto import full_text`**（靠 path-shim + 段有 `__init__.py` 才解析）；全局 ~/.claude/CLAUDE.md 不引 stages/ 路径。
- 配套：run.py `steps()`+`run_auto_sum` 13 处路径改 `<段>/<脚本>.py`，**仍 subprocess spawn + cwd=ROOT**（进程隔离/agent 行为不变）；各脚本 Usage 注释更新；同步 `pipeline/ARCHITECTURE.md`+`CLAUDE.md`，写入代码组织规范（以后主链一律按功能段分文件夹）。
- 验证（全过）：全量 py_compile；14 脚本 import 烟雾测试（含跨段那处）；run.py 调度起的是新路径；git 全识别为 rename。

## 2026-06-17 — 当日多线并行（总结层设计转向 + 打分漂移 + codex 额度，索引）
- 当日多条线并行（本会话只写 markdown/记忆，不碰 db、不跑 pipeline、不改代码——另有 agent 在并发拉论文）。各线细节已分别吸收进对应模块/文档，这里只留索引与决策。
- 线索：① 架构辨析（改库 lookup vs 检索 retrieval；打分不照搬 summary 的 verify 闭环）。② 打分跨批次漂移（另一 agent 已实现并在跑：rubric 通用化 + `topic.json.score_anchors` + batch 20 洗牌 + boundary_rerank，详见 `docs/score-drift-research-findings.md`）。③ codex 额度烧穿 + verify 全盲（连挂三班；根因=外部额度 + 抓不到真错误致熔断失灵；cron 间隔调 4.5h→5.5h，2:00/7:30）。④ 新旧总结逐篇对照（6 agent 核 16 篇三版，发现修正环节会**推翻 codex 正确认定+伪造核对背书**、旁白串正文）。⑤ 初衷重对齐 → 总结=方法/直觉分诊层（判"值不值得深入"），不是数字库；两段式（读总结判→PDF 看细节）；只守语义/方向忠实（`docs/summary-design-principles.md` v1）。
- 用户当日已定决策：核查**保留但改 report-only 三分类**（Supported/Unsupported/Omitted），**取消自动修正环节的裁决权**（根治"反向裁决+伪造背书"致命 bug）；数字保留但精度权威在 PDF；老 221 篇先全不动（已备份 `logs/wipe-summaries-20260617/`）；cron 当晚暂停。
- 后续这些决策已在 06-18 落地为：核查 report-only + major 触发整篇重做（取代 correct_summaries）。

## 2026-06-10 · 运行线 — 两主题放量到 129/100 + tierb 出版商适配 + topic2 建立 + 远程看屏
- ① topic1 `rl-digital-human-interaction` 放量 40→100：漏斗 raw 1560→去重 1158→池 200→增量入库 +95=**129 篇**；全文 OA 68 + recover 12 + tierb 15 = 95/95 零丢失，总结 95 篇 0 失败。**端到端实跑验证 tierb（待办#1 关闭）**：首轮 11/15 成，人工只点 1 次（ScienceDirect Turnstile）。
- ② tierb findPdfUrl 跨出版商适配（首轮 4 篇"landing 无 PDF 链"）：**IEEE Xplore**（SPA 抓不到 DOM 链→从 URL 取 document 号构造 `stampPDF/getPDF.jsp?arnumber=`）、**DSpace 机构库**（选择器加 `a[href*="/bitstream"]`、`.pdf?`）、**SPA 首轮没找到等 5s 重试`。重跑 4/4 成功，且 NYU 会话有效没弹 Duo。
- ③ 新建 topic2 `rl-general-toolbox`（"RL 通用工具箱+诊断箱"，用户思路=训不出来要 reward 设计/算法工具箱/CBF 安全增强；我生成 14 组检索词含 CBF/safe RL/TD3-SAC 改进/model-based/横评，用户过目确认；target=100/窗口12年）：漏斗 raw **3407**→去重 2269→池 200→首跑入库 100（质量闸 block0/flagout3/suspect1）；全文 OA 62 + recover 10 + tierb 14，**8 篇与 topic1 重叠直接复用总结**（全局库设计生效）。
- ④ topic2 tierb 6 篇失败修复：诊断出 6 篇里 5 篇本该免费却漏到 tierb，仅 1 篇真付费墙（Wiley）。**根因=arXiv 取 PDF bug**——`recover_oa` 旧逻辑 strip 版本号后裸 `/pdf/<id>` 个别 404（如 2211.15205）→ 改 `arxiv_pdf_candidates()` **枚举 bare+v1..v最新**取真 %PDF。**Wiley 适配**：`/doi/pdf/` 是 HTML 拦截页→直返 `/doi/pdfdirect/{doi}?download=true`。
- ⑤ ★本会话主交付：手机过验证=远程看屏（Tailscale + noVNC）。验证必须点在机器那个真实 Chrome 上（cf_clearance 绑指纹+IP），故方案=让手机远程看到并点到机器的 `:1`。数据流：手机 ⇄ Tailscale ⇄ websockify（托 noVNC + ws→VNC）⇄ x11vnc（:1）⇄ Chrome。安全：x11vnc 只听 localhost、唯一对外的 websockify 绑 Tailscale IP `100.83.75.76:6080`、VNC 密码、不开 Funnel。落地 `pipeline/remote_view.sh`（幂等启动 + 首跑生成随机密码，密钥 `config/x11vnc.{pass,plain}` gitignored）+ `fetch_tierb.ensure_remote_view()`（开跑预热、验证时 Telegram 带 noVNC 链接）。**注：此远程看屏后于 2026-06-10 即被用户以安全顾虑封存（MOTHBALLED），代码留默认关。**

## 2026-06-10 · 质量线 — 质量评价体系（硬信号+标记优先）诞生 + Codex 跨模型评审团上线
- ① 硬信号质量体系上线（`lib/quality.py` + `config/quality/`）：抓 Beall's 衍生黑名单（stop-predatory-journals，**1309 期刊 + 1161 出版商**）加工成规范化 txt；发现 IJISRT 不在名单（2017 停更）→ 建 `local_blocklist.txt` + `doi_prefix_blocklist.txt`（IJISRT=10.38124，前缀挡法改名躲不掉）+ `venue_whitelist.txt`（38 个顶会顶刊免疫误杀）。OpenAlex 补采 `is_retracted/is_in_doaj/publisher`。修一类误标：OpenAlex 常把已发表论文 venue 标 arXiv → 改"有正式 DOI（非 10.48550）的不算预印本"，flag 46→34。
- ② **设计转向：用户拍板"标记优先，不一刀切 ban"**——核心论点（用户认可）：**污染不发生在存进去，发生在用的时候忘了它是什么**。block 只留死刑信号（撤稿 + DOI 前缀黑名单）；名单命中降为 **suspect**（照常入库但标记持久化到 `papers.quality_tier/quality_signals`，每个下游出口认标记：summarize 注入质疑模式、render 标 ⚠️+低可信节、未来 RAG 必过滤/降权）。commit 闸：block 拒、suspect/flag 需 relevance≥45。`audit_quality.py` 回溯审计 + verdict 回写 DB（--apply 只删 block）；对 129 篇实跑 block0/suspect0/flag34（全真预印本）/trusted36/ok59。
- ③ Codex 跨模型评审团上线（ChatGPT 订阅零 API 费）：`lib/codex.py`=`codex exec --output-last-message`，镜像 lib/claude.py。**打分魔鬼代言人**（score_auto，`quality.codex_panel` 默认 false 没开）：Codex 同批找"该拒"理由→`panel_objection`；commit 合议=边界分(<60)+异议→挡，Codex 无否决权；试金石 3 篇全对。**总结核查** `verify_summaries.py`：suspect 必核 + 抽 10%，Codex 对照原文核数字/论断只出报告；首测 2 篇即抓 1 个 major 幻觉（把"行为变化未被预先指定"写成"面对训练中未见的下坡"）。
- ④ 顺带：确认 `fetch_tierb` Python 版首次端到端实跑通过（4/4，待办#1 关闭，另一实例触发）；score_auto 打分 prompt 带 venue 了。

## 2026-06-09 — Tier B 准备 + 库清洗（删 6 篇垃圾/跑题）
- 库清洗（用户拍板全删 6 篇）：#29 IJISRT 掠夺水刊（相关性被标题骗到 55）、#36 AI 与动物常识（跑题）、#33 VR 社交态度检测（跑题）、#38 虚拟驾驶员认知 RL（发 RFID 刊错配）、#32 2014 行人群体仿真（旧+偏题）、#39 下肢外骨骼增强（擦边）。事务内删 citations/paper_topic/papers，按 relevance 重算 rank（剩 34 篇）。这是 06-10 质量体系（硬信号自动挡掉掠夺刊）的直接动因。
- 免费捞 recover_oa：剩 4 篇全失败（ASE/AMP unpaywall 403；Walk This Way 等无免费源）→ 全确认走 Tier B。现状 34 篇=30 summarized / 3 pdf_failed / 1 discovered。
- Tier B 设计（已与用户确认、待实现）：opencli 用常驻 profile 开代理 URL→探到登录/Duo 页→Telegram 喊用户过 Duo→会话活着一口气抓完。**取 PDF 不碰 cookie**（httpOnly）让 Chrome 自己下（两路：network 抠响应体 / wait download 搬下载目录）。跑通后固化为 fetch_tierb，复用 slug+pdftotext+落库。卡点=等用户给真实 NYU 代理 URL 反推改写格式。

## 2026-06-08 — 流水线初建（Node/JS）+ 首测 target=40
- 主题 `rl-digital-human-interaction`。从零搭起整条流水线（当时是 Node/JS，后于 06-09 整套迁 Python）：5 表 SQLite（papers/topics/paper_topic/summary_versions/citations）；多源发现 discover（OpenAlex/Semantic Scholar/arXiv/PubMed）+ 去重 merge；相关性打分关卡 score（agent fan-out，按摘要打分滤掉高引但跑题论文）；fetch_oa 下 OA 全文 + arXiv 回退 + pdftotext；summarize（每篇一 agent → 中文 v1.md）+ register/render；commit 追加式（增量跑）；prepare/update/register_updates（手动版本化更新）+ suggest_updates；cross_topic（跨主题共享 + 引用桥）；文件名重构为标题 slug（migrate_slugs，81 文件重命名）；一键编排 run.sh。
- 首测漏斗（target=40）：discover 原始 1760→去重 1328→候选池 80（69 有摘要/64 OA）；score 80 篇（8 agent/121k token/44s）；commit eligible 59→选 40（相关性 38–96，32 OA，13 引用边）；fetch_oa 第一轮 21 ok/11 fail，arXiv 回退 +6=27 篇全文（5 篇 403、8 篇非 OA 归 Tier B）；summarize 27 篇（首轮 19 ok+8 限流→重建 worklist 补跑→最终 27 全总结）；对 1 篇做了 v2 版本化更新。
- 当时库状态：1 主题/40 命中/27 已总结/13 引用边。教训/验证：总结质量验证 OK（PADL 读了全文、批判紧扣主题）；Semantic Scholar 无 key 多次 429（已降级）；summarize 遇 API 限流可重跑补齐（幂等）。
