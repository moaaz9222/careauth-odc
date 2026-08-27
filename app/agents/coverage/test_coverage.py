import pytest
import os
from unittest.mock import AsyncMock, patch

from app.agents.coverage.coverage_agent import CoverageAgent, CoverageLLMOutput, EvidenceSelection
from contracts.contracts import (
    CoverageInput,
    CoverageInput_Plan,
    CoverageInput_Service,
    CoverageStatus,
    CoverageResult
)

@pytest.mark.asyncio
async def test_coverage_agent_mri_brain():
    agent = CoverageAgent(api_key="mock")
    
    input_data = CoverageInput(
        request_id="req_123",
        plan=CoverageInput_Plan(id="plan_abc_gold", payer_name="ABC Insurance", plan_name="ABC Gold PPO"),
        service=CoverageInput_Service(id="svc_mri_brain", code="70551", name="MRI Brain"),
        clinical_context="Patient has severe headaches for 6 weeks, failed conservative management with NSAIDs.",
        urgency="routine"
    )
    
    rule_row = {
        "status": "prior_authorization_required",
        "requires_prior_authorization": True
    }
    
    mock_chunks = [
        {
            "id": "chunk_1",
            "policy_document_title": "ABC Insurance MRI Authorization Policy",
            "section_ref": "§4.2",
            "text": "Advanced imaging services, including magnetic resonance imaging of the brain, require prior authorization when performed in an outpatient setting. Documented failure of conservative management for at least 4 weeks is required.",
            "similarity": 0.85
        }
    ]
    
    # Mock LLM to return a valid exact snippet
    mock_parsed = CoverageLLMOutput(
        status=CoverageStatus.PRIOR_AUTHORIZATION_REQUIRED,
        reason="MRI brain requires prior auth per policy.",
        conditions=["Failure of conservative management for 4 weeks"],
        evidence=[
            EvidenceSelection(
                chunk_id="chunk_1",
                snippet="magnetic resonance imaging of the brain, require prior authorization when performed in an outpatient setting."
            )
        ]
    )
    
    agent._call_llm = AsyncMock(return_value=mock_parsed)
    
    result = await agent.analyze(input_data, rule_row=rule_row, mock_chunks=mock_chunks)
    
    assert result.status == CoverageStatus.PRIOR_AUTHORIZATION_REQUIRED
    assert result.requires_prior_authorization is True
    assert len(result.evidence) == 1
    assert result.evidence[0].snippet in mock_chunks[0]["text"]
    assert result.rule_matched is True

@pytest.mark.asyncio
async def test_coverage_agent_evidence_retry():
    agent = CoverageAgent(api_key="mock")
    
    input_data = CoverageInput(
        request_id="req_123",
        plan=CoverageInput_Plan(id="plan_abc_gold", payer_name="ABC Insurance", plan_name="ABC Gold PPO"),
        service=CoverageInput_Service(id="svc_mri_brain", code="70551", name="MRI Brain"),
        clinical_context="Patient has severe headaches.",
        urgency="routine"
    )
    
    rule_row = {
        "status": "prior_authorization_required",
        "requires_prior_authorization": True
    }
    
    mock_chunks = [
        {
            "id": "chunk_1",
            "policy_document_title": "Policy",
            "section_ref": "§4.2",
            "text": "Requires prior authorization.",
            "similarity": 0.85
        }
    ]
    
    # First call: bad snippet
    mock_parsed_1 = CoverageLLMOutput(
        status=CoverageStatus.PRIOR_AUTHORIZATION_REQUIRED,
        reason="Requires auth",
        conditions=[],
        evidence=[EvidenceSelection(chunk_id="chunk_1", snippet="Requires auth!")]
    )
    
    # Second call: fixed snippet
    mock_parsed_2 = CoverageLLMOutput(
        status=CoverageStatus.PRIOR_AUTHORIZATION_REQUIRED,
        reason="Requires auth",
        conditions=[],
        evidence=[EvidenceSelection(chunk_id="chunk_1", snippet="Requires prior authorization.")]
    )
    
    agent._call_llm = AsyncMock(side_effect=[mock_parsed_1, mock_parsed_2])
    
    result = await agent.analyze(input_data, rule_row=rule_row, mock_chunks=mock_chunks)
    
    assert len(result.evidence) == 1
    assert result.evidence[0].snippet == "Requires prior authorization."
    assert agent._call_llm.call_count == 2
