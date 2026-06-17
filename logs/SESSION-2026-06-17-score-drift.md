# SESSION 2026-06-17 — 打分阶段「跨批次校准漂移」问题 + 修法方案

> 目标：定位并准备修复 `score_auto` 逐批独立打分带来的**跨批次校准漂移**。
> 本会话只做**分析 + 出方案 + 落 log**，**没碰任何 pipeline 代码、没动生产库**。明天用户回来一起搞。
> 配套记忆：`memory/score-cross-batch-drift.md`。

## 一、怎么聊到这里的（上下文链）
1. 先确认了一个架构判断：**改库层包含了知识库的全部内容，但不包含"检索这种访问模式"**。
   改库层的读全是 lookup（按主键/状态/外键取已知行）；`ask.py` 是 retrieval（自然语言问题找未知 ID 的最相关篇，自带派生索引 fts.sqlite + bm25 + quality 降权 + 引用扩展）。分界是 **lookup vs retrieval**，不是"写 vs 读"。
2. 然后讨论"打分要不要像 summary 那样加 verify→correct 闭环"。**结论：不要照搬**——summary 之所以值得，是因为它(a)是终端产品(b)有 PDF 当 ground truth 可收敛(c)错误静默+终端；打分三条全不占：是闸门、相关性无客观正解、错误多可见可恢复。现有 Codex 魔鬼代言人(`quality.codex_panel`)默认关，是对的。
3. 讲清了 `discover → score → commit` 全流程（见下）。
4. 纯从**错误形态**看打分：**几乎所有出错都收敛成"论文拿 relevance=0/偏低 → 被静默丢"，系统结构性偏向假阴性**；唯一"放垃圾进来"的是模型真把跑题论文打高分（可见、且会被下游 verify/topic.md 撞到）。**唯独"跨批次校准漂移"是召回冗余兜不住的**——多 query 能补回被漏的论文，补不回被打歪的分。→ 用户拍板：**这个要解决**。

## 二、`discover → score → commit` 流程速记（脚本均在 pipeline/stages/）
- **discover.py**：4源(OpenAlex/SemanticScholar/arXiv/PubMed)×多query 捞 → `merge_all` 去重(规范化DOI主键，记 relRankBySource/sources) → 硬信号质量闸(block当场丢，suspect带标记入池) → `prefilter_rank`(**召回导向：各源最好名次 + 多源加成，故意不用引用量**) → 截 `pool_size=min(500,max(target*2,60))` → 写 `candidates.json`。**不写库。**
- **score_auto.py**：候选池切批(默认10)，**并发4** 个 `claude -p`；每批 prompt = idea + 该批 title/venue/abstract，按 0-100 打 relevance + edge_insight 布尔；强制纯 JSON → `scores/batch_<start>.json`。幂等(开跑清空 scores/)；可选 Codex 魔鬼代言人(默认关)。
- **commit.py**：合分 → 选篇闸(block双保险丢 / rel<30且非edge丢 / flag·suspect需rel≥flag_min(45) / Codex异议合议:边界分<60+异议=挡) → 选篇(首跑 eligible[:target]；增量只追新、cap=target*3) → 写 papers+paper_topic → **全主题按 relevance DESC,citation DESC 重算 rank** → 建主题内引用边 → 落 selected.json。

## 三、问题：跨批次校准漂移（本会话核心）
- **病因**：每批是独立 `claude -p`，批之间无共享参照系。现状已被 prompt 里**带绝对锚点的 rubric**（90-100/60-89/… + 主题专属例子）压成"几分的校准噪声"，不是"每批自造刻度"。但几分噪声落在**截断线附近**就翻转去留、打乱 rank。
- **为什么必须单独治**：召回冗余(多query重复发现)能补"被漏的论文"，**补不回"分被打歪的论文"**。漂移动的是相对次序+截断线，冗余对它无效。
- **⚠️ 陷阱（务必避开）**：**绝不能做"逐批 z-score 归一化"**。池子被 `prefilter_rank` **预排序**过，靠前的批本就更相关；逐批统计归一化会假设各批分布相同，把"批0确实比批20相关"的真信号抹平，越治越糟。**任何按批做统计标准化的方案在这条流水线上都是错的。**

## 四、修法方案（待明天一起定 + 过目后再落码）
核心洞察：**校准只需在"会改变决策"的地方紧——95分和10分不需要跨批校准，只有截断线附近窄带需要。** 三步按性价比叠加：
1. **加大批量**（1行，近免费，先做）：`batch_size` 10 → 25~30，批内自归一化，接缝数降~3×。abstract截1200字，30篇~36k字符+输出，context吃得下。
2. **共享锚点**（prompt改造，便宜，治本于预防）：每批塞**同一组已定分参照论文**(如3篇:铁定95/50/15)，把所有接缝钉到同一把标尺。锚点可用真论文(每主题首跑后挑3篇存topic.json)或先用描述型档位例子。
3. **边界重排一遍**（真正的修，asymmetric）：首跑打完，取首轮 relevance 落在 target 截断线 **±N分** 的窄带，**在一次调用里一起重打**，边界去留在单一参照系下定。一次额外调用、只覆盖会翻转的少数篇，绕开 z-norm 陷阱。
- **建议**：①+② 先上(便宜预防)，③ 作真正校正层。

## 五、明天要拍的决定 / 待办
1. **范围决定（唯一卡点）**：要解决的是
   - (a) **只保截断线去留正确** → 做 ①+②+③、③ 只覆盖边界带就够；还是
   - (b) **连选中集内部 rank 次序也要稳**（影响总结优先级+topic.md展示序，stakes 较低）→ ③ 覆盖范围往上扩，成本上去。
2. ① 的 batch_size 具体调到多少（25 / 30）。
3. ② 的锚点：真论文 vs 描述型；真论文的话每主题怎么挑、存哪（topic.json 加字段？）。
4. ③ 的 ±N 带宽、是否也用于增量跑（增量选篇逻辑不同：fresh + cap=target*3，边界定义要重想）。
5. 落码位置：改 `score_auto.py`(①②③主体) + 可能动 `commit.py`(③的边界带定义依赖选篇逻辑)。**方案先写给用户过目再改，不直接落。**

## 涉及文件（本会话只读未改）
- `pipeline/stages/score_auto.py` — 打分主体，①②③ 主要落点
- `pipeline/stages/discover.py` — prefilter_rank 预排序(z-norm陷阱的根源)
- `pipeline/stages/commit.py` — 选篇闸 + 重算rank(③边界带依赖它)
