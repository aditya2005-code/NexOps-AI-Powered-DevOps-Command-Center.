import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Clock, RefreshCw, Server, Radio, Database } from 'lucide-react'
import { PageHeader } from '@/components/common/PageHeader'
import { MetricCard } from '@/components/common/MetricCard'
import { IncidentOverview } from '@/components/dashboard/IncidentOverview'
import { OperationsActivity } from '@/components/dashboard/OperationsActivity'
import { AgentStatusPanel } from '@/components/dashboard/AgentStatusPanel'
import { IncidentTrendsChart } from '@/components/dashboard/IncidentTrendsChart'
import { SwitchStatusBadge } from '@/components/integrations/SwitchStatusBadge'
import { useHealth } from '@/hooks/useHealth'
import { useSwitchStatus } from '@/hooks/useSwitchStatus'
import { useIncidents, useIncidentStats } from '@/hooks/useIncidents'
import {
  DEMO_METRICS,
  DEMO_INCIDENTS,
  DEMO_AGENTS,
  DEMO_ACTIVITIES,
} from '@/constants/mockData'

export function DashboardPage() {
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d'>('7d')
  const { data: healthData, isError: isHealthError, isLoading: isHealthLoading, refetch: refetchHealth } = useHealth()
  const { data: switchStatus, isError: isSwitchError, isLoading: isSwitchLoading, refetch: refetchSwitch } = useSwitchStatus()
  const { data: liveIncidents, isLoading: isIncidentsLoading, refetch: refetchIncidents } = useIncidents()
  const { data: statsData, refetch: refetchStats } = useIncidentStats()

  const handleRefreshAll = () => {
    refetchHealth()
    refetchSwitch()
    refetchIncidents()
    refetchStats()
  }

  // If live incident stats exist, overlay them onto KPI metrics
  const activeIncidentsValue = statsData ? String(statsData.open) : DEMO_METRICS[0].value
  const displayMetrics = DEMO_METRICS.map((metric, idx) => {
    if (idx === 0) {
      return {
        ...metric,
        value: activeIncidentsValue,
        description: statsData ? 'Live incidents from Neon PostgreSQL' : metric.description,
      }
    }
    return metric
  })

  return (
    <div className="space-y-6">
      {/* Header with Time Period Filter & System Status */}
      <PageHeader
        title="Command Center"
        subtitle="Monitor your infrastructure, investigate incidents, and coordinate AI-powered DevOps operations."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {/* Backend connectivity badge */}
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border ${
                isHealthLoading
                  ? 'bg-amber-500/10 text-amber-300 border-amber-500/20'
                  : isHealthError
                  ? 'bg-rose-500/10 text-rose-300 border-rose-500/20'
                  : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
              }`}
              title="FastAPI Backend Health"
            >
              <Server className="w-3.5 h-3.5" />
              <span>
                {isHealthLoading
                  ? 'Connecting API...'
                  : isHealthError
                  ? 'API Offline'
                  : `API v${healthData?.version ?? '0.1.0'} Online`}
              </span>
            </div>

            {/* Switch integration status badge */}
            <Link to="/integrations/switch" title="View Switch Bridge Status">
              <SwitchStatusBadge
                state={switchStatus?.state}
                connected={switchStatus?.connected}
                isBackendError={isSwitchError}
                isLoading={isSwitchLoading}
              />
            </Link>

            {/* Time range selector */}
            <div className="flex rounded-md border border-[#1e2436] bg-[#121622] p-0.5">
              {(['24h', '7d', '30d'] as const).map((range) => (
                <button
                  key={range}
                  onClick={() => setTimeRange(range)}
                  className={`px-2.5 py-1 text-xs font-medium rounded transition-colors ${
                    timeRange === range
                      ? 'bg-indigo-600 text-white'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {range.toUpperCase()}
                </button>
              ))}
            </div>

            <button
              onClick={handleRefreshAll}
              className="p-1.5 rounded-md border border-[#1e2436] bg-[#121622] text-slate-400 hover:text-white hover:border-[#2f3954] transition-colors"
              title="Refresh Telemetry & Integrations"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        }
      />

      {/* Integration & Data Origin Context Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 px-4 py-3 rounded-lg bg-[#121622] border border-[#1e2436] text-xs">
        <div className="flex items-center gap-2.5">
          <Database className="w-4 h-4 text-emerald-400 shrink-0" />
          <span className="text-slate-300">
            <strong>Phase 4.4 Live Integration Active:</strong> Switch Agent Bridge status and incident persistence are connected to the FastAPI backend.
          </span>
        </div>
        <Link
          to="/integrations/switch"
          className="inline-flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-medium whitespace-nowrap self-end sm:self-auto"
        >
          <Radio className="w-3.5 h-3.5 text-cyan-400" />
          <span>Switch Bridge Console &rarr;</span>
        </Link>
      </div>

      {/* KPI Cards Row */}
      <section aria-label="Key Performance Indicators">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {displayMetrics.map((metric) => (
            <MetricCard key={metric.id} {...metric} />
          ))}
        </div>
      </section>

      {/* Trends Chart & Operations Feed Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="relative">
            <span className="absolute top-4 right-4 text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-500/10 text-slate-400 border border-slate-500/20">
              Demo Simulation Data
            </span>
            <IncidentTrendsChart />
          </div>
        </div>
        <div className="lg:col-span-1">
          <div className="relative">
            <span className="absolute top-4 right-4 text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-500/10 text-slate-400 border border-slate-500/20">
              Demo Feed
            </span>
            <OperationsActivity activities={DEMO_ACTIVITIES} />
          </div>
        </div>
      </div>

      {/* AI Agents Swarm Panel */}
      <div className="relative">
        <span className="absolute top-4 right-4 text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-500/10 text-slate-400 border border-slate-500/20">
          Agent Swarm (Phase 6 Planned)
        </span>
        <AgentStatusPanel agents={DEMO_AGENTS} />
      </div>

      {/* Active Incident Table (Connected to real backend with fallback) */}
      <IncidentOverview
        incidents={DEMO_INCIDENTS}
        liveIncidents={liveIncidents}
        isLiveLoading={isIncidentsLoading}
      />

      {/* Footer Meta */}
      <div className="flex items-center justify-between text-xs text-slate-500 pt-4 border-t border-[#1e2436]">
        <span>NexOps Command Center: React 19 + TypeScript + Vite 6 + FastAPI + Neon</span>
        <span className="flex items-center gap-1 font-mono text-[11px]">
          <Clock className="w-3.5 h-3.5" />
          Poll interval: 10s
        </span>
      </div>
    </div>
  )
}
