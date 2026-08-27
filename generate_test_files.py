import os

def create_sample_pdf(filepath: str, title: str, content: str):
    """Create a minimal valid PDF-1.4 file with human-readable plain text structure"""
    stream_content = f"BT /F1 16 Tf 50 750 Td ({title}) Tj ET\n"
    y = 710
    for line in content.split("\n"):
        # escape parens
        clean_line = line.replace("(", "\\(").replace(")", "\\)")
        stream_content += f"BT /F1 10 Tf 50 {y} Td ({clean_line}) Tj ET\n"
        y -= 18
        if y < 50:
            break
            
    stream_bytes = stream_content.encode("latin-1", "replace")
    stream_len = len(stream_bytes)
    
    pdf_text = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length {stream_len} >>
stream
{stream_content}endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000240 00000 n 
0000000000 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
500
%%EOF"""
    with open(filepath, "wb") as f:
        f.write(pdf_text.encode("latin-1", "replace"))

def generate_all_sample_files():
    out_dir = "test_data/sample_documents"
    os.makedirs(out_dir, exist_ok=True)
    
    # 1. Insurance Card
    create_sample_pdf(
        os.path.join(out_dir, "01_insurance_card_ahmed_ali.pdf"),
        "ABC Insurance -- Member ID Card",
        "Member Name: Ahmed Ali\nSubscriber ID: ABC-4471-9920\nPlan: ABC Gold PPO\nGroup #: G-88219\nEffective Date: 2024-01-01\nRxBIN: 610014 | RxPCN: MEDD\nPayer ID: 99124 - ABC Health Network"
    )
    
    # 2. Physician Order (MRI Brain)
    create_sample_pdf(
        os.path.join(out_dir, "02_physician_order_mri_brain.pdf"),
        "Physician Requisition Order -- Diagnostic Imaging",
        "Patient: Ahmed Ali (DOB: 1981-03-14)\nOrdering Provider: Dr. Hala Mansour, MD (NPI: 1982736451)\nRequested Procedure: MRI Brain without contrast (CPT: 70551)\nClinical Indication: Chronic refractory daily tension headaches >6 weeks.\nHistory: Failed NSAID therapy and muscle relaxants. No red flag trauma.\nUrgency: Routine Outpatient\nDate: 2026-08-20"
    )
    
    # 3. Clinical Progress Notes
    create_sample_pdf(
        os.path.join(out_dir, "03_clinical_progress_notes.pdf"),
        "Outpatient Neurological Progress Note",
        "Patient Name: Ahmed Ali | Age: 45 | Date of Encounter: 2026-08-15\nChief Complaint: Persistent frontal and occipital headaches x 6 weeks.\nSubjective: Moderate pain (6/10), unprovoked, daily frequency.\nMedication Trial: Ibuprofen 600mg TID (4 weeks) - no relief.\nPhysical Exam: Cranial nerves II-XII grossly intact. No focal deficit.\nAssessment: Refractory tension-type headache with migraine features.\nPlan: Order non-contrast brain MRI to rule out structural intracranial pathology."
    )
    
    # 4. Previous Imaging Report (The key missing document for Act 1)
    create_sample_pdf(
        os.path.join(out_dir, "04_prior_imaging_report_2024.pdf"),
        "Radiology Report -- Head CT Without Contrast (Historical)",
        "Patient: Ahmed Ali | Exam Date: 2024-03-10 | Facility: City Imaging Center\nAccession #: RAD-2024-8819 | Modality: Computed Tomography Head\nClinical Indication: Mild concussion following minor fall.\nFindings: No acute intracranial hemorrhage or territorial infarction.\nVentricles and sulci are within normal limits for age.\nImpression: Unremarkable non-contrast head CT scan."
    )
    
    # 5. Detailed Physician Progress Notes Addendum (The key document for resolving Attempt 1 rejection)
    create_sample_pdf(
        os.path.join(out_dir, "05_physician_notes_detailed_addendum.pdf"),
        "Physician Addendum -- Medical Necessity Timeline & Conservative Therapy",
        "Patient: Ahmed Ali | Member: ABC-4471-9920 | Date: 2026-08-25\nAddendum to Order for CPT 70551 (MRI Brain without contrast):\n1. Conservative Management Timeline: Patient completed 6 continuous weeks\nof structured physical therapy (2x/week) and failed two classes of analgesics.\n2. Clinical Necessity: Headaches have intensified from episodic to daily.\nNon-contrast CT from 2024 is remote and insufficient for soft tissue brain evaluation.\n3. Ordering Physician: Dr. Hala Mansour, MD -- Board Certified Neurologist."
    )
    
    # 6. CT Abdomen Order
    create_sample_pdf(
        os.path.join(out_dir, "06_physician_order_ct_abdomen.pdf"),
        "Physician Order -- CT Abdomen & Pelvis With Contrast",
        "Patient: Mona Hassan | Plan: ABC Gold PPO | Date: 2026-08-22\nCPT Code: 74177 (CT Abdomen with IV Contrast)\nIndication: Persistent Right Lower Quadrant Abdominal Pain.\nLabs: Elevated WBC (12.4), Normal renal panel (eGFR > 60).\nOrdering Provider: Dr. Youssef Nabil, MD"
    )
    
    # 7. Lab Results Panel
    create_sample_pdf(
        os.path.join(out_dir, "07_lab_results_panel.pdf"),
        "Comprehensive Diagnostic Laboratory Panel",
        "Patient: Sarah Chen | Collection Date: 2026-08-18\nCBC: WBC 6.8, Hgb 14.2, Plt 245 | BMP: Na 140, K 4.1, Cr 0.82, BUN 14\neGFR: >90 mL/min/1.73m2 | LFTs: AST 22, ALT 24, AlkPhos 68\nStatus: Final Verified by Pathology"
    )
    
    # 8. Referral Letter
    create_sample_pdf(
        os.path.join(out_dir, "08_referral_letter_specialist.pdf"),
        "Specialist Consultation Referral Letter",
        "To: Department of Orthopedic Surgery | From: Dr. Kareem Adel (PCP)\nPatient: Sarah Chen (DOB: 1975-08-22)\nReason for Referral: Evaluation for persistent knee joint pain and mechanical catching.\nRequested Service: CPT 99245 (Specialist Consultation)"
    )

    print("Successfully generated all sample test PDF files in:", os.path.abspath(out_dir))

if __name__ == "__main__":
    generate_all_sample_files()
