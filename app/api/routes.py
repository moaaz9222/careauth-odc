"""
CareAuth AI — FastAPI Router Stubs (501 Not Implemented)

Source: PRD §19 (API Requirements)
All endpoints return 501 until real implementations replace them.
"""

from fastapi import APIRouter, UploadFile, File, Form, Response
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/v1")


# ═══════════════════════════════════════════════════════════════
# Reference Data — §19
# ═══════════════════════════════════════════════════════════════

@router.get("/reference/patients")
async def list_patients():
    return Response(status_code=501)


@router.get("/reference/plans")
async def list_plans():
    return Response(status_code=501)


@router.get("/reference/services")
async def list_services():
    return Response(status_code=501)


@router.get("/reference/document-types")
async def list_document_types():
    return Response(status_code=501)


# ═══════════════════════════════════════════════════════════════
# Requests — §19
# ═══════════════════════════════════════════════════════════════

@router.post("/requests")
async def create_request():
    return Response(status_code=501)


@router.get("/requests")
async def list_requests():
    return Response(status_code=501)


@router.get("/requests/{request_id}")
async def get_request(request_id: str):
    return Response(status_code=501)


@router.patch("/requests/{request_id}")
async def update_request(request_id: str):
    return Response(status_code=501)


# ═══════════════════════════════════════════════════════════════
# Documents — §19
# ═══════════════════════════════════════════════════════════════

@router.post("/requests/{request_id}/documents")
async def upload_document(request_id: str):
    return Response(status_code=501)


@router.delete("/requests/{request_id}/documents/{doc_id}")
async def delete_document(request_id: str, doc_id: str):
    return Response(status_code=501)


# ═══════════════════════════════════════════════════════════════
# Analysis — §19
# ═══════════════════════════════════════════════════════════════

@router.post("/requests/{request_id}/analyze")
async def analyze_request(request_id: str):
    return Response(status_code=501)


# ═══════════════════════════════════════════════════════════════
# Submission — §19
# ═══════════════════════════════════════════════════════════════

@router.post("/requests/{request_id}/submit")
async def submit_request(request_id: str):
    return Response(status_code=501)


# ═══════════════════════════════════════════════════════════════
# Payer Portal — §19
# ═══════════════════════════════════════════════════════════════

@router.get("/payer/submissions")
async def list_payer_submissions():
    return Response(status_code=501)


@router.post("/payer/submissions/{submission_id}/decision")
async def submit_payer_decision(submission_id: str):
    return Response(status_code=501)


@router.post("/payer/mode")
async def set_payer_mode():
    return Response(status_code=501)


# ═══════════════════════════════════════════════════════════════
# Admin — §19
# ═══════════════════════════════════════════════════════════════

@router.post("/admin/reset")
async def admin_reset():
    return Response(status_code=501)
