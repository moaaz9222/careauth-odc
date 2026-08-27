"""
CareAuth AI — Frozen Contracts (Python / Pydantic v2)

These schemas are the law. Do not modify without Lead Agent approval.
Source: PRD §14 (AI Input/Output Contracts), §18 (Data Model), §19 (API Requirements)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
# Document Type Enum — §18, frozen, 9 values
# ═══════════════════════════════════════════════════════════════

class DocumentType(str, Enum):
    INSURANCE_CARD = "insurance_card"
    PHYSICIAN_ORDER = "physician_order"
    CLINICAL_NOTES = "clinical_notes"
    PHYSICIAN_NOTES_DETAILED = "physician_notes_detailed"
    PRIOR_IMAGING_REPORT = "prior_imaging_report"
    LAB_RESULTS = "lab_results"
    REFERRAL_LETTER = "referral_letter"
    PRIOR_AUTH_HISTORY = "prior_auth_history"
    OTHER = "other"


# ═══════════════════════════════════════════════════════════════
# Coverage Status Enum — §14.1 / §18
# ═══════════════════════════════════════════════════════════════

class CoverageStatus(str, Enum):
    COVERED = "covered"
    NOT_COVERED = "not_covered"
    PRIOR_AUTHORIZATION_REQUIRED = "prior_authorization_required"
    UNKNOWN = "unknown"


# ═══════════════════════════════════════════════════════════════
# Evidence Strength — §14.1, derived, never raw confidence
# ═══════════════════════════════════════════════════════════════

class EvidenceStrength(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ═══════════════════════════════════════════════════════════════
# Request Status (State Machine) — §15, 7 states
# ═══════════════════════════════════════════════════════════════

class RequestStatus(str, Enum):
    DRAFT = "DRAFT"
    ANALYZING = "ANALYZING"
    NEEDS_DOCUMENTS = "NEEDS_DOCUMENTS"
    READY_FOR_SUBMISSION = "READY_FOR_SUBMISSION"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    ACTION_REQUIRED = "ACTION_REQUIRED"


# ═══════════════════════════════════════════════════════════════
# Payer Decision — §20
# ═══════════════════════════════════════════════════════════════

class PayerDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    MORE_INFO_REQUIRED = "more_info_required"


# ═══════════════════════════════════════════════════════════════
# Reason Classification — §14.3, fixed 7-value enum
# ═══════════════════════════════════════════════════════════════

class ReasonClassification(str, Enum):
    INSUFFICIENT_CLINICAL_DOCUMENTATION = "insufficient_clinical_documentation"
    MISSING_DOCUMENT = "missing_document"
    SERVICE_NOT_COVERED = "service_not_covered"
    AUTHORIZATION_NOT_REQUIRED = "authorization_not_required"
    ELIGIBILITY_ISSUE = "eligibility_issue"
    ADMINISTRATIVE_ERROR = "administrative_error"
    OTHER = "other"


# ═══════════════════════════════════════════════════════════════
# Urgency — §11 F1
# ═══════════════════════════════════════════════════════════════

class Urgency(str, Enum):
    ROUTINE = "routine"
    URGENT = "urgent"


# ═══════════════════════════════════════════════════════════════
# Payer Mode — §20
# ═══════════════════════════════════════════════════════════════

class PayerMode(str, Enum):
    SCRIPTED = "scripted"
    MANUAL = "manual"


# ═══════════════════════════════════════════════════════════════
# Event Types — §18
# ═══════════════════════════════════════════════════════════════

class EventType(str, Enum):
    REQUEST_CREATED = "REQUEST_CREATED"
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    DOCUMENT_REMOVED = "DOCUMENT_REMOVED"
    ANALYSIS_STARTED = "ANALYSIS_STARTED"
    ANALYSIS_COMPLETE = "ANALYSIS_COMPLETE"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    SUBMITTED = "SUBMITTED"
    PAYER_APPROVED = "PAYER_APPROVED"
    PAYER_REJECTED = "PAYER_REJECTED"
    PAYER_MORE_INFO = "PAYER_MORE_INFO"
    FIELD_UPDATED = "FIELD_UPDATED"


# ═══════════════════════════════════════════════════════════════
# Agent Analysis Status — §22
# ═══════════════════════════════════════════════════════════════

class AgentStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


# ═══════════════════════════════════════════════════════════════
# §14.1 — Coverage Agent Input / Output
# ═══════════════════════════════════════════════════════════════

class CoverageInput_Plan(BaseModel):
    id: str
    payer_name: str
    plan_name: str


class CoverageInput_Service(BaseModel):
    id: str
    code: str
    name: str


class CoverageInput(BaseModel):
    request_id: str
    plan: CoverageInput_Plan
    service: CoverageInput_Service
    clinical_context: str
    urgency: str = "routine"


class EvidenceItem(BaseModel):
    chunk_id: str
    policy_document_title: str
    section_ref: str
    snippet: str
    similarity: float


class CoverageResult(BaseModel):
    agent: str = "coverage"
    version: str = "1.0"
    request_id: str
    status: CoverageStatus
    requires_prior_authorization: Optional[bool] = None
    reason: str
    conditions: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    evidence_strength: EvidenceStrength
    top_similarity: float = 0.0
    rule_matched: bool = False
    model: str = ""
    latency_ms: int = 0
    generated_at: str = ""


# ═══════════════════════════════════════════════════════════════
# §14.2 — Documentation Agent Output
# ═══════════════════════════════════════════════════════════════

class RequiredDocument(BaseModel):
    doc_type: DocumentType
    label: str
    mandatory: bool
    source_section: str


class PresentDocument(BaseModel):
    doc_type: DocumentType
    document_id: str
    file_name: str


class MissingDocument(BaseModel):
    doc_type: DocumentType
    label: str
    mandatory: bool
    why_required: str
    how_to_obtain: str
    source_section: str


class UnrecognizedDocument(BaseModel):
    doc_type: str
    document_id: str
    file_name: str


class DocumentationResult(BaseModel):
    agent: str = "documentation"
    version: str = "1.0"
    request_id: str
    ready_for_submission: bool
    required_documents: list[RequiredDocument] = Field(default_factory=list)
    present_documents: list[PresentDocument] = Field(default_factory=list)
    missing_documents: list[MissingDocument] = Field(default_factory=list)
    unrecognized_documents: list[UnrecognizedDocument] = Field(default_factory=list)
    blocking_summary: str = ""
    model: str = ""
    latency_ms: int = 0
    generated_at: str = ""


# ═══════════════════════════════════════════════════════════════
# §14.3 — Communication Agent: generate_packet
# ═══════════════════════════════════════════════════════════════

class PacketPatient(BaseModel):
    name: str
    dob: str
    member_number: str


class PacketService(BaseModel):
    code: str
    name: str


class PacketPhysician(BaseModel):
    name: str
    id: str


class PolicyBasis(BaseModel):
    policy_document_title: str
    section_ref: str


class PacketStructured(BaseModel):
    patient: PacketPatient
    payer: str
    plan: str
    service: PacketService
    physician: PacketPhysician
    clinical_justification: str
    attached_documents: list[str] = Field(default_factory=list)
    policy_basis: list[PolicyBasis] = Field(default_factory=list)


class SubmissionPacket(BaseModel):
    agent: str = "communication"
    operation: str = "generate_packet"
    version: str = "1.0"
    submission_number: str
    packet_markdown: str
    packet_structured: PacketStructured
    model: str = ""
    latency_ms: int = 0


# ═══════════════════════════════════════════════════════════════
# §14.3 — Communication Agent: analyze_response
# ═══════════════════════════════════════════════════════════════

class RecommendedActionKind(str, Enum):
    UPLOAD_DOCUMENT = "upload_document"
    EDIT_FIELD = "edit_field"
    REVIEW = "review"
    CONTACT = "contact"


class RecommendedAction(BaseModel):
    order: int
    kind: RecommendedActionKind
    doc_type: Optional[str] = None  # required when kind == upload_document
    field: Optional[str] = None     # required when kind == edit_field
    label: str
    detail: str


class ResolutionResult(BaseModel):
    agent: str = "communication"
    operation: str = "analyze_response"
    version: str = "1.0"
    decision: PayerDecision
    reason_classification: ReasonClassification
    payer_reason_verbatim: str
    explanation: str
    is_appealable: bool
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    resubmission_checklist: list[str] = Field(default_factory=list, max_length=5)
    model: str = ""
    latency_ms: int = 0


# ═══════════════════════════════════════════════════════════════
# §19 — Uniform Error Contract
# ═══════════════════════════════════════════════════════════════

class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"           # 422
    NOT_FOUND = "NOT_FOUND"                         # 404
    INVALID_TRANSITION = "INVALID_TRANSITION"       # 409
    SUBMISSION_BLOCKED = "SUBMISSION_BLOCKED"        # 409
    ANALYSIS_STALE = "ANALYSIS_STALE"               # 409
    AGENT_FAILURE = "AGENT_FAILURE"                  # 502
    FILE_TOO_LARGE = "FILE_TOO_LARGE"               # 413
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"  # 415


class ErrorDetail(BaseModel):
    code: ErrorCode
    message: str
    details: Optional[dict] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
