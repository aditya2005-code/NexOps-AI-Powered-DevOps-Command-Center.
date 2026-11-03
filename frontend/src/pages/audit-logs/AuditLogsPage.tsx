import { useState } from 'react'
import { Search, ScrollText, Download, ShieldCheck } from 'lucide-react'
import { PageHeader } from '@/components/common/PageHeader'
import { StatusBadge } from '@/components/common/StatusBadge'
import { EmptyState } from '@/components/common/EmptyState'
import { Button } from '@/components/ui/button'
import { DEMO_AUDIT_LOGS } from '@/constants/mockData'

export function AuditLogsPage() {
  const [search, setSearch] = useState('')
  const [actorFilter, setActorFilter] = useState<'all' | 'user' | 'agent' | 'system'>('all')

  const filteredLogs = DEMO_AUDIT_LOGS.filter((log) => {
    const matchesSearch =
      log.action.toLowerCase().includes(search.toLowerCase()) ||
      log.actor.toLowerCase().includes(search.toLowerCase()) ||
      log.resource.toLowerCase().includes(search.toLowerCase())
    const matchesActor = actorFilter === 'all' || log.actorType === actorFilter
    return matchesSearch && matchesActor
  })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit Logs & Traceability"
        subtitle="Immutable ledger of human-in-the-loop decisions, agent executions, and configuration mutations."
        actions={
          <Button
            variant="outline"
            className="text-xs h-8 border-[#29344e] text-slate-300 hover:text-white gap-1.5"
            onClick={() => alert('Exporting audit log ledger (Demo mode)')}
          >
            <Download className="w-3.5 h-3.5" />
            Export JSON
          </Button>
        }
      />

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3 rounded-lg border border-[#1e2436] bg-[#121622]">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search action, actor, or target resource..."
            className="w-full h-8.5 pl-8 pr-3 rounded-md border border-[#1e2436] bg-[#0c0e15] text-xs text-slate-200 placeholder:text-slate-400 focus:outline-hidden focus:border-indigo-500/50"
          />
        </div>

        <div className="flex items-center gap-1.5 self-end sm:self-auto text-xs">
          {(['all', 'user', 'agent', 'system'] as const).map((type) => (
            <button
              key={type}
              onClick={() => setActorFilter(type)}
              className={`px-3 py-1.5 rounded-md font-medium capitalize transition-colors ${
                actorFilter === type
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:bg-[#1a2030] hover:text-slate-200 border border-transparent'
              }`}
            >
              {type === 'all' ? 'All Actors' : type}
            </button>
          ))}
        </div>
      </div>

      {/* Audit Log Table */}
      {filteredLogs.length === 0 ? (
        <EmptyState
          title="No audit entries found"
          description="Try broadening your search term or selecting all actor categories."
          icon={ScrollText}
          actionLabel="Reset Search"
          onAction={() => {
            setSearch('')
            setActorFilter('all')
          }}
        />
      ) : (
        <div className="rounded-lg border border-[#1e2436] bg-[#121622] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#0e111a] text-slate-400 uppercase tracking-wider font-semibold border-b border-[#1e2436]">
                <tr>
                  <th className="px-4 py-3">Timestamp (UTC)</th>
                  <th className="px-4 py-3">Actor</th>
                  <th className="px-4 py-3">Action</th>
                  <th className="px-4 py-3">Resource / Target</th>
                  <th className="px-4 py-3 text-right">Result</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e2436]/60 text-slate-300">
                {filteredLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-[#181d2c]/50 transition-colors">
                    <td className="px-4 py-3 whitespace-nowrap font-mono text-slate-400">
                      {log.timestamp}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap font-medium text-slate-200">
                      <div className="flex items-center gap-1.5">
                        <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
                        <span>{log.actor}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="font-mono text-[11px] text-cyan-300 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                        {log.action}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-300 font-mono text-[11px]">
                      {log.resource}
                    </td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <StatusBadge status={log.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

