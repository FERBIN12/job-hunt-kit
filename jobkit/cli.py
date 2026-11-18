"""python -m jobkit <command> --profile NAME

Commands:
  init      copy profile/example/ to profile/NAME/ to start your own profile
  discover  pull company boards (+ new-grad / intern lists), filter, keep fresh roles -> data/NAME/roles.csv
  rank      score fresh roles vs facts.yaml, flag work-auth blockers and years -> data/NAME/queue.csv + queue.md
  tailor    one role -> out/NAME/<company>_<role>/ resume.docx/.pdf, cover_letter.md, report.md
  check     honesty-check an edited draft (.docx/.pdf/.md) against facts.yaml
  track     add | list | update rows in data/NAME/tracker.csv (you record what you did)
  contacts  public-email lookup + searches for you to run + a draft email
  today     one-page plan: top 10 fresh roles, follow-ups due

jobkit prepares. You review, apply and send. It never submits, never sends, never automates LinkedIn.
"""
import argparse
import shutil
import sys

from .profile import ROOT, paths


def _init(a):
    dst = paths(a.profile)["profile"]
    if dst.exists():
        raise SystemExit(f"{dst} already exists")
    shutil.copytree(ROOT / "profile" / "example", dst)
    if a.preset:
        t = dst / "targets.yaml"
        t.write_text(t.read_text().replace("preset: software", f"preset: {a.preset}", 1))
    print(f"created {dst}. Now replace everything in facts.yaml with YOUR real facts (see README), "
          f"then edit targets.yaml.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m jobkit", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def cmd(name, **kw):
        s = sub.add_parser(name, **kw)
        s.add_argument("--profile", required=True, help="folder name under profile/")
        return s

    s = cmd("init", help="start a new profile from the example")
    s.add_argument("--preset", choices=["software", "data_ml", "engineering", "robotics_embedded"])
    s = cmd("discover", help="find fresh roles")
    s.add_argument("--limit-companies", type=int, help="only the first N companies (quick test)")
    s.add_argument("--all", action="store_true", help="ignore the seen ledger (show already-seen roles again)")
    s.add_argument("--no-lists", action="store_true", help="skip community new-grad / intern lists")
    cmd("rank", help="rank fresh roles")
    s = cmd("tailor", help="tailor resume + cover letter for one role")
    s.add_argument("--url")
    s.add_argument("--jd", help="file with the JD text (any site)")
    s.add_argument("--company")
    s.add_argument("--title")
    s = cmd("check", help="honesty-check an edited draft")
    s.add_argument("file")
    s.add_argument("--allow", action="append", default=[], help="text to skip, e.g. the company name (repeatable)")
    s = cmd("track", help="tracker")
    s.add_argument("action", choices=["add", "list", "update"])
    s.add_argument("--id")
    s.add_argument("--company")
    s.add_argument("--role")
    s.add_argument("--url", default="")
    s.add_argument("--status")
    s.add_argument("--contact")
    s.add_argument("--follow-up", dest="follow_up", help="YYYY-MM-DD")
    s.add_argument("--notes")
    s = cmd("contacts", help="public email lookup + draft")
    s.add_argument("--company", required=True)
    s.add_argument("--name", default="", help="a person's full name to look up")
    s.add_argument("--role", default="")
    s = cmd("today", help="daily one-pager")
    s.add_argument("-n", type=int, default=10)
    a = ap.parse_args(argv)

    if a.cmd == "init":
        return _init(a)
    if a.cmd == "discover":
        from . import discover
        return discover.run(a.profile, a.limit_companies, use_ledger=not a.all, use_lists=not a.no_lists)
    if a.cmd == "rank":
        from . import rank
        return rank.run(a.profile)
    if a.cmd == "tailor":
        from . import tailor
        return tailor.run(a.profile, a.url, a.jd, a.company, a.title)
    if a.cmd == "check":
        from . import tailor
        return tailor.check_file(a.profile, a.file, a.allow)
    if a.cmd == "track":
        from . import tracker
        if a.action == "add":
            if not (a.company and a.role):
                raise SystemExit("track add needs --company and --role")
            r = tracker.add(a.profile, a.company, a.role, a.url, a.status or "saved", a.contact or "", a.notes or "")
            print(f"added #{r['id']} {r['company']}: {r['role']} [{r['status']}]")
        elif a.action == "update":
            if not a.id:
                raise SystemExit("track update needs --id")
            r = tracker.update(a.profile, a.id, status=a.status, contact=a.contact, follow_up=a.follow_up, notes=a.notes)
            print(f"updated #{r['id']} {r['company']}: {r['role']} [{r['status']}]")
        else:
            rows = tracker.load(a.profile)
            for r in rows:
                print(f"#{r['id']:>3} {r['status']:<10} {r['company']}: {r['role']}  applied {r.get('applied_date') or '-'}"
                      f"  follow-up {r.get('follow_up') or '-'}")
            if not rows:
                print("tracker is empty")
        return 0
    if a.cmd == "contacts":
        from . import contacts
        return contacts.run(a.profile, a.company, a.name, a.role)
    if a.cmd == "today":
        from . import today
        return today.run(a.profile, a.n)
    return 1


if __name__ == "__main__":
    sys.exit(main())
