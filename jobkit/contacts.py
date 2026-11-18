"""contacts: find a PUBLISHED email (GitHub public profile only), suggest searches YOU run, draft a short email.

What it does not do: it never guesses addresses from patterns, never uses
data-broker sites, never opens or scrapes LinkedIn, and never sends anything.
The draft is saved to out/<profile>/contacts/ for you to edit and send yourself.
"""
import json
import os
import re
import urllib.parse

from .net import get
from .profile import load_facts, paths

BAD = re.compile(r"noreply|no-reply|users\.noreply\.github|example\.", re.I)


def github_email(name: str, company: str) -> tuple[str | None, str | None, str]:
    """Search GitHub users by full name, keep one whose public profile names the company and shows an email."""
    headers = {"Accept": "application/vnd.github+json"}
    tok = os.environ.get("GITHUB_TOKEN")      # optional, read-only, never written anywhere
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    q = urllib.parse.quote(f'fullname:"{name}"')
    code, body = get(f"https://api.github.com/search/users?q={q}&per_page=5", headers=headers)
    if code != 200:
        return None, None, f"GitHub search http {code} (unauthenticated limit is 10 searches/min)"
    first = company.split()[0].lower()
    for u in json.loads(body).get("items", [])[:5]:
        c2, b2 = get(u["url"], headers=headers)
        if c2 != 200:
            continue
        prof = json.loads(b2)
        where = f"{prof.get('company') or ''} {prof.get('bio') or ''}".lower()
        email = prof.get("email")
        if email and not BAD.search(email) and first in where:
            return email, prof.get("html_url"), "found on a public GitHub profile"
    return None, None, "no public email on a matching GitHub profile"


def queries(company: str, role: str = "") -> list[str]:
    co = f'"{company}"'
    r = f' "{role}"' if role else ""
    return [
        f'{co} ("university recruiter" OR "technical recruiter" OR "talent acquisition") site:linkedin.com/in',
        f'{co}{r} ("engineering manager" OR "hiring manager") site:linkedin.com/in',
        f'{co} alumni of your school: search your school name + {co} on LinkedIn by hand',
        f'{co} engineering blog OR team page (people often list a contact there)',
        f'{co} careers page "contact" OR "recruiting" email',
    ]


def draft(facts: dict, company: str, person: str = "", role: str = "") -> str:
    c = facts["contact"]
    school = (facts.get("education") or [{}])[0]
    proj = (facts.get("projects") or facts.get("experience") or [{}])[0]
    proj_name = proj.get("name") or proj.get("title") or ""
    hello = f"Hi {person.split()[0]}," if person else "Hi [NAME],"
    role_line = f"the {role} role" if role else "an open role on your team"
    return "\n".join([
        f"Subject: {('Question about ' + role) if role else 'Question about roles at ' + company}",
        "", hello, "",
        f"I am {c['name']}, {school.get('degree', '')} at {school.get('school', '')}. "
        f"I came across {role_line} at {company} and it lines up with my work on {proj_name or '[YOUR PROJECT]'}.",
        "",
        "[EDIT ME: one specific, true sentence about why this team or product interests you.]",
        "",
        "If you are the right person, I would be grateful for any advice on the application. If not, could you point me "
        "to whoever is? My resume is attached.",
        "", "Thank you,", c["name"], " | ".join(x for x in (c.get("email"), (c.get("links") or {}).get("linkedin")) if x),
    ])


def run(profile: str, company: str, name: str = "", role: str = "") -> int:
    facts = load_facts(profile)
    out = paths(profile)["out"] / "contacts"
    out.mkdir(parents=True, exist_ok=True)
    lines = [f"# Contacts: {company}", ""]
    if name:
        email, src, why = github_email(name, company)
        lines += [f"## {name}", "", f"- email: {email or 'not found'} ({why})" + (f", source: {src}" if src else ""), ""]
        print(f"{name}: {email or 'no public email found'} ({why})")
    lines += ["## Searches to run yourself (in your own browser)", "",
              "jobkit never opens LinkedIn. Paste these into a search engine, or browse LinkedIn by hand.", ""]
    lines += [f"- `{q}`" for q in queries(company, role)]
    lines += ["", "## Draft email (edit, then send it yourself)", "", "```", draft(facts, company, name, role), "```", ""]
    f = out / f"{re.sub(r'[^a-z0-9]+', '-', company.lower()).strip('-')}.md"
    f.write_text("\n".join(lines))
    print(f"-> {f}")
    return 0
