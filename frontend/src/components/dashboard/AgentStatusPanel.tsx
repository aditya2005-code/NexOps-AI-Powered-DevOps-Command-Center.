import { Bot, Sparkles } from 'lucide-react'
import { StatusBadge } from '@/components/common/StatusBadge'
import type { Agent } from '@/types'

interface AgentStatusPanelProps {
  agents: Agent[]
}

export function AgentStatusPanel({ agents }: AgentStatusPanelProps) {
  return (
    <div className="rounded-lg border border-[#1e2436] bg-[#121622] p-5">
      <div className="flex items-center justify-between pb-3 border-b border-[#1e2436]">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-white">AI Agent Swarm</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              LangGraph-orchestrated operational specialists (Simulation)
            </p>
          </div>
        </div>
        <span className="flex items-center gap-1 text-[11px] font-medium text-cyan-300 bg-cyan-500/10 border border-cyan-500/20 px-2 py-0.5 rounded">
          <Sparkles className="w-3 h-3" />
          5 Agents Ready
        </span>
      </div>

      <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {agents.map((agent) => (
          <div
            key={agent.id}
            className="flex flex-col justify-between p-3.5 rounded-md border border-[#1e2436] bg-[#0f121b] hover:border-[#2a334d] transition-all"
          >
            <div>
              <div className="flex items-start justify-between gap-1 mb-2">
                <span className="text-xs font-bold text-white tracking-tight">{agent.name}</span>
                <StatusBadge status={agent.status} />
              </div>
              <p className="text-[11px] font-medium text-indigo-400 mb-1.5">{agent.role}</p>
              <p className="text-[11px] text-slate-400 leading-normal line-clamp-2">
                {agent.description}
              </p>
            </div>

            <div className="mt-3 pt-2 border-t border-[#1e2436]/70 flex items-center justify-between text-[11px] text-slate-400">
              <span>Active {agent.lastActivity}</span>
              {agent.currentTask && (
                <span className="w-2 h-2 rounded-full bg-indigo-400" title={agent.currentTask} />
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

