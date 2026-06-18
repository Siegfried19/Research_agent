# prompts 总账 —— 当前写法 + 演变史

> 建于 2026-06-18。回答"当前 prompt 长啥样 / 以前长啥样"——以前要么读代码、要么 git 考古,散在三处,这里集中成一张**导航地图 + 变更史**。
>
> **⚠️ 铁律:代码为准。** 本文件是**地图与 changelog,不是镜像**——prompt 原文的唯一真相在脚本里(下表给了 `文件:函数`)。这里只放"在哪、enforce 什么、为什么变",**节选的句子标「节选」、随时可能和代码漂移**。不要据本文件改 prompt;改 prompt 改代码,然后回来补一行 changelog。
> (反面教材:`summary-prompt-rewrite-plan.md` 曾内嵌完整 prompt 文字 + 标"待执行",落地后没同步就成了误导源。)

---

## 一、prompt 在哪(导航地图)

| # | prompt | 位置(代码为准) | 引擎 | enforce 什么(一句话) |
|--:|---|---|---|---|
| 1 | **打分 rubric** | `find/score_auto.py` → `prompt()` + `GENERIC_BANDS` + `anchor_block()` | claude -p | 0-100 相关性;通用分档 + topic.json `score_anchors` 钉刻度;reason 须引原文 |
| 2 | 打分魔鬼代言人 | `find/score_auto.py` → `panel_prompt()` | codex | 只找"该拒"的理由(默认关,用户 06-10 拍板) |
| 3 | **总结** | `summarize/summarize_auto.py` → `build_prompt()`(+`_resummary_block`/`quality_directive`/`_template`) | claude -p | 边读 PDF 边写;只用本 PDF;正确性>可提取性>文笔;数字让位 PDF;原子句+内联 strength;7 问自查 |
| 4 | **核查** | `verify/verify_summaries.py` → `vprompt()` | codex(claude 应急) | self-render 读整篇 PDF;claim 级语义核查(方向反转/张冠李戴/过度声称);severity 四态;数字从宽;report-only |
| 5 | 免费源猎手(hunt) | `fetch/recover_agent.py` | claude -p + WebSearch | 联网找合法免费 PDF(禁 Sci-Hub 类) |
| 6 | 检索精挑(RCS) | `retrieve/rerank.py` | claude -p | 从混合召回里精挑最相关 |
| 7 | 带引用回答 | `retrieve/answer.py` | claude -p | 闭集综合命中、会说"库里没有" |
| 8 | 老总结更新 | `tools/update_auto.py` | claude -p | 旁路:有新信息时更新已有总结 |

下面只展开 1/3/4(核心三件套);2 与 5–8 直接看代码。

---

## 二、核心三件套·当前写法(设计要点,节选)

### 1. 打分 rubric（`score_auto.prompt`）
- **通用分档骨架**(`GENERIC_BANDS`,节选):`90-100 直接命中核心问题 / 60-89 强相关 / 30-59 弱相关 / 0-29 基本跑题`——通用,不再写死某主题的例子。
- **锚点注入**(`anchor_block`):每批 prompt **一字不差**带上 topic.json 的 `score_anchors`(高~95/边界~45/低~10 三张已定分样本),钉死跨批刻度,治"rubric execution drift"。
- **证据接地**:reason **必须引 title/abstract 里的具体词句**,不许泛泛。
- 配套(非 prompt,但同治漂移):batch 20 + 批内洗牌(对冲位置偏置)、`boundary_rerank` 去留线 ±8 窄带 ×5 取均值复称。
- 冷启动:无 anchors 时裸跑整遍 → `autopick_anchors` 自举挑 3 张写回 topic.json → 带锚重打。

### 3. 总结（`summarize.build_prompt`）
- **一趟边读边写**:通读整篇 PDF(含附录/补充材料,超 20 页分批 `pages` 读完)→ 写 → 7 问自查。**无 note_plan、无接地门**(2026-06-18 去掉,见演变史)。
- **PDF 是唯一原文来源**:事实/数字/公式只能来自本 PDF,原文没写就 `[原文未提]`,不许脑补;**反向也不许**断言"本文没有 X"(没读到≠不存在)。
- **判断轴 = 正确性 > 可提取性 > 文笔**(首要读者是 agent)。
- **数字让位 PDF**:给量级/方向 + 出处即可,不堆精确数字、不把孤立数字当卖点。
- **原子句 + 内联 strength**:一句一个点;结果句末标 `observed|supported|strong`,措辞不许超过 strength。
- **重做避坑块**(`_resummary_block`,核查 major 触发 resummarize 时插在顶部):把上版被核问题当**避坑提示**,但**无裁决权**——不许据清单反推原文、不许照搬旧版、不许伪造"已核对"背书,一切以亲读 PDF 为准。
- **质疑模式**(`quality_directive`):suspect(掠夺刊名单命中)→ 注入批判指令(警示行/"作者声称"/≥5 条质疑)。

### 4. 核查（`verify.vprompt`）
- **同源核查**:原文一律以**整篇 PDF**给核查模型(无文本兜底、无截断)——总结本就只从 PDF 写,核查同源。codex 自渲染(`./paper.pdf`,自己 pdftotext + 渲染页面看公式/图表);claude 应急后端用 Read 工具直读。
- **reasoning_effort = 中等**(claim 级语义核查,不上最贵逐字渲染档;`config.verify.reasoning_effort`)。
- **专查四类**:语义忠实(偷换/过度声称)、**方向反转**(逐条对方向,最易漏)、**张冠李戴**(把背景/related work/别的设定的结果安到本篇)、数字与图表是否被歪曲。
- **认总结的数字立场**:没给精确值/只给量级方向**不算错、不报**;只有数字**矛盾或张冠李戴**才算。
- **severity 四态**:`major`(编造/方向反转/张冠李戴/过度声称=会污染"值不值得深入"判断)→ 触发整篇重做;`minor`(孤立精度/措辞略强)→ 只报告;`unverifiable`(这轮没核到,非错误)→ 提示人工复看;`pass`。
- **report-only**:绝不改总结(改由 summarize 段 resummarize 整篇重做)。

---

## 三、演变史（为什么变成现在这样）

> 链到 `logs/SESSION-*.md`(细节)与 CLAUDE.md 对应节。旧 prompt **原文**靠 `git log -p -- <脚本>` 翻。

### 总结 prompt
| 日期 | 变化 | 缘由 / 出处 |
|---|---|---|
| ~06-09 | claude -p 无头总结(取代 Workflow agent) | 流水线全自动化 |
| 06-15 | 加"张冠李戴"防线 | 抽样发现把被引文献数字安到本篇(commit b5dafc1/145c94a) |
| 06-16 | note_plan + 接地门两阶段(先列计划/逐句接地) | `SESSION-2026-06-16-summarize-verify-IMPL.md` |
| **06-18** | **去 note_plan/接地门 → 回边读边写**;数字让位 PDF;原子句+内联 strength;加"适用边界"段 | note_plan 实测危害>收益;`docs/summary-design-principles.md §八` + `SESSION-2026-06-18-summarize-verify-rewrite.md` |

### 核查 prompt
| 日期 | 变化 | 缘由 / 出处 |
|---|---|---|
| 06-10 | Codex 核查 + `correct_summaries` 打补丁修正 | 跨模型评审团上线 |
| 06-15 | PDF 为唯一原文源;codex 自渲染看公式/图表 | commit 0d0ce64 / 26c3bb8;`SESSION-2026-06-15-verify-rerun.md` |
| 06-17 | 发现旧 correct 会**反向裁决核查员 + 伪造"已核对"背书** | `SESSION-2026-06-17-summary-version-comparison.md` |
| **06-18** | **report-only + major→整篇 resummarize**(删 correct_summaries);severity 加 `unverifiable` 态;**数字精度从宽**(claim 级语义核查,中等 effort) | 根治反向裁决 bug;`docs/summary-design-principles.md §八` |

### 打分 prompt
| 日期 | 变化 | 缘由 / 出处 |
|---|---|---|
| 早期 | rubric 写死 digital-human 例子;batch 10 | — |
| **06-17** | **通用分档骨架 + `score_anchors` 注入 + 证据接地**;batch 10→20 + 批内洗牌;`boundary_rerank` 复称;无锚自举 | 治跨批"rubric execution drift";`docs/score-drift-research-findings.md` + `SESSION-2026-06-17-score-drift-impl.md` |
| 06-10 | 魔鬼代言人(panel)上线,**默认关** | 异议火力集中总结侧(用户拍板) |

---

## 四、维护约定
- 改任一 prompt → 改对应脚本 → 回本文件 §三 对应表补一行(日期/变化/缘由+出处)。
- 想看当前完整原文:打开 §一表里的 `文件:函数`。想看旧原文:`git log -p -- <脚本>`。
- 设计原则的"为什么"层另有专档:总结/核查 → `summary-design-principles.md`;打分 → `score-drift-research-findings.md`。本文件不重复推导,只做地图+changelog。
