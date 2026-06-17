# SESSION 2026-06-17 — 打分跨批次校准漂移：调研 → 落码 → 自举（实现会话）

> 接 `SESSION-2026-06-17-score-drift.md`（前一会话只做分析出方案）。本会话：先 deep-research 调研、
> 再落码核心修法 + 全自动自举，全程在工作区（**未提交**），没碰生产库数据。
> 配套：`docs/score-drift-research-findings.md`（调研结论+方案+落码状态，最全）；记忆 `score-drift-external-research.md`。

## 一、做了什么（按时间线）

1. **外部调研**（deep-research workflow，22 源/100 claim→25 核查→19 确认）。结论落 `docs/score-drift-research-findings.md`。要点：
   - 漂移学名 = **rubric execution drift**（RULERS 2601.08654）；缓解三件套 = 锁死固定 rubric(含 score anchors) + 证据接地 + 截断线事后校准。
   - **保留 0-100 pointwise 是对的**（"Likert or Not" 2505.19334：大有序刻度让 pointwise≈listwise；换 pairwise 在边界反放大 style 噪声 2504.14716）。
   - 边界复称用**批量自一致 + 取分数分布均值**（2505.12570 / 2503.03064）。
   - **z-norm 禁令被佐证**；**打分步不该上 reranker**（reranker 属粗筛门/检索层，打分步被 ≤500 cap 锁死、scale-proof）。

2. **逐项落码到 `score_auto.py`**（原版备份 `/tmp/score_auto.py.bak`）：
   - ② rubric 通用骨架（替掉**写死在 digital-human 主题**的旧例子——潜在 bug）+ `topic.json.score_anchors` 注入每批固定头部 + 证据接地（reason 须引原文片段）。
   - ① batch 默认 10→20 + 批内按 `Random(start)` 洗牌（幂等）对冲位置偏置。
   - ④ `boundary_rerank`：去留线 ±8 分窄带 → 同一次调用 ×5 采样取均值 → 写 `scores/zz_boundary.json`，靠文件名排序让 commit 的 sorted-glob 合并自动覆盖（**commit.py 没动**）。开 DB 认首跑（去留线=第 target 名截断线）/增量（去留线=资格闸 rel≥30·flag_min，已入库篇跳过）。

3. **全自动自举**（用户拍板"没必要我介入"）：`score_auto.main()` 发现 topic.json 无 score_anchors 时——裸跑整遍 → `autopick_anchors` 从**整遍分布**挑高/边界/低 3 张写回 topic.json（非阻塞推 TG 告知）→ 带锚重打。冻好后增量复用、不再自举。
   - **关键设计**：标尺取自"整遍"而非"第一批"——候选池预排序，第一批全高相关、给不出低/边界样本。

4. **gt/dhi 锚点手填**（已有打分库，手挑比自动准；已推 TG 供审）：
   - gt: SAC 95 / 泛连续控制 DRL 45 / 金星探测（"exploration"误撞）8
   - dhi: 物理角色×场景交互 96 / 行人密集避障 DRL 46 / 量子 active-learning（"agents"误撞）10

5. **删掉人工工具**（用户要求）：原建的 `pipeline/tools/pick_anchors.py` 已删——自举全自动，想改锚点直接编辑 topic.json 重跑 score 即可。引用都清理干净（CLAUDE.md/docs/记忆）。

## 二、本会话定的决定
- **范围 = (a) 只保截断线去留正确**（内部 rank stakes 低 + 下游评分/核查系统兜底）。
- 锚点 = 3 张真论文（高~95/边界~45/低~10），偏经典不易过时。
- ③ band=±8 / k=5（默认，可调）。
- 冷启动 = **全自动自举两遍**（裸跑→挑→重打），人工降为"直接改 topic.json"。
- 人工关卡推 Telegram 偏好 → 记忆 `human-gate-telegram`。

## 三、改动文件（均未提交，工作区）
| 文件 | |
|---|---|
| `pipeline/stages/score_auto.py` | 改：漂移修法 ②①④ + 自举 + autopick_anchors |
| `topics/rl-general-toolbox/topic.json` / `…/rl-digital-human-interaction/topic.json` | 改：加 score_anchors |
| `docs/score-drift-research-findings.md` | 新建：调研+方案+落码状态 |
| `CLAUDE.md` | 改：topic.json 字段 + 漂移修法节 + 工具表 |
| 记忆 ×3（仓库外）| score-drift-external-research（新）/ human-gate-telegram（新）/ MEMORY.md（改）|
| `pipeline/tools/pick_anchors.py` | 建后又删（净增 0）|

## 四、验证到哪
- 编译 ✓；隔离逻辑 ✓（prompt 注入/anchor_block/洗牌确定性/boundary cutoff·band·取均值·zz 覆盖/首跑·增量两路）；真实 claude -p 单批烟测 ✓（合法 JSON、reason 真引原文、分 15/56/92）；自举两遍流程 stub 测 ✓（首跑 bare+anchored、二次单遍不自举）。
- **还没做**：临时库（`RESEARCH_DB=/tmp`）完整端到端（discover→score 带自举→commit，确认 zz_boundary 真被合并覆盖、自举真写 topic.json）。

## 五、下一步（待用户定）
- a) 跑临时库端到端验证；b) 提交这批改动；c) 暂停。
- 增量跑 ④ 的 band 宽度/采样次数若实跑后想调，在 `boundary_rerank` 默认参数处改。
