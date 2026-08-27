"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { DocumentType } from "@/lib/contracts";

export function RequestDetailView({ requestId }: { requestId: string }) {
  const router = useRouter();
  const [request, setRequest] = useState<any>(null);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [activeUploadDocType, setActiveUploadDocType] = useState<string>("");
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [expandedSubmission, setExpandedSubmission] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const fetchRequest = async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/requests/${requestId}`);
      if (res.ok) {
        const data = await res.json();
        setRequest(data);
      } else {
        setError("Failed to load request.");
      }
    } catch (e) {
      setError("Network error.");
    }
  };

  useEffect(() => {
    fetchRequest();
  }, [requestId]);

  useEffect(() => {
    let interval: any;
    if (request?.status === "ANALYZING" || request?.status === "SUBMITTED") {
      interval = setInterval(() => {
        fetchRequest();
      }, 1500);
    }
    return () => clearInterval(interval);
  }, [request?.status]);

  if (error) return <div className="text-red-600 p-6">{error}</div>;
  if (!request) return <div className="p-6">Loading authorization request...</div>;

  const isAnalyzing = request.status === "ANALYZING";
  const covAnalysis = request.coverage_analysis;
  const docAnalysis = request.documentation_analysis;
  const readyForSubmission = docAnalysis?.ready_for_submission && covAnalysis?.status !== "unknown";

  const handleAnalyze = async () => {
    showToast("Triggering parallel AI analysis...");
    await fetch(`http://localhost:8000/api/v1/requests/${requestId}/analyze`, { method: "POST" });
    fetchRequest();
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    showToast("Generating packet and transmitting to payer...");
    await fetch(`http://localhost:8000/api/v1/requests/${requestId}/submit`, { method: "POST" });
    fetchRequest();
    setIsSubmitting(false);
  };

  const handleUploadClick = (docType: string) => {
    setActiveUploadDocType(docType);
    fileInputRef.current?.click();
  };

  const onFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setIsUploading(true);
      const file = e.target.files[0];
      const formData = new FormData();
      formData.append("files", file);
      formData.append("doc_types", activeUploadDocType || DocumentType.OTHER);
      
      showToast(`Uploading ${file.name}...`);
      await fetch(`http://localhost:8000/api/v1/requests/${requestId}/documents`, {
        method: "POST",
        body: formData
      });
      
      if (fileInputRef.current) fileInputRef.current.value = "";
      setActiveUploadDocType("");
      setIsUploading(false);
      
      // Auto re-analyze on document upload
      showToast("Document attached. Re-analyzing request...");
      await handleAnalyze();
    }
  };

  const copyPacket = (text: string) => {
    navigator.clipboard.writeText(text);
    showToast("Packet markdown copied to clipboard!");
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-4 right-4 z-50 bg-slate-900 text-white px-4 py-3 rounded-lg shadow-xl border border-slate-700 text-sm flex items-center gap-2 animate-in fade-in slide-in-from-top-2">
          <span>ℹ️</span>
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header */}
      <div className="bg-white p-6 rounded-lg border border-slate-200 flex justify-between items-start shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold text-slate-900">{request.patient_name || request.patient?.full_name}</h2>
            <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">
              {request.member_number}
            </span>
          </div>
          <div className="text-sm text-slate-600 mt-1.5 flex items-center gap-2">
            <span className="font-medium text-slate-800">{request.payer_name || request.plan?.payer_name}</span>
            <span>•</span>
            <span>{request.plan_name || request.plan?.plan_name}</span>
            <span>•</span>
            <span className="text-blue-700 font-medium">{request.service_name || request.service?.name}</span>
          </div>
          {request.submission_number && (
            <div className="text-sm font-semibold text-slate-800 mt-2 flex items-center gap-2">
              <span className="text-slate-500 font-normal">Active Submission:</span>
              <span className="bg-blue-50 text-blue-800 px-2 py-0.5 rounded border border-blue-200 font-mono">
                {request.submission_number}
              </span>
            </div>
          )}
        </div>
        <div>
          <span className={`px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider ${
            request.status === 'APPROVED' ? 'bg-green-100 text-green-800 border border-green-300' :
            request.status === 'ACTION_REQUIRED' ? 'bg-red-100 text-red-800 border border-red-300 animate-pulse' :
            request.status === 'READY_FOR_SUBMISSION' ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' :
            request.status === 'NEEDS_DOCUMENTS' ? 'bg-amber-100 text-amber-800 border border-amber-300' :
            request.status === 'SUBMITTED' ? 'bg-blue-100 text-blue-800 border border-blue-300' :
            'bg-slate-100 text-slate-800 border border-slate-300'
          }`}>
            {request.status.replace(/_/g, ' ')}
          </span>
        </div>
      </div>

      {/* Hidden file input for inline uploads */}
      <input type="file" ref={fileInputRef} className="hidden" onChange={onFileSelected} />

      {/* AI Assessment */}
      <div className="space-y-4">
        {request.analysis_stale && (
          <div className="bg-amber-50 border border-amber-400 text-amber-900 px-4 py-3 rounded-lg text-sm font-medium flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span>⚠️</span>
              <span>This analysis is out of date due to recent document changes. Please re-analyze before submitting.</span>
            </div>
            <button onClick={handleAnalyze} className="bg-amber-600 text-white text-xs px-3 py-1.5 rounded font-semibold hover:bg-amber-700">
              Re-analyze Now
            </button>
          </div>
        )}
        <div className="flex items-center justify-between border-b pb-2">
          <h3 className="text-lg font-bold text-slate-900">AI Assessment</h3>
          <span className="text-xs text-slate-400 font-medium">Decision Support • RAG Grounded</span>
        </div>
        
        {/* Coverage Card */}
        <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-semibold text-slate-900">1. Coverage Determination</h4>
            <span className="text-xs text-slate-400 italic">Based on {request.plan_name || "insurance"} policy</span>
          </div>
          {isAnalyzing && !covAnalysis ? (
            <div className="animate-pulse flex space-x-4">
              <div className="flex-1 space-y-3 py-1">
                <div className="h-4 bg-slate-200 rounded w-3/4"></div>
                <div className="h-4 bg-slate-200 rounded w-1/2"></div>
              </div>
            </div>
          ) : covAnalysis ? (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <span className="px-3 py-1 rounded-md text-xs font-bold uppercase tracking-wider bg-indigo-100 text-indigo-900 border border-indigo-200">
                  {covAnalysis.status.replace(/_/g, ' ')}
                </span>
                <span 
                  title="Evidence strength derived from RAG retrieval similarity floor and rules table match." 
                  className="text-xs px-2.5 py-1 bg-slate-100 text-slate-700 rounded-md border font-medium cursor-help"
                >
                  Evidence Strength: <strong>{covAnalysis.evidence_strength.toUpperCase()}</strong>
                </span>
              </div>
              <p className="text-sm text-slate-800 leading-relaxed">{covAnalysis.reason}</p>
              
              {covAnalysis.conditions?.length > 0 && (
                <div className="text-sm text-slate-700 bg-slate-50 p-3 rounded border">
                  <strong className="text-slate-900">Policy Conditions:</strong>
                  <ul className="list-disc pl-5 mt-1.5 space-y-1">
                    {covAnalysis.conditions.map((c: string, i: number) => <li key={i}>{c}</li>)}
                  </ul>
                </div>
              )}
              
              <details className="mt-4 border-t pt-3 group">
                <summary className="text-xs font-semibold text-blue-600 cursor-pointer hover:underline flex items-center gap-1">
                  <span>Policy Evidence ({covAnalysis.evidence?.length || 0} citations)</span>
                </summary>
                <div className="mt-3 space-y-3">
                  {covAnalysis.evidence?.map((ev: any, idx: number) => (
                    <div key={idx} className="bg-slate-50 p-3 rounded-lg border text-xs space-y-1">
                      <div className="font-bold text-slate-900 flex justify-between">
                        <span>{ev.policy_document_title} — {ev.section_ref}</span>
                        {ev.similarity > 0 && <span className="text-slate-400 font-normal">sim: {ev.similarity}</span>}
                      </div>
                      <div className="text-slate-700 italic border-l-2 border-indigo-400 pl-2 py-0.5">
                        "{ev.snippet}"
                      </div>
                    </div>
                  ))}
                </div>
              </details>
            </div>
          ) : (
            <div className="text-sm text-slate-500">Not analyzed yet. Click 'Analyze Request' to evaluate.</div>
          )}
        </div>

        {/* Documentation Card */}
        <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-semibold text-slate-900">2. Documentation Verification</h4>
            <span className="text-xs text-slate-400 italic">Deterministic gap analysis</span>
          </div>
          {isAnalyzing && !docAnalysis ? (
            <div className="animate-pulse flex space-x-4">
              <div className="flex-1 space-y-3 py-1">
                <div className="h-4 bg-slate-200 rounded w-full"></div>
                <div className="h-4 bg-slate-200 rounded w-5/6"></div>
              </div>
            </div>
          ) : docAnalysis ? (
            <div className="space-y-4">
              {docAnalysis.ready_for_submission ? (
                <div className="text-sm font-medium text-emerald-800 bg-emerald-50 p-3.5 rounded-lg border border-emerald-200 flex items-center gap-2">
                  <span className="text-lg">✅</span>
                  <span>All required documentation verified present. Request is ready for submission!</span>
                </div>
              ) : (
                <div className="text-sm font-medium text-white bg-red-600 p-4 rounded-lg shadow-sm border-l-4 border-red-900 space-y-1">
                  <div className="font-bold flex items-center gap-1.5 text-base">
                    <span>⛔</span>
                    <span>Submission Blocked</span>
                  </div>
                  <div className="text-red-50">{docAnalysis.blocking_summary}</div>
                </div>
              )}
              
              <div className="space-y-2.5">
                {docAnalysis.required_documents?.map((req: any, idx: number) => {
                  const isMissing = docAnalysis.missing_documents?.find((m: any) => m.doc_type === req.doc_type);
                  return (
                    <div key={idx} className={`p-3.5 border rounded-lg transition-colors ${isMissing ? 'bg-red-50/40 border-red-200' : 'bg-slate-50 border-slate-200'}`}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-base">{isMissing ? '❌' : '✅'}</span>
                          <span className={`font-semibold text-sm ${isMissing ? 'text-red-950' : 'text-slate-900'}`}>{req.label}</span>
                          {req.mandatory && <span className="text-xs text-red-600 font-bold" title="Mandatory document">*</span>}
                        </div>
                        <span className="text-xs font-mono text-slate-500 bg-white px-2 py-0.5 rounded border">{req.source_section}</span>
                      </div>
                      
                      {isMissing && (
                        <div className="mt-2.5 ml-6 text-xs text-slate-700 space-y-1.5">
                          <p><strong className="text-slate-900">Why required:</strong> {isMissing.why_required}</p>
                          <p><strong className="text-slate-900">How to obtain:</strong> {isMissing.how_to_obtain}</p>
                          <button 
                            onClick={() => handleUploadClick(isMissing.doc_type)}
                            disabled={isUploading}
                            className="mt-2 bg-red-600 text-white px-3 py-1.5 rounded text-xs font-semibold hover:bg-red-700 shadow-sm flex items-center gap-1"
                          >
                            <span>📎</span>
                            <span>Upload {req.label}</span>
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="text-sm text-slate-500">Not analyzed yet.</div>
          )}
        </div>
      </div>

      {/* Resolution Panel (Rendered only in ACTION_REQUIRED) */}
      {request.status === "ACTION_REQUIRED" && request.resolution_analysis && (
        <div className="bg-red-50 border-2 border-red-300 p-6 rounded-xl space-y-5 shadow-sm">
          <div className="flex items-center justify-between border-b border-red-200 pb-3">
            <h3 className="text-lg font-bold text-red-950 flex items-center gap-2">
              <span>⚠️</span>
              <span>Payer Response Resolution Assistant</span>
            </h3>
            <span className="text-xs font-bold uppercase tracking-wider bg-red-200 text-red-900 px-2.5 py-1 rounded">
              {request.resolution_analysis.decision}
            </span>
          </div>
          
          <div className="bg-white p-4 rounded-lg border border-red-200 text-sm space-y-1">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Payer Verbatim Notice:</span>
            <p className="text-slate-900 font-medium italic">"{request.resolution_analysis.payer_reason_verbatim}"</p>
          </div>
          
          <div className="text-sm text-slate-800 leading-relaxed">
            <strong className="text-slate-900">AI Explanation: </strong>
            {request.resolution_analysis.explanation}
          </div>
          
          <div className="space-y-2.5">
            <h4 className="font-bold text-sm text-slate-900">Recommended Resolution Actions:</h4>
            {request.resolution_analysis.recommended_actions?.map((act: any, idx: number) => (
              <div key={idx} className="bg-white p-3.5 rounded-lg border border-slate-200 text-xs flex justify-between items-center shadow-sm">
                <div>
                  <div className="font-bold text-slate-900 text-sm">{act.order}. {act.label}</div>
                  <div className="text-slate-600 mt-0.5">{act.detail}</div>
                </div>
                {act.kind === "upload_document" && (
                  <button 
                    onClick={() => handleUploadClick(act.doc_type)}
                    className="bg-blue-600 text-white px-3 py-1.5 rounded text-xs font-semibold hover:bg-blue-700 shadow-sm ml-4 whitespace-nowrap"
                  >
                    Upload Document
                  </button>
                )}
              </div>
            ))}
          </div>
          
          <div className="space-y-2 bg-white p-4 rounded-lg border border-red-200">
            <h4 className="font-bold text-sm text-slate-900 mb-2">Resubmission Checklist:</h4>
            {request.resolution_analysis.resubmission_checklist?.map((item: string, idx: number) => (
              <label key={idx} className="flex items-center gap-2 text-xs text-slate-800 cursor-pointer">
                <input type="checkbox" className="rounded border-slate-300 text-blue-600 focus:ring-blue-500" />
                <span>{item}</span>
              </label>
            ))}
          </div>
          
          <button 
            onClick={handleSubmit} 
            disabled={isSubmitting}
            className="mt-2 bg-red-600 text-white px-6 py-2.5 rounded-lg font-bold hover:bg-red-700 w-full shadow transition-colors"
          >
            {isSubmitting ? "Submitting..." : "Resubmit Request (Attempt 2)"}
          </button>
        </div>
      )}

      {/* Action Bar */}
      <div className="flex flex-wrap items-center gap-3 pt-4 border-t">
        {request.status === "DRAFT" && (
          <button 
            onClick={handleAnalyze}
            className="bg-blue-600 text-white px-6 py-2 rounded-md font-semibold hover:bg-blue-700 shadow-sm"
          >
            Analyze Request
          </button>
        )}

        {["NEEDS_DOCUMENTS", "READY_FOR_SUBMISSION"].includes(request.status) && (
          <>
            <button 
              onClick={() => handleUploadClick("")}
              className="bg-white border border-slate-300 text-slate-700 px-4 py-2 rounded-md font-semibold hover:bg-slate-50 text-sm shadow-sm"
            >
              Upload Additional Document
            </button>
            
            <button 
              onClick={handleAnalyze}
              className="bg-white border border-slate-300 text-slate-700 px-4 py-2 rounded-md font-semibold hover:bg-slate-50 text-sm shadow-sm"
            >
              Re-analyze
            </button>
            
            <button 
              onClick={handleSubmit}
              disabled={!readyForSubmission || isSubmitting || request.analysis_stale}
              title={
                request.analysis_stale ? "Analysis is stale. Please re-analyze." : 
                !readyForSubmission ? "Cannot submit with missing documents or unknown coverage" : "Generate packet and submit to payer"
              }
              className="ml-auto bg-blue-600 text-white px-6 py-2 rounded-md font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm text-sm"
            >
              {isSubmitting ? "Submitting..." : "Continue to Submission"}
            </button>
          </>
        )}

        {request.status === "APPROVED" && (
          <div className="bg-green-50 border border-green-300 text-green-900 px-4 py-2.5 rounded-md font-bold text-sm w-full flex items-center justify-between">
            <span>🎉 Prior Authorization Approved — Authorization # ABC-AUTH-88214 (Valid 60 days)</span>
            <button 
              onClick={() => {
                if (request.submissions?.[0]?.packet_markdown) {
                  copyPacket(request.submissions[0].packet_markdown);
                }
              }}
              className="text-xs bg-green-700 text-white px-3 py-1 rounded hover:bg-green-800"
            >
              Export Packet
            </button>
          </div>
        )}
      </div>

      {/* Submissions & Timeline */}
      <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm space-y-6">
        <div>
          <h3 className="text-lg font-bold text-slate-900 border-b pb-2 mb-4">Authorization Packet & Submissions</h3>
          {request.submissions?.length > 0 ? (
            <div className="space-y-3">
              {request.submissions.map((sub: any, idx: number) => (
                <div key={idx} className="border rounded-lg p-4 bg-slate-50 space-y-2">
                  <div className="flex justify-between items-center">
                    <div className="font-bold text-sm text-slate-900">{sub.submission_number} (Attempt #{sub.attempt_number})</div>
                    <div className="flex gap-2">
                      <button 
                        onClick={() => copyPacket(sub.packet_markdown)}
                        className="text-xs bg-white border border-slate-300 text-slate-700 px-2.5 py-1 rounded hover:bg-slate-100"
                      >
                        Copy Packet
                      </button>
                      <button 
                        onClick={() => setExpandedSubmission(expandedSubmission === sub.id ? null : sub.id)}
                        className="text-xs bg-blue-50 text-blue-700 border border-blue-200 px-2.5 py-1 rounded hover:bg-blue-100 font-medium"
                      >
                        {expandedSubmission === sub.id ? "Hide Packet" : "View Packet"}
                      </button>
                    </div>
                  </div>
                  {expandedSubmission === sub.id && (
                    <div className="mt-3 bg-white p-4 rounded border text-xs font-mono whitespace-pre-wrap max-h-80 overflow-auto">
                      {sub.packet_markdown}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">No submissions transmitted yet.</p>
          )}
        </div>

        <div>
          <h3 className="text-lg font-bold text-slate-900 border-b pb-2 mb-4">Request Event Timeline</h3>
          <div className="space-y-3">
            {request.events?.map((evt: any, idx: number) => (
              <div key={idx} className="flex items-start gap-3 text-xs border-l-2 border-slate-300 pl-4 py-1">
                <span className="font-mono text-slate-400 whitespace-nowrap">
                  {new Date(evt.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
                <span className="font-bold text-slate-900 uppercase tracking-wider">{evt.event_type}</span>
                <span className="text-slate-500">by {evt.actor}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      
    </div>
  );
}
