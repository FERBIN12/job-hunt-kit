"""Read work-authorization statements out of a job description. Never infer them.

Three outcomes per JD:
  BLOCKED  the JD states a requirement your work_auth mode cannot meet
  OK       nothing in the JD blocks you (with a note when it says "no sponsorship")
  UNKNOWN  the JD is silent; silence is common and is NOT treated as permission

work_auth modes (targets.yaml):
  us_citizen_or_pr    no visa filtering at all (clearance roles still flagged for info)
  f1_opt              student on F-1 using OPT / STEM OPT. Blockers: US citizenship,
                      security clearance, ITAR / export control, "US person", green card.
                      "No sponsorship" does NOT block: OPT and STEM OPT need no employer
                      sponsorship. It is noted, because H-1B later would need it.
  needs_sponsorship   needs H-1B (or similar) sponsorship now. Everything f1_opt blocks,
                      plus "no sponsorship" / "must not require sponsorship" IS a blocker.
  other               only hard citizenship / clearance / US-person rules block.

Each verdict carries the exact sentence it came from, so a human can check the call.
"""
import re

CITIZEN_RULES = [
    (r"must be (a )?u\.?s\.? citizen", "US citizenship required"),
    (r"u\.?s\.? citizenship (is )?required", "US citizenship required"),
    (r"(restricted|limited|open) (only )?to u\.?s\.? citizens", "US citizens only"),
    (r"requires? u\.?s\.? citizenship", "US citizenship required"),
    (r"(active|current|ability to obtain|eligib\w+ (for|to obtain))[^.]{0,30}(top secret|ts/sci|secret|security)[^.]{0,10}clearance",
     "security clearance"),
    (r"\b(security|secret|ts/sci) clearance (is )?required", "security clearance"),
    (r"\bitar\b", "ITAR restriction"),
    (r"export[- ]control", "export control (usually requires US person status)"),
    (r"\bu\.?s\.? persons?\b", "US person requirement"),
    (r"(must be|requires?)[^.]{0,20}(permanent resident|green card)", "permanent residency required"),
]
SPONSOR_RULES = [
    (r"\b(not|unable|cannot|can't|do not|don't|won'?t|will not)\b[^.]{0,30}?"
     r"\b(provide|offer|sponsor|sponsoring|support)\b[^.]{0,30}?\b(sponsor\w*|visas?|h-?1b)\b", "no sponsorship"),
    (r"\bsponsorship\b[^.]{0,30}?\b(not|unavailable|cannot)\b", "no sponsorship"),
    (r"no (visa )?sponsorship", "no sponsorship"),
    (r"without (the need for |requiring )?(visa )?sponsorship", "no sponsorship"),
    (r"(not|never) (now or in the future )?require[^.]{0,20}sponsorship", "no sponsorship"),
]
POSITIVE = [
    (r"(will|do|can|we) sponsor", "sponsorship offered"),
    (r"sponsorship (is )?(available|provided|offered)", "sponsorship offered"),
    (r"h-?1b (visa )?sponsorship (is )?(available|offered|provided)", "sponsorship offered"),
    (r"\b(opt|cpt|stem opt)\b[^.]{0,30}(welcome|eligible|accepted|considered)", "OPT/CPT welcome"),
]
BENIGN = [
    r"regardless of[^.]{0,80}citizenship", r"equal (employment )?opportunity[^.]{0,160}",
    r"without regard to[^.]{0,120}", r"corporate citizen", r"citizenship status[^.]{0,40}(protected|discriminat)",
]
# Employers whose US engineering roles are mostly cleared, ITAR or US-person only. Used for rows that
# carry no JD text (community lists) and as an extra flag: a non-citizen should read the JD first.
# Not a judgement of the companies; extend or empty it in targets.yaml (defense_employers: [...]).
DEFENSE_EMPLOYERS = [
    "lockheed", "northrop", "raytheon", "rtx", "l3harris", "general dynamics", "bae systems", "leidos", "saic",
    "booz allen", "peraton", "caci", "anduril", "mitre", "applied physics laboratory", "lincoln laboratory",
    "sandia", "los alamos", "lawrence livermore", "huntington ingalls", "general atomics", "parsons", "mantech",
    "amentum", "spacex", "blue origin", "shield ai", "saronic", "textron", "sierra nevada", "kbr", "elbit",
    "rocket lab", "united launch alliance", "aerojet", "draper", "naval", "air force", "army",
]


def defense_employer(company: str, extra: list[str] | None = None) -> str | None:
    c = (company or "").lower()
    for d in DEFENSE_EMPLOYERS + [x.lower() for x in extra or []]:
        if re.search(rf"\b{re.escape(d)}\b", c):
            return d
    return None


MODES = ("us_citizen_or_pr", "f1_opt", "needs_sponsorship", "other")

ABBREV = re.compile(r"\b(?:u\.s\.a?\.?|e\.g\.|i\.e\.|etc\.|inc\.|ltd\.|vs\.|ph\.d\.|m\.s\.|b\.s\.|dr\.|mr\.|ms\.)", re.I)


def sentences(text: str) -> list[str]:
    """Split on sentence ends without cutting 'U.S. citizen' in half."""
    protected = ABBREV.sub(lambda m: m.group(0).replace(".", "\x00"), text)
    parts = re.split(r"(?<=[.!?])\s+|\n+", protected)
    return [p.replace("\x00", ".").strip() for p in parts if p.strip()]


def _scan(sents, rules):
    for s in sents:
        if any(re.search(b, s) for b in BENIGN):
            continue
        for pat, why in rules:
            if re.search(pat, s):
                return why, s[:220]
    return None, ""


def classify(text: str, mode: str = "f1_opt") -> dict:
    """Return {verdict, reason, evidence, note}. verdict in BLOCKED / OK / UNKNOWN."""
    if mode not in MODES:
        raise ValueError(f"work_auth must be one of {MODES}, got {mode!r}")
    low = (text or "").lower()
    if not low.strip():
        return {"verdict": "UNKNOWN", "reason": "empty job description", "evidence": "", "note": ""}
    sents = sentences(low)
    cit, cit_ev = _scan(sents, CITIZEN_RULES)
    spo, spo_ev = _scan(sents, SPONSOR_RULES)
    pos, pos_ev = _scan(sents, POSITIVE)

    if mode == "us_citizen_or_pr":
        note = f"JD mentions: {cit}" if cit else ""
        return {"verdict": "OK", "reason": "no visa filtering for citizens / permanent residents",
                "evidence": cit_ev, "note": note}
    if mode == "other":
        hard = cit if cit and ("citizen" in cit or "clearance" in cit or "person" in cit) else None
        if hard:
            return {"verdict": "BLOCKED", "reason": hard, "evidence": cit_ev, "note": ""}
    elif cit:
        return {"verdict": "BLOCKED", "reason": cit, "evidence": cit_ev, "note": ""}
    if spo:
        if mode == "needs_sponsorship":
            return {"verdict": "BLOCKED", "reason": spo, "evidence": spo_ev, "note": ""}
        note = ("says no sponsorship: fine on OPT / STEM OPT, but H-1B later would need it"
                if mode == "f1_opt" else "says no sponsorship")
        return {"verdict": "OK", "reason": "no blocker for this work_auth mode", "evidence": spo_ev, "note": note}
    if pos:
        return {"verdict": "OK", "reason": pos, "evidence": pos_ev, "note": ""}
    return {"verdict": "UNKNOWN", "reason": "JD does not state a work-authorization requirement",
            "evidence": "", "note": ""}
