from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Candidate, CandidateEducation, CandidateSkill
from app.schemas import CandidateCreate, CandidateUpdate, SearchRequest


def candidate_query(filters: SearchRequest | None = None):
    query = select(Candidate).options(selectinload(Candidate.skills), selectinload(Candidate.education))
    if not filters:
        return query
    if filters.position:
        value = f"%{filters.position.casefold()}%"
        query = query.where(or_(Candidate.current_position.ilike(value), Candidate.position_applied_for.ilike(value)))
    if filters.industry:
        query = query.where(Candidate.industry.ilike(f"%{filters.industry}%"))
    if filters.location:
        query = query.where(Candidate.city.ilike(f"%{filters.location}%"))
    if filters.minimum_experience is not None:
        query = query.where(Candidate.experience_years >= filters.minimum_experience)
    if filters.maximum_salary is not None:
        query = query.where(or_(Candidate.expected_salary.is_(None), Candidate.expected_salary <= filters.maximum_salary))
    if filters.maximum_notice_period is not None:
        query = query.where(or_(Candidate.notice_period_days.is_(None), Candidate.notice_period_days <= filters.maximum_notice_period))
    if filters.screening_status:
        query = query.where(Candidate.screening_status.ilike(f"%{filters.screening_status}%"))
    if filters.current_company:
        query = query.where(Candidate.current_company.ilike(f"%{filters.current_company}%"))
    if filters.query:
        term = f"%{filters.query}%"
        query = query.where(or_(Candidate.name.ilike(term), Candidate.current_position.ilike(term), Candidate.position_applied_for.ilike(term), Candidate.industry.ilike(term), Candidate.city.ilike(term), Candidate.current_company.ilike(term), Candidate.email.ilike(term)))
    if filters.education:
        query = query.join(Candidate.education).where(CandidateEducation.qualification.ilike(f"%{filters.education}%"))
    if filters.skills:
        for skill in filters.skills:
            query = query.where(Candidate.skills.any(CandidateSkill.skill.ilike(f"%{skill}%")))
    return query


def apply_candidate_data(candidate: Candidate, data: CandidateCreate | CandidateUpdate) -> None:
    values = data.model_dump(exclude_unset=True, exclude={"skills", "education"})
    for field, value in values.items():
        if value is not None:
            setattr(candidate, field, value)
    if "skills" in data.model_fields_set:
        candidate.skills.clear()
        candidate.skills.extend(CandidateSkill(skill=skill.strip(), source="manual") for skill in data.skills if skill.strip())
    if "education" in data.model_fields_set:
        candidate.education.clear()
        candidate.education.extend(CandidateEducation(qualification=item.strip()) for item in data.education if item.strip())


def get_or_create_demo_organization(session: Session):
    from app.models import Organization
    organization = session.scalar(select(Organization).limit(1))
    if not organization:
        organization = Organization(name="Demo Recruitment")
        session.add(organization)
        session.flush()
    return organization