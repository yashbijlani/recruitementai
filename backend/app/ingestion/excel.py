import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Candidate, CandidateEducation, CandidateSkill, ImportBatch, Organization

ALIASES = {
    "position_applied_for": ["position applied for", "position", "applied position", "which position are you applying for"],
    "industry": ["industry", "industry ?"], "name": ["name", "candidate name", "what is your full name"], "date_of_birth": ["dob", "date of birth"],
    "age": ["age"], "marital_status": ["marital status"], "experience_years": ["experience", "years of experience", "how many years of experience do you have"],
    "application_source": ["application source", "source", "where did you find out about this position"], "education": ["education", "qualification", "education background institution major"],
    "phone": ["phone", "mobile", "phone number"], "email": ["email", "email address"],
    "notice_period_days": ["notice period / earliest joining", "notice period", "earliest joining", "what is the earliest you can join or what is your notice period at your current company"],
    "city": ["city", "location", "current domicile city"], "current_company": ["current company"], "current_position": ["current position", "current position title"],
    "current_salary": ["current salary", "what is your current salary"], "expected_salary": ["expected salary"],
    "english_proficiency": ["english proficiency"], "screening_status": ["screening", "screening status"],
    "cv_filename": ["cv filename", "cv file", "please upload your cv"],
}


def _key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).strip().casefold()).strip()


def _number(value: object) -> float | None:
    if pd.isna(value) or value in (None, ""):
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value).replace(",", ""))
    return float(match.group()) if match else None


def _int(value: object) -> int | None:
    number = _number(value)
    return int(number) if number is not None else None


def _clean(value: object) -> object:
    if value is None or (isinstance(value, float) and pd.isna(value)) or pd.isna(value):
        return None
    return str(value).strip() if isinstance(value, str) else value


def _notice_days(value: object) -> int | None:
    value = _clean(value)
    if value is None:
        return None
    text = str(value).casefold()
    if "immediate" in text or "available" in text:
        return 0
    number = _number(text)
    if number is None:
        return None
    if "week" in text:
        return int(number * 7)
    if "month" in text:
        return int(number * 30)
    return int(number)


def _value(row: dict, field: str) -> object:
    aliases = {_key(alias) for alias in ALIASES[field]}
    for key, value in row.items():
        if _key(key) in aliases:
            return value
    return None


def _stable_id(row: dict) -> str:
    identity = "|".join(str(_value(row, field) or "").strip().casefold() for field in ("name", "email", "phone"))
    return "CAND-" + hashlib.sha256(identity.encode()).hexdigest()[:12].upper()


def import_workbook(session: Session, path: str | Path, organization_name: str = "Demo Recruitment") -> dict[str, int]:
    workbook = Path(path)
    if not workbook.exists():
        raise FileNotFoundError(f"Seed workbook not found: {workbook}. Place the supplied file at this path or pass --file.")
    try:
        frame = pd.read_excel(workbook, sheet_name="Candidates", dtype=object)
    except ValueError as error:
        raise ValueError("The workbook must contain a worksheet named 'Candidates'.") from error
    if frame.empty:
        raise ValueError("The workbook contains no candidate rows.")
    if not any(_key(column) in set(ALIASES["name"]) for column in frame.columns):
        raise ValueError("The workbook must contain a Name or Candidate Name column.")
    organization = session.scalar(select(Organization).where(Organization.name == organization_name))
    if organization is None:
        organization = Organization(name=organization_name)
        session.add(organization)
        session.flush()
    inserted = updated = skipped = errors = 0
    seen: set[str] = set()
    for raw in frame.to_dict(orient="records"):
        name = str(_value(raw, "name") or "").strip()
        if not name:
            skipped += 1
            continue
        candidate_id = _stable_id(raw)
        if candidate_id in seen:
            skipped += 1
            continue
        seen.add(candidate_id)
        candidate = session.get(Candidate, candidate_id)
        fields = {
            "id": candidate_id, "organization_id": organization.id, "name": name,
            "date_of_birth": _clean(_value(raw, "date_of_birth")).date() if hasattr(_clean(_value(raw, "date_of_birth")), "date") else _clean(_value(raw, "date_of_birth")),
            "age": _int(_value(raw, "age")), "marital_status": _clean(_value(raw, "marital_status")),
            "position_applied_for": _clean(_value(raw, "position_applied_for")), "industry": _clean(_value(raw, "industry")),
            "application_source": _clean(_value(raw, "application_source")), "phone": _clean(_value(raw, "phone")),
            "email": _clean(_value(raw, "email")), "notice_period_days": _notice_days(_value(raw, "notice_period_days")),
            "city": _clean(_value(raw, "city")), "current_company": _clean(_value(raw, "current_company")),
            "current_position": _clean(_value(raw, "current_position")), "current_salary": _number(_value(raw, "current_salary")),
            "expected_salary": _number(_value(raw, "expected_salary")), "experience_years": _number(_value(raw, "experience_years")),
            "english_proficiency": _clean(_value(raw, "english_proficiency")), "screening_status": _clean(_value(raw, "screening_status")),
            "original_row": json.dumps({str(k): (v.isoformat() if isinstance(v, (date, datetime)) else None if pd.isna(v) else v) for k, v in raw.items()}, default=str),
        }
        try:
            if candidate is None:
                candidate = Candidate(**fields)
                session.add(candidate)
                inserted += 1
            else:
                for key, value in fields.items():
                    if key != "id":
                        setattr(candidate, key, value)
                updated += 1
            education_value = _value(raw, "education")
            if education_value and not candidate.education:
                for qualification in re.split(r"[,;/|]", str(education_value)):
                    qualification = qualification.strip()
                    if qualification:
                        candidate.education.append(CandidateEducation(qualification=qualification))
        except Exception:
            session.rollback()
            errors += 1
    session.add(ImportBatch(source_filename=workbook.name, row_count=inserted + updated))
    session.commit()
    return {"rows_read": len(frame), "valid_rows": inserted + updated, "inserted": inserted, "updated": updated, "skipped": skipped, "errors": errors}
