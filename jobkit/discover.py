"""discover: pull company boards (+ new-grad / intern lists), filter, keep fresh-only, dedupe.

Writes data/<profile>/roles.jsonl (full JD text, for rank) and roles.csv (no JD, for you).
"""
import csv
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

from . import boards, newgrad_lists
from .dedupe import Ledger, same_role
from .filters import location_ok, title_ok
from .profile import load_targets, paths
from .tracker import load as load_tracker

CSV_COLS = ["first_seen", "posted", "company", "title", "location", "url", "src"]


def pull_boards(companies: list[dict], workers: int = 4) -> tuple[list[dict], list[str], list[str]]:
    """Few parallel workers plus a pause per request (net.PAUSE): polite on every board."""
    def one(c):
        fetch = boards.FETCHERS.get(c.get("board"))
        if not fetch:
            return [], f"{c.get('name')}: unknown board '{c.get('board')}'", None
        try:
            posts, err = fetch(c["slug"], c.get("name", ""))
        except Exception as e:  # noqa: BLE001
            posts, err = [], f"{type(e).__name__}: {e}"
        if err:
            return [], f"{c.get('name', c['slug'])} ({c['board']}:{c['slug']}): {err}", None
        return posts, None, (c.get("name", c["slug"]) if not posts else None)

    rows, broken, empty = [], [], []
    with ThreadPoolExecutor(workers) as ex:
        for posts, err, emp in ex.map(one, companies):
            rows += posts
            if err:
                broken.append(err)
            if emp:
                empty.append(emp)
    return rows, broken, empty


def run(profile: str, limit_companies: int | None = None, use_ledger: bool = True, use_lists: bool = True) -> int:
    t = load_targets(profile)
    p = paths(profile)
    p["data"].mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    companies = [c for c in t.get("companies") or [] if c.get("slug")]
    seen_slugs, uniq = set(), []
    for c in companies:
        key = (c.get("board"), c["slug"])
        if key not in seen_slugs:
            seen_slugs.add(key)
            uniq.append(c)
    companies = uniq[:limit_companies] if limit_companies else uniq

    t0 = time.time()
    rows, broken, empty = pull_boards(companies)
    print(f"boards: {len(companies)} companies, {len(rows)} postings in {time.time() - t0:.0f}s")
    if empty:
        print(f"  resolved but no openings: {', '.join(empty)}")
    if broken:
        print(f"  BROKEN ({len(broken)}), fix the slug in targets.yaml or the preset:")
        for b in broken:
            print(f"    {b}")
    if use_lists and t["seniority"] in ("intern", "new_grad") and t.get("newgrad_lists", True):
        lrows, lerr = newgrad_lists.pull(t["seniority"], max_age_days=max(t["fresh_days"], 7))
        print(f"lists: {len(lrows)} {t['seniority']} postings from community trackers")
        for e in lerr:
            print(f"  list error: {e}")
        rows += lrows

    block = {b.lower() for b in t.get("company_blocklist") or []}
    cutoff = (date.today() - timedelta(days=int(t["fresh_days"]))).isoformat()
    ledger = Ledger(p["data"] / "seen.json")
    tracked = load_tracker(profile)
    counts = {k: 0 for k in ("blocklist", "title", "seniority", "title_exclude", "non_us", "state", "stale", "seen", "tracked", "dupe")}
    kept, urls = [], set()
    for r in rows:
        if not r.get("url") or not r.get("title"):
            continue
        was_seen = use_ledger and ledger.seen_before(r, today)
        ledger.mark(r, today)
        if any(b and (b in r["company"].lower() or b in r.get("src", "").lower()) for b in block):
            counts["blocklist"] += 1; continue
        ok, why = title_ok(r["title"], t)
        if not ok:
            counts[why] += 1; continue
        ok, why = location_ok(r.get("location", ""), t)
        if not ok:
            counts[why] += 1; continue
        if r.get("posted") and r["posted"] < cutoff:
            counts["stale"] += 1; continue
        if was_seen:
            counts["seen"] += 1; continue
        if any(same_role(r["company"], r["title"], a["company"], a["role"]) for a in tracked):
            counts["tracked"] += 1; continue
        u = r["url"].split("?")[0].lower()
        if u in urls:
            counts["dupe"] += 1; continue
        urls.add(u)
        r["first_seen"] = today
        r["title"] = re.sub(r"\s*[\u2013\u2014]\s*", ", ", r["title"]).strip()
        r["desc"] = (r.get("desc") or "")[:20000]
        kept.append(r)
    ledger.save()

    # keep earlier fresh finds inside the window, so a missed day loses nothing
    new_count = len(kept)
    old_file = p["data"] / "roles.jsonl"
    if old_file.exists():
        for line in old_file.read_text().splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            u = r.get("url", "").split("?")[0].lower()
            if r.get("first_seen", "") >= cutoff and u not in urls and not any(
                    same_role(r["company"], r["title"], a["company"], a["role"]) for a in tracked):
                urls.add(u)
                kept.append(r)

    (p["data"] / "roles.jsonl").write_text("".join(json.dumps(r) + "\n" for r in kept))
    with (p["data"] / "roles.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(kept)
    dropped = ", ".join(f"{k} {v}" for k, v in counts.items() if v)
    print(f"new today: {new_count} of {len(rows)} pulled; {len(kept)} fresh roles in the {t['fresh_days']}-day window (dropped: {dropped or 'none'})")
    print(f"-> {p['data'] / 'roles.csv'}")
    if not rows:
        print("FAIL: zero postings pulled. Check your network and the companies list.")
        return 1
    return 0
