"""Telegram notification + simple two-way control for the pipeline.

Config: config/telegram.json (gitignored) = {"token": "...", "chat_id": "..."}
No daemon — notify() pushes once; wait_for_reply() only polls while a run is
blocked waiting for the user (e.g. after a Cloudflare/Duo prompt).
"""
import json
import time

import requests

from .db import ROOT

CFG = ROOT / "config" / "telegram.json"


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


def wait_for_reply(keyword, timeout=600, poll=3):
    """Block until the user sends a message containing `keyword` (case-insensitive)."""
    c = _load()
    if not c or not c.get("token"):
        return False
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
