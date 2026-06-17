"""Tier B full-text fetch (method ④): drive a real logged-in Chrome via opencli to
pull PDFs that free routes (OA/recover/arXiv) couldn't get — paywalled (NYU
OpenAthens) or bot-protected OA (Cloudflare). Fully scripted; the ONLY human step
is clicking a Cloudflare/Duo challenge when one appears (we pause + ping Telegram,
then resume). Idempotent: skips papers already pdf_downloaded.

  python3 pipeline/stages/fetch_tierb.py <topicId>

Hybrid download (proven 2026-06-09):
  B (preferred) — Chrome auto-downloads the PDF (we set always_open_pdf_externally
      + a known download dir on a fresh launch), we watch the dir for the new file.
  A (fallback)  — in-page fetch(location.href) -> base64 over opencli's text channel.
NYU access uses OpenAthens (EZProxy is dead): go.openathens.net/redirector/nyu.edu?url=<doi>
"""
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

# --- path shim: 让 `from lib...` 解析到 pipeline/lib，无论本文件在哪个子目录 ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lib.db import open_db, ROOT, load_config, now_iso
from lib.log import run_log
from lib.slug import file_id
try:
    from lib.notify import notify
except Exception:  # noqa: BLE001
    def notify(_):  # type: ignore
        return False

config = load_config()
TB = config.get("tier_b", {})
PDF_DIR = ROOT / config["paths"]["pdfs"]
DL_DIR = ROOT / "store" / "dl_tmp"
DISPLAY = os.environ.get("DISPLAY_FOR_CHROME", ":1")
UDD = os.environ.get("CHROME_USER_DATA_DIR", str(Path.home() / ".config" / "google-chrome-scrape"))
PROFILE_DIR = os.environ.get("CHROME_PROFILE_DIR", "Profile 2")
SESSION = "tierb"
LOG_FILE = ROOT / "logs" / f"tierb-{datetime.now().strftime('%Y-%m-%d')}.log"
ALIAS = None


def redirector(doi):
    return f"https://go.openathens.net/redirector/nyu.edu?url={quote('https://doi.org/' + doi, safe='')}"


def tlog(msg):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{now_iso()}\t{msg}\n")
    print(msg)


def sh(cmd, args, timeout=120, inp=None):
    try:
        p = subprocess.run([cmd, *args], input=inp, capture_output=True, text=True,
                           encoding="utf-8", timeout=timeout)
        return p.returncode, p.stdout or "", p.stderr or ""
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"


def oc(*args, timeout=120):
    base = ["--profile", ALIAS] if ALIAS else []
    return sh("opencli", [*base, *args], timeout=timeout)


def br(*args, timeout=120):
    return oc("browser", SESSION, *args, timeout=timeout)


def doctor_connected():
    _, out, _ = sh("opencli", ["doctor"], timeout=30)
    return bool(re.search(r"Extension:\s*connected", out, re.I))


def detect_alias():
    global ALIAS
    _, out, _ = sh("opencli", ["profile", "list"], timeout=20)
    m = re.search(r"([A-Za-z0-9]+)\s+[—-]+\s+connected", out)
    ALIAS = m.group(1) if m else None
    return ALIAS


def set_pdf_download_prefs():
    """One-time profile tweak so Chrome DOWNLOADS PDFs (method B) into DL_DIR
    instead of opening them in the viewer. Safe only while Chrome is not running."""
    pref = Path(UDD) / PROFILE_DIR / "Preferences"
    if not pref.exists():
        tlog("  (no Preferences yet; method B may be skipped until first launch)")
        return
    try:
        j = json.loads(pref.read_text(encoding="utf-8"))
        j.setdefault("plugins", {})["always_open_pdf_externally"] = True
        j.setdefault("download", {})
        j["download"]["default_directory"] = str(DL_DIR)
        j["download"]["prompt_for_download"] = False
        j.setdefault("savefile", {})["default_directory"] = str(DL_DIR)
        pref.write_text(json.dumps(j), encoding="utf-8")
        tlog(f"  profile set to auto-download PDFs -> {DL_DIR.relative_to(ROOT)}")
    except Exception as e:  # noqa: BLE001
        tlog(f"  (could not set PDF download prefs: {e})")


def ensure_chrome():
    DL_DIR.mkdir(parents=True, exist_ok=True)
    if doctor_connected():
        detect_alias()
        tlog(f"Chrome bridge already connected (profile {ALIAS}). "
             f"Note: PDF-download pref only applies on a fresh launch; method A covers it otherwise.")
        return
    tlog(f"launching Chrome (user-data-dir={UDD}, {PROFILE_DIR}, DISPLAY={DISPLAY})...")
    sh("pkill", ["-f", f"user-data-dir={UDD}"], timeout=10)
    time.sleep(2)
    set_pdf_download_prefs()
    env = {**os.environ, "DISPLAY": DISPLAY}
    subprocess.Popen(["google-chrome", f"--user-data-dir={UDD}",
                      f"--profile-directory={PROFILE_DIR}", "--no-restore-session"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True, env=env)
    for i in range(20):
        time.sleep(3)
        if doctor_connected():
            detect_alias()
            tlog(f"  bridge connected (profile {ALIAS}, {(i + 1) * 3}s)")
            return
    raise RuntimeError("Chrome bridge did not connect within 60s (is the OpenCLI extension enabled?)")


def close_chrome():
    """整关抓取专用 Chrome(照 Stock_agent close_chrome)。按独立 user-data-dir 匹配:
    日常 Chrome 不带此 --user-data-dir,绝不误伤;独立目录=独立进程树,主进程连子进程
    一并带走。模式不带前导 '--'(否则 pkill 把它当选项解析而一个都不杀)。"""
    sh("pkill", ["-f", f"user-data-dir={UDD}"], timeout=10)


def chrome_lock():
    """独占抓取专用 Chrome 的文件锁(照 Stock_agent):防两个 tierb(或其它抓取任务)
    并发互踩。锁文件放 UDD 里=共用这个 Chrome 实例的任务天然同一把锁;进程退出时
    OS 自动释放,不会死锁。"""
    Path(UDD).mkdir(parents=True, exist_ok=True)
    fp = open(Path(UDD) / "scrape.lock", "w", encoding="utf-8")
    fcntl.flock(fp, fcntl.LOCK_EX)
    return fp


def clean_eval(out):
    s = (out or "").strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    return s


def eval_js(js, timeout=90):
    _, out, _ = br("eval", js, timeout=timeout)
    return clean_eval(out)


def get_state():
    _, out, _ = br("state", timeout=30)
    url = (re.search(r"(?im)^url:\s*(.+)$", out) or [None, ""])
    title = (re.search(r"(?im)^title:\s*(.*)$", out) or [None, ""])
    return {"url": (url[1] or "").strip(), "title": (title[1] or "").strip(), "raw": out}


CHALLENGE_TITLE = re.compile(r"just a moment|attention required|are you (a )?robot|verify you are human|checking your browser", re.I)
CHALLENGE_URL = re.compile(r"duosecurity|shibboleth|/idp/|login\.nyu|wayf|/login(\?|$)|openathens\.net/.*/(login|auth)", re.I)


def is_challenge(st):
    return bool(CHALLENGE_TITLE.search(st["title"])) or bool(CHALLENGE_URL.search(st["url"]))


REMOTE_VIEW_URL = None


def ensure_remote_view():
    """Idempotently start the phone-accessible view of :1 (x11vnc+noVNC over
    Tailscale) and cache its URL, so the challenge can be cleared from a phone.

    MOTHBALLED (2026-06-10, user's call): OFF by default. The remote-view code is
    kept but never activates unless explicitly enabled via config tier_b.remote_view
    = true (or env RESEARCH_REMOTE_VIEW=1). When off, tierb behaves as before — you
    clear challenges at the machine."""
    if not (TB.get("remote_view", False) or os.environ.get("RESEARCH_REMOTE_VIEW") == "1"):
        return ""
    global REMOTE_VIEW_URL
    if REMOTE_VIEW_URL is not None:
        return REMOTE_VIEW_URL
    REMOTE_VIEW_URL = ""
    try:
        out = subprocess.run(["bash", str(ROOT / "pipeline" / "remote_view.sh")],
                             capture_output=True, text=True, timeout=30)
        lines = [l for l in (out.stdout or "").splitlines() if l.startswith("http")]
        if lines:
            REMOTE_VIEW_URL = lines[-1].strip()
    except Exception:  # noqa: BLE001
        pass
    return REMOTE_VIEW_URL


def wait_human(paper, st):
    url = ensure_remote_view()
    link = f"\n📱 手机点这里过验证: {url}" if url else ""
    msg = (f"🔐 Tier B 需要你手动过验证/登录(research agent 在抓「{(paper['title'] or '')[:40]}」)。\n"
           f"请点掉 Cloudflare/Duo,我会自动继续。{link}")
    tlog(f"  CHALLENGE: {st['title'] or st['url']} — pausing for human")
    notify(msg)
    deadline = time.time() + TB.get("human_wait_ms", 300000) / 1000
    while time.time() < deadline:
        time.sleep(4)
        if not is_challenge(get_state()):
            tlog("  challenge cleared, continuing")
            return True
    tlog("  challenge not cleared in time")
    return False


def find_pdf_url(doi):
    # Publisher overrides FIRST: for these, the generic <a> scan finds a link that
    # serves an HTML interstitial instead of the PDF, so go straight to the real one.
    cur0 = get_state()["url"]
    if "wiley.com" in cur0:  # /doi/pdf/ is an interstitial; pdfdirect is the file
        return f"https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}?download=true"
    js = ("(()=>{const abs=u=>u?new URL(u,location.href).href:null;"
          "const meta=document.querySelector('meta[name=\"citation_pdf_url\"]');if(meta&&meta.content)return abs(meta.content);"
          "const sel=['a[href*=\"/pdfft\"]','a[href*=\"/doi/pdf\"]','a[href*=\"/epdf\"]','a[href*=\"pdf\"][href*=\"download\"]','a[href$=\".pdf\"]','a[href*=\"/bitstream\"]','a[href*=\".pdf?\"]'];"
          "for(const s of sel){const a=document.querySelector(s);if(a&&a.getAttribute('href'))return abs(a.getAttribute('href'));}"
          "return null;})()")
    for attempt in range(2):
        url = clean_eval(br("eval", js)[1])
        if url and url != "null":
            return url
        cur = get_state()["url"]
        if "dl.acm.org" in cur:
            return f"https://dl.acm.org/doi/pdf/{doi}"
        m = re.search(r"^(https?://[^/]*ieeexplore[^/]*)(?:/abstract)?/document/(\d+)", cur)
        if m:
            return f"{m.group(1)}/stampPDF/getPDF.jsp?tp=&arnumber={m.group(2)}"
        if attempt == 0:
            time.sleep(5)  # SPA 页面(Xplore/DSpace7)可能还没渲染完,等一轮再试
    return None


def list_dir(d):
    try:
        return set(os.listdir(d))
    except OSError:
        return set()


def wait_for_download(before, timeout=20):
    """Wait for a NEW, complete (.pdf, no .crdownload sibling, size-stable) file in DL_DIR."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(1.5)
        try:
            files = os.listdir(DL_DIR)
        except OSError:
            files = []
        for f in files:
            if f in before or not f.lower().endswith(".pdf") or (f + ".crdownload") in files:
                continue
            p = DL_DIR / f
            s1 = p.stat().st_size
            time.sleep(0.8)
            if p.exists() and p.stat().st_size == s1 and s1 > 1000:
                return p
    return None


def grab_via_fetch(dest):
    probe = eval_js(
        "(async()=>{try{const r=await fetch(location.href,{credentials:'include'});"
        "const b=await r.arrayBuffer();const u=new Uint8Array(b);const head=Array.from(u.slice(0,5));"
        "let s='';const C=8192;for(let i=0;i<u.length;i+=C)s+=String.fromCharCode.apply(null,u.subarray(i,i+C));"
        "window.__pdf=btoa(s);return JSON.stringify({ok:true,type:r.headers.get('content-type'),blen:window.__pdf.length,head});}"
        "catch(e){return JSON.stringify({ok:false,err:String(e)});}})()")
    try:
        meta = json.loads(probe)
    except Exception:
        raise RuntimeError(f"probe parse fail: {probe[:120]}")
    if not meta.get("ok"):
        raise RuntimeError(f"fetch failed: {meta.get('err')}")
    head = meta.get("head") or []
    if "pdf" not in (meta.get("type") or "").lower() or not (len(head) >= 2 and head[0] == 37 and head[1] == 80):
        raise RuntimeError(f"not a PDF (type={meta.get('type')}, head={head})")
    length, ch, b64 = meta["blen"], 1000000, ""
    for i in range(0, length, ch):
        b64 += clean_eval(br("eval", f"window.__pdf.slice({i},{i + ch})")[1]).replace("\n", "")
    import base64
    dest.write_bytes(base64.b64decode(b64))


def grab_pdf(dest, before):
    dl = wait_for_download(before, TB.get("download_wait_ms", 20000) / 1000)
    if dl:
        shutil.move(str(dl), str(dest))
        tlog(f"  [B] browser download -> {dl.name}")
        return
    tlog("  [A] no browser download; falling back to in-page fetch")
    grab_via_fetch(dest)


def verify_pdf(p):
    if not p.exists() or p.stat().st_size < 1000:
        return False
    with p.open("rb") as f:
        if f.read(5) != b"%PDF-":
            return False
    try:
        out = subprocess.run(["pdfinfo", str(p)], capture_output=True, text=True, timeout=20).stdout
        return bool(re.search(r"Pages:\s*[1-9]", out))
    except Exception:
        return False


def fetch_one(conn, r):
    slug = r["slug"] or file_id(r["id"])
    pdf_path = PDF_DIR / (slug + ".pdf")
    tlog(f"\n>>> {(r['title'] or '')[:55]}  [{r['id']}]")

    br("open", redirector(r["id"]), timeout=60)
    time.sleep(6)
    st = get_state()
    if is_challenge(st):
        if not wait_human(r, st):
            return "pdf_failed"
        st = get_state()

    pdf_url = find_pdf_url(r["id"])
    if not pdf_url:
        tlog("  no PDF link found on landing page")
        return "pdf_failed"
    tlog(f"  pdf link: {pdf_url[:90]}")

    before = list_dir(DL_DIR)
    br("open", pdf_url, timeout=60)
    time.sleep(7)
    st = get_state()
    if is_challenge(st):
        if not wait_human(r, st):
            return "pdf_failed"

    try:
        grab_pdf(pdf_path, before)
    except Exception as e:  # noqa: BLE001
        tlog(f"  grab failed: {e}")
        return "pdf_failed"
    if not verify_pdf(pdf_path):
        tlog("  downloaded file failed PDF verification")
        pdf_path.unlink(missing_ok=True)
        return "pdf_failed"

    conn.execute("UPDATE papers SET pdf_path=?, status='pdf_downloaded', pdf_fetched_at=? WHERE id=?",
                 (str(pdf_path.relative_to(ROOT)), now_iso(), r["id"]))
    conn.commit()
    tlog(f"  OK [{pdf_path.stat().st_size // 1024}KB] -> pdf_downloaded")
    return "pdf_downloaded"


def main():
    if len(sys.argv) < 2:
        print("usage: fetch_tierb.py <topicId>", file=sys.stderr)
        sys.exit(1)
    topic_id = sys.argv[1]
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    conn = open_db()
    rows = conn.execute(
        """SELECT p.id, p.title, p.slug, p.status, p.landing_url
             FROM papers p JOIN paper_topic pt ON pt.paper_id=p.id
            WHERE pt.topic_id=? AND p.status IN ('pdf_failed','discovered')
            ORDER BY pt.rank""", (topic_id,)).fetchall()
    if not rows:
        print("Tier B: nothing to fetch (all papers already have full text).")
        conn.close()
        return

    tlog(f"Tier B: {len(rows)} papers need full text. log -> {LOG_FILE.relative_to(ROOT)}")
    lock_fp = chrome_lock()
    try:
        ensure_chrome()
        rv = ensure_remote_view()
        rv_line = f"\n📱 验证时可手机点: {rv}" if rv else ""
        notify(f"📚 Tier B 开始抓 {len(rows)} 篇付费墙全文。遇验证我会喊你。{rv_line}")

        ok = fail = 0
        for r in rows:
            try:
                res = fetch_one(conn, r)
            except Exception as e:  # noqa: BLE001
                tlog(f"  ERROR: {e}")
                res = "pdf_failed"
            if res == "pdf_downloaded":
                ok += 1
            else:
                fail += 1
                conn.execute("UPDATE papers SET status='pdf_failed', pdf_fetched_at=? WHERE id=?", (now_iso(), r["id"]))
                conn.commit()
            time.sleep(TB.get("delay_ms", 4000) / 1000)
        conn.close()
        summary = f"Tier B done: {ok} fetched, {fail} failed (of {len(rows)})"
        tlog(summary)
        run_log(topic_id, f"fetch_tierb: {summary}")
        notify(f"✅ {summary}")
    finally:
        # 无条件整关(照 Stock_agent):它是独立 user-data-dir 的专属实例,文件锁保证
        # 此刻没有并发任务在用;复用来的实例也一并关,根治"残留→永不关闭→越积越多"。
        tlog("closing scrape Chrome (unconditional)...")
        close_chrome()
        fcntl.flock(lock_fp, fcntl.LOCK_UN)
        lock_fp.close()


if __name__ == "__main__":
    main()
