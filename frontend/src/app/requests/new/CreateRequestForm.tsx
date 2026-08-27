"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { DocumentType } from "@/lib/contracts";

export function CreateRequestForm({ referenceData }: { referenceData: any }) {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [documents, setDocuments] = useState<{ file: File; docType: string }[]>([]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newDocs = Array.from(e.target.files).map(file => ({ file, docType: "" }));
      setDocuments([...documents, ...newDocs]);
    }
  };

  const removeDoc = (index: number) => {
    setDocuments(documents.filter((_, i) => i !== index));
  };

  const updateDocType = (index: number, type: string) => {
    const updated = [...documents];
    updated[index].docType = type;
    setDocuments(updated);
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    
    // Check mandatory document types
    const missingTypes = documents.some(d => !d.docType);
    if (missingTypes) {
      alert("Please select a document type for all uploaded files.");
      return;
    }

    setIsSubmitting(true);
    const formData = new FormData(e.currentTarget);
    
    // append documents
    documents.forEach((doc, i) => {
      formData.append("files", doc.file);
      formData.append("doc_types", doc.docType);
    });

    try {
      const res = await fetch("/api/v1/requests", { // Let's call the backend directly or via an internal API route? No, wait, if I call backend directly I might hit CORS. I'll construct FormData and pass it to api client, but I am in browser so I should call http://localhost:8000/api/v1 directly if it has CORS, or I'll just use full URL.
        method: "POST",
        body: formData
      });
      // Actually let's use the full API URL for simplicity
      const backendRes = await fetch("http://localhost:8000/api/v1/requests", {
        method: "POST",
        body: formData
      });
      
      if (!backendRes.ok) {
        throw new Error("Failed to create request");
      }
      
      const data = await backendRes.json();
      
      // Auto trigger analyze since submit label is "Create & Analyze"
      await fetch(`http://localhost:8000/api/v1/requests/${data.id}/analyze`, { method: "POST" });
      
      router.push(`/requests/${data.id}`);
    } catch (err) {
      console.error(err);
      alert("Error creating request");
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-8 bg-white p-6 rounded-lg border border-slate-200">
      
      <section>
        <h3 className="text-lg font-medium text-slate-900 border-b pb-2 mb-4">Patient & Insurance</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Patient</label>
            <select name="patient_id" required className="w-full border-slate-300 rounded-md border p-2">
              <option value="">Select Patient...</option>
              {referenceData.patients.map((p: any) => (
                <option key={p.id} value={p.id}>{p.name} ({p.dob})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Member Number</label>
            <input type="text" name="member_number" required className="w-full border-slate-300 rounded-md border p-2" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Plan</label>
            <select name="plan_id" required className="w-full border-slate-300 rounded-md border p-2">
              <option value="">Select Plan...</option>
              {referenceData.plans.map((p: any) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
        </div>
      </section>

      <section>
        <h3 className="text-lg font-medium text-slate-900 border-b pb-2 mb-4">Service</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Requested Service</label>
            <select name="service_id" required className="w-full border-slate-300 rounded-md border p-2">
              <option value="">Select Service...</option>
              {referenceData.services.map((s: any) => (
                <option key={s.id} value={s.id}>[{s.code}] {s.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Urgency</label>
            <select name="urgency" className="w-full border-slate-300 rounded-md border p-2">
              <option value="routine">Routine</option>
              <option value="urgent">Urgent</option>
            </select>
          </div>
        </div>
      </section>

      <section>
        <h3 className="text-lg font-medium text-slate-900 border-b pb-2 mb-4">Physician & Clinical Context</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Physician Name</label>
            <input type="text" name="physician_name" required className="w-full border-slate-300 rounded-md border p-2" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Clinical Context</label>
            <textarea name="clinical_context" required minLength={20} rows={4} className="w-full border-slate-300 rounded-md border p-2" placeholder="Provide clinical justification (min 20 characters)..."></textarea>
          </div>
        </div>
      </section>

      <section>
        <h3 className="text-lg font-medium text-slate-900 border-b pb-2 mb-4">Documents</h3>
        <div className="space-y-4">
          <div>
            <input type="file" multiple onChange={handleFileChange} className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" />
          </div>
          
          {documents.length > 0 && (
            <div className="space-y-2 mt-4">
              {documents.map((doc, i) => (
                <div key={i} className="flex items-center gap-3 p-3 bg-slate-50 border border-slate-200 rounded-md">
                  <span className="flex-1 text-sm truncate font-medium">{doc.file.name}</span>
                  <select 
                    value={doc.docType} 
                    onChange={(e) => updateDocType(i, e.target.value)}
                    required
                    className="border-slate-300 rounded border p-1 text-sm bg-white"
                  >
                    <option value="" disabled>Select Type...</option>
                    {Object.entries(DocumentType).map(([k, v]) => (
                      <option key={v} value={v}>{v}</option>
                    ))}
                  </select>
                  <button type="button" onClick={() => removeDoc(i)} className="text-red-500 text-sm hover:underline">Remove</button>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      <div className="flex justify-end pt-4">
        <button type="submit" disabled={isSubmitting} className="bg-blue-600 text-white px-6 py-2 rounded-md font-medium hover:bg-blue-700 transition-colors disabled:opacity-50">
          {isSubmitting ? "Creating & Analyzing..." : "Create & Analyze"}
        </button>
      </div>

    </form>
  );
}
