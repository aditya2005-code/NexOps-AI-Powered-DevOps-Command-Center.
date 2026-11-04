import { useState } from 'react'
import { Search, ShieldAlert, X, Sparkles, CheckCircle2, Database, Radio, RefreshCw } from 'lucide-react'
import { PageHeader } from '@/components/common/PageHeader'
import { SeverityBadge } from '@/components/common/SeverityBadge'
import { StatusBadge } from '@/components/common/StatusBadge'
import { EmptyState } from '@/components/common/EmptyState'
import { Button } from '@/components/ui/button'
import { DEMO_INCIDENTS } from '@/constants/mockData'
import { useIncidents } from '@/hooks/useIncidents'
import type { BackendIncident } from '@/types/incident'
import type { Incident } from '@/types'

export function IncidentsPage() {
  const [search, setSearch] = useState('')
  const [severityFilter, setSeverityFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [useLiveBackend, setUseLiveBackend] = useState<boolean>(true)
  const [selectedLiveIncident, setSelectedLiveIncident] = useState<BackendIncident | null>(null)
  const [selectedDemoIncident, setSelectedDemoIncident] = useState<Incident | null>(null)

  const { data: liveData, isLoading, isError, refetch, isFetching } = useIncidents()

  // Determine active dataset
  const liveIncidents = liveData || []
  const hasLiveRecords = liveIncidents.length > 0
  const isShowingLive = useLiveBackend && hasLiveRecords

  // Filtering for live incidents
  const filteredLive = liveIncidents.filter((inc) => {
    const matchesSearch =
      inc.title.toLowerCase().includes(search.toLowerCase()) ||
      inc.id.toLowerCase().includes(search.toLowerCase()) ||
      (inc.project_name && inc.project_name.toLowerCase().includes(search.toLowerCase())) ||
      inc.source.toLowerCase().includes(search.toLowerCase())
    const matchesSeverity = severityFilter === 'all' || inc.severity.toLowerCase() === severityFilter.toLowerCase()
    const matchesStatus = statusFilter === 'all' || inc.status.toLowerCase() === statusFilter.toLowerCase()
    return matchesSearch && matchesSeverity && matchesStatus
  })

  // Filtering for demo incidents
  const filteredDemo = DEMO_INCIDENTS.filter((inc) => {
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
        subtitle="Monitored DevOps incidents persisted in PostgreSQL and ingested via Switch Agent Bridge or telemetry."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {/* Live vs Demo Toggle */}
            <div className="flex rounded-md border border-[#1e2436] bg-[#121622] p-0.5 text-xs">
              <button
                onClick={() => setUseLiveBackend(true)}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded transition-colors ${
                  useLiveBackend
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Database className="w-3.5 h-3.5" />
                Live Data ({liveIncidents.length})
              </button>
              <button
                onClick={() => setUseLiveBackend(false)}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded transition-colors ${
                  !useLiveBackend
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                Simulation ({DEMO_INCIDENTS.length})
              </button>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              className="h-8 border-[#1e2436] bg-[#121622] text-xs text-slate-300 hover:text-white"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} />
            </Button>
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

      {/* Main Content Area */}
      {isLoading ? (
        <div className="rounded-lg border border-[#1e2436] bg-[#121622] p-12 text-center text-xs text-slate-400">
          <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-indigo-400" />
          Loading incidents from backend...
        </div>
      ) : isError && useLiveBackend ? (
        <div className="rounded-lg border border-rose-500/20 bg-rose-500/10 p-6 text-xs text-rose-300 text-center space-y-2">
          <p className="font-semibold text-rose-200">Failed to connect to Incident API</p>
          <p className="text-slate-400">
            Make sure the FastAPI backend is running at <code>http://localhost:8000</code>.
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setUseLiveBackend(false)}
            className="mt-2 text-xs border-[#1e2436] text-white"
          >
            Switch to Simulated Data
          </Button>
        </div>
      ) : useLiveBackend && liveIncidents.length === 0 ? (
        <div className="rounded-lg border border-[#1e2436] bg-[#121622] p-12 text-center space-y-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-500/10 border border-indigo-500/20 mx-auto text-indigo-400">
            <Database className="w-6 h-6" />
          </div>
          <div className="max-w-md mx-auto space-y-1">
            <h3 className="text-base font-semibold text-white">PostgreSQL Incident Queue is Clean</h3>
            <p className="text-xs text-slate-400">
              No live incidents have been recorded in the database yet. Send a message to any mapped
              Switch room (e.g. <code>ops-payments</code>) to trigger automated intake.
            </p>
          </div>
          <div className="flex items-center justify-center gap-3 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setUseLiveBackend(false)}
              className="text-xs border-[#1e2436] text-slate-300 hover:text-white"
            >
              <Sparkles className="w-3.5 h-3.5 mr-1 text-indigo-400" />
              Preview Simulation Model
            </Button>
          </div>
        </div>
      ) : isShowingLive ? (
        /* Render Live Incidents Table */
        filteredLive.length === 0 ? (
          <EmptyState
            title="No matching live incidents"
            description="Adjust your search query or filters."
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
                    <th className="px-4 py-3">Source</th>
                    <th className="px-4 py-3">Detected</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1e2436]/60 text-slate-300">
                  {filteredLive.map((inc) => (
                    <tr
                      key={inc.id}
                      className={`hover:bg-[#181d2c]/60 transition-colors cursor-pointer ${
                        selectedLiveIncident?.id === inc.id ? 'bg-[#1a2030]/80' : ''
                      }`}
                      onClick={() => setSelectedLiveIncident(inc)}
                    >
                      <td className="px-4 py-3.5">
                        <div className="flex flex-col">
                          <span className="font-mono text-slate-400 text-[11px]">{inc.id.slice(0, 8)}...</span>
                          <span className="font-semibold text-white truncate max-w-sm">{inc.title}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <SeverityBadge severity={inc.severity.toLowerCase()} />
                      </td>
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <StatusBadge status={inc.status.toLowerCase()} />
                      </td>
                      <td className="px-4 py-3.5 whitespace-nowrap text-slate-400">
                        {inc.project_name || inc.project_id.slice(0, 8)}
                      </td>
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 inline-flex items-center gap-1">
                          {inc.source === 'switch' && <Radio className="w-3 h-3 text-cyan-400" />}
                          {inc.source}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 whitespace-nowrap text-slate-400 font-mono text-[11px]">
                        {new Date(inc.detected_at).toLocaleTimeString()}
                      </td>
                      <td className="px-4 py-3.5 text-right whitespace-nowrap">
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-xs h-7 border-[#29344e] text-slate-300 hover:text-white"
                          onClick={(e) => {
                            e.stopPropagation()
                            setSelectedLiveIncident(inc)
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
        )
      ) : (
        /* Render Demo Simulation Table */
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
                {filteredDemo.map((inc) => (
                  <tr
                    key={inc.id}
                    className={`hover:bg-[#181d2c]/60 transition-colors cursor-pointer ${
                      selectedDemoIncident?.id === inc.id ? 'bg-[#1a2030]/80' : ''
                    }`}
                    onClick={() => setSelectedDemoIncident(inc)}
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
                          setSelectedDemoIncident(inc)
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

      {/* Live Incident Detail Drawer */}
      {selectedLiveIncident && (
        <div className="rounded-lg border border-indigo-500/30 bg-[#121622] p-5 shadow-lg relative animate-in fade-in duration-200 space-y-4">
          <button
            onClick={() => setSelectedLiveIncident(null)}
            className="absolute top-4 right-4 p-1 rounded-md text-slate-400 hover:text-white hover:bg-[#1e2436]"
            aria-label="Close details"
          >
            <X className="w-4 h-4" />
          </button>

          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-mono font-bold text-white bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/30">
              {selectedLiveIncident.id}
            </span>
            <SeverityBadge severity={selectedLiveIncident.severity.toLowerCase()} />
            <StatusBadge status={selectedLiveIncident.status.toLowerCase()} />
            <span className="text-[11px] font-mono text-slate-400">
              Source: {selectedLiveIncident.source} ({selectedLiveIncident.source_id || 'manual'})
            </span>
          </div>

          <h3 className="text-base font-semibold text-white">{selectedLiveIncident.title}</h3>
          {selectedLiveIncident.description && (
            <p className="text-xs text-slate-300 whitespace-pre-wrap rounded-md bg-[#0c0e15] p-3 border border-[#1e2436]">
              {selectedLiveIncident.description}
            </p>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div className="p-3 rounded bg-[#0c0e15] border border-[#1e2436]">
              <span className="text-[11px] text-slate-400 block mb-1">Target Project</span>
              <span className="text-white font-medium">
                {selectedLiveIncident.project_name || selectedLiveIncident.project_id}
              </span>
            </div>
            <div className="p-3 rounded bg-[#0c0e15] border border-[#1e2436]">
              <span className="text-[11px] text-slate-400 block mb-1">Detected At</span>
              <span className="text-slate-200 font-mono">
                {new Date(selectedLiveIncident.detected_at).toLocaleString()}
              </span>
            </div>
            <div className="p-3 rounded bg-[#0c0e15] border border-[#1e2436]">
              <span className="text-[11px] text-slate-400 block mb-1">Persistence State</span>
              <span className="text-emerald-400 font-medium flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Neon PostgreSQL
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Demo Incident Detail Drawer */}
      {selectedDemoIncident && !selectedLiveIncident && (
        <div className="rounded-lg border border-indigo-500/30 bg-[#121622] p-5 shadow-lg relative animate-in fade-in duration-200">
          <button
            onClick={() => setSelectedDemoIncident(null)}
            className="absolute top-4 right-4 p-1 rounded-md text-slate-400 hover:text-white hover:bg-[#1e2436]"
            aria-label="Close details"
          >
            <X className="w-4 h-4" />
          </button>

          <div className="flex flex-wrap items-center gap-2 mb-2">
            <span className="text-sm font-bold text-white font-mono">{selectedDemoIncident.id}</span>
            <SeverityBadge severity={selectedDemoIncident.severity} />
            <StatusBadge status={selectedDemoIncident.status} />
          </div>

          <h3 className="text-lg font-semibold text-white">{selectedDemoIncident.title}</h3>
          <p className="mt-1 text-sm text-slate-300">{selectedDemoIncident.summary}</p>

          <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            <div className="p-3 rounded bg-[#0c0e15] border border-[#1e2436]">
              <span className="text-[11px] text-slate-400 block mb-1">Affected Project</span>
              <span className="text-white font-medium">{selectedDemoIncident.project}</span>
            </div>
            <div className="p-3 rounded bg-[#0c0e15] border border-[#1e2436]">
              <span className="text-[11px] text-slate-400 block mb-1">Assigned AI Agent</span>
              <span className="text-indigo-400 font-medium flex items-center gap-1">
                <Sparkles className="w-3 h-3" />
                {selectedDemoIncident.assignedAgent}
              </span>
            </div>
            <div className="p-3 rounded bg-[#0c0e15] border border-[#1e2436]">
              <span className="text-[11px] text-slate-400 block mb-1">Time Elapsed</span>
              <span className="text-white font-medium">{selectedDemoIncident.detectedAt}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
