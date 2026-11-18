"""today: one page to start the day. Top 10 fresh roles not yet tracked, follow-ups due, pipeline counts."""
import csv
from collections import Counter
from datetime import date

from .dedupe import same_role
from .profile import paths
from .tracker import due, load


def run(profile: str, n: int = 10) -> int:
    p = paths(profile)
    qf = p["data"] / "queue.csv"
    queue = list(csv.DictReader(qf.open(newline=""))) if qf.exists() else []
    tracked = load(profile)
    top = [r for r in queue if not any(same_role(r["company"], r["title"], a["company"], a["role"]) for a in tracked)][:n]
    fu = due(profile)
    counts = Counter(r.get("status", "") for r in tracked)
    md = [f"# Today, {date.today().isoformat()} ({profile})", ""]
    md += ["## Top fresh roles", ""]
    if not top:
        md.append("Queue is empty. Run `discover` then `rank`.")
    for i, r in enumerate(top, 1):
        note = "; ".join(x for x in (r.get("auth_note"), r.get("flags")) if x)
        md.append(f"{i}. **{r['company']}**: [{r['title']}]({r['url']}) ({r.get('location', '')[:40]}), "
                  f"score {r['score']}, fit {r['fit']}%" + (f". {note}" if note else ""))
    md += ["", "## Follow-ups due", ""]
    md += [f"- #{r['id']} {r['company']}: {r['role']} (applied {r.get('applied_date')}, contact {r.get('contact') or 'none'})"
           for r in fu] or ["None."]
    md += ["", "## Pipeline", "", ", ".join(f"{k} {v}" for k, v in counts.items()) or "Nothing tracked yet.", "",
           "## Suggested plan (small batches)", "",
           "1. Pick 3 to 5 roles above. For each: `python -m jobkit tailor --profile NAME --url URL`.",
           "2. Read report.md: honesty PASS, ATS 88 to 97, work-auth note. Edit the cover letter yourself.",
           "3. Apply on the company site yourself, then `python -m jobkit track add ... --status applied`.",
           "4. Send at most a few personal notes by hand. Never bulk-message, never automate LinkedIn.", ""]
    f = p["data"] / "today.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("\n".join(md))
    print("\n".join(md))
    return 0
