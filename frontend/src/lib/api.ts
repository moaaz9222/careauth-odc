import { RequestListResponse, RequestSummary, CoverageResult, DocumentationResult, ResolutionResult, SubmissionPacket, DocumentType, Urgency } from "./contracts";

const API_BASE = "http://localhost:8000/api/v1";

export interface RequestDetail extends RequestSummary {
  member_number: string;
  clinical_context: string;
  physician_name: string;
  urgency: Urgency;
  documents: { id: string; doc_type: DocumentType; file_name: string }[];
  coverage_analysis?: CoverageResult;
  documentation_analysis?: DocumentationResult;
  resolution_analysis?: ResolutionResult;
  timeline: any[]; // define later
}

// Temporary mock data to use while backend is down
const MOCK_REQUESTS: RequestListResponse = {
  requests: [],
  counters: { total: 0, draft: 0, needs_documents: 0, submitted: 0, approved: 0, action_required: 0 }
};

export const api = {
  getRequests: async (): Promise<RequestListResponse> => {
    try {
      const res = await fetch(`${API_BASE}/requests`, { cache: 'no-store' });
      if (!res.ok) throw new Error("Failed to fetch requests");
      return res.json();
    } catch (e) {
      console.warn("Using mock data for getRequests", e);
      return MOCK_REQUESTS;
    }
  },

  getRequest: async (id: string): Promise<RequestDetail> => {
    const res = await fetch(`${API_BASE}/requests/${id}`, { cache: 'no-store' });
    if (!res.ok) throw new Error("Failed to fetch request");
    return res.json();
  },

  createRequest: async (formData: FormData): Promise<{ id: string }> => {
    const res = await fetch(`${API_BASE}/requests`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error("Failed to create request");
    return res.json();
  },

  analyzeRequest: async (id: string): Promise<{ status: string }> => {
    const res = await fetch(`${API_BASE}/requests/${id}/analyze`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to analyze request");
    return res.json();
  },

  submitRequest: async (id: string): Promise<{ status: string }> => {
    const res = await fetch(`${API_BASE}/requests/${id}/submit`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to submit request");
    return res.json();
  },

  uploadDocument: async (id: string, formData: FormData): Promise<any> => {
    const res = await fetch(`${API_BASE}/requests/${id}/documents`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error("Failed to upload document");
    return res.json();
  },
  
  getReferenceData: async (): Promise<any> => {
    try {
      const res = await fetch(`${API_BASE}/reference`, { cache: 'no-store' });
      if (!res.ok) throw new Error("Failed to fetch reference data");
      return res.json();
    } catch (e) {
      console.warn("Using mock data for reference data", e);
      return {
        patients: [{ id: "p1", name: "Ahmed Ali", member_number: "ABC-4471-9920", dob: "1981-03-14" }],
        payers: [{ id: "payer1", name: "ABC Insurance" }],
        plans: [{ id: "plan_abc_gold", name: "ABC Gold PPO", payer_id: "payer1" }],
        services: [{ id: "svc_mri_brain", code: "70551", name: "MRI Brain without contrast" }]
      };
    }
  }
};
