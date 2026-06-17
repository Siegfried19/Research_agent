# SESSION 2026-06-17 — codex 额度烧穿 + verify 全盲 诊断

> 现象:清库重跑总结后,连续三班(凌晨补跑 / 5:30 cron / 上午手动补)codex verify 几乎全挂。
> 本会话:定位根因 + 拿一手证据 + 改 cron 间隔(4.5h→5.5h)。**codex 那对根因 bug 还没修,留明天。**

## 一、三班实测(从日志精确数,不是推断)
| 班 | 时间 | verify 想核 | 挂前成功 | 结果 |
|---|---|---|---|---|
| ① 手动补1:00 | ~2am | r1 20 + r2复核20 | **20**(r1全成) | r2 复核20篇全挂;corrected=20→v2 |
| ② cron | ~5:30 | 39 | **0** | 一上来全挂(距①仅3.5h,窗口没恢复) |
| ③ 手动补 | ~10:20 | r1 39 + r2 38 | **19**(r1里就挂20) | corrected=18→v3;r2 38全挂。报告头 checked:19/77 errors:58 |

**经验结论**:此订阅 + 重型 verify(gpt-5.5/high+自读PDF)**一个额度窗口只够 ~20 次核查**,**小时级恢复**(3.5h 不够)。**悬崖式**:成功若干次后突然每次秒 exit 1,不是渐变。

## 二、根因:外部触发 + 四个代码缺陷把"软限流"放大成"硬黑屏+越敲越死"
**外部触发(非bug)**:codex 用最贵配置(gpt-5.5 + reasoning high + 自读PDF/渲染),单次极费——交互探针**只回"OK"就烧 23,290 tokens**(真 verify 调用只重得多)。20篇/班×3班 → 烧穿 ChatGPT 订阅滚动窗口。

**代码缺陷(要修的在这)**:
1. **Bug A(根因·`lib/codex.py:49`)**:`raise RuntimeError(f"...: {stderr[:300]}")` 只截 stderr 前300字,而 codex 开头先打 session 横幅(workdir/model/...),**真错误在横幅之后被截没**。证据:58条失败全长一样、全是横幅(`codex exec exit 1: OpenAI Codex v0.140.0\n--workdir:...model:gpt-5.5...`)。→ 我们全程**不知道**为何挂。
2. **Bug B(根因·`verify_summaries.py:197`)**:熔断器 `if "usage limit" in str(e).lower()` —— 但 str(e) 只有横幅、永无此串 → **熔断从不触发** → 明知会挂还把剩余 39/58 个调用全发,白等 + **对满额账号继续猛敲、把窗口摁更死**。**Bug A 一修,B 自动活**(str(e) 里就有真"usage/rate limit"了)。
3. **Bug C**:全链路无退避/不解析"try again in X"/无每窗口调用预算;reasoning effort 放任默认(high=最贵)。
4. **Bug D(`escalate_verify.py:74`)**:`if not ok: break` 一轮全挂就 abort,未核的记为 failed(而非 deferred),下班从零重来。

**pool 机制(`lib/claude.py:80`)**:worker 抛异常 → `{"error": str(e)}`,所以报告底部能看到 error 但内容是被截的横幅。

## 三、结构性问题:需求 > 供给(间隔治不了)
每班 verify 需求 = r1 核新总结(~20) + r2 复核修正过的(~20) ≈ **40 次** ≫ 窗口供给 **~20 次** → **复核轮(r2)必然撞穿**。每班日志都是"r1还行→r2全挂"正是此故。而且未核积压会进下班的 must 集累积,需求只增不减。

## 四、本会话已改 / 待办
- ✅ **cron 间隔 4.5h→5.5h**(2:00 / **7:30**;crontab 已装、文档已同步 CLAUDE.md + docs/nightly-cron-deploy.md)。**仅缓解批间窗口恢复,不治单批内 r2 撞穿**(已在 deploy 文档写明)。
- ⬜ **修 Bug A+B(最高优先,耦合)**:codex.py 抓 stderr+stdout 尾部、异常带全因并写日志;熔断关键词扩(usage/rate limit/429/quota/too many requests)+ 跨轮持久 + 未核记 deferred。
- ⬜ **修 Bug C/D**:退避+解析重试间隔;给滚动窗口设 ~15-18 次调用预算主动停;abort 时标 deferred 下班优先续。
- ⬜ **降需求(配合间隔才真治)**:批量 20→~8-10(让 r1+r2 ≈一个窗口),或复核轮拆到下一窗口/下一班。
- ⬜ **补 codex token 监控**(现在只记时长,token 是黑箱;与 Bug A 同源)。
- ⬜ (独立问题)**版本通胀**:escalate 对"非pass全重写"(含minor) + verify 几乎不发pass(大量"note_plan无锚点"minor,其实原文支持)→ v2/v3 暴涨但多非真修。修向:这类"原文支持仅未登记锚点"的 minor 不触发重写。

## 五、当前数据状态
- summarized=39 / pdf_downloaded=182;版本 v1=39/v2=20/v3=18。
- 4个真 major(数字张冠李戴/符号写反/论断说反)已改到 v3,但**v3 从未被 codex 复核确认**(每次复核都撞 codex 挂)。
- codex 探针此刻可用,但一上批量即挂(额度未恢复)。
