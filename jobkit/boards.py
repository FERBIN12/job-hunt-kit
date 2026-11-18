"""Public job board APIs: Greenhouse, Lever, Ashby.

These are the feeds companies publish for their own careers pages. They need no
login and no API key. A 404 means the board slug is WRONG (a config bug), not
"no openings", so the two are reported apart.

Each posting is normalised to:
  {company, title, location, url, posted (YYYY-MM-DD or ""), desc, src}
"""
import html
import json
import re
import time

from .net import get, get_json


def strip_html(s: str) -> str:
    s = html.unescape(s or "")
    s = re.sub(r"<br\s*/?>|</p>|</li>|</h\d>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()


def _load(url):
    code, body = get(url)
    if code == 404:
        return None, "404 bad board slug"
    if code != 200:
        return None, f"http {code}"
    try:
        return json.loads(body), None
    except json.JSONDecodeError:
        return None, "unparseable json"


def greenhouse(slug: str, name: str = "") -> tuple[list[dict], str | None]:
    data, err = _load(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
    if err:
        return [], err
    return [{
        "company": name or slug, "title": j.get("title", ""),
        "location": (j.get("location") or {}).get("name", ""),
        "url": j.get("absolute_url", ""), "desc": strip_html(j.get("content", "")),
        # Greenhouse exposes first_published on newer boards; updated_at is the fallback
        "posted": (j.get("first_published") or j.get("updated_at") or "")[:10],
        "src": f"greenhouse:{slug}",
    } for j in (data or {}).get("jobs", [])], None


def lever(slug: str, name: str = "") -> tuple[list[dict], str | None]:
    data, err = _load(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    if err:
        return [], err
    if not isinstance(data, list):
        return [], "unexpected shape (not a list)"
    out = []
    for p in data:
        body = (p.get("descriptionPlain") or strip_html(p.get("description", ""))) + "\n" + "\n".join(
            f"{l.get('text', '')}\n{strip_html(l.get('content', ''))}" for l in p.get("lists", []))
        out.append({
            "company": name or slug, "title": p.get("text", ""),
            "location": (p.get("categories") or {}).get("location", "") or "",
            "url": p.get("hostedUrl", ""), "desc": body.strip(),
            "posted": time.strftime("%Y-%m-%d", time.gmtime((p.get("createdAt") or 0) / 1000)) if p.get("createdAt") else "",
            "src": f"lever:{slug}",
        })
    return out, None


def ashby(slug: str, name: str = "") -> tuple[list[dict], str | None]:
    """Ashby slugs are often hyphenated company names (e.g. 'acme-robotics')."""
    data, err = _load(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    if err:
        return [], err
    jobs = data.get("jobs", []) if isinstance(data, dict) else data
    out = []
    for j in jobs or []:
        if j.get("isListed") is False:          # hidden on the board: a human cannot see it either
            continue
        loc = j.get("location", "") or ""
        if j.get("isRemote") and "remote" not in loc.lower():
            loc = f"{loc} (Remote)".strip()
        out.append({
            "company": name or slug, "title": j.get("title", ""), "location": loc,
            "url": j.get("jobUrl") or j.get("applyUrl", ""),
            "desc": j.get("descriptionPlain") or strip_html(j.get("descriptionHtml", "")),
            "posted": (j.get("publishedAt") or "")[:10], "src": f"ashby:{slug}",
        })
    return out, None


FETCHERS = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby}


def fetch_job(url: str) -> dict:
    """One posting from its public URL -> {company, title, desc, url}. Raises ValueError if unknown."""
    m = re.search(r"jobs\.ashbyhq\.com/([^/?#]+)/([0-9a-f-]{36})", url)
    if m:
        for j in get_json(f"https://api.ashbyhq.com/posting-api/job-board/{m[1]}").get("jobs", []):
            if j.get("id") == m[2]:
                return {"company": m[1], "title": j["title"], "url": url,
                        "desc": j.get("descriptionPlain") or strip_html(j.get("descriptionHtml", ""))}
        raise ValueError(f"Ashby posting {m[2]} is not on the {m[1]} board (closed?)")
    m = re.search(r"greenhouse\.io/(?:embed/job_app\?for=)?([^/?&#]+)/jobs/(\d+)", url) or \
        re.search(r"greenhouse\.io/embed/job_app\?for=([^&#]+).*?token=(\d+)", url)
    if m:
        j = get_json(f"https://boards-api.greenhouse.io/v1/boards/{m[1]}/jobs/{m[2]}")
        return {"company": m[1], "title": j["title"], "url": url, "desc": strip_html(j.get("content", ""))}
    m = re.search(r"gh_jid=(\d+)", url)
    if m:
        board = re.search(r"//(?:www\.|careers\.|jobs\.)?([a-z0-9-]+)\.", url)[1]
        j = get_json(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{m[1]}")
        return {"company": board, "title": j["title"], "url": url, "desc": strip_html(j.get("content", ""))}
    m = re.search(r"jobs\.lever\.co/([^/?#]+)/([0-9a-f-]{36})", url)
    if m:
        j = get_json(f"https://api.lever.co/v0/postings/{m[1]}/{m[2]}")
        body = (j.get("descriptionPlain") or "") + "\n" + "\n".join(
            f"{l.get('text', '')}\n{strip_html(l.get('content', ''))}" for l in j.get("lists", []))
        return {"company": m[1], "title": j["text"], "url": url, "desc": body.strip()}
    raise ValueError("not a Greenhouse / Lever / Ashby URL: save the JD text to a file and use "
                     "--jd FILE --company NAME --title TITLE")
