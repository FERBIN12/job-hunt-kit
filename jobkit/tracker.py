"""track: a plain CSV of roles you are pursuing. You record what YOU did; jobkit never applies."""
import csv
from datetime import date, timedelta

from .profile import paths

COLS = ["id", "added", "company", "role", "url", "status", "applied_date", "follow_up", "contact", "notes"]
STATUSES = ("saved", "tailored", "applied", "interview", "offer", "rejected", "withdrawn", "ghosted")
FOLLOW_UP_DAYS = 7


def _file(profile):
    return paths(profile)["data"] / "tracker.csv"


def load(profile: str) -> list[dict]:
    f = _file(profile)
    if not f.exists():
        return []
    with f.open(newline="") as fh:
        return list(csv.DictReader(fh))


def save(profile: str, rows: list[dict]):
    f = _file(profile)
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def add(profile, company, role, url="", status="saved", contact="", notes="") -> dict:
    if status not in STATUSES:
        raise SystemExit(f"status must be one of {STATUSES}")
    rows = load(profile)
    today = date.today().isoformat()
    row = {"id": str(max([int(r["id"]) for r in rows if r.get("id", "").isdigit()] or [0]) + 1), "added": today,
           "company": company, "role": role, "url": url, "status": status, "contact": contact, "notes": notes,
           "applied_date": today if status == "applied" else "",
           "follow_up": (date.today() + timedelta(days=FOLLOW_UP_DAYS)).isoformat() if status == "applied" else ""}
    rows.append(row)
    save(profile, rows)
    return row


def update(profile, row_id, **changes) -> dict:
    rows = load(profile)
    for r in rows:
        if r["id"] == str(row_id):
            for k, v in changes.items():
                if v is None:
                    continue
                if k == "status" and v not in STATUSES:
                    raise SystemExit(f"status must be one of {STATUSES}")
                r[k] = v
            if changes.get("status") == "applied" and not r.get("applied_date"):
                r["applied_date"] = date.today().isoformat()
                r["follow_up"] = r.get("follow_up") or (date.today() + timedelta(days=FOLLOW_UP_DAYS)).isoformat()
            save(profile, rows)
            return r
    raise SystemExit(f"no tracker row with id {row_id}")


def due(profile: str) -> list[dict]:
    today = date.today().isoformat()
    return [r for r in load(profile) if r.get("follow_up") and r["follow_up"] <= today
            and r.get("status") in ("applied", "interview")]
