import { ArrowDownRight, ArrowUpRight, ShieldAlert, FolderGit2, Bot, CheckCircle2 } from 'lucide-react'
import type { MetricCardData } from '@/types'

const ICONS: Record<string, React.ElementType> = {
  'active-incidents': ShieldAlert,
  'projects-monitored': FolderGit2,
  'ai-agents-active': Bot,
  'successful-resolutions': CheckCircle2,
}

export function MetricCard({
  id,
  title,
  value,
  change,
  isPositive,
  indicator,
  description,
}: MetricCardData) {
  const Icon = ICONS[id] || ShieldAlert

  const indicatorStyles = {
    normal: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20',
    alert: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
    warning: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
    success: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  }

  return (
    <div className="relative rounded-lg border border-[#1e2436] bg-[#121622] p-5 shadow-sm hover:border-[#2d364f] transition-colors">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </span>
        <div className={`p-2 rounded-md border ${indicatorStyles[indicator]}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>

      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-3xl font-bold tracking-tight text-white">{value}</span>
      </div>

      <div className="mt-2 flex items-center gap-1.5 text-xs">
        <span
          className={`inline-flex items-center font-medium ${
            isPositive ? 'text-emerald-400' : 'text-rose-400'
          }`}
        >
          {isPositive ? (
            <ArrowUpRight className="w-3.5 h-3.5 mr-0.5" />
          ) : (
            <ArrowDownRight className="w-3.5 h-3.5 mr-0.5" />
          )}
          {change}
        </span>
      </div>

      <p className="mt-2 text-xs text-slate-400 leading-relaxed border-t border-[#1e2436]/60 pt-2">
        {description}
      </p>
    </div>
  )
}

