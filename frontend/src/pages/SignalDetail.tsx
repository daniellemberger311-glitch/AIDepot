import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, RefreshCw } from 'lucide-react'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, ReferenceLine, CartesianGrid } from 'recharts'
import { fetchSignal, fetchSignalHistory, scanTicker } from '../api/client'
import Card from '../components/Card'
import PageHeader from '../components/PageHeader'
import ZoneBadge from '../components/ZoneBadge'
import DeltaBadge from '../components/DeltaBadge'
import ScoreBar from '../components/ScoreBar'

const ZONE_COLORS: Record<number, string> = { 1: '#10b981', 2: '#eab308', 3: '#f97316', 4: '#6b7280' }

function fmtPrice(price: number | null | undefined, currency: string | null | undefined): string {
  if (price == null) return '–'
  const p = price.toFixed(2)
  if (!currency || currency === 'USD') return `$${p}`
  if (currency === 'EUR') return `${p} €`
  if (currency === 'GBP') return `£${p}`
  return `${p} ${currency}`
}

function Row({ label, value, color }: { label: string; value: React.ReactNode; color?: string }) {
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-gray-800/60 last:border-0">
      <span className="text-xs text-gray-500">{label}</span>
      <span className={`text-sm font-medium ${color ?? 'text-white'}`}>{value}</span>
    </div>
  )
}

function ScoreRow({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = Math.min(100, (value / max) * 100)
  return (
    <div className="flex items-center gap-3 py-1.5 border-b border-gray-800/60 last:border-0">
      <span className="text-xs text-gray-500 w-44 flex-shrink-0">{label}</span>
      <div className="flex-1 bg-gray-800 rounded-full h-1.5">
        <div className="h-1.5 rounded-full bg-emerald-500" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-gray-300 w-8 text-right">{value.toFixed(1)}</span>
    </div>
  )
}

export default function SignalDetail() {
  const { ticker } = useParams<{ ticker: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: signal, isLoading } = useQuery({
    queryKey: ['signal', ticker],
    queryFn: () => fetchSignal(ticker!),
    enabled: !!ticker,
  })

  const { data: history = [] } = useQuery({
    queryKey: ['signalHistory', ticker],
    queryFn: () => fetchSignalHistory(ticker!, 30),
    enabled: !!ticker,
  })

  const rescan = useMutation({
    mutationFn: () => scanTicker(ticker!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['signal', ticker] })
      qc.invalidateQueries({ queryKey: ['signalHistory', ticker] })
    },
  })

  if (isLoading) return <div className="p-6 text-gray-500">Lade…</div>
  if (!signal) return <div className="p-6 text-gray-500">Signal nicht gefunden.</div>

  const bd = signal.breakdown
  const opt = signal.options_rec
  const zoneColor = ZONE_COLORS[signal.zone] ?? '#6b7280'

  const chartData = [...history].reverse().map(h => ({
    date: h.score_date.slice(0, 10),
    score: h.total_score,
    zone: h.zone,
  }))

  return (
    <div>
      <PageHeader
        title={
          <div className="flex items-center gap-3">
            <button onClick={() => navigate(-1)} className="text-gray-500 hover:text-gray-300 transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <span>{signal.ticker}</span>
            <ZoneBadge zone={signal.zone} />
          </div>
        }
        subtitle={signal.name ?? undefined}
        action={
          <button
            onClick={() => rescan.mutate()}
            disabled={rescan.isPending}
            className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white text-sm rounded-lg transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${rescan.isPending ? 'animate-spin' : ''}`} />
            Rescan
          </button>
        }
      />

      <div className="p-6 space-y-6">
        {/* Score Summary */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: 'Gesamt-Score', value: signal.total_score.toFixed(1), color: `text-[${zoneColor}]` },
            { label: 'Fundamental (L1)', value: `${signal.l1_fundamentals.toFixed(1)} / 40` },
            { label: 'Technisch (L2)', value: `${signal.l2_technicals.toFixed(1)} / 35` },
            { label: 'Sentiment (L3)', value: `${signal.l3_sentiment.toFixed(1)} / 25` },
          ].map(c => (
            <div key={c.label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wider">{c.label}</p>
              <p className="text-2xl font-bold mt-1 text-white">{c.value}</p>
              {c.label === 'Gesamt-Score' && (
                <div className="mt-2"><ScoreBar score={signal.total_score} zone={signal.zone} /></div>
              )}
            </div>
          ))}
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          {/* 30-Tage-Chart */}
          <Card title="Score-Verlauf (30 Tage)">
            {chartData.length < 2 ? (
              <p className="text-sm text-gray-500">Noch nicht genug Datenpunkte</p>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6b7280' }} tickLine={false} axisLine={false}
                    tickFormatter={d => d.slice(5)} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: '#6b7280' }} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                    labelStyle={{ color: '#9ca3af', fontSize: 11 }}
                    itemStyle={{ color: '#10b981' }}
                  />
                  <ReferenceLine y={76} stroke="#10b981" strokeDasharray="4 4" strokeOpacity={0.4} />
                  <ReferenceLine y={61} stroke="#eab308" strokeDasharray="4 4" strokeOpacity={0.4} />
                  <ReferenceLine y={41} stroke="#f97316" strokeDasharray="4 4" strokeOpacity={0.4} />
                  <Line type="monotone" dataKey="score" stroke={zoneColor} strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </Card>

          {/* Meta */}
          <Card title="Details">
            <Row label="Kurs" value={fmtPrice(signal.close_price, signal.currency)} />
            <Row label="Sektor" value={signal.sector ?? '–'} />
            <Row label="Score-Datum" value={signal.score_date.slice(0, 10)} />
            <Row label="Stärkstes Signal" value={signal.strongest_signal ?? '–'} />
            <Row label="Nächster Katalysator" value={signal.next_catalyst ?? '–'} />
            {signal.catalyst_days !== null && <Row label="Tage bis Katalysator" value={signal.catalyst_days} />}
            <Row label="Δ 1 Tag" value={<DeltaBadge value={signal.delta_1d} />} />
            <Row label="Δ 7 Tage" value={<DeltaBadge value={signal.delta_7d} />} />
            <Row label="Δ 30 Tage" value={<DeltaBadge value={signal.delta_30d} />} />
            {bd?.sentiment_suppressed && (
              <div className="mt-2 px-2 py-1 bg-yellow-900/30 border border-yellow-700/50 rounded text-xs text-yellow-400">
                Unterdrückt: Sentiment zu schwach für Zone 1
              </div>
            )}
          </Card>
        </div>

        {/* Score-Breakdown */}
        {bd && (
          <div className="grid lg:grid-cols-3 gap-6">
            <Card title="Fundamental (L1)">
              <ScoreRow label="KGV vs. Sektor" value={bd.pe_vs_sector} max={8} />
              <ScoreRow label="EPS-Beat-Streak" value={bd.eps_beat_streak} max={8} />
              <ScoreRow label="Umsatzwachstum" value={bd.revenue_growth} max={8} />
              <ScoreRow label="Free Cashflow" value={bd.fcf_score} max={6} />
              <ScoreRow label="Schulden/EK" value={bd.debt_equity} max={4} />
              <ScoreRow label="Insider-Netto" value={bd.insider_net} max={4} />
              <ScoreRow label="Earnings-Nähe" value={bd.earnings_proximity} max={2} />
            </Card>
            <Card title="Technisch (L2)">
              <ScoreRow label="VCP-Muster" value={bd.vcp_score} max={10} />
              <ScoreRow label="Volumen-Kontraktion" value={bd.volume_contraction} max={6} />
              <ScoreRow label="Preis/Widerstand" value={bd.price_vs_resistance} max={5} />
              <ScoreRow label="RSI-Zone" value={bd.rsi_zone} max={5} />
              <ScoreRow label="Relative Stärke" value={bd.relative_strength} max={5} />
              <ScoreRow label="MACD-Signal" value={bd.macd_signal} max={2} />
              <ScoreRow label="Bollinger Squeeze" value={bd.bollinger_squeeze} max={2} />
            </Card>
            <Card title="Sentiment (L3)">
              <ScoreRow label="News-Sentiment" value={bd.news_sentiment} max={10} />
              <ScoreRow label="StockTwits Bull-Ratio" value={bd.stocktwits_ratio} max={8} />
              <ScoreRow label="Reddit-Momentum" value={bd.reddit_momentum} max={4} />
              <ScoreRow label="Analysten-Delta" value={bd.analyst_delta} max={3} />
            </Card>
          </div>
        )}

        {/* Optionsschein-Empfehlung */}
        {opt && (
          <Card title="Optionsschein-Empfehlung (Zone 1)">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: 'Richtung', value: opt.direction },
                { label: 'Hebel', value: `${opt.leverage_min}×–${opt.leverage_max}×` },
                { label: 'Laufzeit', value: `${opt.duration_weeks} Wochen` },
                { label: 'KO-Abstand', value: `${opt.ko_distance_pct.toFixed(1)}%` },
              ].map(f => (
                <div key={f.label} className="bg-gray-800/50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">{f.label}</p>
                  <p className="text-base font-semibold text-emerald-400 mt-0.5">{f.value}</p>
                </div>
              ))}
            </div>
            {(opt.entry_trigger || opt.stop_loss) && (
              <div className="grid grid-cols-2 gap-4 mt-3">
                {opt.entry_trigger && (
                  <div className="bg-gray-800/50 rounded-lg p-3">
                    <p className="text-xs text-gray-500">Entry-Trigger</p>
                    <p className="text-base font-semibold text-white mt-0.5">${opt.entry_trigger.toFixed(2)}</p>
                    {opt.base_price_at_rec && (
                      <p className="text-xs text-gray-600 mt-0.5">Basispreis: ${opt.base_price_at_rec.toFixed(2)}</p>
                    )}
                  </div>
                )}
                {opt.stop_loss && (
                  <div className="bg-gray-800/50 rounded-lg p-3">
                    <p className="text-xs text-gray-500">Stop-Loss</p>
                    <p className="text-base font-semibold text-red-400 mt-0.5">${opt.stop_loss.toFixed(2)}</p>
                  </div>
                )}
              </div>
            )}
          </Card>
        )}
      </div>
    </div>
  )
}
