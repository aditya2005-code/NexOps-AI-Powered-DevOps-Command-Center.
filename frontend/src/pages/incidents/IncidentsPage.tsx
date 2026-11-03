import { useState } from 'react'
import { Search, ShieldAlert, X, Sparkles, CheckCircle2 } from 'lucide-react'
import { PageHeader } from '@/components/common/PageHeader'
import { SeverityBadge } from '@/components/common/SeverityBadge'
import { StatusBadge } from '@/components/common/StatusBadge'
import { EmptyState } from '@/components/common/EmptyState'
import { Button } from '@/components/ui/button'
import { DEMO_INCIDENTS } from '@/constants/mockData'
import type { Incident } from '@/types'

export function IncidentsPage() {
  const [search, setSearch] = useState('')
  const [severityFilter, setSeverityFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null)

  const filteredIncidents = DEMO_INCIDENTS.filter((inc) => {
    const matchesSearch =
      inc.title.toLowerCase().includes(search.toLowerCase()) ||
      inc.id.toLowerCase().includes(search.toLowerCase()) ||
      inc.project.toLowerCase().includes(search.toLowerCase())
    const matchesSeverity = severityFilter === 'all' || inc.severity === severityFilter
    const matchesStatus = statusFilter === 'all' || inc.status === statusFilter
    return matchesSearch && matchesSeverity && matchesStatus
  })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Incident Queue & Investigation"
        subtitle="Active anomalies detected by telemetry probes and investigated by autonomous AI agents."
        actions={
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-mono">
              Total: {DEMO_INCIDENTS.length} | Open: {DEMO_INCIDENTS.filter((i) => i.status !== 'resolved').length}
            </span>
          </div>
        }
      />

      {/* Filter and Search Controls */}
      <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 p-3.5 rounded-lg border border-[#1e2436] bg-[#121622]">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by incident ID, title, or project..."
            className="w-full h-8.5 pl-8 pr-3 rounded-md border border-[#1e2436] bg-[#0c0e15] text-xs text-slate-200 placeholder:text-slate-400 focus:outline-hidden focus:border-indigo-500/50"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Severity selector */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="h-8 px-2.5 rounded-md border border-[#1e2436] bg-[#0c0e15] text-xs text-slate-300 focus:outline-hidden focus:border-indigo-500/50"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          {/* Status selector */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-8 px-2.5 rounded-md border border-[#1e2436] bg-[#0c0e15] text-xs text-slate-300 focus:outline-hidden focus:border-indigo-500/50"
          >
            <option value="all">All Statuses</option>
            <option value="open">Open</option>
            <option value="investigating">Investigating</option>
            <option value="awaiting_approval">Awaiting Approval</option>
            <option value="resolved">Resolved</option>
          </select>
        </div>
      </div>

      {/* Incident List Table */}
      {filteredIncidents.length === 0 ? (
        <EmptyState
          title="No incidents match criteria"
          description="Try clearing your search query or adjusting your severity/status filters."
          icon={ShieldAlert}
          actionLabel="Reset Filters"
          onAction={() => {
            setSearch('')
            setSeverityFilter('all')
            setStatusFilter('all')
          }}
        />
      ) : (
        <div className="rounded-lg border border-[#1e2436] bg-[#121622] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#0e111a] text-slate-400 uppercase tracking-wider font-semibold border-b border-[#1e2436]">
                <tr>
                  <th className="px-4 py-3">Incident</th>
                  <th className="px-4 py-3">Severity</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Project</th>
                  <th className="px-4 py-3">Assigned Agent</th>
                  <th className="px-4 py-3">Detected</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e2436]/60 text-slate-300">
                {filteredIncidents.map((inc) => (
                  <tr
                    key={inc.id}
                    className={`hover:bg-[#181d2c]/60 transition-colors cursor-pointer ${
                      selectedIncident?.id === inc.id ? 'bg-[#1a2030]/80' : ''
                    }`}
                    onClick={() => setSelectedIncident(inc)}
                  >
                    <td className="px-4 py-3.5">
                      <div className="flex flex-col">
                        <span className="font-semibold text-white">{inc.id}</span>
                        <span className="text-slate-400 truncate max-w-sm">{inc.title}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <SeverityBadge severity={inc.severity} />
                    </td>
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <StatusBadge status={inc.status} />
                    </td>
                    <td className="px-4 py-3.5 whitespace-nowrap text-slate-400">
                      {inc.project}
                    </td>
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded text-[11px] bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                        {inc.assignedAgent}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 whitespace-nowrap text-slate-400">
                      {inc.detectedAt}
                    </td>
                    <td className="px-4 py-3.5 text-right whitespace-nowrap">
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-xs h-7 border-[#29344e] text-slate-300 hover:text-white"
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelectedIncident(inc)
                        }}
                      >
                        Inspect
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Incident Detail Drawer / Panel (when an incident is selected) */}
      {selectedIncident && (
        <div className="rounded-lg border border-indigo-500/30 bg-[#121622] p-5 shadow-lg relative animate-in fade-in duration-200">
          <button
            onClick={() => setSelectedIncident(null)}
            className="absolute top-4 right-4 p-1 rounded-md text-slate-400 hover:text-white hover:bg-[#1e2436]"
            aria-label="Close details"
          >
            <X className="w-4 h-4" />
          </button>

          <div className="flex flex-wrap items-center gap-2 mb-2">
            <span className="text-sm font-bold text-white font-mono">{selectedIncident.id}</span>
            <SeverityBadge severity={selectedIncident.severity} />
            <StatusBadge status={selectedIncident.status} />
          </div>

          <h3 className="text-lg font-semibold text-white">{selectedIncident.title}</h3>
          <p className="mt-1 text-sm text-slate-300">{selectedIncident.summary}</p>

          <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            <div className="p-3 rounded bg-[#0c0e15] border border-[#1e2436]">
              <span className="text-[11px] text-slate-400 block mb-1">Affected Project</span>
              <span className="text-white font-medium">{selectedIncident.project}</span>
            </div>
            <div className="p-3 rounded bg-[#0c0e15] border border-[#1e2436]">
              <span className="text-[11px] text-slate-400 block mb-1">Assigned AI Agent</span>
              <span className="text-indigo-400 font-medium flex items-center gap-1">
                <Sparkles className="w-3 h-3" />
                {selectedIncident.assignedAgent}
              </span>
            </div>
            <div className="p-3 rounded bg-[#0c0e15] border border-[#1e2436]">
              <span className="text-[11px] text-slate-400 block mb-1">Time Elapsed</span>
              <span className="text-white font-medium">{selectedIncident.detectedAt}</span>
            </div>
          </div>

          {selectedIncident.rootCauseCandidate && (
            <div className="mt-4 p-3 rounded bg-amber-500/10 border border-amber-500/20 text-xs">
              <span className="font-semibold text-amber-300 block mb-0.5">
                Root Cause Hypothesis (AI Assessment):
              </span>
              <p className="text-slate-300">{selectedIncident.rootCauseCandidate}</p>
            </div>
          )}

          <div className="mt-4 flex items-center justify-between pt-3 border-t border-[#1e2436]">
            <span className="text-xs text-slate-400">
              Services impacted: {selectedIncident.affectedServices.join(', ')}
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="text-xs h-8 border-[#29344e] text-slate-300 hover:text-white"
                onClick={() => setSelectedIncident(null)}
              >
                Dismiss
              </Button>
              <Button
                size="sm"
                className="text-xs h-8 bg-indigo-600 hover:bg-indigo-500 text-white gap-1.5"
                onClick={() => {
                  alert(`Dispatched action for ${selectedIncident.id} (Simulation mode)`)
                }}
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                Authorize Agent Fix
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
