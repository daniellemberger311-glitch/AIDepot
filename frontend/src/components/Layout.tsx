import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard, Eye, TrendingUp, Briefcase,
  History, FlaskConical, Settings,
} from 'lucide-react'

const NAV = [
  { to: '/',          icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/watchlist', icon: Eye,             label: 'Watchlist' },
  { to: '/portfolio', icon: Briefcase,       label: 'Portfolio' },
  { to: '/history',   icon: History,         label: 'Historie' },
  { to: '/backtest',  icon: FlaskConical,    label: 'Backtest' },
  { to: '/config',    icon: Settings,        label: 'Config' },
]

export default function Layout() {
  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <nav className="w-14 lg:w-52 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col py-4">
        <div className="px-3 mb-6 hidden lg:block">
          <span className="text-lg font-bold text-white tracking-tight">AI<span className="text-emerald-400">Depot</span></span>
        </div>
        <div className="px-3 mb-6 lg:hidden flex justify-center">
          <TrendingUp className="w-5 h-5 text-emerald-400" />
        </div>
        <div className="flex flex-col gap-1 px-2">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-2 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-emerald-500/10 text-emerald-400'
                    : 'text-gray-400 hover:text-gray-100 hover:bg-gray-800'
                }`
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span className="hidden lg:block">{label}</span>
            </NavLink>
          ))}
        </div>
      </nav>

      {/* Hauptinhalt */}
      <main className="flex-1 overflow-auto bg-gray-950">
        <Outlet />
      </main>
    </div>
  )
}
