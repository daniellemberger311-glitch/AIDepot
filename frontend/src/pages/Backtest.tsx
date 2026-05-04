import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Play } from 'lucide-react'
import {
  ResponsiveContainer, ComposedChart, Line, XAxis, YAxis,
  Tooltip, CartesianGrid, ReferenceLine, Legend,
} from 'recharts'
import { runBacktest } from '../api/client'
import type { BacktestResult, BacktestSignalEvent } from '../types/api'
import Card from '../components/Card'
import PageHeader from '../components/PageHeader'
import ZoneBadge from '../components/ZoneBadge'

const EVENT_COLOR: Record<string, string> = {
  ZONE1_ENTRY: '#10b981',
  ZONE_CHANGE: '#eab308',
  DELTA_SPIKE: '#3b82f6',
  STREAK_7D: '#a855f7',
}

function EventBadge({ type }: { type: string }) {
  const color = EVENT_COLOR[type] ?? '#6b7280'
  const labels: Record<string, string> = {
    ZONE1_ENTRY: 'Z1 Entry', ZONE_CHANGE: 'Zonenwechsel',
    DELTA_SPIKE: 'Δ-Spike', STREAK_7D: '7T-Streak',
  }
  return (
    <span className="inline-block px-2 py-0.5 rounded text-xs font-medium" style={{ color, background: `${color}20` }}>
      {labels[type] ?? type}
    </span>
  )
}

interface ChartPoint {
  date: string; close: number; score: number; zone: number
  event?: BacktestSignalEvent
}

export default function Backtest() {
  const [ticker, setTicker] = useState('')
  const [fromDate, setFromDate] = useState(() => {
    const d = new Date(); d.setFullYear(d.getFullYear() - 1); return d.toISOString().slice(0, 10)
  })
  const [toDate, setToDate] = useState(new Date().toISOString().slice(0, 10))
  const [result, setResult] = useState<BacktestResult | null>(null)

  const bt = useMutation({
    mutationFn: () => runBacktest(ticker.toUpperCase().trim(), fromDate, toDate),
    onSuccess: data => setResult(data),
  })

  const chartData: ChartPoint[] = (result?.price_data ?? []).map(p => {
    const event = result?.signals.find(s => s.date === p.date)
    return { date: p.date.slice(0, 10), close: p.close, score: p.score, zone: p.zone, event }
  })

  const sum = result?.summary

  return (
    <div>
      <PageHeader title="Backtesting" subtitle="Historische Scoring-Simulation" />

      <div className="p-6 space-y-6">
        {/* Eingabe */}
        <Card title="Parameter">
          <div className="flex flex-wrap gap-3 items-end">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Ticker</label>
              <input
                value={ticker} onChange={e => setTicker(e.target.value.toUpperCase())}
                placeholder="AAPL"
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white w-32 focus:outline-none focus:border-emerald-500 uppercase"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Von</label>
              <input type="date" value={fromDate} onChange={e => setFromDate(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Bis</label>
              <input type="date" value={toDate} onChange={e => setToDate(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500" />
            </div>
            <button
              onClick={() => bt.mutate()}
              disabled={!ticker || bt.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-sm rounded-lg transition-colors"
            >
              <Play className="w-4 h-4" />
              {bt.isPending ? 'Läuft…' : 'Starten'}
            </button>
          </div>
          {bt.isError && <p className="text-xs text-red-400 mt-2">{String(bt.error)}</p>}
        </Card>

        {result && (
          <>
            {/* KPIs */}
            {sum && (
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  { label: 'Handelstage', value: sum.total_trading_days },
                  { label: 'Zone-1-Tage', value: `${sum.zone1_days} (${sum.zone1_days_pct.toFixed(1)}%)` },
                  { label: 'Zone-1-Eintritte', value: sum.zone1_entries },
                  { label: 'Δ-Spikes', value: sum.delta_spikes },
                  { label: 'Signale gesamt', value: sum.total_signals },
                  { label: 'Ø Score', value: sum.avg_score?.toFixed(1) ?? '–' },
                  { label: 'Max Score', value: sum.max_score?.toFixed(1) ?? '–' },
                  { label: '7T-Streaks', value: sum.streaks_7d },
                ].map(c => (
                  <div key={c.label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                    <p className="text-xs text-gray-500 uppercase tracking-wider">{c.label}</p>
                    <p className="text-xl font-bold mt-1 text-white">{c.value}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Preis-Chart */}
            <Card title={`${result.ticker} – Kurs & Score`}>
              {chartData.length < 2 ? (
                <p className="text-sm text-gray-500">Nicht genug Daten</p>
              ) : (
                <ResponsiveContainer width="100%" height={280}>
                  <ComposedChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: -10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6b7280' }} tickLine={false} axisLine={false}
                      tickFormatter={d => d.slice(2, 7)} interval="preserveStartEnd" />
                    <YAxis yAxisId="price" orientation="right" tick={{ fontSize: 10, fill: '#6b7280' }} tickLine={false} axisLine={false} />
                    <YAxis yAxisId="score" orientation="left" domain={[0, 100]} tick={{ fontSize: 10, fill: '#6b7280' }} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                      labelStyle={{ color: '#9ca3af', fontSize: 11 }}
                    />
                    <Legend wrapperStyle={{ fontSize: 11, color: '#9ca3af' }} />
                    <ReferenceLine yAxisId="score" y={76} stroke="#10b981" strokeDasharray="4 4" strokeOpacity={0.4} />
                    <ReferenceLine yAxisId="score" y={61} stroke="#eab308" strokeDasharray="4 4" strokeOpacity={0.4} />
                    <Line yAxisId="score" type="monotone" dataKey="score" stroke="#6366f1" strokeWidth={1.5}
                      dot={false} name="Score" />
                    <Line yAxisId="price" type="monotone" dataKey="close" stroke="#e5e7eb" strokeWidth={1.5}
                      dot={false} name="Kurs" />
                  </ComposedChart>
                </ResponsiveContainer>
              )}
            </Card>

            {/* Signal-Ereignisse */}
            {result.signals.length > 0 && (
              <Card title="Signal-Ereignisse">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-xs text-gray-500 uppercase tracking-wider border-b border-gray-800">
                        <th className="text-left pb-2">Datum</th>
                        <th className="text-left pb-2">Typ</th>
                        <th className="text-left pb-2">Zone</th>
                        <th className="text-right pb-2">Score</th>
                        <th className="text-right pb-2 hidden md:table-cell">Δ1T</th>
                        <th className="text-left pb-2 hidden lg:table-cell">Beschreibung</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.signals.map((sig, i) => (
                        <tr key={i} className="border-t border-gray-800/50">
                          <td className="py-2 text-gray-400 text-xs">{sig.date.slice(0, 10)}</td>
                          <td className="py-2"><EventBadge type={sig.event_type} /></td>
                          <td className="py-2">
                            {sig.to_zone !== null && <ZoneBadge zone={sig.to_zone} />}
                          </td>
                          <td className="py-2 text-right font-mono text-gray-300">{sig.score.toFixed(1)}</td>
                          <td className="py-2 text-right text-gray-400 hidden md:table-cell text-xs">
                            {sig.delta_1d !== null ? `${sig.delta_1d > 0 ? '+' : ''}${sig.delta_1d.toFixed(1)}` : '–'}
                          </td>
                          <td className="py-2 text-gray-500 text-xs hidden lg:table-cell truncate max-w-[240px]">
                            {sig.description}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            )}
          </>
        )}
      </div>
    </div>
  )
}
