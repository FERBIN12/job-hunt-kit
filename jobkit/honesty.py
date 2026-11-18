"""The honesty lock. Every claim in a tailored resume or cover letter must trace to facts.yaml.

Tailoring may SELECT, REORDER and lightly rephrase existing facts. It must never
add a skill, tool, number or claim that facts.yaml does not contain. This module
fails loudly when it finds one, and it runs on every tailor (and on demand with
`python -m jobkit check`, e.g. after you or an AI assistant edit a draft).

Three checks on the output text, each against the facts.yaml corpus:
  1. keywords  every term from keywords.HARD found in the output must also be found in facts.yaml
  2. tech      tech-looking tokens (acronyms, CamelCase, C++, k8s, ROS2 ...) must appear in facts.yaml
  3. numbers   every number / percentage in the output must appear in facts.yaml

Words that the kit itself writes (section headings, the DRAFT banner, the
company and role you are applying to) are passed in as `allow` and skipped.
"""
import re

from .keywords import HARD, has

SCAFFOLD = {"EDUCATION", "SKILLS", "EXPERIENCE", "PROJECTS", "SUMMARY", "AWARDS", "PUBLICATIONS", "CERTIFICATIONS",
            "LEADERSHIP", "DRAFT", "TECHNICAL", "PROFESSIONAL", "AI", "OK", "USA", "US", "PDF", "GPA", "TODO", "NOTE",
            "ATS", "JD", "PS", "CV", "I", "A", "LLC", "INC", "NA"}
TECH = re.compile(r"(?<![\w@.])(?:[A-Za-z]*[A-Z][a-z0-9]*[A-Z][A-Za-z0-9]*|[A-Za-z]+\d+[A-Za-z0-9]*|[A-Za-z]+[+#]+|\.NET)(?![\w@])")
NUM = re.compile(r"(?<![\w.])\$?\d[\d,]*(?:\.\d+)?%?(?![\w])")
EMAIL_URL = re.compile(r"\S+@\S+|https?://\S+|www\.\S+|\b[\w-]+\.(com|org|io|dev|net|edu|ai)\S*", re.I)


class HonestyError(SystemExit):
    pass


def _norm_num(s: str) -> str:
    return s.replace(",", "").replace("$", "")


def check(output: str, facts_text: str, allow: list[str] | None = None) -> list[str]:
    """Return a list of violations (empty = honest)."""
    allow = [a for a in (allow or []) if a]
    text = EMAIL_URL.sub(" ", output or "")
    for a in allow:
        text = re.sub(re.escape(a), " ", text, flags=re.I)
    facts_low = facts_text.lower()
    facts_nums = {_norm_num(n) for n in NUM.findall(facts_text)}
    facts_nums |= {n.rstrip("%") for n in facts_nums}
    problems = []

    for k, rx in HARD.items():
        if has(rx, text) and not has(rx, facts_text):
            m = re.search(rx, text, re.I)
            problems.append(f"keyword '{k}' (\"{m.group(0)}\") is not in facts.yaml")

    seen = set()
    for tok in TECH.findall(text):
        t = tok.strip()
        if t.upper() in SCAFFOLD or t.lower() in seen or len(t) < 2:
            continue
        seen.add(t.lower())
        if t.lower() not in facts_low:
            problems.append(f"term '{t}' is not in facts.yaml")

    for n in NUM.findall(text):
        k = _norm_num(n)
        if k not in facts_nums and k.rstrip("%") not in facts_nums:
            problems.append(f"number '{n}' is not in facts.yaml")
    return sorted(set(problems))


def enforce(output: str, facts_text: str, allow: list[str] | None = None, what: str = "output"):
    problems = check(output, facts_text, allow)
    if problems:
        msg = [f"HONESTY CHECK FAILED for {what}: {len(problems)} claim(s) not backed by facts.yaml"]
        msg += [f"  - {p}" for p in problems]
        msg += ["Fix: remove the claim, or if it is TRUE, add it to facts.yaml with where it came from, then rerun."]
        raise HonestyError("\n".join(msg))
