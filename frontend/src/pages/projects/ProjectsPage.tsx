import { useState } from 'react'
import { FolderGit2, Search, ExternalLink, Activity, Plus } from 'lucide-react'
import { PageHeader } from '@/components/common/PageHeader'
import { StatusBadge } from '@/components/common/StatusBadge'
import { EmptyState } from '@/components/common/EmptyState'
import { Button } from '@/components/ui/button'
import { DEMO_PROJECTS } from '@/constants/mockData'

export function ProjectsPage() {
  const [search, setSearch] = useState('')
  const [envFilter, setEnvFilter] = useState<'all' | 'production' | 'staging'>('all')

  const filteredProjects = DEMO_PROJECTS.filter((p) => {
    const matchesSearch =
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.repository.toLowerCase().includes(search.toLowerCase())
    const matchesEnv = envFilter === 'all' || p.environment === envFilter
    return matchesSearch && matchesEnv
  })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Monitored Projects"
        subtitle="Connected code repositories, microservices, and cluster workloads under AI surveillance."
        actions={
          <Button className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs gap-1.5">
            <Plus className="w-3.5 h-3.5" />
            Connect Repository
          </Button>
        }
      />

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3 rounded-lg border border-[#1e2436] bg-[#121622]">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter by repository or project name..."
            className="w-full h-8.5 pl-8 pr-3 rounded-md border border-[#1e2436] bg-[#0c0e15] text-xs text-slate-200 placeholder:text-slate-400 focus:outline-hidden focus:border-indigo-500/50"
          />
        </div>

        <div className="flex items-center gap-1.5 self-end sm:self-auto text-xs">
          {(['all', 'production', 'staging'] as const).map((env) => (
            <button
              key={env}
              onClick={() => setEnvFilter(env)}
              className={`px-3 py-1.5 rounded-md font-medium capitalize transition-colors ${
                envFilter === env
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:bg-[#1a2030] hover:text-slate-200 border border-transparent'
              }`}
            >
              {env}
            </button>
          ))}
        </div>
      </div>

      {/* Projects List or Empty State */}
      {filteredProjects.length === 0 ? (
        <EmptyState
          title="No matching projects found"
          description="Adjust your search criteria or connect a new Git repository."
          icon={FolderGit2}
          actionLabel="Clear Filters"
          onAction={() => {
            setSearch('')
            setEnvFilter('all')
          }}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredProjects.map((project) => (
            <div
              key={project.id}
              className="flex flex-col justify-between rounded-lg border border-[#1e2436] bg-[#121622] p-5 hover:border-[#2d3752] transition-colors"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                      <FolderGit2 className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-white">{project.name}</h3>
                      <span className="text-[11px] font-mono text-slate-400 flex items-center gap-1 mt-0.5">
                        {project.repository}
                        <ExternalLink className="w-3 h-3 text-slate-400" />
                      </span>
                    </div>
                  </div>
                  <StatusBadge status={project.health} />
                </div>

                <div className="mt-4 grid grid-cols-2 gap-2 text-xs border-y border-[#1e2436] py-3 text-slate-400">
                  <div>
                    <span className="text-[11px] text-slate-400 block">Environment</span>
                    <span className="text-slate-200 capitalize font-medium">{project.environment}</span>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-400 block">Services</span>
                    <span className="text-slate-200 font-medium">{project.servicesCount} running</span>
                  </div>
                </div>
              </div>

              <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
                <span className="flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-indigo-400" />
                  Active: {project.lastActivity}
                </span>
                {project.activeIncidentsCount > 0 ? (
                  <span className="text-rose-400 font-medium">
                    {project.activeIncidentsCount} active alert
                  </span>
                ) : (
                  <span className="text-emerald-400 font-medium">All systems green</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

