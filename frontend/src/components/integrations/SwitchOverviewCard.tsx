import { useState } from 'react'
import {
  Activity,
  AlertTriangle,
  Bot,
  Clock,
  ExternalLink,
  HelpCircle,
  Info,
  Key,
  Radio,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  XCircle,
} from 'lucide-react'
import { SwitchStatusBadge } from '@/components/integrations/SwitchStatusBadge'
import { useSwitchStatus } from '@/hooks/useSwitchStatus'
import { Button } from '@/components/ui/button'

export function SwitchOverviewCard() {
  const { data: status, isError, isLoading, refetch, isFetching } = useSwitchStatus()
  const [showConfigGuide, setShowConfigGuide] = useState(false)

  const CONFIG_ITEMS = [
    {
      key: 'SWITCH_ENABLED',
      required: true,
      description: 'Master toggle to enable or disable Switch background listener loop',
      example: 'true',
    },
    {
      key: 'SWITCH_CORE_URL',
      required: true,
      description: 'Base HTTP/HTTPS URL of official Switch Core service',
      example: 'http://localhost:8080 or https://switch.internal',
    },
    {
      key: 'SWITCH_API_KEY',
      required: true,
      description: 'Bearer authentication token for Switch Agent Bridge gateway',
      example: 'sk_live_*** (Server-side secret only)',
    },
    {
      key: 'SWITCH_AGENT_ID',
      required: true,
      description: 'Identity under which NexOps registers within Switch rooms',
      example: 'nexops-agent',
    },
    {
      key: 'SWITCH_ROOM_PROJECT_MAPPING',
      required: true,
      description: 'JSON or key-value map linking Switch room IDs to NexOps project names/UUIDs',
      example: '{"ops-payments": "Payments API", "devops-war-room": "Core Gateway"}',
    },
  ]

  return (
    <div className="space-y-6">
      {/* Primary Integration Health Card */}
      <div className="rounded-xl border border-[#1e2436] bg-[#121622] p-5 lg:p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-5 border-b border-[#1e2436]">
          <div className="flex items-center gap-3.5">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <Radio className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-semibold text-white">Switch Agent Bridge</h3>
                <SwitchStatusBadge
                  state={status?.state}
                  connected={status?.connected}
                  isBackendError={isError}
                  isLoading={isLoading}
                />
                {isFetching && !isLoading && (
                  <span className="text-[10px] text-slate-500 flex items-center gap-1">
                    <RefreshCw className="w-2.5 h-2.5 animate-spin" /> polling
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Official bidirectional collaboration gateway for real-time human and agent incident intake
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-end sm:self-auto">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              className="h-8 border-[#1e2436] bg-[#0c0e15] text-xs text-slate-300 hover:text-white hover:bg-[#1a2133] gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} />
              Poll Now
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowConfigGuide(!showConfigGuide)}
              className="h-8 border-[#1e2436] bg-[#0c0e15] text-xs text-indigo-300 hover:text-indigo-200 hover:bg-[#1a2133] gap-1.5"
            >
              <HelpCircle className="w-3.5 h-3.5" />
              {showConfigGuide ? 'Hide Guidance' : 'Setup Guide'}
            </Button>
          </div>
        </div>

        {/* Live Diagnostics Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-5">
          {/* 1. Connection State */}
          <div className="rounded-lg border border-[#1e2436] bg-[#0c0e15] p-3.5">
            <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-slate-400" />
              Lifecycle State
            </span>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-sm font-semibold capitalize text-white">
                {isError ? 'API Error' : isLoading ? 'Querying...' : status?.state || 'Unknown'}
              </span>
              {status?.connected && (
                <span className="text-[10px] text-emerald-400 font-medium">Active Loop</span>
              )}
            </div>
          </div>

          {/* 2. Registered Agent ID */}
          <div className="rounded-lg border border-[#1e2436] bg-[#0c0e15] p-3.5">
            <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1.5">
              <Bot className="w-3.5 h-3.5 text-indigo-400" />
              Bridge Agent ID
            </span>
            <div className="mt-2 font-mono text-xs text-slate-200 truncate">
              {isError
                ? 'Unavailable'
                : isLoading
                ? '...'
                : status?.agent_id || (status?.configured ? 'nexops-agent' : 'Not Configured')}
            </div>
          </div>

          {/* 3. Last Successful Handshake */}
          <div className="rounded-lg border border-[#1e2436] bg-[#0c0e15] p-3.5">
            <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-emerald-400" />
              Last Connection
            </span>
            <div className="mt-2 text-xs text-slate-300">
              {status?.last_connected_at
                ? new Date(status.last_connected_at).toLocaleTimeString() +
                  ' (' +
                  new Date(status.last_connected_at).toLocaleDateString() +
                  ')'
                : 'No session established yet'}
            </div>
          </div>

          {/* 4. Configuration Status */}
          <div className="rounded-lg border border-[#1e2436] bg-[#0c0e15] p-3.5">
            <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1.5">
              <Key className="w-3.5 h-3.5 text-cyan-400" />
              Environment Setup
            </span>
            <div className="mt-2 flex items-center gap-1.5 text-xs">
              {isError ? (
                <span className="text-rose-400">Backend Unreachable</span>
              ) : status?.configured ? (
                <span className="text-emerald-400 flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5" /> Credentials Present
                </span>
              ) : status?.enabled ? (
                <span className="text-amber-400 flex items-center gap-1">
                  <AlertTriangle className="w-3.5 h-3.5" /> Credentials Missing
                </span>
              ) : (
                <span className="text-slate-400">SWITCH_ENABLED=false</span>
              )}
            </div>
          </div>
        </div>

        {/* Dynamic Context Alert */}
        {isError && (
          <div className="mt-4 flex items-start gap-3 rounded-lg border border-rose-500/20 bg-rose-500/10 p-3.5 text-xs text-rose-300">
            <XCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
            <div>
              <p className="font-semibold text-rose-200">NexOps FastAPI Backend Offline</p>
              <p className="mt-0.5 text-rose-300/80">
                The frontend cannot contact <code>/api/v1/integrations/switch/status</code>. Verify that
                the FastAPI service is running on <code>http://localhost:8000</code>.
              </p>
            </div>
          </div>
        )}

        {!isError && status?.state === 'disabled' && (
          <div className="mt-4 flex items-start gap-3 rounded-lg border border-slate-500/20 bg-slate-500/10 p-3.5 text-xs text-slate-300">
            <Info className="w-4 h-4 shrink-0 text-slate-400 mt-0.5" />
            <div>
              <p className="font-semibold text-white">Switch Integration Disabled</p>
              <p className="mt-0.5 text-slate-400">
                The Switch listener is currently inactive by default. To connect to an official Switch
                instance, set <code>SWITCH_ENABLED=true</code> and provide credentials in{' '}
                <code>backend/.env</code>.
              </p>
            </div>
          </div>
        )}

        {!isError && status?.state === 'unconfigured' && (
          <div className="mt-4 flex items-start gap-3 rounded-lg border border-amber-500/20 bg-amber-500/10 p-3.5 text-xs text-amber-300">
            <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
            <div>
              <p className="font-semibold text-amber-200">Missing Switch Credentials</p>
              <p className="mt-0.5 text-amber-300/80">
                <code>SWITCH_ENABLED=true</code> is set, but <code>SWITCH_CORE_URL</code> or{' '}
                <code>SWITCH_API_KEY</code> is unset in the backend environment.
              </p>
            </div>
          </div>
        )}

        {!isError && status?.last_error && (
          <div className="mt-4 flex items-start gap-3 rounded-lg border border-amber-500/20 bg-amber-500/10 p-3.5 text-xs text-amber-300">
            <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
            <div>
              <p className="font-semibold text-amber-200">
                Last Integration Notice ({status.last_error_at ? new Date(status.last_error_at).toLocaleTimeString() : 'Recent'})
              </p>
              <p className="mt-0.5 font-mono text-[11px] text-amber-200/90">{status.last_error}</p>
            </div>
          </div>
        )}
      </div>

      {/* Backend Environment Configuration Guidance Table */}
      {showConfigGuide && (
        <div className="rounded-xl border border-[#1e2436] bg-[#121622] p-5 lg:p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#1e2436]">
            <div>
              <h4 className="text-sm font-semibold text-white">Required Backend Configuration</h4>
              <p className="text-xs text-slate-400 mt-0.5">
                Configure these keys inside <code>backend/.env</code>. For security, credentials are
                never editable via web clients.
              </p>
            </div>
            <a
              href="https://github.com/sandbox-quantum/switch"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300"
            >
              Switch Docs <ExternalLink className="w-3 h-3" />
            </a>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[#1e2436] text-slate-400">
                  <th className="py-2.5 px-3 font-medium">Variable</th>
                  <th className="py-2.5 px-3 font-medium">Required</th>
                  <th className="py-2.5 px-3 font-medium">Description</th>
                  <th className="py-2.5 px-3 font-medium">Example Value</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e2436]/60 font-mono">
                {CONFIG_ITEMS.map((item) => (
                  <tr key={item.key} className="hover:bg-[#161c2c]">
                    <td className="py-2.5 px-3 text-indigo-300 font-semibold">{item.key}</td>
                    <td className="py-2.5 px-3 font-sans">
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        Required
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-sans text-slate-300">{item.description}</td>
                    <td className="py-2.5 px-3 text-slate-400 text-[11px]">{item.example}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="rounded-lg border border-indigo-500/20 bg-indigo-500/5 p-3 text-xs text-indigo-300 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-indigo-400 shrink-0" />
            <span>
              <strong>Zero Secret Exposure:</strong> NexOps never exposes <code>SWITCH_API_KEY</code> in
              API responses, logs, or client-side JavaScript.
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
