import { NavLink, Outlet } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  LayoutDashboard, Eye, TrendingUp, Briefcase,
  History, FlaskConical, Settings, Clock,
} from 'lucide-react'
import { fetchScanStatus } from '../api/client'

const NAV = [
  { to: '/',          icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/watchlist', icon: Eye,             label: 'Watchlist' },
  { to: '/portfolio', icon: Briefcase,       label: 'Portfolio' },
  { to: '/history',   icon: History,         label: 'Historie' },
  { to: '/backtest',  icon: FlaskConical,    label: 'Backtest' },
  { to: '/config',    icon: Settings,        label: 'Config' },
]

export default function Layout() {
  const { data: scanStatus } = useQuery({
    queryKey: ['scanStatus'],
    queryFn: fetchScanStatus,
    refetchInterval: 60_000,
  })

  const lastScan = scanStatus?.last_completed
    ? scanStatus.last_completed.slice(0, 16).replace('T', ' ')
    : null

  return (
    <div className="flex min-h-screen">
      {/* Sidebar – nur auf md+ sichtbar */}
      <nav className="hidden md:flex w-14 lg:w-52 flex-shrink-0 flex-col bg-gray-900 border-r border-gray-800 py-4">
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

        {/* Letzter Scan */}
        <div className="mt-auto px-3 pt-4 border-t border-gray-800/60">
          <div className="items-center gap-2 text-gray-600 hidden lg:flex">
            <Clock className="w-3 h-3 flex-shrink-0" />
            <div className="text-xs leading-tight">
              {lastScan ? (
                <>
                  <p className="text-gray-600">Letzter Scan</p>
                  <p className={`font-mono ${scanStatus?.error ? 'text-red-500' : 'text-gray-500'}`}>
                    {lastScan} UTC
                  </p>
                </>
              ) : (
                <p className="text-gray-700">Noch kein Scan</p>
              )}
            </div>
          </div>
          <div className="flex justify-center lg:hidden">
            <Clock className={`w-3.5 h-3.5 ${scanStatus?.error ? 'text-red-500' : 'text-gray-700'}`} />
          </div>
        </div>
      </nav>

      {/* Hauptinhalt – pb-16 auf Mobile für die Bottom-Nav */}
      <main className="flex-1 overflow-auto bg-gray-950 pb-16 md:pb-0">
        <Outlet />
      </main>

      {/* Bottom Navigation – nur auf Mobile (<md) */}
      <nav
        className="md:hidden fixed bottom-0 inset-x-0 bg-gray-900 border-t border-gray-800 z-50 flex justify-around items-center px-1 pt-2"
        style={{ paddingBottom: 'max(8px, env(safe-area-inset-bottom))' }}
      >
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex flex-col items-center gap-0.5 py-1 px-2 rounded-lg transition-colors min-w-[44px] ${
                isActive ? 'text-emerald-400' : 'text-gray-500 active:text-gray-300'
              }`
            }
          >
            <Icon className="w-5 h-5" />
            <span className="text-[10px] leading-none">{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
