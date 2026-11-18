"""Render a resume plan to DOCX (python-docx) and PDF (LibreOffice, or docx2pdf on Windows/macOS with Word).

Layout: one column, centered header, ruled section headings, right-aligned dates.
ATS-friendly: real text (no images or tables), standard headings, the email
written out as text, no long dashes.
"""
import shutil
import subprocess
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

FONT = "Calibri"
BODY_PT = 10
INK = RGBColor(0, 0, 0)


def _para(doc, before=0, after=1, align=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    if align is not None:
        p.alignment = align
    return p


def _run(p, text, bold=False, italic=False, size=BODY_PT):
    r = p.add_run(text)
    r.bold, r.italic = bold, italic
    r.font.size = Pt(size)
    r.font.name = FONT
    r.font.color.rgb = INK
    return r


def _rule(p):
    ppr = p._p.get_or_add_pPr()
    b = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    for k, v in (("w:val", "single"), ("w:sz", "6"), ("w:space", "1"), ("w:color", "000000")):
        bottom.set(qn(k), v)
    b.append(bottom)
    ppr.append(b)


def _heading(doc, title):
    p = _para(doc, before=5, after=2)
    _run(p, title, bold=True, size=BODY_PT + 1)
    _rule(p)


def _entry(doc, left_bold, left_plain, right):
    p = _para(doc, before=2, after=0)
    p.paragraph_format.tab_stops.add_tab_stop(Inches(7.0), WD_TAB_ALIGNMENT.RIGHT)
    _run(p, left_bold, bold=True)
    if left_plain:
        _run(p, left_plain)
    if right:
        _run(p, f"\t{right}", bold=True)


def _bullet(doc, text):
    p = _para(doc, after=0.5)
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.first_line_indent = Inches(-0.15)
    _run(p, "•  " + text)


def build_docx(plan: dict, path: Path) -> Path:
    doc = Document()
    for s in doc.sections:
        s.top_margin = s.bottom_margin = Inches(0.5)
        s.left_margin = s.right_margin = Inches(0.6)
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(BODY_PT)
    c = plan["contact"]
    p = _para(doc, after=1, align=WD_ALIGN_PARAGRAPH.CENTER)
    _run(p, c["name"], bold=True, size=16)
    line = " | ".join(x for x in (c.get("location"), c.get("email"), c.get("phone")) if x)
    _run(_para(doc, after=0, align=WD_ALIGN_PARAGRAPH.CENTER), line)
    links = " | ".join(str(v) for v in (c.get("links") or {}).values() if v)
    if links:
        _run(_para(doc, after=0, align=WD_ALIGN_PARAGRAPH.CENTER), links)

    if plan.get("summary"):
        _heading(doc, "SUMMARY")
        _run(_para(doc), plan["summary"])

    _heading(doc, "EDUCATION")
    for ed in plan["education"]:
        _entry(doc, ed.get("school", ""), f", {ed['location']}" if ed.get("location") else "", ed.get("dates", ""))
        deg = ed.get("degree", "")
        if ed.get("gpa"):
            deg += f" (GPA {ed['gpa']})"
        _run(_para(doc, after=0), deg, italic=True)
        if ed.get("coursework"):
            _run(_para(doc, after=0), "Coursework: " + ", ".join(ed["coursework"]))

    _heading(doc, "SKILLS")
    for label, items in plan["skills"]:
        p = _para(doc, after=0.5)
        _run(p, f"{label}: ", bold=True)
        _run(p, ", ".join(items))

    for section, key in (("EXPERIENCE", "experience"), ("PROJECTS", "projects")):
        if not plan.get(key):
            continue
        _heading(doc, section)
        for e in plan[key]:
            left = e.get("title") or e.get("name", "")
            org = e.get("org", "")
            _entry(doc, left, f", {org}" if org else "", e.get("dates", ""))
            for b in e["bullets"]:
                _bullet(doc, b)

    for sec in plan.get("extra") or []:
        _heading(doc, sec["heading"].upper())
        for item in sec["items"]:
            _bullet(doc, item)

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    return path


def docx_text(path: Path) -> str:
    return "\n".join(p.text for p in Document(str(path)).paragraphs)


def to_pdf(docx: Path) -> tuple[Path | None, str]:
    """Return (pdf_path or None, how). Tries LibreOffice, then docx2pdf."""
    docx = Path(docx)
    office = shutil.which("soffice") or shutil.which("libreoffice")
    if office:
        r = subprocess.run([office, "--headless", "--convert-to", "pdf", "--outdir", str(docx.parent), str(docx)],
                           capture_output=True, text=True, timeout=180)
        pdf = docx.with_suffix(".pdf")
        if r.returncode == 0 and pdf.exists():
            return pdf, "libreoffice"
    try:
        from docx2pdf import convert  # optional; needs Microsoft Word on Windows/macOS
        pdf = docx.with_suffix(".pdf")
        convert(str(docx), str(pdf))
        if pdf.exists():
            return pdf, "docx2pdf"
    except Exception:  # noqa: BLE001
        pass
    return None, "no PDF converter found (install LibreOffice); the .docx is ready"


def pdf_pages(pdf: Path) -> int | None:
    exe = shutil.which("pdfinfo")
    if not exe or not pdf:
        return None
    r = subprocess.run([exe, str(pdf)], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    return None


def pdf_text(pdf: Path) -> str | None:
    exe = shutil.which("pdftotext")
    if not exe or not pdf:
        return None
    r = subprocess.run([exe, "-layout", str(pdf), "-"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None
