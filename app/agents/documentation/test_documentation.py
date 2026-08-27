import pytest
from app.agents.documentation.documentation_agent import DocumentationAgent
from contracts.contracts import DocumentType

@pytest.mark.asyncio
async def test_documentation_agent_missing_docs():
    agent = DocumentationAgent() # Without actual OpenAI client, will use fallback or mock
    
    required = [
        "insurance_card",
        "physician_order",
        "clinical_notes",
        "prior_imaging_report"
    ]
    
    attached = [
        {"doc_type": "insurance_card", "document_id": "1", "file_name": "a.pdf"},
        {"doc_type": "physician_order", "document_id": "2", "file_name": "b.pdf"},
        {"doc_type": "clinical_notes", "document_id": "3", "file_name": "c.pdf"},
        {"doc_type": "other", "document_id": "4", "file_name": "d.pdf"} # Unrecognized
    ]
    
    res = await agent.analyze(
        request_id="req1",
        plan_id="plan1",
        plan_name="Test Plan",
        service_name="Test Service",
        required_document_types=required,
        attached_documents=attached,
        clinical_context="Test context"
    )
    
    assert res.ready_for_submission is False
    assert len(res.missing_documents) == 1
    assert res.missing_documents[0].doc_type == DocumentType.PRIOR_IMAGING_REPORT
    
    assert len(res.unrecognized_documents) == 1
    assert res.unrecognized_documents[0].doc_type == "other"
    
    req_docs_out = [d.doc_type.value for d in res.required_documents]
    assert set(req_docs_out) == set(required)

@pytest.mark.asyncio
async def test_documentation_agent_all_docs_present():
    agent = DocumentationAgent() 
    
    required = [
        "insurance_card",
        "physician_order"
    ]
    
    attached = [
        {"doc_type": "insurance_card", "document_id": "1", "file_name": "a.pdf"},
        {"doc_type": "physician_order", "document_id": "2", "file_name": "b.pdf"}
    ]
    
    res = await agent.analyze(
        request_id="req2",
        plan_id="plan1",
        plan_name="Test Plan",
        service_name="Test Service",
        required_document_types=required,
        attached_documents=attached,
        clinical_context="Test context"
    )
    
    assert res.ready_for_submission is True
    assert len(res.missing_documents) == 0
    assert len(res.unrecognized_documents) == 0
