from app.models import Candidate


def score_candidate(candidate: Candidate, request) -> tuple[float, list[str], list[str]]:
    required = {skill.casefold() for skill in request.skills}
    available = {skill.skill.casefold() for skill in candidate.skills}
    skill_ratio = len(required & available) / len(required) if required else 1.0
    experience_ratio = min((candidate.experience_years or 0) / request.minimum_experience, 1) if request.minimum_experience else 1.0
    role_match = 1.0 if request.position and request.position.casefold() in (candidate.current_position or candidate.position_applied_for or "").casefold() else 0.0 if request.position else 1.0
    industry_match = 1.0 if request.industry and request.industry.casefold() in (candidate.industry or "").casefold() else 0.0 if request.industry else 1.0
    compensation = 1.0 if not request.maximum_salary or not candidate.expected_salary else max(0.0, min(1.0, (request.maximum_salary - candidate.expected_salary) / request.maximum_salary + 0.5))
    score = round(100 * (0.40 * skill_ratio + 0.25 * experience_ratio + 0.15 * role_match + 0.10 * industry_match + 0.10 * compensation), 1)
    reasons = []
    gaps = []
    if required:
        reasons.append(f"{len(required & available)}/{len(required)} required skills matched")
    if candidate.experience_years is not None:
        reasons.append(f"{candidate.experience_years:g} years of experience")
    if role_match:
        reasons.append("Role aligns with the search")
    if industry_match and request.industry:
        reasons.append("Industry aligns with the search")
    if request.maximum_notice_period and (candidate.notice_period_days or 9999) > request.maximum_notice_period:
        gaps.append(f"Notice period exceeds {request.maximum_notice_period} days")
    if required - available:
        gaps.append("Missing: " + ", ".join(sorted(required - available)))
    return score, reasons, gaps
