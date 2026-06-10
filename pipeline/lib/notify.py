"""Telegram notification + simple two-way control for the pipeline.

Config: config/telegram.json (gitignored) = {"token": "...", "chat_id": "..."}
notify() pushes once; wait_for_reply() only polls while a run is blocked
waiting for the user (e.g. after a Cloudflare/Duo prompt).

Optional daemon: pipeline/bot.py (chat relay to claude -p). While it runs it
owns getUpdates (Telegram allows one consumer per token), so wait_for_reply()
switches to reading the bot's message spool (logs/bot_inbox.jsonl) instead.
"""
import json
import os
import time

import requests

from .db import ROOT

CFG = ROOT / "config" / "telegram.json"
BOT_PID = ROOT / "logs" / "bot.pid"
BOT_INBOX = ROOT / "logs" / "bot_inbox.jsonl"
BOT_WAIT = ROOT / "logs" / "bot_wait.json"


def _bot_alive():
    try:
        os.kill(int(BOT_PID.read_text(encoding="utf-8").strip()), 0)
        return True
    except Exception:
        return False


def _load():
    try:
        return json.loads(CFG.read_text(encoding="utf-8"))
    except Exception:
        return None


def _api(token, method):
    return f"https://api.telegram.org/bot{token}/{method}"


def notify(text):
    """Send a message. No-op (prints) if Telegram isn't configured yet."""
    c = _load()
    if not c or not c.get("token") or not c.get("chat_id"):
        print("[notify:offline]", text)
        return False
    try:
        res = requests.post(_api(c["token"], "sendMessage"),
                            json={"chat_id": c["chat_id"], "text": text}, timeout=20)
        return res.ok
    except Exception as e:
        print("[notify:error]", e, "::", text)
        return False


def fetch_chat_id(token=None):
    t = token or (_load() or {}).get("token")
    if not t:
        raise RuntimeError("no token")
    d = requests.get(_api(t, "getUpdates"), timeout=20).json()
    msgs = [u["message"] for u in (d.get("result") or []) if u.get("message")]
    if not msgs:
        return None
    last = msgs[-1]
    chat = last.get("chat") or {}
    return {"chat_id": chat.get("id"), "from": chat.get("username") or chat.get("first_name")}


def _wait_via_inbox(keyword, timeout, poll):
    """bot.py is polling getUpdates for us — watch its spool file instead."""
    BOT_WAIT.write_text(json.dumps({"keyword": keyword, "ts": time.time()}),
                        encoding="utf-8")
    pos = BOT_INBOX.stat().st_size if BOT_INBOX.exists() else 0
    deadline = time.time() + timeout
    try:
        while time.time() < deadline:
            if not _bot_alive():
                return wait_for_reply(keyword, max(1, int(deadline - time.time())), poll)
            if BOT_INBOX.exists() and BOT_INBOX.stat().st_size > pos:
                with BOT_INBOX.open("r", encoding="utf-8") as f:
                    f.seek(pos)
                    chunk = f.read()
                    pos = f.tell()
                for line in chunk.splitlines():
                    try:
                        if keyword.lower() in json.loads(line).get("text", "").lower():
                            return True
                    except Exception:
                        pass
            time.sleep(poll)
        return False
    finally:
        BOT_WAIT.unlink(missing_ok=True)


def wait_for_reply(keyword, timeout=600, poll=3):
    """Block until the user sends a message containing `keyword` (case-insensitive)."""
    c = _load()
    if not c or not c.get("token"):
        return False
    if _bot_alive():
        return _wait_via_inbox(keyword, timeout, poll)
    offset = 0
    deadline = time.time() + timeout
    try:
        init = requests.get(_api(c["token"], "getUpdates"), timeout=25).json()
        ids = [u["update_id"] for u in (init.get("result") or [])]
        if ids:
            offset = max(ids) + 1
    except Exception:
        pass
    while time.time() < deadline:
        try:
            res = requests.get(_api(c["token"], "getUpdates"),
                               params={"offset": offset, "timeout": 20}, timeout=30).json()
            for u in res.get("result") or []:
                offset = u["update_id"] + 1
                txt = ((u.get("message") or {}).get("text") or "")
                if keyword.lower() in txt.lower():
                    return True
        except Exception:
            time.sleep(poll)
    return False
