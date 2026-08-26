import re
from dataclasses import dataclass, field

from app.ranking.normalization import normalize_industry, normalize_location, normalize_position

KNOWN_INDUSTRIES = ("banking & finance", "banking", "fintech", "healthcare", "technology", "it", "consulting", "energy", "fmcg", "logistics", "manufacturing", "retail", "telecommunications")
KNOWN_POSITIONS = ("project manager", "software engineer", "machine learning engineer", "ml engineer", "ai engineer", "data analyst", "finance manager", "marketing executive", "senior accountant")
KNOWN_SKILLS = ("python", "llm", "pytorch", "fastapi", "sql", "machine learning", "langchain", "langgraph", "ai", "ml")


@dataclass(frozen=True)
class Requirements:
    raw_query: str
    position: str | None = None
    industry: str | None = None
    location: str | None = None
    minimum_experience: float | None = None
    maximum_experience: float | None = None
    maximum_salary: float | None = None
    maximum_notice_period: int | None = None
    required_skills: tuple[str, ...] = field(default_factory=tuple)
    explicit_fields: frozenset[str] = field(default_factory=frozenset)
    unsupported_criteria: tuple[str, ...] = field(default_factory=tuple)


def _salary(match: re.Match[str]) -> float:
    value = float(match.group(1).replace(",", ""))
    return value * 100000 if match.group(2) and match.group(2).casefold() in {"lpa", "lakh", "lakhs"} else value


def parse_requirements(query: str) -> Requirements:
    text = query.strip()
    lowered = text.casefold()
    minimum = maximum_experience = maximum_salary = maximum_notice = None
    explicit: set[str] = set()
    minimum_match = re.search(r"(?:at least|minimum(?: of)?|with)\s+(\d+(?:\.\d+)?)\s*\+?\s*years?", lowered)
    range_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*years?", lowered)
    if range_match:
        minimum, maximum_experience = float(range_match.group(1)), float(range_match.group(2)); explicit.add("experience")
    elif minimum_match:
        minimum = float(minimum_match.group(1)); explicit.add("experience")
    salary_match = re.search(r"(?:under|below|maximum|max|less than)\s*(?:₹|rs\.?\s*)?(\d+(?:\.\d+)?)\s*(lpa|lakh|lakhs)?", lowered)
    if salary_match:
        maximum_salary = _salary(salary_match); explicit.add("salary")
    notice_match = re.search(r"(?:join|available|joining)[^\n,;]*?(?:within|in)\s+(\d+)\s*days?", lowered)
    if not notice_match:
        notice_match = re.search(r"within\s+(\d+)\s*days?", lowered)
    if notice_match:
        maximum_notice = int(notice_match.group(1)); explicit.add("notice")
    location = None
    location_match = re.search(r"(?:in|based in|from|located in)\s+([a-z][a-z ]+?)(?=\s+(?:with|at least|under|below|and|who|that)\b|[,.;]|$)", lowered)
    if location_match:
        location_value = location_match.group(1).strip()
        if "industry" not in location_value:
            location = normalize_location(location_value); explicit.add("location")
    industry = None
    for candidate in KNOWN_INDUSTRIES:
        if re.search(rf"\b{re.escape(candidate)}\b", lowered) or (candidate == "banking & finance" and "banking" in lowered):
            industry = normalize_industry(candidate); explicit.add("industry"); break
    position = None
    for candidate in sorted(KNOWN_POSITIONS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(candidate)}s?\b", lowered):
            position = normalize_position(candidate); explicit.add("position"); break
    skills = tuple(skill for skill in KNOWN_SKILLS if re.search(rf"\b{re.escape(skill)}\b", lowered))
    unsupported = tuple(f"required skill '{skill}' (not present in master database)" for skill in skills)
    if "senior" in lowered:
        unsupported += ("seniority level (not a structured master-data field)",)
    return Requirements(raw_query=text, position=position, industry=industry, location=location, minimum_experience=minimum, maximum_experience=maximum_experience, maximum_salary=maximum_salary, maximum_notice_period=maximum_notice, required_skills=skills, explicit_fields=frozenset(explicit), unsupported_criteria=unsupported)
