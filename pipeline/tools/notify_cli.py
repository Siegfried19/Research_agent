"""Thin CLI around lib.notify.notify — lets the find orchestrator send Telegram via Bash.
Usage: python3 pipeline/tools/notify_cli.py "message text"
"""
import sys

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.notify import notify

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]).strip()
    if msg:
        notify(msg)
