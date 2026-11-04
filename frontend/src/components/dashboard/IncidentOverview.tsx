import { Link } from 'react-router-dom'
import { ArrowUpRight, Database, Radio, Sparkles } from 'lucide-react'
import { SeverityBadge } from '@/components/common/SeverityBadge'
import { StatusBadge } from '@/components/common/StatusBadge'
import type { Incident } from '@/types'
import type { BackendIncident } from '@/types/incident'

interface IncidentOverviewProps {
  incidents: Incident[]
  liveIncidents?: BackendIncident[]
  isLiveLoading?: boolean
}

export function IncidentOverview({
  incidents,
  liveIncidents = [],
  isLiveLoading = false,
}: IncidentOverviewProps) {
  const hasLiveIncidents = liveIncidents.length > 0

  return (
    <div className="rounded-lg border border-[#1e2436] bg-[#121622] overflow-hidden">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 border-b border-[#1e2436] gap-2">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-white">Active Incident Queue</h2>
            {hasLiveIncidents ? (
              <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                <Database className="w-3 h-3" /> Live Backend Data ({liveIncidents.length})
              </span>
            ) : (
              <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 flex items-center gap-1">
                <Sparkles className="w-3 h-3" /> Simulation Mode
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            {hasLiveIncidents
              ? 'Real-time incident records queried directly from the NexOps backend API'
              : 'Operational anomalies prioritized by severity (Simulated telemetry model)'}
          </p>
        </div>
        <Link
          to="/incidents"
          className="inline-flex items-center gap-1 text-xs font-medium text-indigo-400 hover:text-indigo-300 transition-colors"
        >
          View all incidents
          <ArrowUpRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-[#0e111a] text-slate-400 uppercase tracking-wider font-semibold border-b border-[#1e2436]">
            <tr>
              <th className="px-4 py-3">ID & Title</th>
              <th className="px-4 py-3">Severity</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 hidden md:table-cell">Project</th>
              <th className="px-4 py-3 hidden sm:table-cell">Source</th>
              <th className="px-4 py-3 text-right">Detected</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1e2436]/60 text-slate-300">
            {isLiveLoading ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                  Loading incidents from backend...
                </td>
              </tr>
            ) : hasLiveIncidents ? (
              liveIncidents.slice(0, 5).map((inc) => (
                <tr key={inc.id} className="hover:bg-[#181d2c]/50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex flex-col">
                      <span className="font-mono text-slate-300 text-xs">{inc.id.slice(0, 8)}...</span>
                      <span className="font-semibold text-white truncate max-w-[240px] sm:max-w-xs">
                        {inc.title}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <SeverityBadge severity={inc.severity.toLowerCase()} />
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <StatusBadge status={inc.status.toLowerCase()} />
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell whitespace-nowrap text-slate-400">
                    {inc.project_name || inc.project_id.slice(0, 8)}
                  </td>
                  <td className="px-4 py-3 hidden sm:table-cell whitespace-nowrap">
                    <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 inline-flex items-center gap-1">
                      {inc.source === 'switch' && <Radio className="w-3 h-3 text-cyan-400" />}
                      {inc.source}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-slate-400 whitespace-nowrap">
                    {new Date(inc.detected_at).toLocaleTimeString()}
                  </td>
                </tr>
              ))
            ) : (
              incidents.slice(0, 4).map((inc) => (
                <tr key={inc.id} className="hover:bg-[#181d2c]/50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex flex-col">
                      <span className="font-semibold text-white">{inc.id}</span>
                      <span className="text-slate-400 text-xs truncate max-w-[240px] sm:max-w-xs">
                        {inc.title}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <SeverityBadge severity={inc.severity} />
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <StatusBadge status={inc.status} />
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell whitespace-nowrap text-slate-400">
                    {inc.project}
                  </td>
                  <td className="px-4 py-3 hidden sm:table-cell whitespace-nowrap">
                    <span className="px-2 py-0.5 rounded text-[11px] bg-slate-500/10 text-slate-400 border border-slate-500/20">
                      demo
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-slate-400 whitespace-nowrap">
                    {inc.detectedAt}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
