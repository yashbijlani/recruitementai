from dataclasses import dataclass

from app.models import Candidate
from app.ranking.normalization import normalize_industry, normalize_location, position_similarity
from app.ranking.query_parser import Requirements

WEIGHTS = {"position": 0.25, "experience": 0.25, "industry": 0.15, "location": 0.15, "salary": 0.10, "notice": 0.10}


@dataclass(frozen=True)
class ScoreResult:
    overall_score: float
    breakdown: dict[str, float]
    matched_criteria: list[str]
    concerns: list[str]
    explanation: str


def _experience(candidate: Candidate, requirements: Requirements) -> float:
    if requirements.minimum_experience is None:
        return 1.0
    value = candidate.experience_years or 0
    if value >= requirements.minimum_experience:
        return 1.0
    return max(0.0, value / requirements.minimum_experience)


def _salary(candidate: Candidate, requirements: Requirements) -> float:
    if requirements.maximum_salary is None:
        return 1.0
    if candidate.current_salary is None:
        return 0.5
    if candidate.current_salary <= requirements.maximum_salary:
        return 1.0
    return max(0.0, requirements.maximum_salary / candidate.current_salary)


def _notice(candidate: Candidate, requirements: Requirements) -> float:
    if requirements.maximum_notice_period is None:
        return 1.0
    if candidate.notice_period_days is None:
        return 0.5
    if candidate.notice_period_days <= requirements.maximum_notice_period:
        return 1.0
    return max(0.0, requirements.maximum_notice_period / candidate.notice_period_days)


def score_candidate(candidate: Candidate, requirements: Requirements) -> ScoreResult | None:
    values = {
        "position": position_similarity(requirements.position, candidate.current_position or candidate.position_applied_for) if requirements.position else 1.0,
        "experience": _experience(candidate, requirements),
        "industry": 1.0 if requirements.industry and normalize_industry(candidate.industry) == requirements.industry else 0.0 if requirements.industry else 1.0,
        "location": 1.0 if requirements.location and normalize_location(candidate.city) == requirements.location else 0.0 if requirements.location else 1.0,
        "salary": _salary(candidate, requirements),
        "notice": _notice(candidate, requirements),
    }
    hard_failures = []
    if "position" in requirements.explicit_fields and values["position"] == 0:
        hard_failures.append("position")
    if "experience" in requirements.explicit_fields and requirements.minimum_experience is not None and (candidate.experience_years or 0) < requirements.minimum_experience:
        hard_failures.append("minimum experience")
    if "location" in requirements.explicit_fields and values["location"] == 0:
        hard_failures.append("location")
    if "salary" in requirements.explicit_fields and candidate.current_salary is not None and values["salary"] == 0:
        hard_failures.append("salary")
    if "notice" in requirements.explicit_fields and candidate.notice_period_days is not None and values["notice"] == 0:
        hard_failures.append("notice period")
    if hard_failures:
        return None
    active = [key for key in WEIGHTS if key in requirements.explicit_fields or key == "position" and requirements.position]
    if not active:
        active = ["position", "experience", "industry", "location", "salary", "notice"]
    total_weight = sum(WEIGHTS[key] for key in active)
    weighted = {key: round(values[key] * 100, 1) for key in values}
    overall = round(sum(values[key] * WEIGHTS[key] for key in active) / total_weight * 100, 1)
    matched, concerns = [], list(requirements.unsupported_criteria)
    labels = {"position": "requested position", "experience": "minimum experience", "industry": "industry", "location": "location", "salary": "salary range", "notice": "notice period"}
    for key in active:
        if values[key] >= 0.8: matched.append(labels[key])
        elif values[key] < 0.8: concerns.append(f"{labels[key]} is not a strong match")
    details = ", ".join(matched[:3]) if matched else "the available profile fields"
    explanation = ("Strong match" if overall >= 80 else "Good match" if overall >= 60 else "Partial match") + f" based on {details}."
    if concerns:
        explanation += " Concerns: " + "; ".join(concerns[:2]) + "."
    return ScoreResult(overall, weighted, matched, concerns, explanation)
