/**
 * CareAuth AI — Frozen Contracts (TypeScript)
 *
 * These types are the law. Do not modify without Lead Agent approval.
 * Source: PRD §14 (AI Input/Output Contracts), §18 (Data Model), §19 (API Requirements)
 */

// ═══════════════════════════════════════════════════════════════
// Document Type Enum — §18, frozen, 9 values
// ═══════════════════════════════════════════════════════════════

export const DocumentType = {
  INSURANCE_CARD: "insurance_card",
  PHYSICIAN_ORDER: "physician_order",
  CLINICAL_NOTES: "clinical_notes",
  PHYSICIAN_NOTES_DETAILED: "physician_notes_detailed",
  PRIOR_IMAGING_REPORT: "prior_imaging_report",
  LAB_RESULTS: "lab_results",
  REFERRAL_LETTER: "referral_letter",
  PRIOR_AUTH_HISTORY: "prior_auth_history",
  OTHER: "other",
} as const;

export type DocumentType = (typeof DocumentType)[keyof typeof DocumentType];

// ═══════════════════════════════════════════════════════════════
// Coverage Status — §14.1 / §18
// ═══════════════════════════════════════════════════════════════

export const CoverageStatus = {
  COVERED: "covered",
  NOT_COVERED: "not_covered",
  PRIOR_AUTHORIZATION_REQUIRED: "prior_authorization_required",
  UNKNOWN: "unknown",
} as const;

export type CoverageStatus =
  (typeof CoverageStatus)[keyof typeof CoverageStatus];

// ═══════════════════════════════════════════════════════════════
// Evidence Strength — §14.1, derived, never raw confidence
// ═══════════════════════════════════════════════════════════════

export const EvidenceStrength = {
  HIGH: "high",
  MEDIUM: "medium",
  LOW: "low",
} as const;

export type EvidenceStrength =
  (typeof EvidenceStrength)[keyof typeof EvidenceStrength];

// ═══════════════════════════════════════════════════════════════
// Request Status (State Machine) — §15, 7 states
// ═══════════════════════════════════════════════════════════════

export const RequestStatus = {
  DRAFT: "DRAFT",
  ANALYZING: "ANALYZING",
  NEEDS_DOCUMENTS: "NEEDS_DOCUMENTS",
  READY_FOR_SUBMISSION: "READY_FOR_SUBMISSION",
  SUBMITTED: "SUBMITTED",
  APPROVED: "APPROVED",
  ACTION_REQUIRED: "ACTION_REQUIRED",
} as const;

export type RequestStatus =
  (typeof RequestStatus)[keyof typeof RequestStatus];

// ═══════════════════════════════════════════════════════════════
// Payer Decision — §20
// ═══════════════════════════════════════════════════════════════

export const PayerDecision = {
  APPROVED: "approved",
  REJECTED: "rejected",
  MORE_INFO_REQUIRED: "more_info_required",
} as const;

export type PayerDecision =
  (typeof PayerDecision)[keyof typeof PayerDecision];

// ═══════════════════════════════════════════════════════════════
// Reason Classification — §14.3, fixed 7-value enum
// ═══════════════════════════════════════════════════════════════

export const ReasonClassification = {
  INSUFFICIENT_CLINICAL_DOCUMENTATION: "insufficient_clinical_documentation",
  MISSING_DOCUMENT: "missing_document",
  SERVICE_NOT_COVERED: "service_not_covered",
  AUTHORIZATION_NOT_REQUIRED: "authorization_not_required",
  ELIGIBILITY_ISSUE: "eligibility_issue",
  ADMINISTRATIVE_ERROR: "administrative_error",
  OTHER: "other",
} as const;

export type ReasonClassification =
  (typeof ReasonClassification)[keyof typeof ReasonClassification];

// ═══════════════════════════════════════════════════════════════
// Urgency — §11 F1
// ═══════════════════════════════════════════════════════════════

export const Urgency = {
  ROUTINE: "routine",
  URGENT: "urgent",
} as const;

export type Urgency = (typeof Urgency)[keyof typeof Urgency];

// ═══════════════════════════════════════════════════════════════
// Payer Mode — §20
// ═══════════════════════════════════════════════════════════════

export const PayerMode = {
  SCRIPTED: "scripted",
  MANUAL: "manual",
} as const;

export type PayerMode = (typeof PayerMode)[keyof typeof PayerMode];

// ═══════════════════════════════════════════════════════════════
// Event Types — §18
// ═══════════════════════════════════════════════════════════════

export const EventType = {
  REQUEST_CREATED: "REQUEST_CREATED",
  DOCUMENT_UPLOADED: "DOCUMENT_UPLOADED",
  DOCUMENT_REMOVED: "DOCUMENT_REMOVED",
  ANALYSIS_STARTED: "ANALYSIS_STARTED",
  ANALYSIS_COMPLETE: "ANALYSIS_COMPLETE",
  ANALYSIS_FAILED: "ANALYSIS_FAILED",
  SUBMITTED: "SUBMITTED",
  PAYER_APPROVED: "PAYER_APPROVED",
  PAYER_REJECTED: "PAYER_REJECTED",
  PAYER_MORE_INFO: "PAYER_MORE_INFO",
  FIELD_UPDATED: "FIELD_UPDATED",
} as const;

export type EventType = (typeof EventType)[keyof typeof EventType];

// ═══════════════════════════════════════════════════════════════
// Agent Analysis Status — §22
// ═══════════════════════════════════════════════════════════════

export const AgentStatus = {
  SUCCESS: "success",
  ERROR: "error",
} as const;

export type AgentStatus = (typeof AgentStatus)[keyof typeof AgentStatus];

// ═══════════════════════════════════════════════════════════════
// §14.1 — Coverage Agent Input / Output
// ═══════════════════════════════════════════════════════════════

export interface CoverageInputPlan {
  id: string;
  payer_name: string;
  plan_name: string;
}

export interface CoverageInputService {
  id: string;
  code: string;
  name: string;
}

export interface CoverageInput {
  request_id: string;
  plan: CoverageInputPlan;
  service: CoverageInputService;
  clinical_context: string;
  urgency: string;
}

export interface EvidenceItem {
  chunk_id: string;
  policy_document_title: string;
  section_ref: string;
  snippet: string;
  similarity: number;
}

export interface CoverageResult {
  agent: "coverage";
  version: "1.0";
  request_id: string;
  status: CoverageStatus;
  requires_prior_authorization: boolean | null;
  reason: string;
  conditions: string[];
  evidence: EvidenceItem[];
  evidence_strength: EvidenceStrength;
  top_similarity: number;
  rule_matched: boolean;
  model: string;
  latency_ms: number;
  generated_at: string;
}

// ═══════════════════════════════════════════════════════════════
// §14.2 — Documentation Agent Output
// ═══════════════════════════════════════════════════════════════

export interface RequiredDocument {
  doc_type: DocumentType;
  label: string;
  mandatory: boolean;
  source_section: string;
}

export interface PresentDocument {
  doc_type: DocumentType;
  document_id: string;
  file_name: string;
}

export interface MissingDocument {
  doc_type: DocumentType;
  label: string;
  mandatory: boolean;
  why_required: string;
  how_to_obtain: string;
  source_section: string;
}

export interface UnrecognizedDocument {
  doc_type: string;
  document_id: string;
  file_name: string;
}

export interface DocumentationResult {
  agent: "documentation";
  version: "1.0";
  request_id: string;
  ready_for_submission: boolean;
  required_documents: RequiredDocument[];
  present_documents: PresentDocument[];
  missing_documents: MissingDocument[];
  unrecognized_documents: UnrecognizedDocument[];
  blocking_summary: string;
  model: string;
  latency_ms: number;
  generated_at: string;
}

// ═══════════════════════════════════════════════════════════════
// §14.3 — Communication Agent: generate_packet
// ═══════════════════════════════════════════════════════════════

export interface PacketPatient {
  name: string;
  dob: string;
  member_number: string;
}

export interface PacketService {
  code: string;
  name: string;
}

export interface PacketPhysician {
  name: string;
  id: string;
}

export interface PolicyBasis {
  policy_document_title: string;
  section_ref: string;
}

export interface PacketStructured {
  patient: PacketPatient;
  payer: string;
  plan: string;
  service: PacketService;
  physician: PacketPhysician;
  clinical_justification: string;
  attached_documents: string[];
  policy_basis: PolicyBasis[];
}

export interface SubmissionPacket {
  agent: "communication";
  operation: "generate_packet";
  version: "1.0";
  submission_number: string;
  packet_markdown: string;
  packet_structured: PacketStructured;
  model: string;
  latency_ms: number;
}

// ═══════════════════════════════════════════════════════════════
// §14.3 — Communication Agent: analyze_response
// ═══════════════════════════════════════════════════════════════

export const RecommendedActionKind = {
  UPLOAD_DOCUMENT: "upload_document",
  EDIT_FIELD: "edit_field",
  REVIEW: "review",
  CONTACT: "contact",
} as const;

export type RecommendedActionKind =
  (typeof RecommendedActionKind)[keyof typeof RecommendedActionKind];

export interface RecommendedAction {
  order: number;
  kind: RecommendedActionKind;
  doc_type?: string; // required when kind == "upload_document"
  field?: string; // required when kind == "edit_field"
  label: string;
  detail: string;
}

export interface ResolutionResult {
  agent: "communication";
  operation: "analyze_response";
  version: "1.0";
  decision: PayerDecision;
  reason_classification: ReasonClassification;
  payer_reason_verbatim: string;
  explanation: string;
  is_appealable: boolean;
  recommended_actions: RecommendedAction[];
  resubmission_checklist: string[]; // max 5 items
  model: string;
  latency_ms: number;
}

// ═══════════════════════════════════════════════════════════════
// §19 — Uniform Error Contract
// ═══════════════════════════════════════════════════════════════

export const ErrorCode = {
  VALIDATION_ERROR: "VALIDATION_ERROR",           // 422
  NOT_FOUND: "NOT_FOUND",                         // 404
  INVALID_TRANSITION: "INVALID_TRANSITION",       // 409
  SUBMISSION_BLOCKED: "SUBMISSION_BLOCKED",        // 409
  ANALYSIS_STALE: "ANALYSIS_STALE",               // 409
  AGENT_FAILURE: "AGENT_FAILURE",                  // 502
  FILE_TOO_LARGE: "FILE_TOO_LARGE",               // 413
  UNSUPPORTED_FILE_TYPE: "UNSUPPORTED_FILE_TYPE",  // 415
} as const;

export type ErrorCode = (typeof ErrorCode)[keyof typeof ErrorCode];

export interface ErrorDetail {
  code: ErrorCode;
  message: string;
  details?: Record<string, unknown>;
}

export interface ErrorResponse {
  error: ErrorDetail;
}

// ═══════════════════════════════════════════════════════════════
// API Response Wrappers — for GET /requests (list with counters)
// ═══════════════════════════════════════════════════════════════

export interface StatusCounters {
  total: number;
  draft: number;
  needs_documents: number;
  submitted: number;
  approved: number;
  action_required: number;
}

export interface RequestSummary {
  id: string;
  patient_name: string;
  payer_name: string;
  plan_name: string;
  service_name: string;
  status: RequestStatus;
  created_at: string;
  updated_at: string;
}

export interface RequestListResponse {
  requests: RequestSummary[];
  counters: StatusCounters;
}
