# CareAuth AI — Product Requirements Document
### AI-Powered Prior Authorization & Documentation Assistant
**Version:** 1.0 (One-Day MVP / Hackathon Build)
**Owner:** Product / Tech Lead
**Team:** 3 AI Developers, 1 Frontend Developer, 1 Backend Developer
**Build window:** 1 working day (~9 hours including integration and demo prep)

---

## 0. PM Note — What I Changed and Why

This PRD does not implement the source brief verbatim. Seven changes were made because the original scope does not fit in one day with five people. Each change is listed with its rationale so the team can accept or reject it consciously.

| # | Change | Rationale |
|---|---|---|
| 1 | **Documents are declared by type at upload, not read by AI.** No OCR, no PDF text extraction in MVP. | Document content extraction is the single largest time sink and the largest failure surface (scanned PDFs, encoding, layout). It contributes almost nothing to the demo narrative. The Documentation Agent's value is *gap detection and explanation*, which works perfectly on declared metadata. |
| 2 | **Required-document lists and coverage outcomes come from a deterministic rules table.** The LLM explains and cites; it does not decide. | An LLM that decides coverage will occasionally flip its answer mid-demo. A rules table cannot. The demo still shows RAG (evidence retrieval + citation) and agent reasoning, but the state machine never depends on a coin flip. |
| 3 | **`confidence: 0.91` is removed.** Replaced with `evidence_strength` (high/medium/low) derived from retrieval similarity + rule match. | Self-reported LLM confidence scores are not calibrated and are meaningless. Any judge or clinician who asks "what does 0.91 mean?" gets an answer that damages credibility. A derived evidence signal is defensible. |
| 4 | **Five UI pages collapsed to four routes.** Timeline is a panel inside Request Detail, not its own page. | One frontend developer, one day. Four routes is already aggressive. |
| 5 | **State machine reduced from 9 states to 7.** `Under Review` and `AI Validation` merged into `ANALYZING`. | The original had two states with no distinct trigger, no distinct UI, and no distinct exit condition. Dead states create bugs. |
| 6 | **No vector database service.** Embeddings held in a NumPy array in process memory. | ~5 policy documents produce ~40 chunks. Standing up Chroma/Qdrant/pgvector costs 45–90 minutes and buys nothing at this scale. Cosine similarity over 40 vectors is ~15 lines of code. |
| 7 | **Mock insurer runs in scripted mode by default, manual mode on demand.** | The demo requires a specific reject-then-approve sequence. A human clicking buttons in a second browser tab during a live demo is a failure waiting to happen. Scripted responses guarantee the narrative; the manual portal stays available for interactive questioning. |

**Two risks the original brief did not name:**

- **Latency.** Three sequential LLM calls at 4–8s each is a 20-second dead screen. Coverage and Documentation agents must run in parallel, and the UI must show per-agent skeleton states. This is a demo-killing detail, not a polish item.
- **API contract freeze.** With three AI devs, one FE dev and one BE dev, the critical path is not any single feature. It is the moment the frontend can start building against something real. The contract must be frozen and mock-served by **T+45 minutes** or the frontend developer loses half the day.

---

## 1. Executive Summary

CareAuth AI is a workflow assistant for hospital insurance/authorization staff. Before a prior authorization request is sent to a payer, CareAuth AI checks the requested service against the patient's insurance policy, verifies that every required supporting document is attached, explains any blocker in plain language with a citation to the policy section, and refuses to let an incomplete request be submitted.

When the payer responds with a rejection or a request for more information, CareAuth AI classifies the reason, explains it, and produces a concrete resubmission checklist.

The MVP demonstrates a complete, closed loop: **create → analyze → block → resolve → submit → reject → explain → resolve → resubmit → approve.** Every external system (payer, EHR, identity) is simulated. The workflow is real.

**What this product is not:** a chatbot with insurance knowledge. There is no free-text chat surface in the MVP. Every AI output is attached to a specific request, a specific decision, and a specific next action.

---

## 2. Product Vision

Prior authorization is one of the highest-friction administrative workflows in healthcare delivery. The friction is not clinical, it is informational: the person preparing the request does not reliably know what the policy requires, what documents are needed, or why a rejection happened.

CareAuth AI closes that information gap at the point of work. Longer term it becomes the system of record for authorization readiness, sitting between the hospital's clinical systems and the payer, so that no request leaves the building unless it is complete.

**One-line positioning:** *CareAuth AI makes a prior authorization request submission-ready before it is submitted.*

---

## 3. Problem Statement

An authorization coordinator preparing an MRI request today must:

1. Identify the patient's payer and plan.
2. Locate the correct policy document, often a PDF of dozens of pages.
3. Determine whether the service is covered and whether prior authorization applies.
4. Determine the required supporting documentation for that service under that plan.
5. Collect those documents from disparate sources.
6. Assemble and transmit the request.
7. Interpret the payer's response, which is frequently a terse rejection code.
8. Determine what to fix and resubmit.

**Consequences:** avoidable rejections caused by incomplete submissions, rework cycles that extend time-to-care, and a knowledge burden that lives in individual staff members' heads rather than in a system.

**Assumption:** the specific volume, cost, and delay figures commonly cited for prior authorization burden are not reproduced in this PRD because they are not verifiable within this project. The problem framing above is structural and does not depend on them.

---

## 4. Target Users

### Primary — Hospital Insurance / Authorization Coordinator
Non-technical. Handles multiple requests concurrently. Measured on throughput and first-pass approval rate. Works in a browser all day. Has no tolerance for a tool that adds steps.

### Secondary (visible in MVP, not optimized for) — Payer Reviewer
Represented by the Mock Insurance Portal. Exists in the MVP only to close the loop and make the demo end-to-end.

### Out of scope for MVP
Physicians, patients, billing, compliance/audit staff, IT administrators.

---

## 5. User Personas

**Persona 1 — Mona, Authorization Coordinator (Primary)**
- 8 years in hospital admin, no clinical training, no technical training.
- Handles 20–35 authorization requests per day across 6 payers.
- Pain: "I don't find out what was missing until the payer rejects it two days later."
- Success looks like: submitting fewer requests, but having more of them approved on the first attempt.
- Trust requirement: she will not act on an AI statement she cannot verify. She needs to see the policy text.

**Persona 2 — Karim, Payer Reviewer (Secondary, simulated)**
- Reviews inbound authorization requests, approves/rejects/requests more information.
- Rejects on documentation insufficiency far more often than on clinical grounds.
- In the MVP he is a scripted actor plus a manual override screen.

---

## 6. Goals

| ID | Goal | Measure |
|---|---|---|
| G1 | Prevent submission of incomplete requests | System blocks `SUBMIT` while any mandatory document is missing. 100% enforcement. |
| G2 | Make every AI decision verifiable | Every coverage decision renders at least one policy citation with document title, section reference, and a verbatim snippet. |
| G3 | Reduce interpretation effort on rejections | Every payer rejection produces a classified reason, a plain-language explanation, and an ordered checklist of ≤5 actions. |
| G4 | Demonstrate a complete lifecycle | The full demo scenario (§33) runs end to end without a manual database edit or code change. |
| G5 | Stay buildable | Feature-complete and integrated by T+7h, leaving 2h for testing and demo rehearsal. |

---

## 7. Non-Goals

Explicitly excluded from this MVP. These are not "later in the day" items; they are out.

- Real EHR, HL7/FHIR, or hospital system integration
- Real payer APIs or clearinghouse connectivity
- Real patient identity, MPI, or eligibility verification
- Claims adjudication, payments, remittance
- Any form of medical diagnosis, triage, or treatment recommendation
- Clinical appropriateness judgment (whether the MRI is *medically* warranted)
- Production HIPAA/PHI controls, encryption at rest, BAAs
- Authentication, authorization, RBAC, multi-tenancy, user management
- OCR, document content extraction, document authenticity verification
- Email/Gmail/Outlook integration
- Microservices, Kubernetes, message queues, background workers
- Analytics dashboards beyond simple status counters
- Free-form chat interface
- Mobile responsive design beyond "does not break"

---

## 8. Product Scope

### In scope
1. Authorization request creation with patient, plan, service, physician, and clinical context.
2. Document attachment with user-declared document type.
3. Coverage determination with RAG-retrieved policy evidence.
4. Required-vs-present document gap analysis with explanation.
5. Submission gating based on combined assessment.
6. Structured authorization packet generation.
7. Mock payer receipt and response (approve / reject / more info), scripted or manual.
8. Rejection analysis with classified reason and resubmission checklist.
9. Document upload → re-analysis → resubmission loop.
10. Full request timeline.

### Simulated
Payer system, patient records (seeded), insurance policies (authored mock text), physician records, document contents.

### Data seeded before demo
2 payers, 3 plans, 4 services, 5 policy documents, 3 patients, 1 coverage rules table.

---

## 9. Core User Journey

```
Coordinator opens Dashboard
        ↓
"New Authorization Request"
        ↓
Selects patient · payer · plan · service · physician · clinical context
        ↓
Attaches documents (declares type for each)
        ↓
[Analyze Request]
        ↓
Orchestrator fans out ──┬── Coverage Agent (RAG)
                        └── Documentation Agent
        ↓ (parallel, joined)
Combined Assessment rendered
        ↓
   ┌────────────────────┴────────────────────┐
   │                                         │
NEEDS_DOCUMENTS                    READY_FOR_SUBMISSION
   │                                         │
Coordinator uploads missing doc     [Generate & Submit]
   │                                         ↓
   └──── Re-analyze ────┘            Communication Agent builds packet
                                             ↓
                                    Mock Payer responds
                                             ↓
              ┌──────────────┬───────────────┴──────────────┐
          APPROVED        REJECTED                  MORE_INFO_REQUIRED
              │               │                              │
            Done      Communication Agent analyses response  │
                              └──────────────┬───────────────┘
                                             ↓
                              Explanation + resubmission checklist
                                             ↓
                              Upload → Re-analyze → Resubmit
```

**Design principle applied:** the coordinator never sees a raw AI blob. Every AI output resolves into one of three UI states: *this is fine*, *this is blocked and here is exactly why*, *do these things next*.

---

## 10. Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-1 | Create an authorization request from seeded patients, plans, and services | Must |
| FR-2 | Attach one or more documents to a request with a declared document type | Must |
| FR-3 | Trigger AI analysis on demand; re-trigger after any document change | Must |
| FR-4 | Return a coverage determination with status, reason, and ≥1 policy citation | Must |
| FR-5 | Return a document gap analysis listing required, present, missing, and unrecognized documents | Must |
| FR-6 | Compute a combined `ready_for_submission` boolean from both agent outputs | Must |
| FR-7 | Block the submit action while `ready_for_submission` is false | Must |
| FR-8 | Generate a structured, human-readable authorization packet | Must |
| FR-9 | Submit the packet to the mock payer and persist the submission | Must |
| FR-10 | Receive and persist a payer decision (approved / rejected / more_info_required) | Must |
| FR-11 | On a non-approval, produce a classified reason, plain-language explanation, and ordered checklist | Must |
| FR-12 | Allow document upload post-rejection and return the request to the analysis loop | Must |
| FR-13 | Persist and render a chronological event timeline per request | Must |
| FR-14 | Provide a payer-side portal listing submissions with approve/reject/more-info actions | Must |
| FR-15 | Show status counters on a dashboard | Must |
| FR-16 | Persist every AI agent invocation with input hash, output JSON, model, and latency | Must |
| FR-17 | Render a global disclaimer that CareAuth AI is decision support, not a clinical or coverage authority | Must |
| FR-18 | Reject a submit attempt server-side even if the client sends one | Must |

---

## 11. Detailed Feature Requirements

### F1 — Create Authorization Request

**Purpose.** Capture the minimum structured input required for coverage and documentation analysis.

**User story.** *As a coordinator, I want to create a request by selecting a patient, plan, and service so that the system can analyze it without me hunting through policy PDFs.*

**Inputs**
| Field | Type | Source | Required |
|---|---|---|---|
| `patient_id` | select | seeded patients | Yes |
| `plan_id` | select | seeded plans (filtered by payer) | Yes |
| `member_number` | text | free text, prefilled from patient | Yes |
| `service_id` | select | seeded service catalog | Yes |
| `physician_name` | text | free text | Yes |
| `physician_id_mock` | text | free text | No |
| `clinical_context` | textarea, 20–2000 chars | free text | Yes |
| `urgency` | select: routine / urgent | — | No, default routine |
| documents[] | file + declared `doc_type` | upload | No at create time |

**Processing**
1. Validate required fields server-side; reject with field-level errors.
2. Persist `authorization_requests` row with `status = DRAFT`.
3. Store uploaded files to local disk; persist `documents` rows with declared type.
4. Emit `REQUEST_CREATED` and one `DOCUMENT_UPLOADED` event per file.

**Outputs.** `AuthorizationRequest` object with `id`, `status = DRAFT`, and attached document list.

**Acceptance criteria**
- AC-1.1 A request cannot be created without patient, plan, member number, service, physician, and clinical context.
- AC-1.2 `clinical_context` under 20 characters is rejected with an inline message.
- AC-1.3 Every uploaded file has a declared `doc_type` selected from the enum; upload without a type is rejected client-side and server-side.
- AC-1.4 Files >10MB or outside `pdf/png/jpg/jpeg/docx` are rejected with a clear message.
- AC-1.5 The created request appears on the dashboard within one refresh.

**Dependencies.** Seeded reference data (BE). Document type enum frozen in the API contract.

---

### F2 — AI Coverage Check

**Purpose.** Determine whether the requested service is covered under the selected plan, whether prior authorization applies, and show the policy text that says so.

**User story.** *As a coordinator, I want to see whether this service needs prior authorization and read the exact policy clause, so that I can trust the answer without opening the policy PDF.*

**Inputs.** `plan_id`, `service_id`, `service_name`, `clinical_context`, `urgency`.

**Processing**
1. Build a retrieval query: `"{service_name} {plan_name} prior authorization coverage requirements"`.
2. Embed the query; cosine-rank against the in-memory policy chunk index; take top-k (k=4) above a similarity floor of 0.25.
3. Look up the deterministic `coverage_rules` row for `(plan_id, service_id)`.
4. Call the LLM with: retrieved chunks, the service, the plan, the clinical context, and the rule row, with instructions to (a) produce the reason text and any conditions, (b) select which retrieved chunks constitute the supporting evidence, and (c) **never contradict the rule row**.
5. If no rule row exists, `status = "unknown"` and the agent must say so rather than guess. (This is the anti-hallucination fallback.)
6. Derive `evidence_strength`: `high` if rule row exists AND top chunk score ≥ 0.45; `medium` if rule row exists AND top score ≥ 0.25; `low` otherwise.
7. Persist the full output to `ai_analyses`.

**Outputs.** `CoverageResult` (§14.1).

**Acceptance criteria**
- AC-2.1 Every non-`unknown` result carries ≥1 evidence item with `policy_document_title`, `section_ref`, and a verbatim `snippet` that exists in `policy_chunks`.
- AC-2.2 The returned `status` always equals the `coverage_rules` value when a rule exists. Verified by a test asserting rule-vs-output equality across all seeded pairs.
- AC-2.3 When no rule exists, `status = "unknown"`, `requires_prior_authorization = null`, and the UI shows "Cannot determine from available policies" rather than a guess.
- AC-2.4 Agent P95 latency ≤ 8 seconds.
- AC-2.5 Agent returns valid JSON conforming to the schema on 10/10 consecutive runs of the demo scenario.

**Dependencies.** RAG index built (AI-1). Seeded `coverage_rules` and `policy_documents` (BE + AI-1).

---

### F3 — Missing Documents Detection

**Purpose.** Determine the required document set for this service and plan, compare against what is attached, and explain each gap.

**User story.** *As a coordinator, I want to know what is missing before I submit, and why the payer needs it, so that I don't get rejected two days later.*

**Inputs.** `plan_id`, `service_id`, attached `documents[]` (with declared types), `clinical_context`, coverage rule row.

**Processing**
1. Read `required_document_types` from `coverage_rules` for `(plan_id, service_id)`. **This is deterministic — the LLM does not invent the list.**
2. Set-difference the required types against the declared types of attached documents.
3. Flag attached documents whose type is not in the required set as `unrecognized` (not an error; surfaced as informational).
4. Call the LLM to produce, for each missing document: a human label, a `why_required` sentence grounded in the retrieved policy chunk, and a `how_to_obtain` hint.
5. Set `ready_for_submission = (mandatory missing count == 0)`.
6. Persist to `ai_analyses`.

**Outputs.** `DocumentationResult` (§14.2).

**Acceptance criteria**
- AC-3.1 The required list is byte-identical to `coverage_rules.required_document_types` for the pair. The LLM cannot add or remove entries.
- AC-3.2 `ready_for_submission` is false whenever any mandatory required type has no attached document.
- AC-3.3 Every missing document renders a `why_required` string of ≥1 sentence.
- AC-3.4 Uploading a missing document type and re-analyzing flips `ready_for_submission` to true with no other change.
- AC-3.5 Agent P95 latency ≤ 6 seconds.

**Dependencies.** Document type enum. `coverage_rules` seed. Upload endpoint (BE).

**Explicit non-requirement.** The agent does not open, read, parse, or validate file contents. A file declared as `physician_order` is treated as a physician order. **Assumption:** for MVP purposes, declared type is trusted. Content verification is roadmap item R3.

---

### F4 — Submission & Payer Response

**Purpose.** Turn an approved-for-submission request into a structured packet, transmit it to the mock payer, and record the decision.

**User story.** *As a coordinator, I want the system to assemble and send the authorization request so that I don't retype the same information into a payer portal.*

**Inputs.** Full request with agent outputs and document list.

**Processing**
1. Server re-validates `ready_for_submission` from the latest persisted analysis. If false, return `409 SUBMISSION_BLOCKED`. **The gate is server-side, not a disabled button.**
2. Communication Agent operation `generate_packet` produces the packet narrative and structured summary.
3. Persist `insurance_submissions` row with `submission_number` (format `PA-{YYYYMMDD}-{seq}`), full payload snapshot, and timestamp.
4. Transition request to `SUBMITTED`, emit `SUBMITTED` event.
5. Mock payer responds:
   - **Scripted mode (default):** deterministic response from `mock_payer_script` keyed on `(service_id, attempt_number)`.
   - **Manual mode:** submission sits in the payer portal awaiting a human action.
6. Persist `insurance_responses`, transition request state, emit event.

**Outputs.** `SubmissionPacket` + `InsuranceResponse`.

**Acceptance criteria**
- AC-4.1 A direct `POST /requests/{id}/submit` on a `NEEDS_DOCUMENTS` request returns 409 and does not create a submission.
- AC-4.2 The packet includes patient, member number, payer, plan, service, physician, clinical narrative, and an enumerated attached-document list.
- AC-4.3 The packet is rendered in the UI before or immediately after sending, and is retrievable from the timeline afterwards.
- AC-4.4 In scripted mode, attempt 1 for MRI Brain returns `rejected / insufficient_clinical_documentation`; attempt 2 returns `approved`.
- AC-4.5 Every submission and every response is visible in the request timeline with a timestamp.

**Dependencies.** F2 + F3 outputs persisted. Mock payer service (BE). Packet template (AI-3).

---

### F5 — Rejection / Resolution Assistant

**Purpose.** Convert a payer response into a classified reason, a plain-language explanation, and an ordered list of actions.

**User story.** *As a coordinator, I want to be told exactly what to fix, in order, so that my resubmission is approved.*

**Inputs.** `insurance_responses` row (decision, reason_code, reason_text), original request, current document list, prior agent outputs.

**Processing**
1. Classify `reason_code` into one of: `insufficient_clinical_documentation`, `missing_document`, `service_not_covered`, `authorization_not_required`, `eligibility_issue`, `administrative_error`, `other`.
2. Generate a plain-language explanation at roughly a 9th-grade reading level, referencing the payer's stated reason without embellishing it.
3. Map the classification to concrete actions. Where the action is "attach document X", `X` must be a valid `doc_type` from the enum so the UI can deep-link the upload control.
4. Produce an ordered `resubmission_checklist` of ≤5 items.
5. Transition request to `ACTION_REQUIRED`.

**Outputs.** `ResolutionResult` (§14.3).

**Acceptance criteria**
- AC-5.1 The explanation never introduces a rejection reason the payer did not state.
- AC-5.2 Every `recommended_action` of kind `upload_document` carries a valid `doc_type`.
- AC-5.3 Checklist items are ordered and ≤5.
- AC-5.4 Completing all checklist items and re-analyzing yields `READY_FOR_SUBMISSION`.
- AC-5.5 Resubmission creates a new `insurance_submissions` row with `attempt_number = 2`; the original submission and response remain visible in the timeline.

**Dependencies.** F4. Document type enum.

---

## 12. AI Agent Architecture

Three agents, one orchestrator. No agent calls another agent. No agent has memory beyond what the orchestrator passes it. All communication is structured JSON.

```
                POST /requests/{id}/analyze
                            ↓
                     Orchestrator
                            ↓
        ┌───────────────────┴───────────────────┐
        ↓ (parallel)                            ↓
  Coverage Agent                       Documentation Agent
  · RAG retrieval                      · Deterministic required list
  · LLM reason + evidence selection    · Set difference
  · Rule-bound status                  · LLM why/how text
        └───────────────────┬───────────────────┘
                            ↓
              Combined Assessment (deterministic join)
                            ↓
                  ready_for_submission


       POST /requests/{id}/submit ──→ Communication Agent :: generate_packet
       Payer response received  ──→ Communication Agent :: analyze_response
```

### Agent 1 — Coverage Agent (AI Dev 1)
- **Owns:** the RAG index, retrieval, coverage reasoning, evidence selection.
- **Does not:** decide the required document list, generate payer-facing text, judge clinical appropriateness.
- **Hard constraint:** cannot output a `status` that contradicts the `coverage_rules` row. Enforced by post-validation in code, not by prompt alone.

### Agent 2 — Documentation Agent (AI Dev 2)
- **Owns:** required-vs-present reconciliation and gap explanation.
- **Does not:** read document contents, diagnose, determine coverage.
- **Hard constraint:** the required list is injected, not generated. Post-validation asserts set equality with the rule row.

### Agent 3 — Communication & Resolution Agent (AI Dev 3)
Two named operations behind one agent module:
- `generate_packet(request) → SubmissionPacket`
- `analyze_response(request, response) → ResolutionResult`
- **Does not:** decide whether to submit, decide coverage, contact anything real.

### Orchestrator (AI Dev 3)
Pure Python, no LLM. Responsibilities: fan out, join, apply the combined rule, handle per-agent failure, persist analyses, emit events.

**Combined rule (deterministic):**
```python
ready_for_submission = (
    coverage.status in ("covered", "prior_authorization_required")
    and coverage.status != "unknown"
    and documentation.ready_for_submission
)
```

**Failure handling.** If one agent throws or returns unparseable JSON, the orchestrator retries once with a repair instruction. On second failure it returns a partial assessment with that agent marked `status: "error"`, sets `ready_for_submission = false`, and the UI shows a "Re-run analysis" button. **A failed agent never yields an optimistic result.**

---

## 13. RAG Architecture

### Recommendation: in-memory NumPy cosine similarity. No vector database.

**Rationale.** The knowledge base is 5 short documents producing roughly 40 chunks. Every vector database option costs setup time and adds an operational dependency that a one-day build cannot justify. At 40 vectors, brute-force cosine is instantaneous and takes ~15 lines.

**Rejected alternatives:**

| Option | Verdict |
|---|---|
| Chroma / Qdrant / Weaviate | Rejected. 45–90 min setup, new dependency, zero retrieval quality gain at n=40. |
| pgvector | Rejected. Requires Postgres + extension. MVP uses SQLite. |
| No retrieval, stuff all policies into the prompt | Tempting and would work at this size, but produces no chunk-level `section_ref` for citation, which is a core requirement (§23). Rejected. |
| BM25 / keyword only | Viable fallback. Keep as the offline contingency if the embedding API is unreachable. |

### Pipeline

```
5 policy .md files (hand-authored)
        ↓
Chunk by markdown heading, max 500 tokens, 50-token overlap
        ↓
Each chunk retains: policy_document_id, title, section_ref (e.g. "§4.2"), text
        ↓
Embed once at startup (text-embedding-3-small or equivalent)
        ↓
Persist embeddings to policy_chunks.embedding (BLOB) — rebuild only when a policy file changes
        ↓
Load into a single NumPy (n, d) matrix at process start
        ↓
Retrieve: cosine top-k (k=4), similarity floor 0.25
        ↓
Coverage Agent context
```

### Knowledge base contents (to be authored by AI Dev 1 in the first hour)

```
policies/
├── abc_coverage_policy.md          — general coverage, exclusions, definitions
├── abc_mri_authorization.md        — §4.2 MRI prior auth requirement + criteria
├── abc_required_documents.md       — §6.1 documentation matrix by service class
├── xyz_coverage_policy.md
└── xyz_authorization_policy.md
```

**Authoring requirement.** Each file uses `## §N.N Title` headings so `section_ref` extraction is a regex, not a judgment call. Each file is 400–900 words. Write them to *sound* like real policy documents (defined terms, cross-references, conditions) because the citations appear on screen during the demo.

**Assumption.** All policy text is fabricated for demonstration. Every screen rendering policy text carries the label "Sample policy — illustrative only."

### Retrieval quality safeguard
Because retrieval feeds evidence but not the decision, poor retrieval degrades the citation quality, not the correctness of the workflow. This is the architectural reason the rules table exists.

---

## 14. AI Input/Output Contracts

All agents return JSON matching these schemas. All are validated with Pydantic on the Python side and mirrored as TypeScript interfaces on the frontend. **The contract is frozen at T+45m.**

### 14.1 Coverage Agent

**Input**
```json
{
  "request_id": "req_01H...",
  "plan": { "id": "plan_abc_gold", "payer_name": "ABC Insurance", "plan_name": "ABC Gold PPO" },
  "service": { "id": "svc_mri_brain", "code": "70551", "name": "MRI Brain without contrast" },
  "clinical_context": "45yo male, persistent headaches 6 weeks, failed conservative management...",
  "urgency": "routine"
}
```

**Output**
```json
{
  "agent": "coverage",
  "version": "1.0",
  "request_id": "req_01H...",
  "status": "prior_authorization_required",
  "requires_prior_authorization": true,
  "reason": "MRI Brain is a covered benefit under ABC Gold PPO but is designated as an advanced imaging service requiring prior authorization before scheduling.",
  "conditions": [
    "Documented failure of conservative management for at least 4 weeks",
    "Referral from a treating physician"
  ],
  "evidence": [
    {
      "chunk_id": "chunk_abc_mri_004",
      "policy_document_title": "ABC Insurance MRI Authorization Policy",
      "section_ref": "§4.2",
      "snippet": "Advanced imaging services, including magnetic resonance imaging of the brain, require prior authorization when performed in an outpatient setting.",
      "similarity": 0.61
    }
  ],
  "evidence_strength": "high",
  "top_similarity": 0.61,
  "rule_matched": true,
  "model": "gpt-4o-mini",
  "latency_ms": 4120,
  "generated_at": "2026-08-27T09:41:22Z"
}
```

**Changes from the original schema and why:**
- `confidence: 0.91` → removed. Replaced by `evidence_strength` (derived, explainable), `top_similarity` (real number from retrieval), and `rule_matched` (boolean fact). A judge can be told exactly how each is computed.
- `requirements: []` → renamed `conditions`, because "requirements" collided with document requirements owned by Agent 2.
- `evidence` items now carry `chunk_id` and `similarity` so any citation can be traced back to the source chunk.
- Added `status: "unknown"` as a valid value. The original schema had no way to express "I cannot determine this," which is precisely the state where an LLM hallucinates.

---

### 14.2 Documentation Agent

**Output**
```json
{
  "agent": "documentation",
  "version": "1.0",
  "request_id": "req_01H...",
  "ready_for_submission": false,
  "required_documents": [
    { "doc_type": "insurance_card", "label": "Insurance Card", "mandatory": true, "source_section": "§6.1" },
    { "doc_type": "physician_order", "label": "Physician Order", "mandatory": true, "source_section": "§6.1" },
    { "doc_type": "clinical_notes", "label": "Clinical Notes", "mandatory": true, "source_section": "§6.1" },
    { "doc_type": "prior_imaging_report", "label": "Previous Imaging Report", "mandatory": true, "source_section": "§4.2" }
  ],
  "present_documents": [
    { "doc_type": "insurance_card", "document_id": "doc_a1", "file_name": "card.pdf" },
    { "doc_type": "physician_order", "document_id": "doc_a2", "file_name": "order.pdf" },
    { "doc_type": "clinical_notes", "document_id": "doc_a3", "file_name": "notes.pdf" }
  ],
  "missing_documents": [
    {
      "doc_type": "prior_imaging_report",
      "label": "Previous Imaging Report",
      "mandatory": true,
      "why_required": "ABC Gold PPO requires prior imaging history for advanced imaging requests to establish that the study is not duplicative.",
      "how_to_obtain": "Request from the hospital PACS/radiology department or the referring physician's office.",
      "source_section": "§4.2"
    }
  ],
  "unrecognized_documents": [],
  "blocking_summary": "This request cannot be submitted. 1 required document is missing: Previous Imaging Report.",
  "model": "gpt-4o-mini",
  "latency_ms": 3050,
  "generated_at": "2026-08-27T09:41:21Z"
}
```

**Changes from the original schema:**
- `issues: []` → replaced by `unrecognized_documents` and `blocking_summary`. "Issues" was an undefined bucket, which in practice becomes a dumping ground the frontend cannot render.
- `mandatory` flag added, because `ready_for_submission` must be computable without inference.
- `source_section` added on every requirement so the documentation view is also evidence-backed, not just the coverage view.

---

### 14.3 Communication & Resolution Agent

**Operation `generate_packet` — output**
```json
{
  "agent": "communication",
  "operation": "generate_packet",
  "version": "1.0",
  "submission_number": "PA-20260827-0007",
  "packet_markdown": "## Prior Authorization Request\n\n**Patient:** Ahmed Ali...",
  "packet_structured": {
    "patient": { "name": "Ahmed Ali", "dob": "1981-03-14", "member_number": "ABC-4471-9920" },
    "payer": "ABC Insurance",
    "plan": "ABC Gold PPO",
    "service": { "code": "70551", "name": "MRI Brain without contrast" },
    "physician": { "name": "Dr. Hala Mansour", "id": "NPI-MOCK-2211" },
    "clinical_justification": "...",
    "attached_documents": ["Insurance Card", "Physician Order", "Clinical Notes", "Previous Imaging Report"],
    "policy_basis": [{ "policy_document_title": "ABC Insurance MRI Authorization Policy", "section_ref": "§4.2" }]
  },
  "model": "gpt-4o-mini",
  "latency_ms": 5200
}
```

**Operation `analyze_response` — output**
```json
{
  "agent": "communication",
  "operation": "analyze_response",
  "version": "1.0",
  "decision": "rejected",
  "reason_classification": "insufficient_clinical_documentation",
  "payer_reason_verbatim": "Clinical documentation insufficient to establish medical necessity.",
  "explanation": "The payer accepted that this service is covered, but did not find enough written clinical detail to show why the scan is needed now. This is a documentation gap, not a coverage denial.",
  "is_appealable": true,
  "recommended_actions": [
    {
      "order": 1,
      "kind": "upload_document",
      "doc_type": "physician_notes_detailed",
      "label": "Attach detailed physician progress notes",
      "detail": "Notes should state symptom duration, conservative treatments already tried, and why imaging is needed now."
    },
    {
      "order": 2,
      "kind": "edit_field",
      "field": "clinical_context",
      "label": "Expand the clinical justification",
      "detail": "Include the failed conservative management timeline referenced in §4.2."
    }
  ],
  "resubmission_checklist": [
    "Attach detailed physician progress notes",
    "Expand clinical justification to include conservative management history",
    "Confirm all four required documents remain attached",
    "Resubmit as attempt 2"
  ],
  "model": "gpt-4o-mini",
  "latency_ms": 4400
}
```

**Changes from the original schema:**
- Split one flat object into two operations with distinct schemas. The original mixed packet generation and rejection analysis into one shape where most fields were null on any given call, which forces the frontend to guess.
- `recommended_actions` became typed objects with `kind` and `doc_type`, so the UI can render an actual upload button rather than a paragraph the coordinator must interpret.
- Added `payer_reason_verbatim` alongside `explanation` so the coordinator can always see the payer's own words next to the AI's paraphrase. This is a trust requirement.

---

## 15. Workflow / State Machine

### States (7)

| State | Meaning |
|---|---|
| `DRAFT` | Created, not yet analyzed |
| `ANALYZING` | Orchestrator running (transient) |
| `NEEDS_DOCUMENTS` | Analysis complete, blocked on missing documents |
| `READY_FOR_SUBMISSION` | Analysis complete, no blockers |
| `SUBMITTED` | Packet sent, awaiting payer |
| `APPROVED` | Terminal success |
| `ACTION_REQUIRED` | Payer rejected or requested more info; resolution guidance available |

`REJECTED` and `MORE_INFO_REQUIRED` are **response outcomes stored on `insurance_responses`**, not request states. Both drive the request to `ACTION_REQUIRED`. This is a deliberate reduction: from the coordinator's point of view the required behaviour is identical, and two states with identical UI and identical exits are two states too many.

### Transitions

| From | Event | To | Guard |
|---|---|---|---|
| `DRAFT` | `ANALYZE` | `ANALYZING` | request has required fields |
| `ANALYZING` | `ANALYSIS_COMPLETE` | `NEEDS_DOCUMENTS` | `ready_for_submission == false` |
| `ANALYZING` | `ANALYSIS_COMPLETE` | `READY_FOR_SUBMISSION` | `ready_for_submission == true` |
| `ANALYZING` | `ANALYSIS_FAILED` | `DRAFT` | both agents errored after retry |
| `NEEDS_DOCUMENTS` | `ANALYZE` | `ANALYZING` | triggered after document upload |
| `READY_FOR_SUBMISSION` | `ANALYZE` | `ANALYZING` | document or field changed |
| `READY_FOR_SUBMISSION` | `SUBMIT` | `SUBMITTED` | server re-validates readiness |
| `SUBMITTED` | `PAYER_APPROVED` | `APPROVED` | — |
| `SUBMITTED` | `PAYER_REJECTED` | `ACTION_REQUIRED` | — |
| `SUBMITTED` | `PAYER_MORE_INFO` | `ACTION_REQUIRED` | — |
| `ACTION_REQUIRED` | `ANALYZE` | `ANALYZING` | after document upload or field edit |
| `APPROVED` | — | — | terminal |

**Invariant:** any mutation of documents or request fields invalidates the current analysis. The frontend must show a "This analysis is out of date — re-analyze" banner, and the server must refuse `SUBMIT` when `ai_analyses.input_hash != current_input_hash`. This closes the "upload a document then submit without re-analyzing" hole.

---

## 16. Frontend Requirements

**Stack.** Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui. Server components for reads, client components for forms and polling. No state management library. TanStack Query optional; `fetch` + `router.refresh()` is sufficient.

**Routes (4).**

### `/` — Dashboard
- Six status counters: Total, Draft, Needs Documents, Submitted, Approved, Action Required.
- Table of requests: patient, payer, service, status badge, last updated, row link.
- Primary CTA: "New Authorization Request".
- No filtering, sorting, or search in MVP.

### `/requests/new` — Create Request
- Single-column form, sections: Patient & Insurance, Service, Physician & Clinical Context, Documents.
- Document uploader: file input + **mandatory** document-type select per file. Files appear as chips with type badge and remove action.
- Inline validation. Submit button label: "Create & Analyze".

### `/requests/[id]` — Request Detail
The core screen. Vertical layout, four sections:

1. **Header** — patient, payer/plan, service, status badge, submission number if submitted.
2. **AI Assessment**
   - *Coverage card:* status pill, reason paragraph, conditions list, expandable "Policy Evidence" showing document title, `§section`, and verbatim snippet. Evidence strength shown as a labelled badge with a tooltip explaining derivation.
   - *Documentation card:* required documents as a checklist with ✅/❌ per item; each ❌ expands to `why_required` + `how_to_obtain` + an inline upload button pre-set to that `doc_type`.
   - *Blocking banner* when not ready: red, states the count and names the missing documents.
   - Actions: `Upload Document` · `Re-analyze` · `Continue to Submission` (disabled with a tooltip explaining why, when blocked).
3. **Resolution panel** — rendered only in `ACTION_REQUIRED`. Payer verbatim reason, AI explanation, ordered actions with inline upload buttons, resubmission checklist with checkboxes (client-side only), `Resubmit` button.
4. **Timeline** — reverse-chronological event list with icons and timestamps. Submission events expand to show the packet.

**Loading behaviour (required, not optional).** During `ANALYZING`, render two independent skeleton cards. Coverage and Documentation resolve independently and each renders the moment its result lands. Poll `GET /requests/{id}` every 1500ms while status is `ANALYZING`. A single 20-second spinner is a rejected design.

### `/payer` — Mock Insurance Portal
- Visually distinct (different accent colour, "ABC Insurance — Reviewer Console" header) so it is obviously a different system during the demo.
- Table of submissions: submission number, patient, service, document count, status, submitted at.
- Row expands to show the full packet.
- Actions: `Approve` · `Request More Information` · `Reject` (reject and more-info open a reason textarea with 4 preset reason chips).
- Toggle: **Scripted / Manual** mode.

**Global.** Persistent footer disclaimer: *"CareAuth AI is an administrative decision-support tool. It does not provide medical advice and does not make coverage determinations. All policy content shown is sample data."*

---

## 17. Backend Requirements

**Stack recommendation: Python + FastAPI + SQLite (SQLModel/SQLAlchemy) + local disk storage, single process, single repo.**

**Rationale for Python over Node:** three of five developers are writing Python AI code. A Node backend introduces a cross-language service boundary, a second deploy target, and an HTTP hop between the orchestrator and the data it needs. FastAPI gives Pydantic validation of agent outputs for free, which is directly load-bearing for §14. The frontend developer is unaffected either way because they consume HTTP.

**Tradeoff, stated honestly:** if the backend developer is meaningfully stronger in Node/TypeScript than in Python, that individual productivity difference outweighs the architectural neatness. Decide this in the first 15 minutes and do not revisit it.

**SQLite over Postgres:** zero setup, file-backed, trivially resettable between demo runs (`cp seed.db app.db`). The demo-reset property alone justifies it.

**Modules**
```
app/
├── api/          routers: requests, documents, analysis, submissions, payer, reference
├── models/       SQLModel entities
├── schemas/      Pydantic request/response + agent contracts
├── services/     request_service, document_service, submission_service, event_service
├── agents/       coverage/, documentation/, communication/, orchestrator.py, rag/
├── mock_payer/   scripted responder + manual queue
├── seed/         reference data, policies/, seed.py
└── storage/      local file writes to ./uploads/{request_id}/{uuid}.{ext}
```

**Responsibilities:** CRUD, state machine enforcement, document metadata, orchestrator invocation, analysis persistence, input hashing, mock payer, event emission, structured logging.

**State machine enforcement lives in `request_service`, not in the router and not in the frontend.** Every transition goes through one function that validates the guard and emits the event. This is the single most important structural decision in the backend.

---

## 18. Data Model

```sql
patients(id, full_name, date_of_birth, gender, mock_national_id, created_at)

insurance_plans(id, payer_name, plan_name, plan_code, notes)

services(id, code, name, category)            -- 70551 MRI Brain, 74177 CT Abdomen, etc.

policy_documents(id, plan_id FK, title, doc_kind, raw_text, created_at)

policy_chunks(id, policy_document_id FK, chunk_index, section_ref, text,
              embedding BLOB, token_count)

coverage_rules(id, plan_id FK, service_id FK,
               status,                          -- covered | not_covered | prior_authorization_required
               requires_prior_authorization BOOL,
               required_document_types JSON,    -- ["insurance_card","physician_order",...]
               conditions JSON,
               primary_policy_document_id FK,
               primary_section_ref)

authorization_requests(id, patient_id FK, plan_id FK, service_id FK,
                       member_number, physician_name, physician_id_mock,
                       clinical_context, urgency,
                       status, current_input_hash,
                       created_at, updated_at)

documents(id, request_id FK, doc_type, file_name, mime_type, size_bytes,
          storage_path, uploaded_at, uploaded_after_rejection BOOL)

ai_analyses(id, request_id FK, agent, operation, version,
            input_hash, output_json, model, latency_ms, status, error_text, created_at)

insurance_submissions(id, request_id FK, submission_number, attempt_number,
                      packet_markdown, packet_json, submitted_at)

insurance_responses(id, submission_id FK, decision, reason_code, reason_text,
                    responder, responded_at)

request_events(id, request_id FK, event_type, actor, payload_json, created_at)
```

**Document type enum (frozen at T+45m — the frontend, both AI agents, and the seed data all depend on this list):**
```
insurance_card
physician_order
clinical_notes
physician_notes_detailed
prior_imaging_report
lab_results
referral_letter
prior_auth_history
other
```

**`current_input_hash`** = SHA256 of `(clinical_context, service_id, plan_id, sorted document doc_types + ids)`. Compared against `ai_analyses.input_hash` to detect stale analyses.

---

## 19. API Requirements

Base: `/api/v1`. JSON. No auth in MVP.

| Method | Path | Purpose |
|---|---|---|
| GET | `/reference/patients` | Seeded patients |
| GET | `/reference/plans` | Seeded payers + plans |
| GET | `/reference/services` | Service catalog |
| GET | `/reference/document-types` | Document type enum with labels |
| POST | `/requests` | Create request (multipart: fields + files + declared types) |
| GET | `/requests` | List with status counters |
| GET | `/requests/{id}` | Full detail: request, documents, latest analyses, submissions, responses, events |
| POST | `/requests/{id}/documents` | Upload document (multipart: file + doc_type) |
| DELETE | `/requests/{id}/documents/{doc_id}` | Remove document |
| PATCH | `/requests/{id}` | Update `clinical_context` / `urgency` |
| POST | `/requests/{id}/analyze` | Run orchestrator (async → poll GET) |
| POST | `/requests/{id}/submit` | Generate packet + send to mock payer |
| GET | `/payer/submissions` | Payer portal queue |
| POST | `/payer/submissions/{id}/decision` | `{decision, reason_code, reason_text}` |
| POST | `/payer/mode` | `{mode: "scripted" \| "manual"}` |
| POST | `/admin/reset` | Wipe transactional data, keep seeds (demo safety) |

**Error contract (uniform):**
```json
{ "error": { "code": "SUBMISSION_BLOCKED", "message": "2 required documents are missing.", "details": { "missing": ["prior_imaging_report"] } } }
```

**Error codes:** `VALIDATION_ERROR` (422), `NOT_FOUND` (404), `INVALID_TRANSITION` (409), `SUBMISSION_BLOCKED` (409), `ANALYSIS_STALE` (409), `AGENT_FAILURE` (502), `FILE_TOO_LARGE` (413), `UNSUPPORTED_FILE_TYPE` (415).

---

## 20. Mock Insurance System

### Scripted mode (default, and the mode used in the live demo)

`mock_payer_script` is a seeded table keyed on `(service_id, attempt_number)`:

| service | attempt | decision | reason_code | reason_text |
|---|---|---|---|---|
| MRI Brain | 1 | `rejected` | `insufficient_clinical_documentation` | "Clinical documentation insufficient to establish medical necessity." |
| MRI Brain | 2 | `approved` | — | "Approved. Authorization number ABC-AUTH-88214. Valid 60 days." |
| CT Abdomen | 1 | `more_info_required` | `missing_document` | "Prior imaging report required for comparison." |
| CT Abdomen | 2 | `approved` | — | — |
| Specialist Consult | 1 | `approved` | — | — |
| Knee Arthroscopy | 1 | `rejected` | `service_not_covered` | "Procedure excluded under this plan." |

Response is returned after a deliberate 2-second delay so the UI shows a realistic "awaiting payer" state.

### Manual mode
Submission enters the payer portal queue. A human reviewer approves, rejects with reason, or requests more information. Used when a judge asks "can I try it?" — which is the moment the manual mode earns its keep.

**Assumption.** Payer decision logic is entirely fabricated. Real payers use proprietary medical necessity criteria not modelled here. Every payer screen carries a "Simulated payer system" badge.

---

## 21. UX Requirements

The coordinator must be able to answer four questions at any moment without clicking:

| Question | Where it is answered |
|---|---|
| What is happening? | Status badge in the request header, always visible |
| Why is it happening? | Reason paragraph + policy evidence on the coverage card |
| What is missing? | Documentation checklist with ❌ items and a red blocking banner |
| What should I do next? | A single primary action button, contextual to state |

**Rules**
1. **One primary action per state.** `DRAFT` → Analyze. `NEEDS_DOCUMENTS` → Upload Missing Document. `READY_FOR_SUBMISSION` → Continue to Submission. `ACTION_REQUIRED` → Upload & Resubmit. Never two primary buttons.
2. **Disabled buttons must explain themselves.** A disabled Submit renders a tooltip naming the exact blocker.
3. **Evidence is one click away, never zero and never three.** Collapsed by default with a visible "Policy Evidence (§4.2)" affordance.
4. **Missing documents are actionable in place.** Each ❌ row has its own upload control pre-set to that type. The coordinator never navigates away to fix a gap.
5. **AI output is never presented as authority.** Coverage results are framed "Based on ABC Gold PPO policy §4.2" rather than "CareAuth AI has determined".
6. **Stale analysis is loudly flagged.** Changing anything after analysis shows an amber banner and disables Submit.
7. **No blocking full-screen spinners.** Per-card skeletons only.

---

## 22. Error Handling

| Scenario | Behaviour |
|---|---|
| Agent returns invalid JSON | Retry once with a repair prompt; on second failure mark that agent `error`, set `ready_for_submission = false`, show "Analysis incomplete — re-run" |
| Both agents fail | Request returns to `DRAFT`, banner: "Analysis could not complete. Try again." |
| LLM API timeout (>25s) | Abort, mark `error`, same as above |
| Embedding API unreachable at startup | Fall back to BM25 keyword retrieval; log a warning; evidence still cites `section_ref` |
| No coverage rule for the pair | `status = "unknown"`, submission blocked, UI: "This service/plan combination is not in the loaded policy set." |
| Submit on non-ready request | `409 SUBMISSION_BLOCKED` with the missing list |
| Submit with stale analysis | `409 ANALYSIS_STALE`, UI prompts re-analysis |
| File too large / wrong type | `413` / `415` with a plain-language message; other files in the batch still upload |
| Upload with no declared type | `422`, rejected client-side first |
| Payer portal action on an already-decided submission | `409 INVALID_TRANSITION` |
| Duplicate submit (double-click) | Idempotency on `(request_id, attempt_number)`; second call returns the first result |

**Principle:** every failure path leaves the request in a state the coordinator can act on. There is no error that requires a page reload or a database fix.

---

## 23. Explainability Requirements

This is a hard requirement, not a UI nicety. A coverage statement without evidence is unusable in this domain.

| ID | Requirement |
|---|---|
| EX-1 | Every coverage decision renders ≥1 evidence item: policy document title, section reference, verbatim snippet |
| EX-2 | Every snippet must exist verbatim in `policy_chunks`. Validated by substring check before persistence; a snippet that fails validation is dropped and the agent is retried |
| EX-3 | Every required document carries a `source_section` |
| EX-4 | `evidence_strength` is derived and its derivation is disclosed in a tooltip |
| EX-5 | The payer's verbatim rejection text is always displayed adjacent to the AI's paraphrase |
| EX-6 | Every AI-generated region of the UI carries a subtle "AI-generated" marker |
| EX-7 | The system never states a policy fact without a citation. If evidence is absent, the honest output is "unknown" |

**EX-2 is the anti-hallucination control that actually works.** Prompting a model not to hallucinate is a hope. Validating that every quoted snippet exists as a substring of a real chunk is a guarantee.

---

## 24. Non-Functional Requirements

### MVP (must hold on demo day)

| ID | Requirement |
|---|---|
| NFR-1 | AI logic is isolated in `app/agents/`. No LLM call anywhere else. Business logic is testable without an API key. |
| NFR-2 | Frontend↔backend communication is HTTP JSON only. No shared code, no direct DB access from the frontend. |
| NFR-3 | All agent outputs validated against Pydantic schemas before persistence. |
| NFR-4 | Full analysis (both agents, parallel) P95 ≤ 10s. |
| NFR-5 | Non-AI endpoints P95 ≤ 300ms. |
| NFR-6 | Every agent invocation persisted with input hash, output, model, latency. |
| NFR-7 | Structured logs with `request_id` on every line. |
| NFR-8 | Server-side validation on every mutating endpoint. |
| NFR-9 | Full timeline reconstructible from `request_events`. |
| NFR-10 | `POST /admin/reset` restores a clean demo state in <2s. |
| NFR-11 | The app runs from `docker compose up` or two terminal commands. No cloud dependency except the LLM API. |

### Future production (explicitly not built now)

Horizontal scalability, PHI encryption at rest and in transit, audit logging with tamper evidence, HIPAA controls and BAAs, SSO/RBAC, rate limiting, disaster recovery, 99.9% availability, model versioning and evaluation pipelines, human-in-the-loop review queues, data retention policies.

---

## 25. Security Considerations

**Explicitly deferred in MVP:** authentication, authorization, encryption, audit trails, PHI handling controls, secure file storage, input sanitisation beyond validation.

**Minimum bar that must still hold:**

| ID | Control |
|---|---|
| SEC-1 | No real patient data. All records fabricated. Demo data labelled as synthetic on screen. |
| SEC-2 | LLM API key in `.env`, never committed, never sent to the frontend. |
| SEC-3 | File uploads restricted by extension and MIME to `pdf/png/jpg/jpeg/docx`, max 10MB. |
| SEC-4 | Uploaded files stored under a generated UUID, never the original filename, to prevent path traversal. |
| SEC-5 | Uploaded files never executed, never rendered inline as HTML. |
| SEC-6 | Parameterised queries only (ORM). |
| SEC-7 | CORS restricted to the frontend origin. |
| SEC-8 | README states in the first paragraph that this is a demo with no security controls and must not be used with real PHI. |

**Honest statement for the demo:** if asked about HIPAA, the correct answer is "this is a workflow prototype with synthetic data and no production security controls; compliance work is on the roadmap and is substantial." Do not claim HIPAA readiness.

---

## 26. AI Safety / Reliability Considerations

| ID | Control | Mechanism |
|---|---|---|
| AS-1 | **No clinical decisions.** Agents never assess medical necessity, diagnose, or recommend treatment. | System prompt boundary + the fact that no agent is given a decision surface for it. Documentation Agent explicitly instructed to refuse clinical questions. |
| AS-2 | **No invented policy facts.** | EX-2 substring validation. Snippets that fail are dropped. |
| AS-3 | **No invented coverage outcomes.** | Post-validation: if LLM `status` ≠ rule row `status`, the rule wins and a warning is logged. |
| AS-4 | **No invented required documents.** | Required list is injected from the rules table and asserted for set equality post-generation. |
| AS-5 | **Honest uncertainty.** | `status: "unknown"` exists and blocks submission rather than guessing. |
| AS-6 | **No fabricated rejection reasons.** | `payer_reason_verbatim` carried through unmodified and displayed alongside the paraphrase. |
| AS-7 | **Human retains control.** | The system never auto-submits. Every submission requires an explicit human click. |
| AS-8 | **Determinism where it matters.** | `temperature = 0.2` for all agents. |
| AS-9 | **Traceability.** | Every invocation persisted with input hash and output. |
| AS-10 | **Scope refusal.** | If `clinical_context` contains a direct clinical question, agents decline and state their scope. |

**Boundary statement, to be reproduced in the README and stated aloud in the demo:** *CareAuth AI determines whether an administrative request is complete and consistent with the stated policy. It does not determine whether care is appropriate. That judgment belongs to the physician, and the coverage decision belongs to the payer.*

---

## 27. Team Responsibilities

### AI Developer 1 — RAG + Coverage Agent
- Author 5 mock policy documents with `## §N.N` heading structure
- Chunker, embedder, in-memory index, retriever with similarity floor
- Coverage Agent: prompt, structured output, rule post-validation, evidence substring validation
- Deliver: `coverage_agent.analyze(input) -> CoverageResult`
- **Blocks:** BE (analysis endpoint), AI-3 (orchestrator)
- **Blocked by:** contract freeze, `coverage_rules` seed shape

### AI Developer 2 — Documentation Agent
- Required-vs-present reconciliation logic (pure Python)
- LLM layer for `why_required` / `how_to_obtain` / `blocking_summary`
- Set-equality post-validation
- Deliver: `documentation_agent.analyze(input) -> DocumentationResult`
- **Blocks:** AI-3 (orchestrator)
- **Blocked by:** contract freeze, document type enum, `coverage_rules` seed

### AI Developer 3 — Orchestrator + Communication Agent
- Orchestrator: parallel fan-out (`asyncio.gather`), join, combined rule, per-agent failure handling, retry-with-repair
- Communication Agent: `generate_packet` and `analyze_response`
- Owns the JSON repair utility used by all three agents
- Deliver: `orchestrator.run(request_id) -> CombinedAssessment`, `communication_agent.*`
- **Blocks:** BE integration
- **Blocked by:** AI-1 and AI-2 agent interfaces (mitigated: AI-3 codes against stubs from hour 1)

### Frontend Developer
- 4 routes, all components, polling, skeleton states, evidence disclosure, inline upload controls, payer portal
- **Blocked by:** contract freeze at T+45m only. From that point, works entirely against the mock API server until T+5h.
- **Critical:** must not wait for a real backend. If the mock server is not up by T+1h, this is a project-level escalation.

### Backend Developer
- Models, migrations, seeds (patients, plans, services, coverage rules, payer script)
- All endpoints, state machine service, event emission, file storage, input hashing
- **Mock API server serving contract-shaped fixtures — this is the first deliverable, due T+45m, before anything else**
- Mock payer (scripted + manual), `/admin/reset`
- **Blocks:** everyone at T+45m, then FE at T+5h integration
- **Blocked by:** contract freeze

---

## 28. One-Day Implementation Plan

Assumes a 9-hour day starting 09:00. Times are elapsed from T+0.

### Phase 0 — Contract Freeze (T+0 → T+0:45) · **Whole team, one room**
| Task | Owner |
|---|---|
| Agree stack, repo structure, branch strategy | Lead |
| **Freeze all §14 agent schemas** | Lead + 3 AI devs |
| **Freeze document type enum and API paths** | Lead + BE + FE |
| Agree the four demo services and two payers | All |
| Create repo, `.env.example`, README skeleton | BE |

**Exit criterion:** `contracts.py` and `contracts.ts` are committed and pushed. Nothing else starts until this exists. This 45 minutes is the highest-leverage time in the day.

### Phase 1 — Unblock (T+0:45 → T+1:30)
| Owner | Task |
|---|---|
| BE | **Mock API server returning fixture responses for every endpoint.** Push immediately. |
| AI-1 | Author 5 policy documents |
| AI-2 | Build the required-vs-present reconciliation function (no LLM yet) |
| AI-3 | Orchestrator skeleton with stubbed agents returning fixtures |
| FE | Project scaffold, layout, design tokens, API client typed from `contracts.ts` |

**Exit criterion:** FE can `fetch` every endpoint and get contract-shaped data.

### Phase 2 — Parallel Build (T+1:30 → T+5:00)
| Owner | Task |
|---|---|
| BE | Models, seeds (including `coverage_rules` and payer script), real CRUD, upload, state machine service, event emission |
| AI-1 | Chunk → embed → index → retrieve; Coverage Agent + validations |
| AI-2 | Documentation Agent LLM layer + validations |
| AI-3 | Communication Agent both operations; real orchestrator with `asyncio.gather` |
| FE | All four routes fully built against the mock server, including skeleton states and the resolution panel |

**Checkpoint at T+3:00 (10 minutes, standing):** each owner demonstrates their unit working in isolation. Anything not demonstrable is cut or descoped on the spot.

### Phase 3 — Integration (T+5:00 → T+6:30)
| Step | Owners |
|---|---|
| Wire real agents into `/analyze` | BE + AI-3 |
| Point FE at the real backend | FE + BE |
| First full path: create → analyze → blocked | All |
| Wire submit + mock payer | BE + AI-3 |
| Wire resolution panel to `analyze_response` | FE + AI-3 |

**Exit criterion at T+6:30:** the happy path runs end to end at least once.

### Phase 4 — Demo Scenario Hardening (T+6:30 → T+7:45)
- Run the §33 scenario start to finish, five consecutive times
- Fix every break encountered
- Seed the demo request pre-populated so the demo does not begin with form typing
- Verify `POST /admin/reset` restores clean state
- Tune loading copy and latency perception
- Screen-record a full successful run **as a fallback if live fails**

### Phase 5 — Polish & Rehearsal (T+7:45 → T+9:00)
- Nice-to-haves from §30, strictly in priority order, strictly time-boxed
- Two full spoken rehearsals with the actual presenter
- Freeze the code. **Hard rule: no commits in the final 30 minutes.**

### Critical path
```
Contract freeze → Mock API server → FE build (longest single-owner track)
                                 ↘
Contract freeze → Coverage Agent + Orchestrator → Integration → Demo hardening
```
The frontend track and the AI track are roughly equal in length. **The mock API server is the single point of serialisation for the entire day.** If it slips by an hour, the day slips by an hour.

### Anti-patterns to refuse
- Building the RAG index before writing the policy documents
- Frontend waiting for a real endpoint
- Integrating at T+7 instead of T+5
- Any developer adding a feature not in §30 Must Have
- Debugging a nice-to-have after T+7:45

---

## 29. Dependencies

### External
| Dependency | Risk | Mitigation |
|---|---|---|
| LLM API (chat + embeddings) | Outage or rate limit kills the demo | Cache every demo-scenario agent response to disk at T+7:00. A `DEMO_CACHE=1` env flag replays cached responses. **Build this. It is 30 minutes of insurance on the entire day.** |
| Embedding API | Index build fails | BM25 fallback (§22) |
| Node/Python runtimes | Version drift across five machines | Pin versions in the first 15 minutes; `.nvmrc` + `requirements.txt` |

### Internal (ordered)
1. Contract freeze → everything
2. Document type enum → BE seeds, FE uploader, AI-2
3. `coverage_rules` seed → AI-1 and AI-2 both
4. Mock API server → FE
5. Agent interfaces → orchestrator
6. Orchestrator → `/analyze` endpoint
7. `/analyze` → Request Detail screen
8. Submission → payer portal → resolution panel

---

## 30. MVP vs Nice-to-Have

### Must Have — the demo fails without these

| Feature | Owner |
|---|---|
| Create request with documents and declared types | FE + BE |
| Coverage Agent with RAG evidence and citation | AI-1 |
| Documentation Agent with gap detection and explanation | AI-2 |
| Orchestrator with parallel execution and combined assessment | AI-3 |
| Server-side submission gating | BE |
| Packet generation | AI-3 |
| Mock payer, scripted mode | BE |
| Rejection analysis with checklist | AI-3 |
| Upload → re-analyze → resubmit loop | FE + BE |
| Request timeline | FE + BE |
| Dashboard with counters | FE |
| Payer portal with manual actions | FE + BE |
| `/admin/reset` | BE |

### Nice to Have — only after T+7:45, in this order

| # | Feature | Est. |
|---|---|---|
| 1 | Response caching for demo safety | 30m (**do this first, it is really a Must**) |
| 2 | Toast notifications on state transitions | 20m |
| 3 | Packet export as a downloadable file | 25m |
| 4 | Third payer with a differing rule set (shows the system generalises) | 30m |
| 5 | Similarity score badges on evidence items | 15m |
| 6 | Email-preview rendering of the packet | 30m |
| 7 | Document content preview | 40m |
| 8 | Dashboard charts | 30m |
| 9 | Search and filtering | 40m |
| 10 | AI chat interface | **Never.** Directly contradicts §27 of the brief. |

**Rule:** a nice-to-have that touches a Must Have file after T+7:45 is rejected regardless of how small it looks. Regression risk at that hour exceeds any marginal demo value.

---

## 31. Success Metrics

### Functional (binary, verified before demo)
| ID | Criterion |
|---|---|
| SM-1 | Coordinator creates a request with ≥3 documents |
| SM-2 | Coverage Agent returns a status with ≥1 valid, verbatim-verified citation |
| SM-3 | Documentation Agent correctly identifies the missing document |
| SM-4 | Submit is blocked, and blocked server-side when bypassed |
| SM-5 | Uploading the missing document and re-analyzing flips to ready |
| SM-6 | Packet generates with all required sections |
| SM-7 | Mock payer receives and responds |
| SM-8 | Rejection produces classification, explanation, and ordered checklist |
| SM-9 | Resubmission produces approval |
| SM-10 | Timeline shows all 12+ events in order |
| SM-11 | Full lifecycle completes with zero manual DB edits |

### Quality
| ID | Criterion | Target |
|---|---|---|
| SM-12 | Full analysis latency | P95 ≤ 10s |
| SM-13 | Agent JSON validity across 10 consecutive scenario runs | 10/10 |
| SM-14 | Evidence snippets verified as verbatim | 100% |
| SM-15 | Coverage status matches rule table across all seeded pairs | 100% |
| SM-16 | Demo scenario completes without error, 5 consecutive runs | 5/5 |

### Demo
| ID | Criterion |
|---|---|
| SM-17 | Full narrative delivered in ≤5 minutes |
| SM-18 | The audience understands what is blocked and why, without narration |
| SM-19 | Every claimed capability is live, not a slide |

---

## 32. Risks & Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | LLM hallucinates a policy fact | High | Critical | EX-2 verbatim substring validation; rule table binding (AS-3/AS-4); `unknown` fallback |
| R2 | Agent returns malformed JSON mid-demo | Medium | Critical | Structured output mode, `temperature=0.2`, retry-with-repair, response caching for the demo path |
| R3 | LLM API slow or unavailable | Medium | Critical | Parallel execution, per-card skeletons, 25s timeout, **`DEMO_CACHE=1` replay mode**, screen recording fallback |
| R4 | Integration starts too late | **High** | Critical | Hard T+5:00 integration gate; mock API server at T+45m; T+3:00 demonstrable-unit checkpoint |
| R5 | Frontend blocked on backend | High | High | Mock API server is BE's first deliverable, before models |
| R6 | Scope creep | High | High | §30 table is the contract; §7 non-goals reviewed aloud at T+0; anything new goes to §34 |
| R7 | Poor RAG retrieval | Medium | Medium | Rules table means retrieval affects citation quality only, not correctness; similarity floor; BM25 fallback |
| R8 | Document parsing consumes the day | **Was high** | Was critical | **Eliminated by design.** Declared types, no content extraction. |
| R9 | Contract drift between FE and agents | Medium | High | Single frozen contract file in both languages, committed at T+45m; changes require lead sign-off |
| R10 | Demo requires manual payer clicking | Medium | High | Scripted mode default; manual mode reserved for Q&A |
| R11 | Judge asks about HIPAA/PHI | High | Medium | Prepared honest answer (§25); synthetic data labels visible on screen |
| R12 | Judge asks what confidence 0.91 means | Medium | Medium | Score removed; `evidence_strength` derivation disclosed in tooltip and rehearsed |
| R13 | Agents step outside scope into clinical judgment | Medium | High | AS-1 prompt boundaries + no clinical decision surface exists in the data model |
| R14 | Merge conflicts across 5 devs late in the day | Medium | Medium | Ownership boundaries are directory-level; `contracts.*` is lead-only after freeze |
| R15 | Presenter unfamiliar with the flow | Medium | High | Two full rehearsals in Phase 5, non-negotiable |

---

## 33. Demo Scenario

**Setup:** patient Ahmed Ali, ABC Insurance, ABC Gold PPO, MRI Brain without contrast, Dr. Hala Mansour. Scripted payer mode. Database reset. Request pre-seeded in `DRAFT` with three documents attached so the demo does not open on a form.

### Act 1 — Blocked before submission *(~90s)*
1. Dashboard shows 6 requests across statuses. Open Ahmed Ali's request.
2. Click **Analyze**. Two skeleton cards appear; both resolve within ~8s.
3. **Coverage:** `Requires Prior Authorization`. Reason shown. Expand **Policy Evidence (§4.2)** to reveal the verbatim clause from *ABC Insurance MRI Authorization Policy*.
   > *Narration point:* "The system is not asserting this. It is quoting the policy."
4. **Documentation:** three ✅, one ❌ Previous Imaging Report. Red banner: "This request cannot be submitted. 1 required document is missing."
5. **Continue to Submission** is disabled. Hover shows the blocker.
   > *Narration point:* "Today this request gets sent, and comes back rejected two days later. Here it never leaves the building."
6. Status: `NEEDS_DOCUMENTS`.

### Act 2 — Resolve and submit *(~60s)*
7. Click the inline upload on the ❌ row. Attach `prior_mri_2024.pdf`, type pre-set to `prior_imaging_report`.
8. Amber stale-analysis banner appears. Click **Re-analyze**.
9. Documentation flips to four ✅. Status: `READY_FOR_SUBMISSION`.
10. Click **Continue to Submission**. Packet renders: patient, member number, payer, plan, service, physician, clinical justification, four attached documents, policy basis §4.2.
11. Confirm. Status: `SUBMITTED`, submission number `PA-20260827-0007`.

### Act 3 — Rejection and resolution *(~90s)*
12. After ~2s the payer responds: **Rejected — "Clinical documentation insufficient to establish medical necessity."**
13. Resolution panel renders:
    - Payer's verbatim reason
    - Classification: `insufficient_clinical_documentation`
    - Plain-language explanation distinguishing a documentation gap from a coverage denial
    - Two ordered actions with inline controls
    - Four-item resubmission checklist
    > *Narration point:* "This is the moment coordinators lose the most time. A rejection code becomes a to-do list."
14. Upload detailed physician notes via the inline control. Re-analyze. `READY_FOR_SUBMISSION`.
15. **Resubmit** → attempt 2 → **Approved**, authorization number `ABC-AUTH-88214`.

### Act 4 — Audit *(~30s)*
16. Scroll to the timeline: 14 events from creation to approval, including both submissions, both payer responses, every document upload, and every analysis run.
17. Open the payer portal in a second tab to show the reviewer side, including the manual-mode toggle.
    > *Closing line:* "Frontend, backend, RAG, three coordinated agents, and a complete authorization lifecycle. The payer is simulated. The workflow is not."

**Total: ~4.5 minutes.**

**Fallback:** if any live step fails, the presenter switches to the screen recording without pausing the narrative.

---

## 34. Future Roadmap

### Phase 1 — Production Foundation (post-hackathon, ~1 quarter)
- Authentication, RBAC, multi-tenancy by hospital
- PHI encryption at rest and in transit, BAAs, HIPAA control implementation
- Tamper-evident audit logging
- Postgres + pgvector; real document storage (S3 with signed URLs)
- Model evaluation harness with a labelled policy-QA set

### Phase 2 — Document Intelligence
- OCR and layout-aware extraction (Textract, Document AI, or equivalent)
- Automatic document type classification, replacing the declared-type assumption
- Content validation: does the attached physician order actually name this service?
- Clinical detail extraction to pre-fill the justification narrative

### Phase 3 — Real Integrations
- EHR integration via FHIR (`ServiceRequest`, `Coverage`, `DocumentReference`)
- Real payer connectivity where APIs exist; X12 278 for those where they do not
- Real-time eligibility verification (270/271)
- Payer portal RPA for payers with no programmatic channel

### Phase 4 — Intelligence Layer
- Approval likelihood prediction from historical outcomes
- Rejection-pattern analytics by payer, service, and physician
- Policy change detection with automatic re-indexing
- Auto-drafted appeal letters with human approval gates
- Coordinator productivity and first-pass approval dashboards

### Phase 5 — Scale
- Multi-payer policy ingestion pipeline
- Configurable rules engine so hospital staff can maintain rules without engineering
- Human-in-the-loop review queue for low-`evidence_strength` determinations
- SLA monitoring and payer turnaround benchmarking

**Nothing in §34 is in scope for the one-day MVP.**

---

## 35. Final MVP Definition

**CareAuth AI MVP is:** a single-tenant, unauthenticated web application in which a hospital authorization coordinator creates a prior authorization request against seeded patient, payer, and service data; attaches documents with declared types; and receives a combined AI assessment from two agents running in parallel. A Coverage Agent retrieves relevant clauses from an in-memory RAG index over five fabricated policy documents and returns a rule-bound coverage status with verbatim policy citations. A Documentation Agent reconciles a deterministically-sourced required-document list against attached documents and explains every gap with a policy reference. Submission is gated server-side on the combined result. When ready, a Communication Agent generates a structured authorization packet, which is transmitted to a scripted mock payer that rejects on the first attempt and approves on the second. The rejection is classified, explained in plain language beside the payer's verbatim reason, and converted into an ordered resubmission checklist with inline upload controls. Every event is persisted and rendered as a request timeline.

**It is not:** a chatbot, a clinical tool, a coverage authority, a production system, or a HIPAA-compliant application.

**It is done when:** the §33 demo scenario runs end to end, five consecutive times, without a manual database edit, code change, or unexplained AI output — and every AI statement on screen can be traced to either a policy citation or the payer's own words.

---

## Appendix A — Alternative Product Names

| Name | Rationale | Concern |
|---|---|---|
| **AuthPilot** | Conveys assisted navigation of a process rather than autonomy. Short, memorable, familiar suffix in healthcare IT. | "Pilot" may over-imply automation for a tool whose core promise is human control. |
| **PriorPath** | Names the exact workflow ("prior auth") and the product's function (showing the path to submission-ready). Alliterative and unambiguous to the target buyer. | Less brandable outside the prior-auth niche. |
| **ClearFile** | Emphasises the actual outcome: a complete, clean file before it leaves the building. Avoids AI-washing. | Loses the "authorization" signal; could read as document management. |

**Recommendation: keep CareAuth AI.** It carries both the domain ("Care", "Auth") and the category in four syllables, and renaming buys nothing on hackathon day. If this becomes a real product, **PriorPath** is the stronger long-term candidate because it names the job the buyer is hiring the product to do.

---

## Appendix B — Assumptions Register

| # | Assumption | Impact if wrong |
|---|---|---|
| A1 | All insurance policy text is fabricated for demonstration and does not reflect any real payer's terms | None for the MVP; disclosed on screen |
| A2 | Payer decision logic is fabricated; real payers use proprietary medical necessity criteria not modelled here | None for the MVP; disclosed |
| A3 | Users truthfully declare document types at upload | Documentation Agent's accuracy is only as good as the declaration. Addressed by roadmap Phase 2. |
| A4 | Required document sets can be expressed as a deterministic function of (plan, service) | Real payer requirements are often conditional on clinical facts. A rules engine with conditional predicates is roadmap Phase 5. |
| A5 | A single coordinator persona is sufficient for the MVP | Multi-role workflows (physician attestation, supervisor approval) are Phase 4 |
| A6 | Chunk-level `section_ref` extraction via markdown headings is representative of real policy documents | Real policy PDFs require layout-aware parsing. Roadmap Phase 2. |
| A7 | A one-day build permits no authentication | True only for a hackathon context; blocks any pilot deployment |
| A8 | 4 services × 2 payers is sufficient breadth to demonstrate generalisation | If judges probe breadth, add a third payer (nice-to-have #4) |
| A9 | Structured-output mode is available on the chosen model | If not, add a JSON repair pass; AI-3 owns this utility regardless |
| A10 | Latency targets are achievable with a small, fast model at temperature 0.2 | If not, cut the Documentation Agent's LLM layer to templated text and keep only the reconciliation logic |
