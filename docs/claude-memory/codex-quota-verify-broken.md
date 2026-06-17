---
name: codex-quota-verify-broken
description: "codex verify 因额度烧穿+代码缺陷连挂三班;已调 cron 间隔,根因bug待修"
metadata: 
  node_type: memory
  type: project
  originSessionId: cfdbc7ff-12f4-4ae2-b443-9a8bb71629da
---

2026-06-17 清库重跑总结后,codex verify 连挂三班。**实测**:此 ChatGPT 订阅 + 重型 verify(gpt-5.5/high+自读PDF)**一个额度窗口只够 ~20 次核查、小时级恢复、悬崖式失败**(探针只回"OK"就烧 23k tokens)。

**根因 = 外部触发(额度) + 四个代码缺陷**:
- Bug A(`lib/codex.py:49`):异常只截 `stderr[:300]`=codex 开机横幅,真错误被截没 → 全程不知为何挂。
- Bug B(`verify_summaries.py:197`):熔断器查 "usage limit" 字样,但 str(e) 只有横幅永无此串 → **熔断从不触发**,把注定失败的调用全发、越敲越死。**A 一修 B 自动活,这对最高优先。**
- Bug C:无退避/无每窗口预算/reasoning effort 放任 high。Bug D(`escalate_verify.py:74`):一轮全挂就 abort、未核记 failed 非 deferred。

**结构性**:一批 verify(~20)+复核轮(~20)≈40 次 ≫ 窗口 ~20 → 复核轮(r2)必撞穿。**怀疑 2026-06-17 把批量 10→20 是诱因**(10 时 r1+r2≈20 正好一窗口)。

**已做**:cron 间隔 4.5h→5.5h(2:00/7:30)。**⚠️ 只缓解批间,治不了单批内 r2 撞穿。** 真治要降批量(20→~10)或拆复核到下一窗口 + 修 A/B/C/D + 补 codex token 监控。

**数据状态**:summarized=39/pdf_downloaded=182;v1=39/v2=20/v3=18;4个真 major 改到 v3 但从未被 codex 复核确认。完整诊断+证据见 `logs/SESSION-2026-06-17-codex-quota.md`。相关:版本通胀另是独立问题(escalate 非pass全重写+verify几乎不发pass)。
