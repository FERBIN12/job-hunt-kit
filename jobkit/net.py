"""Polite HTTP: one generic User-Agent, retries with backoff, a pause between calls.

Only public, documented endpoints are called (company job boards, GitHub's API,
raw GitHub files). No cookies, no logins, no browser automation.
"""
import json
import time
import urllib.error
import urllib.request

from . import USER_AGENT

TIMEOUT = 25
PAUSE = 0.5          # seconds between requests to the same kind of host
_last_call = [0.0]


def get(url: str, attempts: int = 3, headers: dict | None = None) -> tuple[int, str]:
    """Return (status, body). status -1 means a network error after retries.

    A 404 is returned immediately: it means the board slug is wrong, which no
    retry will fix, and it must not be confused with "no openings".
    """
    last = (-1, "no attempt")
    for i in range(attempts):
        wait = PAUSE - (time.time() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.time()
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT * (i + 1)) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:      # rate limited or server trouble: back off
                last = (e.code, "")
                time.sleep(3 * (i + 1))
                continue
            return e.code, ""
        except Exception as e:  # noqa: BLE001
            last = (-1, f"{type(e).__name__}: {e}")
            time.sleep(1.5 * (i + 1))
    return last


def get_json(url: str, headers: dict | None = None):
    code, body = get(url, headers=headers)
    if code != 200:
        raise RuntimeError(f"http {code} for {url}")
    return json.loads(body)
