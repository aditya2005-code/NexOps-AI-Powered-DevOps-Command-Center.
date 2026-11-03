interface StatusBadgeProps {
  status: string
  className?: string
}

export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const normalized = status.toLowerCase().replace(/[\s-]/g, '_')

  const styles: Record<string, { bg: string; text: string; border: string; label: string }> = {
    open: {
      bg: 'bg-amber-500/10',
      text: 'text-amber-300',
      border: 'border-amber-500/20',
      label: 'Open',
    },
    investigating: {
      bg: 'bg-indigo-500/15',
      text: 'text-indigo-300',
      border: 'border-indigo-500/30',
      label: 'Investigating',
    },
    awaiting_approval: {
      bg: 'bg-purple-500/15',
      text: 'text-purple-300',
      border: 'border-purple-500/30',
      label: 'Awaiting Approval',
    },
    resolved: {
      bg: 'bg-emerald-500/10',
      text: 'text-emerald-400',
      border: 'border-emerald-500/20',
      label: 'Resolved',
    },
    working: {
      bg: 'bg-cyan-500/15',
      text: 'text-cyan-300',
      border: 'border-cyan-500/30',
      label: 'Working',
    },
    idle: {
      bg: 'bg-slate-500/10',
      text: 'text-slate-400',
      border: 'border-slate-500/20',
      label: 'Idle',
    },
    waiting_for_approval: {
      bg: 'bg-purple-500/15',
      text: 'text-purple-300',
      border: 'border-purple-500/30',
      label: 'Waiting for Approval',
    },
    offline: {
      bg: 'bg-zinc-600/10',
      text: 'text-zinc-400',
      border: 'border-zinc-600/20',
      label: 'Offline',
    },
    healthy: {
      bg: 'bg-emerald-500/10',
      text: 'text-emerald-400',
      border: 'border-emerald-500/20',
      label: 'Healthy',
    },
    degraded: {
      bg: 'bg-amber-500/10',
      text: 'text-amber-300',
      border: 'border-amber-500/20',
      label: 'Degraded',
    },
    active: {
      bg: 'bg-emerald-500/10',
      text: 'text-emerald-400',
      border: 'border-emerald-500/20',
      label: 'Active',
    },
    success: {
      bg: 'bg-emerald-500/10',
      text: 'text-emerald-400',
      border: 'border-emerald-500/20',
      label: 'Success',
    },
    failure: {
      bg: 'bg-rose-500/10',
      text: 'text-rose-400',
      border: 'border-rose-500/20',
      label: 'Failure',
    },
    pending: {
      bg: 'bg-amber-500/10',
      text: 'text-amber-300',
      border: 'border-amber-500/20',
      label: 'Pending',
    },
  }

  const current = styles[normalized] || {
    bg: 'bg-slate-500/10',
    text: 'text-slate-300',
    border: 'border-slate-500/20',
    label: status,
  }

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${current.bg} ${current.text} ${current.border} ${className}`}
    >
      {current.label}
    </span>
  )
}

