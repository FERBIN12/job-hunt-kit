"""Offline tests: work-auth rules, the honesty lock, dedupe, filters, and a full tailor on a local JD."""
from pathlib import Path

import pytest
import yaml

from jobkit import honesty, workauth
from jobkit.dedupe import Ledger, role_key, same_role, url_key
from jobkit.filters import location_ok, title_ok, years_required
from jobkit.profile import ROOT, corpus

FACTS = yaml.safe_load((ROOT / "profile/example/facts.yaml").read_text())
FACTS_TEXT = corpus(FACTS)


# ---------------------------------------------------------------- work authorization

@pytest.mark.parametrize("jd, why", [
    ("Applicants must be a U.S. citizen.", "citizenship"),
    ("This role requires an active security clearance.", "clearance"),
    ("This position is subject to ITAR.", "ITAR"),
    ("Candidates must be U.S. persons as defined by export control regulations.", "export control"),
    ("Must be a permanent resident or green card holder.", "permanent"),
])
def test_f1_blockers(jd, why):
    v = workauth.classify(jd, "f1_opt")
    assert v["verdict"] == "BLOCKED", v
    assert why.lower() in v["reason"].lower()
    assert v["evidence"]


def test_no_sponsorship_does_not_block_f1_opt():
    jd = "We are unable to provide visa sponsorship for this role."
    v = workauth.classify(jd, "f1_opt")
    assert v["verdict"] == "OK"
    assert "OPT" in v["note"]


def test_no_sponsorship_blocks_needs_sponsorship():
    jd = "We are unable to provide visa sponsorship for this role."
    assert workauth.classify(jd, "needs_sponsorship")["verdict"] == "BLOCKED"


def test_citizen_mode_never_blocks():
    assert workauth.classify("Must be a U.S. citizen. Active secret clearance.", "us_citizen_or_pr")["verdict"] == "OK"


def test_silence_is_unknown_and_eeo_is_benign():
    assert workauth.classify("Build APIs in Python. Great team.", "f1_opt")["verdict"] == "UNKNOWN"
    eeo = ("We are an equal opportunity employer and consider all applicants without regard to race, religion, "
           "or citizenship status. We are a good corporate citizen.")
    assert workauth.classify(eeo, "f1_opt")["verdict"] == "UNKNOWN"


def test_blocker_deep_in_long_jd():
    jd = "Build things. " * 300 + "Applicants must be a U.S. citizen."
    assert workauth.classify(jd, "f1_opt")["verdict"] == "BLOCKED"


def test_defense_employer_flag():
    assert workauth.defense_employer("Lockheed Martin")
    assert workauth.defense_employer("Example Bakery") is None


# ---------------------------------------------------------------- honesty lock

def _resume_text():
    lines = [FACTS["contact"]["name"], "EDUCATION", FACTS["education"][0]["degree"], "SKILLS"]
    for label, items in FACTS["skills"].items():
        lines.append(f"{label}: {', '.join(items)}")
    lines.append("EXPERIENCE")
    for e in FACTS["experience"]:
        lines += e["bullets"]
    return "\n".join(lines)


def test_honest_resume_passes():
    assert honesty.check(_resume_text(), FACTS_TEXT) == []


@pytest.mark.parametrize("injected, expect", [
    ("Languages: Python, Java, Kubernetes", "Kubernetes"),
    ("Designed MPC controllers for the fleet.", "MPC"),
    ("Built robotic manipulation pipelines.", "manipulation"),
    ("Cut latency by 37%.", "37%"),
    ("Shipped features in GoLangX and TensorRT.", "TensorRT"),
])
def test_injected_claim_fails(injected, expect):
    problems = honesty.check(_resume_text() + "\n" + injected, FACTS_TEXT)
    assert problems, f"injected '{injected}' was not caught"
    assert any(expect.lower() in p.lower() for p in problems), problems


def test_enforce_raises():
    with pytest.raises(honesty.HonestyError):
        honesty.enforce(_resume_text() + "\nKubernetes", FACTS_TEXT)


def test_allow_list_skips_company_and_title():
    text = "I am applying for the Machine Learning Engineer role at AcmeAI."
    assert honesty.check(text, FACTS_TEXT)
    assert honesty.check(text, FACTS_TEXT, allow=["Machine Learning Engineer", "AcmeAI"]) == []


# ---------------------------------------------------------------- dedupe

def test_url_key_keeps_job_id_drops_tracking():
    assert url_key("https://x.com/jobs/1?utm_source=a&gh_jid=55#top") == "https://x.com/jobs/1?gh_jid=55"
    assert url_key("https://X.com/jobs/1/") == "https://x.com/jobs/1"


def test_same_role_fuzzy():
    assert same_role("Acme Inc.", "Software Engineer, New Grad", "acme", "Software Engineer New Grad 2027")
    assert not same_role("Acme", "Software Engineer", "Other Co", "Software Engineer")
    assert not same_role("Acme", "Software Engineer", "Acme", "Account Executive")


def test_ledger_repost_is_not_new(tmp_path: Path):
    led = Ledger(tmp_path / "seen.json")
    a = {"company": "Acme", "title": "Data Analyst", "url": "https://jobs.example.com/1"}
    led.mark(a, "2026-01-01")
    led.save()
    led2 = Ledger(tmp_path / "seen.json")
    repost = {**a, "url": "https://jobs.example.com/999"}       # new id, same company + title
    assert led2.seen_before(repost, "2026-01-05")
    assert not led2.seen_before(a, "2026-01-01")                # same day is still "new"
    assert role_key("Acme Inc", "Data Analyst") == role_key("ACME", "Data  Analyst")


# ---------------------------------------------------------------- filters

def test_seniority_titles():
    t = {"seniority": "new_grad"}
    assert title_ok("Software Engineer, New Grad", t)[0]
    assert not title_ok("Senior Software Engineer", t)[0]
    assert not title_ok("Software Engineer II", t)[0]
    assert title_ok("Software Engineering Intern", {"seniority": "intern"})[0]
    assert not title_ok("Software Engineer", {"seniority": "intern"})[0]


def test_location_and_years():
    t = {"locations": {"remote_ok": True}}
    assert location_ok("Austin, TX", t)[0]
    assert location_ok("Remote - US", t)[0]
    assert not location_ok("London, UK", t)[0]
    assert years_required("Requirements: 5+ years of experience in Python.") == 5
    assert years_required("Great benefits, founded 10 years ago.") is None


# ---------------------------------------------------------------- end to end (offline)

def test_tailor_local_jd(tmp_path, monkeypatch):
    from jobkit import profile as prof, tailor
    monkeypatch.setattr(prof, "ROOT", tmp_path)
    (tmp_path / "profile").mkdir()
    import shutil
    shutil.copytree(ROOT / "profile/example", tmp_path / "profile/example")
    shutil.copytree(ROOT / "presets", tmp_path / "presets")
    jd = tmp_path / "jd.txt"
    jd.write_text("Requirements:\nPython, Java, SQL, REST APIs, Docker, AWS. Unit tests. Bachelor's in computer science.\n"
                  "Nice to have: Kubernetes, React.\nWe cannot sponsor visas.")
    rc = tailor.run("example", jd_file=str(jd), company="Acme", title="Software Engineer")
    out = tmp_path / "out/example/acme_software-engineer"
    assert rc == 0
    assert (out / "resume.docx").exists() and (out / "cover_letter.md").exists()
    report = (out / "report.md").read_text()
    assert "Honesty check: PASS" in report and "Kubernetes" in report     # Kubernetes reported as GAP, never claimed
    assert "DRAFT" in (out / "cover_letter.md").read_text()
    # the same run with an injected claim must fail
    assert tailor.run("example", jd_file=str(jd), company="Acme", title="Software Engineer",
                      extra_text="\nKubernetes, MPC") == 2
