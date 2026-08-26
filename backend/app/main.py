import re
import json
from collections import Counter
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import resolve_path, settings
from app.db import Base, SessionLocal, engine, get_db
from app.documents.extraction import extract_document_text
from app.documents.storage import get_storage
from app.ingestion.excel import import_workbook
from app.models import Candidate, CandidateDocument, CandidateUpdateProposal
from app.schemas import CandidateCreate, CandidateRead, CandidateUpdate, ChangeProposalRead, DocumentRead, ExtractionDiagnostic, MetricsRead, RecommendationRequest, RecommendationResponse, RecommendationResult, ScoreBreakdown, SearchRequest, SearchResponse, UploadStatus
from app.services.candidates import apply_candidate_data, candidate_query, get_or_create_demo_organization
from app.services.cv_extraction import extract_structured_candidate
from app.services.identity import resolve_identity
from app.services.ranking import score_candidate
from app.ranking.recommender import recommend, static_recommend

Base.metadata.create_all(engine)
app = FastAPI(title=settings.app_name, version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins_list, allow_methods=["*"], allow_headers=["*"])


def parse_query(request: SearchRequest) -> SearchRequest:
    query = request.query
    skills = list(request.skills)
    for skill in ("python", "llm", "pytorch", "fastapi", "sql", "machine learning", "ai", "ml"):
        if re.search(rf"\b{re.escape(skill)}\b", query, re.I) and skill not in [item.casefold() for item in skills]:
            skills.append(skill)
    experience = re.search(r"(?:at least|minimum of)\s+(\d+(?:\.\d+)?)\s+years?", query, re.I)
    notice = re.search(r"(?:within|under|below)\s+(\d+)\s+days?", query, re.I)
    salary = re.search(r"(?:below|under|less than)\s+(\d+(?:\.\d+)?)\s*(?:lpa|lakhs?)", query, re.I)
    location = re.search(r"(?:based in|located in|from)\s+([A-Za-z ]+?)(?:,|\s+and|$)", query, re.I)
    return request.model_copy(update={
        "skills": skills,
        "minimum_experience": float(experience.group(1)) if experience else request.minimum_experience,
        "maximum_notice_period": int(notice.group(1)) if notice else request.maximum_notice_period,
        "maximum_salary": float(salary.group(1)) * 100000 if salary else request.maximum_salary,
        "location": location.group(1).strip() if location else request.location,
    })


def to_read(candidate: Candidate, request: SearchRequest | None = None) -> CandidateRead:
    score, reasons, gaps = score_candidate(candidate, request) if request else (None, [], [])
    return CandidateRead(
        id=candidate.id, name=candidate.name, position_applied_for=candidate.position_applied_for,
        current_position=candidate.current_position, current_company=candidate.current_company,
        industry=candidate.industry, city=candidate.city, experience_years=candidate.experience_years,
        current_salary=candidate.current_salary, expected_salary=candidate.expected_salary,
        notice_period_days=candidate.notice_period_days, screening_status=candidate.screening_status,
        education=[item.qualification for item in candidate.education], email=candidate.email,
        phone=candidate.phone, age=candidate.age, marital_status=candidate.marital_status,
        english_proficiency=candidate.english_proficiency, skills=[item.skill for item in candidate.skills],
        suitability_score=score, score_reasons=reasons, score_gaps=gaps,
    )


def list_candidates(filters: SearchRequest, db: Session) -> SearchResponse:
    query = candidate_query(filters)
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    candidates = db.scalars(query.order_by(Candidate.updated_at.desc()).offset((filters.page - 1) * filters.page_size).limit(filters.page_size)).unique().all()
    return SearchResponse(items=[to_read(candidate, filters if filters.query or filters.skills else None) for candidate in candidates], total=total, page=filters.page, page_size=filters.page_size)


@app.post("/api/recommendations", response_model=RecommendationResponse)
def recommendations(request: RecommendationRequest, db: Session = Depends(get_db)) -> RecommendationResponse:
    requirements, ranked = recommend(db, request.query, request.limit)
    parsed = {
        "position": requirements.position, "industry": requirements.industry, "location": requirements.location,
        "minimum_experience": requirements.minimum_experience, "maximum_experience": requirements.maximum_experience,
        "maximum_salary": requirements.maximum_salary, "maximum_notice_period": requirements.maximum_notice_period,
        "required_skills": list(requirements.required_skills), "unsupported_criteria": list(requirements.unsupported_criteria),
    }
    return RecommendationResponse(query=request.query, parsed_requirements=parsed, results=[
        RecommendationResult(rank=index, candidate_id=candidate.id, candidate=to_read(candidate), overall_score=result.overall_score, score_breakdown=ScoreBreakdown(**result.breakdown), matched_criteria=result.matched_criteria, concerns=result.concerns, explanation=result.explanation)
        for index, (candidate, result) in enumerate(ranked, 1)
    ])


@app.get("/api/recommendations/static", response_model=RecommendationResponse)
def static_recommendations(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)) -> RecommendationResponse:
    ranked = static_recommend(db, limit)
    return RecommendationResponse(query="Static best matches", parsed_requirements={"mode": "static_profile_ranking"}, results=[
        RecommendationResult(rank=index, candidate_id=candidate.id, candidate=to_read(candidate), overall_score=result.overall_score, score_breakdown=ScoreBreakdown(**result.breakdown), matched_criteria=result.matched_criteria, concerns=result.concerns, explanation=result.explanation)
        for index, (candidate, result) in enumerate(ranked, 1)
    ])


@app.get("/api/health")
def health(db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        count = db.scalar(select(func.count()).select_from(Candidate)) or 0
        return {"status": "ok", "database": "connected", "candidate_count": count, "storage_backend": settings.storage_backend}
    except Exception:
        return {"status": "degraded", "database": "unavailable", "candidate_count": 0, "storage_backend": settings.storage_backend}


@app.get("/api/candidates", response_model=SearchResponse)
def get_candidates(
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), q: str = "",
    position: str | None = None, industry: str | None = None, city: str | None = None,
    min_experience: float | None = Query(None, ge=0), max_salary: float | None = Query(None, ge=0),
    max_notice_period: int | None = Query(None, ge=0), education: str | None = None,
    screening: str | None = None, current_company: str | None = None, current_position: str | None = None,
    db: Session = Depends(get_db),
) -> SearchResponse:
    filters = SearchRequest(query=q, position=position or current_position, industry=industry, location=city, minimum_experience=min_experience, maximum_salary=max_salary, maximum_notice_period=max_notice_period, education=education, screening_status=screening, current_company=current_company, page=page, page_size=page_size)
    return list_candidates(filters, db)


@app.get("/api/candidates/search", response_model=SearchResponse)
def get_candidate_search(q: str = "", page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), db: Session = Depends(get_db)) -> SearchResponse:
    return list_candidates(SearchRequest(query=q, page=page, page_size=page_size), db)


@app.post("/api/candidates/search", response_model=SearchResponse)
def search_candidates(request: SearchRequest, db: Session = Depends(get_db)) -> SearchResponse:
    return list_candidates(parse_query(request), db)


@app.post("/api/candidates", response_model=CandidateRead, status_code=201)
def create_candidate(data: CandidateCreate, db: Session = Depends(get_db)) -> CandidateRead:
    organization = get_or_create_demo_organization(db)
    candidate = Candidate(id=f"CAND-{uuid4().hex[:12].upper()}", organization_id=organization.id, name=data.name)
    apply_candidate_data(candidate, data)
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return to_read(candidate)


@app.get("/api/candidates/{candidate_id}", response_model=CandidateRead)
def get_candidate(candidate_id: str, db: Session = Depends(get_db)) -> CandidateRead:
    candidate = db.scalar(candidate_query().where(Candidate.id == candidate_id))
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return to_read(candidate)


@app.get("/api/candidates/{candidate_id}/documents", response_model=list[DocumentRead])
def get_documents(candidate_id: str, db: Session = Depends(get_db)) -> list[DocumentRead]:
    if not db.get(Candidate, candidate_id):
        raise HTTPException(status_code=404, detail="Candidate not found")
    return list(db.scalars(select(CandidateDocument).where(CandidateDocument.candidate_id == candidate_id)).all())


@app.get("/api/cv-uploads/{upload_id}", response_model=UploadStatus)
def get_upload_status(upload_id: str, db: Session = Depends(get_db)) -> UploadStatus:
    document = db.get(CandidateDocument, upload_id)
    if not document:
        raise HTTPException(status_code=404, detail="Upload not found")
    proposal = db.scalar(select(CandidateUpdateProposal).where(CandidateUpdateProposal.document_id == document.id))
    return UploadStatus(upload_id=document.id, filename=document.filename, status=document.status, extraction_method=document.extraction_method, extraction_quality=document.extraction_quality, extracted_character_count=document.extracted_character_count, extracted_word_count=document.extracted_word_count, candidate_id=document.candidate_id, identity_confidence=proposal.confidence if proposal else None, error=document.extraction_error)


@app.get("/api/cv-uploads/{upload_id}/proposal", response_model=ChangeProposalRead)
def get_upload_proposal(upload_id: str, db: Session = Depends(get_db)) -> ChangeProposalRead:
    proposal = db.scalar(select(CandidateUpdateProposal).where(CandidateUpdateProposal.document_id == upload_id))
    if not proposal:
        raise HTTPException(status_code=404, detail="No update proposal is available")
    return ChangeProposalRead(id=proposal.id, document_id=proposal.document_id, candidate_id=proposal.candidate_id, status=proposal.status, confidence=proposal.confidence, changes=json.loads(proposal.changes))


@app.post("/api/cv-uploads/{upload_id}/proposal/approve", response_model=ChangeProposalRead)
def approve_upload_proposal(upload_id: str, db: Session = Depends(get_db)) -> ChangeProposalRead:
    proposal = db.scalar(select(CandidateUpdateProposal).where(CandidateUpdateProposal.document_id == upload_id))
    document = db.get(CandidateDocument, upload_id)
    if not proposal or not document:
        raise HTTPException(status_code=404, detail="No update proposal is available")
    extracted = extract_structured_candidate(document.extracted_text or "")
    if not extracted.name and not proposal.candidate_id:
        raise HTTPException(status_code=422, detail="The CV does not contain a usable candidate name")
    candidate = db.get(Candidate, proposal.candidate_id) if proposal.candidate_id else None
    if candidate is None:
        organization = get_or_create_demo_organization(db)
        candidate = Candidate(id=f"CAND-{uuid4().hex[:12].upper()}", organization_id=organization.id, name=extracted.name or "Unnamed candidate")
        db.add(candidate)
        db.flush()
    data = CandidateCreate(name=extracted.name or candidate.name, position_applied_for=extracted.current_position, current_position=extracted.current_position, current_company=extracted.current_company, industry=extracted.industry, city=extracted.city, experience_years=extracted.experience_years, current_salary=extracted.current_salary, expected_salary=extracted.expected_salary, notice_period_days=extracted.notice_period_days, email=extracted.email, phone=extracted.phone, skills=extracted.skills, education=[item.qualification for item in extracted.education])
    apply_candidate_data(candidate, data)
    document.candidate_id = candidate.id
    document.status = "approved"
    proposal.candidate_id = candidate.id
    proposal.status = "approved"
    db.commit()
    return ChangeProposalRead(id=proposal.id, document_id=proposal.document_id, candidate_id=proposal.candidate_id, status=proposal.status, confidence=proposal.confidence, changes=json.loads(proposal.changes))


@app.post("/api/cv-uploads/{upload_id}/proposal/reject", response_model=ChangeProposalRead)
def reject_upload_proposal(upload_id: str, db: Session = Depends(get_db)) -> ChangeProposalRead:
    proposal = db.scalar(select(CandidateUpdateProposal).where(CandidateUpdateProposal.document_id == upload_id))
    if not proposal:
        raise HTTPException(status_code=404, detail="No update proposal is available")
    proposal.status = "rejected"
    document = db.get(CandidateDocument, upload_id)
    if document:
        document.status = "rejected"
    db.commit()
    return ChangeProposalRead(id=proposal.id, document_id=proposal.document_id, candidate_id=proposal.candidate_id, status=proposal.status, confidence=proposal.confidence, changes=json.loads(proposal.changes))


@app.put("/api/candidates/{candidate_id}", response_model=CandidateRead)
def update_candidate(candidate_id: str, data: CandidateUpdate, db: Session = Depends(get_db)) -> CandidateRead:
    candidate = db.scalar(candidate_query().where(Candidate.id == candidate_id))
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    apply_candidate_data(candidate, data)
    db.commit()
    db.refresh(candidate)
    return to_read(candidate)


@app.delete("/api/candidates/{candidate_id}", status_code=204)
def delete_candidate(candidate_id: str, db: Session = Depends(get_db)) -> None:
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    db.delete(candidate)
    db.commit()


@app.get("/api/dashboard/metrics", response_model=MetricsRead)
def dashboard_metrics(db: Session = Depends(get_db)) -> MetricsRead:
    candidates = db.scalars(select(Candidate).options(selectinload(Candidate.skills), selectinload(Candidate.education))).all()
    recent = sorted(candidates, key=lambda item: item.created_at, reverse=True)[:5]
    return MetricsRead(
        total_candidates=len(candidates), screened_candidates=sum(bool(item.screening_status) for item in candidates),
        industries=dict(Counter(item.industry or "Unspecified" for item in candidates).most_common(6)),
        positions=dict(Counter(item.current_position or item.position_applied_for or "Unspecified" for item in candidates).most_common(6)),
        locations=dict(Counter(item.city or "Unspecified" for item in candidates).most_common(6)),
        screening_statuses=dict(Counter(item.screening_status or "Unspecified" for item in candidates).most_common()),
        experience_distribution=dict(Counter("0-2 years" if (item.experience_years or 0) < 2 else "2-5 years" if (item.experience_years or 0) < 5 else "5+ years" for item in candidates).most_common()),
        salary_distribution=dict(Counter("Not listed" if item.expected_salary is None else "Under 10 LPA" if item.expected_salary < 1000000 else "10-20 LPA" if item.expected_salary < 2000000 else "20+ LPA" for item in candidates).most_common()),
        recent_candidates=[to_read(item) for item in recent],
    )


def process_upload(document_id: str, storage_key: str) -> None:
    with SessionLocal() as db:
        document = db.get(CandidateDocument, document_id)
        if not document:
            return
        with get_storage().temporary_path(storage_key) as document_path:
            result = extract_document_text(document_path)
        document.status = "extracted" if result.quality >= 0.35 else "extraction_failed"
        document.extraction_method = result.method
        document.extraction_quality = result.quality
        document.extracted_character_count = result.characters
        document.extracted_word_count = result.words
        document.extraction_error = result.error
        document.extracted_text = result.text
        if result.quality >= 0.35:
            extracted = extract_structured_candidate(result.text)
            match = resolve_identity(db, extracted)
            document.candidate_id = match.candidate.id if match.candidate and match.confidence >= 0.9 else None
            document.status = "ready_for_review"
            changes = []
            if match.candidate:
                for field in ("name", "email", "phone", "city", "current_company", "current_position", "experience_years", "industry", "notice_period_days"):
                    new_value = getattr(extracted, field, None)
                    old_value = getattr(match.candidate, field, None)
                    if new_value is not None and new_value != old_value:
                        changes.append({"field": field, "old_value": old_value, "new_value": new_value, "confidence": match.confidence})
            db.add(CandidateUpdateProposal(document_id=document.id, candidate_id=match.candidate.id if match.candidate else None, confidence=match.confidence, changes=json.dumps(changes)))
        db.commit()


@app.post("/api/candidates/upload-cv", status_code=202, response_model=UploadStatus)
async def upload_cv(background_tasks: BackgroundTasks, file: UploadFile = File(...)) -> dict[str, str]:
    extension = Path(file.filename or "").suffix.casefold()
    if extension not in {".pdf", ".docx", ".txt"}:
        raise HTTPException(status_code=415, detail="Supported CV formats are PDF, DOCX, and TXT.")
    content = await file.read()
    storage_key = get_storage().save(file.filename or "upload", content)
    with SessionLocal() as db:
        document = CandidateDocument(filename=file.filename or "upload", storage_key=storage_key, status="queued")
        db.add(document)
        db.commit()
        db.refresh(document)
        upload_id = document.id
    background_tasks.add_task(process_upload, upload_id, storage_key)
    return UploadStatus(upload_id=upload_id, filename=file.filename or "upload", status="queued")


@app.post("/api/dev/extract-diagnostic", response_model=ExtractionDiagnostic)
async def extract_diagnostic(file: UploadFile = File(...)) -> ExtractionDiagnostic:
    content = await file.read()
    storage = get_storage()
    key = storage.save(file.filename or "diagnostic", content)
    with storage.temporary_path(key) as document_path:
        result = extract_document_text(document_path)
    return ExtractionDiagnostic(filename=file.filename or "diagnostic", pages=result.pages, method=result.method, characters=result.characters, words=result.words, quality=result.quality, preview=result.text[:500])


@app.post("/api/admin/import-candidates")
async def admin_import_candidates(file: UploadFile | None = File(None), x_role: str | None = Header(None)) -> dict[str, object]:
    if (x_role or "").casefold() != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    source = resolve_path(settings.seed_file)
    if file:
        storage = get_storage()
        source = Path(storage.save(file.filename or "master.xlsx", await file.read()))
        with storage.temporary_path(source.name) as source_path:
            return import_workbook(db, source_path)
    with SessionLocal() as db:
        return import_workbook(db, source)
