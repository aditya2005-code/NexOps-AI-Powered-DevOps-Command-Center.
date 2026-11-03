import { useState } from 'react'
import { Clock, RefreshCw, Server, AlertCircle } from 'lucide-react'
import { PageHeader } from '@/components/common/PageHeader'
import { MetricCard } from '@/components/common/MetricCard'
import { IncidentOverview } from '@/components/dashboard/IncidentOverview'
import { OperationsActivity } from '@/components/dashboard/OperationsActivity'
import { AgentStatusPanel } from '@/components/dashboard/AgentStatusPanel'
import { IncidentTrendsChart } from '@/components/dashboard/IncidentTrendsChart'
import { useHealth } from '@/hooks/useHealth'
import {
  DEMO_METRICS,
  DEMO_INCIDENTS,
  DEMO_AGENTS,
  DEMO_ACTIVITIES,
} from '@/constants/mockData'

export function DashboardPage() {
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d'>('7d')
  const { data: healthData, isError, isLoading } = useHealth()

  return (
    <div className="space-y-6">
      {/* Header with Time Period Filter & System Status */}
      <PageHeader
        title="Command Center"
        subtitle="Monitor your infrastructure, investigate incidents, and coordinate AI-powered DevOps operations."
        actions={
          <div className="flex items-center gap-2">
            {/* Backend connectivity badge */}
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border ${
                isLoading
                  ? 'bg-amber-500/10 text-amber-300 border-amber-500/20'
                  : isError
                  ? 'bg-rose-500/10 text-rose-300 border-rose-500/20'
                  : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
              }`}
              title="FastAPI Backend Health"
            >
              <Server className="w-3.5 h-3.5" />
              <span>
                {isLoading
                  ? 'Connecting API...'
                  : isError
                  ? 'API Offline'
                  : `API v${healthData?.version ?? '0.1.0'} Online`}
              </span>
            </div>

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
              className="p-1.5 rounded-md border border-[#1e2436] bg-[#121622] text-slate-400 hover:text-white hover:border-[#2f3954] transition-colors"
              title="Refresh Telemetry"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        }
      />

      {/* Demo Warning / Context Notice */}
      <div className="flex items-center gap-2.5 px-4 py-2.5 rounded-md bg-indigo-500/10 border border-indigo-500/20 text-xs text-indigo-300">
        <AlertCircle className="w-4 h-4 text-indigo-400 shrink-0" />
        <span>
          <strong>Phase 2 Demonstration Mode:</strong> Metrics, incidents, and activity streams are
          rendered from structured simulation models. Live agents and cluster integrations will
          connect in subsequent phases.
        </span>
      </div>

      {/* KPI Cards Row */}
      <section aria-label="Key Performance Indicators">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {DEMO_METRICS.map((metric) => (
            <MetricCard key={metric.id} {...metric} />
          ))}
        </div>
      </section>

      {/* Trends Chart & Operations Feed Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <IncidentTrendsChart />
        </div>
        <div className="lg:col-span-1">
          <OperationsActivity activities={DEMO_ACTIVITIES} />
        </div>
      </div>

      {/* AI Agents Swarm Panel */}
      <AgentStatusPanel agents={DEMO_AGENTS} />

      {/* Active Incident Table */}
      <IncidentOverview incidents={DEMO_INCIDENTS} />

      {/* Footer Meta */}
      <div className="flex items-center justify-between text-xs text-slate-500 pt-4 border-t border-[#1e2436]">
        <span>NexOps Architecture: React 19 + Vite 6 + Tailwind v4 + FastAPI</span>
        <span className="flex items-center gap-1">
          <Clock className="w-3.5 h-3.5" />
          Last telemetry poll: Just now
        </span>
      </div>
    </div>
  )
}

