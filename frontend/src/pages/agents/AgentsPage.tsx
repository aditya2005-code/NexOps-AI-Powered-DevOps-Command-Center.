import { Bot, Sparkles, CheckCircle2, Shield, Wrench, FileSearch, Terminal } from 'lucide-react'
import { PageHeader } from '@/components/common/PageHeader'
import { StatusBadge } from '@/components/common/StatusBadge'
import { DEMO_AGENTS } from '@/constants/mockData'

const AGENT_ICONS: Record<string, React.ElementType> = {
  'Incident Manager': Shield,
  'Log Analyst': FileSearch,
  'Code Investigator': Terminal,
  'Fix Agent': Wrench,
  'Testing Agent': CheckCircle2,
}

export function AgentsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Agent Swarm"
        subtitle="Specialized autonomous DevOps agents coordinated via LangGraph state machines."
        badge={
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
            Multi-Agent Architecture
          </span>
        }
      />

      {/* Architecture Disclaimer */}
      <div className="rounded-lg border border-cyan-500/20 bg-cyan-500/5 p-4 text-xs text-cyan-200">
        <div className="flex items-center gap-2 font-semibold text-cyan-300 mb-1">
          <Sparkles className="w-4 h-4 text-cyan-400" />
          <span>LangGraph & LangChain Coordinated System</span>
        </div>
        <p className="text-slate-300 leading-relaxed">
          These five agents operate within a unified LangGraph state workflow rather than independent bots.
          When an anomaly is flagged, the Incident Manager routes state through log analysis, AST code investigation,
          patch synthesis, and sandbox testing with human-in-the-loop checkpoints.
        </p>
      </div>

      {/* Five Agent Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {DEMO_AGENTS.map((agent) => {
          const Icon = AGENT_ICONS[agent.name] || Bot
          return (
            <div
              key={agent.id}
              className="flex flex-col justify-between rounded-lg border border-[#1e2436] bg-[#121622] p-5 hover:border-indigo-500/40 transition-colors shadow-sm"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-white">{agent.name}</h3>
                      <p className="text-xs text-indigo-400 font-medium">{agent.role}</p>
                    </div>
                  </div>
                  <StatusBadge status={agent.status} />
                </div>

                <p className="text-xs text-slate-300 leading-relaxed mb-4">
                  {agent.description}
                </p>

                {/* Capabilities Tags */}
                <div className="space-y-1.5 border-t border-[#1e2436] pt-3">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                    Core Capabilities
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {agent.capabilities.map((cap) => (
                      <span
                        key={cap}
                        className="text-[11px] font-medium text-slate-300 bg-[#0c0e15] border border-[#1e2436] px-2 py-0.5 rounded"
                      >
                        {cap}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Task / Activity Footer */}
              <div className="mt-5 pt-3 border-t border-[#1e2436] text-[11px] text-slate-400">
                <span className="block font-medium text-slate-400 mb-0.5">Current Task:</span>
                <span className="text-slate-200 font-mono text-[11px] block truncate">
                  {agent.currentTask || 'Idle on standby'}
                </span>
                <span className="text-[10px] text-slate-500 block mt-1">
                  Last activity: {agent.lastActivity}
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

