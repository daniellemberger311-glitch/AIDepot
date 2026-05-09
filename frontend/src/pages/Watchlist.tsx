import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { ChevronUp, ChevronDown, Search, X } from 'lucide-react'
import { fetchWatchlist, fetchZoneSummary } from '../api/client'
import PageHeader from '../components/PageHeader'
import ZoneBadge from '../components/ZoneBadge'
import ScoreBar from '../components/ScoreBar'
import DeltaBadge from '../components/DeltaBadge'

function fmtPrice(price: number | null | undefined, currency: string | null | undefined): string {
  if (price == null) return '–'
  const p = price.toFixed(2)
  if (!currency || currency === 'USD') return `$${p}`
  if (currency === 'EUR') return `${p} €`
  if (currency === 'GBP') return `£${p}`
  return `${p} ${currency}`
}

const ZONE_LABELS: Record<number, string> = {
  0: 'Alle',
  1: 'Zone 1 – Kaufzone',
  2: 'Zone 2 – Aufbau',
  3: 'Zone 3 – Radar',
  4: 'Zone 4 – Universum',
}

type SortKey = 'total_score' | 'delta_7d' | 'delta_1d' | 'ticker' | 'l1_fundamentals' | 'l2_technicals' | 'l3_sentiment'

const SORT_LABELS: { key: SortKey; label: string }[] = [
  { key: 'total_score',     label: 'Score' },
  { key: 'l1_fundamentals', label: 'L1 Fund.' },
  { key: 'l2_technicals',   label: 'L2 Tech.' },
  { key: 'l3_sentiment',    label: 'L3 Sent.' },
  { key: 'delta_1d',        label: 'Δ1T' },
  { key: 'delta_7d',        label: 'Δ7T' },
  { key: 'ticker',          label: 'Ticker' },
]

export default function Watchlist() {
  const navigate = useNavigate()
  const [zone, setZone] = useState(0)
  const [sort, setSort] = useState<SortKey>('total_score')
  const [asc, setAsc] = useState(false)
  const [search, setSearch] = useState('')

  const { data: summary } = useQuery({ queryKey: ['zoneSummary'], queryFn: fetchZoneSummary, refetchInterval: 60_000 })
  const { data: stocks = [], isLoading } = useQuery({
    queryKey: ['watchlist', zone, sort],
    queryFn: () => fetchWatchlist({ zone: zone || undefined, sort, limit: 1000 }),
    refetchInterval: 60_000,
  })

  const filtered = search.trim()
    ? stocks.filter(s =>
        s.ticker.toLowerCase().includes(search.toLowerCase()) ||
        (s.name ?? '').toLowerCase().includes(search.toLowerCase())
      )
    : stocks

  const sorted = [...filtered].sort((a, b) => {
    const av = (a[sort as keyof typeof a] ?? (sort === 'ticker' ? '' : -Infinity)) as number | string
    const bv = (b[sort as keyof typeof b] ?? (sort === 'ticker' ? '' : -Infinity)) as number | string
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
        subtitle={summary ? `${summary.total} Aktien – Stand ${summary.date?.slice(0, 10) ?? '–'}` : undefined}
      />

      <div className="p-4 space-y-3">
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
          <span className="text-sm text-gray-500 self-center ml-1">{ZONE_LABELS[zone]}</span>
        </div>

        {/* Suche + Sortier-Schnellauswahl */}
        <div className="flex flex-wrap gap-2 items-center">
          {/* Suchfeld */}
          <div className="relative flex-1 min-w-[160px] max-w-xs">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500 pointer-events-none" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Ticker / Name suchen…"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-8 pr-7 py-1.5 text-sm text-white focus:outline-none focus:border-emerald-500"
            />
            {search && (
              <button onClick={() => setSearch('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300">
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Sortier-Buttons */}
          <div className="flex gap-1 flex-wrap">
            {SORT_LABELS.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => toggleSort(key)}
                className={`flex items-center gap-0.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  sort === key
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                {label}
                {sort === key && (asc
                  ? <ChevronUp className="w-3 h-3" />
                  : <ChevronDown className="w-3 h-3" />)}
              </button>
            ))}
          </div>
        </div>

        {/* Tabelle mit horizontalem Scroll */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-x-auto">
          <table className="w-full text-sm min-w-[520px]">
            <thead className="border-b border-gray-800">
              <tr className="text-gray-500 text-xs uppercase tracking-wider">
                <th className="text-left px-4 py-3 w-8">#</th>
                <th className="text-left px-4 py-3 cursor-pointer hover:text-gray-300" onClick={() => toggleSort('ticker')}>
                  Ticker <SortIcon k="ticker" />
                </th>
                <th className="hidden md:table-cell text-left px-4 py-3">Sektor</th>
                <th className="text-left px-4 py-3">Zone</th>
                <th className="text-left px-4 py-3 cursor-pointer hover:text-gray-300" onClick={() => toggleSort('total_score')}>
                  Score <SortIcon k="total_score" />
                </th>
                <th className="text-right px-3 py-3 cursor-pointer hover:text-gray-300 text-blue-400" onClick={() => toggleSort('l1_fundamentals')}>
                  L1 <SortIcon k="l1_fundamentals" />
                </th>
                <th className="text-right px-3 py-3 cursor-pointer hover:text-gray-300 text-purple-400" onClick={() => toggleSort('l2_technicals')}>
                  L2 <SortIcon k="l2_technicals" />
                </th>
                <th className="text-right px-3 py-3 cursor-pointer hover:text-gray-300 text-amber-400" onClick={() => toggleSort('l3_sentiment')}>
                  L3 <SortIcon k="l3_sentiment" />
                </th>
                <th className="hidden md:table-cell text-right px-4 py-3">Kurs</th>
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
                  <td colSpan={11} className="px-4 py-8 text-center text-gray-500">Lade…</td>
                </tr>
              ) : sorted.length === 0 ? (
                <tr>
                  <td colSpan={11} className="px-4 py-8 text-center text-gray-500">
                    {search ? `Keine Ergebnisse für „${search}“` : 'Keine Einträge'}
                  </td>
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
                    <td className="hidden md:table-cell px-4 py-3 text-gray-400 text-xs truncate max-w-[100px]">
                      {s.sector ?? '–'}
                    </td>
                    <td className="px-4 py-3">
                      <ZoneBadge zone={s.zone} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold text-white w-8">{s.total_score.toFixed(0)}</span>
                        <div className="hidden lg:block w-16">
                          <ScoreBar score={s.total_score} zone={s.zone} />
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-3 text-right font-mono text-xs text-blue-400">
                      {s.l1_fundamentals?.toFixed(0) ?? '–'}
                    </td>
                    <td className="px-3 py-3 text-right font-mono text-xs text-purple-400">
                      {s.l2_technicals?.toFixed(0) ?? '–'}
                    </td>
                    <td className="px-3 py-3 text-right font-mono text-xs text-amber-400">
                      {s.l3_sentiment?.toFixed(0) ?? '–'}
                    </td>
                    <td className="hidden md:table-cell px-4 py-3 text-right font-mono text-sm text-gray-300">
                      {fmtPrice(s.close_price, s.currency)}
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
        {sorted.length > 0 && (
          <p className="text-xs text-gray-600 text-right">{sorted.length} Aktien</p>
        )}
      </div>
    </div>
  )
}
