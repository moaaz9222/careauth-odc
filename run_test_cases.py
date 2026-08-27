import asyncio
import io
import os
import time
import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"
DOCS_DIR = "test_data/sample_documents"

def load_file_bytes(filename: str):
    path = os.path.join(DOCS_DIR, filename)
    with open(path, "rb") as f:
        return f.read()

async def run_all_test_cases():
    print("=" * 75)
    print("CAREAUTH AI -- COMPREHENSIVE TEST CASES EXECUTION SUITE")
    print("=" * 75)
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Reset DB before starting
        await client.post("/admin/reset")
        
        # -------------------------------------------------------------
        # TEST CASE 1: Full Prior Auth & Rejection Resolution (Ahmed Ali - MRI Brain)
        # -------------------------------------------------------------
        print("\n" + "-" * 75)
        print("TEST CASE 1: Prior Authorization with Missing Document & Rejection Resolution")
        print("-" * 75)
        print("Patient: Ahmed Ali | Plan: ABC Gold PPO | Service: MRI Brain without contrast (70551)")
        
        # 1.1 Create request
        data = {
            "patient_id": "pat_1",
            "plan_id": "plan_abc_gold",
            "service_id": "svc_mri",
            "member_number": "ABC-4471-9920",
            "physician_name": "Dr. Hala Mansour",
            "clinical_context": "45yo male with persistent daily headaches for 6 weeks, failed NSAIDs and physical therapy.",
            "urgency": "routine",
        }
        res = await client.post("/requests", data=data)
        assert res.status_code == 200, f"Failed create: {res.text}"
        req_id = res.json()["id"]
        print(f"  [1.1] Request created: {req_id} (Status: DRAFT)")
        
        # 1.2 Attach initial 3 documents (missing prior imaging report)
        files1 = {"files": ("01_insurance_card_ahmed_ali.pdf", load_file_bytes("01_insurance_card_ahmed_ali.pdf"), "application/pdf")}
        await client.post(f"/requests/{req_id}/documents", files=files1, data={"doc_types": "insurance_card"})
        
        files2 = {"files": ("02_physician_order_mri_brain.pdf", load_file_bytes("02_physician_order_mri_brain.pdf"), "application/pdf")}
        await client.post(f"/requests/{req_id}/documents", files=files2, data={"doc_types": "physician_order"})
        
        files3 = {"files": ("03_clinical_progress_notes.pdf", load_file_bytes("03_clinical_progress_notes.pdf"), "application/pdf")}
        await client.post(f"/requests/{req_id}/documents", files=files3, data={"doc_types": "clinical_notes"})
        print("  [1.2] Attached 3 documents: Insurance Card, Physician Order, Clinical Notes")
        
        # 1.3 Trigger AI Analysis
        res = await client.post(f"/requests/{req_id}/analyze")
        assert res.status_code == 200
        for _ in range(25):
            await asyncio.sleep(0.3)
            r = (await client.get(f"/requests/{req_id}")).json()
            if r["status"] != "ANALYZING":
                break
        print(f"  [1.3] Analysis resolved: Status={r['status']}")
        assert r["status"] == "NEEDS_DOCUMENTS"
        assert r["documentation_analysis"]["ready_for_submission"] is False
        assert r["documentation_analysis"]["missing_documents"][0]["doc_type"] == "prior_imaging_report"
        print(f"        Identified Missing Document: {r['documentation_analysis']['missing_documents'][0]['label']}")
        print(f"        Why Required: {r['documentation_analysis']['missing_documents'][0]['why_required']}")
        
        # 1.4 Upload missing Previous Imaging Report
        upload_files = {"files": ("04_prior_imaging_report_2024.pdf", load_file_bytes("04_prior_imaging_report_2024.pdf"), "application/pdf")}
        upload_data = {"doc_types": "prior_imaging_report"}
        res = await client.post(f"/requests/{req_id}/documents", files=upload_files, data=upload_data)
        assert res.status_code == 200
        print("  [1.4] Uploaded missing '04_prior_imaging_report_2024.pdf'")
        
        # 1.5 Re-analyze -> READY_FOR_SUBMISSION
        await client.post(f"/requests/{req_id}/analyze")
        for _ in range(25):
            await asyncio.sleep(0.3)
            r = (await client.get(f"/requests/{req_id}")).json()
            if r["status"] != "ANALYZING":
                break
        print(f"  [1.5] Re-analysis resolved: Status={r['status']}")
        assert r["status"] == "READY_FOR_SUBMISSION"
        assert r["documentation_analysis"]["ready_for_submission"] is True
        
        # 1.6 Submit Attempt 1 -> Expect Scripted Payer Rejection
        res = await client.post(f"/requests/{req_id}/submit")
        assert res.status_code == 200
        sub_info = res.json()
        print(f"  [1.6] Submitted Attempt #1: {sub_info['submission_number']}")
        
        # Wait 2.2s for Mock Payer response
        await asyncio.sleep(2.3)
        r = (await client.get(f"/requests/{req_id}")).json()
        print(f"  [1.7] Payer Response: Status={r['status']}")
        assert r["status"] == "ACTION_REQUIRED"
        assert r["resolution_analysis"] is not None
        print(f"        Payer Reason: '{r['resolution_analysis']['payer_reason_verbatim']}'")
        print(f"        AI Resolution Explanation: '{r['resolution_analysis']['explanation']}'")
        print(f"        Checklist: {r['resolution_analysis']['resubmission_checklist']}")
        
        # 1.8 Upload Detailed Notes Addendum & Resubmit Attempt 2
        upload_files = {"files": ("05_physician_notes_detailed_addendum.pdf", load_file_bytes("05_physician_notes_detailed_addendum.pdf"), "application/pdf")}
        upload_data = {"doc_types": "physician_notes_detailed"}
        await client.post(f"/requests/{req_id}/documents", files=upload_files, data=upload_data)
        print("  [1.8] Uploaded '05_physician_notes_detailed_addendum.pdf'")
        
        await client.post(f"/requests/{req_id}/analyze")
        for _ in range(25):
            await asyncio.sleep(0.3)
            r = (await client.get(f"/requests/{req_id}")).json()
            if r["status"] != "ANALYZING":
                break
        assert r["status"] == "READY_FOR_SUBMISSION"
        
        await client.post(f"/requests/{req_id}/submit")
        print("  [1.9] Resubmitted Attempt #2")
        await asyncio.sleep(2.3)
        r = (await client.get(f"/requests/{req_id}")).json()
        print(f"  [1.10] Final Outcome: Status={r['status']}")
        assert r["status"] == "APPROVED"
        print("  >>> TEST CASE 1 PASSED (100%) <<<\n")

        # -------------------------------------------------------------
        # TEST CASE 2: Covered Service (Specialist Consultation - Sarah Chen)
        # -------------------------------------------------------------
        print("-" * 75)
        print("TEST CASE 2: Covered Procedure (No Prior Auth Required)")
        print("-" * 75)
        print("Patient: Sarah Chen | Plan: ABC Gold PPO | Service: Specialist Consultation (99245)")
        
        data_tc2 = {
            "patient_id": "pat_2",
            "plan_id": "plan_abc_gold",
            "service_id": "svc_consult",
            "member_number": "XYZ-9988-1122",
            "physician_name": "Dr. Kareem Adel",
            "clinical_context": "Patient referred for evaluation of persistent knee mechanical catching.",
            "urgency": "routine",
        }
        res = await client.post("/requests", data=data_tc2)
        assert res.status_code == 200
        req_id_2 = res.json()["id"]
        
        files_card = {"files": ("01_insurance_card_ahmed_ali.pdf", load_file_bytes("01_insurance_card_ahmed_ali.pdf"), "application/pdf")}
        await client.post(f"/requests/{req_id_2}/documents", files=files_card, data={"doc_types": "insurance_card"})
        
        files_ref = {"files": ("08_referral_letter_specialist.pdf", load_file_bytes("08_referral_letter_specialist.pdf"), "application/pdf")}
        await client.post(f"/requests/{req_id_2}/documents", files=files_ref, data={"doc_types": "physician_order"})
        
        await client.post(f"/requests/{req_id_2}/analyze")
        for _ in range(25):
            await asyncio.sleep(0.3)
            r2 = (await client.get(f"/requests/{req_id_2}")).json()
            if r2["status"] != "ANALYZING":
                break
        print(f"  [2.1] Analysis resolved: Status={r2['status']}")
        assert r2["coverage_analysis"]["status"] == "covered"
        assert r2["coverage_analysis"]["requires_prior_authorization"] is False
        assert r2["status"] == "READY_FOR_SUBMISSION"
        print(f"        Coverage Reason: {r2['coverage_analysis']['reason']}")
        print("  >>> TEST CASE 2 PASSED (100%) <<<\n")

        # -------------------------------------------------------------
        # TEST CASE 3: Policy Exclusion / Not Covered (Knee Arthroscopy - James Wilson)
        # -------------------------------------------------------------
        print("-" * 75)
        print("TEST CASE 3: Non-Covered / Policy Excluded Service")
        print("-" * 75)
        print("Patient: James Wilson | Plan: ABC Gold PPO | Service: Knee Arthroscopy (29881)")
        
        data_tc3 = {
            "patient_id": "pat_3",
            "plan_id": "plan_abc_gold",
            "service_id": "svc_knee",
            "member_number": "XYZ-3344-5566",
            "physician_name": "Dr. Youssef Nabil",
            "clinical_context": "Patient requests elective arthroscopic knee debridement for chronic osteoarthritic changes.",
            "urgency": "routine",
        }
        res = await client.post("/requests", data=data_tc3)
        assert res.status_code == 200
        req_id_3 = res.json()["id"]
        
        await client.post(f"/requests/{req_id_3}/analyze")
        for _ in range(25):
            await asyncio.sleep(0.3)
            r3 = (await client.get(f"/requests/{req_id_3}")).json()
            if r3["status"] != "ANALYZING":
                break
        print(f"  [3.1] Analysis resolved: Status={r3['status']}")
        assert r3["coverage_analysis"]["status"] == "not_covered"
        print(f"        Coverage Status: {r3['coverage_analysis']['status']}")
        print(f"        Exclusion Explanation: {r3['coverage_analysis']['reason']}")
        print("  >>> TEST CASE 3 PASSED (100%) <<<\n")

        # -------------------------------------------------------------
        # TEST CASE 4: Security & Validation Guardrails (Negative Tests)
        # -------------------------------------------------------------
        print("-" * 75)
        print("TEST CASE 4: Security, Input Validation & State Machine Guardrails")
        print("-" * 75)
        
        # 4.1 Test clinical_context too short (< 20 chars)
        res = await client.post("/requests", data={
            "patient_id": "pat_1", "plan_id": "plan_abc_gold", "service_id": "svc_mri",
            "member_number": "ABC-123", "physician_name": "Dr. Test", "clinical_context": "Headache"
        })
        print(f"  [4.1] Short clinical context test: Status={res.status_code} (Expected 422)")
        assert res.status_code == 422
        
        # 4.2 Test unsupported file type (.exe)
        bad_file = {"files": ("malicious_payload.exe", b"MZ\x90\x00BinaryExeContent", "application/octet-stream")}
        res = await client.post(f"/requests/{req_id}/documents", files=bad_file, data={"doc_types": "other"})
        print(f"  [4.2] Unsupported file extension (.exe): Status={res.status_code} (Expected 415)")
        assert res.status_code == 415
        
        # 4.3 Test file too large (> 10MB)
        large_file = {"files": ("huge_scan.pdf", b"0" * (11 * 1024 * 1024), "application/pdf")}
        res = await client.post(f"/requests/{req_id}/documents", files=large_file, data={"doc_types": "other"})
        print(f"  [4.3] File too large (>10MB): Status={res.status_code} (Expected 413)")
        assert res.status_code == 413
        
        print("  >>> TEST CASE 4 PASSED (100%) <<<\n")

    print("=" * 75)
    print("ALL 4 COMPREHENSIVE TEST CASES PASSED WITH 100% SUCCESS!")
    print("=" * 75)

if __name__ == "__main__":
    asyncio.run(run_all_test_cases())
