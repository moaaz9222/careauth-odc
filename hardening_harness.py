import asyncio
import io
import time
import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"

async def run_single_demo_cycle(run_index: int, client: httpx.AsyncClient):
    print(f"\n>>> Starting Demo Scenario Run #{run_index} <<<")
    
    # 1. Reset
    t0 = time.time()
    res = await client.post("/admin/reset")
    reset_time = time.time() - t0
    assert res.status_code == 200, f"Run {run_index}: Reset failed: {res.text}"
    assert reset_time < 2.0, f"Run {run_index}: Reset took {reset_time:.2f}s (>= 2s)"
    
    # 2. Check draft demo request
    res = await client.get("/requests")
    assert res.status_code == 200
    data = res.json()
    assert len(data["requests"]) >= 1
    demo_id = data["requests"][0]["id"]
    
    # 3. Analyze -> should transition to NEEDS_DOCUMENTS
    res = await client.post(f"/requests/{demo_id}/analyze")
    assert res.status_code == 200
    
    # Poll until resolved
    for _ in range(25):
        await asyncio.sleep(0.3)
        res = await client.get(f"/requests/{demo_id}")
        rdata = res.json()
        if rdata["status"] != "ANALYZING":
            break
    assert rdata["status"] == "NEEDS_DOCUMENTS", f"Expected NEEDS_DOCUMENTS, got {rdata['status']}"
    assert rdata["documentation_analysis"]["ready_for_submission"] is False
    assert len(rdata["coverage_analysis"]["evidence"]) >= 1
    
    # 4. Gating check
    res = await client.post(f"/requests/{demo_id}/submit")
    assert res.status_code == 409, f"Expected 409 blocked, got {res.status_code}"
    
    # 5. Upload missing prior imaging report
    file_payload = {"files": ("prior_mri_2024.pdf", io.BytesIO(b"%PDF-1.4 Mock MRI Imaging Report 2024"), "application/pdf")}
    data_payload = {"doc_types": "prior_imaging_report"}
    res = await client.post(f"/requests/{demo_id}/documents", files=file_payload, data=data_payload)
    assert res.status_code == 200
    
    # 6. Re-analyze -> READY_FOR_SUBMISSION
    res = await client.post(f"/requests/{demo_id}/analyze")
    assert res.status_code == 200
    for _ in range(25):
        await asyncio.sleep(0.3)
        res = await client.get(f"/requests/{demo_id}")
        rdata = res.json()
        if rdata["status"] != "ANALYZING":
            break
    assert rdata["status"] == "READY_FOR_SUBMISSION", f"Expected READY_FOR_SUBMISSION, got {rdata['status']}"
    assert rdata["documentation_analysis"]["ready_for_submission"] is True
    
    # 7. Submit attempt 1
    res = await client.post(f"/requests/{demo_id}/submit")
    assert res.status_code == 200
    assert rdata["status"] in ("READY_FOR_SUBMISSION", "SUBMITTED")
    
    # 8. Wait 2.2s for Mock Payer rejection
    await asyncio.sleep(2.3)
    res = await client.get(f"/requests/{demo_id}")
    rdata = res.json()
    assert rdata["status"] == "ACTION_REQUIRED", f"Expected ACTION_REQUIRED, got {rdata['status']}"
    assert rdata["resolution_analysis"] is not None
    assert len(rdata["resolution_analysis"]["resubmission_checklist"]) <= 5
    
    # 9. Upload detailed physician notes & re-analyze
    file_payload = {"files": ("detailed_physician_notes.pdf", io.BytesIO(b"%PDF-1.4 Detailed clinical notes"), "application/pdf")}
    data_payload = {"doc_types": "physician_notes_detailed"}
    res = await client.post(f"/requests/{demo_id}/documents", files=file_payload, data=data_payload)
    assert res.status_code == 200
    
    await client.post(f"/requests/{demo_id}/analyze")
    for _ in range(25):
        await asyncio.sleep(0.3)
        res = await client.get(f"/requests/{demo_id}")
        rdata = res.json()
        if rdata["status"] != "ANALYZING":
            break
    assert rdata["status"] == "READY_FOR_SUBMISSION"
    
    # 10. Resubmit (Attempt 2)
    res = await client.post(f"/requests/{demo_id}/submit")
    assert res.status_code == 200
    
    # 11. Wait 2.2s for Mock Payer approval
    await asyncio.sleep(2.3)
    res = await client.get(f"/requests/{demo_id}")
    rdata = res.json()
    assert rdata["status"] == "APPROVED", f"Expected APPROVED, got {rdata['status']}"
    assert len(rdata["events"]) >= 10
    
    print(f"  -> Run #{run_index} PASSED cleanly in {time.time() - t0:.2f}s!")

async def main():
    print("=" * 70)
    print("CAREAUTH AI — DEMO HARDENING HARNESS (5 CONSECUTIVE CLEAN RUNS)")
    print("=" * 70)
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        for i in range(1, 6):
            await run_single_demo_cycle(i, client)
            
    print("\n" + "=" * 70)
    print("SUCCESS: 5 / 5 CONSECUTIVE RUNS COMPLETED WITH ZERO ERRORS!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
