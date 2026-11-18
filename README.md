# job-hunt-kit

A prep-only job hunt kit you run on your own laptop, with or without a coding agent
(Claude Code, Codex CLI, Cursor, Aider, Gemini CLI, or just a shell).

It finds fresh roles on public company job boards, ranks them against your real background,
flags work-authorization blockers, tailors a resume and a cover-letter draft per role from a
facts file you control, and drafts short outreach emails. **You** review everything, apply and
send. The Python package is `jobkit`.

## What it does

- **discover**: pulls company job boards (Greenhouse, Lever, Ashby public APIs) and, for interns and
  new grads, community new-grad / internship lists on GitHub. Filters by title, seniority and US
  location, keeps only roles you have not seen before, and dedupes against your tracker.
- **rank**: scores each role by how much of the JD your facts back, freshness, your keywords and
  location; moves roles with work-auth blockers or too many required years to a flagged list,
  quoting the sentence that triggered it.
- **tailor**: per role, builds `resume.docx` + `resume.pdf`, a `cover_letter.md` DRAFT, an ATS score
  report and an honesty check result.
- **contacts**: looks up an email a person published on their public GitHub profile, prints searches
  for you to run by hand, and drafts a short email for you to edit.
- **track** and **today**: a plain CSV tracker and a one-page daily plan with follow-ups due.

## What it will NOT do, and why

| It never... | Why |
|---|---|
| submits applications | You must read what goes out under your name. Automated submits send wrong answers. |
| sends email or messages | Outreach only works when it is personal and you stand behind it. |
| scrapes or automates LinkedIn | It breaks LinkedIn's terms and gets accounts restricted. Use LinkedIn by hand. |
| stores passwords, cookies or tokens | Nothing here needs a login. |
| invents skills or numbers | See "The honesty lock" below. A resume claim you cannot defend costs you the interview. |

It only calls public, documented endpoints, with a generic User-Agent, a pause between requests
and a few parallel workers. Run discovery a few times a day at most.

## Install

Python 3.10 or newer.

```
git clone <this repo> job-hunt-kit && cd job-hunt-kit
python3 -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest -q                       # optional: everything should pass
```

PDF output needs one of:
- **LibreOffice** (Linux / macOS / Windows): `sudo apt install libreoffice-writer`, `brew install --cask libreoffice`,
  or the installer from libreoffice.org. jobkit finds `soffice` on your PATH.
- **docx2pdf** with Microsoft Word installed (Windows / macOS): `pip install docx2pdf`.

Without either you still get `resume.docx`; export it to PDF from Word or Google Docs.
`pdftotext` / `pdfinfo` (poppler-utils) are optional; with them jobkit scores the delivered PDF and
checks it fits one page.

## Quick start with your agent

Open your agent in this folder and paste:

> Read AGENTS.md and follow it. Then help me set up my profile from my resume at
> `<path/to/resume.pdf>` (I am looking for `<field>` roles, `<seniority>`, work authorization
> `<us_citizen_or_pr | f1_opt | needs_sponsorship | other>`), and find jobs for today.

The agent will draft `facts.yaml` from your resume, then go through it with you line by line.

## Set up your profile by hand

```
python -m jobkit init --profile yourname --preset software    # or data_ml, engineering, robotics_embedded
```

This copies `profile/example/` to `profile/yourname/` (gitignored). Then:

1. **facts.yaml**: replace the fake "Alex Example" with your real contact info, education, skills,
   experience bullets, projects and any extras. Write only what is true and what you can explain in
   an interview. If an agent drafted it from your resume, **verify every line yourself**.
2. **targets.yaml**: pick a preset, your seniority, work_auth, locations, keywords, any companies to
   add and any to block. Every option is commented in the example.

### seniority

| value | effect |
|---|---|
| `intern` | only intern / co-op / apprentice titles; pulls internship lists |
| `new_grad` | drops Senior, Staff, Lead, Manager, II/III titles; pulls new-grad lists |
| `early` | 0 to 3 years; drops Senior / Staff / Principal / III+ |
| `mid` | drops intern, new grad, junior, principal, director |
| `senior` | drops intern, new grad, junior, entry level |

`max_years` (default by seniority) flags roles whose JD asks for more experience.

### work_auth

| value | who | blocks |
|---|---|---|
| `us_citizen_or_pr` | US citizens, green card holders | nothing |
| `f1_opt` (default) | F-1 students on OPT / STEM OPT | US citizenship, security clearance, ITAR / export control, "US person", green card. **"No sponsorship" does not block**: OPT needs no sponsorship. It is noted, because H-1B later would. |
| `needs_sponsorship` | needs H-1B or similar now | everything above, plus "no sponsorship" |
| `other` | anything else | citizenship, clearance and US-person rules only |

A JD that says nothing is reported as UNKNOWN, never as OK. Roles at defense and clearance-heavy
employers are flagged for every mode except `us_citizen_or_pr` (configurable). This is a text
reader, not legal advice: check with your school's international office or an attorney.

### Presets

| preset | fields | companies |
|---|---|---|
| `software` | backend, frontend, full stack, mobile, cloud, SRE | 36 |
| `data_ml` | data science, data engineering, analytics, ML, applied AI | 30 |
| `engineering` | mechanical, electrical, industrial, manufacturing, civil / construction, energy | 30 |
| `robotics_embedded` | robotics, autonomy, controls, perception, embedded, firmware | 30 |

Every board was verified live when the preset was written; `python -m jobkit.verify_boards` rechecks
them. Civil and construction firms rarely use these boards, so add your own targets. No defense or
ITAR-focused companies are included.

To add a company: find its careers page. If the job links look like `boards.greenhouse.io/<slug>`,
`job-boards.greenhouse.io/<slug>`, `jobs.lever.co/<slug>` or `jobs.ashbyhq.com/<slug>`, add
`{name: Acme, board: greenhouse, slug: <slug>}` under `companies:` in your targets.yaml.

## Daily workflow (20 to 40 minutes)

```
python -m jobkit discover --profile yourname     # fresh roles -> data/yourname/roles.csv
python -m jobkit rank --profile yourname         # -> data/yourname/queue.md
python -m jobkit today --profile yourname        # top 10 + follow-ups due
```

For each of the 3 to 5 roles you choose:

```
python -m jobkit tailor --profile yourname --url <posting URL>
```

1. Open `out/yourname/<company>_<role>/report.md`: ATS band, GAP keywords, work-auth verdict, honesty result.
2. Edit `cover_letter.md` (fill the EDIT ME line). Run `python -m jobkit check --profile yourname <file>`.
3. Apply on the company's own site. Then:
   `python -m jobkit track add --profile yourname --company Acme --role "Data Analyst" --url <url> --status applied`
4. Optional: `python -m jobkit contacts --profile yourname --company Acme --role "Data Analyst"`, then send a
   short personal note yourself.

Small daily batches beat big sweeps: each application gets real attention, and you never look like a bot
to any site.

## Commands

| command | what it does | output |
|---|---|---|
| `init --profile N [--preset P]` | copy the example profile | `profile/N/` |
| `discover --profile N [--limit-companies K] [--all] [--no-lists]` | pull, filter, fresh-only, dedupe | `data/N/roles.csv`, `roles.jsonl`, `seen.json` |
| `rank --profile N` | score vs facts, flag blockers | `data/N/queue.csv`, `queue.md` |
| `tailor --profile N --url URL` or `--jd FILE --company C --title T` | tailored resume + letter + reports | `out/N/<company>_<role>/` |
| `check --profile N FILE [--allow TEXT]` | honesty lock on any edited .docx / .pdf / .md | PASS or a list of claims |
| `track add/list/update --profile N ...` | your application tracker | `data/N/tracker.csv` |
| `contacts --profile N --company C [--name "Full Name"] [--role R]` | public email lookup, searches, draft | `out/N/contacts/<company>.md` |
| `today --profile N [-n 10]` | one-page plan | `data/N/today.md` |

`tailor --url` understands Greenhouse, Lever and Ashby links (and company pages with `?gh_jid=`). For any
other site, save the JD text to a file and use `--jd`.

## The honesty lock

`facts.yaml` is the only source of truth. Tailoring may only **select**, **reorder** and lightly
rephrase what is already there. After rendering, jobkit re-reads the DOCX/PDF and the cover letter and
fails the run (exit code 2) if it finds:

1. a known skill keyword (from `jobkit/keywords.py`, about 200 terms across fields) not in facts.yaml,
2. a tech-looking term (acronym, CamelCase, `C++`, `k8s` style) not in facts.yaml, or
3. a number or percentage not in facts.yaml.

Run `check` after you or an agent edit a draft. Keywords the JD wants that you lack are listed as GAP:
they are never added. If one is really true for you, add it to facts.yaml first, then re-tailor.

ATS bands: below 88 LOW (real gaps), 88 to 97 OK (target), 98 to 100 STUFFED (reads as keyword
stuffing to a human). A low score on an honest resume is useful information about fit.

## FAQ

**Is this allowed by the job sites?** It reads the public job-board feeds companies publish for their
own careers pages, plus public GitHub files. It does not log in anywhere. Still, respect each site's
terms and keep usage light.

**Why no LinkedIn?** Automating LinkedIn violates its terms and gets accounts restricted. Use it by
hand; `contacts` gives you searches to run.

**Discover found zero roles.** Check `BROKEN` lines (a wrong slug), loosen `title_include`, raise
`fresh_days`, or run with `--all` once (it ignores the seen ledger).

**Can I use this outside the US?** The location filter is US-first. Set `locations: {anywhere: true}`;
work-auth rules are US specific.

**The work-auth verdict looks wrong.** It is a regex reader. The evidence sentence is always shown;
trust the JD over the tool, and open an issue with the sentence.

**Can my agent apply for me?** No. AGENTS.md forbids it and the kit has no code for it.

## Disclaimer

No guarantee of results, accuracy or fitness for any purpose. Job data comes from third-party public
feeds and can be stale or wrong. Work-authorization output is not legal advice. You are responsible
for what you submit and send, and for respecting each website's terms of use. Uses public job-board
APIs only.

## License

MIT, see LICENSE. Contributions welcome, see CONTRIBUTING.md.
