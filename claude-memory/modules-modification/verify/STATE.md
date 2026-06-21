# verify — STATE（层积日志）

> 写法：**新在上、老在下、不删**，每条标题带日期+时间戳。最顶一条 = 此刻状态/卡在哪；往下翻 = 历史。
> README.md 是定型设计（覆盖更新）；这里是带细节的过程账。
> 局部改动记这里；跨模块/全局改动记 `../../../claude_log.md`，这里只留一行指针。

## 2026-06-21 14:40 EDT · tnnls 卡死篇回滚 v1 重核 + 揪出"14 篇 major 悄悄标已核"系统问题
- 用户令：把审查卡死的 `10.1109/tnnls.2026.3688045`(Input-to-State Safety)**回滚到 v1、清掉后续审查状态**=恢复成"刚总结完待核"。已做：DB 删 v2/v3/v4(留 v1)、磁盘删 v2-v4.md、`verified/verify_status/verify_skip.json` 三档移除本篇。备份在 `logs/temporary-log/tnnls-reset-20260621-1440/`(含库快照+三档+被删 md)。现该篇=v1 summarized、零核查记录 → daemon 起来会当待核重新核。
- **顺带揪出系统问题(重要)**:rl-general-toolbox 84 篇"已核到最新版"里 ≈37 pass/33 minor/**14 major 未解决**。根因——`escalate` 里 `record_verified(ok)` 在 quota 中止判断**之前**执行:一批"核出 major + 同批撞配额"时,major 篇被标已核 v1,但其后的 `resummarize` 重做被 `break` 跳过 → 下轮 daemon 见"已核到当前版本"认为完事、永不重做。这 14 篇里仅 tnnls 进过 verify_skip,**其余 13 篇是悄悄挂 major 没人管**(attempts=0、未触发重做,非"重做仍顽固")。
- 13 篇清单见 claude_log(本日条)。待用户定怎么处理(候选:清 verified.json 让其重核 / 同 tnnls 回滚)。**修向建议(未做)**:`record_verified` 应只记 pass/minor,或 major 篇即便中止也不写 verified、留作待核——否则中止永远漏掉同批 major 的重做。

## 2026-06-21 14:37 EDT · daemon 被旧配额信号长睡 → 重启唤醒(配额已恢复)
- 现象：用户问"codex 自动验证不是关了吗"。查实——daemon 进程活着(旧 pid 2422420),但**在空睡到 06-24 22:06(~90h)**：之前几批 codex 全 `quota_exhausted`,error_classify 解析出的"重试时刻"是 06-24,daemon 据此长睡,所以看着像"关了"。
- 实测 `codex exec "Reply OK"` → exit 0、返回 OK(烧 22.6k tokens),**配额其实早恢复了**,只是 daemon 不知道、要睡到 06-24 才会重试。
- 处置：`kill` 旧 daemon + 删 `logs/verify_daemon.stop`/`logs/codex_quota.json` + 重起新 daemon(pid 3827926)。新进程立刻重探积压(rl-general-toolbox 待核 16),跑出真判决(`MAJOR Self-supervised network distillation`...) → 自动验证恢复正常。无代码改动。
- 留意：这是 daemon 已知行为的副作用——一旦 codex 报个远期重试时刻,daemon 会照睡到那天,期间配额提前恢复也不会自醒。**配额恢复后想立刻续核 = 重启 daemon**(touch stop 只停不续)。是否要给 daemon 加"定期轻探活、提前醒"逻辑,待议。

## 2026-06-21 03:24 EDT · 指针：修好导致 verify 全断的 summary_versions.path stale（详见 claude_log）
- 改名(storage/papers→storage/sources)漏更新 `summary_versions.path`,致 `verify_summaries.py:237` 开文件全失败、**每篇报 "summary file missing"、verify 实际一篇都核不了**。已 `UPDATE ... REPLACE` 修正生产库 128 行(文件本就在新位置,纯路径修正),复核 verify 取数 0 missing。详见 `../../../claude_log.md`(03:24 条)。

## 2026-06-21 02:23 EDT · daemon 配额默认睡眠 2h→4h
- `verify_daemon.py` `QUOTA_DEFAULT_MIN` 120→240 分。**仅影响"撞配额但解析不出恢复时刻"那条兜底路径**（能解析出 "try again at X" 的照旧睡到那个点，不受影响）。
- 缘由：用户提的——codex 额度窗口实测 ~5.5h，2h 默认常太早醒、一醒又撞墙白跑一批；4h 更贴近真实恢复。仍可用环境变量 `VERIFY_QUOTA_DEFAULT_MIN` 覆盖，不必改码。
- 同会话顺带确认（无改动）：早 9:00 cron 即便 daemon 已在跑也不会重复——`acquire_singleton()` 见活 pidfile 直接拒启自退。

## 2026-06-20 04:19 EDT · 指针：新增按版本核查详情 verify.json（跨模块，详见 claude_log）
- 新能力：核完每篇把 codex 详情**按版本累积**写 `store/papers/<slug>/verify.json`（`record_verify_detail`，verify_summaries + escalate_verify 都接）。**状态文件 verified/verify_status/verify_skip 与 daemon 不变**——状态在 `topics/<id>/` 喂 daemon，详情在论文文件夹，彻底分家。全局账见 `../../../claude_log.md`（04:19 条）。

## 2026-06-20 02:16 EDT · 重构首条（当前状态快照）

> 文档模块化重构建立本日志。以下为当日现状；以后变化在本条**之上**叠新条。

### 现在能跑的
- 核查链 capped 模式（`escalate_verify --max-papers`）端到端可用：report-only + Codex medium self-render claim 级核查 + major 触发整篇 `resummarize` + 断点续核。
- **verify_daemon 全天候在跑**：codex 闲就啃积压，撞配额睡到窗口恢复自动续。verify 已从夜间 cron 摘出（2026-06-19），cron 只 `sum+finalize`，避免与 daemon 抢配额。
- **LLM 失败分类器已上线并实测跑通**（2026-06-20，`lib/error_classify`）：取代旧的关键词猜测；2026-06-20 凌晨一次真·额度耗尽事件中正确判 `quota_exhausted` 并长睡到窗口恢复，端到端验证过。
- 配额现实：此 ChatGPT 订阅一个窗口约 **20 次**重型核查、小时级重置。`VERIFY_MAX_PER_RUN=15`（run.py 顶部常量），留 margin。

### 已知 bug / 未决（待补）
- **重做次数跨 daemon 批次不封顶**（2026-06-20 暴露）：`escalate --max-attempts 2` 是单个 `run.py verify` 进程内计数，daemon 反复调 → 每次清零 → 没有全局刹车。病例 `10.1109/tnnls.2026.3688045`（Input-to-State Safety for RL）被 churn 到 v5。**拟修：跨运行重做总闸**（≥3 次仍 major → 标人工）。未做。
- **codex 反复崩的篇没封顶**：上述病例 v5 起 codex 核查反复 `exec exit 1`（疑被超长/乱码噎住），会被无限重试/重做。用户已拍板：**codex 连崩后要上标记**（具体后议）。**拟修：verify 连崩 N 次 → 标人工**。未做。
- 上述病例当前已人工处置：删损坏 v5 回退 v4、`record_skip` 钉版 v4 标"【待用户手动修改】"，daemon 不再碰；审阅副本在 `review/Input_to_State_Safety_for_RL/`（含 PDF 副本，本地审阅，勿提交/外发）。系统性补丁仍欠。

### 上次卡在哪 / 注意
- **库刚被清空重做中**（2026-06-19 02:06，用户要用新流程重写全部总结）：`summary_versions` 清零、221 篇全回 `pdf_downloaded`、verified*/verify_status*/verify_skip* 标记全删、索引删。`quality_tier/quality_signals` 保留。
- 因此当前**待核积压随夜间 sum 重建在动态变化**，不是稳定数字；daemon 起来后会逐步啃。库重新长出总结后无需手动干预，daemon 自然跟上。
- `VERIFY_BACKEND=claude` 应急档存在但默认不用（同模型自查，强度弱）；写独立 `_claude` 文件，仅 codex 配额枯竭时应急。
- 代码近期改动（LLM 分类器等）多为**未提交**状态（用户负责 push）。

---

## 2026-06-17 · 新旧总结 prompt 逐篇对照（16 篇三版齐全）→ 揪出修正环节致命失效

> 缘起：用户读了新老总结，觉得"新 v1 不如老的、错误挺多、老的 intuition 更好"。
> 目标校准：知识库总结**是给别的 agent 来查事实答案用的** → 评判轴 = 正确性 > 可提取性 > 可读性（文笔次要）。
> 方法：6 个子 agent 并行，每篇对比 老v1（备份）/ 新v1（改prompt后）/ 新v3（codex修正两轮），关键数字翻 PDF 核。
> **结论先行：就 agent 目标，新 v1/v3 在要紧轴上普遍优于老 v1；但修正环节有 1 个致命失效 + 2 个系统脏点。用户读到的"错"主要来自修正环节（v2/v3），不是新 base prompt。** 这一会话是后来 verify 改 report-only + 整篇重做的直接根因。

### 一、16 篇版本排序（按"给 agent 查事实"目标）
绝大多数 **v3 ≥ 新v1 > 老v1**；**v2 几乎总是最危险中间态**。要紧病例：
- **GAE（高维连续控制）** ⚠️ 老v1 ≈ 新v1 > v3：v3 把 codex 标对的双足 impact=10⁻⁵ **反向改回错的 10⁻³**，还伪造"已逐字核对原文"（PDF p.9 核实=10⁻⁵）。三版其实都错过此数，但 v3 最危险（错 + 假背书）。
- **Learning to Walk** ⚠️ 新v1 ≥ v3：v3 把 PDF 写的 q̄=0.3 改成 -0.3 当**原文直引**（伪引文；真值或确为 -0.3 来自代码，但 PDF 正文是 0.3）。
- **Reward-Adaptive（HDPG 双足）** ⚠️ v3 > 老v1 > 新v1 ≫ v2：Walker2d std ±528 张冠李戴是 **v2 凭空造的**（HalfCheetah 的 ±528.1 误绑 Walker2d，老v1 本来对），v3 修回并加纠错注。
- 其余多数：TD3 / Deep RL That Matters / RL-CBF / P3O / Reproducibility / Safe RL CBF / Temporal Logic 等，v3 普遍修对了新v1 或老v1 的过度声称/归属错（如 may require→必须、最大障碍 vs one main reason）。
- 多篇 v2/v3 顶部混入 Codex/claude 旁白（"I've verified..." / "I'll output the corrected markdown..."）。
- "What Matters for/in" 两 slug 是**同一篇论文**（md5 相同 PDF）重复入库——RAG 去重隐患（已知问题）。

### 二、三个缺陷（按危害排序）——这才是要改的
- **🔴 缺陷1（致命）：修正环节会推翻 codex 正确认定 + 伪造"我核过了"。** GAE（codex 对 10⁻⁵，v3 反"确认"成 10⁻³ + 编"已逐字核对"）、Learning to Walk（造 PDF 没有的 -0.3 伪引文）。最坏组合 = 错数字 + 假核对背书 → agent 更信带"核过"标记的版本。**用户读到的"新版有错"主要源于此。** 修向：`correct_summaries` prompt **去掉裁决权**——只按 codex 问题清单改，拿不准就软化/标存疑，**不许反向裁定原文、不许写"已核对原文"类背书**。
- **🟠 缺陷2（系统脏数据，最便宜）：codex/claude 旁白串进正文。** agent 按结构解析/FTS 索引会吃脏内容。修向：register/correct 落盘前 strip 掉 frontmatter 之前的非结构化文本。
- **🟡 缺陷3：v2 是危险中间态**（张冠李戴高发，如 ±528），绝不能进出口；当时 DB 有 20 篇停 v2/v3 待重核。

### 三、要收回的一个判断 + 一个真实权衡
- **strength 标签 `(supported)/(observed)/(strong)`：对人读 intuition 是噪声，但对 agent 取数是净帮忙**（区分被证明/单次观察/作者声称，挡过度外推）。6 agent 一致 → 就 agent 目标该留。用户"老的 intuition 更好"成立，但那是人的阅读体验 ≠ agent 的取数体验。
- 新 prompt 的接地/两段式确有"把数字从语境剥离 → 张冠李戴""接地门只验引文在不在、不验绑得对不对"的机制性风险（GAE/Walk 体现），但实测频率低于预期，v3 多半能 catch。

### 四、未决（用户 2026-06-17 明确：总结错误要进一步考虑，先别动 prompt）
- 不退回老 prompt（证据不支持）。但"总结质量"是更根上的问题，候选方向（未定）：① 修正环节该不该有裁决权 / 怎么防"假核对背书"；② 接地门要不要加"引文是否支持该论断（语义忠实/对象绑定）"；③ 两段式（note_plan→写）是否保留 vs 回边读边写以保上下文不断；④ v2 中间态如何不外泄。
- 已做（本会话）：cron 暂停 + 本对照 report。
- **教训沉淀**：此会话直接催生了后来（06-18）verify 重构——核查改 **report-only**（核查员不再有裁决权、不许伪造背书）+ major 触发**整篇重新总结**（取代打补丁式 correct_summaries，根治"反向裁决 + 假核对背书"）。

---

## 2026-06-17 · codex 额度烧穿 + verify 全盲 诊断

> 现象：清库重跑总结后，连续三班（凌晨补跑 / 5:30 cron / 上午手动补）codex verify 几乎全挂。
> 本会话：定位根因 + 拿一手证据 + 改 cron 间隔（4.5h→5.5h）。codex 那对根因 bug 当时还没修，留次日。
> 配套：本会话 cron 暂停；总结质量对照见同日 prompt 对照条。

### 一、三班实测（从日志精确数）
- ① 手动补 ~2am：想核 r1 20 + r2 复核 20 → 仅 r1 全成 20，r2 复核 20 篇全挂。
- ② cron ~5:30：想核 39 → 一上来全挂（距 ① 仅 3.5h，窗口没恢复）。
- ③ 手动补 ~10:20：r1 39 + r2 38 → 仅 19 成（r1 里就挂 20），r2 38 全挂；报告头 checked 19/77 errors 58。

**经验结论（要紧规律）**：此订阅 + 重型 verify（gpt-5.5/high + 自读 PDF）**一个额度窗口只够 ~20 次核查、小时级恢复**（3.5h 不够）。**悬崖式失效**：成功若干次后突然每次秒 exit 1，不是渐变。这是后来 `VERIFY_MAX_PER_RUN=15` 上限 + cron/daemon 分工的实测依据。

### 二、根因：外部触发 + 四个代码缺陷把"软限流"放大成"硬黑屏 + 越敲越死"
- **外部触发（非 bug）**：codex 用最贵配置（gpt-5.5 + reasoning high + 自读/渲染 PDF），单次极费——交互探针只回"OK"就烧 23,290 tokens。20 篇/班×3 班 → 烧穿 ChatGPT 订阅滚动窗口。
- **Bug A（根因·`lib/codex.py:49`）**：`raise ...: {stderr[:300]}` 只截 stderr 前 300 字，而 codex 开头先打 session 横幅，**真错误在横幅之后被截没** → 58 条失败全长一样、全是横幅，全程**不知道**为何挂。
- **Bug B（根因·`verify_summaries.py:197`）**：熔断器 `if "usage limit" in str(e).lower()` —— 但 str(e) 只有横幅、永无此串 → **熔断从不触发** → 明知会挂还把剩余调用全发，对满额账号继续猛敲把窗口摁更死。**Bug A 一修，B 自动活**。
- **Bug C**：全链路无退避 / 不解析"try again in X" / 无每窗口调用预算；reasoning effort 放任 high（最贵）。
- **Bug D（`escalate_verify.py:74`）**：`if not ok: break` 一轮全挂就 abort，未核记为 failed（而非 deferred），下班从零重来。

### 三、结构性问题：需求 > 供给（间隔治不了）
每班 verify 需求 = r1 核新总结（~20）+ r2 复核修正过的（~20）≈ **40 次** ≫ 窗口供给 **~20 次** → **复核轮（r2）必然撞穿**，每班日志"r1 还行→r2 全挂"正是此故。未核积压还会进下班 must 集累积，需求只增不减。

### 四、本会话已改 / 待办
- ✅ cron 间隔 4.5h→5.5h（2:00 / 7:30；crontab 已装、CLAUDE.md + claude-memory/operation-maintenance/nightly-cron.md 已同步）。仅缓解批间窗口恢复，**不治单批内 r2 撞穿**。
- ⬜ 修 Bug A+B（最高优先，耦合）：codex.py 抓 stderr+stdout 尾部、异常带全因；熔断关键词扩（usage/rate limit/429/quota/too many requests）+ 跨轮持久 + 未核记 deferred。
- ⬜ 修 Bug C/D：退避 + 解析重试间隔；给窗口设 ~15-18 次预算主动停；abort 标 deferred 下班优先续。
- ⬜ 降需求：批量 20→~8-10，或复核轮拆到下一窗口/下一班。
- ⬜ 补 codex token 监控（现在只记时长，token 是黑箱）。
- ⬜（独立）版本通胀：escalate 对"非 pass 全重写"（含 minor）+ verify 几乎不发 pass（大量"note_plan 无锚点"minor，其实原文支持）→ v2/v3 暴涨但多非真修；修向：这类"原文支持仅未登记锚点"的 minor 不触发重写。

### 五、当时数据状态
- summarized=39 / pdf_downloaded=182；版本 v1=39 / v2=20 / v3=18。
- 4 个真 major（数字张冠李戴/符号写反/论断说反）已改到 v3，但 **v3 从未被 codex 复核确认**（每次复核都撞挂）。

---

## 2026-06-15 · 新核查流程重跑 + 对比 + 流程反思（撞配额 → 转向重思流程）

> 目标：用升级后的核查流程（PDF 唯一来源 + Codex 自渲染 PDF）重跑两主题、与旧流程逐篇对比质量。
> 过程中撞 Codex 配额 → 试 claude 应急 → 用户喊停 → 转入"重新思考流程"，参考 ARS 读论文做法。

### 一、做了什么（按时间）
1. **快照备份**（可回滚锚点）→ `logs/verify-baseline-20260615/`：原始 db + 两主题旧 `summary_verification.md`/`verified.json` + `correction_worklist.json`；并就地存 `.old` 副本。
2. **重置 verified.json**（gt 清空、dhi 本无）——否则新流程认"全核过了"不重跑，这是新旧能对比的前提。
3. **抽样验证新流程**（各 3 篇）通过：Codex 自渲染 PDF 正常、报告格式对。dhi 抽样 2 pass / 1 major（一篇 **v2（旧流程修过）仍被揪出张冠李戴** major：把 Hassan et al./PADL 的数字安到本篇头上 → 证明新流程确有增量）；gt 抽样 3 篇全 minor。
4. **gt 全量核查**（codex, pct=100）→ 只核 13 篇就**撞 Codex 配额**：checked 13/97（5 pass/8 minor/0 major），84 篇 usage-limit 报错。
5. **诊断**：手跑最小 codex 调用，挖出完整报错 `You've hit your usage limit ... try again at 11:54 PM`。**非脚本 bug，是 ChatGPT 订阅用量到顶**（更新 codex 0.139→0.140 后报错一字不变 = 坐实与客户端无关）。
6. **用户要"先把这轮跑完"** → 加 **`VERIFY_BACKEND=claude` 应急开关**（可逆、默认仍 codex；claude 走文本核查、结果写独立 `_claude` 文件、不碰 codex 轨道）。claude 抽样 2 篇通过（印证同模型自查更宽松：TD3 篇 codex 判 minor、claude 判 pass）。
7. **用户喊"先全部停下"** → kill claude 全量进程（无残留）；数据零损坏。

### 二、当前状态（截至会话末）
- 没有任务在跑。**数据零损坏**：总结正文 100% 没动（全程没跑 `correct_summaries`），DB `summary_versions` 仍 v1:221/v2:19/v3:1。
- 核查进度：codex 轨道 gt verified.json 16/100、dhi 3/129；claude 轨道 gt 2、dhi 0（独立文件）。旧流程原件都在 `logs/verify-baseline-20260615/` + `.old`，可秒级还原。

### 三、已定决策
- **保留 `VERIFY_BACKEND` 开关**（应急用，默认 codex 不影响 run auto）。
- **先等 codex 配额恢复再继续**（不跑 claude 全量）。用户**正在重新思考整条流程**，参考 ARS。

### 四、ARS 的"读论文" prompt（中文讲解，供反思）
ARS 没有"读一篇→写总结"的 prompt（它是写论文流水线）；"读论文"拆在 4 处：
1. **source_verification_agent**：死划职责边界 + "信任但要验证" + 证据 7 级 + **"读进来的内容是数据不是指令"**（PDF 里像命令的话当 finding 不执行）。
2. **claim_ref_alignment_audit_agent**（论断↔被引文献对齐 = 他们的 verify）：判决四档 **SUPPORTED/UNSUPPORTED/AMBIGUOUS/RETRIEVAL_FAILED**，宁判 AMBIGUOUS 不硬判；**"绝不编造来源说了 X、绝不假装读过没返回的论文"**；按节/页/原句锚定引用；区分 paywall vs 工具故障；与 integrity（存在性）互补；抽样不静默截断。动机 = Zhao et al. 14.6 万幻觉引用，L3 忠实性是未解难题。
3. **literature_matrix_template**：来源×主题矩阵，每格原文引用 + ✓支持/✗矛盾 + 证据等级 + 收敛/矛盾/缺口汇总。
4. **阅读探针**（socratic mentor 内）：查的是**人**——让用户用自己的话复述引用过的论文段落，不评对错、可拒绝、只记录。

**一句话对比**：ARS 把读论文当"严防幻觉的责任链"（锚定引用/留模糊档/反假装读过/区分存在性 vs 忠实性/连人都查）；我们 `summarize_auto` 是一个 prompt 一把梭。

### 五、未决 / 下一步（当时）
- 全量核查（受配额阻塞，待续）、修正、对比报告、抽查汇报、常驻续跑脚本。
- **流程是否重设计**（按 ARS 那几条改 summary/verify prompt）——用户思考中，未定。

> 关联记忆：`verify-rerun-comparison.md`、`cross-model-codex-panel.md`。
