import { LayoutDashboard, Activity, Settings } from 'lucide-react'
import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/activity', icon: Activity, label: 'Activity' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export function Sidebar() {
  return (
    <aside className="flex h-screen w-56 flex-col border-r bg-slate-900 text-slate-100">
      <div className="flex items-center gap-2 px-5 py-4 text-lg font-bold tracking-tight">
        <span className="text-blue-400">⬡</span> NexOps
      </div>
      <nav className="flex-1 space-y-1 px-2 py-2">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                isActive ? 'bg-slate-700 text-white' : 'text-slate-400 hover:bg-slate-800 hover:text-white'
              }`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
