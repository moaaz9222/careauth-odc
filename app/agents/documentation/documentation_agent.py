import json
import time
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from contracts.contracts import (
    DocumentationResult,
    RequiredDocument,
    PresentDocument,
    MissingDocument,
    UnrecognizedDocument,
    DocumentType
)

from openai import AsyncOpenAI

# Standard explanations for known document types in prior authorization
DOC_EXPLANATIONS = {
    DocumentType.PRIOR_IMAGING_REPORT.value: {
        "label": "Previous Imaging Report",
        "why_required": "Policy requires prior imaging history for advanced imaging requests to establish that the study is not duplicative and to evaluate baseline progression.",
        "how_to_obtain": "Request from the hospital PACS/radiology department or the referring physician's office.",
        "source_section": "§4.2"
    },
    DocumentType.PHYSICIAN_ORDER.value: {
        "label": "Physician Order",
        "why_required": "A signed physician order is mandatory to confirm the medical necessity and clinical indication for the requested study.",
        "how_to_obtain": "Obtain signed order from the ordering provider or EHR orders module.",
        "source_section": "§6.1"
    },
    DocumentType.CLINICAL_NOTES.value: {
        "label": "Clinical Notes",
        "why_required": "Clinical notes detailing symptom duration, physical exam findings, and prior conservative treatments tried.",
        "how_to_obtain": "Export from EHR chart notes or request progress notes from treating clinic.",
        "source_section": "§6.1"
    },
    DocumentType.INSURANCE_CARD.value: {
        "label": "Insurance Card",
        "why_required": "Copy of front and back of active insurance card to verify subscriber identity and benefit tier.",
        "how_to_obtain": "Request from patient at intake or check scanned documents in patient registration file.",
        "source_section": "§6.1"
    },
    DocumentType.PHYSICIAN_NOTES_DETAILED.value: {
        "label": "Detailed Physician Progress Notes",
        "why_required": "Payer requires expanded clinical documentation specifying conservative therapy timeline and medical necessity rationale.",
        "how_to_obtain": "Request addendum or detailed office encounter note from ordering physician.",
        "source_section": "§4.3"
    },
    DocumentType.LAB_RESULTS.value: {
        "label": "Laboratory Results",
        "why_required": "Recent diagnostic lab panels required to assess baseline clinical parameters.",
        "how_to_obtain": "Retrieve from EHR lab results tab or laboratory portal.",
        "source_section": "§5.1"
    },
    DocumentType.REFERRAL_LETTER.value: {
        "label": "Referral Letter",
        "why_required": "Specialist referral letter from primary care provider.",
        "how_to_obtain": "Request from referring provider.",
        "source_section": "§3.1"
    }
}

class LLMMissingDocExplanation(BaseModel):
    doc_type: str
    why_required: str
    how_to_obtain: str

class LLMResponse(BaseModel):
    missing_explanations: List[LLMMissingDocExplanation]
    blocking_summary: str

class DocumentationAgent:
    def __init__(self, openai_client: Optional[AsyncOpenAI] = None):
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL")
        self.model = os.getenv("LLM_MODEL", "gemini-3.6-flash")
        self.client = openai_client or (AsyncOpenAI(api_key=self.api_key, base_url=self.base_url) if self.api_key else None)

    async def analyze(
        self,
        request_id: str,
        plan_id: str,
        plan_name: str,
        service_name: str,
        required_document_types: list[str],
        attached_documents: list[dict],
        clinical_context: str,
        policy_context: str = "",
        source_section: str = ""
    ) -> DocumentationResult:
        start_time = time.time()
        
        req_set = set(required_document_types)
        attached_docs_by_type = {}
        for d in attached_documents:
            dt = d.get('doc_type')
            if dt not in attached_docs_by_type:
                attached_docs_by_type[dt] = []
            attached_docs_by_type[dt].append(d)
        
        att_set = set(attached_docs_by_type.keys())
        
        missing_types = [dt for dt in required_document_types if dt not in att_set]
        unrecognized_types = [dt for dt in att_set if dt not in req_set]
        
        required_docs = []
        for dt in required_document_types:
            info = DOC_EXPLANATIONS.get(dt, {})
            label = info.get("label", dt.replace('_', ' ').title())
            sec = info.get("source_section", source_section or "§6.1")
            required_docs.append(RequiredDocument(
                doc_type=DocumentType(dt),
                label=label,
                mandatory=True,
                source_section=sec
            ))
            
        present_docs = []
        unrecognized_docs = []
        
        for d in attached_documents:
            dt = d.get('doc_type')
            if dt in req_set:
                present_docs.append(PresentDocument(
                    doc_type=DocumentType(dt),
                    document_id=d.get('document_id', ''),
                    file_name=d.get('file_name', '')
                ))
            else:
                unrecognized_docs.append(UnrecognizedDocument(
                    doc_type=dt or "other",
                    document_id=d.get('document_id', ''),
                    file_name=d.get('file_name', '')
                ))
                
        ready_for_submission = (len(missing_types) == 0)
        
        missing_docs = []
        blocking_summary = ""
        model_used = "system-reconciliation"
        
        if missing_types:
            llm_res = None
            if self.client and os.getenv("DEMO_CACHE", "0") != "1":
                try:
                    prompt = self._build_prompt(plan_name, service_name, set(missing_types), clinical_context, policy_context)
                    completion = await self.client.beta.chat.completions.parse(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are a medical documentation expert for prior authorization."},
                            {"role": "user", "content": prompt}
                        ],
                        response_format=LLMResponse,
                        temperature=0.2
                    )
                    llm_res = completion.choices[0].message.parsed
                    model_used = self.model
                    blocking_summary = llm_res.blocking_summary
                except Exception as e:
                    print(f"DocumentationAgent LLM call skipped/failed: {e}")
            
            if llm_res and llm_res.missing_explanations:
                explanations = {ex.doc_type: ex for ex in llm_res.missing_explanations}
                for dt in missing_types:
                    ex = explanations.get(dt)
                    info = DOC_EXPLANATIONS.get(dt, {})
                    label = info.get("label", dt.replace('_', ' ').title())
                    sec = info.get("source_section", source_section or "§6.1")
                    missing_docs.append(MissingDocument(
                        doc_type=DocumentType(dt),
                        label=label,
                        mandatory=True,
                        why_required=ex.why_required if ex else info.get("why_required", "Required by insurance policy."),
                        how_to_obtain=ex.how_to_obtain if ex else info.get("how_to_obtain", "Obtain from medical records."),
                        source_section=sec
                    ))
            else:
                # Deterministic high-quality fallback per PRD §14.2
                missing_labels = []
                for dt in missing_types:
                    info = DOC_EXPLANATIONS.get(dt, {})
                    label = info.get("label", dt.replace('_', ' ').title())
                    missing_labels.append(label)
                    sec = info.get("source_section", source_section or "§6.1")
                    missing_docs.append(MissingDocument(
                        doc_type=DocumentType(dt),
                        label=label,
                        mandatory=True,
                        why_required=info.get("why_required", f"{plan_name} requires {label} to verify medical necessity."),
                        how_to_obtain=info.get("how_to_obtain", "Request from ordering provider or hospital PACS/medical records."),
                        source_section=sec
                    ))
                blocking_summary = f"This request cannot be submitted. {len(missing_types)} required document{' is' if len(missing_types) == 1 else 's are'} missing: {', '.join(missing_labels)}."
        
        latency_ms = max(10, int((time.time() - start_time) * 1000))
        
        return DocumentationResult(
            request_id=request_id,
            ready_for_submission=ready_for_submission,
            required_documents=required_docs,
            present_documents=present_docs,
            missing_documents=missing_docs,
            unrecognized_documents=unrecognized_docs,
            blocking_summary=blocking_summary,
            model=model_used,
            latency_ms=latency_ms,
            generated_at=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        )
        
    def _build_prompt(self, plan_name: str, service_name: str, missing_types: set, clinical_context: str, policy_context: str) -> str:
        return f"""
Plan: {plan_name}
Service: {service_name}
Clinical context: {clinical_context}
Policy context: {policy_context}
Missing documents: {list(missing_types)}

For each missing document, provide a short 1-2 sentence 'why_required' grounded in the policy context, and a 'how_to_obtain' hint.
Also provide a 'blocking_summary' summarizing the overall missing documents (e.g. "This request cannot be submitted. 1 required document is missing: Previous Imaging Report.").
"""
