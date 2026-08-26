from types import SimpleNamespace

from app.ranking.query_parser import parse_requirements
from app.ranking.scoring import score_candidate


def candidate(**values):
    defaults = {"current_position": "Software Engineer", "position_applied_for": None, "industry": "Technology", "city": "Bengaluru", "experience_years": 4.0, "current_salary": 1200000, "notice_period_days": 15}
    defaults.update(values)
    return SimpleNamespace(**defaults)


def test_parser_normalizes_realistic_query():
    requirements = parse_requirements("Find AI engineers with at least 3 years experience in Bangalore under 15 LPA")
    assert requirements.position == "software engineer"
    assert requirements.minimum_experience == 3
    assert requirements.location == "bengaluru"
    assert requirements.maximum_salary == 1500000
    assert "ai" in requirements.required_skills
    assert any("required skill 'ai'" in item for item in requirements.unsupported_criteria)


def test_exact_position_and_experience_score():
    result = score_candidate(candidate(), parse_requirements("Software Engineer with 3+ years in Bengaluru"))
    assert result is not None
    assert result.breakdown["position"] == 100
    assert result.breakdown["experience"] == 100
    assert result.overall_score == 100


def test_wrong_position_is_hard_filtered():
    result = score_candidate(candidate(current_position="Project Manager"), parse_requirements("Software Engineer with 3+ years"))
    assert result is None


def test_below_minimum_experience_is_hard_filtered():
    result = score_candidate(candidate(experience_years=2), parse_requirements("Software Engineer with at least 3 years"))
    assert result is None


def test_salary_and_notice_are_scored_and_missing_criteria_are_omitted():
    requirements = parse_requirements("Software Engineer under 15 LPA, join within 30 days")
    result = score_candidate(candidate(current_salary=1400000, notice_period_days=15), requirements)
    assert result is not None
    assert result.breakdown["salary"] == 100
    assert result.breakdown["notice"] == 100
    assert "industry" not in requirements.explicit_fields
    assert result.overall_score == 100


def test_different_location_is_hard_filtered():
    result = score_candidate(candidate(city="Delhi"), parse_requirements("Software Engineer in Bangalore"))
    assert result is None


def test_repeatability():
    requirements = parse_requirements("Project Manager in IT with 5+ years")
    person = candidate(current_position="Project Manager", industry="Technology", experience_years=7)
    first = score_candidate(person, requirements)
    second = score_candidate(person, requirements)
    assert first == second
