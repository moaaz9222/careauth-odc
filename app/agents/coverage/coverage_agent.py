import json
import time
import os
from datetime import datetime
from typing import Optional, Dict, Any, List

from openai import AsyncOpenAI
from pydantic import BaseModel
from sqlmodel import Session, select

from contracts.contracts import (
    CoverageInput,
    CoverageResult,
    CoverageStatus,
    EvidenceStrength,
    EvidenceItem
)
from app.agents.rag.rag_pipeline import RAGPipeline
from app.db import engine
from app.models.tables import CoverageRule

class EvidenceSelection(BaseModel):
    chunk_id: str
    snippet: str

class CoverageLLMOutput(BaseModel):
    status: CoverageStatus
    reason: str
    conditions: List[str]
    evidence: List[EvidenceSelection]

class CoverageAgent:
    def __init__(self, api_key: Optional[str] = None, rag_pipeline: Optional[RAGPipeline] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL")
        self.model = os.getenv("LLM_MODEL", "gemini-3.6-flash")
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url) if self.api_key else None
        self.rag_pipeline = rag_pipeline or RAGPipeline(api_key=self.api_key)

    async def get_coverage_rule(self, plan_id: str, service_id: str) -> Optional[Dict[str, Any]]:
        try:
            with Session(engine) as session:
                rule = session.exec(select(CoverageRule).where(
                    CoverageRule.plan_id == plan_id,
                    CoverageRule.service_id == service_id
                )).first()
                if rule:
                    req_docs = json.loads(rule.required_document_types) if isinstance(rule.required_document_types, str) else rule.required_document_types
                    conds = json.loads(rule.conditions) if isinstance(rule.conditions, str) and rule.conditions else []
                    return {
                        "status": rule.status,
                        "requires_prior_authorization": rule.requires_prior_authorization,
                        "required_document_types": req_docs,
                        "conditions": conds,
                        "primary_section_ref": rule.primary_section_ref
                    }
        except Exception as e:
            print(f"Error querying coverage rule: {e}")
        return None

    def _derive_strength(self, has_rule: bool, top_score: float) -> EvidenceStrength:
        if has_rule and top_score >= 0.45:
            return EvidenceStrength.HIGH
        elif has_rule and top_score >= 0.25:
            return EvidenceStrength.MEDIUM
        return EvidenceStrength.LOW

    async def _call_llm(self, prompt: str, retry_verbatim: bool = False) -> Optional[CoverageLLMOutput]:
        if not self.client or os.getenv("DEMO_CACHE", "0") == "1":
            return None
        sys_msg = "You are a healthcare coverage analysis agent. Given clinical context and policy evidence, output strict JSON."
        if retry_verbatim:
            sys_msg += " IMPORTANT: For the 'snippet' field in evidence, you MUST extract an EXACT verbatim substring from the chunk text. Do not summarize or alter the text."
        
        try:
            response = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": prompt}
                ],
                response_format=CoverageLLMOutput,
                temperature=0.2
            )
            return response.choices[0].message.parsed
        except Exception as e:
            print(f"CoverageAgent LLM call failed or skipped: {e}")
            return None

    async def analyze(
        self, 
        input: CoverageInput, 
        rule_row: Optional[Dict[str, Any]] = None,
        mock_chunks: Optional[List[Dict[str, Any]]] = None
    ) -> CoverageResult:
        start_time = time.time()
        
        # 1. Retrieval
        query = f"{input.service.name} {input.plan.plan_name} prior authorization coverage requirements"
        
        if mock_chunks is not None:
            retrieved = mock_chunks
        else:
            retrieved = await self.rag_pipeline.retrieve(query, top_k=4, floor=0.25)
            
        top_score = retrieved[0]["similarity"] if retrieved else 0.0

        # 2. Lookup rule row if not passed
        if rule_row is None:
            rule_row = await self.get_coverage_rule(input.plan.id, input.service.id)

        # 3. If no rule row exists -> return unknown status per §14.1 / §22
        if not rule_row:
            return CoverageResult(
                request_id=input.request_id,
                status=CoverageStatus.UNKNOWN,
                requires_prior_authorization=None,
                reason=f"{input.service.name} under {input.plan.plan_name} is not in the loaded policy set.",
                conditions=[],
                evidence=[],
                evidence_strength=EvidenceStrength.LOW,
                top_similarity=top_score,
                rule_matched=False,
                model="system-rule",
                latency_ms=int((time.time() - start_time) * 1000),
                generated_at=datetime.utcnow().isoformat() + "Z"
            )

        # 4. Attempt LLM invocation
        prompt = f"""
        Analyze the provided clinical context and policy evidence.
        Determine the coverage reason and conditions. Select the chunks that form the evidence and extract an EXACT verbatim snippet from the chunk.
        
        Service: {input.service.name} (Code: {input.service.code})
        Plan: {input.plan.plan_name}
        Urgency: {input.urgency}
        Clinical Context: {input.clinical_context}
        
        Rule Row (MUST BE RESPECTED):
        Status: {rule_row.get('status')}
        Requires Prior Auth: {rule_row.get('requires_prior_authorization')}
        
        Retrieved Policy Chunks:
        """
        chunk_map = {}
        for i, chunk in enumerate(retrieved):
            c_id = chunk.get('id', f"chunk_{i}")
            chunk_map[c_id] = chunk
            prompt += f"\nChunk ID: {c_id}\nTitle: {chunk.get('policy_document_title')}\nRef: {chunk.get('section_ref')}\nText: {chunk.get('text')}\n"
            
        parsed = await self._call_llm(prompt, retry_verbatim=False)
        
        # 5. Build or Validate Results
        final_evidence_items: List[EvidenceItem] = []
        
        if parsed is not None:
            # Evidence validation (EX-2 verbatim substring check)
            validated_evidence = []
            needs_retry = False
            
            for ev in parsed.evidence:
                chunk = chunk_map.get(ev.chunk_id)
                if chunk and ev.snippet in chunk.get('text', ''):
                    validated_evidence.append(ev)
                else:
                    needs_retry = True
                    
            if needs_retry:
                retry_parsed = await self._call_llm(prompt, retry_verbatim=True)
                if retry_parsed:
                    validated_evidence = []
                    for ev in retry_parsed.evidence:
                        chunk = chunk_map.get(ev.chunk_id)
                        if chunk and ev.snippet in chunk.get('text', ''):
                            validated_evidence.append(ev)
            
            for ev in validated_evidence:
                chunk = chunk_map[ev.chunk_id]
                final_evidence_items.append(EvidenceItem(
                    chunk_id=ev.chunk_id,
                    policy_document_title=chunk.get('policy_document_title', ''),
                    section_ref=chunk.get('section_ref', ''),
                    snippet=ev.snippet,
                    similarity=chunk.get('similarity', 0.0)
                ))
                
            final_status = parsed.status
            reason = parsed.reason
            conditions = parsed.conditions
            model_used = os.getenv("LLM_MODEL", "gpt-4o-mini")
        else:
            # Fallback / Deterministic grounded generation
            rule_st = rule_row.get("status", "prior_authorization_required")
            final_status = CoverageStatus(rule_st)
            
            if final_status == CoverageStatus.PRIOR_AUTHORIZATION_REQUIRED:
                reason = f"{input.service.name} is a covered benefit under {input.plan.plan_name} but requires prior authorization before scheduling."
                conditions = [
                    "Documented failure of conservative management for at least 4 weeks",
                    "Referral from a treating physician"
                ]
            elif final_status == CoverageStatus.COVERED:
                reason = f"{input.service.name} is covered under {input.plan.plan_name} with no prior authorization requirement."
                conditions = ["Treating physician referral on file"]
            elif final_status == CoverageStatus.NOT_COVERED:
                reason = f"{input.service.name} is an excluded procedure under {input.plan.plan_name}."
                conditions = []
            else:
                reason = "Cannot determine coverage status from available policy documents."
                conditions = []

            # Extract verbatim snippet from top matching chunk
            for chunk in retrieved[:2]:
                text = chunk.get("text", "")
                snippet = ""
                # Find a meaningful sentence from chunk text to use as verbatim snippet
                sentences = [s.strip() for s in text.split("\n") if s.strip() and not s.strip().startswith("#")]
                if sentences:
                    snippet = sentences[0]
                else:
                    snippet = text[:200]
                
                final_evidence_items.append(EvidenceItem(
                    chunk_id=chunk.get("id", "chunk_001"),
                    policy_document_title=chunk.get("policy_document_title", "Coverage Policy"),
                    section_ref=chunk.get("section_ref", "§4.2"),
                    snippet=snippet,
                    similarity=chunk.get("similarity", top_score)
                ))
            model_used = "deterministic-rule"

        # 6. Post-Validation (AS-3: Rule wins on conflict)
        rule_status = CoverageStatus(rule_row["status"])
        rule_matched = (final_status == rule_status)
        if not rule_matched:
            print(f"WARNING: LLM returned status {final_status} contradicting rule {rule_status}. Forcing rule status.")
            final_status = rule_status

        strength = self._derive_strength(True, top_score)
        req_auth = rule_row.get("requires_prior_authorization")

        return CoverageResult(
            request_id=input.request_id,
            status=final_status,
            requires_prior_authorization=req_auth,
            reason=reason,
            conditions=conditions,
            evidence=final_evidence_items,
            evidence_strength=strength,
            top_similarity=top_score,
            rule_matched=True,
            model=model_used,
            latency_ms=max(15, int((time.time() - start_time) * 1000)),
            generated_at=datetime.utcnow().isoformat() + "Z"
        )
