# SESSION 2026-06-16 — summarize+verify 改造**落地**(接上 refstudy 收尾)

> 上一会话出了方案(`ref/TO-BORROW.md` ★落地决定),本会话**动生产代码实现 summarize 侧 + verify 侧**。
> 架构=单 agent 模式:确定性 Python 批量层不动,单篇层一个 `claude -p` 多步(读→note_plan→接地门→写→自检),外层 Codex 跨模型核查(写≠查)。

## summarize 侧(已实现 + 端到端测过)
- **新增 `pipeline/tools/grounding_gate.py`(接地门)**:对 PDF 跑 pdftotext,把 note_plan 每条 `quote_en` 与原文都归一化成"连续字母数字串"(抹空白/连字符/标点/断词换行)做子串匹配;`ok`/`partial`(前后半段中)/`fail`/`too_short`;退出码全过 0、钉不住 1、读不动 2。零 token、确定性。
- **`pipeline/config.json`** 加 `summarize.grounding_gate`(默认 true)。它是新流程唯一多烧 token 处=省 token 开关,但实测省不下多少 → **保持开**,当调试逃生口。
- **`pipeline/stages/summarize_auto.py` 重写 prompt**:`build_prompt` 五步——①知识隔离铁律(事实只来自本 PDF,没写标 `[原文未提]`,写作能力照常)②读全文 ③用 Write 列 `note_plan.json`(每条 kind/point/quote_en/where/strength)④接地门必过循环(Bash 跑门脚本,钉不住改 note_plan 重跑,≤2 轮)⑤写总结(引文加引号、措辞不超 strength)⑥7问自查。`clean_output()` 砍模型在 YAML 前的寒暄。note_plan **持久化**到 `summary_dir/note_plan.json`(供 verify 复用)。工具加 `Write`+`Bash(python3:*)`;超时 900→1200。`quality_directive` suspect 分支加"strength 封顶 observed"。
- **决策**:门保持开;**反 AI 腔暂不加**(治文笔、机器读者优先级低);**7 问保留**(用户要——输出要喂别的 agent,深度重要);strength 逐条(observed/supported/strong),method 类不填。
- **实测**(PPG Reloaded,生产没碰,写 `/tmp/bakeoff/`):323s;36 条 note_plan 接地门全过;新总结 vs 旧——英文引文 39 vs 3、页/节锚点 71 vs 0,局限更批判;抓到旧总结一处疑似编的数(墙钟 20.4s,新从表2 锚出 31.2s)。**下一步=多篇 bake-off 过 Codex 比 major 率。**

## verify 侧(已实现,**未跑真 Codex**——省额度,留给 bake-off)
逻辑:接地门已包"引文存在性"→Codex 收窄到机械门查不到的语义层,用 note_plan 当坐标定点核对省额度。
- **`pipeline/stages/verify_summaries.py`**:`vprompt` 重写——加 note_plan 坐标块(有则定点核对+查无锚论断,老总结无则优雅回退通读)、三层检查(语义忠实 / **张冠李戴**=引文真但安错对象或设定 / 数字+图表防误配=就近文字≠本图)、**核不到≠编造**两分(明确矛盾→major;没核到的数字/存在性类→`unverifiable` 提示人看、解读类→从宽不报)。verdict/severity 枚举加 `unverifiable`。worker 从 `summary_dir/note_plan.json` 读 note_plan 喂两种模式。`write_report` 加"⚪ 未能核实 unverifiable"独立节。
- **`pipeline/stages/correct_summaries.py`**:`run_corrections` 过滤掉 `severity=unverifiable` 的 issue,全是 unverifiable 的篇直接跳过(没东西可改,改了反而可能弄错)。
- **`pipeline/stages/escalate_verify.py`**:round 日志加 unverifiable 计数。`majors`/`fresh_major_pct` 本就只认 `verdict=="major"`,unverifiable **不触发修正、不计入 major 率**(不会无谓翻倍抽样、烧 Codex 额度)。
- **仍待拍/待验**:无锚论断的 minor 归类是否合适(本会话默认加了);单篇真 Codex 跑一次坐实 JSON 可解析 + note_plan 定点是否真省 token。

## 改动文件清单
- 新增:`pipeline/tools/grounding_gate.py`、`logs/SESSION-2026-06-16-summarize-verify-IMPL.md`(本文件)。
- 改:`pipeline/config.json`、`pipeline/stages/summarize_auto.py`、`pipeline/stages/verify_summaries.py`、`pipeline/stages/correct_summaries.py`、`pipeline/stages/escalate_verify.py`。
- 全部 `py_compile` 通过 + prompt 结构 smoke test 通过;summarize 端到端在 /tmp 实跑通过。生产 DB/总结未碰。

## 运行节奏改变后的策略调整(2026-06-16,用户改"每晚两次×~10 篇,挑不占 token 时段")
token 不再是约束 → 把省 token、换最大质量:
- **去掉 Codex 省 token 的窄化**:verify 的 note_plan 从"定点核对、不必通读全篇"改成"**辅助坐标 + 仍完整读全篇**"(note_plan 继续供张冠李戴/无锚论断对照)。`verify.codex_self_render` **保留 true**(它是最费最准的,不是省 token 项)。
- **"有问题的都重新来"**:`escalate_verify` 的 correction 从"只修 major"扩到 **非 pass 全修=major+minor+unverifiable**(修完下轮自动复核,2 次仍不过转人工)。
- **`unverifiable` 也重做**(用户二次确认):correct 不再过滤它;`cprompt` 加专门指令——重读原文补实出处,补不上就软化/删去,别留无依据断言。
- **默认全审**:`verify_summaries`/`escalate_verify` 的抽样默认 10%→**100%**(每次就 ~10 篇,不抽样;run.py 本就传 --start-pct 100)。
- 改的文件:`verify_summaries.py`(plan_block 措辞+默认100+docstring)、`escalate_verify.py`(problems=非pass全部+默认100+docstring+stubborn 文案)、`correct_summaries.py`(不再过滤 unverifiable + cprompt 加 unverifiable 处理指令)。py_compile + 逻辑 smoke 通过。

## 真 Codex 端到端测试(2026-06-16,verify 侧坐实)
拿 summarize 侧 bake-off 出的 PPG Reloaded 新总结(自带 note_plan.json)直接喂 `verify_batch`(生产 DB 没碰):
- **跑通**:114s,USE_SELF_RENDER=true、note_plan 加载成功、隔离沙箱拷 PDF、Codex 自渲染读全篇、**JSON 一次解析成功** verdict=major + 3 issues。新 prompt 的 schema/流程全 OK。
- **新检查真的开火**:
  1. 🔴 张冠李戴/反向错误——总结写"频繁蒸馏下需要更强的价值正则",Codex 揪出原文说的是 **infrequent** distillation(T_freq=32)才需更强价值正则,方向写反了。
  2. 🔴 假的元论断——总结称"本 PDF 不含附录图表";Codex 读 PDF 后指出含 Appendix A/B + 图9–38。**独立用 pdfinfo/pdftotext 核实:PDF 确有 Appendix A/B、Figure 10–17**——Codex 对、总结错。
  3. 🟠 minor——"每次只动一个、固定其余"表述过绝对(图3 实为联动改 T_freq 与 β_π)。
- **坐实"写≠查"价值**:接地门已让 36 条引文全过,但 Codex 仍揪出一个**绝对查不到的幻觉**(关于"附录不存在"的论断不是引文,门结构上管不到)→ 证明事后跨模型核查不可省。
- **顺带的 summarize 侧发现(待跟进)**:新总结尽管接地,仍编了"PDF 无附录"的假话——疑似没读到附录页就断言其不存在。summarize 的"读全文"指令可能要再强调"别对没读到的部分断言其不存在"(正好是 unverifiable 思路的撰写侧版本)。

## summarize 侧补丁(2026-06-16,由上面测试直接暴露)
测试揪出新总结编了"本 PDF 不含附录图表"的假话(实际有 Appendix A/B)→ 给 `summarize_auto.py` 的 prompt 加两处:
- **铁律加"反向"一条**:不要断言原文"没有/未包含/未给出"某内容——**没读到≠不存在**(附录/补充材料/大表常在后几页),拿不准就别下"缺失"判断、回去读完后面的页。这是 unverifiable 思路的撰写侧版本(撰写者也不该对没核到的东西下绝对断言)。
- **第一步·读全文**补"**含正文之后的附录/补充材料/大表**"。
py_compile + 结构 smoke 过(戒律在、读全文含附录)。**未重跑端到端**(下次 bake-off 一并验)。

## 下一步
1. **多篇 bake-off**:挑 ~10 篇(含 suspect、含旧流程被揪过 major 的),新 prompt 各写一遍 → 过新 verify 比 major 率 + 文笔;**顺带验证"附录假话"补丁是否生效**。
2. bake-off 数据 OK → 决定是否放量重跑两主题总结。

## 本会话改动文件总清单(summarize + verify 两侧落地 + 测试 + 补丁)
- **新增**:`pipeline/tools/grounding_gate.py`、`logs/SESSION-2026-06-16-summarize-verify-IMPL.md`。
- **改**:`pipeline/config.json`(summarize.grounding_gate)、`pipeline/stages/summarize_auto.py`(五步 prompt+clean_output+note_plan+铁律反向条+读附录)、`pipeline/stages/verify_summaries.py`(vprompt 重写+note_plan+unverifiable+默认100%)、`pipeline/stages/correct_summaries.py`(不过滤 unverifiable+cprompt unverifiable 指令)、`pipeline/stages/escalate_verify.py`(非pass全修+默认100%+docstring)。
- **验证**:全部 py_compile;grounding_gate 单测(真/编造/太短);summarize 端到端真跑(PPG,323s,新总结锚点 39引文/71锚 vs 旧 3/0);verify 端到端真 Codex(PPG,114s,verdict=major,JSON 一次解析,揪方向反+附录假话)。生产 DB/总结全程未碰(测试写 /tmp/bakeoff)。
