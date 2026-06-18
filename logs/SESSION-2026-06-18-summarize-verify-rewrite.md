# SESSION 2026-06-18 — summarize/verify 层重构 + 总结/核查 prompt 重写

> 缘起:换机器后继续 2026-06-17 搁置的"总结层设计转向"。先落结构性重构,再重写两个 prompt。
> 上游原则:`docs/summary-design-principles.md`(§八 + 八续定稿);prompt 细节:`docs/summary-prompt-rewrite-plan.md`。
> ⚠️ **本会话只改代码/文档,未提交、未重跑任何生产总结。** 老 221 篇原封不动(备份 `logs/wipe-summaries-20260617/`)。

## 一、做了什么(按先后)

### 1. 结构性重构(机制层,先做)
- **核查引擎**:codex `reasoning_effort=medium`(`lib/codex.py` 加 `effort` 参→`-c model_reasoning_effort=`;`config.json` verify 段加 `reasoning_effort:"medium"`)、永远 self-render 读整篇 PDF;**删省钱文本路径 + 40 万截断**;claude 应急后端改用 Read 直读 PDF。
- **修正→重做**:删 `correct_summaries.py`(打补丁式,反向裁决+伪造背书 bug 的来源);新增 `summarize_auto.resummarize`——major 触发→从 PDF **整篇重写** vN+1,问题清单只当避坑提示、**无裁决权**(`_resummary_block`)。
- **severity 四态**:只有 **major** 触发重做;minor/unverifiable 仅进报告(`escalate_verify` 收窄;原来是"非 pass 全重写"→版本通胀)。
- 用户拍板:codex"中等"=reasoning_effort medium;"取消自动修正"=取消裁决权而非取消修正,且因"反正要重做"直接退化成整篇重做、无独立打补丁步。

### 2. 去掉 note_plan + 接地门,总结回到"边读边写"(prompt 层)
- 删 `pipeline/tools/grounding_gate.py`、`config.json` 的整个 `summarize` 段、`summarize_auto` 里 `GATE_ON`/`_gate_block`/note_plan 脚手架。
- **去掉理由(查史坐实,写进 plan 文档 §四)**:note_plan 实测制造"无锚论断"假阳性洪水(`redo-batch2` 报告成片"原文其实支持"的假 minor)→旧"非 pass 全重写"放大成版本通胀;接地门只验"引文在不在"、防不住张冠李戴(真危险);两段式"剥离数字成锚点"本身是张冠李戴诱因。**且老总结时代严格"编造引文"本就几乎没发生**(老总结几乎不引文;接地门唯一真跑那次 36 条全过、0 抓到,真幻觉是 codex 抓的)——它防的威胁没真发生,真问题它接不住。

### 3. 重写两个 prompt(`docs/summary-prompt-rewrite-plan.md` 是完整文字源)
- **summarize `build_prompt`**:4 步→3 步(通读→边读边写→7问自查);开头加"给谁看(agent 首要)+判断轴(正确性>可提取性>文笔)";**数字让位 PDF**;论断**原子句+内联 strength**;模板加**适用边界**一等段落 + "主要结果(写方向不堆精确数字)" + "用什么方法(含直觉)";7 问重排到方向/直觉/防张冠李戴/可提取。tools 收成 `["Read"]`。
- **codex verify `vprompt`**:加"总结数字立场"告知(没给精确数字不报,防误报)+ **方向反转专项检查** + severity 让孤立数字精度从宽;删 note_plan 坐标块(plan_block/anchor_task)。

### 4. 样例验证(SAC,arxiv:1801.01290)
- 用新 prompt 实跑一版到 `/tmp/sac_new_prompt.md`(临时,没碰生产);**119s**(note_plan 时代 ~300s+,快一半)。
- 对照现有 v1(2026-06-17,note_plan 引文密集风格):新版在**可提取性(内联 strength)、方向准确、适用边界段、直觉、批判性**上明显更优;**唯一偏差**:"数字克制"只做了一半——仍逐字转写全部公式+Table1 超参(但都挂了出处、没当结论卖点)。对 agent 无害,偏密。
- 用户结论:**目前问题不大,后面有问题再改**。

## 二、改动文件清单(未提交)
- 改:`pipeline/lib/codex.py`、`pipeline/config.json`、`pipeline/summarize/summarize_auto.py`、`pipeline/verify/verify_summaries.py`、`pipeline/verify/escalate_verify.py`、`CLAUDE.md`、`pipeline/ARCHITECTURE.md`、`docs/summary-design-principles.md`。
- 删:`pipeline/verify/correct_summaries.py`、`pipeline/tools/grounding_gate.py`。
- 新增:`docs/summary-prompt-rewrite-plan.md`、本 SESSION 日志。
- 冒烟:py_compile / config 解析 / 三脚本加载 / build_prompt 两版渲染(无 note_plan 残留、含适用边界) / vprompt 两后端渲染(含方向反转+数字立场) 全过。

## 三、下一步(待定)
1. **提交**:本会话改动尚未 commit(用户说先 log,没说提交)。
2. **数字克制要不要更狠**:想更精简就把"公式只述结构不逐字转写"写进 prompt 再跑(选项 b);否则保持。
3. **怎么处理存量总结**:新 prompt 定型后,"去掉今天 40 篇重做" vs "拿老 221 篇当基线只补未总结"——未定。
4. 还没用新 codex(中等 self-render)实跑核查过一篇新总结。
5. (独立)note_plan claim-JSON 对 agent 公开(改 ask.py --json)——本轮明确不做,留作检索层增强。
