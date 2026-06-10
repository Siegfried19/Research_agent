#!/usr/bin/env python3
"""Telegram 对话 bot（暂时升级，照 Stock_agent/daily-digest/bot.py 移植）。

    python3 pipeline/bot.py        # 常驻运行（长轮询，不开任何本机端口）

命令（私聊发给 bot，无需斜杠）：
    log [N]           看 logs/run.log 最后 N 行（默认 30）
    new               开新对话（清掉 claude 会话上下文）
    help              用法
    其他任何话         转给本机 claude -p（--resume 连续会话，带项目全部上下文
                      与工具权限，可问库、可跑流水线、可改代码）

安全：只响应 config/telegram.json 里 chat_id 的消息；token 不进 git。
与 tierb 的协作：bot 常驻时独占 getUpdates，所以每条消息也落一份到
logs/bot_inbox.jsonl；lib/notify.wait_for_reply 检测到 bot 在跑（logs/bot.pid）
就改读 inbox 文件，等验证的 done 回复不会被 bot 吞掉。
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

from lib.db import ROOT
from lib.notify import BOT_INBOX, BOT_PID, BOT_WAIT, _load

LOGS = ROOT / "logs"
SESSION_FILE = LOGS / "bot_session.txt"

USAGE = (
    "命令：\n"
    "log [N] — 看 run.log 最后 N 行（默认 30）\n"
    "new — 开新对话（清掉上下文）\n"
    "其他任何话 — 和 Claude 连续对话（带项目全部上下文，"
    "可问论文库、可跑流水线、可改代码；多轮记忆）\n"
)


def fix_path():
    """systemd/裸 shell 启动时 PATH 可能缺 ~/.local/bin（claude）和 nvm（codex），补上。"""
    extras = [str(Path.home() / ".local/bin")]
    nvm = Path.home() / ".nvm/versions/node"
    if nvm.exists():
        bins = sorted(nvm.glob("*/bin"), reverse=True)
        if bins:
            extras.append(str(bins[0]))
    os.environ["PATH"] = ":".join(extras + [os.environ.get("PATH", "")])


def claude_chat(text):
    """与 Claude Code 连续对话：--resume 续接同一会话，带工具权限。"""
    args = ["claude", "-p", "--model", "opus",
            "--dangerously-skip-permissions", "--output-format", "json"]
    sid = SESSION_FILE.read_text(encoding="utf-8").strip() if SESSION_FILE.exists() else ""
    if sid:
        args += ["--resume", sid]
    p = subprocess.run(args, input=text, capture_output=True, text=True,
                       encoding="utf-8", timeout=1800, cwd=str(ROOT))
    if p.returncode != 0:
        if sid:  # 旧会话可能已失效，清掉重来一次
            SESSION_FILE.unlink(missing_ok=True)
            return claude_chat(text)
        return f"❌ claude 出错: {((p.stderr or p.stdout) or '')[-400:]}"
    try:
        data = json.loads(p.stdout)
        if data.get("session_id"):
            SESSION_FILE.write_text(data["session_id"], encoding="utf-8")
        return data.get("result") or "(空回答)"
    except json.JSONDecodeError:
        return p.stdout.strip()[-3900:] or "(空输出)"


class Bot:
    def __init__(self, cfg):
        self.token = cfg["token"]
        self.chat_id = str(cfg["chat_id"])

    def api(self, method, http_timeout=70, **params):
        r = requests.post(f"https://api.telegram.org/bot{self.token}/{method}",
                          json=params, timeout=http_timeout)
        return r.json()

    def send(self, text):
        text = (text or "").strip() or "(空)"
        for i in range(0, len(text), 3900):  # Telegram 单条上限 4096
            try:
                self.api("sendMessage", chat_id=self.chat_id, text=text[i:i + 3900])
            except Exception as e:
                print(f"sendMessage 失败: {e}", file=sys.stderr)

    def handle(self, text):
        parts = text.strip().split()
        if not parts:
            return
        cmd = parts[0].lower().lstrip("/")

        if cmd in ("help", "start"):
            self.send(USAGE)

        elif cmd == "new":
            SESSION_FILE.unlink(missing_ok=True)
            self.send("已开新对话。")

        elif cmd == "log":
            n = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 30
            f = LOGS / "run.log"
            lines = f.read_text(encoding="utf-8").splitlines() if f.exists() else []
            self.send("\n".join(lines[-n:]) or "(run.log 为空)")

        else:  # 自由对话 → Claude Code 连续会话
            self.send("处理中...")
            try:
                self.send(claude_chat(text))
            except subprocess.TimeoutExpired:
                self.send("claude 超时(30 分钟)")

    def spool(self, text):
        """每条主人消息落一份到 inbox，给 wait_for_reply 读。"""
        try:
            with BOT_INBOX.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": time.time(), "text": text},
                                   ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"inbox 写入失败: {e}", file=sys.stderr)

    def waiting_keyword(self):
        """tierb 等回复时会写 bot_wait.json；命中关键词的消息不转 claude。"""
        try:
            return json.loads(BOT_WAIT.read_text(encoding="utf-8")).get("keyword", "")
        except Exception:
            return ""

    def loop(self):
        offset = 0
        try:  # 启动时丢弃积压的旧消息，避免重放历史命令
            for u in self.api("getUpdates", http_timeout=10).get("result", []):
                offset = u["update_id"] + 1
        except Exception:
            pass
        self.send("🤖 Research_agent bot 已上线。发 help 看用法。")
        print("bot 运行中...")
        while True:
            try:
                updates = self.api("getUpdates", offset=offset, timeout=50,  # 长轮询 50s
                                   http_timeout=70)
            except Exception as e:
                print(f"getUpdates 异常: {e}，5s 后重试", file=sys.stderr)
                time.sleep(5)
                continue
            for u in updates.get("result", []):
                offset = u["update_id"] + 1
                msg = u.get("message") or {}
                if str((msg.get("chat") or {}).get("id", "")) != self.chat_id:
                    continue  # 只认主人
                text = msg.get("text", "")
                if not text:
                    continue
                self.spool(text)
                kw = self.waiting_keyword()
                if kw and kw.lower() in text.lower():
                    self.send("（已转给等待中的流水线）")
                    continue
                try:
                    self.handle(text)
                except Exception as e:
                    self.send(f"❌ 处理出错: {e}")


def main():
    cfg = _load()
    if not cfg or not cfg.get("token") or not cfg.get("chat_id"):
        sys.exit("缺 token/chat_id — 先 python3 pipeline/notify.py settoken/chatid")
    if BOT_PID.exists():  # 单例：同一 token 不能有两个 getUpdates 消费者
        try:
            os.kill(int(BOT_PID.read_text().strip()), 0)
            sys.exit("bot 已在运行（logs/bot.pid）。要重启先 kill 它。")
        except (ValueError, ProcessLookupError, PermissionError):
            pass
    fix_path()
    LOGS.mkdir(exist_ok=True)
    BOT_PID.write_text(str(os.getpid()), encoding="utf-8")
    try:
        Bot(cfg).loop()
    finally:
        BOT_PID.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
