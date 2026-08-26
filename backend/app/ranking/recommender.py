from sqlalchemy.orm import Session

from app.ranking.query_parser import Requirements, parse_requirements
from app.ranking.scoring import ScoreResult, score_candidate
from app.services.candidates import candidate_query
from app.schemas import SearchRequest


def _retrieve(session: Session, requirements: Requirements):
    filters = SearchRequest(
        position=requirements.position,
        industry=requirements.industry,
        location=requirements.location,
        minimum_experience=requirements.minimum_experience,
        maximum_salary=requirements.maximum_salary,
        maximum_notice_period=requirements.maximum_notice_period,
        page=1,
        page_size=100,
    )
    return session.scalars(candidate_query(filters)).unique().all()


def recommend(session: Session, query: str, limit: int = 10) -> tuple[Requirements, list[tuple[object, ScoreResult]]]:
    requirements = parse_requirements(query)
    scored = []
    for candidate in _retrieve(session, requirements):
        result = score_candidate(candidate, requirements)
        if result is not None:
            scored.append((candidate, result))
    scored.sort(key=lambda item: (-item[1].overall_score, item[0].name.casefold(), item[0].id))
    return requirements, scored[:limit]


def static_recommend(session: Session, limit: int = 10) -> list[tuple[object, ScoreResult]]:
    candidates = session.scalars(candidate_query()).unique().all()
    scored = []
    for candidate in candidates:
        experience = min(1.0, (candidate.experience_years or 0) / 10)
        screening = 1.0 if (candidate.screening_status or "").casefold() == "pass" else 0.7 if candidate.screening_status else 0.4
        completeness = sum(value is not None for value in (candidate.current_position, candidate.current_company, candidate.industry, candidate.city, candidate.current_salary, candidate.notice_period_days)) / 6
        breakdown = {"position": round(completeness * 100, 1), "experience": round(experience * 100, 1), "industry": 100.0 if candidate.industry else 0.0, "location": 100.0 if candidate.city else 0.0, "salary": 100.0 if candidate.current_salary is not None else 0.0, "notice": 100.0 if candidate.notice_period_days is not None else 0.0}
        overall = round(100 * (0.35 * experience + 0.25 * screening + 0.20 * completeness + 0.20 * (1 if candidate.current_position else 0)), 1)
        matched = ["screening passed"] if screening == 1 else []
        matched += [label for label, value in (("experience listed", candidate.experience_years), ("current role listed", candidate.current_position), ("location listed", candidate.city)) if value is not None]
        concerns = ["screening status is not Pass"] if screening < 1 else []
        concerns += ["experience not listed"] if candidate.experience_years is None else []
        result = ScoreResult(overall, breakdown, matched, concerns, "Static ranking based on profile completeness, experience, and screening data." + (" Concerns: " + "; ".join(concerns[:2]) + "." if concerns else ""))
        scored.append((candidate, result))
    scored.sort(key=lambda item: (-item[1].overall_score, item[0].name.casefold(), item[0].id))
    return scored[:limit]
