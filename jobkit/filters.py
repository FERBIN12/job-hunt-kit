"""Title, seniority, location and years-of-experience filters."""
import re

# Built-in seniority title rules, applied on top of your own title_include / title_exclude.
SENIORITY_RULES = {
    "intern": {"include": r"\bintern(ship)?s?\b|\bco-?op\b|apprentice", "exclude": r"\bsenior\b|\bstaff\b|\bprincipal\b|\bmanager\b|\bdirector\b"},
    "new_grad": {"include": None,
                 "exclude": r"\bsenior\b|\bsr\.?\b|\bstaff\b|\bprincipal\b|\blead\b|\bmanager\b|\bdirector\b|\bhead of\b|\bvp\b|"
                            r"\bvice president\b|\barchitect\b|\b(ii|iii|iv|v)\b|\b[2-5]\b(?=\s*$)|\bintern(ship)?\b|\bco-?op\b|\bdistinguished\b|\bfellow\b"},
    "early": {"include": None,
              "exclude": r"\bsenior\b|\bsr\.?\b|\bstaff\b|\bprincipal\b|\bmanager\b|\bdirector\b|\bhead of\b|\bvp\b|\b(iii|iv|v)\b|\bintern(ship)?\b|\bdistinguished\b"},
    "mid": {"include": None,
            "exclude": r"\bprincipal\b|\bdirector\b|\bhead of\b|\bvp\b|\bintern(ship)?\b|\bnew grad\b|\bjunior\b|\bentry[- ]level\b|\bdistinguished\b"},
    "senior": {"include": None, "exclude": r"\bintern(ship)?\b|\bnew grad\b|\bjunior\b|\bentry[- ]level\b|\bassociate\b"},
}
NEWGRAD_HINT = re.compile(r"new (college )?grad|university (grad|graduate|hire)|recent grad|early[- ]career|entry[- ]level|"
                          r"\bjunior\b|\bassociate\b|\b(engineer|developer|scientist|analyst) i\b|\bgraduate\b|rotation", re.I)

STATES = ("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA "
          "RI SC SD TN TX UT VT VA WA WV WI WY DC").split()
STATE_NAMES = ("alabama alaska arizona arkansas california colorado connecticut delaware florida georgia hawaii idaho illinois "
               "indiana iowa kansas kentucky louisiana maine maryland massachusetts michigan minnesota mississippi missouri "
               "montana nebraska nevada ohio oklahoma oregon pennsylvania tennessee texas utah vermont virginia washington "
               "wisconsin wyoming").split() + ["new hampshire", "new jersey", "new mexico", "new york", "north carolina",
                                               "north dakota", "rhode island", "south carolina", "south dakota", "west virginia"]
US_CITIES = r"san francisco|new york|nyc|seattle|austin|boston|chicago|los angeles|denver|atlanta|bay area|silicon valley|" \
            r"mountain view|palo alto|sunnyvale|san jose|pittsburgh|detroit|houston|dallas|miami|portland|san diego|" \
            r"philadelphia|washington,? d\.?c|salt lake|phoenix|raleigh|minneapolis|columbus|nashville"
US_RE = re.compile(r",\s*(" + "|".join(STATES) + r")\b|\b(" + "|".join(STATE_NAMES) + r")\b|united states|\busa?\b|\bu\.s\.|"
                   + US_CITIES, re.I)
NON_US = re.compile(r"canada|toronto|vancouver|montreal|london|united kingdom|\buk\b|india|bengaluru|bangalore|hyderabad|germany|"
                    r"berlin|munich|france|paris|china|shanghai|beijing|singapore|israel|tel aviv|mexico|ireland|dublin|poland|"
                    r"netherlands|amsterdam|japan|tokyo|korea|seoul|australia|sydney|brazil|spain|switzerland|zurich|sweden|"
                    r"taiwan|philippines|argentina|colombia|costa rica|romania|serbia|portugal|lisbon|emea|apac|latam", re.I)
REMOTE = re.compile(r"\bremote\b|anywhere|distributed", re.I)


def title_ok(title: str, targets: dict) -> tuple[bool, str]:
    t = title or ""
    rule = SENIORITY_RULES[targets["seniority"]]
    if rule["exclude"] and re.search(rule["exclude"], t, re.I):
        return False, "seniority"
    if rule["include"] and not re.search(rule["include"], t, re.I):
        return False, "seniority"
    inc = targets.get("title_include") or []
    if inc and not any(re.search(rx, t, re.I) for rx in inc):
        return False, "title"
    if any(re.search(rx, t, re.I) for rx in targets.get("title_exclude") or []):
        return False, "title_exclude"
    return True, ""


def location_ok(loc: str, targets: dict) -> tuple[bool, str]:
    """US-wide by default. Remote counts as US unless it names only a non-US region."""
    locs = targets.get("locations") or {}
    l = loc or ""
    if not l.strip():
        return True, ""                          # unknown location: keep, a human checks
    if locs.get("anywhere"):
        return True, ""
    remote = bool(REMOTE.search(l))
    us = bool(US_RE.search(l))
    non_us = bool(NON_US.search(l))
    if remote and not locs.get("remote_ok", True):
        remote = False
    if us or (remote and not non_us):
        allowed = [s.upper() for s in locs.get("only_states") or []]
        if allowed and not remote:
            if not any(re.search(rf",\s*{s}\b", l) for s in allowed):
                return False, "state"
        return True, ""
    return False, "non_us"


def location_bonus(loc: str, targets: dict) -> float:
    pref = [s.upper() for s in (targets.get("locations") or {}).get("preferred_states") or []]
    if any(re.search(rf",\s*{s}\b", loc or "") for s in pref):
        return 1.0
    for c in (targets.get("locations") or {}).get("preferred_cities") or []:
        if c.lower() in (loc or "").lower():
            return 1.0
    return 0.0


YEARS = re.compile(r"(\d{1,2})\s*\+?\s*(?:-|to|or more)?\s*(?:\d{1,2}\s*\+?\s*)?years?", re.I)


def years_required(desc: str) -> int | None:
    """Smallest 'N years' figure that sits near the word 'experience'. None if the JD gives none."""
    found = []
    for m in YEARS.finditer(desc or ""):
        window = desc[max(0, m.start() - 80): m.end() + 80].lower()
        if "experience" in window and "old" not in window[: 90]:
            n = int(m.group(1))
            if 0 < n <= 25:
                found.append(n)
    return min(found) if found else None
