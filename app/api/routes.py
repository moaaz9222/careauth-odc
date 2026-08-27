import os
import uuid
import json
import hashlib
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Form, Response, Request, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlmodel import Session, select, delete

from app.db import get_session, engine
from app.models.tables import (
    Patient, InsurancePlan, Service, AuthorizationRequest, Document,
    AiAnalysis, InsuranceSubmission, InsuranceResponse, RequestEvent,
    CoverageRule, MockPayerScript
)
from app.services.request_service import RequestService
from app.mock_payer.service import MockPayerService
from app.agents.communication.communication_agent import CommunicationAgent
from contracts.contracts import (
    DocumentType, RequestStatus, EventType, ErrorCode, PayerDecision
)

router = APIRouter(prefix="/api/v1")
STORAGE_DIR = "./uploads"

def get_current_input_hash(session: Session, request: AuthorizationRequest) -> str:
    docs = session.exec(select(Document).where(Document.request_id == request.id)).all()
    doc_strings = sorted([f"{d.id}:{d.doc_type}" for d in docs])
    hasher = hashlib.sha256()
    hasher.update((request.clinical_context or "").encode('utf-8'))
    hasher.update((request.service_id or "").encode('utf-8'))
    hasher.update((request.plan_id or "").encode('utf-8'))
    for ds in doc_strings:
        hasher.update(ds.encode('utf-8'))
    return hasher.hexdigest()

# ═══════════════════════════════════════════════════════════════
# Reference Endpoints — §19
# ═══════════════════════════════════════════════════════════════

@router.get("/reference/patients")
async def list_patients(session: Session = Depends(get_session)):
    return session.exec(select(Patient)).all()

@router.post("/reference/patients")
async def create_patient(
    request: Request,
    session: Session = Depends(get_session)
):
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        full_name = body.get("full_name") or body.get("name")
        dob_str = body.get("date_of_birth") or body.get("dob")
        gender = body.get("gender", "M")
        mock_id = body.get("mock_national_id") or body.get("member_number")
    else:
        form_data = await request.form()
        full_name = form_data.get("full_name") or form_data.get("name")
        dob_str = form_data.get("date_of_birth") or form_data.get("dob")
        gender = form_data.get("gender", "M")
        mock_id = form_data.get("mock_national_id") or form_data.get("member_number")
        
    if not full_name:
        raise HTTPException(status_code=422, detail="full_name is required")
        
    try:
        from datetime import date
        dob = datetime.strptime(str(dob_str), "%Y-%m-%d").date() if dob_str else date(1990, 1, 1)
    except:
        from datetime import date
        dob = date(1990, 1, 1)
        
    patient = Patient(
        full_name=str(full_name),
        date_of_birth=dob,
        gender=str(gender),
        mock_national_id=str(mock_id) if mock_id else f"ABC-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient

@router.get("/reference/plans")
async def list_plans(session: Session = Depends(get_session)):
    return session.exec(select(InsurancePlan)).all()

@router.get("/reference/services")
async def list_services(session: Session = Depends(get_session)):
    return session.exec(select(Service)).all()

@router.get("/reference/document-types")
async def list_document_types():
    return [e.value for e in DocumentType]

@router.get("/reference")
async def get_all_reference(session: Session = Depends(get_session)):
    patients = session.exec(select(Patient)).all()
    plans = session.exec(select(InsurancePlan)).all()
    services = session.exec(select(Service)).all()
    
    # Structure for frontend consumption
    payers_dict = {}
    for pl in plans:
        if pl.payer_name not in payers_dict:
            payers_dict[pl.payer_name] = {"id": pl.payer_name.lower().replace(" ", "_"), "name": pl.payer_name}
    
    return {
        "patients": [
            {"id": p.id, "name": p.full_name, "full_name": p.full_name, "dob": str(p.date_of_birth), "member_number": p.mock_national_id}
            for p in patients
        ],
        "payers": list(payers_dict.values()),
        "plans": [
            {"id": pl.id, "name": pl.plan_name, "plan_name": pl.plan_name, "payer_name": pl.payer_name, "plan_code": pl.plan_code}
            for pl in plans
        ],
        "services": [
            {"id": s.id, "name": s.name, "code": s.code, "category": s.category}
            for s in services
        ],
        "document_types": [
            {"value": dt.value, "label": dt.value.replace("_", " ").title()}
            for dt in DocumentType
        ]
    }

# ═══════════════════════════════════════════════════════════════
# Request Endpoints — §19
# ═══════════════════════════════════════════════════════════════

@router.post("/requests")
async def create_request(
    request: Request,
    session: Session = Depends(get_session)
):
    form_data = await request.form()
    patient_id = form_data.get("patient_id")
    plan_id = form_data.get("plan_id")
    service_id = form_data.get("service_id")
    member_number = form_data.get("member_number")
    physician_name = form_data.get("physician_name")
    clinical_context = form_data.get("clinical_context")
    urgency = form_data.get("urgency") or "routine"
    
    if not all([patient_id, plan_id, service_id, member_number, physician_name, clinical_context]):
        raise HTTPException(status_code=422, detail="Missing required fields")
        
    if len(str(clinical_context)) < 20:
        raise HTTPException(status_code=422, detail="Clinical context must be at least 20 characters")
        
    req = AuthorizationRequest(
        patient_id=str(patient_id),
        plan_id=str(plan_id),
        service_id=str(service_id),
        member_number=str(member_number),
        physician_name=str(physician_name),
        clinical_context=str(clinical_context),
        urgency=str(urgency),
        status=RequestStatus.DRAFT.value
    )
    session.add(req)
    session.commit()
    session.refresh(req)
    
    # Process any files uploaded during creation
    files = form_data.getlist("files")
    doc_types = form_data.getlist("doc_types")
    
    for i, file_item in enumerate(files):
        if hasattr(file_item, "filename") and file_item.filename:
            dtype = doc_types[i] if i < len(doc_types) else DocumentType.OTHER.value
            content = await file_item.read()
            ext = file_item.filename.split(".")[-1].lower() if "." in file_item.filename else "pdf"
            
            req_dir = os.path.join(STORAGE_DIR, req.id)
            os.makedirs(req_dir, exist_ok=True)
            fid = str(uuid.uuid4())
            path = os.path.join(req_dir, f"{fid}.{ext}")
            with open(path, "wb") as f:
                f.write(content)
                
            doc = Document(
                request_id=req.id,
                doc_type=dtype,
                file_name=file_item.filename,
                mime_type=getattr(file_item, "content_type", "application/octet-stream"),
                size_bytes=len(content),
                storage_path=path,
                uploaded_after_rejection=False
            )
            session.add(doc)
            
    session.commit()
    
    RequestService.transition(session, req, EventType.REQUEST_CREATED.value, "user")
    return {"id": req.id, "status": req.status}

@router.get("/requests")
async def list_requests(session: Session = Depends(get_session)):
    reqs = session.exec(select(AuthorizationRequest).order_by(AuthorizationRequest.updated_at.desc())).all()
    out = []
    for r in reqs:
        p = session.get(Patient, r.patient_id)
        s = session.get(Service, r.service_id)
        pl = session.get(InsurancePlan, r.plan_id)
        out.append({
            "id": r.id,
            "patient_name": p.full_name if p else "",
            "payer_name": pl.payer_name if pl else "",
            "plan_name": pl.plan_name if pl else "",
            "service_name": s.name if s else "",
            "status": r.status,
            "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat()
        })
        
    counters = {
        "total": len(reqs),
        "draft": sum(1 for r in reqs if r.status == RequestStatus.DRAFT.value),
        "needs_documents": sum(1 for r in reqs if r.status == RequestStatus.NEEDS_DOCUMENTS.value),
        "submitted": sum(1 for r in reqs if r.status == RequestStatus.SUBMITTED.value),
        "approved": sum(1 for r in reqs if r.status == RequestStatus.APPROVED.value),
        "action_required": sum(1 for r in reqs if r.status == RequestStatus.ACTION_REQUIRED.value),
    }
    return {"requests": out, "counters": counters}

@router.get("/requests/{request_id}")
async def get_request(request_id: str, session: Session = Depends(get_session)):
    r = session.get(AuthorizationRequest, request_id)
    if not r:
        raise HTTPException(status_code=404, detail="Authorization request not found")
    
    p = session.get(Patient, r.patient_id)
    s = session.get(Service, r.service_id)
    pl = session.get(InsurancePlan, r.plan_id)
    
    docs = session.exec(select(Document).where(Document.request_id == request_id)).all()
    analyses = session.exec(select(AiAnalysis).where(AiAnalysis.request_id == request_id).order_by(AiAnalysis.created_at.desc())).all()
    submissions = session.exec(select(InsuranceSubmission).where(InsuranceSubmission.request_id == request_id).order_by(InsuranceSubmission.submitted_at.desc())).all()
    events = session.exec(select(RequestEvent).where(RequestEvent.request_id == request_id).order_by(RequestEvent.created_at.desc())).all()
    
    responses = []
    for sub in submissions:
        resps = session.exec(select(InsuranceResponse).where(InsuranceResponse.submission_id == sub.id)).all()
        responses.extend(resps)
        
    cov_an = next((a for a in analyses if a.agent == "coverage"), None)
    doc_an = next((a for a in analyses if a.agent == "documentation"), None)
    res_an = next((a for a in analyses if a.agent == "communication" and a.operation == "analyze_response"), None)
    
    cov_result = json.loads(cov_an.output_json) if cov_an and cov_an.output_json else None
    doc_result = json.loads(doc_an.output_json) if doc_an and doc_an.output_json else None
    res_result = json.loads(res_an.output_json) if res_an and res_an.output_json else None

    current_hash = get_current_input_hash(session, r)
    is_stale = False
    if cov_an and cov_an.input_hash and cov_an.input_hash != current_hash and r.status != RequestStatus.ANALYZING.value:
        is_stale = True

    latest_sub = submissions[0] if submissions else None

    return {
        "id": r.id,
        "status": r.status,
        "patient_name": p.full_name if p else "",
        "payer_name": pl.payer_name if pl else "",
        "plan_name": pl.plan_name if pl else "",
        "service_name": s.name if s else "",
        "patient": p.dict() if p else {},
        "service": s.dict() if s else {},
        "plan": pl.dict() if pl else {},
        "clinical_context": r.clinical_context,
        "member_number": r.member_number,
        "physician_name": r.physician_name,
        "urgency": r.urgency,
        "documents": [d.dict() for d in docs],
        "coverage_analysis": cov_result,
        "documentation_analysis": doc_result,
        "resolution_analysis": res_result,
        "submission_number": latest_sub.submission_number if latest_sub else None,
        "analysis_stale": is_stale,
        "submissions": [sub.dict() for sub in submissions],
        "responses": [rs.dict() for rs in responses],
        "events": [e.dict() for e in events],
        "updated_at": r.updated_at.isoformat()
    }

@router.patch("/requests/{request_id}")
async def update_request(
    request_id: str,
    request: Request,
    session: Session = Depends(get_session)
):
    r = session.get(AuthorizationRequest, request_id)
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")
        
    data = await request.json()
    if "clinical_context" in data:
        r.clinical_context = data["clinical_context"]
    if "urgency" in data:
        r.urgency = data["urgency"]
    r.updated_at = datetime.utcnow()
    session.add(r)
    session.commit()
    
    RequestService.transition(session, r, EventType.FIELD_UPDATED.value, "user")
    return {"status": "updated"}

# ═══════════════════════════════════════════════════════════════
# Document Upload / Delete — §19
# ═══════════════════════════════════════════════════════════════

@router.post("/requests/{request_id}/documents")
async def upload_document(
    request_id: str,
    request: Request,
    session: Session = Depends(get_session)
):
    r = session.get(AuthorizationRequest, request_id)
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")
    
    form_data = await request.form()
    
    # Handle single file or multiple files
    files = form_data.getlist("files") or ([form_data.get("file")] if form_data.get("file") else [])
    doc_types = form_data.getlist("doc_types") or ([form_data.get("doc_type")] if form_data.get("doc_type") else [])
    
    created_docs = []
    for i, file_item in enumerate(files):
        if hasattr(file_item, "filename") and file_item.filename:
            dtype = doc_types[i] if i < len(doc_types) else DocumentType.OTHER.value
            if dtype not in [e.value for e in DocumentType]:
                raise HTTPException(status_code=422, detail="Invalid doc_type")
                
            ext = file_item.filename.split(".")[-1].lower() if "." in file_item.filename else "pdf"
            if ext not in ["pdf", "png", "jpg", "jpeg", "docx"]:
                raise HTTPException(status_code=415, detail=ErrorCode.UNSUPPORTED_FILE_TYPE.value)
                
            content = await file_item.read()
            if len(content) > 10 * 1024 * 1024:
                raise HTTPException(status_code=413, detail=ErrorCode.FILE_TOO_LARGE.value)
                
            req_dir = os.path.join(STORAGE_DIR, request_id)
            os.makedirs(req_dir, exist_ok=True)
            fid = str(uuid.uuid4())
            path = os.path.join(req_dir, f"{fid}.{ext}")
            with open(path, "wb") as f:
                f.write(content)
                
            doc = Document(
                request_id=request_id,
                doc_type=dtype,
                file_name=file_item.filename,
                mime_type=getattr(file_item, "content_type", "application/pdf"),
                size_bytes=len(content),
                storage_path=path,
                uploaded_after_rejection=(r.status == RequestStatus.ACTION_REQUIRED.value)
            )
            session.add(doc)
            created_docs.append(doc)
            
    session.commit()
    RequestService.transition(session, r, EventType.DOCUMENT_UPLOADED.value, "user")
    return {"uploaded": len(created_docs)}

@router.delete("/requests/{request_id}/documents/{doc_id}")
async def delete_document(request_id: str, doc_id: str, session: Session = Depends(get_session)):
    d = session.get(Document, doc_id)
    if d and d.request_id == request_id:
        session.delete(d)
        session.commit()
        r = session.get(AuthorizationRequest, request_id)
        if r:
            RequestService.transition(session, r, EventType.DOCUMENT_REMOVED.value, "user")
    return Response(status_code=204)

# ═══════════════════════════════════════════════════════════════
# AI Analysis Execution — §19 / §12
# ═══════════════════════════════════════════════════════════════

@router.post("/requests/{request_id}/analyze")
async def analyze_request(request_id: str, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    r = session.get(AuthorizationRequest, request_id)
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")
    
    RequestService.transition(session, r, "ANALYZE")
    
    r.current_input_hash = get_current_input_hash(session, r)
    session.add(r)
    session.commit()

    plan = session.get(InsurancePlan, r.plan_id)
    service = session.get(Service, r.service_id)
    docs = session.exec(select(Document).where(Document.request_id == request_id)).all()
    
    rule = session.exec(
        select(CoverageRule).where(
            CoverageRule.plan_id == r.plan_id,
            CoverageRule.service_id == r.service_id
        )
    ).first()

    plan_data = {"id": plan.id, "payer_name": plan.payer_name, "plan_name": plan.plan_name} if plan else {}
    service_data = {"id": service.id, "code": service.code, "name": service.name} if service else {}
    clinical_context = r.clinical_context
    urgency = r.urgency
    input_hash = r.current_input_hash
    
    rule_row = None
    required_doc_types = []
    source_section = ""
    if rule:
        rule_row = {
            "status": rule.status,
            "requires_prior_authorization": rule.requires_prior_authorization,
            "required_document_types": json.loads(rule.required_document_types) if isinstance(rule.required_document_types, str) else rule.required_document_types,
            "conditions": json.loads(rule.conditions) if isinstance(rule.conditions, str) and rule.conditions else [],
        }
        required_doc_types = rule_row["required_document_types"]
        source_section = rule.primary_section_ref or ""

    attached_docs = [{"doc_type": d.doc_type, "document_id": d.id, "file_name": d.file_name} for d in docs]

    async def run_analysis():
        from app.agents.orchestrator import Orchestrator
        from contracts.contracts import CoverageInput, CoverageInput_Plan, CoverageInput_Service
        
        orchestrator = Orchestrator()
        
        coverage_input = CoverageInput(
            request_id=request_id,
            plan=CoverageInput_Plan(**plan_data),
            service=CoverageInput_Service(**service_data),
            clinical_context=clinical_context,
            urgency=urgency
        )
        
        documentation_input = {
            "request_id": request_id,
            "plan_id": plan_data.get("id", ""),
            "plan_name": plan_data.get("plan_name", ""),
            "service_name": service_data.get("name", ""),
            "required_document_types": required_doc_types,
            "attached_documents": attached_docs,
            "clinical_context": clinical_context,
            "source_section": source_section,
        }
        
        async def persist_analysis(req_id, result):
            from sqlmodel import Session as S
            from app.db import engine as eng
            with S(eng) as s:
                cov_data = result.get("coverage", {})
                cov_analysis = AiAnalysis(
                    request_id=req_id,
                    agent="coverage",
                    version="1.0",
                    input_hash=input_hash,
                    output_json=json.dumps(cov_data, default=str),
                    model=cov_data.get("model", ""),
                    latency_ms=cov_data.get("latency_ms", 0),
                    status="success" if not isinstance(cov_data, dict) or cov_data.get("status") != "error" else "error"
                )
                s.add(cov_analysis)
                
                doc_data = result.get("documentation", {})
                doc_analysis = AiAnalysis(
                    request_id=req_id,
                    agent="documentation",
                    version="1.0",
                    input_hash=input_hash,
                    output_json=json.dumps(doc_data, default=str),
                    model=doc_data.get("model", ""),
                    latency_ms=doc_data.get("latency_ms", 0),
                    status="success" if not isinstance(doc_data, dict) or doc_data.get("status") != "error" else "error"
                )
                s.add(doc_analysis)
                s.commit()

        async def emit_event(event_type, result):
            from sqlmodel import Session as S
            from app.db import engine as eng
            with S(eng) as s:
                req = s.get(AuthorizationRequest, request_id)
                if req:
                    RequestService.transition(
                        s, req, event_type, "system",
                        json.dumps({"ready_for_submission": result.get("ready_for_submission", False)})
                    )
        
        try:
            await orchestrator.run(
                request_id=request_id,
                coverage_input=coverage_input,
                documentation_input=documentation_input,
                persist_analysis=persist_analysis,
                emit_event=emit_event,
                rule_row=rule_row
            )
        except Exception as e:
            print(f"Error during async orchestrator run: {e}")
            from sqlmodel import Session as S
            from app.db import engine as eng
            with S(eng) as s:
                req = s.get(AuthorizationRequest, request_id)
                if req:
                    try:
                        RequestService.transition(s, req, "ANALYSIS_FAILED", "system")
                    except:
                        req.status = RequestStatus.DRAFT.value
                        s.add(req)
                        s.commit()

    background_tasks.add_task(run_analysis)
    return {"status": r.status, "message": "Analysis started"}

# ═══════════════════════════════════════════════════════════════
# Submission & Mock Payer — §19 / §11 F4
# ═══════════════════════════════════════════════════════════════

@router.post("/requests/{request_id}/submit")
async def submit_request(request_id: str, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    r = session.get(AuthorizationRequest, request_id)
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # 1. Stale check
    current_hash = get_current_input_hash(session, r)
    if current_hash != r.current_input_hash:
        raise HTTPException(
            status_code=409, 
            detail={"error": {"code": ErrorCode.ANALYSIS_STALE.value, "message": "Analysis is stale. Please re-analyze before submitting."}}
        )
        
    # 2. Server-side readiness check (NFR-8 / §11 F4)
    analyses = session.exec(select(AiAnalysis).where(AiAnalysis.request_id == request_id).order_by(AiAnalysis.created_at.desc())).all()
    doc_an = next((a for a in analyses if a.agent == "documentation"), None)
    cov_an = next((a for a in analyses if a.agent == "coverage"), None)
    
    if doc_an and doc_an.output_json:
        doc_json = json.loads(doc_an.output_json)
        if not doc_json.get("ready_for_submission", False):
            raise HTTPException(
                status_code=409,
                detail={"error": {"code": ErrorCode.SUBMISSION_BLOCKED.value, "message": doc_json.get("blocking_summary", "Submission blocked by missing documents")}}
            )
            
    # 3. Create Submission record
    subs = session.exec(select(InsuranceSubmission).where(InsuranceSubmission.request_id == request_id)).all()
    attempt = len(subs) + 1
    sub_num = f"PA-{datetime.now().strftime('%Y%m%d')}-{attempt:04d}"
    
    p = session.get(Patient, r.patient_id)
    pl = session.get(InsurancePlan, r.plan_id)
    s = session.get(Service, r.service_id)
    docs = session.exec(select(Document).where(Document.request_id == request_id)).all()
    
    # Generate packet via Communication Agent
    comm_agent = CommunicationAgent()
    packet_req_data = {
        "submission_number": sub_num,
        "attempt_number": attempt,
        "patient": p.dict() if p else {},
        "plan": pl.dict() if pl else {},
        "service": s.dict() if s else {},
        "physician_name": r.physician_name,
        "physician_id_mock": r.physician_id_mock or "NPI-MOCK-2211",
        "clinical_context": r.clinical_context,
        "documents": [d.dict() for d in docs],
        "policy_title": "ABC Insurance MRI Authorization Policy",
        "section_ref": "§4.2"
    }
    packet = await comm_agent.generate_packet(packet_req_data)
    
    sub = InsuranceSubmission(
        request_id=request_id,
        submission_number=sub_num,
        attempt_number=attempt,
        packet_markdown=packet.packet_markdown,
        packet_json=json.dumps(packet.packet_structured.model_dump(), default=str)
    )
    session.add(sub)
    
    RequestService.transition(session, r, "SUBMIT", "user")
    session.commit()
    session.refresh(sub)
    
    # Background mock payer processing
    async def process_mock():
        with Session(engine) as bg_session:
            bg_sub = bg_session.get(InsuranceSubmission, sub.id)
            bg_req = bg_session.get(AuthorizationRequest, request_id)
            await MockPayerService.process_submission(bg_session, bg_sub, bg_req)
            
    background_tasks.add_task(process_mock)
    
    return {"submission_id": sub.id, "submission_number": sub_num, "status": r.status}

# ═══════════════════════════════════════════════════════════════
# Payer Portal & Admin Endpoints — §19 / §20
# ═══════════════════════════════════════════════════════════════

@router.get("/payer/submissions")
async def list_payer_submissions(session: Session = Depends(get_session)):
    subs = session.exec(select(InsuranceSubmission).order_by(InsuranceSubmission.submitted_at.desc())).all()
    out = []
    for s in subs:
        r = session.get(AuthorizationRequest, s.request_id)
        if not r: continue
        p = session.get(Patient, r.patient_id)
        svc = session.get(Service, r.service_id)
        docs = session.exec(select(Document).where(Document.request_id == r.id)).all()
        resps = session.exec(select(InsuranceResponse).where(InsuranceResponse.submission_id == s.id)).all()
        
        parsed_packet = {}
        if s.packet_json:
            try:
                parsed_packet = json.loads(s.packet_json)
            except:
                pass
                
        out.append({
            "id": s.id,
            "submission_number": s.submission_number,
            "attempt_number": s.attempt_number,
            "patient_name": p.full_name if p else "",
            "service_name": svc.name if svc else "",
            "service_code": svc.code if svc else "",
            "document_count": len(docs),
            "status": "pending" if not resps else resps[0].decision,
            "decision": resps[0].decision if resps else "pending",
            "packet_markdown": s.packet_markdown,
            "packet_structured": parsed_packet,
            "submitted_at": s.submitted_at.isoformat()
        })
    return {"submissions": out, "mode": MockPayerService.MODE}

@router.get("/payer/mode")
async def get_payer_mode():
    return {"mode": MockPayerService.MODE}

@router.post("/payer/submissions/{submission_id}/decision")
async def submit_payer_decision(
    submission_id: str, 
    request: Request,
    session: Session = Depends(get_session)
):
    decision = None
    reason_code = None
    reason_text = None
    
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        decision = body.get("decision")
        reason_code = body.get("reason_code")
        reason_text = body.get("reason_text")
    else:
        form_data = await request.form()
        decision = form_data.get("decision")
        reason_code = form_data.get("reason_code")
        reason_text = form_data.get("reason_text")
    
    s = session.get(InsuranceSubmission, submission_id)
    if not s:
        raise HTTPException(status_code=404, detail="Submission not found")
    r = session.get(AuthorizationRequest, s.request_id)
    
    resp = InsuranceResponse(
        submission_id=submission_id,
        decision=str(decision),
        reason_code=str(reason_code) if reason_code else None,
        reason_text=str(reason_text) if reason_text else None,
        responder="manual"
    )
    session.add(resp)
    session.commit()
    
    # If decision is rejected, generate resolution analysis
    if decision in (PayerDecision.REJECTED.value, PayerDecision.MORE_INFO_REQUIRED.value):
        comm_agent = CommunicationAgent()
        res_data = {
            "decision": decision,
            "reason_code": reason_code or "insufficient_clinical_documentation",
            "reason_text": reason_text or "Manual reviewer requested clinical documentation.",
            "payer_reason_verbatim": reason_text or "Manual reviewer requested clinical documentation."
        }
        res_result = await comm_agent.analyze_response(res_data)
        analysis = AiAnalysis(
            request_id=r.id,
            agent="communication",
            operation="analyze_response",
            version="1.0",
            input_hash=r.current_input_hash or "",
            output_json=json.dumps(res_result.model_dump(), default=str),
            model=res_result.model,
            latency_ms=res_result.latency_ms,
            status="success"
        )
        session.add(analysis)
        session.commit()

    event_map = {
        PayerDecision.APPROVED.value: EventType.PAYER_APPROVED.value,
        PayerDecision.REJECTED.value: EventType.PAYER_REJECTED.value,
        PayerDecision.MORE_INFO_REQUIRED.value: EventType.PAYER_MORE_INFO.value
    }
    RequestService.transition(session, r, event_map[decision], "mock_payer_reviewer")
    return {"status": "ok", "decision": decision}

@router.api_route("/payer/mode", methods=["POST", "PUT"])
async def set_payer_mode(request: Request):
    mode = "scripted"
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        mode = body.get("mode") or "scripted"
    else:
        form_data = await request.form()
        mode = form_data.get("mode") or "scripted"
    MockPayerService.MODE = str(mode)
    return {"mode": MockPayerService.MODE}

@router.post("/admin/reset")
async def admin_reset(session: Session = Depends(get_session)):
    # 1. Clean transactional tables
    session.exec(delete(RequestEvent))
    session.exec(delete(InsuranceResponse))
    session.exec(delete(InsuranceSubmission))
    session.exec(delete(AiAnalysis))
    session.exec(delete(Document))
    session.exec(delete(AuthorizationRequest))
    session.commit()
    
    # 2. Pre-seed the demo scenario request in DRAFT with 3 documents
    from app.seed.seed import seed_demo_request
    seed_demo_request(session)
    
    return {"status": "reset", "message": "Transactional state reset successfully (<2s)"}
