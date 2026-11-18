"""rank: score each fresh role against facts.yaml, flag work-auth blockers and years > max.

score (0-100) = 55 skill fit + 15 target keywords + 10 freshness + 10 seniority hint + 5 preferred location + 5 has JD
skill fit = share of the JD's weighted keywords that your facts.yaml backs.
Blocked roles and roles asking for more years than max_years go to a separate
"flagged" list instead of the queue, with the sentence that triggered it.
"""
import csv
import json
import re
from datetime import date

from . import ats
from .filters import NEWGRAD_HINT, location_bonus, years_required
from .keywords import HARD, has
from .profile import corpus, load_facts, load_targets, paths
from .tracker import load as load_tracker
from .dedupe import same_role
from .workauth import classify, defense_employer

COLS = ["rank", "score", "fit", "company", "title", "location", "posted", "work_auth", "auth_note", "years", "flags", "url"]


def score_row(r: dict, facts_text: str, t: dict) -> dict:
    desc = r.get("desc") or ""
    has_jd = len(desc) >= 300
    jd = f"{r.get('title', '')}\n{desc}" if has_jd else r.get("title", "")
    w = ats.jd_weights(jd)
    fit = sum(v for k, v in w.items() if has(HARD[k], facts_text)) / sum(w.values()) if w else 0.0
    if not has_jd:
        fit *= 0.5          # title-only guess: never let a listing without a JD outrank a real match
    kws = t.get("keywords") or []
    kw = sum(1 for k in kws if re.search(rf"\b{re.escape(k)}\b", jd, re.I)) / min(len(kws), 5) if kws else 0.0
    kw = min(kw, 1.0)
    try:
        age = (date.today() - date.fromisoformat(r.get("posted") or r.get("first_seen"))).days
    except (TypeError, ValueError):
        age = 7
    fresh = max(0.0, 1 - age / max(int(t["fresh_days"]), 1))
    hint = 1.0 if t["seniority"] in ("intern", "new_grad", "early") and NEWGRAD_HINT.search(r.get("title", "")) else 0.0
    if t["seniority"] == "intern" or r.get("src", "").startswith("list:"):
        hint = 1.0
    auth = classify(desc, t.get("work_auth", "f1_opt"))
    yrs = years_required(desc)
    flags = []
    if auth["verdict"] == "BLOCKED":
        flags.append(f"work-auth: {auth['reason']}")
    if yrs is not None and yrs > int(t["max_years"]):
        flags.append(f"asks {yrs}+ years (max {t['max_years']})")
    mode = t.get("work_auth", "f1_opt")
    d = defense_employer(r.get("company", ""), t.get("defense_employers"))
    if d and mode != "us_citizen_or_pr" and t.get("flag_defense_employers", True):
        flags.append(f"work-auth: defense / clearance-heavy employer ({d}); read the JD before applying")
    if not has_jd:
        flags.append("no JD text (tracker listing): open the link")
    score = 55 * fit + 15 * kw + 10 * fresh + 10 * hint + 5 * location_bonus(r.get("location", ""), t) + 5 * has_jd
    return {**r, "score": round(score, 1), "fit": round(100 * fit), "work_auth": auth["verdict"],
            "auth_note": auth["note"] or (auth["reason"] if auth["verdict"] == "BLOCKED" else ""),
            "auth_evidence": auth["evidence"], "years": "" if yrs is None else yrs, "flags": "; ".join(flags),
            "blocked": any(f.startswith(("work-auth", "asks")) for f in flags)}


def run(profile: str) -> int:
    facts_text = corpus(load_facts(profile))
    t = load_targets(profile)
    p = paths(profile)
    src = p["data"] / "roles.jsonl"
    if not src.exists():
        raise SystemExit("no roles yet: run `python -m jobkit discover --profile NAME` first")
    rows = [json.loads(l) for l in src.read_text().splitlines() if l.strip()]
    tracked = load_tracker(profile)
    rows = [r for r in rows if not any(same_role(r["company"], r["title"], a["company"], a["role"]) for a in tracked)]
    scored = sorted((score_row(r, facts_text, t) for r in rows), key=lambda r: -r["score"])
    queue = [r for r in scored if not r["blocked"]]
    flagged = [r for r in scored if r["blocked"]]
    for i, r in enumerate(queue, 1):
        r["rank"] = i
    with (p["data"] / "queue.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(queue)
    md = [f"# Queue for {profile}, {date.today().isoformat()}", "",
          f"{len(queue)} roles ranked, {len(flagged)} flagged. work_auth: {t.get('work_auth')}, seniority: {t['seniority']}, "
          f"max years: {t['max_years']}.", "",
          "| # | score | fit | company | title | location | posted | auth | notes |", "|---|---|---|---|---|---|---|---|---|"]
    for r in queue[:50]:
        note = "; ".join(x for x in (r["auth_note"], r["flags"]) if x)
        md.append(f"| {r['rank']} | {r['score']} | {r['fit']}% | {r['company']} | [{r['title']}]({r['url']}) | "
                  f"{r.get('location', '')[:40]} | {r.get('posted', '')} | {r['work_auth']} | {note} |")
    if flagged:
        md += ["", "## Flagged (not queued). Check the evidence; a regex can misread a JD.", ""]
        for r in flagged[:40]:
            md.append(f"- {r['company']}: [{r['title']}]({r['url']}): {r['flags']}"
                      + (f' ("{r["auth_evidence"][:140]}")' if r.get("auth_evidence") and "work-auth" in r["flags"] else ""))
    (p["data"] / "queue.md").write_text("\n".join(md) + "\n")
    print(f"ranked {len(queue)} roles, flagged {len(flagged)} -> {p['data'] / 'queue.md'}")
    for r in queue[:5]:
        print(f"  {r['score']:5.1f}  fit {r['fit']:3d}%  {r['company']}: {r['title']}")
    return 0
