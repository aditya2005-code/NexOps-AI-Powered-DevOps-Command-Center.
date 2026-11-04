import { ExternalLink, ShieldAlert, MessageSquare, ArrowRight } from 'lucide-react'
import { PageHeader } from '@/components/common/PageHeader'
import { SwitchOverviewCard } from '@/components/integrations/SwitchOverviewCard'
import { useIncidents } from '@/hooks/useIncidents'
import { StatusBadge } from '@/components/common/StatusBadge'
import { SeverityBadge } from '@/components/common/SeverityBadge'
import { Link } from 'react-router-dom'

export function SwitchIntegrationPage() {
  const { data: incidents, isLoading: incidentsLoading } = useIncidents()
  const switchIncidents = (incidents || []).filter((i) => i.source === 'switch')

  return (
    <div className="space-y-6">
      <PageHeader
        title="Switch Collaboration Bridge"
        subtitle="Real-time Agent Bridge connection to the official Switch platform for collaborative DevOps incident intake."
        actions={
          <div className="flex items-center gap-2">
            <a
              href="https://github.com/sandbox-quantum/switch"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-[#1e2436] bg-[#121622] text-xs font-medium text-slate-300 hover:text-white transition-colors"
            >
              <span>GitHub</span>
              <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
            </a>
          </div>
        }
      />

      {/* Main Switch Health & Status Card */}
      <SwitchOverviewCard />

      {/* Bidirectional Intake Flow Diagram */}
      <div className="rounded-xl border border-[#1e2436] bg-[#121622] p-5 shadow-sm space-y-4">
        <h4 className="text-sm font-semibold text-white flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-cyan-400" />
          Bidirectional Messaging Architecture
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="rounded-lg border border-[#1e2436] bg-[#0c0e15] p-3.5 space-y-2">
            <span className="font-semibold text-indigo-300 flex items-center gap-1.5">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-500/20 text-indigo-400 text-[11px]">
                1
              </span>
              Inbound Incident Intake
            </span>
            <p className="text-slate-400 leading-relaxed">
              When a team member reports an anomaly in a mapped Switch room (e.g. <code>ops-payments</code>),
              the Switch Agent Bridge streams a WebSocket event frame to NexOps. The intake service enforces
              room mapping, derives a collision-resistant composite idempotency key, persists the incident to PostgreSQL,
              and stages an audit log entry.
            </p>
          </div>

          <div className="rounded-lg border border-[#1e2436] bg-[#0c0e15] p-3.5 space-y-2">
            <span className="font-semibold text-emerald-300 flex items-center gap-1.5">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 text-[11px]">
                2
              </span>
              Post-Commit Room Acknowledgement
            </span>
            <p className="text-slate-400 leading-relaxed">
              Once database persistence succeeds, an outbound acknowledgement is dispatched to Switch Core
              at <code>/ops</code> via <code>send_message</code>. The message thread in Switch receives the
              created Incident ID and project status. Delivery failures do not compromise the persisted incident.
            </p>
          </div>
        </div>
      </div>

      {/* Recent Incidents Ingested via Switch */}
      <div className="rounded-xl border border-[#1e2436] bg-[#121622] p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[#1e2436]">
          <div>
            <h4 className="text-sm font-semibold text-white flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-amber-400" />
              Incidents Ingested via Switch
            </h4>
            <p className="text-xs text-slate-400 mt-0.5">
              Incidents created automatically from human chat messages in mapped Switch rooms
            </p>
          </div>
          <Link
            to="/incidents"
            className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium"
          >
            View All Incidents <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {incidentsLoading ? (
          <div className="py-8 text-center text-xs text-slate-400">Loading ingested incidents...</div>
        ) : switchIncidents.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-400 space-y-1">
            <p className="font-medium text-slate-300">No Switch incidents recorded yet</p>
            <p className="text-slate-400 text-[11px]">
              When a message is sent in a configured Switch room, it will appear here automatically.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[#1e2436] text-slate-400">
                  <th className="py-2.5 px-3 font-medium">Incident ID</th>
                  <th className="py-2.5 px-3 font-medium">Title</th>
                  <th className="py-2.5 px-3 font-medium">Project</th>
                  <th className="py-2.5 px-3 font-medium">Severity</th>
                  <th className="py-2.5 px-3 font-medium">Status</th>
                  <th className="py-2.5 px-3 font-medium">Source Key</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e2436]/60">
                {switchIncidents.map((inc) => (
                  <tr key={inc.id} className="hover:bg-[#161c2c]">
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-300">{inc.id.slice(0, 8)}...</td>
                    <td className="py-2.5 px-3 font-medium text-white">{inc.title}</td>
                    <td className="py-2.5 px-3 text-slate-300">{inc.project_name || inc.project_id.slice(0, 8)}</td>
                    <td className="py-2.5 px-3">
                      <SeverityBadge severity={inc.severity.toLowerCase()} />
                    </td>
                    <td className="py-2.5 px-3">
                      <StatusBadge status={inc.status.toLowerCase()} />
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-400">
                      {inc.source_id || 'switch'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
