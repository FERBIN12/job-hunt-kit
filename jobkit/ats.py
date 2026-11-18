"""ATS match score for one resume text against one JD, modelled on common match-rate tools.

Score (0-100) = 60 hard skills + 10 job title + 10 education + 8 soft skills + 12 format.

Bands:
  LOW      below 88: real gaps; the role may not fit, or your facts.yaml is missing true skills
  OK       88 to 97: the target
  STUFFED  98 to 100: reads as keyword stuffing to a human reviewer; jobkit never aims here

Every keyword the JD wants that the resume lacks is classed against facts.yaml:
  ADD  facts.yaml backs it, so a different selection could show it truthfully
  GAP  no evidence in facts.yaml; NEVER add it to chase the score
"""
import re

from .keywords import HARD, LIGHT, SOFT, has

REQ_HDR = r"(requirements|qualifications|what you('ll)? (need|bring)|you (have|bring|are)|must have|basic|minimum|about you)"
PREF_HDR = r"(preferred|nice to have|bonus|plus|ideally|desired)"
DEGREES = {"phd": r"ph\.?d|doctor", "ms": r"master|\bm\.?s\.?\b|\bmsc\b|graduate degree",
           "bs": r"bachelor|\bb\.?s\.?\b|\bbsc\b|\bb\.?e\.?\b|\bb\.?tech\b|degree"}
FIELDS = r"computer science|engineering|mathematics|statistics|physics|data science|information|science|technical field|related"
TITLE_STOP = {"new", "grad", "i", "ii", "and", "the", "of", "level", "early", "career", "entry", "2026", "2027", "-", "us",
              "remote", "senior", "junior", "associate", "intern", "internship", "summer", "fall", "spring"}
LOW_MAX, OK_MAX = 88, 97


def clean_jd(s: str) -> str:
    s = re.sub(r"<br\s*/?>|</p>|</li>", "\n", s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"&nbsp;|&amp;", " ", s)


def jd_weights(jd: str) -> dict:
    """keyword -> weight: required section 1.0, preferred 0.5, elsewhere 0.75; +0.25 if said 3+ times."""
    mode, w = 0.75, {}
    for line in clean_jd(jd).splitlines():
        short = len(line.strip()) < 70
        if short and re.search(PREF_HDR, line, re.I):
            mode = 0.5
        elif short and re.search(REQ_HDR, line, re.I):
            mode = 1.0
        for k, rx in HARD.items():
            if has(rx, line):
                w[k] = max(w.get(k, 0), mode)
    for k in list(w):
        if len(re.findall(HARD[k], jd, re.I)) >= 3:
            w[k] += 0.25
        if k in LIGHT:
            w[k] = min(w[k], 0.5)
    return w


def band(total: float) -> str:
    return "LOW" if total < LOW_MAX else "OK" if total <= OK_MAX else "STUFFED"


def score(jd: str, resume: str, facts_text: str, title: str = "") -> dict:
    w = jd_weights(jd)
    layout = resume
    flat = re.sub(r"\s+", " ", re.sub(r"-\s*\n\s*", "-", resume))
    hit = {k: v for k, v in w.items() if has(HARD[k], flat)}
    miss = {k: v for k, v in w.items() if k not in hit}
    add = sorted([k for k in miss if has(HARD[k], facts_text)], key=lambda k: -miss[k])
    gap = sorted([k for k in miss if k not in add], key=lambda k: -miss[k])
    hard = sum(hit.values()) / sum(w.values()) if w else 1.0

    words = [x for x in re.findall(r"[a-z0-9+#]+", (title or "").lower()) if x not in TITLE_STOP]
    t = sum(1 for x in words if re.search(rf"\b{re.escape(x)}", flat, re.I)) / len(words) if words else 1.0

    need = next((d for d in ("phd", "ms", "bs") if re.search(rf"({DEGREES[d]}).{{0,60}}({FIELDS})", jd, re.I)
                 and not re.search(rf"(preferred|plus|bonus)[^.]{{0,40}}({DEGREES[d]})", jd, re.I)), None)
    if need is None:
        need = "bs" if re.search(rf"({DEGREES['bs']}).{{0,60}}({FIELDS})", jd, re.I) else None
    have = "phd" if has(DEGREES["phd"], flat) else "ms" if has(DEGREES["ms"], flat) else "bs" if has(DEGREES["bs"], flat) else None
    rank = {None: 0, "bs": 1, "ms": 2, "phd": 3}
    edu = 1.0 if need is None or rank[have] >= rank[need] else 0.5

    sw = {k for k, rx in SOFT.items() if has(rx, jd)}
    s_hit = {k for k in sw if has(SOFT[k], flat)}
    soft = len(s_hit) / len(sw) if sw else 1.0

    checks = {
        "parsed": len(flat) > 800,
        "email": has(r"[\w.+-]+@[\w-]+\.[\w.]+", flat),
        "phone": has(r"\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}", flat),
        "sections": all(re.search(rf"^\s*({s})\s*$", layout, re.M | re.I) for s in ("EDUCATION", "SKILLS", "EXPERIENCE|PROJECTS")),
        "no_long_dashes": "\u2014" not in flat and "\u2013" not in flat,
        "length": 200 <= len(flat.split()) <= 1100,
    }
    fmt = sum(checks.values()) / len(checks)
    total = 60 * hard + 10 * t + 10 * edu + 8 * soft + 12 * fmt
    return {
        "score": round(total, 1), "band": band(total), "hard": round(100 * hard), "title": round(100 * t),
        "education": round(100 * edu), "soft": round(100 * soft), "format": round(100 * fmt),
        "format_fail": [k for k, v in checks.items() if not v], "matched": sorted(hit, key=lambda k: -hit[k]),
        "add": add, "gap": gap, "missing_soft": sorted(sw - s_hit),
    }
