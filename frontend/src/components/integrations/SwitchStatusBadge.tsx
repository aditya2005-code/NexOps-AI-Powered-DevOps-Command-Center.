import { AlertCircle, CheckCircle2, Clock, Radio, RefreshCw, XCircle } from 'lucide-react'
import type { SwitchConnectionState } from '@/types/switch'

interface SwitchStatusBadgeProps {
  state?: SwitchConnectionState
  connected?: boolean
  isBackendError?: boolean
  isLoading?: boolean
  className?: string
  showIcon?: boolean
}

export function SwitchStatusBadge({
  state,
  connected,
  isBackendError = false,
  isLoading = false,
  className = '',
  showIcon = true,
}: SwitchStatusBadgeProps) {
  if (isBackendError) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border bg-rose-500/10 text-rose-300 border-rose-500/20 ${className}`}
      >
        {showIcon && <XCircle className="w-3.5 h-3.5 text-rose-400" />}
        <span>Backend Offline</span>
      </span>
    )
  }

  if (isLoading) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border bg-indigo-500/10 text-indigo-300 border-indigo-500/20 ${className}`}
      >
        {showIcon && <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-400" />}
        <span>Checking Switch...</span>
      </span>
    )
  }

  if (connected || state === 'connected') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border bg-emerald-500/10 text-emerald-300 border-emerald-500/20 ${className}`}
      >
        {showIcon && (
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
        )}
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
        <span>Switch Connected</span>
      </span>
    )
  }

  if (state === 'connecting') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border bg-amber-500/10 text-amber-300 border-amber-500/20 ${className}`}
      >
        {showIcon && <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-400" />}
        <span>Connecting to Switch...</span>
      </span>
    )
  }

  if (state === 'disconnected') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border bg-amber-500/10 text-amber-300 border-amber-500/20 ${className}`}
      >
        {showIcon && <Clock className="w-3.5 h-3.5 text-amber-400" />}
        <span>Switch Disconnected</span>
      </span>
    )
  }

  if (state === 'unconfigured') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border bg-amber-500/10 text-amber-300 border-amber-500/20 ${className}`}
      >
        {showIcon && <AlertCircle className="w-3.5 h-3.5 text-amber-400" />}
        <span>Credentials Missing</span>
      </span>
    )
  }

  if (state === 'error') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border bg-rose-500/10 text-rose-300 border-rose-500/20 ${className}`}
      >
        {showIcon && <AlertCircle className="w-3.5 h-3.5 text-rose-400" />}
        <span>Switch Error</span>
      </span>
    )
  }

  // default / disabled
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border bg-slate-500/10 text-slate-400 border-slate-500/20 ${className}`}
    >
      {showIcon && <Radio className="w-3.5 h-3.5 text-slate-400" />}
      <span>Switch Disabled</span>
    </span>
  )
}
