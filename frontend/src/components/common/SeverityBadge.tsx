import type { IncidentSeverity } from '@/types'

interface SeverityBadgeProps {
  severity: IncidentSeverity
  className?: string
}

export function SeverityBadge({ severity, className = '' }: SeverityBadgeProps) {
  const styles: Record<IncidentSeverity, { bg: string; text: string; border: string; dot: string }> = {
    critical: {
      bg: 'bg-rose-500/10',
      text: 'text-rose-400',
      border: 'border-rose-500/25',
      dot: 'bg-rose-400 animate-pulse',
    },
    high: {
      bg: 'bg-amber-500/10',
      text: 'text-amber-400',
      border: 'border-amber-500/25',
      dot: 'bg-amber-400',
    },
    medium: {
      bg: 'bg-cyan-500/10',
      text: 'text-cyan-400',
      border: 'border-cyan-500/25',
      dot: 'bg-cyan-400',
    },
    low: {
      bg: 'bg-slate-500/10',
      text: 'text-slate-400',
      border: 'border-slate-500/25',
      dot: 'bg-slate-400',
    },
  }

  const current = styles[severity] || styles.low
  const label = severity.charAt(0).toUpperCase() + severity.slice(1)

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium border ${current.bg} ${current.text} ${current.border} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${current.dot}`} />
      {label}
    </span>
  )
}

