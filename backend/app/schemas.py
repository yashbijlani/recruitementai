from pydantic import BaseModel, ConfigDict, Field


class ExtractedEducation(BaseModel):
    qualification: str
    institution: str | None = None


class ExtractedExperience(BaseModel):
    company: str | None = None
    position: str | None = None
    years: float | None = Field(default=None, ge=0)


class ExtractedCandidate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    city: str | None = None
    current_company: str | None = None
    current_position: str | None = None
    experience_years: float | None = Field(default=None, ge=0)
    skills: list[str] = []
    industry: str | None = None
    education: list[ExtractedEducation] = []
    current_salary: float | None = Field(default=None, ge=0)
    expected_salary: float | None = Field(default=None, ge=0)
    notice_period_days: int | None = Field(default=None, ge=0)
    previous_experience: list[ExtractedExperience] = []
    certifications: list[str] = []
    projects: list[str] = []
    provenance: dict[str, str] = {}


class SkillRead(BaseModel):
    skill: str
    model_config = ConfigDict(from_attributes=True)


class CandidateRead(BaseModel):
    id: str
    name: str
    position_applied_for: str | None = None
    current_position: str | None = None
    current_company: str | None = None
    industry: str | None = None
    city: str | None = None
    experience_years: float | None = None
    current_salary: float | None = None
    expected_salary: float | None = None
    notice_period_days: int | None = None
    screening_status: str | None = None
    education: list[str] = []
    email: str | None = None
    phone: str | None = None
    age: int | None = None
    marital_status: str | None = None
    english_proficiency: str | None = None
    skills: list[str] = []
    suitability_score: float | None = None
    score_reasons: list[str] = []
    score_gaps: list[str] = []


class SearchRequest(BaseModel):
    query: str = ""
    position: str | None = None
    industry: str | None = None
    location: str | None = None
    minimum_experience: float | None = Field(default=None, ge=0)
    maximum_salary: float | None = Field(default=None, ge=0)
    maximum_notice_period: int | None = Field(default=None, ge=0)
    education: str | None = None
    screening_status: str | None = None
    current_company: str | None = None
    skills: list[str] = []
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SearchResponse(BaseModel):
    items: list[CandidateRead]
    total: int
    page: int
    page_size: int


class RecommendationRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=50)


class ScoreBreakdown(BaseModel):
    position: float
    experience: float
    industry: float
    location: float
    salary: float
    notice: float


class RecommendationResult(BaseModel):
    rank: int
    candidate_id: str
    candidate: CandidateRead
    overall_score: float
    score_breakdown: ScoreBreakdown
    matched_criteria: list[str]
    concerns: list[str]
    explanation: str


class RecommendationResponse(BaseModel):
    query: str
    parsed_requirements: dict[str, object]
    results: list[RecommendationResult]


class CandidateListResponse(SearchResponse):
    pass


class CandidateCreate(BaseModel):
    name: str
    position_applied_for: str | None = None
    current_position: str | None = None
    current_company: str | None = None
    industry: str | None = None
    city: str | None = None
    experience_years: float | None = Field(default=None, ge=0)
    current_salary: float | None = Field(default=None, ge=0)
    expected_salary: float | None = Field(default=None, ge=0)
    notice_period_days: int | None = Field(default=None, ge=0)
    screening_status: str | None = None
    email: str | None = None
    phone: str | None = None
    skills: list[str] = []
    education: list[str] = []


class CandidateUpdate(CandidateCreate):
    name: str | None = None


class DocumentRead(BaseModel):
    id: str
    filename: str
    document_type: str
    status: str
    extraction_method: str | None = None
    extraction_quality: float | None = None
    extracted_character_count: int | None = None
    extracted_word_count: int | None = None
    extraction_error: str | None = None
    model_config = ConfigDict(from_attributes=True)


class UploadStatus(BaseModel):
    upload_id: str
    filename: str
    status: str
    extraction_method: str | None = None
    extraction_quality: float | None = None
    extracted_character_count: int | None = None
    extracted_word_count: int | None = None
    candidate_id: str | None = None
    identity_confidence: float | None = None
    error: str | None = None


class ChangeProposalRead(BaseModel):
    id: str
    document_id: str
    candidate_id: str | None = None
    status: str
    confidence: float
    changes: list[dict]


class ExtractionDiagnostic(BaseModel):
    filename: str
    pages: int
    method: str
    characters: int
    words: int
    quality: float
    preview: str


class MetricsRead(BaseModel):
    total_candidates: int
    screened_candidates: int
    industries: dict[str, int]
    positions: dict[str, int]
    locations: dict[str, int]
    screening_statuses: dict[str, int]
    experience_distribution: dict[str, int]
    salary_distribution: dict[str, int]
    recent_candidates: list[CandidateRead] = []
