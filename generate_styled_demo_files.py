import os

def create_styled_pdf(filepath: str, title: str, subtitle: str, fields: list, body_paragraphs: list, footer: str = ""):
    """Generates clean, realistic formatted PDF documents for presentation demos"""
    stream = f"BT /F1 16 Tf 50 750 Td ({title}) Tj ET\n"
    stream += f"BT /F2 10 Tf 50 732 Td ({subtitle}) Tj ET\n"
    
    # Draw a line separator conceptually
    y = 705
    for label, val in fields:
        clean_label = label.replace("(", "\\(").replace(")", "\\)")
        clean_val = str(val).replace("(", "\\(").replace(")", "\\)")
        stream += f"BT /F1 9 Tf 50 {y} Td ({clean_label}:) Tj ET\n"
        stream += f"BT /F2 9 Tf 180 {y} Td ({clean_val}) Tj ET\n"
        y -= 16
        
    y -= 10
    for p in body_paragraphs:
        for line in p.split("\n"):
            clean_line = line.replace("(", "\\(").replace(")", "\\)")
            stream += f"BT /F2 9 Tf 50 {y} Td ({clean_line}) Tj ET\n"
            y -= 14
        y -= 8
        if y < 80:
            break
            
    if footer:
        stream += f"BT /F2 8 Tf 50 50 Td ({footer.replace('(', '\\(').replace(')', '\\)')}) Tj ET\n"

    stream_bytes = stream.encode("latin-1", "replace")
    stream_len = len(stream_bytes)
    
    pdf_content = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>
endobj
4 0 obj
<< /Length {stream_len} >>
stream
{stream}endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>
endobj
6 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 7
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000255 00000 n 
0000000000 00000 n 
0000000000 00000 n 
trailer
<< /Size 7 /Root 1 0 R >>
startxref
500
%%EOF"""
    with open(filepath, "wb") as f:
        f.write(pdf_content.encode("latin-1", "replace"))

def generate_live_demo_files():
    kit_dir = "LIVE_DEMO_KIT"
    os.makedirs(kit_dir, exist_ok=True)
    
    # Document 1: Insurance Card
    create_styled_pdf(
        os.path.join(kit_dir, "01_Insurance_Card_Ahmed_Ali.pdf"),
        "ABC HEALTHCARE NETWORK -- MEMBER IDENTIFICATION",
        "Official Proof of Active Insurance Coverage & Benefit Tier",
        [
            ("Patient Full Name", "Ahmed Ali"),
            ("Member / Subscriber ID", "ABC-4471-9920"),
            ("Plan Name", "ABC Gold PPO Network"),
            ("Group Policy Number", "GRP-99482-GOLD"),
            ("Effective Date", "January 01, 2024 -- Active"),
            ("Copay Tier", "Specialist: $30 | Advanced Imaging: 10% Coinsurance"),
            ("Prior Auth Required", "Yes -- For All Advanced Outpatient Imaging"),
        ],
        [
            "Payer Contact for Authorizations: ABC Insurance Prior Authorization Unit",
            "Electronic Submission Portal: CareAuth Electronic Interchange Gateway",
            "Customer Service: 1-800-555-0199 | Provider Pre-Auth Line: 1-800-555-0122"
        ],
        footer="CONFIDENTIAL HEALTHCARE DOCUMENT -- FOR PRIOR AUTHORIZATION USE ONLY"
    )
    
    # Document 2: Physician Order (MRI Brain)
    create_styled_pdf(
        os.path.join(kit_dir, "02_Physician_Order_Brain_MRI.pdf"),
        "METROPOLITAN NEUROLOGY CLINIC -- PHYSICIAN ORDER",
        "Clinical Requisition for Outpatient Diagnostic Neuroimaging",
        [
            ("Patient Name", "Ahmed Ali (Age 45, Gender: Male)"),
            ("Date of Birth", "1981-03-14"),
            ("Ordering Physician", "Dr. Hala Mansour, MD -- Board Certified Neurologist"),
            ("Physician NPI", "NPI-1982736451 | State License: ME-88319"),
            ("Requested Service", "MRI Brain Without Contrast"),
            ("CPT Procedure Code", "70551 (Magnetic Resonance Imaging Brain)"),
            ("Primary ICD-10 Diagnosis", "G44.209 (Tension-type headache, unspecified, intractable)"),
            ("Secondary ICD-10 Diagnosis", "R51.9 (Headache, unspecified, chronic daily)"),
        ],
        [
            "Clinical Order Rationale:\nPatient presents with progressive daily frontal-occipital headaches lasting greater than 6 weeks.\nPain intensity is worsening (rated 6-7/10). Failed outpatient conservative oral NSAID regimen.\nRequesting non-contrast brain MRI to rule out intracranial mass lesion or structural etiology.",
            "Physician Electronic Signature: Dr. Hala Mansour, MD (Signed 2026-08-20 09:45 AM EST)"
        ],
        footer="METROPOLITAN NEUROLOGY CLINIC -- 100 HEALTH PARKWAY, SUITE 400"
    )
    
    # Document 3: Clinical Notes
    create_styled_pdf(
        os.path.join(kit_dir, "03_Clinical_Progress_Notes.pdf"),
        "CLINICAL PROGRESS NOTE -- OUTPATIENT NEUROLOGY",
        "Comprehensive Patient Encounter & History of Present Illness",
        [
            ("Patient", "Ahmed Ali"),
            ("Encounter Date", "2026-08-15"),
            ("Attending Physician", "Dr. Hala Mansour, MD"),
            ("Vital Signs", "BP: 124/82 mmHg | HR: 72 bpm | Temp: 36.8 C | SpO2: 99%"),
        ],
        [
            "Subjective / History of Present Illness:\n45-year-old male with no prior history of chronic migraines presents with new-onset persistent\ndaily headaches for the past 6 continuous weeks. Symptoms unprovoked, worse in afternoons.\nPatient tried over-the-counter Ibuprofen 600mg TID and Acetaminophen for 4 weeks with zero relief.\nDenies fever, visual aura, motor weakness, or recent head trauma.",
            "Physical & Neurological Examination:\nAlert and oriented x 3. Cranial nerves II-XII intact. Sensation intact bilaterally.\nMotor strength 5/5 in all extremities. No pronator drift. Reflexes 2+ symmetric.\nFunduscopic exam: Sharp disc margins bilaterally, no papilledema noted.",
            "Assessment & Plan:\n1. Chronic refractory headache syndrome -- rule out intracranial mass or vascular lesion.\n2. Ordering non-contrast Brain MRI (CPT 70551).\n3. Initiating physical therapy referral and lifestyle modifications."
        ],
        footer="DOCUMENT GENERATED FROM EPIC EHR -- ENCOUNTER ID: ENC-2026-88192"
    )
    
    # Document 4: Previous Imaging Report (THE KEY MISSING DOCUMENT FOR STEP 2)
    create_styled_pdf(
        os.path.join(kit_dir, "04_PREVIOUS_IMAGING_REPORT_MISSING_DOC.pdf"),
        "ADVANCED RADIOLOGY PARTNERS -- HISTORICAL REPORT",
        "Prior Non-Contrast Head CT Examination (For Baseline Comparison)",
        [
            ("Patient Name", "Ahmed Ali"),
            ("Exam Date", "2024-03-10 (Historical Baseline)"),
            ("Accession Number", "RAD-CT-2024-88102"),
            ("Modality", "Computed Tomography (CT) Head / Brain without IV contrast"),
            ("Referring Physician", "Dr. Kareem Adel, MD (Emergency Medicine)"),
            ("Indication", "Minor head contusion following slip and fall at work"),
        ],
        [
            "Comparative Findings:\n- No evidence of acute intracranial hemorrhage, extra-axial fluid collection, or mass effect.\n- Ventricular system and cortical sulci are symmetrical and normal in size for patient age.\n- Basal cisterns are patent. Bony calvarium and skull base appear intact without fracture.\n- Visualized paranasal sinuses and mastoid air cells are clear.",
            "Impression:\n1. Normal non-contrast head CT scan. No acute intracranial trauma.\n2. Note: CT scan from 2024 is remote and did not utilize MRI soft-tissue parenchymal resolution.",
            "Interpreting Radiologist: Dr. Tariq Al-Sayed, MD -- Board Certified Radiologist"
        ],
        footer="ADVANCED RADIOLOGY PARTNERS -- ARCHIVE PACS RECORD"
    )
    
    # Document 5: Detailed Physician Notes Addendum (THE KEY RECOVERY DOCUMENT FOR STEP 3)
    create_styled_pdf(
        os.path.join(kit_dir, "05_DETAILED_PHYSICIAN_NOTES_ADDENDUM.pdf"),
        "PHYSICIAN EXPANDED CLINICAL ADDENDUM",
        "Response to Payer Prior Authorization Documentation Request",
        [
            ("Patient Name", "Ahmed Ali (Member ID: ABC-4471-9920)"),
            ("Ordering Provider", "Dr. Hala Mansour, MD (Neurology)"),
            ("Date of Addendum", "2026-08-25"),
            ("Regarding Request", "Prior Authorization Appeal / Re-evaluation for CPT 70551"),
        ],
        [
            "Specific Clarification of Medical Necessity & Conservative Management:\nTo Medical Review Board -- ABC Insurance:\n\n1. Conservative Therapy Trial Timeline (§4.2 Policy Compliance):\nPatient has documented failure of conservative management exceeding 6 weeks:\n- NSAIDs: Ibuprofen 600mg TID and Naproxen 500mg BID for 4 weeks (No improvement).\n- Physical Therapy: Completed 6 weeks of cervical spine and posture therapy (2 sessions/week).\n- Muscle relaxants: Cyclobenzaprine 10mg nightly for 2 weeks (Discontinued due to lack of efficacy).",
            "2. Soft Tissue MRI Necessity vs 2024 CT Scan:\nPrevious normal CT scan from 2024 was performed for acute trauma, not parenchymal evaluation.\nMRI is uniquely indicated to rule out structural dural lesions, microvascular ischemia, or posterior fossa pathology.",
            "Conclusion: Clinical documentation establishes full medical necessity under Plan Policy §4.2.\nAttending Physician: Dr. Hala Mansour, MD -- Chief of Neurology"
        ],
        footer="OFFICIAL ADDENDUM ATTACHED TO ELECTRONIC AUTHORIZATION DOSSIER"
    )

    print("Successfully generated all 5 live presentation files in LIVE_DEMO_KIT/")

if __name__ == "__main__":
    generate_live_demo_files()
