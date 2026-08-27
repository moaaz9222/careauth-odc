import asyncio
import json
import time
from sqlmodel import Session, select
from app.models.tables import (
    MockPayerScript, 
    InsuranceSubmission, 
    InsuranceResponse, 
    AuthorizationRequest,
    AiAnalysis,
    Patient,
    InsurancePlan,
    Service,
    Document
)
from app.services.request_service import RequestService
from app.agents.communication.communication_agent import CommunicationAgent
from contracts.contracts import EventType, PayerDecision

class MockPayerService:
    MODE = "scripted" # scripted | manual
    
    @staticmethod
    async def process_submission(session: Session, submission: InsuranceSubmission, request: AuthorizationRequest):
        if MockPayerService.MODE == "scripted":
            # 2 second delay per PRD §20
            await asyncio.sleep(2)
            
            # lookup script by (service_id, attempt_number)
            script = session.exec(select(MockPayerScript).where(
                MockPayerScript.service_id == request.service_id,
                MockPayerScript.attempt_number == submission.attempt_number
            )).first()
            
            if script:
                decision = script.decision
                reason_code = script.reason_code
                reason_text = script.reason_text
            else:
                # Default to approved for higher attempts or unscripted
                decision = PayerDecision.APPROVED.value
                reason_code = None
                reason_text = "Approved. Prior authorization approved under standard clinical review."
            
            # store response
            resp = InsuranceResponse(
                submission_id=submission.id,
                decision=decision,
                reason_code=reason_code,
                reason_text=reason_text,
                responder="scripted"
            )
            session.add(resp)
            session.commit()
            session.refresh(resp)
            
            # If decision is not approved, trigger Communication Agent to analyze response
            if decision in (PayerDecision.REJECTED.value, PayerDecision.MORE_INFO_REQUIRED.value):
                comm_agent = CommunicationAgent()
                resp_data = {
                    "decision": decision,
                    "reason_code": reason_code,
                    "reason_text": reason_text,
                    "payer_reason_verbatim": reason_text
                }
                res_result = await comm_agent.analyze_response(resp_data)
                
                # Persist to ai_analyses table
                analysis = AiAnalysis(
                    request_id=request.id,
                    agent="communication",
                    operation="analyze_response",
                    version="1.0",
                    input_hash=request.current_input_hash or "",
                    output_json=json.dumps(res_result.model_dump(), default=str),
                    model=res_result.model,
                    latency_ms=res_result.latency_ms,
                    status="success"
                )
                session.add(analysis)
                session.commit()

            # apply transition
            event_map = {
                PayerDecision.APPROVED.value: EventType.PAYER_APPROVED.value,
                PayerDecision.REJECTED.value: EventType.PAYER_REJECTED.value,
                PayerDecision.MORE_INFO_REQUIRED.value: EventType.PAYER_MORE_INFO.value
            }
            RequestService.transition(session, request, event_map[decision], "mock_payer", None)
            
            return resp
        else:
            # manual mode: submission stays in queue for payer portal
            return None
