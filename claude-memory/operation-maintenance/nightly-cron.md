# 夜间自动跑流水线 — 部署 runbook

> 给将来换机器部署的我自己看。源自 `claude-memory/operation-maintenance/nightly-cron.md`（2026-06-16 建，2026-06-20 搬进 ops/）。
> 背景：用户要在**一台常开机器**上半夜自动跑流水线，白天把 token 额度留给自己用。
> 配套代码：`pipeline/run.py` 的 `auto-pull` / `auto-sum` / `auto-sum-next` 组合模式。

## 一句话设计

把 `run auto` 这条链按 **token 消耗 + 要不要人** 切成几段：

| 模式 | 阶段 | 谁跑 / 何时 | 吃 token? | 要人? |
|---|---|---|---|---|
| `auto-pull` | discover→score→commit→fetch→recover→hunt→**tierb**→worklist | **人在场时手动跑**（白天/会话里） | 小（score+hunt） | **是**（tierb 点验证） |
| `auto-sum` / `auto-sum-next` | **sum**→finalize | **夜间 cron 无人值守** | 大（sum，走 Claude Max） | 否 |
| `verify_daemon` | **verify**（跨模型 codex 核查） | **全天候后台，cron 每早 9:00 拉起** | 大（codex，独立配额） | 否 |

> ⚠️ **2026-06-19 改**：verify 已从 `auto-sum` 链摘出，改由 `tools/verify_daemon.py` 全天候单跑。理由：夜间 cron 顺手 verify 会和 daemon 抢同一个 codex 配额窗口（~20 次/窗）。现在 `auto-sum` 只 sum+finalize，verify 全交给 daemon。凡旧描述里"auto-sum 跑 verify"均已不成立。

切点的理由：`tierb`（唯一要人的阶段）卡在链子中间，而 token 大户（sum/verify）在后半段。前半段连人带付费墙验证一起白天搞定；后半段纯烧 token 的丢给夜里，不和用户白天抢 Max 额度。

- `auto`（原全程）保留不动，随时能整条跑。
- 设计经用户拍板（2026-06-16）：score/hunt 这点小 token **留在白天 auto-pull**，不挪夜里（挪了会把链拆碎、顺序绕）。

## 前提：整个仓库住在这一台机器上

用户定了**方案 A**——repo + `data-base/papers.sqlite` + `store/`（PDF/全文/总结）全在常开机器这一台，**不跨机器同步**，所以没有 DB/PDF 错位问题。`auto-pull` 的 tierb 也在这台跑 → **这台必须能开图形界面 Chrome 让人点验证**（不是纯 headless 服务器）。

## 部署清单（到新机器上逐项过）

1. **clone / 整目录搬仓库**（换机器细节见 `migration.md`）+ 装环境。运行环境统一是 conda 环境 **`research-agent`**（`environment.yml` 一键重建；含 GPU torch / sentence-transformers / sqlite-vec，是超集，主链只要 requests 也在内）。
2. **`claude login`** —— `claude -p` 无头要登录（走 Max 订阅）。score/sum 全靠它。
3. **`npm i -g @openai/codex` + `codex login`** —— verify 阶段 Codex 跨模型核查要它（走 ChatGPT 订阅）。**漏这步 verify 会全跳过/报错。**
4. **重配 Telegram** —— `config/telegram.json` 是 gitignored（token 是密钥，不随 git 来）。详见 `telegram.md`，最简：
   ```
   python3 pipeline/tools/notify.py settoken <BOT_TOKEN>   # 贴 bot token
   python3 pipeline/tools/notify.py chatid     # 给 bot 发条消息再跑，抓 chat_id
   python3 pipeline/tools/notify.py test       # 验证能收到
   ```
   没配 notify 不报错（降级成打印），但夜间 cron 就收不到结果通知了。
5. **装 cron 行**（见下）。

## cron 行（队列模式，一晚两批，各 20 篇，相隔 ~5.5h）

用户要的节奏：**每晚跑两次、一次 20 篇**（2026-06-17：看过 10 篇用量校准后从 10 提到 20）。

**2026-06-17 起用队列模式 `auto-sum-next`**（取代写死单主题的 `auto-sum <id>`）：每次跑**从 `topics` 表按 `priority` 挑第一个"还有可做篇"的主题**做 ≤N 篇，做完自动顺到下一个主题。好处：加新主题自动进队、不用改 cron；一次只跑一个主题=串行不抢 Max 额度。第一个位置参数是占位符（被忽略，只为满足 `<topicId> <stage>` 位置）。

**本机（siegfried）2026-06-19 实装的 crontab**（`crontab -l` 即见；PATH 头让 cron 干净环境也能找到 claude/codex；python 直接用 research-agent 环境的解释器，免 envguard re-exec）：

```cron
PATH=/home/siegfried/.local/bin:/home/siegfried/.nvm/versions/node/v24.16.0/bin:/usr/local/bin:/usr/bin:/bin
# 夜间两批，各 ≤20 篇，相隔 5.5h
0 2 * * *   cd /home/siegfried/Projects/Research_agent && /home/siegfried/anaconda3/envs/research-agent/bin/python pipeline/run.py queue auto-sum-next 20 >> logs/cron-sum.log 2>&1
30 7 * * *  cd /home/siegfried/Projects/Research_agent && /home/siegfried/anaconda3/envs/research-agent/bin/python pipeline/run.py queue auto-sum-next 20 >> logs/cron-sum.log 2>&1
# 上午 9:00 起 verify_daemon 啃当晚总结的核查积压（单例锁：还在跑则拒启；撞配额自动睡；啃完自退）
0 9 * * *   cd /home/siegfried/Projects/Research_agent && setsid nohup /home/siegfried/anaconda3/envs/research-agent/bin/python pipeline/tools/verify_daemon.py >> logs/verify_daemon.log 2>&1 &
```

> **verify_daemon 为何也挂 cron**：它"啃完积压就自退"（非常驻服务），所以每早拉起一次去清当晚 sum 出的新总结；单例 pidfile 保证若昨天那只还在啃（配额慢），今早这次直接被拒、不会重开。撞 codex 配额会自动睡到窗口恢复再续。手动起停：
> ```
> setsid nohup /home/siegfried/anaconda3/envs/research-agent/bin/python pipeline/tools/verify_daemon.py >> logs/verify_daemon.log 2>&1 &
> kill $(cat logs/verify_daemon.pid)   # 或 touch logs/verify_daemon.stop
> ```

> **队列顺序/插队**：排序 = `topics.priority DESC, 建立序(rowid) ASC`，默认都 0=按建立先后。想让某主题先做就调高它的 `priority`（`UPDATE topics SET priority=1 WHERE id='...'`）——清单每晚现读，当晚生效。可经 Telegram bot 让 claude 帮你改。
> **报告**：每批收尾发 Telegram = 本主题燃尽（🎉做完/⚠️即将耗尽/✅有余量）+ **全队列各主题剩余**；全清完发 🎉；某批 0 进展（疑似卡坏 PDF）发 ⚠️ 提醒人工看。报告头还带 `📋待核N`=daemon 还剩多少要核。
> **旧版单主题** `auto-sum <id> [N]` 保留不动，想只跑某一个主题时仍可用。

### 批量与 token 重置（为什么是两批 + 间隔 ~5.5h）

- Claude Max 额度是**滚动窗口（~4–5h）**，重置时刻 = 窗口内**第一次用之后 N 小时**，**浮动**，cron 无法精确卡在重置瞬间。
- 实用等价：**两个固定钟点相隔 ~5.5h**（现为 2:00 / 7:30），让第二批落进新窗口。20 篇/批（实测单篇 summarize ~$3.36 等效 / Max 实付 $0）一般仍在一个窗口内；跨窗口也由幂等 + continue-on-error 兜住，所以对齐不苛刻。
- **2026-06-17 从 4.5h 调到 5.5h**：codex（verify 用，走 ChatGPT 订阅，**独立于 Claude Max**）的额度窗口实测只够 ~20 次重型核查、且小时级恢复；4.5h 时第二批常落进尚未恢复的 codex 窗口、verify 整批全挂（见 `claude-memory/modules-modification/verify/STATE.md`）。⚠️ 加间隔只缓解"批与批之间"，治不了"单批内部"；verify 已摘出夜间链交给 daemon，这条对夜间 sum 不再是约束，留作 token 节奏参考。
- `auto-sum-next 20` 里 `sum` 只总结被选中主题里 rank 最高的 20 篇没总结的（`summarize_auto --limit 20`，幂等，下批接着往下）。每批前会先重建该主题 worklist（`run_auto_sum` chain 头部，便宜幂等）以便切主题后自洽。
- 想加量/改节奏：调 N 即可。

### 干净环境的三个坑（cron 不读 `.bashrc`）

1. **Python 用绝对路径**——直接指向 research-agent 环境的解释器 `~/anaconda3/envs/research-agent/bin/python`（既免 envguard re-exec，又保证 GPU 检索依赖在）。
2. **`claude` / `codex` 可能不在 cron 的 PATH 里** → 子进程找不到会让 sum/verify 失败。解法：cron 文件最前面补 PATH（见上面 crontab 头）。部署时先 `which claude; which codex` 查出真实路径，把它们的目录拼进 PATH（本机 = `~/.local/bin` + nvm 的 node 目录）。
3. **机器必须开着**，睡眠/关机不跑（常开机器满足）。
- 输出已重定向到 `logs/cron-sum.log` / `logs/verify_daemon.log`；`run.py` 自身还写 `logs/run.log`（机器日志）。

## auto-sum 的内建韧性 / 通知（已在 run.py 里）

- **continue-on-error**：某阶段撞 Max 限流失败，**不中断**——继续往下跑（sum/finalize 都幂等），最后返回非零让 cron 日志能看出来。已总结的下一晚自动跳过，所以部分失败 = 次晚补齐。
- **Telegram**：开跑发 `🌙 auto-sum start`，跑完发 `✅/⚠️ done (rc=N)` + 全队列各主题剩余。没配 telegram 则降级打印，不报错。
- **限流调并发**：夜间 sum 跑上百篇易撞 Max 限流。慢点无所谓（在睡），需要时把 `summarize_auto.py` 并发调到 1~2。如要在 cron 里固定小并发，改 run.py 的 `AUTO_SUM` 对应 step 传参，或单独 cron 跑 `summarize_auto.py <id> 1` 再跑 finalize。

## 日常使用流（单机）

1. **白天/会话里**：用户说要跑某主题 → 起 `python3 pipeline/run.py <id> auto-pull`，盯着，到 tierb 时用户点付费墙验证。跑完所有 PDF 就绪、worklist 建好。
2. **当晚 2:00 / 7:30**：cron 自动 `auto-sum-next` 把新拉到的篇总结，手机收到 ✅。
3. **每早 9:00**：verify_daemon 拉起，啃当晚总结的核查积压（撞 codex 配额自动睡、续核）。
4. 付费墙没赶上某篇就停在 `source_failed`，等下次 auto-pull 补；sum 幂等，不会重做已总结的。

## 相关文件

- `pipeline/run.py` —— AUTO / AUTO_PULL / AUTO_SUM 链 + 队列 `select_next_topic/queue_report/burn_down_msg/topic_progress` + `run_chain(continue_on_error=)`。
- `pipeline/tools/verify_daemon.py` —— 全天候核查守护进程（单例 pidfile、撞配额按类睡、啃完自退）。
- `claude-memory/operation-maintenance/migration.md` —— 换机器总清单（记忆分布、telegram/codex/conda 重建）。
- `CLAUDE.md` / `claude-memory/ARCHITECTURE.md` —— 项目总上下文。
</content>
</invoke>
