from sqlmodel import Session
from app.models.tables import AuthorizationRequest, RequestEvent
from datetime import datetime
from typing import Optional
from app.db import get_session
from fastapi import HTTPException
from contracts.contracts import RequestStatus, EventType

class RequestService:
    @staticmethod
    def transition(session: Session, request: AuthorizationRequest, event_type: str, actor: str = "system", payload: Optional[str] = None):
        current_state = request.status
        next_state = current_state
        
        if event_type == "ANALYZE":
            if current_state in [RequestStatus.DRAFT.value, RequestStatus.NEEDS_DOCUMENTS.value, RequestStatus.READY_FOR_SUBMISSION.value, RequestStatus.ACTION_REQUIRED.value]:
                # Guard: request has required fields
                if not request.patient_id or not request.plan_id or not request.service_id or not request.clinical_context:
                    raise HTTPException(status_code=422, detail="VALIDATION_ERROR: Missing required fields")
                next_state = RequestStatus.ANALYZING.value
            else:
                raise HTTPException(status_code=409, detail=f"INVALID_TRANSITION: Cannot ANALYZE from {current_state}")

        elif event_type == EventType.ANALYSIS_COMPLETE.value:
            if current_state == RequestStatus.ANALYZING.value:
                # We expect the caller to pass ready_for_submission in payload or check it before
                import json
                ready = False
                if payload:
                    try:
                        data = json.loads(payload)
                        ready = data.get("ready_for_submission", False)
                    except:
                        pass
                
                next_state = RequestStatus.READY_FOR_SUBMISSION.value if ready else RequestStatus.NEEDS_DOCUMENTS.value
            else:
                raise HTTPException(status_code=409, detail=f"INVALID_TRANSITION: Cannot ANALYSIS_COMPLETE from {current_state}")

        elif event_type == EventType.ANALYSIS_FAILED.value:
            if current_state == RequestStatus.ANALYZING.value:
                next_state = RequestStatus.DRAFT.value
            else:
                raise HTTPException(status_code=409, detail=f"INVALID_TRANSITION: Cannot ANALYSIS_FAILED from {current_state}")
                
        elif event_type == "SUBMIT":
            if current_state == RequestStatus.READY_FOR_SUBMISSION.value:
                # We expect the caller to do the readiness/hash validation before calling this transition
                next_state = RequestStatus.SUBMITTED.value
                event_type = EventType.SUBMITTED.value  # Map to correct event type for DB
            else:
                raise HTTPException(status_code=409, detail=f"INVALID_TRANSITION: Cannot SUBMIT from {current_state}")
                
        elif event_type == EventType.PAYER_APPROVED.value:
            if current_state == RequestStatus.SUBMITTED.value:
                next_state = RequestStatus.APPROVED.value
            else:
                raise HTTPException(status_code=409, detail=f"INVALID_TRANSITION: Cannot PAYER_APPROVED from {current_state}")
                
        elif event_type == EventType.PAYER_REJECTED.value or event_type == EventType.PAYER_MORE_INFO.value:
            if current_state == RequestStatus.SUBMITTED.value:
                next_state = RequestStatus.ACTION_REQUIRED.value
            else:
                raise HTTPException(status_code=409, detail=f"INVALID_TRANSITION: Cannot {event_type} from {current_state}")
        else:
            # For other events (like DOCUMENT_UPLOADED) that don't transition state directly
            pass

        # Apply state
        request.status = next_state
        request.updated_at = datetime.utcnow()
        session.add(request)
        
        # Create event
        evt = RequestEvent(
            request_id=request.id,
            event_type=event_type,
            actor=actor,
            payload_json=payload
        )
        session.add(evt)
        session.commit()
        session.refresh(request)
        return request
