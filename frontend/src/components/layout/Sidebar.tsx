import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  FolderGit2,
  ShieldAlert,
  Bot,
  ScrollText,
  Settings,
  ChevronLeft,
  ChevronRight,
  Hexagon,
  Sparkles,
  Radio,
} from 'lucide-react'

interface SidebarProps {
  collapsed: boolean
  onToggleCollapse: () => void
  mobileOpen: boolean
  onCloseMobile: () => void
}

interface NavItem {
  to: string
  icon: React.ElementType
  label: string
  badge?: string
}

interface NavSection {
  title: string
  items: NavItem[]
}

const NAV_SECTIONS: NavSection[] = [
  {
    title: 'OVERVIEW',
    items: [
      { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    ],
  },
  {
    title: 'WORKSPACE',
    items: [
      { to: '/projects', icon: FolderGit2, label: 'Projects', badge: '12' },
      { to: '/incidents', icon: ShieldAlert, label: 'Incidents' },
      { to: '/integrations/switch', icon: Radio, label: 'Switch Bridge' },
      { to: '/agents', icon: Bot, label: 'AI Agents', badge: '5' },
    ],
  },
  {
    title: 'OBSERVABILITY',
    items: [
      { to: '/audit-logs', icon: ScrollText, label: 'Audit Logs' },
    ],
  },
  {
    title: 'SYSTEM',
    items: [
      { to: '/settings', icon: Settings, label: 'Settings' },
    ],
  },
]

export function Sidebar({
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onCloseMobile,
}: SidebarProps) {
  return (
    <>
      {/* Mobile backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-xs lg:hidden"
          onClick={onCloseMobile}
        />
      )}

      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 flex flex-col border-r border-[#1e2436] bg-[#0c0e15] transition-all duration-300 lg:static ${
          collapsed ? 'w-18' : 'w-64'
        } ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Brand header */}
        <div className="flex h-16 items-center justify-between px-4 border-b border-[#1e2436]">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-indigo-600/20 border border-indigo-500/30 text-indigo-400">
              <Hexagon className="h-5 w-5 fill-indigo-500/20" />
            </div>
            {!collapsed && (
              <div className="flex flex-col">
                <span className="text-sm font-bold tracking-tight text-white flex items-center gap-1.5">
                  NexOps
                  <span className="text-[10px] font-semibold text-indigo-400 bg-indigo-500/15 border border-indigo-500/30 px-1 rounded">
                    v0.1
                  </span>
                </span>
                <span className="text-[11px] text-slate-400 truncate">
                  AI DevOps Center
                </span>
              </div>
            )}
          </div>

          <button
            onClick={onToggleCollapse}
            className="hidden lg:flex h-6 w-6 items-center justify-center rounded text-slate-400 hover:text-white hover:bg-[#1a2030] transition-colors"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
        </div>

        {/* Navigation list */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
          {NAV_SECTIONS.map((section) => (
            <div key={section.title} className="space-y-1">
              {!collapsed && (
                <div className="px-2 pb-1 text-[10px] font-bold tracking-wider text-slate-400 uppercase">
                  {section.title}
                </div>
              )}
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={onCloseMobile}
                  className={({ isActive }) =>
                    `group relative flex items-center gap-3 rounded-md px-2.5 py-2 text-xs font-medium transition-all ${
                      isActive
                        ? 'bg-indigo-600/15 text-indigo-300 border border-indigo-500/30'
                        : 'text-slate-400 hover:bg-[#151926] hover:text-slate-200 border border-transparent'
                    } ${collapsed ? 'justify-center' : ''}`
                  }
                  title={collapsed ? item.label : undefined}
                >
                  <item.icon className="h-4 w-4 shrink-0 transition-transform group-hover:scale-105" />
                  {!collapsed && <span className="flex-1 truncate">{item.label}</span>}
                  {!collapsed && item.badge && (
                    <span className="ml-auto rounded bg-[#1c2336] px-1.5 py-0.5 text-[10px] font-mono text-slate-400 border border-[#2b3550]">
                      {item.badge}
                    </span>
                  )}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        {/* Bottom Agent / System Status */}
        <div className="p-3 border-t border-[#1e2436] bg-[#090b11]">
          {!collapsed ? (
            <div className="rounded-md border border-[#1e2436] bg-[#121622] p-2.5">
              <div className="flex items-center justify-between text-[11px] font-medium text-slate-300">
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                  Autonomous Engine
                </span>
                <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
              </div>
              <p className="mt-1 text-[10px] text-slate-400">
                5 agents idle / monitoring
              </p>
            </div>
          ) : (
            <div className="flex justify-center" title="Autonomous Engine Active">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 animate-pulse" />
            </div>
          )}
        </div>
      </aside>
    </>
  )
}
