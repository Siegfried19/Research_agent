"""Tiny HTTP wrapper: timeout, retries, polite delay (uses requests)."""
import time

import requests

DEFAULT_UA = "ResearchAgent/0.1"


class HttpError(Exception):
    def __init__(self, message, status=None, body=None, fatal=False):
        super().__init__(message)
        self.status = status
        self.body = body
        self.fatal = fatal


def sleep(seconds):
    time.sleep(seconds)


def get(url, as_="json", headers=None, timeout=60, retries=2, retry_delay=1.5):
    """GET with retries. 429/5xx are retried; other 4xx are fatal (no retry)."""
    hdrs = {"User-Agent": DEFAULT_UA}
    if headers:
        hdrs.update(headers)
    last_err = None
    for attempt in range(retries + 1):
        try:
            res = requests.get(url, headers=hdrs, timeout=timeout, allow_redirects=True)
            if res.status_code == 429 or res.status_code >= 500:
                raise HttpError(f"HTTP {res.status_code}", status=res.status_code)
            if not res.ok:
                raise HttpError(
                    f"HTTP {res.status_code} {url}",
                    status=res.status_code,
                    body=res.text[:300],
                    fatal=(400 <= res.status_code < 500 and res.status_code != 429),
                )
            return res.json() if as_ == "json" else res.text
        except HttpError as e:
            last_err = e
            if e.fatal:
                break
            if attempt < retries:
                time.sleep(retry_delay * (attempt + 1))
        except requests.RequestException as e:
            last_err = HttpError(str(e))
            if attempt < retries:
                time.sleep(retry_delay * (attempt + 1))
    raise last_err


def get_json(url, **kw):
    return get(url, as_="json", **kw)


def get_text(url, **kw):
    return get(url, as_="text", **kw)


def download_pdf(url, dest, ua=DEFAULT_UA, timeout=60):
    """Download a PDF to `dest`. Raises if the response isn't a real PDF
    (e.g. a publisher landing/Cloudflare page). Returns byte length."""
    res = requests.get(url, headers={"User-Agent": ua, "Accept": "application/pdf,*/*"},
                       timeout=timeout, allow_redirects=True)
    if not res.ok:
        raise HttpError(f"HTTP {res.status_code}", status=res.status_code)
    data = res.content
    if data[:5] != b"%PDF-":
        raise HttpError("not a PDF (likely landing page)")
    with open(dest, "wb") as f:
        f.write(data)
    return len(data)
