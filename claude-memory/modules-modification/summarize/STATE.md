# summarize — STATE（层积日志）

> 写法：**新在上、老在下、不删**，每条标题带日期+时间戳。最顶一条 = 此刻状态/卡在哪；往下翻 = 历史。
> README.md 是定型设计（覆盖更新）；这里是带细节的过程账。
> 局部改动记这里；跨模块/全局改动记 `../../../claude_log.md`，这里只留一行指针。

## 2026-06-21 03:18 EDT · 指针：web 源排除谓词补齐 + 拉取改版接口对齐（跨模块，详见 claude_log）
- `kind='web'` 源不进总结的谓词 `(kind IS NULL OR kind!='web')` 之前只在 `build_worklist`,本轮补到 `register_summaries`(否则 web 恒算"missing")+ `run.py:topic_progress`(否则夜间队列卡死)。三处现已一致。大改名(papers→sources 等)在 summarize 侧已传导完整。详见 `../../../claude_log.md`(03:18 条)。

## 2026-06-20 04:19 EDT · 指针：存储布局改版（跨模块，详见 claude_log）
- 总结落点 `store/summaries/<slug>/vN.md` → `store/papers/<slug>/vN.md`。build_worklist/register_summaries/summarize_auto/render_topic + tools/prepare_update 已改走 `lib/store.py:paper_dir/summary_file`。全局账见 `../../../claude_log.md`（04:19 条）。

## 2026-06-20 02:16 EDT · 重构首条（当前状态快照）

> 文档模块化重构建立本日志。以下为当日现状；以后变化在本条**之上**叠新条。

### 现在能跑的
- 三步主链稳定：`worklist → sum → finalize`（run auto / auto-sum 链上）。代码即现行设计——边读边写 + 7问自查 + 内联 strength + 适用边界段，note_plan/接地门已去掉（2026-06-18 落地）。
- `resummarize`（整篇重做，无裁决权）已落代码，被 verify 段 major 回调；旧 `correct_summaries.py` 已删。
- 夜间无人值守靠队列模式 `auto-sum-next [N]`（cron 按 `topics.priority` 挑下一个有可做篇的主题，一批 ≤N 篇）。批量节奏：一晚两批、各 ~20 篇、相隔 ~5.5h（2:00/7:30 两条 cron）。
- ⚠️ **verify 已从夜间 sum 链摘出**（2026-06-19）：夜间 cron 只 `sum+finalize`，核查交给全天候守护 `tools/verify_daemon.py`（避免 cron 和 daemon 抢同一 codex 配额窗）。

### 当前进度（库重建中，会动）
- 用户正在**按新原则重做总结**（旧 221 篇老总结已备份 `logs/wipe-summaries-20260617/`，留作基线）。
- **截至 2026-06-20，DB 实测 `status='summarized'` = 60 篇**（version 分布 v1=60 / v2=13 / v3=6 / v4=2，重做版叠加 verify churn 的产物）。
  - 注：claude_log 早先条目（06-19 04:43）写"库现 20 篇"、交接处写"~39 篇"——都是重建过程中的快照，**现已推进到 ~60**；这是动态数字，跑前以 `sqlite3 db/papers.sqlite "SELECT count(*) FROM papers WHERE status='summarized'"` 为准。
- 重做完后要重跑 `retrieve/index` 让检索层增量跟上（属 retrieve 模块的事）。

### 未决 / 已知问题
- **重做次数无全局闸（待补，与 verify 模块联动）**：`escalate` 的 `--max-attempts 2` 是单进程内计数，daemon 反复调会清零 → 硬论文被 churn（病例 `Input-to-State Safety for RL` churn 到 v5，v5 还被 claude 写出 11 处阿拉伯乱码 `ISالالسf`）。用户已拍：要做**跨运行重做总闸（≥3 次仍 major → 标人工）**。详见 claude_log 2026-06-20 00:36 条。
  - 该篇当前已 `record_skip` 钉版 v4、复制进 `review/` 待用户手动改；daemon 不再碰。
- **v2 危险中间态**（重做产出的中间版本）如何不外泄给下游消费者：未决（design-principles §七遗留）。
- 老 221 篇基线 vs 重做版的最终取舍（"全部重做" vs "拿老版当基线只补未做篇"）：用户尚未最终拍板（design-principles §六/§七）。
- claude 偶发输出抽风（如上面乱码版本）目前靠 verify 端 record_skip 兜，summarize 端无主动检测。

### 待办（已讨论未做）
- **手动加 PDF 入库** `tools/add_paper.py <主题id> 论文.pdf...`：跳过整条下载链，直接落库→sum→verify。命门=从 PDF 识别身份（DOI/arXiv → OpenAlex 标题模糊配 → 裸入库）+ 去重（规范化 DOI 精确判重）。3 个待拍决定见旧 CLAUDE.md「待办」节。搁置中。

### 上次卡在哪
- 主线在跑：用户重做总结（库已到 ~60 篇）+ verify daemon 全天候啃积压。
- 系统性补丁（跨运行重做总闸 / codex 连崩封顶）已被用户认领"细节后议"，**未落代码**。
- 本模块代码近期改动止于 2026-06-18（prompt 重写 + resummarize）；之后的动作集中在 verify 段（失败分类器重构 2026-06-20 00:09、daemon churn 修补）。

---

## 2026-06-18 · summarize 层重构 + 总结 prompt 重写（去 note_plan，回"边读边写"）

> 缘起：换机器后继续 2026-06-17 搁置的"总结层设计转向"。先落结构性重构，再重写 prompt。
> 上游原则：`claude-memory/Prompt-structure-design/summary-design-principles.md`（§八 + 八续定稿）；prompt 细节：`claude-memory/Prompt-structure-design/summary-prompt-rewrite-plan.md`。
> ⚠️ 本会话只改代码/文档，未提交、未重跑任何生产总结。老 221 篇原封不动（备份 `logs/wipe-summaries-20260617/`）。

**修正→重做（机制层）**：删 `correct_summaries.py`（打补丁式，是"反向裁决+伪造背书 bug"的来源）；新增 `summarize_auto.resummarize`——major 触发 → 从 PDF **整篇重写** vN+1，问题清单只当避坑提示、**无裁决权**（`_resummary_block`）。用户拍板："取消自动修正"=取消裁决权而非取消修正，且因"反正要重做"直接退化成整篇重做、无独立打补丁步。

**去掉 note_plan + 接地门，总结回到"边读边写"**：删 `pipeline/tools/grounding_gate.py`、`config.json` 整个 `summarize` 段、`summarize_auto` 里 `GATE_ON`/`_gate_block`/note_plan 脚手架。去掉理由（查史坐实，写进 plan 文档 §四）：
- note_plan 实测制造"无锚论断"假阳性洪水（`redo-batch2` 报告成片"原文其实支持"的假 minor）→ 被旧"非 pass 全重写"放大成版本通胀。
- 接地门只验"引文在不在"、防不住张冠李戴（真危险）；两段式"剥离数字成锚点"本身是张冠李戴的诱因。
- 且老总结时代严格"编造引文"本就几乎没发生（老总结几乎不引文；接地门唯一真跑那次 36 条全过、0 抓到，真幻觉是 codex 抓的）——它防的威胁没真发生，真问题它接不住。

**重写 summarize `build_prompt`**（`claude-memory/Prompt-structure-design/summary-prompt-rewrite-plan.md` 是完整文字源）：4 步→3 步（通读→边读边写→7问自查）；开头加"给谁看（agent 首要）+ 判断轴（正确性>可提取性>文笔）"；**数字让位 PDF**；论断改**原子句 + 内联 strength**；模板加**适用边界**一等段落 +"主要结果（写方向不堆精确数字）"+"用什么方法（含直觉）"；7 问重排到方向/直觉/防张冠李戴/可提取。tools 收成 `["Read"]`。

**样例验证（SAC，arxiv:1801.01290）**：新 prompt 实跑一版到 `/tmp/sac_new_prompt.md`（临时，没碰生产）；**119s**（note_plan 时代 ~300s+，快一半）。对照现有 v1（note_plan 引文密集风格）：新版在可提取性（内联 strength）、方向准确、适用边界段、直觉、批判性上明显更优；**唯一偏差**："数字克制"只做了一半——仍逐字转写全部公式+Table1 超参（但都挂了出处、没当结论卖点），对 agent 无害，偏密。用户结论：目前问题不大，后面有问题再改。

待定（summarize 侧）：是否提交（先 log 没说提交）；"数字克制"要不要更狠（把"公式只述结构不逐字转写"写进 prompt）；存量总结取舍（"去掉今天 40 篇重做" vs "拿老 221 篇当基线只补未总结"）——未定。

> ⚠️ 属 verify、未搬（留给 verify 模块）：核查引擎重构（codex `reasoning_effort=medium`、永远 self-render 读整篇 PDF、删省钱文本路径+40万截断、claude 应急后端改 Read 直读 PDF）；severity 四态收窄到"只有 major 触发重做"（`escalate_verify`）；codex verify `vprompt` 重写（数字立场告知 + 方向反转专项检查 + 删 note_plan 坐标块）；"还没用新 codex 实跑核查过一篇新总结"这条待办。

## 2026-06-17 · 总结层设计 deep-research 调研（外部验证 + 立场校准）

> 来源：`logs/SESSION-2026-06-17-design-research.md`（已搬入，原文件用户统一删）。
> deep-research（104 agent / 22 源 / 101 claim 抽取 / 25 条对抗核验，3 杀）对"总结=方法分诊层、数字让位 PDF、只守语义方向"取向的外部验证。服务于 `claude-memory/Prompt-structure-design/summary-design-principles.md`（据本调研升 v1）。
> 一句话结论：**大方向被强力支持，但"数字不必守"这条被校准为"数字精度让位 PDF、但语义级核查仍会顺带守住要命的数字（misattribution / 矛盾）"。**

**强力支持的（我们对的部分）**：
- 两段式科学 RAG 是主流，**PaperQA2 最可抄**：检索块先经 LLM 产 `{summary, relevance_score}` JSON 再进答案上下文（RCS=Reranking & Contextual Summarization），摘要 200-400 token vs 原块 2250（~5-6x 压缩不降效）；OpenScholar / SciRAG 同模式。
- **PaperTrail（CHI 2026, arXiv 2602.21045）= 与我们架构最贴近的原型**：离线预抽每篇 claim+evidence 成**可版本化 JSON 知识库当 ground truth**，昂贵的相关性判断延后到查询时——正是"摘要/claim 层即真相、原文延后、算力前移到离线"。溯源单位=**claim**（非引文/数字），三分类 **Supported / Unsupported / Omitted**。
- **核查要下沉到 claim/原子级、不做整体二元打分**（FActScore, EMNLP2023："生成混合被支持与不被支持的信息，二元判断不充分"；拆原子事实算被支持占比，作者明说可推广到科学文献）。
- **词面指标（ROUGE/BLEU）对事实错不敏感 → 必须语义级核查**（QAGS, ACL2020：语义一致性与人工相关性约为 ROUGE 的 3x）——直接支持"守语义不守 token/数字面"。
- **便宜语义核查工程可行（关键，解 codex 额度）**：MiniCheck（770M，~400x 便宜于 GPT-4 却达 GPT-4 级事实核查，逐句对证据核；arXiv 2404.10774）、SummaC / AlignScore（轻量 NLI 切句聚合）。
- **结构化、机器可消费的总结已成熟**：Dagdelen（Nat Comm 2024，抽成 JSON 对象列表填库）、CS-PaperSum（固定字段 Key Takeaways/Method/Performance/Future Work）、Paper2Agent（论文方法→可执行 MCP Tools 供下游 agent 调）。

**被校准 / 反对的（我们要收的部分）**：
- **"数字不重要、可让位 PDF"只得部分支持 + 有明确反例**：压缩摘要快筛（PaperQA2）、抽象总结牺牲逐条可归因（SciRAG 自陈）只支持"摘要层适合快筛"；**但 FActScore 把数字当原子事实去核、CS-PaperSum 专设数字字段——没有任何一手来源主张"总结里可放过数字"。**
- **可辩护立场（改这条）**："**语义/方向忠实最致命、数字精度让位 PDF 检索**"，而非"数字不必守"。
- **3 条被对抗性否决（别过度引用）**：① FActScore 不能宣称"误差<2%替代人工"；② 引文/grounding 忠实重要但**不是"唯一决定性失败模式"**；③ SciRAG 的 Correctness Score 不是"方向+相关性替代数字精确"。

**对设计的净启示（落进 design-principles v1）**：
1. **架构对**：沿用"总结层分诊 → PDF 按需"；可抄 PaperQA2 的 `{summary, relevance_score}` 与 PaperTrail 的"claim 级离线 JSON + Supported/Unsupported/Omitted 三分类"。
2. **数字立场收一格**：**保留数字**（它们是原子事实），但**数字精度的权威在 PDF**——总结不装精确、不堆假精度。
3. **结构化**：总结可往"claim 级可抽取"靠（每条方法论断成原子单元），便于核查 + 便于 agent 提取。

可抄清单：PaperQA2（`{summary,relevance_score}` 逐块 + Gather-Evidence 早筛）、PaperTrail（三分类 + 版本化 JSON ground truth）、FActScore（拆原子事实非二元）、MiniCheck/SummaC/AlignScore（小模型逐句 entailment 替 codex）、CS-PaperSum/Dagdelen（固定字段 + JSON）、Paper2Agent（方法转 MCP tools，远期出口③）。

> ⚠️ 属 verify、未搬（留给 verify 模块）：本调研对"核查重做"的取向——用便宜 claim 级语义核查（MiniCheck/SummaC/AlignScore 或便宜 LLM-judge）拆 claim 逐条判 entailed（顺带抓 misattribution/数字张冠李戴，免 codex 逐字渲染 PDF）；另配一个针对"结论说反"的 LLM-judge（NLI 工具不擅方向反转，此为工具契合度 caveat）；输出走 Supported/Unsupported/Omitted 三分类、report-only 不自动重写（根除"修正环节反向裁决+伪造背书"bug）。

## 2026-06-16 · summarize 改造落地（接地门 + 五步 prompt，端到端测过）

> 上一会话出了方案（`ref/TO-BORROW.md` ★落地决定），本会话动生产代码实现 summarize 侧（此为当时设计；后被 2026-06-18 推翻回"边读边写"）。
> 架构=单 agent 模式：确定性 Python 批量层不动，单篇层一个 `claude -p` 多步（读→note_plan→接地门→写→自检），外层 Codex 跨模型核查（写≠查）。

**新增 `pipeline/tools/grounding_gate.py`（接地门）**：对 PDF 跑 pdftotext，把 note_plan 每条 `quote_en` 与原文都归一化成"连续字母数字串"（抹空白/连字符/标点/断词换行）做子串匹配；判 `ok`/`partial`/`fail`/`too_short`；退出码全过 0、钉不住 1、读不动 2。零 token、确定性。`config.json` 加 `summarize.grounding_gate`（默认 true）——它是新流程唯一多烧 token 处=省 token 开关，但实测省不下多少 → 保持开，当调试逃生口。

**`summarize_auto.py` 重写 prompt**：`build_prompt` 五步——①知识隔离铁律（事实只来自本 PDF，没写标 `[原文未提]`，写作能力照常）②读全文 ③用 Write 列 `note_plan.json`（每条 kind/point/quote_en/where/strength）④接地门必过循环（Bash 跑门脚本，钉不住改 note_plan 重跑，≤2 轮）⑤写总结（引文加引号、措辞不超 strength）⑥7问自查。`clean_output()` 砍模型在 YAML 前的寒暄。note_plan 持久化到 `summary_dir/note_plan.json`（供 verify 复用）。工具加 `Write`+`Bash(python3:*)`；超时 900→1200。`quality_directive` suspect 分支加"strength 封顶 observed"。

决策：门保持开；**反 AI 腔暂不加**（治文笔、机器读者优先级低）；**7 问保留**（用户要——输出要喂别的 agent，深度重要）；strength 逐条（observed/supported/strong），method 类不填。

实测（PPG Reloaded，生产没碰，写 `/tmp/bakeoff/`）：323s；36 条 note_plan 接地门全过；新总结 vs 旧——英文引文 39 vs 3、页/节锚点 71 vs 0，局限更批判；抓到旧总结一处疑似编的数（墙钟 20.4s，新从表2 锚出 31.2s）。

**运行节奏改变后的策略调整**（用户改"每晚两次×~10 篇，挑不占 token 时段"，token 不再是约束 → 省 token 换最大质量）：去掉 Codex 省 token 的窄化（verify 的 note_plan 从"定点核对、不必通读"改成"辅助坐标 + 仍完整读全篇"）；"有问题的都重新来"（escalate 的 correction 从"只修 major"扩到非 pass 全修）；`unverifiable` 也重做；默认全审（抽样 10%→100%，每次就 ~10 篇）。

**summarize 侧补丁（由 verify 端到端测试暴露）**：测试揪出新总结编了"本 PDF 不含附录图表"的假话（实际有 Appendix A/B）→ 给 prompt 加两处：①铁律加"反向"一条——不要断言原文"没有/未包含/未给出"某内容，**没读到≠不存在**（附录/补充材料/大表常在后几页），拿不准就回去读完后面的页；这是 unverifiable 思路的撰写侧版本。②第一步·读全文补"含正文之后的附录/补充材料/大表"。py_compile + 结构 smoke 过，未重跑端到端。

下一步（当时）：多篇 bake-off（含 suspect、含旧流程被揪过 major 的）过新 verify 比 major 率 + 验"附录假话"补丁 → 决定是否放量重跑两主题总结。

> ⚠️ 属 verify、未搬（留给 verify 模块）：verify 侧全部实现（`verify_summaries.vprompt` 重写 + note_plan 坐标块 + 张冠李戴/数字图表防误配三层检查 + `unverifiable` 两分政策）、`correct_summaries.py` 过滤 unverifiable、`escalate_verify` round 日志加 unverifiable 计数/非pass全修；真 Codex 端到端测试（PPG，114s，verdict=major，揪方向反 + "附录不存在"假话，坐实"写≠查"价值）。其中"附录假话"测试是 verify 跑出来的，但由它催生的 summarize 侧补丁已搬入上文。

## 2026-06-16 · 参考调研收尾 + 架构拍板（未动代码）

> 目标：改造 summarize+verify，治"张冠李戴幻觉"+"summarize prompt 不够好"。本会话=逐个过完 4 个重点参考 + 拍板架构，未动任何生产代码。

逐个过完 4 个参考，把"要借的"落到 `ref/TO-BORROW.md`（取用清单，跟描述性的 REFS-OVERVIEW 分开）：
- ① DeepPaperNote：接地 + 证据四分（note_plan）/ 接地门脚本 / 7问。
- ② claude-scholar：Evidence-gated → claim strength 四档 / allowed-forbidden 措辞 / source trust 分级（已拍板要借）。
- ③ ARS：借**两个写作侧文件**（anti_leakage 知识隔离 + writing_quality 反AI腔），**非** deep-research 13-agent 本体；补 3 条（vibe-citing / 魔鬼代言人 / 灰区=FAIL→unverifiable 分类型）。
- ④ paper-qa：A组现用（图表防误配 / I-cannot-answer / 引文加引号）；B组（闭集 citation key）留给出口②③ RAG。

**拍板架构=单 agent 模式**（模式1）：一个 agent 多步 + 确定性脚本（接地门）+ 外层 Codex（写≠查）。依据：真正读单篇的①②④全单 agent，唯一多 agent 的③干的是整篇论文大活；借的全部装得进单 agent。处理一篇的 6 步全流程见 `ref/TO-BORROW.md` ★落地决定节。

支线：把 claude-scholar 的 `planning-with-files` 抽成独立库 `~/Projects/agent-skills`（复制式 install→`~/.claude/skills/`，远端待用户 push）。

下一步（当时）：出正式落地方案——写单篇总结 skill（知识隔离→note_plan+claim strength→接地门→写/引文加引号不夸→自检/反AI腔词表/7问）+ 改 `summarize_auto.py` 每格调它。待拍板小取舍：7问只进 summarize 还是也进 verify；接地门对"中文总结→英文 PDF"怎么定位出处。

> ⚠️ 属 verify、未搬（留给 verify 模块）：本会话的产物中，`verify_summaries.py` 加 `unverifiable` 档（按论断类型分政策）、反AI腔英文词表本地化属 verify/旁路；架构里"外层 Codex 写≠查"是共享前提，已在上文带出。
