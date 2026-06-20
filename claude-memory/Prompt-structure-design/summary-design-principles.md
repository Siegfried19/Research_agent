# 总结层设计原则(2026-06-17 草拟,2026-06-18 定稿并落地)

> 状态:**已定稿 + 已改代码**(2026-06-18,用户拍板)。落地详情见 **§八**;§一~§七是定稿前的推导/证据/未决,保留作背景。
> v1 已折入 deep-research 证据(`claude-memory/modules-modification/summarize/STATE.md`,含可抄项目清单)。
> 一句话校准:大方向(分诊层/语义忠实/便宜核查)被外部强力支持;**唯"数字不必守"收一格 → "数字精度让位 PDF,但 claim 级语义核查仍顺带守住要命的数字错(misattribution/矛盾)"。**
> 缘起:清库用新 prompt 重跑后,发现新总结(尤其修正版 v2/v3)质量问题;深挖后重新对齐初衷,得出下面的取向转变。
> 配套:逐篇对照证据 `claude-memory/modules-modification/verify/STATE.md`;codex 问题 `claude-memory/modules-modification/verify/STATE.md`。

## 一、重新对齐的初衷:总结是什么、不是什么
这个库的消费者是:① 用户本人读来判断方法值不值得深入;② **别的 agent 卡在某问题/症状时来查"别人用什么方法解的"**;③ ARS idea→论文(要引用量化结果时回读 PDF)。
**没有一种消费者真正需要总结提供"精确数字"。** 而 **PDF 是唯一原文、始终在盘上**,任何精确值随时可取。

→ **定位:总结 = 方法/直觉的「分诊层」,不是「权威数字库」。**
**两段式工作流(核心心智模型):**
1. 读**总结**判断"这方法是什么、值不值得我花时间"(triage/选择)。
2. 觉得值得 → 才去 **PDF** 看精确细节(实现/超参/确切数字/引用)。

## 二、核心判断:什么重要、什么不重要
**唯一 PDF 兜不住、因而总结必须守的事:帮消费者正确决定"要不要深入"。** 别的都能被"去读 PDF"兜住。

由此,总结里的"错"分两类,价值天差地别:
- **🔴 会污染"值不值得"判断的错(必须守)**:结论说反、A 比 B 写成 B 比 A、方法描述反了、能力吹大(AIRS 型)、相关性吹大/缩小。
  - 其中**假阴性最毒**:总结把一个相关方法说得没用 → 消费者根本不会去开 PDF,没有兜底。
  - 这类错**便宜**:读懂论文在讲什么就能判,**不需要逐字对 PDF 数字**。
- **🟡 精确数字偏差(分两种,deep-research 校准过)**:
  - **孤立的数字精度**(系数 10⁻⁵ vs 10⁻³、成功率几个百分点,且绑定对象正确)→ 基本无害,要精确值去 PDF。⚠️ 但**不主张"总结里放过/删掉数字"**:文献(FActScore/CS-PaperSum)把数字当原子事实保留——**保留数字,只是其精度权威在 PDF,总结不装精确**。
  - **数字张冠李戴/与原文矛盾**(±528 安到 Walker2d 实为 HalfCheetah)→ **这其实是 claim 级语义错,不是单纯数字错**,会污染判断,**该抓**;好消息是 claim 级语义核查(下文)会**顺带抓住它**,无需逐字数字审计。
  - 实证:今天 4 个 major,3 个是数字类——其中 GAE/Reward-Adaptive 的本质是 misattribution(语义错,该抓),Learning-to-Walk 的符号是孤立精度(可让位 PDF);AIRS 是方向反转(最该抓)。**结论不变:逐字核数字的重型机器该退役,但抓"数字绑错对象"的语义核查要留。**

## 三、反直觉但关键的一条:克制"自信的精确数字"
一份说"对冲击力加个小惩罚(系数见 PDF)"的总结,**优于**斩钉截铁写"10⁻³"的——后者把 tier-2 细节伪装成 tier-1 结论,**引诱消费者直接信用、不去 PDF 核**。
→ 新 prompt"每句挂具体数字锚点"的本能方向是反的:它在制造一堆求着被信任的自信细节,而设计本意要把这些**推迟到 PDF**。**具体数字应"克制 + 显式指向 PDF",不装权威。**

## 四、由此推出的设计取向(待 deep-research 验证)
**A. 总结该写什么**:方法 + 直觉("为什么 work")+ 解决什么问题 + **什么时候管用/不管用** + 诚实局限 + 结果的**方向**(beat/不beat、稳/不稳)。回到"老总结"那种讲解气质。
**B. 总结不该做什么**:不堆具体数字锚点;具体数值一律"指示性 + 让位 PDF";不为可核查性牺牲可读性。
**C. 核查该怎么做(已定要核,走便宜语义版 — deep-research 落地了具体范式)**:
  - **claim 级、非整体二元**(FActScore):把总结拆成原子方法论断,逐条判"原文撑不撑得起"。
  - **便宜模型代替 codex**(解额度):MiniCheck(770M,~400x 便宜于 GPT-4 却达其水平)/SummaC/AlignScore 这类**逐句对证据 entailment** 的轻量核查;或便宜 LLM-judge。**这层顺带抓住 over-claim 和 misattribution(含数字张冠李戴)**。
  - **方向反转另配一道**:NLI 类工具不擅长"结论说反",需额外一个**专门判方向反转的 LLM-judge 提示**。
  - **输出 report-only 三分类**(PaperTrail:Supported / Unsupported / Omitted),**不自动重写**。
**D. 退役/根治什么**:① codex 逐字渲染 PDF 核数字的重型机器 → 退役(解额度烧穿);② **会反向裁决 codex + 伪造"已核对"背书的自动修正环节 → 取消**(改成只出三分类报告,人或单独一步按报告改,修正环节无裁决权)——根治那个致命 bug。

## 五、deep-research 已回(wtmd392c3,结论见 `claude-memory/modules-modification/summarize/STATE.md`)
可抄清单:**PaperQA2**(`{summary,relevance_score}` 逐块上下文摘要)、**PaperTrail**(claim 级离线 JSON KB + Supported/Unsupported/Omitted)、**FActScore**(原子事实核查)、**MiniCheck/SummaC/AlignScore**(便宜语义核查,替 codex)、**CS-PaperSum/Dagdelen**(结构化字段)、**Paper2Agent**(方法→MCP,远期出口③)。
校准:大方向获强力支持;"数字不必守"收为"数字精度让位 PDF,但 claim 级语义核查顺带守 misattribution"(已折入 §二/§四)。3 条被对抗否决的别过度引用(详见研究 doc §二)。

## 六、决策(用户 2026-06-17)
- ✅ **核查保留**——但走**便宜的语义/方向版**(claude 级 LLM-as-judge 守方向性错),不是全退役;codex 逐字核数字的重型机器降级/退出。
- ✅ **旧的 221 篇老总结:先全部不动**(完整备份在 `logs/wipe-summaries-20260617/`,intuition 更好,留作基线/候选)。
- 🔄 **今天重跑的 ~40 篇新总结:可能整个去掉、按新原则重做再评估**(用户"可能又要把现在的去掉重新看看";尚未执行,等新 prompt/核查定型)。

## 七、仍未决(等用户拍)
- 两段式(note_plan→写)保留还是回到"边读边写"(影响"数字从语境剥离"的张冠李戴风险)。
- 语义核查具体怎么落:用 claude 自查(同模型盲点) vs 仍用 codex 但只判方向(省额度)。
- v2 危险中间态如何不外泄(若保留任何修正环节)。
- 新原则定型后,是"去掉今天 40 篇重做",还是"直接拿老 221 篇当基线、只补未总结的"。

## 八、定稿 + 已落地(用户 2026-06-18 拍板,本次已改代码)
讨论后定下并**已实现**(改了 `lib/codex.py`/`config.json`/`verify_summaries.py`/`summarize_auto.py`/`escalate_verify.py`,删了 `correct_summaries.py`):

1. **核查引擎 = Codex 中等强度**(不走便宜小模型 MiniCheck/SummaC——用户:"不要太便宜的")。
   - `config.json` verify 段 `reasoning_effort: "medium"`;`run_codex(effort=)` 落到 `-c model_reasoning_effort=medium`。
   - **永远 self-render**:整篇 PDF 给 Codex(隔离沙箱+paper.pdf+workspace-write,自抽文本+渲染图表)。
   - **删掉省钱文本路径 + 40 万字符截断**(§五"数字不必守"那条收口的延伸):总结本就只从 PDF 写(2026-06-16 移除 store/text),核查同源即可,文本兜底是历史遗留。claude 应急后端改用 Read 工具直读 PDF。**结果:unverifiable 的"被截断"成因消失**,只剩"图表没看清/某段没读到"。

2. **修正环节取消裁决权 = 不再打补丁,改"整篇重新总结"**(§四D 那个致命 bug 的根治)。
   - 旧 `correct_summaries.py`(在旧版总结上按问题清单改、"其余原样保留")**已删**——它正是"反向裁决核查员+伪造'已核对'背书"的来源。
   - 新 `summarize_auto.resummarize`:major 触发 → **从 PDF 整篇重写**出 vN+1,复用 build_prompt 全套(note_plan+接地门+7问自查);核查问题只当**避坑提示**喂进去,prompt 明令**不许据清单反推原文、不许照搬旧版、不许写"已核对"背书**(`_resummary_block`)。改完下轮必复核,2 次仍 major 转人工分诊。
   - 逻辑(用户):"既然要重新总结,裁决就不要了;报修改了就重新总结"——所以没有独立"修正"步,修正=重做。

3. **severity 四态**(`major`/`minor`/`unverifiable`/`pass`):**只有 major 触发重做**;minor(孤立数字精度/措辞略强,精度让位 PDF)+ unverifiable(没核到、非错误)**只进报告**。

4. **核查输出粒度 = 做法 B(整篇 verdict + issues 清单)**,不引入 claim 级三分类。
   - **做法 A(PaperTrail/FActScore 式 claim 级 Supported/Unsupported/Omitted 逐条判)保留备查**(用户要求):它颗粒度细、对下游 agent 提取友好、Omitted 还覆盖"漏没漏",但**当前核查唯一目的是决定"要不要重做",B 已够**,A 更贵更重、Omitted 主观,服务的是出口③(claim 级知识库)而非核查环节。将来真做 claim 级知识库再上 A。

> 仍按 §六:老 221 篇先不动(备份 `logs/wipe-summaries-20260617/`);"去掉 40 篇重做 vs 拿老 221 当基线"待用户定。本次只改机制,未重跑任何总结。

### 八续(2026-06-18)：summarize/verify 两个 prompt 的重写方案
机制改完后,进一步定了**总结生成 + 核查 prompt 本身怎么改**(上面 §三/§四A-B 的取向落到具体 prompt 文字)。核心:**去掉 note_plan + 接地门、总结回到"边读边写"**(note_plan 实测制造"无锚论断"假阳性洪水→版本通胀,且接地门只验引文在不在、防不住张冠李戴——危害>收益);数字让位 PDF;论断原子化+内联 strength;加"适用边界"段;codex 端告知数字立场防误报+加方向反转检查。**完整 prompt 文字 + 去 note_plan 的证据 → `claude-memory/Prompt-structure-design/summary-prompt-rewrite-plan.md`。** 尚未落代码,先出样例对比再定。
