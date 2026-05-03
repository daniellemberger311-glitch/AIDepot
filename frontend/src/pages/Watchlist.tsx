import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { ChevronUp, ChevronDown } from 'lucide-react'
import { fetchWatchlist, fetchZoneSummary } from '../api/client'
import PageHeader from '../components/PageHeader'
import ZoneBadge from '../components/ZoneBadge'
import ScoreBar from '../components/ScoreBar'
import DeltaBadge from '../components/DeltaBadge'

const ZONE_LABELS: Record<number, string> = {
  0: 'Alle',
  1: 'Zone 1 – Kaufzone',
  2: 'Zone 2 – Aufbau',
  3: 'Zone 3 – Radar',
  4: 'Zone 4 – Universum',
}

type SortKey = 'total_score' | 'delta_7d' | 'delta_1d' | 'ticker'

export default function Watchlist() {
  const navigate = useNavigate()
  const [zone, setZone] = useState(0)
  const [sort, setSort] = useState<SortKey>('total_score')
  const [asc, setAsc] = useState(false)

  const { data: summary } = useQuery({ queryKey: ['zoneSummary'], queryFn: fetchZoneSummary, refetchInterval: 60_000 })
  const { data: stocks = [], isLoading } = useQuery({
    queryKey: ['watchlist', zone, sort],
    queryFn: () => fetchWatchlist({ zone: zone || undefined, sort, limit: 200 }),
    refetchInterval: 60_000,
  })

  const sorted = [...stocks].sort((a, b) => {
    let av: number | string = a[sort] ?? (sort === 'ticker' ? '' : -Infinity)
    let bv: number | string = b[sort] ?? (sort === 'ticker' ? '' : -Infinity)
    if (typeof av === 'string') return asc ? av.localeCompare(bv as string) : (bv as string).localeCompare(av)
    return asc ? (av as number) - (bv as number) : (bv as number) - (av as number)
  })

  function toggleSort(key: SortKey) {
    if (sort === key) setAsc(a => !a)
    else { setSort(key); setAsc(false) }
  }

  function SortIcon({ k }: { k: SortKey }) {
    if (sort !== k) return <span className="w-3 h-3 inline-block" />
    return asc ? <ChevronUp className="w-3 h-3 inline-block" /> : <ChevronDown className="w-3 h-3 inline-block" />
  }

  return (
    <div>
      <PageHeader
        title="Watchlist"
        subtitle={summary ? `${summary.total} Aktien mit Scores – Stand ${summary.date?.slice(0, 10) ?? '–'}` : undefined}
      />

      <div className="p-6 space-y-4">
        {/* Zone Tabs */}
        <div className="flex gap-2 flex-wrap">
          {[0, 1, 2, 3, 4].map(z => {
            const count = z === 0 ? summary?.total : summary?.zones[z]
            return (
              <button
                key={z}
                onClick={() => setZone(z)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  zone === z
                    ? 'bg-emerald-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                {z === 0 ? 'Alle' : `Z${z}`}
                {count !== undefined && (
                  <span className="ml-1.5 text-xs opacity-70">{count}</span>
                )}
              </button>
            )
          })}
          <span className="text-sm text-gray-500 self-center ml-2">{ZONE_LABELS[zone]}</span>
        </div>

        {/* Table */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-gray-800">
              <tr className="text-gray-500 text-xs uppercase tracking-wider">
                <th className="text-left px-4 py-3 cursor-pointer hover:text-gray-300 w-8">#</th>
                <th className="text-left px-4 py-3 cursor-pointer hover:text-gray-300" onClick={() => toggleSort('ticker')}>
                  Ticker <SortIcon k="ticker" />
                </th>
                <th className="hidden md:table-cell text-left px-4 py-3 text-gray-500">Sektor</th>
                <th className="text-left px-4 py-3">Zone</th>
                <th className="text-left px-4 py-3 cursor-pointer hover:text-gray-300" onClick={() => toggleSort('total_score')}>
                  Score <SortIcon k="total_score" />
                </th>
                <th className="hidden sm:table-cell text-right px-4 py-3 cursor-pointer hover:text-gray-300" onClick={() => toggleSort('delta_1d')}>
                  Δ1T <SortIcon k="delta_1d" />
                </th>
                <th className="text-right px-4 py-3 cursor-pointer hover:text-gray-300" onClick={() => toggleSort('delta_7d')}>
                  Δ7T <SortIcon k="delta_7d" />
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-500">Lade…</td>
                </tr>
              ) : sorted.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-500">Keine Einträge</td>
                </tr>
              ) : (
                sorted.map((s, i) => (
                  <tr
                    key={s.ticker}
                    onClick={() => navigate(`/signal/${s.ticker}`)}
                    className="border-t border-gray-800/50 hover:bg-gray-800/40 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3 text-gray-600 text-xs">{i + 1}</td>
                    <td className="px-4 py-3">
                      <div className="font-semibold text-white">{s.ticker}</div>
                      {s.name && <div className="text-xs text-gray-500 truncate max-w-[140px]">{s.name}</div>}
                    </td>
                    <td className="hidden md:table-cell px-4 py-3 text-gray-400 text-xs truncate max-w-[120px]">
                      {s.sector ?? '–'}
                    </td>
                    <td className="px-4 py-3">
                      <ZoneBadge zone={s.zone} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold text-white w-8">{s.total_score.toFixed(0)}</span>
                        <div className="hidden lg:block w-20">
                          <ScoreBar score={s.total_score} zone={s.zone} />
                        </div>
                      </div>
                    </td>
                    <td className="hidden sm:table-cell px-4 py-3 text-right">
                      <DeltaBadge value={s.delta_1d} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <DeltaBadge value={s.delta_7d} />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
