import { useLocation } from 'react-router-dom'
import {
  Menu,
  Search,
  Bell,
  Terminal,
} from 'lucide-react'

interface TopNavbarProps {
  onOpenMobile: () => void
}

const PAGE_TITLES: Record<string, { title: string; category: string }> = {
  '/': { title: 'Command Center', category: 'Overview' },
  '/dashboard': { title: 'Command Center', category: 'Overview' },
  '/projects': { title: 'Monitored Projects', category: 'Workspace' },
  '/incidents': { title: 'Incident Response & Queue', category: 'Workspace' },
  '/agents': { title: 'AI Agent Swarm', category: 'Workspace' },
  '/audit-logs': { title: 'Audit Trail & Compliance', category: 'Observability' },
  '/settings': { title: 'System Settings', category: 'System' },
}

export function TopNavbar({ onOpenMobile }: TopNavbarProps) {
  const location = useLocation()
  const pageInfo = PAGE_TITLES[location.pathname] || {
    title: 'Command Center',
    category: 'Overview',
  }

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-[#1e2436] bg-[#0c0e15]/90 px-4 sm:px-6 backdrop-blur-md">
      {/* Left: Mobile trigger & Breadcrumb */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobile}
          className="flex h-9 w-9 items-center justify-center rounded-md border border-[#1e2436] text-slate-400 hover:text-white lg:hidden"
          aria-label="Open mobile menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-400 hidden sm:inline">{pageInfo.category}</span>
          <span className="text-slate-400 hidden sm:inline">/</span>
          <span className="font-semibold text-white">{pageInfo.title}</span>
        </div>
      </div>

      {/* Center: Search UI */}
      <div className="hidden md:flex items-center w-72 lg:w-96">
        <div className="relative w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
          <input
            type="text"
            readOnly
            placeholder="Search incidents, services, traces... (⌘K)"
            className="w-full h-8 pl-8 pr-12 rounded-md border border-[#1e2436] bg-[#121622] text-xs text-slate-300 placeholder:text-slate-400 focus:outline-hidden focus:border-indigo-500/50 cursor-pointer"
          />
          <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded bg-[#1c2336] px-1.5 py-0.5 text-[10px] font-mono text-slate-400 border border-[#2b3550]">
            ⌘K
          </kbd>
        </div>
      </div>

      {/* Right: Environment, Notifications, User Profile */}
      <div className="flex items-center gap-3">
        {/* Environment Badge */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-[11px] font-medium text-indigo-300">
          <Terminal className="w-3 h-3 text-indigo-400" />
          <span>Stage: Development</span>
        </div>

        {/* Notifications */}
        <button
          className="relative flex h-8 w-8 items-center justify-center rounded-md border border-[#1e2436] bg-[#121622] text-slate-400 hover:text-white hover:border-[#2f3954] transition-colors"
          title="Incident Alerts"
          aria-label="Incident Alerts"
        >
          <Bell className="h-4 w-4" />
          <span className="absolute -top-1 -right-1 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-rose-500 text-[9px] font-bold text-white">
            3
          </span>
        </button>

        {/* User Profile */}
        <div className="flex items-center gap-2.5 pl-2 border-l border-[#1e2436]">
          <div className="h-7 w-7 rounded-full bg-linear-to-tr from-indigo-600 to-cyan-500 flex items-center justify-center text-xs font-bold text-white shadow-xs">
            AM
          </div>
          <div className="hidden xl:flex flex-col text-left">
            <span className="text-xs font-semibold text-white leading-tight">Alex Mercer</span>
            <span className="text-[10px] text-slate-400 leading-tight">Principal DevOps</span>
          </div>
        </div>
      </div>
    </header>
  )
}

