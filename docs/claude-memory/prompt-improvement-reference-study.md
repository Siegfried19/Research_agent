---
name: prompt-improvement-reference-study
description: 改进 summarize+verify;参考在 ref/。summarize 侧已实现+测过(note_plan+接地门+strength+7问);verify 侧设计中,确认要加张冠李戴语义核查+unverifiable档
metadata: 
  node_type: memory
  type: project
  originSessionId: 87413dbd-2eb6-4cf3-b40b-e306df72f89d
---

用户觉得 `summarize_auto.py` 的总结 prompt 不够好 + 有"张冠李戴"幻觉(verify 揪的那类),让我去 GitHub 找参考拉到 `ref/` 研究。目标=优化 **summarize + verify 两关**。

**克隆了 8 个项目到 `ref/`**(已删 .git/node_modules):老批 ChatPaper/ChatPaperPlus/paper-qa/ChatDailyPapers/summarizepaper(2023 GPT-3.5 时代,只学 prompt 内容不学切块管线) + ARS(academic-research-skills,本就在) + 独立 prompt 在 `ref/prompt-samples/`。

## ⭐ 四个重点来源(用户 2026-06-16 拍板;会**新开对话专门处理**)
> 订正(2026-06-16):此前误记为"三个",把 paper-qa 错归进老批。用户记得是 4 个,核对后确认 paper-qa 是第 4 个重点(本次会话翻它 prompt 验明)。
各管一段,凑一块刚好覆盖用户两句不满(幻觉 + prompt不够好):
1. **DeepPaperNote**(`ref/DeepPaperNote`)——2026 单篇深读 agent skill(支持 Claude Code/Codex),**最对口**=我们 summarize 的高配版。核心抗幻觉机制:写前把每条核心结论拆 **声称/证据出处(节·图)/证明了什么/没证明**(note_plan)。另:创新点专节、机制流程3-4步、数学语法门($...$)、几道分开的质量门。→ summarize 怎么写。
2. **claude-scholar**(`ref/claude-scholar`)——Claude Code 研究助手。借:每条论断标 **claim strength**(speculative/observed/supported/strong) + 引用绝不凭记忆编一律程序化核验。
3. **ARS 的 deep-research 模块**(不是独立仓,在 `ref/academic-research-skills`,两个文件:`academic-paper/references/anti_leakage_protocol.md` + `writing_quality_check.md`)——
   - **知识隔离(Anti-Leakage)**=整个 ARS 最值钱一条,治"张冠李戴"**文本侧**:事实/数字/方法只能来自这篇 PDF,不许拿模型领域知识填,论文没写标出不准推断;但写作能力可用。
   - **写作质量自查(Writing Quality Check)**:反 AI 腔(中文废词黑名单/删清嗓子/凑三定律/术语一致/句长起伏),治"prompt不够好"文笔面。
4. **paper-qa = PaperQA2**(`ref/paper-qa`,Future House,github.com/future-house/paper-qa,**Apache-2.0**可放心借;prompt 全在 `src/paperqa/prompts.py`)——和上三者不重复,补"张冠李戴"最硬两段:
   - **机械化引用落地**:每条论断挂**闭集真实 citation key**(`CITATION_KEY_CONSTRAINTS`:只用上下文给的key/不拼接/不许 `Author et al.(2023)`手挥);信息不足回哨兵句 **`I cannot answer`**(印证我们要加的 `unverifiable` 档);找不到DOI留空绝不编 `10.xxxx`。
   - **图表/公式"就近文字≠本图内容"防误配**(`individual_media_enrichment_prompt_template`/`full_page_enrichment_*`):直击我们 verify 揪的张冠李戴**多模态侧**——图旁文字可能属别处别盲目当本图说明,带 RELEVANT/IRRELEVANT 标签+失败模式(logo/乱码/子图)。配合"Codex 自渲染 PDF 看图表"用。

## 关键判断(供新会话用)
- **summarize 与 verify 耦合**:让总结自己"带证据(声称/出处/证明了什么)",verify 就从通读全文→照出处定点核对,又快又准。最高杠杆=同时改善两关的那几条(DeepPaperNote 的四分 + ARS 知识隔离)。
- 我们 verify **已做对很多**(跨模型 codex≠写总结的claude、PDF 唯一来源、codex 自渲染看公式、"核不到≠编造"豁免、按版本记进度)。最自然的增量=verdict 加 **`unverifiable`** 档(把"原文矛盾=编造"和"这轮没核到=存疑非错"分开)。
- 待用户拍板的取舍:verify 要不要从"只查幻觉"扩成"也查深度/完整"(DeepPaperNote 7问)——与现设计(只查真伪)冲突,非默认。

## DeepPaperNote 细读(2026-06-16,逐个参考重读第①个)
DeepPaperNote 的 prompt 改动可拆**两条线**,共用同一个动作"下笔前先列 note_plan",但字段分属两线:
- **线一 防幻觉(主线,治张冠李戴)**:接地(grounding)=每条论断必须钉到原文坐标(section_id/页码),钉不到不让写;note_plan 里 `central_claims` 四分(声称/出处/证明了什么/没证明)+ evidence-first/raw-source authority/fail-closed。配套脚本 `lint_grounding.py`=**接地门**(写正文前先验出处真实存在且非泛指)。
- **线二 提质量(副线,治"prompt不够好",与幻觉无关)**:`final_quality_review` **深度7问**(证据链完整/关键数字在/机制↔结果对应/比强基线/讨论是机制性解释/证明vs没证明分开/复用要点具体) + 结构要求(创新点专节、机制流程3-4步、关键公式渲数学) + `final_readability_review` 反AI腔。7问是 lint(地板,只查格式语言)**之后**才跑的内容门。
- **交叉点**:7问的**第6问(证明vs没证明分开)**既是深度又顺手抗"过度声称"幻觉,两线非完全独立。
- **待拍板**:这次改造**只搬线一(防幻觉)**进 verify+summarize,还是**两线一起搬**?我倾向7问只进 summarize 当写作门、别塞 verify(免得 verify 从"查真伪"糊成"查一切")。用户 2026-06-16 说**先不搬,逐个参考过完再定**。

## claude-scholar 细读(2026-06-16,第②个参考;用户看好两点)
claude-scholar=Claude Code 大插件(MIT,~47 skill+35 command+6 agent+5 rule+hook),idea→发表全生命周期,纯 **agent-driven**(无确定性批处理层)。跟我们对口的只有内功,生态/调度/全生命周期不借。
- **★ Evidence-gated 契约(用户 2026-06-16 拍板:确实不错,要借)**——脊梁在 `skills/research-ideation/references/research-contract.md`。三结构+两闸,贯穿全系统:
  1. **Evidence Record**(每条证据:稳定唯一 ID `ER-日期-slug-NN` / Source type / Supports / Contradicts / Limitation / **Claim strength** 四档);
  2. **Claim Candidate**(每个待入正文的说法:挂哪条 Evidence ID / **Allowed wording** / **Forbidden stronger wording**(禁止夸到的程度,很独特,直治"全部任务大幅超越"式夸大) / Decision keep|weaken|revise|discard);
  3. **Source Trust Levels**(`full paper/preprint` 可撑 strong;`abstract-only/webpage` 只能"待读"路由,绝不撑硬结论——与我们 `quality_tier` 同思路,可打通);
  - **Claim Promotion Gate**(论断进 Knowledge/正文前过 5 项:有 Evidence ID?来源够硬?强度没偷偷抬?allowed/forbidden 都记?矛盾/缺失保留?任一不过→只能当假设,不许润色成结论) + **Strength Rules**(不点名证据不许升级强度)。
  - **可直接搬进我们 summarize/verify 的 3 条**:claim strength 四档 + allowed/forbidden wording + source trust 分级。与 DeepPaperNote **正交互补**:DPN 管"出处对不对"(接地),scholar 管"话说多满/谁说的"(强度措辞)。topic2 两类 major 各归一边(数字张冠李戴→DPN;夸大→scholar)。
- **★ planning-with-files(用户看好 agent-driven,这是支撑)**——`skills/planning-with-files/`,搬 Manus(被 Meta 20亿收购)context engineering。**3 文件模式**:`task_plan.md`(阶段+checkbox+Decisions+Errors+Status)/`notes.md`(证据发现)/`[deliverable].md`。治 agent 4 毛病:①文件当无限外部内存(上下文只留路径,压缩可逆);②**每决策前重读 task_plan 操纵注意力**(对治 ~50 工具调用后忘目标);③**保留失败痕迹**(Errors Encountered,别偷偷重试);④避免 few-shot 过拟合(引入变化抗漂移幻觉)。
- **调度结论(印证路 C)**:scholar 全 agent-driven——单篇长任务里 planning-with-files 让它不跑偏(好);但**批量层也 agent for 循环=脆点**(`/zotero-notes` 200篇必崩,无并发/幂等/续跑/记账)。路 C 正好各取所长:**批量层=确定性 Python(我们强项,不动)** + **单篇层=agent-driven(借 planning-with-files 3文件当单篇 skill 内部骨架)**。用户欣赏的 agent-driven 只在"单篇有界范围"里要,批量调度坚决不交 agent。

## 四个参考全过完 + 落地拍板(2026-06-16 本会话)
**★ 取用清单落到 `ref/TO-BORROW.md`**(新对话先读它,比本记忆更细;①②③④ 全填好 + 落地决定节)。要点:
- **③ ARS 借的是两个写作侧文件**(`academic-paper/references/` 下,不是 deep-research 13-agent 本体):**anti_leakage(知识隔离,治张冠李戴根,写时注入prompt,与Codex事前/事后互补)** + **writing_quality(反AI腔,自检清单,Codex不查文笔=纯增量,英文词表要本地化中文版)**。补充3条:vibe-citing命名/魔鬼代言人(我们Codex已是同philosophy)/灰区=FAIL启发 unverifiable 按论断类型分政策(存在性数字从严·解读从宽)。deep-research本体≈出口③不借。**"深读单篇"在①DeepPaperNote 不在ARS,别混。**
- **④ paper-qa**(RAG库≈出口②③,本体不借):A组现在能用=图表"就近文字≠本图"防误配(配Codex看图)/`I cannot answer`哨兵(印证unverifiable)/引文加引号;B组(闭集citation key+不许拼接+不许Author et al.手挥)留给出口②③ RAG问答。
- **★ 架构拍板=单 agent 模式(模式1)**:一个 agent 多步+确定性脚本(接地门)+外层Codex(写≠查)。**依据**:真正读/总结单篇的①②④全是单agent;唯一多agent的③ARS干的是"主题→整篇论文"大活。借的全部内容都装进单agent,不在单篇内拆小agent。用户量小(几十篇非几百)成本非约束。处理一篇的6步全流程见 TO-BORROW ★落地决定节。
- **下一步**:出正式落地方案(改 summarize_auto+写单篇skill+verify加unverifiable档+反AI腔词表中文化),再动代码。仍**未动任何生产代码**。

## 落地进度(2026-06-16 本会话,已动生产代码)
**summarize 侧已实现 + 端到端测过**(单 agent 模式,最小+):
- 新增 `pipeline/tools/grounding_gate.py`(接地门:pdftotext 抽全文,把 note_plan 每条 quote_en 与原文都归一化成连续字母数字串做子串匹配;退出码全过0/钉不住1;真引文 ok/编造 fail/太短 too_short)。
- `pipeline/config.json` 加 `summarize.grounding_gate`(默认 true;它是新流程唯一多烧 token 处=省token开关,但实测省不下多少→保持开,当调试逃生口)。
- `summarize_auto.py` 重写:`build_prompt` 五步(知识隔离铁律→读全文→列 note_plan→接地门必过循环→写总结[引文加引号+strength约束]→7问自查);`clean_output()` 砍模型在 YAML 前的寒暄;note_plan **持久化**到 `summary_dir/note_plan.json`(供 verify 复用);工具加 Write+Bash(python3:*);超时 900→1200。
- **决策**:门保持开;**反AI腔暂不加**(治文笔,机器读者优先级低);**7问保留**(用户要,因输出要喂别的 agent,深度重要);strength=逐条(observed/supported/strong),suspect 来源封顶 observed(把旧的来源级 quality_directive 接成逐条封顶)。
- **实测**(PPG Reloaded,生产没碰,写 /tmp/bakeoff):323s,36 条 note_plan 接地门全过;新总结 vs 旧:英文引文 39 vs 3、页/节锚点 71 vs 0,局限更批判;抓到旧总结一处疑似编的数(墙钟 20.4s,新从表2 锚出 31.2s)。下一步=多篇 bake-off 过 Codex 比 major 率。
- **补丁(2026-06-16,verify 测试暴露)**:新总结仍编了"本 PDF 不含附录"假话(实际有 Appendix A/B)→ 铁律加"反向"条(别断言没读到的内容不存在,没读到≠不存在)+ 读全文补"含附录/补充材料"。未重跑,下次 bake-off 一并验。

## verify 侧改造方案(2026-06-16 设计中,**未动代码**)
**逻辑**:接地门已包"引文存在性"→verify 收窄到机械门查不到的语义层,用 note_plan 当坐标定点核对(省 Codex 额度)。三层=①语义忠实(中文 point 忠不忠实它引的 quote_en,跨模型治同模型盲点)②图表/数字(自渲染看图表)③贴不贴(引文真但安错对象/设定=张冠李戴语义版)。
**确认要加(用户 2026-06-16 拍板)**:
- **张冠李戴语义核查**(③④):引文虽真但讲的是基线/别人工作被安到本篇、或 easy 设定数据被写成 hard——门只查在不在、不查谁说的/哪个设定,只能 Codex 读上下文判。**用户明确"要加,记录下来"。**
- **unverifiable 档**(②③④三处指向):把"原文明确矛盾=编造(major)"与"这轮没核到=存疑非错"分开。**不计入 major 率、不触发 correct**(否则误伤+白烧两边 token+无谓翻倍抽样)。分类政策:数字/存在性核不到从严·解读/机制核不到从宽。
- **图表防误配**(④):prompt 加"图旁文字可能属别图,别盲目照抄",配已有自渲染。
**要改的文件**:`verify_summaries.py`(vprompt 重写+读 note_plan 喂沙箱+老总结无 note_plan 优雅回退通读+write_report 加 unverifiable 节)、`correct_summaries.py`+`escalate_verify.py`(correction worklist 排除 unverifiable、major 率不计 unverifiable;worklist 具体构建处落地前确认)。
**仍待拍**:无锚论断要不要查(总结正文里 note_plan 没有对应锚的句子=可能没接地的私货,我倾向要);unverifiable 宽严政策最终确认。

**已实现(2026-06-16 本会话动了代码)**:上面四条全落地——`verify_summaries.py`(vprompt 重写:note_plan 块+三层检查+核不到≠编造+verdict/severity 加 unverifiable;worker 读 note_plan;write_report 加 ⚪ 未能核实节)、`correct_summaries.py`(过滤 unverifiable 不重写)、`escalate_verify.py`(unverifiable 不计 major 率)。无锚论断默认加了(minor 级)。py_compile + 结构 smoke 过。**真 Codex 端到端测过(2026-06-16)**:拿 PPG bake-off 新总结(带 note_plan)喂 verify_batch,114s 跑通、JSON 一次解析、verdict=major;揪出①价值正则方向写反(张冠李戴)②"PDF 无附录"假论断(独立核实 PDF 确有 Appendix A/B+图10-17,Codex 对总结错)③minor 过绝对。坐实"写≠查"——接地门 36 引文全过仍漏掉这俩,Codex 补上。
**运行节奏改变后的策略调整(2026-06-16,用户改"每晚两次×~10 篇,挑不占 token 时段",token 不再约束)**:
- verify 的 note_plan 从"定点核对、不必通读"改成"**辅助坐标 + 仍完整读全篇**"(去掉省 token 窄化;`verify.codex_self_render` 保留 true=最准非省 token)。
- `escalate_verify` correction 扩到 **非 pass 全修=major+minor+unverifiable**(用户二次确认 unverifiable 也重做;correct 加专门指令:重读原文补实出处,补不上软化/删去)。
- **默认全审**:verify 抽样 10%→**100%**(每次就 ~10 篇,不抽样)。

## 状态
**summarize 侧已落地+测过;verify 侧已出方案待落地。** 用户 2026-06-16 让把"四个参考的角色+调度模型"落到 **`ref/REFS-OVERVIEW.md`**(新对话从这份起读;早先的 `ref/PROMPT-NOTES.md` 已删)。
**本会话核实的调度模型结论**:这桌上只有我们"拿一堆论文做程序化批处理、出逐篇独立总结"——批量调度层(run.py/build_worklist/并发池)是我们独有的,**不借**;参考们的价值全在"单篇怎么写好"。DeepPaperNote=单篇 skill 无批量层;claude-scholar=agent 拿清单在上下文 for 循环(200 篇脆);ARS deep-research=收"一个问题"不收论文、并行的是角色;paper-qa=确定性建索引+agent 按问句检索、**不出逐篇总结**(是出口②③ RAG 的参照,不是 summarize 层)。
**用户 2026-06-16 拍板方向(未实现,详见 `ref/REFS-OVERVIEW.md` ★决策节)**:直接走**路 C**——批量层(run.py/并发池)仍确定性 Python,**单篇层换成 `claude -p` 跑一个我们写的 DeepPaperNote 式 skill**(plan→ground→写→自检+用工具);verify 的 Codex 跨模型关保留(写≠查)。配套节流:**每次发车上限 ~50 篇 + 每天发车一次**(C 单篇 agent 贵,一锅端会撞 Max 限流)。放弃路 B。
关联 [[cross-model-codex-panel]]、[[research-paper-pipeline]]。
