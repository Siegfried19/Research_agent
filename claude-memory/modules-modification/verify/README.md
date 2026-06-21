# verify — 跨模型核查（Codex 评审团）

> 定型设计。当前状态见 `STATE.md`。
> 代码：`pipeline/verify/{verify_summaries,escalate_verify}.py`；守护进程 `pipeline/tools/verify_daemon.py`；引擎 `pipeline/lib/codex.py`。

## 这个模块是什么
拿 **Codex**（第二个模型）核对 **claude** 写的中文总结里有没有幻觉，揪出会污染"这篇值不值得深入"判断的错；命中严重错误就**回 summarize 段整篇重做**，而不是在本模块打补丁。是 `run auto` 的 `verify` 阶段，也被 `verify_daemon` 全天候调用。

## 核心理念（不可动摇）
- **写的人 ≠ 查的人**：总结是 claude 写的，核查交给 Codex（不共享 claude 的幻觉盲点）。同模型自查（`VERIFY_BACKEND=claude` 应急档）强度更弱，结果写独立文件、绝不污染 codex 轨道。
- **Codex 永远没有否决权**：只提异议 / 出报告。本模块**report-only，绝不改总结**——`verify_summaries.py` 只写 `summary_verification.md` + `verified.json` + `verify_status.json`。
- **major → 整篇重做，不是打补丁**：major 触发 summarize 段的 `resummarize`（从 PDF 整篇重新总结出 vN+1），核查问题清单只当"避坑提示"喂进去，**无裁决权**（不许据清单反推原文、不许照搬旧版、不许伪造"已核对"背书）。这是为根治旧 `correct_summaries` 那个"反向裁决核查员 + 伪造核对背书"的致命 bug（见历史 SESSION-2026-06-17-summary-version-comparison）。
- **原文唯一来源 = PDF，整篇、无截断、无文本兜底**：总结本就只从 PDF 写，核查同源。Codex 自渲染——PDF 拷进隔离临时目录（`./paper.pdf`）+ `workspace-write`，它自己抽文本查数字、按需渲染页面看公式/图表。reasoning_effort = **medium**（claim 级语义核查，不用最贵档逐字渲染，省 ChatGPT 配额）。
- **精度让位 PDF**：总结故意不堆精确数字。所以"没给某精确值/只给量级或方向"不是错、不报；只有数字与原文矛盾、或被安到错误对象/设定才算错。

## severity 四态
- **major** → 触发重做：编造原文没有的事实 / 方向反转（谁好写成谁差、有效写成无效、梯度不等式方向写反）/ 张冠李戴（把基线或他人工作的结果安到本篇头上、把某设定的数字写成另一设定）/ 过度声称（observed 夸成全面大幅超越）。
- **minor** → 只进报告：孤立数字精度偏差（对象绑对、只是不够精确）、措辞略强。
- **unverifiable** → 只进报告（非错误）：这轮没核到（图表不清 / 某数字或存在性没读到）。self-render 下数字/存在性类没核到标此，解读/机制类没核到从宽不报。提示人工复看，**不触发重做**。
- **pass**。
- verdict 取全篇最严：有 major→major；否则有 minor→minor；否则有 unverifiable→unverifiable；都没→pass。

## 核查上限与配额熔断
- **每次硬上限 `--max-sources M`**：封顶本次核查总篇数（含 major 复核），主动停在 codex 一个配额窗口以内（此 ChatGPT 订阅一窗口 ~20 次重型核查、小时级重置）。`run.py` 的 `verify` 阶段默认 `--max-sources VERIFY_MAX_PER_RUN`（=**15**，定在 `run.py` 顶部常量）。超出的报为"待核"、留下次续（断点续核）。
- **篇序：最近总结的优先**（夜间先核当晚那批，旧积压留后）；取代随机抽样，配合上限确定性收口。
- **失败分类不靠关键词，交 LLM 判**（`lib/error_classify`，2026-06-20 重构）。一批失败 → 分类 → `classify_and_signal` 决定停轮还是逐篇跳过，并写信号文件 `logs/codex_quota.json` 给 daemon：
  - `quota_exhausted` → 写 until，daemon 睡到窗口恢复（解不出睡默认 ~2h）。
  - `transient` / `unknown` → daemon 递增短退避重试（15→30→60 分）。
  - `real_error`（未登录/配置错）→ 报警 + 跳过该主题（睡也没用，要人修）。
  - `bad_input` / `malformed_output`（坏 PDF、反复畸形输出）→ 不停轮，`record_skip` 把那几篇**钉版**写进 `verify_skip.json` 跳过（免每轮白核成配额黑洞；总结重做出新版会自动重新合格）。
- **熔断器**：一批里引擎调用失败累计到 `CIRCUIT_TRIP=4` 就跳过本批剩余（不白敲），余下次轮重试。进度按轮落盘到 `verified.json`，撞配额/熔断后重跑即续。

## 两个驱动 + 两个模式
- `verify_summaries.py <id> [pct] [并发] [--limit N]`：单批核查器（必核=suspect + 重做过的 v≥2 未复核，其余按 pct 抽；默认 pct=100=不抽样）。report-only。
- `escalate_verify.py <id> [...]`：驱动器，两个模式——
  - **capped**（传 `--max-sources`，= `run auto` 的 verify 阶段 / daemon 走这条）：不抽样、不翻倍；所有未核都合格、最近总结的优先；`--max-sources` 定本轮核几篇；跨轮只复核重做出的新版；`--start-pct` 被忽略。让总结一进库就已核。
  - **sampling**（手动/调试，不传 `--max-sources`）：抽 `--start-pct%`；fresh-sample major 率 ≥ `--threshold` 则下轮**抽样翻倍**扩面（"escalate"本名由来）。`pct`/`threshold` 仅此模式有意义。
  - 每篇重做次数本进程内封顶 `--max-attempts`（默认 2）；仍 major 标"需人工分诊"，不无限循环。建议性，exit code 恒 0。

## verify_daemon（全天候排空）
`tools/verify_daemon.py`：codex 平时闲着，就让核查整天啃积压。挑队列里待核最高优先主题 → 跑一批 `run.py <id> verify` → 撞配额按类睡到窗口恢复自动续 / 有进展接着吃满当前窗口 / 全清发 Telegram 自停。单例（pidfile），不随开机自启。起停见脚本头注释。
- **分工**：verify 已从夜间 cron 链摘出（2026-06-19）——夜间 cron 只 `sum + finalize`，verify 全天候交给 daemon，避免两者抢同一个 codex 配额窗口。

## 唯一跨段 import
`escalate_verify.py`：`from summarize.summarize_auto import resummarize`——major 时回总结段整篇重做。靠两段都有 `__init__.py` 才解析得到。总结/重做的**写法**是 summarize 模块的事，本模块只在"major 触发它"这个接口处对接。

## 坑
- `verify_status.json` 给检索层出口认（像 `quality_tier` 一样透传 verdict）；每轮只核一部分，合并写入、保留其余篇旧态——别整体覆盖。
- 报告/状态文件按 backend 分名：codex 轨道 = `summary_verification.md`/`verified.json`/`verify_status.json`/`verify_skip.json`；claude 应急轨道全部带 `_claude` 后缀，两轨道不互相污染。
- `summarized` 的篇必然曾有 PDF；核查时没 PDF = 异常（被删/移动）→ 归 `bad_input` 逐篇跳过，**绝不另找来源**去核一份本就从 PDF 写出来的总结。
- 换机器需重装 codex：`npm i -g @openai/codex` + `codex login`（ChatGPT 订阅，零 API 费）。
