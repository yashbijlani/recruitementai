import re

from app.schemas import ExtractedCandidate

EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)")


def _section(text: str, names: tuple[str, ...]) -> str:
    pattern = r"(?:^|\n)\s*(?:" + "|".join(names) + r")\s*:?\s*\n(.*?)(?=\n\s*[A-Z][A-Za-z /&-]{2,30}\s*:?\s*\n|\Z)"
    match = re.search(pattern, text, re.I | re.S)
    return match.group(1).strip() if match else ""


def extract_structured_candidate(text: str) -> ExtractedCandidate:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    email = EMAIL.search(text)
    phone = PHONE.search(text)
    skills_text = _section(text, ("skills", "technical skills", "core skills"))
    education_text = _section(text, ("education", "academic background"))
    experience_match = re.search(r"(?:over\s+|about\s+|total\s+)?(\d+(?:\.\d+)?)\+?\s+years?\s+(?:of\s+)?experience", text, re.I)
    skill_items = [item.strip(" -•") for item in re.split(r"[,|;/]", skills_text) if item.strip(" -•")]
    education = [item.strip(" -•") for item in education_text.splitlines() if item.strip(" -•")]
    name = next((line for line in lines[:8] if not EMAIL.search(line) and not PHONE.search(line) and len(line.split()) <= 6), None)
    return ExtractedCandidate(name=name, email=email.group(0) if email else None, phone=phone.group(0).strip() if phone else None, experience_years=float(experience_match.group(1)) if experience_match else None, skills=skill_items, education=[{"qualification": item} for item in education], provenance={"name": "document_text" if name else "missing", "email": "document_text" if email else "missing", "skills": "document_section" if skill_items else "missing"})