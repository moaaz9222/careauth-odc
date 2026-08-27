import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.agents.communication.communication_agent import CommunicationAgent
from contracts.contracts import (
    SubmissionPacket,
    ResolutionResult,
    PacketStructured,
    PacketPatient,
    PacketService,
    PacketPhysician,
    PayerDecision,
    ReasonClassification
)

@pytest.mark.asyncio
async def test_generate_packet():
    agent = CommunicationAgent()
    
    mock_packet = SubmissionPacket(
        submission_number="PA-20260827-1",
        packet_markdown="test narrative",
        packet_structured=PacketStructured(
            patient=PacketPatient(name="John", dob="2000-01-01", member_number="123"),
            payer="ABC",
            plan="Gold",
            service=PacketService(code="70551", name="MRI"),
            physician=PacketPhysician(name="Dr. Smith", id="456"),
            clinical_justification="test",
            attached_documents=[],
            policy_basis=[]
        )
    )
    
    with patch("app.agents.communication.communication_agent.AsyncOpenAI") as mock_openai:
        mock_client = mock_openai.return_value
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.parsed = mock_packet
        mock_client.beta.chat.completions.parse = AsyncMock(return_value=mock_response)
        
        agent.client = mock_client
        
        result = await agent.generate_packet({"req": "data"})
        assert result.submission_number == "PA-20260827-1"
        assert result.packet_markdown == "test narrative"

@pytest.mark.asyncio
async def test_analyze_response():
    agent = CommunicationAgent()
    
    mock_res = ResolutionResult(
        decision=PayerDecision.REJECTED,
        reason_classification=ReasonClassification.MISSING_DOCUMENT,
        payer_reason_verbatim="Need doc",
        explanation="Missing a doc",
        is_appealable=True,
        recommended_actions=[],
        resubmission_checklist=[]
    )
    
    with patch("app.agents.communication.communication_agent.AsyncOpenAI") as mock_openai:
        mock_client = mock_openai.return_value
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.parsed = mock_res
        mock_client.beta.chat.completions.parse = AsyncMock(return_value=mock_response)
        
        agent.client = mock_client
        
        result = await agent.analyze_response({"res": "data"})
        assert result.decision == PayerDecision.REJECTED
        assert result.payer_reason_verbatim == "Need doc"
