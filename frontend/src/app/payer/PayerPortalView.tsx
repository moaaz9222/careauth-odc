"use client";

import React, { useEffect, useState } from "react";

export function PayerPortalView() {
  const [submissions, setSubmissions] = useState<any[]>([]);
  const [mode, setMode] = useState<"scripted" | "manual">("scripted");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchSubmissions = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/payer/submissions");
      if (res.ok) {
        const data = await res.json();
        setSubmissions(data.submissions || []);
        // also get mode
        const modeRes = await fetch("http://localhost:8000/api/v1/payer/mode");
        if (modeRes.ok) {
          const modeData = await modeRes.json();
          setMode(modeData.mode);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchSubmissions();
    const interval = setInterval(fetchSubmissions, 2000);
    return () => clearInterval(interval);
  }, []);

  const toggleMode = async () => {
    const newMode = mode === "scripted" ? "manual" : "scripted";
    await fetch(`http://localhost:8000/api/v1/payer/mode`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: newMode })
    });
    setMode(newMode);
  };

  const submitDecision = async (subId: string, decision: string, reason_code: string = "", reason_text: string = "") => {
    await fetch(`http://localhost:8000/api/v1/payer/submissions/${subId}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, reason_code, reason_text })
    });
    setExpandedId(null);
    fetchSubmissions();
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <label className="flex items-center gap-2 text-slate-300">
          <span className="text-sm font-medium">Mode:</span>
          <button 
            onClick={toggleMode}
            className={`px-3 py-1 rounded text-sm font-medium ${mode === 'scripted' ? 'bg-teal-600 text-white' : 'bg-slate-700 text-slate-300'}`}
          >
            Scripted
          </button>
          <button 
            onClick={toggleMode}
            className={`px-3 py-1 rounded text-sm font-medium ${mode === 'manual' ? 'bg-teal-600 text-white' : 'bg-slate-700 text-slate-300'}`}
          >
            Manual
          </button>
        </label>
      </div>

      <div className="bg-slate-800 rounded-lg overflow-hidden border border-slate-700">
        <table className="min-w-full divide-y divide-slate-700">
          <thead className="bg-slate-900">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Sub #</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Patient</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Service</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Submitted</th>
            </tr>
          </thead>
          <tbody className="bg-slate-800 divide-y divide-slate-700">
            {submissions.map((sub) => (
              <React.Fragment key={sub.id}>
                <tr 
                  className="hover:bg-slate-750 cursor-pointer text-slate-300"
                  onClick={() => setExpandedId(expandedId === sub.id ? null : sub.id)}
                >
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{sub.submission_number}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{sub.patient_name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{sub.service_name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className={`px-2 py-1 rounded text-xs ${sub.status === 'pending' ? 'bg-amber-900 text-amber-200' : 'bg-slate-700 text-slate-300'}`}>
                      {sub.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{new Date(sub.submitted_at).toLocaleString()}</td>
                </tr>
                {expandedId === sub.id && (
                  <tr>
                    <td colSpan={5} className="bg-slate-900 p-6 border-b border-slate-700">
                      <div className="grid grid-cols-2 gap-6 text-slate-300 text-sm">
                        <div>
                          <h4 className="font-medium text-teal-400 mb-2">Packet Data</h4>
                          <pre className="bg-slate-950 p-4 rounded overflow-auto text-xs font-mono max-h-64">
                            {JSON.stringify(sub.packet_structured, null, 2)}
                          </pre>
                        </div>
                        <div className="space-y-4">
                          <h4 className="font-medium text-teal-400 mb-2">Reviewer Actions</h4>
                          {mode === "scripted" ? (
                            <div className="text-slate-400 italic">Actions disabled in scripted mode. The system will auto-respond.</div>
                          ) : sub.status !== "pending" ? (
                            <div className="text-slate-400 italic">Decision already recorded: {sub.status}</div>
                          ) : (
                            <div className="space-y-4">
                              <button 
                                onClick={() => submitDecision(sub.id, "approved")}
                                className="w-full bg-teal-600 text-white px-4 py-2 rounded hover:bg-teal-700"
                              >
                                Approve Request
                              </button>
                              
                              <div className="border border-slate-700 p-4 rounded bg-slate-800 space-y-3">
                                <h5 className="font-medium text-white">Reject / Request More Info</h5>
                                <textarea 
                                  id={`reason-${sub.id}`}
                                  className="w-full bg-slate-900 border-slate-700 rounded p-2 text-sm text-slate-300"
                                  placeholder="Enter reviewer notes here..."
                                  rows={3}
                                ></textarea>
                                
                                <div className="flex gap-2">
                                  <button onClick={() => { (document.getElementById(`reason-${sub.id}`) as HTMLTextAreaElement).value = "Clinical documentation insufficient to establish medical necessity."; }} className="text-xs bg-slate-700 px-2 py-1 rounded hover:bg-slate-600">Insufficient Clinical</button>
                                  <button onClick={() => { (document.getElementById(`reason-${sub.id}`) as HTMLTextAreaElement).value = "Missing previous imaging report."; }} className="text-xs bg-slate-700 px-2 py-1 rounded hover:bg-slate-600">Missing Imaging</button>
                                </div>
                                
                                <div className="flex gap-2 pt-2">
                                  <button 
                                    onClick={() => submitDecision(sub.id, "more_info_required", "missing_document", (document.getElementById(`reason-${sub.id}`) as HTMLTextAreaElement).value)}
                                    className="flex-1 bg-amber-600 text-white px-3 py-2 rounded hover:bg-amber-700 text-sm"
                                  >
                                    Request More Info
                                  </button>
                                  <button 
                                    onClick={() => submitDecision(sub.id, "rejected", "insufficient_clinical_documentation", (document.getElementById(`reason-${sub.id}`) as HTMLTextAreaElement).value)}
                                    className="flex-1 bg-red-600 text-white px-3 py-2 rounded hover:bg-red-700 text-sm"
                                  >
                                    Reject Request
                                  </button>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
