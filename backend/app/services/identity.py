import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Candidate
from app.schemas import ExtractedCandidate


def normalize(value: str | None) -> str:
    return re.sub(r"\D", "", value or "") if value and any(char.isdigit() for char in value) else " ".join((value or "").casefold().split())


@dataclass
class IdentityMatch:
    candidate: Candidate | None
    confidence: float
    reason: str


def resolve_identity(session: Session, extracted: ExtractedCandidate) -> IdentityMatch:
    if extracted.email:
        candidate = session.scalar(select(Candidate).where(Candidate.email.ilike(extracted.email.strip())))
        if candidate:
            return IdentityMatch(candidate, 0.99, "exact_email")
    if extracted.phone:
        phone = normalize(extracted.phone)
        candidates = session.scalars(select(Candidate).where(Candidate.phone.is_not(None))).all()
        candidate = next((item for item in candidates if normalize(item.phone) == phone), None)
        if candidate:
            return IdentityMatch(candidate, 0.97, "exact_phone")
    if extracted.name:
        candidates = session.scalars(select(Candidate).where(Candidate.name.ilike(extracted.name))).all()
        if len(candidates) == 1:
            return IdentityMatch(candidates[0], 0.75, "unique_name_review")
    return IdentityMatch(None, 0.0, "no_match")
