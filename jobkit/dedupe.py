"""Dedupe keys and the seen-postings ledger.

A posting is "seen" if its URL OR its company+title pair was pulled before, so a
repost under a new id does not come back as new. Tracker matching is fuzzy
because people spell companies many ways ("Acme Inc", "acme-inc", "ACME").
"""
import json
import os
import re
from pathlib import Path

CO_STOP = {"inc", "llc", "ltd", "corp", "corporation", "co", "company", "the", "technologies", "technology",
           "labs", "group", "holdings", "usa", "us", "hq"}
TITLE_STOP = {"the", "and", "of", "a", "i", "ii", "iii", "us", "usa", "remote", "new", "grad", "-", "2026", "2027"}


def url_key(u: str) -> str:
    """Lowercase, drop tracking query strings but keep job-id parameters."""
    u = (u or "").strip().lower()
    if "?" in u:
        base, q = u.split("?", 1)
        keep = [p for p in q.split("&") if re.match(r"(gh_jid|jid|id|job|token|for)=", p)]
        u = base + ("?" + "&".join(keep) if keep else "")
    return u.split("#")[0].rstrip("/")


def co_key(s: str) -> str:
    s = (s or "").lower().replace("_", " ").replace("-", " ")
    s = re.sub(r"\([^)]*\)", " ", s)
    return "".join(t for t in re.findall(r"[a-z0-9]+", s) if t not in CO_STOP)


def role_key(company: str, title: str) -> str:
    return co_key(company)[:12] + "|" + re.sub(r"[^a-z0-9]", "", (title or "").lower())


def title_tokens(s: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9+#]+", (s or "").lower()) if t not in TITLE_STOP}


def same_role(c1, t1, c2, t2) -> bool:
    """Same company (fuzzy) and title tokens overlap by Jaccard >= 0.6 or one contains the other."""
    k1, k2 = co_key(c1), co_key(c2)
    if not k1 or not k2 or not (k1 == k2 or k1.startswith(k2) or k2.startswith(k1)):
        return False
    a, b = title_tokens(t1), title_tokens(t2)
    if not a or not b:
        return False
    return len(a & b) / len(a | b) >= 0.6 or a <= b or b <= a


class Ledger:
    """data/<profile>/seen.json: {"urls": {key: first_seen}, "roles": {key: first_seen}}."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.data = {"urls": {}, "roles": {}}
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text())
            except ValueError:
                raise SystemExit(f"{self.path} is damaged; fix or delete it (deleting makes every posting new again)")

    def seen_before(self, row: dict, today: str) -> bool:
        u, k = url_key(row.get("url")), role_key(row.get("company"), row.get("title"))
        first = [d for d in (self.data["urls"].get(u), self.data["roles"].get(k)) if d]
        return any(d < today for d in first)

    def mark(self, row: dict, today: str):
        u, k = url_key(row.get("url")), role_key(row.get("company"), row.get("title"))
        if u:
            self.data["urls"].setdefault(u, today)
        self.data["roles"].setdefault(k, today)

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data))
        os.replace(tmp, self.path)
