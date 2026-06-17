---
name: verify-rerun-comparison
description: 进行中任务——用升级后的核查流程(PDF唯一来源+Codex自渲染)重跑两主题、与旧流程逐篇对比质量;含待办清单与续跑状态
metadata: 
  node_type: memory
  type: project
  originSessionId: 28ae5a5d-9caf-40a8-a138-6a9460efdcbc
---

**⚡ 重大进展（2026-06-17）：从"逐篇对比"升级为"全清重做 + 夜间 cron 自动跑"。**
- 用户看过 10 篇用量校准后拍板：**清掉整个总结层、用新 prompt 重做全部 221 篇**（不重建 DB schema、不重下 PDF、不重打分——只换"总结"这一层）。
- **已执行 wipe**（备份在 `logs/wipe-summaries-20260617/`，可回滚）：`summary_versions` 241→0、全部 221 篇 status→`pdf_downloaded`、`store/summaries/` 清空、两主题 verified.json 置空+报告删除、worklist 重建(gt100/dhi129)。**保留**：papers/paper_topic(打分排名)/citations/topics/**store/pdfs(221)**。
- **夜间 cron 已真装并冒烟验证通过**（之前一直"未装"）：crontab 两行 `rl-general-toolbox auto-sum 20`（01:00/05:30），PATH 前缀含 claude(`~/.local/bin`)+codex(nvm 目录)。**先只挂 gt 单主题验证**，跑通几晚再加 dhi。批量 10→20（doc+CLAUDE.md 已改）。
- **夜间队列模式 `auto-sum-next` 已建+提交**（用户选了 B 跨主题队列）：cron 不写死主题,从 `topics` 表按 `priority DESC,建立序` 挑第一个还有可做篇的主题跑 ≤N 篇,做完自动顺到下一主题;加新主题自动进队、一次只跑一个=串行不抢额度。插队=调 `topics.priority`(可经 Telegram bot 让 claude 改,当晚生效;现 gt=1 先做/dhi=0)。`run.py`: `select_next_topic/all_topics_ordered/queue_report/burn_down_msg/topic_progress`;`run_auto_sum` chain 头部加 worklist;旧单主题 `auto-sum <id>` 保留。
- **燃尽报告**：每批 Telegram 发 本主题 🎉做完/⚠️即将耗尽(剩≤一晚量)/✅有余量 + **全队列各主题剩余**;全清🎉;0进展(疑似坏PDF)⚠️提醒人工。纯查库(`topic_progress` 排除无PDF篇)。
- **已提交**（2 commit）：`data:` 清空总结层 + `feat:` 队列模式/燃尽/用量探针(`LLM_USAGE_LOG` env 开关,默认关)。测试 5 分支全过(py_compile+单测+集成测)。cron 已真装冒烟验证(PATH 含 ~/.local/bin+nvm codex),下次真跑=每日 01:00/05:30。
- 10 篇校准结论(见下"用量校准")：summarize ~$3.36/篇等效(Max实付$0)、verify codex ~131s/篇、major 率 20%。

---
**任务（用户 2026-06-15 发起）**：总结核查流程刚升级（verify/correct 统一以 PDF 为唯一原文来源 + Codex 自渲染 PDF 看公式图表，commit 0d0ce64/26c3bb8）。用户要：**保留旧总结 → 用新流程重跑核查 → 每篇对比新旧总结质量**。旧总结不用手动备份（correct 写 vN+1、版本史天然保留），但旧核查产物会被覆盖、已快照。详见 [[cross-model-codex-panel]]。

**关键前提（已做）**：
- 快照旧产物到 `logs/verify-baseline-20260615/`（db + 两主题 summary_verification.md/verified.json + correction_worklist.json）+ 就地 `.old` 副本。
- **重置了 verified.json**（gt 清空、dhi 本就无）——否则新流程因"全核过了"一篇不重跑。这是让新旧能对比的前提。

**待办清单（按序）**：
1. ✅ 快照锚点 + 旧 baseline 副本
2. ✅ 抽样验证新流程跑通（gt 3 / dhi 3，Codex 自渲染 PDF 正常，报告格式对）
3. ⏳ **全量核查两主题（verify_summaries `<id> 100 2`，report-only）** — 进行中，受 Codex 配额限制跨窗口
4. ⏳ 自动修正 major → vN+1（`correct_summaries.py`，等 3 完）
5. ⏳ 写逐篇新旧对比报告 `verify-comparison.md`（旧判定 vs 新判定:多揪/少揪/一致 + vN→vN+1 diff）
6. ⏳ 抽查"新揪出"的篇是否真问题 + 向用户汇报决策（要不要设为默认/继续）
7. ⏳ **写本机常驻脚本自动续跑核查（脱离终端，仿 bot.py setsid nohup）** — 用户 2026-06-15 决定先记 todo、暂不建。轮询 codex 配额→恢复即续跑 verify(两主题,verified.json 断点续传)→撞墙再等→全核完发 Telegram。不需 Claude 在场、关终端照跑。**当前用 Claude 定时唤醒循环临时顶着（需开终端），此脚本是其替代。**

**续跑进度（更新于 2026-06-15 22:34 EDT）**：codex 轨道 gt 16/100、dhi 3/129（合计 19 篇，在 verified.json）。配额恢复后重跑同一命令自动只补剩余 210 篇。

**claude 应急后端（2026-06-15 22:55 加，用户要"先把这轮跑完"）**：`verify_summaries.py` 加 env 开关 `VERIFY_BACKEND=claude`（默认仍 codex，可逆、不影响 run auto）→ 改用 claude -p 文本核查（看不到公式图表），结果写**独立轨道** `verified_claude.json` / `summary_verification_claude.md`，报告头带 ⚠️，**不碰 codex 轨道**。⚠️ **同模型自查**(总结也是 claude 写的)共享盲点、强度弱——只算先跑完覆盖率，claude 判 pass 的篇待 codex 配额回来再抽查把关。实测印证:TD3 篇 codex 判 MINOR、claude 判 PASS(claude 更宽松)。正后台跑两主题 claude 全量(gt 剩 98→dhi 129)。codex 监控循环仍并行存活(23:35 探针),配额回来照做真跨模型核查。

**10 篇用量校准（2026-06-17，用户要"先跑10篇看用量"）**：取 gt top10，可逆重做（备份 DB+10篇总结目录+verified.json 到 `logs/redo-test-20260617/`，DB 整库备份在 `papers.sqlite.bak`，只重置这10篇 status/清旧总结/摘 verified.json）。给 `lib/claude.py`+`lib/codex.py` 加了**env 开关用量探针** `LLM_USAGE_LOG`（默认关，set 时 claude 走 `--output-format json` 拿 token/cost、codex 记时长；不影响 run auto）。结果：
- **summarize**：~2 claude 调用/篇（note_plan+正文），等效成本 **$3.36/篇**（Max 订阅实付$0，是滚动窗口配额代理；大头 cache_read 1.66M/篇＝PDF 多轮重读），CPU ~9.5min/篇（并发2墙钟约半）。
- **verify**：1 codex 调用/篇，**131s/篇**，ChatGPT 订阅 $0 token。
- **质量**：0 pass / 8 minor / **2 major（20%，与历史一致）**——新 summarize prompt 未消灭问题，major 仍靠 verify+correct 兜底。
- **外推 221 篇全量重做**：summarize 等效~$743/CPU~35h、verify CPU~8h（codex配额会拉长）；按夜间2批×10/晚节奏约 **11 晚**。
- **用户决定（2026-06-17）：先留这 10 篇重做版，其余 211 篇暂不动**，待人工看 10 篇新旧质量再定全量。探针代码未提交（env 默认关，留着备用）。

**发现**：
- 84 篇报错 = **Codex(ChatGPT订阅)配额用尽**，非故障（更新 codex 0.139→0.140 后报错一字不变=坐实与客户端无关）。提示 23:54 恢复。
- **脚本短板（待改进，未改）**：`verify_summaries.verify_batch` 的熔断只查 `stderr` 有无 "usage limit"，但 codex 把限流信息打在 stdout/横幅、returncode 时0时1 → 熔断没识别 → 撞墙后逐篇白撞剩余几十次（秒回、几乎不耗 token，失败篇不记 verified.json 无污染，但日志被刷脏、每窗口重复）。一行级小修：让熔断也认 stdout/out_file 里的 usage limit。
- 抽样实测：dhi 一篇 **v2(旧流程已修正过)仍被新流程揪出 5 条 major**——把被引文献 Hassan et al./PADL 的数字论断安到本篇头上（本篇 PDF 无），"张冠李戴"型幻觉，旧流程没抓、新流程抓到 = 新流程有增量。gt 全量已核 13 篇:5 pass/8 minor/0 major（多是 v2+ 旧流程修过的，符合预期，真考验在 82 篇 v1 还没核到）。

关联 [[cross-model-codex-panel]] [[research-paper-pipeline]]。
