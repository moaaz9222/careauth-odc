import Link from "next/link";
import { api } from "@/lib/api";

export default async function Dashboard() {
  const data = await api.getRequests();
  const { counters, requests } = data;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-slate-900">Dashboard</h2>
        <Link 
          href="/requests/new" 
          className="bg-blue-600 text-white px-4 py-2 rounded-md font-medium hover:bg-blue-700 transition-colors"
        >
          New Authorization Request
        </Link>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {[
          { label: "Total", count: counters.total, color: "bg-slate-100" },
          { label: "Draft", count: counters.draft, color: "bg-slate-100" },
          { label: "Needs Documents", count: counters.needs_documents, color: "bg-amber-50" },
          { label: "Submitted", count: counters.submitted, color: "bg-blue-50" },
          { label: "Approved", count: counters.approved, color: "bg-green-50" },
          { label: "Action Required", count: counters.action_required, color: "bg-red-50" },
        ].map((stat, i) => (
          <div key={i} className={`p-4 rounded-lg border border-slate-200 ${stat.color}`}>
            <div className="text-sm font-medium text-slate-600">{stat.label}</div>
            <div className="text-2xl font-bold text-slate-900 mt-1">{stat.count}</div>
          </div>
        ))}
      </div>

      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Patient</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Payer</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Service</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Last Updated</th>
              <th className="px-6 py-3 relative">
                <span className="sr-only">View</span>
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-slate-200">
            {requests.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                  No authorization requests found.
                </td>
              </tr>
            ) : (
              requests.map((req) => (
                <tr key={req.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900">{req.patient_name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">{req.payer_name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">{req.service_name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-800">
                      {req.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                    {new Date(req.updated_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <Link href={`/requests/${req.id}`} className="text-blue-600 hover:text-blue-900">
                      View
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
