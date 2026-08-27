"""
CareAuth AI — SQLModel Table Definitions

Source: PRD §18 (Data Model)
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlmodel import Column, Field, SQLModel, Text, JSON


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


# ─── Reference / Seed Tables ────────────────────────────────

class Patient(SQLModel, table=True):
    __tablename__ = "patients"

    id: str = Field(default_factory=_uuid, primary_key=True)
    full_name: str
    date_of_birth: date
    gender: str
    mock_national_id: str
    created_at: datetime = Field(default_factory=_now)


class InsurancePlan(SQLModel, table=True):
    __tablename__ = "insurance_plans"

    id: str = Field(default_factory=_uuid, primary_key=True)
    payer_name: str
    plan_name: str
    plan_code: str
    notes: Optional[str] = None


class Service(SQLModel, table=True):
    __tablename__ = "services"

    id: str = Field(default_factory=_uuid, primary_key=True)
    code: str
    name: str
    category: str


# ─── Policy / RAG Tables ────────────────────────────────────

class PolicyDocument(SQLModel, table=True):
    __tablename__ = "policy_documents"

    id: str = Field(default_factory=_uuid, primary_key=True)
    plan_id: str = Field(foreign_key="insurance_plans.id")
    title: str
    doc_kind: str  # e.g. "coverage", "authorization", "documentation"
    raw_text: str = Field(sa_column=Column(Text))
    created_at: datetime = Field(default_factory=_now)


class PolicyChunk(SQLModel, table=True):
    __tablename__ = "policy_chunks"

    id: str = Field(default_factory=_uuid, primary_key=True)
    policy_document_id: str = Field(foreign_key="policy_documents.id")
    chunk_index: int
    section_ref: str  # e.g. "§4.2"
    text: str = Field(sa_column=Column(Text))
    embedding: Optional[bytes] = None  # BLOB, numpy array serialized
    token_count: int = 0


# ─── Coverage Rules ──────────────────────────────────────────

class CoverageRule(SQLModel, table=True):
    __tablename__ = "coverage_rules"

    id: str = Field(default_factory=_uuid, primary_key=True)
    plan_id: str = Field(foreign_key="insurance_plans.id")
    service_id: str = Field(foreign_key="services.id")
    status: str  # "covered" | "not_covered" | "prior_authorization_required"
    requires_prior_authorization: bool
    required_document_types: str = Field(sa_column=Column(JSON))  # JSON list of DocumentType values
    conditions: Optional[str] = Field(default=None, sa_column=Column(JSON))  # JSON list of condition strings
    primary_policy_document_id: Optional[str] = Field(
        default=None, foreign_key="policy_documents.id"
    )
    primary_section_ref: Optional[str] = None


# ─── Authorization Requests ─────────────────────────────────

class AuthorizationRequest(SQLModel, table=True):
    __tablename__ = "authorization_requests"

    id: str = Field(default_factory=_uuid, primary_key=True)
    patient_id: str = Field(foreign_key="patients.id")
    plan_id: str = Field(foreign_key="insurance_plans.id")
    service_id: str = Field(foreign_key="services.id")
    member_number: str
    physician_name: str
    physician_id_mock: Optional[str] = None
    clinical_context: str = Field(sa_column=Column(Text))
    urgency: str = "routine"  # "routine" | "urgent"
    status: str = "DRAFT"  # RequestStatus enum value
    current_input_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


# ─── Documents ───────────────────────────────────────────────

class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: str = Field(default_factory=_uuid, primary_key=True)
    request_id: str = Field(foreign_key="authorization_requests.id")
    doc_type: str  # DocumentType enum value
    file_name: str
    mime_type: str
    size_bytes: int
    storage_path: str
    uploaded_at: datetime = Field(default_factory=_now)
    uploaded_after_rejection: bool = False


# ─── AI Analyses ─────────────────────────────────────────────

class AiAnalysis(SQLModel, table=True):
    __tablename__ = "ai_analyses"

    id: str = Field(default_factory=_uuid, primary_key=True)
    request_id: str = Field(foreign_key="authorization_requests.id")
    agent: str  # "coverage" | "documentation" | "communication"
    operation: Optional[str] = None  # "generate_packet" | "analyze_response" | null
    version: str = "1.0"
    input_hash: str
    output_json: str = Field(sa_column=Column(Text))  # serialized JSON
    model: str
    latency_ms: int
    status: str = "success"  # "success" | "error"
    error_text: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)


# ─── Insurance Submissions ───────────────────────────────────

class InsuranceSubmission(SQLModel, table=True):
    __tablename__ = "insurance_submissions"

    id: str = Field(default_factory=_uuid, primary_key=True)
    request_id: str = Field(foreign_key="authorization_requests.id")
    submission_number: str  # PA-{YYYYMMDD}-{seq}
    attempt_number: int
    packet_markdown: str = Field(sa_column=Column(Text))
    packet_json: str = Field(sa_column=Column(Text))  # serialized JSON
    submitted_at: datetime = Field(default_factory=_now)


# ─── Insurance Responses ─────────────────────────────────────

class InsuranceResponse(SQLModel, table=True):
    __tablename__ = "insurance_responses"

    id: str = Field(default_factory=_uuid, primary_key=True)
    submission_id: str = Field(foreign_key="insurance_submissions.id")
    decision: str  # "approved" | "rejected" | "more_info_required"
    reason_code: Optional[str] = None
    reason_text: Optional[str] = None
    responder: str = "scripted"  # "scripted" | "manual"
    responded_at: datetime = Field(default_factory=_now)


# ─── Request Events (Timeline) ──────────────────────────────

class RequestEvent(SQLModel, table=True):
    __tablename__ = "request_events"

    id: str = Field(default_factory=_uuid, primary_key=True)
    request_id: str = Field(foreign_key="authorization_requests.id")
    event_type: str  # EventType enum value
    actor: str = "system"  # "system" | "user" | "payer"
    payload_json: Optional[str] = Field(
        default=None, sa_column=Column(Text)
    )
    created_at: datetime = Field(default_factory=_now)


# ─── Mock Payer Script ───────────────────────────────────────

class MockPayerScript(SQLModel, table=True):
    __tablename__ = "mock_payer_script"

    id: str = Field(default_factory=_uuid, primary_key=True)
    service_id: str = Field(foreign_key="services.id")
    attempt_number: int
    decision: str  # "approved" | "rejected" | "more_info_required"
    reason_code: Optional[str] = None
    reason_text: Optional[str] = None
