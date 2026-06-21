# find — STATE（层积日志）

> 写法：**新在上、老在下、不删**，每条标题带日期+时间戳。最顶一条 = 此刻状态/卡在哪；往下翻 = 历史。
> README.md 是定型设计（覆盖更新）；这里是带细节的过程账（含旧 SESSION 的"为什么"）。
> 局部改动记这里；跨模块/全局改动记 `../../../claude_log.md`，这里只留一行指针。

## 2026-06-21 06:12 EDT · 坑：drive.py 大池扩展易超时——确定性收尾兜底
- agentic-knowledge-synthesis 从 50→~100 扩展:`drive.py`(orchestrator)**跑满 50min(timeout 3000)超时被杀**,前期已扩 topic.json 检索词+seed、池 77→587、打分 3/5 facet,但 **commit 前被杀=本次 find 不算数**。
- **应对(已验证可行)**:别盲目重启 orchestrator(可能又超时)。改确定性收尾——`score_auto`(idempotent,补全剩余 facet 打分)→ `commit --plan` 看分布 → 人/接手 agent 定 `commit --keep <facet>=N` 按相关性提交。本次新增 48 篇,主题达 98 source。
- 经验:**目标翻倍这种大扩展,orchestrator 单次 50min 常不够**(discover 多 facet + 嵌套打分 + 子 agent 慢)。要么给更大 timeout 分多次、要么直接走确定性链。详见 `../../../claude_log.md`(06:12 条)。

## 2026-06-21 03:44 EDT · 指针：web 线拆分——discover_web 改为只发现（详见 claude_log）
- `discover_web.py` 现**只管发现**(无数量上限,够格直接落库 kind=web/status=discovered;不打分;留痕 web_candidates.json + topic_state[web])。**抓正文+落盘搬到 `fetch/fetch_web.py`**(对齐论文 discover→fetch 两段);find 不再 import fetch。下面 03:02 条那套"抓取 agentic 化"逻辑整体迁到 fetch_web。详见 `../../../claude_log.md`(03:44 条)、fetch STATE。

## 2026-06-21 03:02 EDT · X 二期：discover_web 抓取 agentic 化（工具箱交给 agent）
- 用户定"提供抓取工具、怎么看交给 claude"。抓正文阶段重构：agent 拿 WebFetch + Bash(opencli 真 Chrome：open/screenshot/extract) + Read，自己决定静态 WebFetch 还是动态截图+读图。脚本只管 Chrome 起停+独占锁（`start_chrome()` 复用 fetch_tierb 的 `chrome_lock`/`ensure_chrome`/`close_chrome`，防越开越多），起不来降级纯静态（`WEB_NO_CHROME=1` 亦可强制）。opencli 截图=`browser <session> screenshot <path>`。真跑前置：隔离 profile 登 X 账号。详见 `../../../claude_log.md`（03:02 条）。

## 2026-06-21 02:26 EDT · web 发现入库落地：discover_web.py（blog/技术报告，kind='web'）
- 2026-06-20 16:16 敲定的"博客/网络源扩展"落码了（当时纯设计）。新建 `find/discover_web.py`：agent 联网搜（复用 hunt 外壳 `run_claude`+WebSearch/WebFetch）→ prompt 软判①相关性②内容质量 → 抓正文 markdown 落 `storage/papers/<slug>/source.md` → `upsert_paper(kind='web')`+`set_paper_topic` 入库 + URL 规范化去重。**套论文 discover/commit 骨架、不另起炉灶**；跳过 score、不总结（worklist 排除 `kind='web'`）。注册 `run.py <id> web`（opt-in，不进 AUTO）。
- 与旧"add_url"副轨的关系：这就是它的实现，但**改成自动发现（非手动喂 URL）+ 复用 store 入库出口**（`upsert_paper` 的 kind 改成参数）。地基（`source_path`/`kind` 列）见 claude_log 02:14。真跑待用户（billed）。全局账见 `../../../claude_log.md`（02:26 条）。

## 2026-06-21 00:39 EDT · 指针：facet 现在落盘了（跨模块，详见 claude_log）
- `commit` 经 `store.set_paper_topic` 把每篇的 facet 写进新列 `paper_topic.facet`（调用处未改，传的 `p` 本就带 facet）。供 retrieve 日后按 facet 过滤用。agentic 旧行已从 candidates.json 回填。全局账见 `../../../claude_log.md`（00:39 条）+ fetch STATE。

## 2026-06-20 22:48 EDT · TODO-6 验证场跑通(真实数据)+ 抓出并修两个 bug

> 拉起 orchestrator 真跑 agentic-knowledge-synthesis(冷启动,生产库)。**验证成功:端到端跑通、6 奠基作全回库。** 过程抓出两个 bug,都已修。
>
> **结果**:discover faceted(5 facet/pool 70)→ seed 6/6 → score_auto[faceted x5] 75 scored → commit FIRST RUN +39 → 增量 +2 = 41 篇 → 清掉 3 篇偏题 = **38 篇入库**。GraphRAG(首轮被切)rel=95 回来,6 奠基作全部入库。orchestrator 展现真判断:按 facet 分配、自己发现 longctx 饿死补播、改 discover 误标的 facet、写 turning_seeds。
>
> **Bug 1(已修)——orchestrator 挂后台等唤醒**:首跑时 orchestrator 把 score_auto 挂后台 + "pause 等唤醒",但无头 `claude -p` 没有唤醒机制→进程提前结束,commit 没跑、库 0 篇。**修**:`drive.py` prompt 加【⚠️ 无头运行】块——每步前台同步跑、绝不挂后台、一口气 discover→score→commit 走完再回报。重跑即通。
>
> **Bug 2(已修)——commit 不豁免 seed**:`--keep N` 纯按 rel 取 top-N,不认 `seeded`。用户标"重点"的 MAST 只打 rel=24 垫底,要进只能 keep=16,顺带拖 3 篇偏题(Ego-R1/Generative Agents/Securing the Agent)。**违背 seed=必进 的初衷。修**:`commit.py` 两处加 seed 强制入库——①资格闸:seeded 绕过 rel≥30/flag/panel(block 仍挡);②选篇后:所有 seeded(非block/不在库/未选中)强制并入,不受 keep/top-N 截断。实测 `--keep fa=1` + seeded rel20 → 强制带上共 2 篇。**以后 orchestrator 可 keep=4 只留真好的,MAST 照进不拖垃圾。**
>
> **运行中发现的改进(保留)**:`seed.py` 被加了 `--facet`(种子按 topic.json per-facet seed_ids 落到正确 facet,否则标 `_all` 会在打分时漏掉);orchestrator 手动修了 candidates.json 里被 discover 误标的 facet。
> **遗留(下轮)**:cross-paper-structure 偏生物医学;citation 边稀疏(仅 1 条);turning_seeds 已写入 topic_state.json。
> **TODO-6 完成。** 改动(commit/drive/seed + 38 篇入库 + 3 篇删除)在工作区,未 push。

## 2026-06-20 18:48 EDT · 合并:删掉 score 的新旧并行,全主题归一走 facet 路

> 用户:"都变成新的"(不喜欢新旧并行)。**score_auto 不再分 faceted/非faceted 两支——永远走 facet 循环**(load_topic 把无 facets 的老主题归一成 1 个隐式 `_all` facet)。
> - `score_auto.main()`:删掉非 faceted 单尺分支 + `if _faceted...return` 包壳;现在永远 `for fac in facets`(facets 来自 load_topic,≥1)。日志 tag = `faceted xN` 或 `single(_all)`。删掉 `target`/`anchors` 的旧读取。
> - `boundary_rerank`:删掉 `target` 参数 + "首跑用第 target 名截断线"那套;**去留线只剩资格闸 `{30, flag_min}`**(centers=None 默认即它)。
> - 删掉 `autopick_anchors`(写 topic.json + TG 的旧单尺自举)——归一后没人调;faceted 路用 `_pick_anchors` 做 **in-memory 自举**(不碰 topic.json 意图档)。
> - **老主题行为变化(已跟用户讲、获准)**:rl-general-toolbox / rl-digital-human-interaction 现在走 `_all` facet——分数文件命名变 `_all_batch_*.json`(commit 按 `*.json` glob 读,无影响)、边界复称去留线从"第 target 名"变"资格闸 30/45"、冷启动自举不再回写 topic.json(改 in-memory)。已入库的不动,只影响以后增量怎么算边界。
> - commit 未动:本来就总按 facet 分组(老主题=1 组 `_all`),auto 选篇是"没给 --keep 的兜底"非重复逻辑。
> - **实测**:faceted(2 facet)走 `faceted x2`;老主题归一走 `single(_all)`、文件 `_all_batch_0.json`、boundary centers={30,45};commit auto 读新命名文件 OK、--plan/--keep 按 facet 正确;全量 compile、无 autopick/target 残留。
> - **rl-general-toolbox 拆 facet**:用户说暂不拆,后续自己用对话处理(本次只让它作为 `_all` 走新路,不动它的 topic.json)。

## 2026-06-20 18:20 EDT · 修正:orchestrator `find` 转为 AUTO 默认(不再 opt-in)

> 用户纠正:"现在还在搭建阶段,更喜欢直接用新的"。**把 `run.py` 的 `AUTO` 与 `AUTO_PULL` 里的 `discover, score, commit` 三段换成 `find`(orchestrator)。** 即 `python3 pipeline/run.py <id> auto` 现在 find 部分走 orchestrator,不再是焊死三段。
> - discover/score/commit 仍保留为独立 stage(调试 + orchestrator 当工具调)。
> - **撤销 18:08 的「护栏1:find 是 opt-in、AUTO 不动」**——现在 AUTO 默认走 orchestrator,包括老主题 rl-general-toolbox / rl-digital-human-interaction(非 faceted 会被当 1 隐式 facet 由 orchestrator 跑)。搭建阶段优先用新路、不维护新旧双轨。
> - 唯一在跑的进程是 `tools/verify_daemon.py`(全天候核查,与 find 无关)——**未动**,等用户确认是否要停。
> - run.py compile OK。

## 2026-06-20 18:08 EDT · TODO-4/5 drive.py orchestrator + TODO-6 验证场就绪(整套落码完)

> 接 18:02。**TODO-4+5(drive.py + prompt)落码完,TODO-6 验证场 topic.json 备好。整套 facet 改写代码全落地。**
>
> **TODO-4/5 — `pipeline/find/drive.py`(新 launcher)+ orchestrator prompt**
> - 拉起一个 agentic `claude -p`(model=opus, timeout=1800, allowedTools=Bash/Read/Write/Edit/Glob/Grep/Task/WebSearch/WebFetch),`os.chdir(ROOT)` 让它的 Bash 从仓库根跑。python 只"拉起+收尾"。
> - prompt(设计 §5 落地,含 ⭐ 顺引用补漏那句):情况(库现状+facets 概览,注入)+ 工具(discover/seed/score/commit --plan/--keep/Read/Write/Task/notify_cli,**真实命令行**)+ 项目契约 + 通知规则。**不教怎么找**。
> - `build_situation`:读 topic+state+DB 计数 → 冷启动/增量 + 每 facet queries/seed_ids/anchors/库内/覆盖 概览。`--dry-run` 只打 prompt 不烧 claude。
> - 新增 `pipeline/tools/notify_cli.py`(给 orchestrator 用 Bash 发 TG)。
> - `run.py` steps() 加 **`find` 阶段** = `find/drive.py`。**不动 AUTO**(discover/score/commit 仍在 AUTO,gt/dhi 老链路零影响);orchestrator 是 opt-in,跑法 `python3 pipeline/run.py <id> find`。
> - 实测:drive --dry-run 在 gt(非faceted,显示"已入库100/增量/facets(1)无facets")和 agentic(faceted,显示冷启动/5 facets 概览)都渲染正确;全量 compile OK。
>
> **TODO-6 — 验证场 `topics/agentic-knowledge-synthesis/topic.json` 改成 faceted**
> - 5 facets(cross-doc-synthesis / cross-paper-structure / agentic-retrieval / longctx-vs-retrieval / corpus-qa),15 条 query 分配到各 facet,每 facet 写了 hit_criteria。
> - **6 个奠基作 seed_ids(arxiv id 全 fetch 核对过标题)**:RAPTOR 2401.18059 / CoA 2406.02818 / OpenScholar 2411.14199 / **GraphRAG 2404.16130(首轮被切的)** / MAST 2503.13657 / PaperQA2 2409.13740。
> - load_topic 验过:faceted=True、all_queries=15、all_seed_ids=6。
> - **未做(交用户,billed)**:实际跑 orchestrator(写生产库、重网络、可能卡 Cloudflare)。命令:`python3 pipeline/run.py agentic-knowledge-synthesis find`(或分步 discover→seed→score→commit 调试)。
>
> **TODO-7(gt 拆 6 facet)**:按用户决定留给用户后续自己改(老主题 opt-in),本次不动。
>
> **整体现状**:find 段 facet 改写 1→5 全部落码+自测;6 验证场就绪待用户 billed 跑;7 用户自理。新增文件:lib/pool.py、lib/topic.py、find/seed.py、find/drive.py、tools/notify_cli.py。改:lib/sources.py、find/{discover,score_auto,commit}.py、run.py。

## 2026-06-20 18:02 EDT · TODO-3 score/commit per-facet 落码 + 实测通过

> 接 17:50。**方案 A 定**（用户拍板）：单 `candidates.json` + 每条候选带 `facet` 标签（被哪个 facet 检索词命中），不拆多文件（子 agent 回总结、orchestrator 单写池，无并行写冲突）。
>
> **改了什么**
> - `lib/pool.py`：`candidate_entry/record_to_candidate` 加 `facet="_all"` 参数 → 候选多一个 `facet` 字段。
> - `find/discover.py`：接 `lib/topic`；建 query→facet 映射，按 `matched_queries` 给每条候选打 facet 标签；加 `--facet <key>`（只搜该 facet + 已有池**合并**而非覆盖，给 orchestrator 定向补搜）。无 facets → 全 `_all`，行为不变。
> - `find/score_auto.py`：**非 faceted 走原逻辑(完全不变)、faceted 新分支**。prompt 加 `hit_criteria` 注入；`do_pass` 抽成模块级 `run_pass`（带 file_prefix/clear，per-facet 独立批文件 `{key}_batch_*.json`）；`boundary_rerank` 加 `centers/file_glob/out_name/hit_criteria`（faceted 用资格闸 centers={30,flag_min}、独立 zz 文件）；`autopick` 抽出 `_pick_anchors/_scores_from`，faceted 每 facet 缺 anchors 就**in-memory 自举**（不改 topic.json 意图档）。
> - `find/commit.py`：加 `--plan`（按 facet 摆分布:eligible/fresh/分档桶/papers,**不写库**,给 orchestrator 读）+ `--keep all|f=N,...`（按 facet 留 top-N 写库）；无 flag = auto（老行为）。selected.json 加 `facet`,日志加 per-facet added。
>
> **实测（in-process 假 run_claude + 临时 DB,不烧真 claude/网络）**：
> - faceted score_auto：facetA 无锚点→自举 `[95,45,10]`→带锚重打;facetB 用给定锚点;批文件 `facetA_batch_0/facetB_batch_0` 命名空间隔离不撞。
> - commit `--plan`：per-facet 分布桶正确、不写库;`--keep facetA=2,facetB=1`→精确选 2A+1B,DB 3 行,selected.json 带 facet。
> - **back-compat**：非 faceted+预置锚点→单路、`batch_0.json`(无前缀)、first-run boundary→**与老行为一致**;commit 无 flag=auto。
>
> **现状**：find 段「主链工具」全部 facet 化完毕(discover/seed/score/commit + topic/pool 存档层)。**下一步 TODO-4**：`drive.py` 拉起 orchestrator 把这些工具串起来。注:边界复称 faceted 用资格闸 centers(judgment 时代去留线不再是全局 target),与设计"选篇=orchestrator 判断"一致。

## 2026-06-20 17:50 EDT · TODO-2 存档层 `lib/topic.py` 落码 + 实测通过

> 接 17:40。**新建 `pipeline/lib/topic.py`** = 意图(topic.json)+状态(topic_state.json)存档层。
> - `load_topic(ref)`：把 topic.json **归一成"永远带 facets"**形式——无 facets 自动合成 1 个隐式 facet `_all`（hit_criteria←preferences、queries←顶层 queries、anchors←score_anchors、seed_ids←顶层 seed_ids）。**完全向后兼容**：现有 gt/dhi 不动照跑。
> - 辅助：`is_faceted / facet_by_key / all_queries(union 去重) / all_seed_ids(union)`。
> - topic_state：`load_state / save_state / update_facet_state(in_db/coverage/last_run) / add_turning_seed`。空则返 `{facets:{}, turning_seeds:[]}`。
> - **实测**：gt 退化成 1 隐式 facet（14q/3anchor，all_queries==原 queries）；合成 2-facet topic 解析对（hit_criteria 缺失回退 preferences、union 对）；state 往返对。
> - **未做**：score/commit 尚未接 topic 层（TODO-3）；discover 仍读 `topic["queries"]`（faceted 接线在 TODO-3 一并做）。

## 2026-06-20 17:40 EDT · TODO-1「按 id 播种」落码 + 实测通过（开始落代码）

> 接 17:14。开始把整套 facet 改写落代码（用户："直接开始全部完成，慢慢来"）。本条 = TODO-1 完成。
>
> **改了什么**
> - `lib/sources.py`：抽出 `_openalex_norm/_ss_norm/_arxiv_norm` 三个 per-record 规范化器（query 与 by-id 共用，零行为变化）；新增 `openalex_by_id / semantic_scholar_by_id / arxiv_by_id` + 统一 `parse_ident(raw)` + `fetch_by_id(raw)`。
> - **端点定论（实测）**：DOI→OpenAlex `/works/doi:<doi>`（最富，带 refs）；arxiv→arxiv 官方 API `?id_list=`（稳、无需 key；OpenAlex 对纯 arxiv 常 count 0）；SS 无 key 必 429，只当末路兜底（容错返 None）。
> - `lib/pool.py`（**新，存储层地基，TODO-2 复用**）：`candidate_entry()`（从 discover 抽出）、`record_to_candidate()`（单记录→merge→quality→候选条目）、`candidate_keys()`（去重键=id+doi+arxiv）、`load/save_candidates()`。
> - `find/discover.py`：改用 `poolmod.candidate_entry`（局部 `pool` 改名 `cands` 避免遮蔽模块）。**输出唯一变化=每条候选多一个 `"seeded": false` 字段**（附加，向后兼容，下游不读不受影响）。
> - `find/seed.py`（**新 CLI**）：`seed.py <topicId> <id...>` → 逐个 fetch→规范→去重→写 candidates.json，标 `seeded:true`，绕过 prefilter；池里已有则把那篇升 `seeded:true`（防截断）；池不存在则从 topic.json 建骨架；stdout 打 JSON 摘要给 orchestrator 读。block 质量会 WARN（commit 仍不入库，守"block 永不入库"契约）。
>
> **实测**：parse_ident 13 例全对（含 url/老式 arxiv/垃圾）；fetch_by_id 三篇真论文 OK（GraphRAG arxiv 带摘要、Deep learning DOI 带 53 引用、Attention url）；seed.py 端到端：3 播入+1 垃圾 DOI 正确失败、重播触发 already+升 seeded、池计数正确。临时 `_seedtest` 已清。
>
> **未做/下一步**：TODO-2 存档读写（facets/preferences/web_sources 解析 + topic_state.json + 向后兼容）。注：seed 暂未读 topic.json 的 `seed_ids`（那是 orchestrator/TODO-2 串起来的事；seed.py 当前是"给 id 就播"的纯工具）。

## 2026-06-20 17:14 EDT · 4 个待拍小决定全定 + 讲解中澄清两点（纯设计，未落码）

> 接 16:44。本轮用户过完整套设计，**§7 那 4 个待拍项全定**（回填进设计文档 §7，标 ✅）：
> - launcher → **新开 `pipeline/find/drive.py`**（不塞 run.py 阶段分发；run.py 的 find 阶段调它）。
> - prompt（§5）→ 措辞基本认，**【怎么干】加 ⭐"顺引用补漏"那句**（收完翻引用、把高频被引却没收的奠基作按 id 播种捞回）——不点这句播种能力会闲置。细措辞用户后续可再磨。
> - 防卡死安全网 → **默认不加**（死规则与初心相悖；harness 高位兜底 + 库规模框成本 + TG 可叫停；真空转再补最小护栏，通常封拐弯轮数）。
> - gt/dhi → **先留 facet=1，opt-in 再补 facets**（无 facets 自动退化、老篇不重评；升级拿 gt 拆 6-facet 当样板）。
>
> **讲解中澄清两点（写进 §7 补充）**：① **score_auto.py 打分工具保留**（升级 per-facet），砍的是"机器全局 Top-N 硬选"那个死规则→降级成"分数喂 orchestrator 判断留几篇"；"无人冷启动自举+TG审批"流程不要了，改"讨论当场定"，但"库空怎么起步"状态仍由 Claude 处理（hit_criteria 兜尺子）。② **多开子 agent 设计上不限**（fan-out 甜区），唯一天花板=harness 高位兜底，即"防卡死安全网"管的事（默认不加）。
>
> 现状：**设计 + 4 决定全齐，可落代码**。下一步从 §6 TODO-1「按 id 播种」起。

## 2026-06-20 16:44 EDT · 地基②「编排模型」定稿 + 设计成品落档（纯设计，未落码）

> 接 16:30。本轮把地基②（叫醒后的编排逻辑）也敲定，**facet 改写整套设计齐了**。完整成品（存档 schema 说明 + orchestrator prompt 初稿 + 实现 TODO）写进独立文档 **`claude-memory/Prompt-structure-design/find-facet-rewrite-design.md`**——新会话接手直接照那份实现。本条只记要点 + 对 16:30 的修正。

**编排模型（唯一）：拉起一个 claude 全权驱动。**
- cron 和对话**共用同一套**：launcher 拉起 claude -p（cwd=仓库根，allowedTools Bash/Read/Write/Task），给它工具 + 当前情况(两存档+DB现状) + prompt（情况/工具/项目契约/通知规则）。python 只"拉起+收尾"，中间不插手；discover/score/commit 就是它 Bash 调的 CLI。差别只剩"谁触发"(定时/对话) 和"通知与否"。
- **每次拉起本身就是一次完整 find 过程**（用户原话），所以全程 claude 驱动，不存在"python 攥流程、claude 只在点上搭手"。

**⚠️ 修正 16:30 写的几条编排细节（经用户纠正,作废）：**
- ~~单 orchestrator 不 fan-out~~ → **fan-out 在 find 是甜区,鼓励**（facet 是独立搜索线,一 facet 一子 agent 各搜各回小总结;Anthropic 多agent+90.2% 擅长广度优先独立探索）。我把 retrieve 的"合并是雷区"误搬到 find 了——那条只适用"读已有论文答问题",find 是"去搜去发现"。唯一仍单线程=最后跨 facet 合并+定稿(orchestrator 自己收齐小总结再拍,本就不会 spawn 合并 agent,不必写进 prompt)。
- ~~拐弯有界 2 轮~~ → **撤；拐几轮是它"判够不够"的判断,不设界**。
- ~~A/B 双驱动(python攥流程+claude检查点)~~ → **作废,永远是"拉起 claude 全权驱动"**。
- ~~5 段路书~~ → **撤；"怎么找"是它自己的逻辑,prompt 不教,只给它推不出来的(情况/工具/项目契约/通知)**。

**还得真造的前置零件**：「按 id 播种」——`lib/sources` 缺"按 DOI/arxiv id 单查元数据"。seed_ids/add_url/将来 add_paper 共此地基(一鱼三吃)。

**实现 TODO（详见设计文档 §6）**：①按id播种工具(前置) → ②存档读写(facets/state,向后兼容) → ③score/commit 支持 per-facet → ④launcher(run.py find 接管 vs 新 drive.py,待拍) → ⑤prompt 落地(用户最终过目) → ⑥验证场=agentic-knowledge-synthesis 重搜捞回奠基作 → ⑦(可选)gt 拆 6 facet 当样板。
**仍待拍**：launcher 放哪 / prompt 最终措辞 / 要不要防卡死安全网(默认不加) / gt-dhi 留旧还是 opt-in facets。

## 2026-06-20 16:30 EDT · facet 改写「存档格式」定稿 + 治理/通知模型敲定（纯设计，未落码）

> 接 02:16 顶条挂的「🔶 找段大方向改写」。本轮把卡住一切的地基①「升级版 topic.json 存档」从悬而未决推到**可落代码的定稿**，并敲定配套的治理/通知模型。地基②「叫醒后的编排逻辑」仍未做（见末）。

**治理/通知模型（用户拍板，纠正了我一个走偏）：**
- 工作流 = **「你出问题 → 我们讨论定方向 → 交给我自主跑」**。facets/命中标准/锚点/种子**都在讨论里当场定**（像本轮），不是 claude 背着用户自举完再回头推 TG 审批。我一度套用旧 `autopick_anchors`「cron 自举→推 TG→过目」那套——那是为**无人在场冷启动**设计的，套到"一起定 topic"场景上多余。**facet 不走自举+通知,讨论里定、我直接写进 topic.json。**
- **通知三档**（用户定）:①例行判断(每 facet 留几篇/边界取舍/增量 commit)→**只留痕**(log/state/commit 报告)不打断;②**新发现**(讨论时没料到的新维度/值得开新 facet/拐弯种子指向意外方向)→**TG 通知**(默认继续跑不停等审批,但给用户随时叫停/改向的机会;大到改范围则通知里说清由用户定);③commit 回报 + tierb 验证点击→照旧。**「通知」专指 FYI 留痕,不是审批闸。**

**配额改判断(用户拍板)**:删掉 `min_keep` 数字。配额不再 python 按固定 M 切,而是 commit「claude 定稿」那步——pipeline 把候选+打分**按 facet 分好组**摆出来,claude 看分布自己决定每组留几篇(小簇别饿死/富矿别滥收=判断非公式)。存档不存配额数字,顶多 facet 留句软话(如 note:"safety 是重点别饿死")。

**存档格式定稿(拆两文件,用户同意):**
- **`topic.json`(意图——讨论里定,pipeline 基本不回写)**:`id/title/idea/window_years/target` + `preferences`(全局取舍偏好) + `facets[]` + `web_sources[]`。
  - `facets[]` 每项:`key`,`title`,`hit_criteria`(⭐一句话命中标准=per-facet 语言尺子,补 anchors 这3个点之间的"规则";冷启动 anchors 没凑齐时先顶上当尺子;discover 判够不够/commit 归类/博客软判命中 facet 都复用它),`queries[]`(per-facet 检索词),`anchors[]?`(per-facet 锚点,从全局挪进 facet——治"一把尺子量五件事"),`seed_ids[]?`(按 DOI/arxiv id 点名必进的奠基作),`note?`(软偏好)。
  - `web_sources[]`:`{url, facet, note}` 手工策展的博客/X(对接 add_url,见 16:16 条)。
- **`topic_state.json`(状态——pipeline 每轮自动写,用户一般不碰但可当手动开关)**:`facets:{<key>:{in_db,coverage,last_run}}` + `turning_seeds[]:{hint|id, from, kind}`(拐弯种子=上轮发现的好线索/下轮起点)。想逼某 facet 重搜=清它的 coverage。
- **优雅退化**:无 `facets` 时 = 现状(facet=1 全局单尺子)。**gt/dhi 不改也照常跑。**

**已有 topic(gt/dhi)怎么办**:①不动=留 facet=1 老模式照跑;②opt-in 补 facets=只惠及**将来增量**(新篇按 facet 分组打分/定稿),**已入库 100/129 篇不自动重评**(去留已定,增量只碰新篇),想重评得显式清 scores 重跑 score。gt 的 idea 本就含 6 facet(reward-design/training-tricks/exploration/algo-zoo/safety-cbf/task-instances),升级近乎把 idea 拆成结构。

**改 topic 的工作流**:编辑 `topic.json`(意图)→重跑受影响阶段,pipeline 增量跟上(同现在改 anchors 重跑 score)。加 facet/词→discover→score→commit(只追新);改命中标准/锚点→score→commit(影响之后的篇,老篇要重评需显式重打分);加 web_sources→add_url→sum。将来地基②做好后改为对话式(跟 claude 说"加个关于X的facet"它自己改存档),但**现在先落"手编意图文件+重跑"这条确定路**。

**仍未做=地基② 叫醒后的编排逻辑**:claude 拿这份存档具体怎么一步步调 discover/score/commit(含拆facet定词/判够不够/按id播种/拐弯再搜/对话式改存档)。存档定了才轮到它。**本轮未碰任何代码。**

## 2026-06-20 16:16 EDT · 博客/网络源扩展（add_url）架构敲定 + 推翻旧 text_path 支点（纯设计，未落码）

> 本轮把 2026-06-19「副轨：add_url」那版计划重新过了一遍，发现旧计划有个**死支点**，并把架构敲定到可落代码的程度。接口统一那步用户说**后面再看**，本轮没碰。

**⚠️ 重大纠正：旧计划的 text_path 支点作废。**
- 旧计划写「papers 表本就有 text_path、新版 summarize 喂文件路径让 claude Read → 博客直接走现有链」——**基于过时认知，不成立**。
- 实测：`lib/db.py:38` 明标 `text_path … DEPRECATED(2026-06-16):此列恒为 NULL;留列免动 prod 库`；全库 0 条非空；summarize（`summarize_auto.py`/`build_worklist.py`）**只读 `pdf_path`，从不碰 text_path**。它是当年英文全文索引(`fts_text`，已随 2026-06-16 移除)的遗留死字段。**别再照旧计划救它。**

**敲定的最终架构（end-to-end）：**
1. **抓取分级**（治旧计划只会 requests/纯 HTTP GET、抓不到 X 的洞）：
   - 静态博客(Lilian Weng/Anthropic…) → **轻抓**：让 claude 用 **WebFetch** 自己拉，不写独立爬虫（替掉旧计划的 trafilatura/BS4 抽取器——待拍决定#1 作废）。
   - X / 动态页 / 登录墙 → **opencli 真 Chrome**（`fetch_tierb.py` 已在用的那套 Chrome 桥：独立 user-data-dir + 登录态 + noVNC 手机过 Cloudflare/Duo）。**复用 tierb 设施，不新建**。图多的 X thread 直接**截图**喂 claude（治"纯文字对图表有损"）。⚠️ 前置：那个隔离 profile 现只登 NYU 图书馆，抓 X 要先在里面登一次 X 账号。
2. **落盘 = 路线B（用户拍板）**：博客 md/截图**占 `pdf_path` 位**，存 `storage/papers/<slug>/`（`source.md` / `screenshot.png`）。**不用 text_path**。理由：summarize 本就是"把文件路径塞 prompt 让 claude `Read`"，Read 一个 .md/图片 跟 Read PDF 没区别——机制天然通。
   - ⚠️ 旧计划写的落盘路径 `store/web/<slug>.md` 也过时（目录已 `store`→`storage` 且是**每篇一文件夹**，非扁平大目录）。
3. **质量：砍硬档 → 软约束（用户拍板）**：废掉旧计划的 `url_allowlist.txt` 白名单 + trusted/flag 硬挡（待拍决定#2/#3 作废）。可信度交给 **两道 claude 软判**：①查找阶段 agentic 搜索 claude 决定收不收时顺带判；②summarize 阶段 claude 总结时再判、写进总结。**无硬过滤门**。
4. **blog 身份标记（三重，全不改库表，合"避免 ALTER"惯例）**：①`id`=规范化 URL（剥 utm/fragment，结构上区别于 DOI/arxiv）；②`sources=["web"]`+域名（主标记+溯源）；③`quality_signals` 加轻量 `web` tag（**不参与过滤**，只为出口/verify 一眼可辨）。

**搁后面（用户明确 defer）：summarize 接口统一。** 现接口从 DB→worklist→prompt 全焊死"PDF"假设（`build_worklist.py:24` status='pdf_downloaded'、字段名 `pdf_path`、`build_prompt` 满篇"从PDF写/pages参数/直读PDF见公式图表"）。统一方案（已想好待落）：抽象成 source——worklist 加 `source_kind`（按扩展名 pdf/markdown/image）、`build_prompt` 按 kind 分支措辞（md/截图换说法 + 软可信度提示）、status 语义拓宽成"source 就绪"（保字符串免迁移）、worklist 层 `pdf_path`→`source_path` 别名。**本轮未动。**

**与按 id 播种共地基**：add_url 和「按 DOI/arXiv id 点名入池」(facet 改写里捞奠基作那条) 是同一块"按外部标识单点入库"地基——一鱼三吃（add_url / 按 id 播种 / 将来 add_paper）。

## 2026-06-20 02:16 EDT · 重构首条（当前状态快照）

> 文档模块化重构建立本日志。以下为当日现状；以后变化在本条**之上**叠新条。

### 现在能跑
- 三步（discover / score / commit）端到端可用，`run auto` 串起。两个老主题（rl-digital-human-interaction 129 篇、rl-general-toolbox 100 篇）就是这条链建的。
- **跨批次校准漂移修法已全部落码 + 三层验证通过**（2026-06-17）：锚点注入 + 证据接地 + batch 20+批内洗牌 + `boundary_rerank` 边界复称 + 冷启动自举（`autopick_anchors`）。实测 claude -p 烟测返回合法 JSON、reason 引原文、分数合理。
  - ⚠️ **这批改动当时记为"未提交/在工作区"**（备份 `/tmp/score_auto.py.bak`）。现 `pipeline/find/score_auto.py` 已是新版且在 git 跟踪下——是否已 commit 入库**待核实**（查 git log）。
- gt/dhi 的 `score_anchors` 已手挑填好（gt=SAC95/泛连续控制DRL45/金星探测8；dhi=物理角色交互96/行人避障DRL46/量子active-learning10），增量复用、不触发自举。
- Codex 魔鬼代言人（`quality.codex_panel`）实现完整但**默认关**（用户 2026-06-10 拍板，异议火力集中总结侧）。

### 已知 bug / 坑
- **`first_run_target` 两处默认不一致**：config.json=200 vs score_auto.py fallback=100。低危（实跑靠 topic.json.target），但该统一。
- **重复入库残留**：`Reinforcement Learning for Robust Parameterized Locomotion Control`（Bipedal Robots）以两个 id 重复入库（slug `..._Bipedal_Robots` 和 `..._2`，两主题各自发现、merge 没合上），待去重。另 `tools/similar.py` 抓出过 2103.14295 重复。

### 未决 / 设计在动（重要）
- **🔶 「找」段大方向暂定改写（2026-06-20，纯设计对齐、未动代码）**：用户发现"一个主题其实是好多组论文（facets）"，现行"一把尺子全局 Top-N"有三病——**小簇饿死**（冷门 facet 被论文多的 facet 挤掉名额）、**一把尺子量五件事**、**丢结构**。
  - 暂定钉死的核心原则：**Claude 智能负责"判断与编排"、现有管道负责"力气与确定性执行"；管道脚本从焊死一条龙变成"我手里的工具"，在每个决策点介入**。这是对 2026-06-09"把 Claude 移出 runtime"的**精修不是推翻**（仅限 find + fetch 两段；summarize/verify 那段继续无人黑箱）。
  - 逐阶段分工：discover=管道召回 / 我拆 facet 定词判够不够；score=管道打分 / 我定 per-facet 尺子 + 配额 + 看边界；commit=管道写库 / **我定稿，增量新篇直接 commit、事后 Telegram 回报**（用户"信我判断"，不每篇等点头）。
  - facet 配额倾向"保底 M 篇 + 剩余全局按分填"（治饿死又不过度限制富矿），facet=1 时优雅退化成现状。
  - **未落地、刻意推迟**：文件保存架构（topic.json 升级成"装得下判断的存档"：facets+命中标准+取舍偏好+score_anchors+覆盖状态+拐弯种子）用户说"后面整体改一遍再定"；"叫醒后的编排逻辑"同。当前 topic.json 仍是旧形态。
- **召回漏洞教训（2026-06-19，新主题 agentic-knowledge-synthesis 首轮废弃）**：`prefilter_rank` 纯词法取前 N，把领域奠基作（GraphRAG/RAPTOR/PaperQA2 等）切掉 → 召回不足 + 生物医学 bleed。该主题已删首轮全部产物（生产库未触碰，commit 没跑），topic.json 保留待"补 ~7 条精准检索词 +（可选）按 id 播种原语 → 重搜 → commit"。**这是上面"facet 改写"的现实触发器之一**。

### 上次卡在哪 / 下一步
- find 段代码本身稳定可跑；**真正在动的是设计层**：等用户定"存档（升级版 topic.json）长什么样" + "叫醒编排逻辑"，再落 facet 配额 / per-facet 打分 / 按 id 播种 / 增量召回编排。
- 小活：① 核实 score 漂移修法是否已 git commit；② 统一 first_run_target 默认；③ Bipedal Robots 去重；④ agentic-knowledge-synthesis 补检索词重搜。

---

## 2026-06-19 · 新主题 agentic-knowledge-synthesis 设计 + 首轮搜索（已废弃重来）

> 缘由：讨论"知识库该怎么被 agent 消费、能否发现跨论文关联"时，意识到这本身是个值得做的研究主题，决定用本项目自己的流水线攒这方面语料（dogfooding：用论文库研究"论文库该怎么用"）。本会话**只到搜索一轮、未入生产库**；首轮因召回不佳被叫停并删除，主题定义保留待重搜。

**主题怎么来的（讨论脉络）**：从"问答层五方案"（`claude-memory/Prompt-structure-design/qa-layer-design.md` §10）聊到——⑤合成层/金字塔在**质量**上并不更准（GraphRAG C0≈TS 平手、赢成本）；而**"跨论文综合/关联发现"恰是领域里最没被解决的格子**（单篇 QA 已被 PaperQA2 打穿，但"把多篇想到一起产生新论断"没有架构稳定赢）。用户由此提出：这是真空里的研究点。

**主题定稿（边界）**：
- id=`agentic-knowledge-synthesis`；标题=Agent 消费知识库与跨论文综合（长上下文时代）。
- **三个内置前提**（区别于泛 RAG 研究）：①长上下文是给定条件（Opus 时代，"几十篇直读进去综合"可行，不预设激进检索；翻转了 lost-in-the-middle 等多在弱模型上测的旧证据）；②消费方=agent 为主、人为次（agent 要机器可读/可追溯，人要可解释可信）；③已有库内引用图资产（`citations` 表，跨论文关联不是从零）。
- **收（脊柱→外围）**：⭐跨论文综合+关联发现（综述生成、矛盾/共识、LBD 假设生成、**"如何构建跨论文关系结构"的方法学**——引用图之外更好的结构，用户特别点名要去论文里找答案）；agent 主动求知（检索/工具增强、何时检索、结果接回任务）；长上下文 vs 检索（强模型档，只收与综合相关的）；库上科学问答（agent+人 双消费、可追溯）。
- **不收**：通用 RAG 工程 / 向量库调优 / 切块·embedding 选型；纯单篇 QA；通用 agent 记忆 / 通用 KG 构建。
- **配置**：`window_years=3`（2023 起）、`target=35` 起步、`score_anchors` 不手填（冷启动自举）。
- **关键澄清**：跨论文**综合**不砍（它是脊柱），砍的只是"通用 RAG 工程"；且"该用什么跨论文关系结构（引用图偏薄：稀疏+引用≠思想关联；语义相似图/概念图/论断关系图更厚）"本身列为一个检索侧面，让语料用论文证据反哺我们怎么建，不拍脑袋。

**首轮搜索 + 为什么废弃（重要教训）**：
- 跑了 discover（raw 3003 → 去重 2135 → **池只取 70**；有摘要 49；偏新）+ score（冷启动自举）。脊柱覆盖到了：Literature Meets Data(95)、LBD(80)、Lost in the Middle(78)、RAG-or-Long-Context(75)、Unifying LLMs+KGs(65)、Agentic RAG Survey(58) 都落顶。
- **❌ 病① 召回漏洞（致命，叫停主因）**：discover 的 `prefilter_rank` **纯词法**按各源排位取 `papers[:70]`，不认领域奠基作 → 我们自己 evidence 文档钦定的 **GraphRAG / RAPTOR / PaperQA2 / OpenScholar / Chain-of-Agents / MAST 一篇都没进池**（它们在 2135 里但被 70 这刀切了）。这几篇恰是"跨论文综合结构"最核心的（RAPTOR/GraphRAG=合成层原始论文）。
- **❌ 病② 生物医学 bleed（中度）**：`literature-based discovery` / `knowledge graph from scientific papers` 本是生物医学术语，pubmed 灌回大量临床文献（FoodAtlas 82、PubMed KG 60、medical QA 一堆）——方法沾边、领域跑偏。
- **用户决定**：删掉这轮全部产物、先把讨论入库，补搜方案下次再拍。

**下次接着做（待办）**：
1. **补召回再重搜**（commit 前必做）：(a) 加 ~7 条精准检索词把奠基作捞进各自 query 前排（graph-based RAG / query-focused summarization → GraphRAG；recursive abstractive tree retrieval → RAPTOR；language agents superhuman synthesis → PaperQA2/OpenScholar；self-reflective RAG → Self-RAG；multi-agent LLM failure modes → MAST 等）；(b) **可选**建"按 DOI/arXiv id 点名播种入池"小原语（保证 evidence 文档那 8 篇钻石必进；且是 add_url/搁置 add_paper 的同一块地基，一鱼三吃）。`sources` 目前缺"按 id 单查元数据"，需补。
2. 重跑 discover→score→看分布→commit（commit 截断时连同打分理由收紧生物医学 bleed）。
3. 建 `add_url.py` + 策展博客清单（详见下"副轨"）。
4. **教训**：discover 的 70 池上限对"已知有奠基作"的主题召回不足——纯词法排位会切掉低词频高地位的经典。对这类主题应先播种已知必备，或加精准 query。

**副轨：非论文内容（博客/技术报告）—— `add_url` 工具（计划，未建）** ⚠️ 偏 fetch/ingest 段，记在此处仅因与本主题重搜捆绑：
- **发现**：agent/长上下文/agentic RAG 这摊，最前沿一大半不在 arXiv，在 Anthropic/OpenAI research blog、Lilian Weng、FutureHouse、distill 等。只搜 arXiv 会系统性漏半个领域。
- **决定**：暂时方案 A——工具我（Claude）建、博客我策展（锁 2024–2026）。
- **`tools/add_url.py` 实现计划（已与用户过，待拍 3 决定后建）**：①`lib.http` 拉 HTML → 抽正文为 markdown（抽取器待定：推荐 trafilatura 进 conda 超集，主链仍只 requests）→ 存 `store/web/<slug>.md`，路径写 `papers.text_path`；②**关键利好**：papers 表本就有 `text_path` 字段、新版 summarize 把文件路径喂 claude 让它直接 Read（不止认 PDF）→ 博客不用伪造 PDF、不用改表结构，直接走现有 sum→verify；③身份/去重：`id=规范化URL`（剥 utm/fragment），按 URL+标题归一判重，无 DOI 没关系（papers.id 是 TEXT 主键）；④质量档：新建 `config/quality/url_allowlist.txt`（域名白名单），命中→trusted、否则→flag「非同行评审网络来源」；⑤入库+关联：upsert papers(status=pdf_downloaded, text_path)、paper_topic 强制入选。
- **待拍 3 决定**：①抽取器(trafilatura vs BS4)；②质量档命名(复用 trusted+signal 标 web-authoritative vs 独立新档)；③手挑博客是否跳过相关性/质量闸强制入选。

**状态**：主题定义 `topics/agentic-knowledge-synthesis/topic.json` 保留（已清掉自举锚点，待重搜）；首轮 candidates.json/scores/两 .out 日志已删；**生产库未被触碰**（该主题 topics/paper_topic 均 0 行）。

---

## 2026-06-17 · 打分跨批次校准漂移：调研 → 落码 → 自举（实现会话）

> 接同日"分析出方案"会话（见下条）。本会话：deep-research 调研 → 落码核心修法 + 全自动自举，全程在工作区（**未提交**），未碰生产库。配套：`claude-memory/Prompt-structure-design/score-drift-research-findings.md`（调研+方案+落码状态，最全）。

**做了什么（时间线）**：
1. **外部调研**（deep-research，22 源 / 100 claim→25 核查→19 确认）。要点：漂移学名=**rubric execution drift**（RULERS 2601.08654）；缓解三件套=锁死固定 rubric（含 score anchors）+ 证据接地 + 截断线事后校准。**保留 0-100 pointwise 是对的**（"Likert or Not" 2505.19334：大有序刻度让 pointwise≈listwise；换 pairwise 在边界反放大 style 噪声 2504.14716）。边界复称用**批量自一致+取分数分布均值**（2505.12570 / 2503.03064）。**z-norm 禁令被佐证**；**打分步不该上 reranker**（reranker 属粗筛门/检索层，打分步被 ≤500 cap 锁死、scale-proof）。
2. **逐项落码到 `score_auto.py`**（原版备份 `/tmp/score_auto.py.bak`）：
   - ② rubric 通用骨架（替掉**写死在 digital-human 主题**的旧例子——潜在 bug）+ `topic.json.score_anchors` 注入每批固定头部 + 证据接地（reason 须引原文片段）。
   - ① batch 默认 10→20 + 批内按 `Random(start)` 洗牌（幂等）对冲位置偏置。
   - ④ `boundary_rerank`：去留线 ±8 分窄带 → 同一次调用 ×5 采样取均值 → 写 `scores/zz_boundary.json`，靠文件名排序让 commit 的 sorted-glob 合并自动覆盖（**commit.py 没动**）。开 DB 认首跑（去留线=第 target 名截断线）/增量（去留线=资格闸 rel≥30·flag_min，已入库篇跳过）。
3. **全自动自举**（用户拍板"没必要我介入"）：`score_auto.main()` 发现 topic.json 无 score_anchors 时——裸跑整遍 → `autopick_anchors` 从**整遍分布**挑高/边界/低 3 张写回 topic.json（非阻塞推 TG）→ 带锚重打。冻好后增量复用、不再自举。**关键设计**：标尺取自"整遍"而非"第一批"——候选池预排序，第一批全高相关、给不出低/边界样本。
4. **gt/dhi 锚点手填**（已有打分库，手挑比自动准；已推 TG 供审）：gt=SAC 95 / 泛连续控制 DRL 45 / 金星探测（"exploration"误撞）8；dhi=物理角色×场景交互 96 / 行人密集避障 DRL 46 / 量子 active-learning（"agents"误撞）10。
5. **删掉人工工具**（用户要求）：原建的 `pipeline/tools/pick_anchors.py` 已删——自举全自动，想改锚点直接编辑 topic.json 重跑 score 即可。引用都清理干净。

**本会话定的决定**：范围=**(a) 只保截断线去留正确**（内部 rank stakes 低 + 下游评分/核查兜底）；锚点=3 张真论文（高~95/边界~45/低~10，偏经典不易过时）；④ band=±8 / k=5（默认可调）；冷启动=**全自动自举两遍**（裸跑→挑→重打），人工降为"直接改 topic.json"。

**改动文件（均未提交，工作区）**：`pipeline/stages/score_auto.py`（漂移修法 ②①④ + 自举 + autopick_anchors）；`topics/{rl-general-toolbox,rl-digital-human-interaction}/topic.json`（加 score_anchors）；`claude-memory/Prompt-structure-design/score-drift-research-findings.md`（新建）；`CLAUDE.md`（topic.json 字段 + 漂移修法节 + 工具表）；`pipeline/tools/pick_anchors.py`（建后又删，净增 0）。

**验证到哪**：编译 ✓；隔离逻辑 ✓（prompt 注入 / anchor_block / 洗牌确定性 / boundary cutoff·band·取均值·zz 覆盖 / 首跑·增量两路）；真实 claude -p 单批烟测 ✓（合法 JSON、reason 真引原文、分 15/56/92）；自举两遍流程 stub 测 ✓。**还没做**：临时库（`RESEARCH_DB=/tmp`）完整端到端（discover→score 带自举→commit，确认 zz_boundary 真被合并覆盖、自举真写 topic.json）。

**下一步（待用户定）**：a) 跑临时库端到端验证；b) 提交这批改动；c) 暂停。增量跑 ④ 的 band/采样次数若实跑后想调，在 `boundary_rerank` 默认参数处改。

---

## 2026-06-17 · 打分「跨批次校准漂移」问题定位 + 修法方案（分析会话）

> 目标：定位并准备修复 `score_auto` 逐批独立打分带来的**跨批次校准漂移**。本会话只做**分析+出方案+落 log**，**未碰任何 pipeline 代码、未动生产库**。（同日另有实现会话，见上条。）

**怎么聊到这里（上下文链）**：
1. 先确认架构判断：**改库层包含知识库全部内容，但不含"检索这种访问模式"**——改库层的读全是 lookup（按主键/状态/外键取已知行），`ask.py` 是 retrieval（自然语言问题找未知 ID 的最相关篇）。分界是 **lookup vs retrieval**，不是"写 vs 读"。
2. 讨论"打分要不要像 summary 那样加 verify→correct 闭环"。**结论：不要照搬**——summary 值得是因为它(a)是终端产品(b)有 PDF 当 ground truth 可收敛(c)错误静默+终端；打分三条全不占（是闸门、相关性无客观正解、错误多可见可恢复）。现有 Codex 魔鬼代言人默认关，是对的。
3. 纯从**错误形态**看打分：**几乎所有出错收敛成"论文拿 relevance=0/偏低 → 被静默丢"，系统结构性偏向假阴性**；唯一"放垃圾进来"的是模型真把跑题论文打高分（可见、会被下游 verify/topic.md 撞到）。**唯独"跨批次校准漂移"是召回冗余兜不住的**——多 query 能补回被漏的论文，补不回被打歪的分 → 用户拍板：这个要解决。

**`discover → score → commit` 流程速记**：
- **discover.py**：4 源（OpenAlex/SemanticScholar/arXiv/PubMed）×多 query 捞 → `merge_all` 去重（规范化 DOI 主键，记 relRankBySource/sources）→ 硬信号质量闸（block 当场丢，suspect 带标记入池）→ `prefilter_rank`（**召回导向：各源最好名次+多源加成，故意不用引用量**）→ 截 `pool_size=min(500,max(target*2,60))` → 写 candidates.json。**不写库。**
- **score_auto.py**：候选池切批（默认 10），**并发 4** 个 `claude -p`；每批 prompt=idea+该批 title/venue/abstract，按 0-100 打 relevance + edge_insight 布尔；强制纯 JSON → `scores/batch_<start>.json`。幂等（开跑清空 scores/）；可选 Codex 魔鬼代言人（默认关）。
- **commit.py**：合分 → 选篇闸（block 双保险丢 / rel<30 且非 edge 丢 / flag·suspect 需 rel≥flag_min(45) / Codex 异议合议:边界分<60+异议=挡）→ 选篇（首跑 eligible[:target]；增量只追新、cap=target*3）→ 写 papers+paper_topic → **全主题按 relevance DESC, citation DESC 重算 rank** → 建主题内引用边 → 落 selected.json。

**问题：跨批次校准漂移**：
- **病因**：每批是独立 `claude -p`，批间无共享参照系。现状已被 prompt 里带绝对锚点的 rubric 压成"几分校准噪声"，但几分噪声落在**截断线附近**就翻转去留、打乱 rank。
- **为什么必须单独治**：召回冗余能补"被漏的论文"，**补不回"分被打歪的论文"**——漂移动的是相对次序+截断线，冗余对它无效。
- **⚠️ 陷阱（务必避开）**：**绝不能做"逐批 z-score 归一化"**。池子被 `prefilter_rank` 预排序过，靠前的批本就更相关；逐批统计归一化假设各批分布相同，会把"批0确实比批20相关"的真信号抹平，越治越糟。**任何按批做统计标准化的方案在这条流水线上都是错的。**

**修法方案（核心洞察：校准只需在"会改变决策"处紧——95 分和 10 分不需要跨批校准，只有截断线附近窄带需要）**，三步按性价比叠加：① **加大批量**（10→25~30，批内自归一化，接缝数降~3×，context 吃得下）；② **共享锚点**（每批塞同一组已定分参照论文如 3 篇铁定 95/50/15，把所有接缝钉到同一把标尺）；③ **边界重排一遍**（首跑后取 target 截断线 ±N 分窄带，在一次调用里一起重打，绕开 z-norm 陷阱）。建议 ①+② 先上（便宜预防）、③ 作真正校正层。

**待拍决定**：①范围（只保截断线去留正确 vs 连选中集内部 rank 次序也稳）；②batch_size 调多少；③锚点真论文 vs 描述型、怎么挑存哪；④③ 的 ±N 带宽、是否也用于增量跑。（次日实现会话已逐一定，见上条。）
