import { useHealth } from '@/hooks/useHealth'

export function Dashboard() {
  const { data, isLoading, isError } = useHealth()

  const backendStatus = isLoading ? 'Checking…' : isError ? '✗ Offline' : `✓ Online (v${data?.version})`
  const statusColor = isLoading ? 'text-yellow-500' : isError ? 'text-red-500' : 'text-green-500'

  return (
    <main className="flex-1 p-8">
      <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
      <p className="mt-1 text-sm text-slate-500">NexOps – AI-Powered DevOps Command Center</p>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-lg border bg-white p-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Application</p>
          <p className="mt-1 text-lg font-semibold text-green-600">✓ Running</p>
        </div>
        <div className="rounded-lg border bg-white p-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Backend API</p>
          <p className={`mt-1 text-lg font-semibold ${statusColor}`}>{backendStatus}</p>
        </div>
        <div className="rounded-lg border bg-white p-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Environment</p>
          <p className="mt-1 text-lg font-semibold text-slate-700">{data?.environment ?? '—'}</p>
        </div>
      </div>

      <div className="mt-8 rounded-lg border border-dashed bg-white p-10 text-center text-slate-400">
        <p className="text-lg font-medium">Dashboard content coming soon</p>
        <p className="mt-1 text-sm">Agent status, incident feed, and metrics will appear here.</p>
      </div>
    </main>
  )
}
