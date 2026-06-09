"""Telegram CLI: set up the bot config, grab chat id, send test messages.
  python3 pipeline/notify.py settoken <BOT_TOKEN>   # save token to config/telegram.json
  python3 pipeline/notify.py chatid                 # read chat id (after you message the bot once)
  python3 pipeline/notify.py test "hello"           # send a test message
"""
import json
import os
import sys

from lib.notify import notify, fetch_chat_id, CFG


def read_cfg():
    try:
        return json.loads(CFG.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_cfg(o):
    CFG.parent.mkdir(parents=True, exist_ok=True)
    CFG.write_text(json.dumps(o, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(CFG, 0o600)


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else None
    arg = args[1] if len(args) > 1 else None
    if cmd == "settoken":
        if not arg:
            print("usage: notify.py settoken <BOT_TOKEN>", file=sys.stderr)
            sys.exit(1)
        c = read_cfg(); c["token"] = arg.strip(); write_cfg(c)
        print("token saved to config/telegram.json (chmod 600). Now message your bot once, then: notify.py chatid")
    elif cmd == "chatid":
        found = fetch_chat_id()
        if not found:
            print("no message found — send any message to your bot first, then retry")
            return
        c = read_cfg(); c["chat_id"] = found["chat_id"]; write_cfg(c)
        print(f"chat_id {found['chat_id']} (from {found['from']}) saved. Telegram ready.")
    elif cmd == "test":
        print("sent" if notify(arg or "Research_agent: test ✅") else "not sent (check config/telegram.json)")
    else:
        print('commands: settoken <token> | chatid | test "<msg>"')


if __name__ == "__main__":
    main()
