# Telegram 通知 + 对话 bot

> 整合自 CLAUDE.md「Telegram 通知 + 对话 bot」节（2026-06-20 搬进 ops/）。
> bot：@research_agentffbot。配置在 `config/telegram.json`（**gitignore，不入库**；token 是密钥）。

## 三层用途

| 层 | 代码 | 干什么 |
|---|---|---|
| 一次性推送 | `notify()`（`lib/notify.py`） | tierb 登录/Duo 提醒、进度、报错、夜间燃尽/队列报告 |
| 等回复轮询 | `wait_for_reply()` | 仅在一次运行卡住等用户时轮询（如 tierb 等人点验证） |
| 对话 bot | `pipeline/tools/bot.py` | 常驻长轮询，用户在 Telegram 发任何话 → 转本机 `claude -p` |

## 配置（换机器/首次必做）

`config/telegram.json` 是 gitignored（token 是密钥，不随 git 来）。CLI：
```bash
python3 pipeline/tools/notify.py settoken   # 贴 bot token
python3 pipeline/tools/notify.py chatid     # 先给 bot 发条消息，再跑此命令抓 chat_id
python3 pipeline/tools/notify.py test       # 验证能收到
```
没配不报错（`notify()` 降级成打印），但夜间 cron 就收不到结果通知。只认配置里的 `chat_id`。

## 对话 bot（2026-06-10 上线，照 Stock_agent/daily-digest/bot.py 移植）

常驻长轮询：用户在 Telegram 上发任何话 → 转本机 `claude -p --resume`（opus、`--dangerously-skip-permissions`、cwd=仓库根，多轮记忆存 `logs/bot_session.txt`）。命令：`help` / `new`（清会话）/ `log [N]`（看 run.log）。只认配置里的 chat_id。

**起停**（单例，`bot.pid` 活着就拒启；**不随开机自启**，机器重启要手动拉起）：
```bash
cd ~/Projects/Research_agent && setsid nohup python3 -u pipeline/tools/bot.py >> logs/bot.log 2>&1 &
kill $(cat logs/bot.pid)   # 停
```

### ⚠️ 与 tierb 协作（独占 getUpdates 的坑）

bot 常驻时**独占 Telegram getUpdates**，所以：
- bot 把每条消息额外落一份 `logs/bot_inbox.jsonl`。
- `wait_for_reply()` 检测到 bot 在跑（`logs/bot.pid` 进程活着）就改读 inbox，并写 `logs/bot_wait.json` 声明它在等的关键词；bot 对命中关键词的消息只转交、不回给 claude。
- bot 死了则自动回退到老的 getUpdates 轮询。

这样 tierb 等人点验证（`wait_for_reply`）和常驻 bot 可以共存，不会互抢 getUpdates。

## 谁在发通知

- **夜间 cron**（`auto-sum-next`）：开跑 `🌙 auto-sum start`，收尾发本主题燃尽（🎉/⚠️/✅）+ 全队列各主题剩余 + `📋待核N`。详见 `nightly-cron.md`。
- **verify_daemon**：撞 codex 配额耗尽时发 Telegram + 干净停止；额度恢复重跑续核。
- **tierb**：撞 Cloudflare/Duo 验证暂停时喊人来点（封存的手机看屏会带 noVNC 链接，见 `remote-access.md`）。
- **新主题冷启动自举**：`score` 阶段自动挑 score_anchors 后非阻塞推 TG 告知可事后改。

## 相关文件

- `pipeline/lib/notify.py` —— `notify()` / `wait_for_reply()`。
- `pipeline/tools/notify.py` —— settoken/chatid/test CLI。
- `pipeline/tools/bot.py` —— 对话 bot（长轮询 + inbox 机制）。
- `config/telegram.json` —— token + chat_id（gitignored）。
- 换机器重配 → `migration.md`。
</content>
