# 夜间自动跑流水线 — 部署 runbook

> 给将来换机器部署的我自己看。2026-06-16 建。
> 背景:用户要在**一台常开机器**上半夜自动跑流水线,白天把 token 额度留给自己用。
> 配套代码改动:`pipeline/run.py` 新增 `auto-pull` / `auto-sum` 两个组合模式(见下)。

## 一句话设计

把 `run auto` 这条链按 **token 消耗 + 要不要人** 切成两半:

| 模式 | 阶段 | 谁跑 / 何时 | 吃 token? | 要人? |
|---|---|---|---|---|
| `auto-pull` | discover→score→commit→fetch→recover→hunt→**tierb**→worklist | **人在场时手动跑**(白天/会话里) | 小(score+hunt) | **是**(tierb 点验证) |
| `auto-sum` | **sum**→finalize→**verify** | **夜间 cron 无人值守** | 大(sum+verify) | 否 |

切点的理由:`tierb`(唯一要人的阶段)卡在链子中间,而 token 大户(sum/verify)在后半段。前半段连人带付费墙验证一起白天搞定;后半段纯烧 token 的丢给夜里,不和用户白天抢 Max 额度。

- `auto`(原全程,11 阶段)保留不动,随时能整条跑。
- 设计经用户拍板(2026-06-16):score/hunt 这点小 token **留在白天 auto-pull**,不挪夜里(挪了会把链拆碎、顺序绕)。

## 前提:整个仓库住在这一台机器上

用户定了**方案 A**——repo + `db/papers.sqlite` + `store/`(PDF/全文/总结)全在常开机器这一台。**不跨机器同步**,所以没有 DB/PDF 错位问题。`auto-pull` 的 tierb 也在这台跑 → **这台必须能开图形界面 Chrome 让人点验证**(不是纯 headless 服务器)。

## 部署清单(到新机器上逐项过)

1. **clone 仓库** + `pip install -r requirements.txt`(唯一第三方依赖 `requests`)。
2. **`claude login`** —— `claude -p` 无头要登录(走 Max 订阅)。score/sum/correct 全靠它。
3. **`npm i -g @openai/codex` + `codex login`** —— verify 阶段 Codex 跨模型核查要它(走 ChatGPT 订阅)。**漏这步 verify 会全跳过/报错。**
4. **重配 Telegram** —— `config/telegram.json` 是 gitignored(token 是密钥,不随 git 来)。跑:
   ```
   python3 pipeline/tools/notify.py settoken   # 贴 bot token
   python3 pipeline/tools/notify.py chatid     # 给 bot 发条消息再跑,抓 chat_id
   python3 pipeline/tools/notify.py test        # 验证能收到
   ```
   没配 notify 不报错(降级成打印),但夜间 cron 就收不到结果通知了。
5. **装 cron 行**(见下)。

## cron 行(队列模式,一晚两批,各 20 篇,相隔 ~5.5h)

用户要的节奏:**每晚跑两次、一次 20 篇**(2026-06-17:看过 10 篇用量校准后从 10 提到 20)。

**2026-06-17 起用队列模式 `auto-sum-next`**(取代写死单主题的 `auto-sum <id>`):每次跑**从 `topics` 表按 `priority` 挑第一个"还有可做篇"的主题**做 ≤N 篇,做完自动顺到下一个主题。好处:加新主题自动进队、不用改 cron;一次只跑一个主题=串行不抢 Max 额度。第一个位置参数是占位符(被忽略,只为满足 `<topicId> <stage>` 位置)。`crontab -e` 加两行:

```cron
0 2 * * *  cd ~/Projects/Research_agent && /usr/bin/python3 pipeline/run.py queue auto-sum-next 20 >> logs/cron-sum.log 2>&1
30 7 * * * cd ~/Projects/Research_agent && /usr/bin/python3 pipeline/run.py queue auto-sum-next 20 >> logs/cron-sum.log 2>&1
```

> **队列顺序/插队**:排序 = `topics.priority DESC, 建立序(rowid) ASC`,默认都 0=按建立先后。想让某主题先做就调高它的 `priority`(`UPDATE topics SET priority=1 WHERE id='...'`)——清单每晚现读,当晚生效。可经 Telegram bot 让 claude 帮你改。
> **报告**:每批收尾发 Telegram = 本主题燃尽(🎉做完/⚠️即将耗尽/✅有余量) + **全队列各主题剩余**;全清完发 🎉;某批 0 进展(疑似卡坏PDF)发 ⚠️ 提醒人工看。
> **旧版单主题** `auto-sum <id> [N]` 保留不动,想只跑某一个主题时仍可用。

### 批量与 token 重置(为什么是两批 + 间隔 ~5.5h)

- Claude Max 额度是**滚动窗口(~4–5h)**,重置时刻 = 窗口内**第一次用之后 N 小时**,**浮动**,cron 无法精确卡在重置瞬间。
- 实用等价:**两个固定钟点相隔 ~5.5h**(现为 2:00 / 7:30),让第二批落进新窗口。20 篇/批(实测单篇 summarize ~$3.36 等效/Max 实付$0)一般仍在一个窗口内,跨窗口也由幂等+continue-on-error 兜住,所以对齐不苛刻。
- **2026-06-17 从 4.5h 调到 5.5h**:codex(verify 用,走 ChatGPT 订阅,**独立于 Claude Max**)的额度窗口实测只够 ~20 次重型核查、且小时级恢复;4.5h 时第二批常落进尚未恢复的 codex 窗口、verify 整批全挂(见 `logs/SESSION-2026-06-17-codex-quota.md`)。⚠️ **但加间隔只缓解"批与批之间",治不了"单批内部":一批 verify(~20)+复核轮(~20)≈40 次需求 > 单窗口 ~20 次供给,复核轮仍会撞穿——根治要降批量/拆复核到下一窗口/修 codex 熔断那对 bug。**
- `auto-sum-next 20` 里 `sum` 只总结被选中主题里 rank 最高的 20 篇没总结的(`summarize_auto --limit 20`,幂等,下批接着往下),`verify` 仍扫全部未核查的但被 codex 用量熔断 + 每晚只新增 20 篇自然收口。每批前会先重建该主题 worklist(`run_auto_sum` chain 头部,便宜幂等)以便切主题后自洽。
- 想加量/改节奏:调 N 即可。**首夜若有大量"已总结未核查"积压**,verify 会被 codex 限流熔断、只清一部分,余下后续每晚续清(verified.json 按轮落盘,进度不丢)。

- **多主题不用复制 cron 行**:队列模式一次只跑一个主题、串行排队(天然不抢额度),加新主题自动进队。要控制先做谁就调 `topics.priority`。
- **cron 的环境很干净**(不读 `.bashrc`),三个坑:
  1. **Python 用绝对路径**(`which python3` 查,常是 `/usr/bin/python3`)。
  2. **`claude` / `codex` 可能不在 cron 的 PATH 里** → 子进程找不到会让 sum/verify 失败。解法:cron 行最前面补 PATH,例如
     ```cron
     0 2 * * *  cd ~/Projects/Research_agent && PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:$PATH /usr/bin/python3 pipeline/run.py <id> auto-sum >> logs/cron-sum.log 2>&1
     ```
     部署时先 `which claude; which codex` 查出真实路径,把它们的目录拼进 PATH。
  3. **机器必须开着**,睡眠/关机不跑(常开机器满足)。
- 输出已重定向到 `logs/cron-sum.log`;`run.py` 自身还写 `logs/run.log`(机器日志)。

## auto-sum 的内建韧性 / 通知(已在 run.py 里)

- **continue-on-error**:某阶段撞 Max 限流失败,**不中断**——继续往下跑(sum/finalize/verify 都幂等),最后返回非零让 cron 日志能看出来。已总结的下一晚自动跳过,所以部分失败=次晚补齐。
- **Telegram**:`auto-sum` 开跑发 `🌙 auto-sum start: <id>`,跑完发 `✅/⚠️ auto-sum done: <id> (rc=N)`。没配 telegram 则降级打印,不报错。
- **限流调并发**:夜间 sum 跑上百篇易撞 Max 限流。慢点无所谓(在睡),需要时把 `summarize_auto.py` 并发调到 1~2。如要在 cron 里固定小并发,改 run.py 的 `AUTO_SUM` 对应 step 传参,或单独 cron 跑 `summarize_auto.py <id> 1` 再跑 finalize/verify。

## 日常使用流(单机)

1. **白天/会话里**:用户说要跑某主题 → 我起 `python3 pipeline/run.py <id> auto-pull`,盯着,到 tierb 时用户点付费墙验证。跑完所有 PDF 就绪、worklist 建好。
2. **当晚 2:00**:cron 自动 `auto-sum` 把新拉到的篇总结+核查,手机收到 ✅。
3. 付费墙没赶上某篇就停在 `pdf_failed`,等下次 auto-pull 补;sum 幂等,不会重做已总结的。

## 相关文件

- `pipeline/run.py` —— AUTO / AUTO_PULL / AUTO_SUM 三个链 + `run_chain(continue_on_error=)`。
- `change-device/MIGRATION.md` —— 换机器总清单(记忆分布、telegram/codex 重建);换机器流程见 `change-device/README.md`。本文件是它们在"夜间自动化"这一块的细化。
- `CLAUDE.md` —— 项目总上下文。
