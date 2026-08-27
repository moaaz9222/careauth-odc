import asyncio
import io
import time
import httpx
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000/api/v1"

async def run_end_to_end_verification():
    print("=" * 70)
    print("CAREAUTH AI — END-TO-END DEMO SCENARIO INTEGRATION TEST")
    print("=" * 70)
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Step 1: Admin Reset
        print("\n[Step 1] POST /admin/reset")
        t0 = time.time()
        res = await client.post("/admin/reset")
        reset_duration = time.time() - t0
        assert res.status_code == 200, f"Reset failed: {res.text}"
        print(f"  -> Reset response: {res.json()}")
        print(f"  -> Reset duration: {reset_duration:.2f}s (< 2.0s requirement: {'PASS' if reset_duration < 2.0 else 'FAIL'})")
        assert reset_duration < 2.0

        # Step 2: Dashboard verification
        print("\n[Step 2] GET /requests")
        res = await client.get("/requests")
        assert res.status_code == 200
        data = res.json()
        reqs = data["requests"]
        counters = data["counters"]
        print(f"  -> Total requests: {len(reqs)}")
        print(f"  -> Counters: {counters}")
        assert len(reqs) >= 1
        demo_req_id = reqs[0]["id"]
        assert reqs[0]["status"] == "DRAFT"

        # Step 3: Get Request Detail (Act 1: Pre-seeded in DRAFT with 3 docs)
        print(f"\n[Step 3] GET /requests/{demo_req_id}")
        res = await client.get(f"/requests/{demo_req_id}")
        assert res.status_code == 200
        req_data = res.json()
        print(f"  -> Patient: {req_data['patient_name']}")
        print(f"  -> Service: {req_data['service_name']}")
        print(f"  -> Plan: {req_data['plan_name']}")
        print(f"  -> Attached Documents count: {len(req_data['documents'])}")
        assert len(req_data['documents']) == 3
        assert req_data["status"] == "DRAFT"

        # Step 4: Trigger AI Analysis
        print(f"\n[Step 4] POST /requests/{demo_req_id}/analyze")
        res = await client.post(f"/requests/{demo_req_id}/analyze")
        assert res.status_code == 200
        print(f"  -> Analyze triggered: {res.json()}")

        # Step 5: Wait and Poll for Analysis Completion
        print("  -> Polling for analysis resolution...")
        for _ in range(20):
            await asyncio.sleep(0.5)
            res = await client.get(f"/requests/{demo_req_id}")
            req_data = res.json()
            if req_data["status"] != "ANALYZING":
                break
                
        print(f"  -> Resolved Status: {req_data['status']}")
        assert req_data["status"] == "NEEDS_DOCUMENTS"
        doc_analysis = req_data["documentation_analysis"]
        cov_analysis = req_data["coverage_analysis"]
        assert doc_analysis is not None
        assert cov_analysis is not None
        print(f"  -> Coverage Status: {cov_analysis['status']}")
        print(f"  -> Coverage Evidence Strength: {cov_analysis['evidence_strength']}")
        print(f"  -> Evidence Count: {len(cov_analysis['evidence'])}")
        assert len(cov_analysis["evidence"]) >= 1
        print(f"  -> Verbatim Snippet: '{cov_analysis['evidence'][0]['snippet']}'")
        print(f"  -> Documentation ready_for_submission: {doc_analysis['ready_for_submission']}")
        assert doc_analysis["ready_for_submission"] is False
        assert len(doc_analysis["missing_documents"]) == 1
        assert doc_analysis["missing_documents"][0]["doc_type"] == "prior_imaging_report"
        print(f"  -> Missing document identified: {doc_analysis['missing_documents'][0]['label']}")
        print(f"  -> Blocking summary: {doc_analysis['blocking_summary']}")

        # Step 6: Verify Server-Side Submission Gating
        print("\n[Step 6] Attempting illegal POST /submit when NEEDS_DOCUMENTS")
        res = await client.post(f"/requests/{demo_req_id}/submit")
        print(f"  -> Response Status: {res.status_code}")
        assert res.status_code == 409
        print(f"  -> Gating enforced: {res.json()}")

        # Step 7: Upload Missing Document (prior_imaging_report)
        print("\n[Step 7] Uploading missing 'prior_imaging_report'")
        file_payload = {"files": ("prior_mri_2024.pdf", io.BytesIO(b"%PDF-1.4 Mock MRI Imaging Report 2024"), "application/pdf")}
        data_payload = {"doc_types": "prior_imaging_report"}
        res = await client.post(f"/requests/{demo_req_id}/documents", files=file_payload, data=data_payload)
        assert res.status_code == 200
        print(f"  -> Document uploaded successfully: {res.json()}")

        # Step 8: Re-Analyze
        print("\n[Step 8] POST /requests/{demo_req_id}/analyze (Re-analysis)")
        res = await client.post(f"/requests/{demo_req_id}/analyze")
        assert res.status_code == 200

        print("  -> Polling for re-analysis resolution...")
        for _ in range(20):
            await asyncio.sleep(0.5)
            res = await client.get(f"/requests/{demo_req_id}")
            req_data = res.json()
            if req_data["status"] != "ANALYZING":
                break
                
        print(f"  -> Resolved Status: {req_data['status']}")
        assert req_data["status"] == "READY_FOR_SUBMISSION"
        assert req_data["documentation_analysis"]["ready_for_submission"] is True
        print("  -> All 4 required documents now verified present!")

        # Step 9: Submit Request (Attempt 1)
        print("\n[Step 9] POST /requests/{demo_req_id}/submit (Attempt 1)")
        res = await client.post(f"/requests/{demo_req_id}/submit")
        assert res.status_code == 200
        sub_info = res.json()
        print(f"  -> Submission Created: {sub_info}")
        assert "PA-" in sub_info["submission_number"]

        # Step 10: Wait for Mock Payer Response (2s delay in scripted mode)
        print("\n[Step 10] Awaiting Mock Payer Scripted Response (~2s)...")
        await asyncio.sleep(2.5)
        res = await client.get(f"/requests/{demo_req_id}")
        req_data = res.json()
        print(f"  -> Status after attempt 1: {req_data['status']}")
        assert req_data["status"] == "ACTION_REQUIRED"
        res_analysis = req_data["resolution_analysis"]
        assert res_analysis is not None
        print(f"  -> Payer verbatim reason: '{res_analysis['payer_reason_verbatim']}'")
        print(f"  -> AI Explanation: '{res_analysis['explanation']}'")
        print(f"  -> Recommended Actions: {len(res_analysis['recommended_actions'])} actions")
        print(f"  -> Resubmission Checklist: {res_analysis['resubmission_checklist']}")
        assert len(res_analysis["resubmission_checklist"]) <= 5

        # Step 11: Upload detailed physician progress notes per checklist
        print("\n[Step 11] Attaching 'physician_notes_detailed' as requested by resolution action")
        file_payload = {"files": ("detailed_notes_addendum.pdf", io.BytesIO(b"%PDF-1.4 Detailed clinical addendum"), "application/pdf")}
        data_payload = {"doc_types": "physician_notes_detailed"}
        res = await client.post(f"/requests/{demo_req_id}/documents", files=file_payload, data=data_payload)
        assert res.status_code == 200

        # Step 12: Re-analyze before resubmission
        print("\n[Step 12] Re-analyzing request")
        await client.post(f"/requests/{demo_req_id}/analyze")
        for _ in range(20):
            await asyncio.sleep(0.5)
            res = await client.get(f"/requests/{demo_req_id}")
            req_data = res.json()
            if req_data["status"] != "ANALYZING":
                break
        assert req_data["status"] == "READY_FOR_SUBMISSION"
        print(f"  -> Ready for resubmission: {req_data['status']}")

        # Step 13: Resubmit (Attempt 2)
        print("\n[Step 13] POST /requests/{demo_req_id}/submit (Attempt 2 - Resubmission)")
        res = await client.post(f"/requests/{demo_req_id}/submit")
        assert res.status_code == 200
        print(f"  -> Resubmitted attempt 2: {res.json()}")

        # Step 14: Await Mock Payer Approval (~2s)
        print("\n[Step 14] Awaiting Mock Payer Approval for Attempt 2...")
        await asyncio.sleep(2.5)
        res = await client.get(f"/requests/{demo_req_id}")
        req_data = res.json()
        print(f"  -> Final Request Status: {req_data['status']}")
        assert req_data["status"] == "APPROVED"
        assert len(req_data["submissions"]) == 2
        assert len(req_data["responses"]) == 2
        print(f"  -> Payer Approval Response: {req_data['responses'][-1]['reason_text']}")

        # Step 15: Timeline verification
        print(f"\n[Step 15] Verifying Full Request Timeline")
        events = req_data["events"]
        print(f"  -> Total Timeline Events logged: {len(events)}")
        for evt in events:
            print(f"     * [{evt['created_at']}] {evt['event_type']} (by {evt['actor']})")
        assert len(events) >= 10

        # Step 16: Payer Portal API Check
        print("\n[Step 16] GET /payer/submissions")
        res = await client.get("/payer/submissions")
        assert res.status_code == 200
        payer_data = res.json()
        print(f"  -> Submissions listed in payer console: {len(payer_data['submissions'])}")
        assert len(payer_data["submissions"]) >= 2
        
        print("\n" + "=" * 70)
        print("ALL DEMO SCENARIO INTEGRATION STEPS COMPLETED 100% CLEANLY!")
        print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_end_to_end_verification())
