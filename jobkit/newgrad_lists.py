"""Community-maintained new-grad / internship trackers on GitHub (public raw files).

Used only when seniority is intern or new_grad. These lists carry no job
description, so their rows rank on title and company only until you tailor.

  SimplifyJobs/New-Grad-Positions   structured listings.json (new grad)
  SimplifyJobs/Summer2026-Internships  structured listings.json (intern)

Lists move and rename every season. If a URL 404s, update LISTS below.
"""
import json
import time
from datetime import datetime, timezone

from .net import get

LISTS = {
    "new_grad": ["https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json"],
    "intern": ["https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/.github/scripts/listings.json"],
}


def pull(seniority: str, max_age_days: int = 30) -> tuple[list[dict], list[str]]:
    rows, errors = [], []
    cutoff = time.time() - max_age_days * 86400
    for url in LISTS.get(seniority, []):
        code, body = get(url)
        if code != 200:
            errors.append(f"{url}: http {code}")
            continue
        try:
            items = json.loads(body)
        except ValueError:
            errors.append(f"{url}: unparseable json")
            continue
        for x in items:
            if not x.get("active") or not x.get("is_visible", True):
                continue
            ts = x.get("date_posted") or 0
            if ts < cutoff:
                continue
            spons = x.get("sponsorship") or ""
            rows.append({
                "company": (x.get("company_name") or "").strip(), "title": (x.get("title") or "").strip(),
                "location": "; ".join(x.get("locations") or []), "url": (x.get("url") or "").split("?utm")[0],
                "posted": datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat(),
                # the list's own sponsorship note feeds the work-auth reader
                "desc": f"Listed on a community {seniority.replace('_', ' ')} tracker. Category: "
                        f"{x.get('category', '')}. Sponsorship note: {spons}.",
                "src": "list:simplify",
            })
    return rows, errors
