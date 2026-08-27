import json
import os
import glob
import re
from sqlmodel import Session, select
from app.db import engine, create_db_and_tables
from app.models.tables import (
    Patient, 
    InsurancePlan, 
    Service, 
    CoverageRule, 
    MockPayerScript, 
    AuthorizationRequest, 
    Document,
    RequestEvent,
    PolicyDocument,
    PolicyChunk
)
from app.agents.rag.rag_pipeline import chunk_policy_text
from datetime import date, datetime

def seed_data():
    create_db_and_tables()
    with Session(engine) as session:
        # Check if policy documents are seeded
        if not session.query(PolicyDocument).first():
            seed_policies_into_db(session)

        # Check if reference data is already seeded
        if session.query(Patient).first():
            return
            
        # 1. Patients
        patients_list = [
            Patient(id="pat_1", full_name="Ahmed Ali", date_of_birth=date(1981, 3, 14), gender="M", mock_national_id="ABC-4471-9920"),
            Patient(id="pat_2", full_name="Sarah Chen", date_of_birth=date(1975, 8, 22), gender="F", mock_national_id="XYZ-9988-1122"),
            Patient(id="pat_3", full_name="James Wilson", date_of_birth=date(1990, 1, 5), gender="M", mock_national_id="XYZ-3344-5566"),
            Patient(id="pat_4", full_name="Mona Hassan", date_of_birth=date(1988, 11, 12), gender="F", mock_national_id="ABC-7788-3344"),
            Patient(id="pat_5", full_name="Omar Khaled", date_of_birth=date(1964, 7, 30), gender="M", mock_national_id="ABC-5522-8811"),
            Patient(id="pat_6", full_name="Fatima Al-Zahra", date_of_birth=date(1995, 4, 18), gender="F", mock_national_id="XYZ-4411-9900"),
            Patient(id="pat_7", full_name="David Miller", date_of_birth=date(1972, 9, 3), gender="M", mock_national_id="ABC-1234-5678"),
        ]
        session.add_all(patients_list)
        
        # 2. Plans (3 across 2 payers)
        pl1 = InsurancePlan(id="plan_abc_gold", payer_name="ABC Insurance", plan_name="ABC Gold PPO", plan_code="ABC-GOLD")
        pl2 = InsurancePlan(id="plan_abc_silver", payer_name="ABC Insurance", plan_name="ABC Silver HMO", plan_code="ABC-SILV")
        pl3 = InsurancePlan(id="plan_xyz_premier", payer_name="XYZ Health", plan_name="XYZ Premier PPO", plan_code="XYZ-PREM")
        session.add_all([pl1, pl2, pl3])
        
        # 3. Services (4)
        s1 = Service(id="svc_mri", code="70551", name="MRI Brain without contrast", category="imaging")
        s2 = Service(id="svc_ct", code="74177", name="CT Abdomen with contrast", category="imaging")
        s3 = Service(id="svc_consult", code="99245", name="Specialist Consultation", category="consult")
        s4 = Service(id="svc_knee", code="29881", name="Knee Arthroscopy", category="surgery")
        session.add_all([s1, s2, s3, s4])
        
        session.commit()
        
        # 4. Coverage Rules
        rules = [
            CoverageRule(
                plan_id="plan_abc_gold", 
                service_id="svc_mri", 
                status="prior_authorization_required", 
                requires_prior_authorization=True, 
                required_document_types=json.dumps(["insurance_card", "physician_order", "clinical_notes", "prior_imaging_report"]),
                conditions=json.dumps([
                    "Documented failure of conservative management for at least 4 weeks",
                    "Referral from a treating physician"
                ]),
                primary_section_ref="§4.2"
            ),
            CoverageRule(
                plan_id="plan_abc_gold", 
                service_id="svc_ct", 
                status="prior_authorization_required", 
                requires_prior_authorization=True, 
                required_document_types=json.dumps(["insurance_card", "physician_order", "clinical_notes", "prior_imaging_report"]),
                conditions=json.dumps(["Prior imaging report required for comparison"]),
                primary_section_ref="§5.1"
            ),
            CoverageRule(
                plan_id="plan_abc_gold", 
                service_id="svc_consult", 
                status="covered", 
                requires_prior_authorization=False, 
                required_document_types=json.dumps(["insurance_card", "physician_order"]),
                conditions=json.dumps(["Referral on file"]),
                primary_section_ref="§2.1"
            ),
            CoverageRule(
                plan_id="plan_abc_gold", 
                service_id="svc_knee", 
                status="not_covered", 
                requires_prior_authorization=False, 
                required_document_types=json.dumps([]),
                conditions=json.dumps([]),
                primary_section_ref="§8.1"
            )
        ]
        session.add_all(rules)
        
        # 5. Policy Documents & Policy Chunks in Database
        seed_policies_into_db(session)

        # 6. Mock Payer Scripts per PRD §20
        scripts = [
            MockPayerScript(service_id="svc_mri", attempt_number=1, decision="rejected", reason_code="insufficient_clinical_documentation", reason_text="Clinical documentation insufficient to establish medical necessity."),
            MockPayerScript(service_id="svc_mri", attempt_number=2, decision="approved", reason_code=None, reason_text="Approved. Authorization number ABC-AUTH-88214. Valid 60 days."),
            MockPayerScript(service_id="svc_ct", attempt_number=1, decision="more_info_required", reason_code="missing_document", reason_text="Prior imaging report required for comparison."),
            MockPayerScript(service_id="svc_ct", attempt_number=2, decision="approved", reason_code=None, reason_text="Approved. Authorization number ABC-AUTH-99012."),
            MockPayerScript(service_id="svc_consult", attempt_number=1, decision="approved", reason_code=None, reason_text="Approved under standard specialist benefit."),
            MockPayerScript(service_id="svc_knee", attempt_number=1, decision="rejected", reason_code="service_not_covered", reason_text="Procedure excluded under this plan.")
        ]
        session.add_all(scripts)
        session.commit()

        # 7. Pre-seed Demo Request in DRAFT with 3 documents attached (PRD §33)
        seed_demo_request(session)

def seed_policies_into_db(session: Session):
    policy_dir = os.path.join(os.path.dirname(__file__), "policies")
    if not os.path.exists(policy_dir):
        policy_dir = "app/seed/policies"
        
    for path in glob.glob(os.path.join(policy_dir, "*.md")):
        fname = os.path.basename(path)
        if fname.lower() == "readme.md":
            continue
        doc_id = os.path.splitext(fname)[0]
        
        plan_id = "plan_abc_gold" if "abc" in fname else "plan_xyz_premier"
        doc_kind = "coverage" if "coverage" in fname else ("authorization" if "auth" in fname else "documentation")
        
        with open(path, "r", encoding="utf-8") as f:
            raw_text = f.read()
            
        title_match = re.search(r"^#\s+(.+)$", raw_text, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else doc_id.replace("_", " ").title()
        
        existing_doc = session.get(PolicyDocument, doc_id)
        if not existing_doc:
            doc_obj = PolicyDocument(
                id=doc_id,
                plan_id=plan_id,
                title=title,
                doc_kind=doc_kind,
                raw_text=raw_text,
                created_at=datetime.utcnow()
            )
            session.add(doc_obj)
            
            # Chunk and add chunks
            chunks = chunk_policy_text(raw_text, doc_id, title)
            for ch in chunks:
                chunk_obj = PolicyChunk(
                    id=ch["id"],
                    policy_document_id=doc_id,
                    chunk_index=ch["chunk_index"],
                    section_ref=ch["section_ref"],
                    text=ch["text"],
                    token_count=ch["token_count"]
                )
                session.add(chunk_obj)
                
    session.commit()

def seed_demo_request(session: Session):
    existing = session.get(AuthorizationRequest, "req_demo_ahmed_mri")
    if existing:
        return existing
        
    demo_req = AuthorizationRequest(
        id="req_demo_ahmed_mri",
        patient_id="pat_1",
        plan_id="plan_abc_gold",
        service_id="svc_mri",
        member_number="ABC-4471-9920",
        physician_name="Dr. Hala Mansour",
        physician_id_mock="NPI-MOCK-2211",
        clinical_context="45yo male, persistent headaches for 6 weeks, failed conservative management with NSAIDs and physical therapy. Referral from Dr. Hala Mansour for diagnostic MRI Brain.",
        urgency="routine",
        status="DRAFT",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    session.add(demo_req)
    
    # Pre-attach 3 documents (Missing: prior_imaging_report)
    d1 = Document(
        id="doc_demo_card",
        request_id="req_demo_ahmed_mri",
        doc_type="insurance_card",
        file_name="ahmed_ali_insurance_card.pdf",
        mime_type="application/pdf",
        size_bytes=102400,
        storage_path="./uploads/req_demo_ahmed_mri/ahmed_ali_insurance_card.pdf",
        uploaded_at=datetime.utcnow(),
        uploaded_after_rejection=False
    )
    d2 = Document(
        id="doc_demo_order",
        request_id="req_demo_ahmed_mri",
        doc_type="physician_order",
        file_name="physician_order_mri_brain.pdf",
        mime_type="application/pdf",
        size_bytes=81920,
        storage_path="./uploads/req_demo_ahmed_mri/physician_order_mri_brain.pdf",
        uploaded_at=datetime.utcnow(),
        uploaded_after_rejection=False
    )
    d3 = Document(
        id="doc_demo_notes",
        request_id="req_demo_ahmed_mri",
        doc_type="clinical_notes",
        file_name="clinical_progress_notes_2026.pdf",
        mime_type="application/pdf",
        size_bytes=143360,
        storage_path="./uploads/req_demo_ahmed_mri/clinical_progress_notes_2026.pdf",
        uploaded_at=datetime.utcnow(),
        uploaded_after_rejection=False
    )
    session.add_all([d1, d2, d3])
    
    # Event
    evt = RequestEvent(
        request_id="req_demo_ahmed_mri",
        event_type="REQUEST_CREATED",
        actor="system",
        payload_json=json.dumps({"info": "Pre-seeded demo request with 3 documents"}),
        created_at=datetime.utcnow()
    )
    session.add(evt)
    session.commit()
    return demo_req

if __name__ == "__main__":
    seed_data()
