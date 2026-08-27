import { PayerPortalView } from "./PayerPortalView";

export default function PayerPage() {
  return (
    <div className="min-h-screen bg-slate-900 -m-6 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <header className="border-b border-slate-700 pb-4 flex justify-between items-center text-white">
          <h1 className="text-2xl font-bold text-teal-400">ABC Insurance — Reviewer Console</h1>
          <div className="text-sm text-slate-400">Mock Payer Portal</div>
        </header>
        <PayerPortalView />
      </div>
    </div>
  );
}
