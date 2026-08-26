from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12].upper()}"


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ORG"))
    name: Mapped[str] = mapped_column(String(200), unique=True)
    candidates: Mapped[list["Candidate"]] = relationship(back_populates="organization")


class Candidate(Base):
    __tablename__ = "candidates"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    age: Mapped[int | None] = mapped_column(Integer)
    marital_status: Mapped[str | None] = mapped_column(String(80))
    position_applied_for: Mapped[str | None] = mapped_column(String(200), index=True)
    industry: Mapped[str | None] = mapped_column(String(160), index=True)
    application_source: Mapped[str | None] = mapped_column(String(160))
    phone: Mapped[str | None] = mapped_column(String(80), index=True)
    email: Mapped[str | None] = mapped_column(String(254), index=True)
    notice_period_days: Mapped[int | None] = mapped_column(Integer, index=True)
    city: Mapped[str | None] = mapped_column(String(120), index=True)
    current_company: Mapped[str | None] = mapped_column(String(200))
    current_position: Mapped[str | None] = mapped_column(String(200), index=True)
    current_salary: Mapped[float | None] = mapped_column(Float)
    expected_salary: Mapped[float | None] = mapped_column(Float)
    experience_years: Mapped[float | None] = mapped_column(Float, index=True)
    english_proficiency: Mapped[str | None] = mapped_column(String(80))
    screening_status: Mapped[str | None] = mapped_column(String(80), index=True)
    original_row: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization: Mapped[Organization] = relationship(back_populates="candidates")
    skills: Mapped[list["CandidateSkill"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    education: Mapped[list["CandidateEducation"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    notes: Mapped[list["CandidateNote"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    documents: Mapped[list["CandidateDocument"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), primary_key=True)
    skill: Mapped[str] = mapped_column(String(120), primary_key=True)
    source: Mapped[str] = mapped_column(String(40), default="import")
    candidate: Mapped[Candidate] = relationship(back_populates="skills")


class CandidateEducation(Base):
    __tablename__ = "candidate_education"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("EDU"))
    candidate_id: Mapped[str | None] = mapped_column(ForeignKey("candidates.id"), index=True, nullable=True)
    qualification: Mapped[str] = mapped_column(String(240))
    institution: Mapped[str | None] = mapped_column(String(240))
    candidate: Mapped[Candidate] = relationship(back_populates="education")


class CandidateDocument(Base):
    __tablename__ = "candidate_documents"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("DOC"))
    candidate_id: Mapped[str | None] = mapped_column(ForeignKey("candidates.id"), index=True, nullable=True)
    filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    document_type: Mapped[str] = mapped_column(String(40), default="cv")
    status: Mapped[str] = mapped_column(String(40), default="uploaded")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    extraction_method: Mapped[str | None] = mapped_column(String(40))
    extraction_quality: Mapped[float | None] = mapped_column(Float)
    extracted_character_count: Mapped[int | None] = mapped_column(Integer)
    extracted_word_count: Mapped[int | None] = mapped_column(Integer)
    extraction_error: Mapped[str | None] = mapped_column(Text)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    candidate: Mapped[Candidate] = relationship(back_populates="documents")


class CandidateUpdateProposal(Base):
    __tablename__ = "candidate_update_proposals"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("PROP"))
    document_id: Mapped[str] = mapped_column(ForeignKey("candidate_documents.id"), index=True)
    candidate_id: Mapped[str | None] = mapped_column(ForeignKey("candidates.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="pending")
    confidence: Mapped[float] = mapped_column(Float, default=0)
    changes: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CandidateNote(Base):
    __tablename__ = "candidate_notes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("NOTE"))
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), index=True)
    body: Mapped[str] = mapped_column(Text)
    candidate: Mapped[Candidate] = relationship(back_populates="notes")


class ImportBatch(Base):
    __tablename__ = "import_batches"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("IMP"))
    source_filename: Mapped[str] = mapped_column(String(255))
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("AUD"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    candidate_id: Mapped[str | None] = mapped_column(ForeignKey("candidates.id"), index=True)
    actor: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(100))
    details: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("USR"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    role: Mapped[str] = mapped_column(String(40), default="viewer")
