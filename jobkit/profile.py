"""Load and validate profile/<name>/facts.yaml and targets.yaml (+ optional preset)."""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SENIORITY = ("intern", "new_grad", "early", "mid", "senior")


class ProfileError(SystemExit):
    pass


def paths(name: str) -> dict:
    return {
        "profile": ROOT / "profile" / name,
        "data": ROOT / "data" / name,
        "out": ROOT / "out" / name,
    }


def load_facts(name: str) -> dict:
    p = paths(name)["profile"] / "facts.yaml"
    if not p.exists():
        raise ProfileError(f"no {p}. Copy profile/example/ to profile/{name}/ and edit it (see README).")
    facts = yaml.safe_load(p.read_text()) or {}
    for key in ("contact", "education", "skills"):
        if key not in facts:
            raise ProfileError(f"{p}: missing required section '{key}'")
    if not facts["contact"].get("name"):
        raise ProfileError(f"{p}: contact.name is required")
    return facts


def load_targets(name: str) -> dict:
    p = paths(name)["profile"] / "targets.yaml"
    if not p.exists():
        raise ProfileError(f"no {p}. Copy profile/example/targets.yaml and edit it.")
    t = yaml.safe_load(p.read_text()) or {}
    preset = t.get("preset")
    if preset:
        pp = ROOT / "presets" / f"{preset}.yaml"
        if not pp.exists():
            raise ProfileError(f"preset '{preset}' not found in presets/")
        base = yaml.safe_load(pp.read_text()) or {}
        # profile values win; companies are merged (preset first, then yours)
        merged = {**base, **{k: v for k, v in t.items() if v is not None}}
        merged["companies"] = (base.get("companies") or []) + (t.get("companies") or [])
        merged["keywords"] = list(dict.fromkeys((base.get("keywords") or []) + (t.get("keywords") or [])))
        t = merged
    t.setdefault("seniority", "new_grad")
    t.setdefault("work_auth", "f1_opt")
    t.setdefault("fresh_days", 14)
    t.setdefault("max_years", {"intern": 1, "new_grad": 2, "early": 3, "mid": 7, "senior": 30}.get(t["seniority"], 3))
    t.setdefault("locations", {})
    t.setdefault("company_blocklist", [])
    if t["seniority"] not in SENIORITY:
        raise ProfileError(f"targets.yaml seniority must be one of {SENIORITY}")
    for key in ("title_include", "title_exclude"):
        for rx in t.get(key) or []:
            try:
                re.compile(rx)
            except re.error as e:
                raise ProfileError(f"targets.yaml {key}: bad regex {rx!r}: {e}")
    return t


def corpus(facts: dict) -> str:
    """Every string in facts.yaml, joined: the evidence the honesty check allows."""
    out = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, (list, dict)) and not str(k).islower():
                    out.append(str(k))          # your own group labels ("Tools & Cloud") print on the resume
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif o is not None:
            out.append(str(o))
    walk(facts)
    return "\n".join(out)
