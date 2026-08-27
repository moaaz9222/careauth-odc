import json
import os
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from openai import AsyncOpenAI

from contracts.contracts import (
    SubmissionPacket,
    ResolutionResult,
    PacketStructured,
    PacketPatient,
    PacketService,
    PacketPhysician,
    PolicyBasis,
    PayerDecision,
    ReasonClassification,
    RecommendedAction,
    RecommendedActionKind
)
from app.agents.json_repair import repair_json

class CommunicationAgent:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL")
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url) if self.api_key else None
        self.model = os.getenv("LLM_MODEL", "gemini-3.6-flash")

    async def generate_packet(self, request_data: dict) -> SubmissionPacket:
        """
        Input: full request data (patient, plan, service, physician, clinical context, documents, coverage result, policy evidence)
        Output: SubmissionPacket
        submission_number format: PA-{YYYYMMDD}-{seq}
        """
        start_time = time.time()
        
        # Extract fields safely
        patient_info = request_data.get("patient", {})
        plan_info = request_data.get("plan", {})
        service_info = request_data.get("service", {})
        physician_name = request_data.get("physician_name", "Treating Physician")
        member_number = request_data.get("member_number", patient_info.get("member_number", "ABC-MOCK-001"))
        clinical_context = request_data.get("clinical_context", "")
        seq = request_data.get("attempt_number", 1)
        sub_num = request_data.get("submission_number", f"PA-{datetime.now().strftime('%Y%m%d')}-{seq:04d}")
        
        docs = request_data.get("documents", [])
        attached_names = [d.get("file_name", d.get("doc_type", "Document")) for d in docs]
        if not attached_names:
            attached_names = ["Insurance Card", "Physician Order", "Clinical Notes", "Previous Imaging Report"]
            
        policy_basis = [
            PolicyBasis(
                policy_document_title=request_data.get("policy_title", "ABC Insurance MRI Authorization Policy"),
                section_ref=request_data.get("section_ref", "§4.2")
            )
        ]

        patient_obj = PacketPatient(
            name=patient_info.get("full_name", patient_info.get("name", "Ahmed Ali")),
            dob=str(patient_info.get("date_of_birth", patient_info.get("dob", "1981-03-14"))),
            member_number=member_number
        )
        service_obj = PacketService(
            code=service_info.get("code", "70551"),
            name=service_info.get("name", "MRI Brain without contrast")
        )
        physician_obj = PacketPhysician(
            name=physician_name,
            id=request_data.get("physician_id_mock", "NPI-MOCK-2211")
        )
        
        structured_data = PacketStructured(
            patient=patient_obj,
            payer=plan_info.get("payer_name", "ABC Insurance"),
            plan=plan_info.get("plan_name", "ABC Gold PPO"),
            service=service_obj,
            physician=physician_obj,
            clinical_justification=clinical_context,
            attached_documents=attached_names,
            policy_basis=policy_basis
        )

        packet_md = f"""## Prior Authorization Request Packet
**Submission ID:** {sub_num}
**Date:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

### Patient Information
- **Full Name:** {patient_obj.name}
- **Date of Birth:** {patient_obj.dob}
- **Member Number:** {patient_obj.member_number}
- **Payer / Plan:** {structured_data.payer} — {structured_data.plan}

### Requested Clinical Service
- **Service:** {service_obj.name} (CPT: {service_obj.code})
- **Ordering Physician:** {physician_obj.name} (ID: {physician_obj.id})

### Clinical Justification & History
{clinical_context}

### Policy Evidence & Basis
- **Policy:** {policy_basis[0].policy_document_title} ({policy_basis[0].section_ref})

### Attached Supporting Documentation ({len(attached_names)})
""" + "\n".join([f"- {name}" for name in attached_names])

        if self.client and os.getenv("DEMO_CACHE", "0") != "1":
            try:
                prompt = f"""
                You are generating a prior authorization submission packet for insurance review.
                Request Data: {json.dumps(request_data, default=str)}
                Generate the markdown narrative and structured data according to the schema.
                """
                response = await self.client.beta.chat.completions.parse(
                    model=self.model,
                    messages=[{"role": "system", "content": prompt}],
                    response_format=SubmissionPacket,
                    temperature=0.2
                )
                if response.choices[0].message.parsed:
                    return response.choices[0].message.parsed
            except Exception as e:
                print(f"CommunicationAgent generate_packet LLM call skipped/failed: {e}")

        return SubmissionPacket(
            agent="communication",
            operation="generate_packet",
            version="1.0",
            submission_number=sub_num,
            packet_markdown=packet_md,
            packet_structured=structured_data,
            model="system-template" if not self.client else self.model,
            latency_ms=max(10, int((time.time() - start_time) * 1000))
        )

    async def analyze_response(self, response_data: dict) -> ResolutionResult:
        """
        Input: insurance response (decision, reason_code, reason_text), original request data, current documents, prior agent outputs
        Output: ResolutionResult
        """
        start_time = time.time()
        
        decision_str = response_data.get("decision", "rejected")
        decision = PayerDecision(decision_str)
        reason_code = response_data.get("reason_code", "insufficient_clinical_documentation")
        payer_verbatim = response_data.get("reason_text") or response_data.get("payer_reason_verbatim") or "Clinical documentation insufficient to establish medical necessity."

        # Map reason code to classification
        classification_map = {
            "insufficient_clinical_documentation": ReasonClassification.INSUFFICIENT_CLINICAL_DOCUMENTATION,
            "missing_document": ReasonClassification.MISSING_DOCUMENT,
            "service_not_covered": ReasonClassification.SERVICE_NOT_COVERED,
            "authorization_not_required": ReasonClassification.AUTHORIZATION_NOT_REQUIRED,
            "eligibility_issue": ReasonClassification.ELIGIBILITY_ISSUE,
            "administrative_error": ReasonClassification.ADMINISTRATIVE_ERROR,
        }
        classification = classification_map.get(reason_code, ReasonClassification.OTHER)

        if self.client and os.getenv("DEMO_CACHE", "0") != "1":
            try:
                prompt = f"""
                You are analyzing an insurance prior authorization response.
                Response Data: {json.dumps(response_data, default=str)}
                
                Classify the reason, explain it at a 9th-grade reading level, and generate a resubmission checklist (ordered, <= 5 items) and recommended actions.
                Make sure `payer_reason_verbatim` is exactly the payer's stated reason: "{payer_verbatim}".
                """
                response = await self.client.beta.chat.completions.parse(
                    model=self.model,
                    messages=[{"role": "system", "content": prompt}],
                    response_format=ResolutionResult,
                    temperature=0.2
                )
                if response.choices[0].message.parsed:
                    return response.choices[0].message.parsed
            except Exception as e:
                print(f"CommunicationAgent analyze_response LLM call skipped/failed: {e}")

        # Deterministic high-quality ResolutionResult per PRD §14.3
        if classification == ReasonClassification.INSUFFICIENT_CLINICAL_DOCUMENTATION:
            explanation = "The payer accepted that this service is covered, but did not find enough written clinical detail to show why the scan is needed now. This is a documentation gap, not a coverage denial."
            actions = [
                RecommendedAction(
                    order=1,
                    kind=RecommendedActionKind.UPLOAD_DOCUMENT,
                    doc_type="physician_notes_detailed",
                    label="Attach detailed physician progress notes",
                    detail="Notes should state symptom duration, conservative treatments already tried (NSAIDs/PT for >=4 weeks), and why imaging is needed now."
                ),
                RecommendedAction(
                    order=2,
                    kind=RecommendedActionKind.EDIT_FIELD,
                    field="clinical_context",
                    label="Expand the clinical justification",
                    detail="Include the failed conservative management timeline referenced in §4.2."
                )
            ]
            checklist = [
                "Attach detailed physician progress notes",
                "Expand clinical justification to include conservative management history",
                "Confirm all four required documents remain attached",
                "Resubmit as attempt 2"
            ]
        elif classification == ReasonClassification.MISSING_DOCUMENT:
            explanation = "The payer requires a specific supporting document that was not attached to the initial submission."
            actions = [
                RecommendedAction(
                    order=1,
                    kind=RecommendedActionKind.UPLOAD_DOCUMENT,
                    doc_type="prior_imaging_report",
                    label="Attach previous imaging report",
                    detail="Attach prior radiologic study report for comparison."
                )
            ]
            checklist = [
                "Attach missing previous imaging report",
                "Verify all documentation is complete",
                "Resubmit authorization request"
            ]
        else:
            explanation = f"The payer returned decision '{decision_str}' with notice: {payer_verbatim}"
            actions = [
                RecommendedAction(
                    order=1,
                    kind=RecommendedActionKind.REVIEW,
                    label="Review payer denial",
                    detail="Review policy exclusion or eligibility requirements with billing team."
                )
            ]
            checklist = [
                "Review payer denial notice",
                "Consult with ordering provider"
            ]

        return ResolutionResult(
            agent="communication",
            operation="analyze_response",
            version="1.0",
            decision=decision,
            reason_classification=classification,
            payer_reason_verbatim=payer_verbatim,
            explanation=explanation,
            is_appealable=True,
            recommended_actions=actions,
            resubmission_checklist=checklist,
            model="system-resolution" if not self.client else self.model,
            latency_ms=max(10, int((time.time() - start_time) * 1000))
        )
