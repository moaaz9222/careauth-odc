import { CreateRequestForm } from "./CreateRequestForm";
import { api } from "@/lib/api";

export default async function NewRequestPage() {
  const referenceData = await api.getReferenceData();
  
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">New Authorization Request</h2>
        <p className="text-slate-500 text-sm mt-1">Complete the details below to analyze coverage requirements.</p>
      </div>
      <CreateRequestForm referenceData={referenceData} />
    </div>
  );
}
