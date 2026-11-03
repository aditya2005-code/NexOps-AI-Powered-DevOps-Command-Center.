import {
  AlertTriangle,
  FileSearch,
  GitPullRequest,
  ShieldCheck,
  CheckCircle2,
} from 'lucide-react'
import type { ActivityEvent, ActivityEventType } from '@/types'

const EVENT_ICONS: Record<ActivityEventType, React.ElementType> = {
  incident_detected: AlertTriangle,
  log_analyzed: FileSearch,
  root_cause_found: FileSearch,
  patch_generated: GitPullRequest,
  approval_requested: ShieldCheck,
  test_completed: CheckCircle2,
}

interface OperationsActivityProps {
  activities: ActivityEvent[]
}

export function OperationsActivity({ activities }: OperationsActivityProps) {
  return (
    <div className="rounded-lg border border-[#1e2436] bg-[#121622] p-5">
      <div className="flex items-center justify-between pb-3 border-b border-[#1e2436]">
        <div>
          <h2 className="text-base font-semibold text-white">Operations Activity</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time feed of multi-agent coordination and audit triggers
          </p>
        </div>
        <span className="text-[11px] font-medium text-slate-400 bg-[#1a1f2e] px-2 py-0.5 rounded border border-[#273046]">
          Live stream
        </span>
      </div>

      <div className="mt-4 space-y-4">
        {activities.map((act) => {
          const Icon = EVENT_ICONS[act.type] || AlertTriangle
          return (
            <div key={act.id} className="flex items-start gap-3 text-xs">
              <div className="p-1.5 rounded bg-[#1a2030] border border-[#26314a] text-indigo-400 shrink-0 mt-0.5">
                <Icon className="w-3.5 h-3.5" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold text-slate-200 truncate">{act.title}</span>
                  <span className="text-[11px] text-slate-500 whitespace-nowrap">{act.timestamp}</span>
                </div>
                <p className="mt-0.5 text-slate-400 leading-relaxed text-xs">{act.description}</p>
                <div className="mt-1.5 flex items-center gap-2">
                  <span className="text-[11px] font-medium text-indigo-300 bg-indigo-500/10 px-1.5 py-0.5 rounded border border-indigo-500/20">
                    {act.agentName}
                  </span>
                  {act.incidentId && (
                    <span className="text-[11px] font-mono text-slate-400">
                      {act.incidentId}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

