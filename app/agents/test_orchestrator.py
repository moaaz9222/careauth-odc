import pytest
import asyncio
from app.agents.orchestrator import Orchestrator
from contracts.contracts import CoverageInput, CoverageInput_Plan, CoverageInput_Service

@pytest.mark.asyncio
async def test_orchestrator_run_ready():
    orchestrator = Orchestrator()
    
    plan = CoverageInput_Plan(id="plan_abc_gold", payer_name="ABC Insurance", plan_name="ABC Gold PPO")
    service = CoverageInput_Service(id="svc_mri", code="70551", name="MRI Brain without contrast")
    cov_input = CoverageInput(
        request_id="req_1", 
        plan=plan, 
        service=service, 
        clinical_context="45yo male with persistent headaches for 6 weeks, failed NSAIDs."
    )
    doc_input = {
        "request_id": "req_1",
        "plan_id": "plan_abc_gold",
        "plan_name": "ABC Gold PPO",
        "service_name": "MRI Brain without contrast",
        "required_document_types": ["insurance_card", "physician_order"],
        "attached_documents": [
            {"doc_type": "insurance_card", "document_id": "doc_1", "file_name": "card.pdf"},
            {"doc_type": "physician_order", "document_id": "doc_2", "file_name": "order.pdf"}
        ],
        "clinical_context": "45yo male with persistent headaches for 6 weeks, failed NSAIDs.",
        "source_section": "§4.2"
    }
    
    rule_row = {
        "status": "prior_authorization_required",
        "requires_prior_authorization": True,
        "required_document_types": ["insurance_card", "physician_order"]
    }
    
    analysis_persisted = False
    event_emitted = False
    
    async def persist_analysis(request_id, result):
        nonlocal analysis_persisted
        analysis_persisted = True
        
    async def emit_event(event_type, result):
        nonlocal event_emitted
        event_emitted = True
        
    result = await orchestrator.run(
        request_id="req_1",
        coverage_input=cov_input,
        documentation_input=doc_input,
        persist_analysis=persist_analysis,
        emit_event=emit_event,
        rule_row=rule_row
    )
    
    assert result["ready_for_submission"] is True
    assert result["coverage"]["status"] in ("prior_authorization_required", "covered")
    assert result["documentation"]["ready_for_submission"] is True
    assert analysis_persisted is True
    assert event_emitted is True

@pytest.mark.asyncio
async def test_orchestrator_run_blocked():
    orchestrator = Orchestrator()
    
    plan = CoverageInput_Plan(id="plan_abc_gold", payer_name="ABC Insurance", plan_name="ABC Gold PPO")
    service = CoverageInput_Service(id="svc_mri", code="70551", name="MRI Brain without contrast")
    cov_input = CoverageInput(
        request_id="req_2", 
        plan=plan, 
        service=service, 
        clinical_context="45yo male with persistent headaches."
    )
    # Missing prior_imaging_report
    doc_input = {
        "request_id": "req_2",
        "plan_id": "plan_abc_gold",
        "plan_name": "ABC Gold PPO",
        "service_name": "MRI Brain without contrast",
        "required_document_types": ["insurance_card", "prior_imaging_report"],
        "attached_documents": [
            {"doc_type": "insurance_card", "document_id": "doc_1", "file_name": "card.pdf"}
        ],
        "clinical_context": "45yo male with persistent headaches.",
        "source_section": "§4.2"
    }
    
    rule_row = {
        "status": "prior_authorization_required",
        "requires_prior_authorization": True,
        "required_document_types": ["insurance_card", "prior_imaging_report"]
    }
    
    async def persist_analysis(request_id, result):
        pass
    async def emit_event(event_type, result):
        pass
        
    result = await orchestrator.run(
        request_id="req_2",
        coverage_input=cov_input,
        documentation_input=doc_input,
        persist_analysis=persist_analysis,
        emit_event=emit_event,
        rule_row=rule_row
    )
    
    assert result["ready_for_submission"] is False
    assert result["documentation"]["ready_for_submission"] is False
