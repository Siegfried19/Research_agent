# find 段「facet 改写」设计成品（存档格式 + 编排 prompt）

> 状态：**设计定稿，未落代码**（2026-06-20）。新会话接手直接照此实现。
> 来龙去脉见 `claude-memory/modules-modification/find/STATE.md`（2026-06-20 的几条层积日志）。
> 大原则：**Claude 负责判断与编排、管道负责力气与确定性执行；脚本从焊死一条龙变成"agent 手里的工具"**。这是对 2026-06-09「把 Claude 移出 runtime」的**精修**（仅限 find + fetch；summarize/verify 继续无人黑箱）。

---

## 0. 为什么改（病根）

现行 discover→score→commit 是焊死的一条龙，"一把尺子全局 Top-N"。一个主题其实是**好多组论文（facets）**，三病：①**小簇饿死**（冷门 facet 被论文多的挤掉名额）；②**一把尺子量五件事**；③**丢结构**。
现实触发器：新主题 `agentic-knowledge-synthesis` 首轮，`prefilter_rank` 纯词法取前 70，把奠基作 GraphRAG/RAPTOR/PaperQA2/OpenScholar 全切掉 → 召回不足（首轮已废弃重来）。**find 的病=死规则判断失误**——所以这里值得 Claude 重介入（与 retrieve 不同，retrieve 实证说小库 agentic 增益有限）。

---

## 1. 存档格式（地基①，定稿）

**拆两个文件**（关键：pipeline 自动写的状态 与 人/讨论手定的意图 分开，否则状态每轮脏掉手编意图）。

### `topic.json`（意图——讨论里当场定，pipeline 基本不回写）

```json
{
  "id": "rl-general-toolbox",
  "title": "...",
  "idea": "...全局总思路,保留...",
  "window_years": 12,
  "target": 100,
  "preferences": "偏好可操作/有实验对比/给 do-don't;排斥纯理论",

  "facets": [
    {
      "key": "safety-cbf",
      "title": "control barrier function 等安全增强 × RL",
      "hit_criteria": "命中=CBF/安全约束真正与 RL 结合且有方法或实验;只谈 safe RL 不涉 CBF 算半相关;纯控制论 CBF 不沾 RL 不算",
      "queries": ["control barrier function reinforcement learning safe control",
                  "safe RL constrained policy optimization"],
      "anchors": [{"title": "...", "score": 95, "reason": "..."}],
      "seed_ids": ["arxiv:2010.xxxxx", "10.xxxx/yyy"],
      "note": "用户标重点,别饿死"
    }
  ],

  "web_sources": [
    {"url": "https://lilianweng.github.io/posts/...", "facet": "training-tricks", "note": "手挑"}
  ]
}
```

字段说明（这段同时是要喂进 orchestrator prompt 的"存档 schema 说明"）：
- `idea`：全局总思路，保留（facet 是它的拆分，不替代）。
- `target`：全局目标总篇数。
- `preferences`：全局取舍偏好（一句话，所有 facet 通用）。
- `facets[]`：主题的子方向。**无此字段=退化成现状**（facet=1 全局单尺子；gt/dhi 不改也照跑）。
  - `key`：稳定短标识（程序用）。
  - `title`：人读的 facet 名。
  - `hit_criteria`：⭐**一句话命中标准=per-facet 语言尺子**。补 anchors 这 3 个点之间的"规则"；冷启动 anchors 没凑齐时先顶上当尺子；discover 判够不够 / commit 归类 / 博客软判命中哪个 facet 都复用它。
  - `queries[]`：该 facet 的检索词。
  - `anchors[]`：该 facet 的打分锚点（高~95/边界~45/低~10 的已定分参照样本）。**从全局挪进 per-facet**，治"一把尺子量五件事"。无则冷启动可自举或先靠 hit_criteria。
  - `seed_ids[]`：按 DOI/arxiv id 点名**必进**的奠基作（绕开 prefilter 词法漏洞）。需「按 id 播种」工具（见 §4）。
  - `note`：软偏好（如"重点别饿死"），**非配额数字**——留几篇是 commit 时 Claude 判断。

### `topic_state.json`（状态——pipeline/orchestrator 每轮自动写，用户一般不碰、必要时当手动开关）

```json
{
  "facets": {
    "safety-cbf":    {"in_db": 3,  "coverage": "薄,下轮补", "last_run": "2026-06-20"},
    "reward-design": {"in_db": 18, "coverage": "够",        "last_run": "2026-06-20"}
  },
  "turning_seeds": [
    {"hint": "intrinsic curiosity 那条线没挖", "from": "reward-design 某篇引用", "kind": "query"},
    {"id": "arxiv:2401.xxxxx", "from": "顺引用发现", "kind": "id"}
  ]
}
```

- `facets.<key>`：各 facet 覆盖状态 / 已入库计数 / 上次跑时间。**想逼某 facet 重搜=清它的 coverage。**
- `turning_seeds[]`：**拐弯种子**——上一轮发现的好线索，下一轮起点。`kind`=query（补检索词）或 id（顺引用/发现的具体论文）。

---

## 2. 治理 / 通知模型（定稿）

- 工作流 = **「你出问题 → 我们讨论定方向 → 交给我自主跑」**。facets/命中标准/锚点/种子**都在讨论里当场定**（不是 Claude 背着用户自举完再推 TG 审批——那套是无人冷启动才需要）。讨论定完，Claude 直接写进 topic.json。
- **配额=判断不是数字**：存档不存配额数字。commit「定稿」时 pipeline 把候选+打分按 facet 分好组摆出来，Claude 看分布自己决定每组留几篇（小簇别饿死/富矿别滥收）。
- **通知三档**：
  1. 例行判断（每 facet 留几篇/边界取舍/增量 commit）→ **只留痕**（log/state/commit 报告），不打断。
  2. **新发现** → **TG 通知**（默认继续跑不停等审批，但给用户随时叫停/改向的机会）。三类：① 想加存档里没有的 facet；② 拐弯种子明显指向新子领域；③ 某 facet 喂不饱（持续饿死）。
  3. commit 回报 + tierb 验证点击 → 照旧。
- 「通知」专指 **FYI 留痕**，不是审批闸。

---

## 3. 编排模型（地基②，定稿）

**唯一模型：拉起一个 Claude 全权驱动**（cron 和对话共用同一套，差别只在"谁触发"和"通知与否"）。

```
触发（cron 定时 / 用户对话里说）
   ↓
launcher 拉起一个 claude（claude -p，cwd=仓库根，照 bot.py/explore 路子，allowedTools 含 Bash/Read/Write/Task）
   ├─ 给工具：discover.py / score.py / commit.py / 按id播种 / Read / Write(存档) / Task(放手开子agent) / notify
   ├─ 给当前情况：topic.json + topic_state.json + DB 现状(已入库/各facet计数)
   └─ 给 prompt（见 §5）：情况 + 工具 + 项目契约 + 通知规则。**不给"怎么找"的路书。**
   ↓
这个 claude 自己跑完整个 find（判断 + 调工具 + 写回状态 + 回报）
```

**python 只干两件事**：① 拉起 claude、喂情况；② 收尾。中间不插手——discover/score/commit 就是它用 Bash 调的命令行工具（已是 CLI、输出 JSON）。

**关键护栏 = 只有一条，且不写死**：
- **「怎么找/开几个/拐几轮/留几篇」全是它自己的判断，不限制**（撤掉了早先的 5 段路书、拐弯 2 轮上限——都是它的判断）。
- **fan-out 是甜区，鼓励**：facet 天生是独立搜索线，一个 facet 一个子 agent 各搜各的、各回小总结（找到啥/覆盖够不够/候选/拐弯线索）。实证：Anthropic 多 agent "+90.2%、擅长广度优先独立探索"。
  - ⚠️ 唯一仍单线程的是**最后跨 facet 合并 + 定稿**——但那是 orchestrator 在自己上下文里收齐小总结再拍，本来就不会去 spawn"合并 agent"（合并是雷区 MAST 17×），**不用写进 prompt**。
- （可选）防"卡死循环"安全网——用户说连这个都可砍，它按判断停不会空转。**默认不加。**

**与早先 16:30 STATE 的修正**：那条写的"单 orchestrator 不 fan-out""拐弯有界 2 轮""A/B 双驱动"**已作废**——经用户纠正：① fan-out 在 find 是甜区（我把 retrieve 的"合并是雷区"误搬了）；② 拐弯/停止是它的判断不设界；③ 不要 A/B，永远是"拉起 claude 全权驱动"。

---

## 4. 还得真造的零件：「按 id 播种」

`lib/sources` 目前**缺"按 DOI/arxiv id 单查元数据"**的能力。`seed_ids` 要落地、博客 add_url 要落地，都需要它。一鱼三吃（按id播种 / add_url / 将来 add_paper 共"按外部标识单点入库"地基）。
- 输入：DOI 或 arxiv id（或 URL）。
- 动作：单查该 id 的元数据（OpenAlex/SS/arxiv 按 id 查）→ 规范化成 candidate 入池（绕过 prefilter 截断）。

---

## 5. Orchestrator prompt 初稿（待用户最终过目）

> 原则：只给它**推不出来的东西**（情况/工具/项目契约/通知规则），**不教它怎么找**（那是它的逻辑）。

```
你在为研究主题 <topic_id> 做文献「发现」(find)：把一段研究思路 + 检索词，变成"哪些论文进这个主题"。只决定选篇并写库,不取全文、不写总结(那是后面 fetch/summarize 的事)。

【当前情况】
- 意图存档 topics/<id>/topic.json,字段含义:
  · idea=全局总思路;target=目标总篇数;preferences=全局取舍偏好。
  · facets[]=主题的子方向,每个带:key/title、hit_criteria(这个 facet 的命中标准=你打分判相关的尺子)、queries(该方向检索词)、anchors(已定分参照样本,把打分刻度对齐到它们)、seed_ids(必须收进来的奠基作,按 id 播种)、note(软偏好)。无 facets=当单一主题处理。
- 状态存档 topics/<id>/topic_state.json:各 facet 覆盖/已入库数、turning_seeds(上轮留的拐弯线索,可作本轮起点)。
- 库现状:<已入库篇数 + 各 facet 计数>;冷启动(库空)还是增量(每周追新),你据此决定力度。

【你的工具(Bash 调,输出 JSON 你读了再决定下一步)】
- python3 pipeline/find/discover.py <topic.json>  → 按 queries 四源召回去重成候选池(不写库)
- 按 id 播种 <id...>  → 把指定 DOI/arxiv 的奠基作直接拉元数据入池
- python3 pipeline/find/score_auto.py <id>  → 对候选逐批打相关性分(锚点校准)
- python3 pipeline/find/commit.py topics/<id>  → 选定的篇写库
- Read/Write  → 读写两个存档(你可更新 queries/turning_seeds/coverage)
- Task  → 放手开子 agent(facet 是独立搜索线,鼓励一个 facet 一个子 agent 各搜各的、各回小总结)
- notify  → 给用户发 TG

【怎么干——你自己判断】
拆/搜/开几个子 agent/拐几轮/每个 facet 留几篇,全凭你判断。覆盖够了就停。preferences 和各 facet 的 note 要认。
⭐ 收进论文后,翻它们的引用:被反复引、却没在候选池里的奠基作,按 id 播种捞回来——关键词检索常漏这种,这是兜底主力。

【项目契约(你必须遵守,这些不是你能凭空知道的)】
- 选篇靠你的相关性判断,不靠 API 引用量排序(高引常跑题)。
- 文件名用 slug 不用 DOI;papers.id 是 TEXT 主键(无 DOI 没关系)。
- 质量"标记进库、出口认标记":block 永不入库,flag/suspect 带标记入库需更相关。
- 幂等可重跑(已做的跳过);别 git push(只 commit 由用户 push)。
- 撞限流就重跑该步;并发别开太猛刷崩学校访问。

【通知规则】
跑完给 commit 回报(FYI)。撞到"新发现"主动 notify 我:① 想加存档里没有的 facet;② 拐弯线索指向一个新子领域;③ 某 facet 怎么都喂不饱。默认你继续跑,通知只是让我能叫停/改向,不必等我。

开始吧。
```

---

## 6. 实现 TODO（新会话照此落代码）

1. **建「按 id 播种」工具**（§4）——前置,seed_ids/add_url 都要它。`lib/sources` 加按 id 单查。
2. **存档读写**：定义 topic_state.json 的读写;topic.json 加 facets/preferences/web_sources 解析(向后兼容:无 facets 退化现状)。
3. **score/commit 支持 per-facet**：anchors/hit_criteria 降到 facet 粒度;commit 按 facet 分组摆出来给"定稿"判断;漂移修法(锚点/边界复称)降 per-facet。
4. **launcher**：`run.py <id> find` 接管(把焊死的 discover→score→commit 换成"拉起 orchestrator claude")——或单开 `pipeline/find/drive.py`。**待用户拍放哪**。
5. **prompt 落地**(§5,用户最终过目后)。
6. **验证场**:`agentic-knowledge-synthesis` 重搜——把被切的奠基作(GraphRAG/RAPTOR/PaperQA2/OpenScholar/CoA/MAST)经 seed_ids 捞回,验证新设计第一例。
7. **gt 升级样板**(可选):把 gt 拆成 6 facet(reward-design/training-tricks/exploration/algo-zoo/safety-cbf/task-instances)填好,当第一个新格式实例 + 验退化兼容。

## 7. 待用户拍的小决定 —— 2026-06-20 对话已定 4/4

- **launcher 放哪 → 新开 `pipeline/find/drive.py`**(✅定)。find 从"焊死链"变"Claude 驱动",性质和其它阶段(fetch/sum/verify 仍老式)不同,塞 run.py 阶段分发别扭;单独驱动脚本更干净,run.py 的 `find` 阶段调它即可。
- **prompt 初稿(§5)→ 措辞基本认,加一句"顺引用补漏"**(✅定,§5【怎么干】已加 ⭐ 那句;细措辞用户可再磨)。理由:不点这句,「按 id 播种」能力会闲置——Claude 自主播种的主力路径就是"收完翻引用、把高频被引却没收的奠基作捞回"。
- **防卡死安全网 → 默认不加**(✅定)。它本身是个死规则,与"换掉死规则"初心相悖;harness 自带 agent 总数高位兜底 + 库规模天然框成本 + TG 可随时叫停。真发现爱空转再补一个最小的(通常封拐弯轮数即可)。
- **gt/dhi → 先留 facet=1 老模式,opt-in 再补 facets**(✅定,先这样;用户后续按对话改)。无 facets 自动退化,老篇不重评;想升级时拿 gt 拆 6-facet 当样板(§6 TODO-7)。

> 补充确认(同次对话):**打分工具 score_auto.py 保留**(升级 per-facet),变的是"机器全局 Top-N 硬选"那个死规则——降级成"分数喂 orchestrator 判断留几篇"。**"无人冷启动自举+TG审批"流程不要了**,改"讨论当场定";但"库空怎么起步"这个状态 Claude 仍处理(hit_criteria 兜尺子)。**多开子 agent 设计上不限**(fan-out 是甜区),唯一天花板=harness 高位兜底,即"防卡死安全网"管的事(默认不加)。
