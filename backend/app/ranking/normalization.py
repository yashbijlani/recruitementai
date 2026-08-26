import re

LOCATION_ALIASES = {"bangalore": "bengaluru", "bengaluru": "bengaluru", "bombay": "mumbai", "new delhi": "delhi"}
POSITION_ALIASES = {
    "machine learning engineer": "software engineer", "machine learning developer": "software engineer",
    "ml engineer": "software engineer", "ai engineer": "software engineer", "ai developer": "software engineer",
    "project manager": "project manager", "software engineer": "software engineer", "data analyst": "data analyst",
    "finance manager": "finance manager", "marketing executive": "marketing executive",
}
INDUSTRY_ALIASES = {"fintech": "banking & finance", "banking": "banking & finance", "it": "technology", "tech": "technology"}


def normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").casefold()).strip()


def normalize_location(value: str | None) -> str:
    text = normalize_text(value)
    return LOCATION_ALIASES.get(text, text)


def normalize_position(value: str | None) -> str:
    text = normalize_text(value)
    return POSITION_ALIASES.get(text, text)


def normalize_industry(value: str | None) -> str:
    text = normalize_text(value)
    return INDUSTRY_ALIASES.get(text, text)


def position_similarity(requested: str, actual: str | None) -> float:
    requested = normalize_position(requested)
    actual = normalize_position(actual)
    if not requested or not actual:
        return 0.0
    if requested == actual:
        return 1.0
    requested_words = set(requested.split())
    actual_words = set(actual.split())
    overlap = len(requested_words & actual_words) / max(len(requested_words), 1)
    return 0.8 if overlap >= 0.5 else 0.0
