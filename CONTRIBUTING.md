# Contributing

Thanks for helping. Keep changes small, tested, and true to the rules in AGENTS.md: prep only,
no LinkedIn automation, no sending or submitting, public endpoints only, no personal data.

## Setup

```
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt pytest
pytest -q
```

## Add or fix a preset company

1. Find the company's board slug from its careers page links
   (`boards.greenhouse.io/<slug>`, `jobs.lever.co/<slug>`, `jobs.ashbyhq.com/<slug>`).
2. Add `{name: ..., board: greenhouse|lever|ashby, slug: ...}` to the right `presets/*.yaml`.
3. Run `python -m jobkit.verify_boards presets/<file>.yaml`. Every line must resolve.
4. No defense, clearance or ITAR-focused employers in presets.

## Add a board source

1. Add a fetcher to `jobkit/boards.py` that returns `(rows, error)`, where each row is
   `{company, title, location, url, posted, desc, src}` and `error` is `None` or a short string
   (keep "404 bad slug" separate from "no openings").
2. Register it in `FETCHERS`, and teach `fetch_job()` its posting URL pattern.
3. Use `jobkit.net.get` (generic User-Agent, retries, pause between calls). Only documented public
   APIs or feeds: no logins, cookies, browser automation or scraping of sites that forbid it.
4. Add an offline test with a small fixture.

## Add keywords for a field

Add `"Name": r"regex"` to `jobkit/keywords.py`. Every keyword is also policed by the honesty lock,
so make the regex specific enough not to match ordinary words.

## Pull requests

- `pytest -q` passes.
- No real names, emails or personal paths in code, tests or examples (use Alex Example / example.com).
- No long dashes in docs; plain words over jargon.
