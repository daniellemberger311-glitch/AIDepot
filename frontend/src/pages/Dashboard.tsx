import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { TrendingUp, AlertTriangle, Briefcase, Play, RefreshCw } from 'lucide-react'
import { fetchDashboard, fetchScanStatus, triggerScan, acknowledgeSignal } from '../api/client'
import Card from '../components/Card'
import PageHeader from '../components/PageHeader'
import ZoneBadge from '../components/ZoneBadge'
import DeltaBadge from '../components/DeltaBadge'
import ScoreBar from '../components/ScoreBar'
import SeverityBadge from '../components/SeverityBadge'

function StatCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <Card>
      <p className="text-xs text-gray-500 uppercase tracking-wider">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${color ?? 'text-white'}`}>{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
    </Card>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: dash, isLoading } = useQuery({ queryKey: ['dashboard'], queryFn: fetchDashboard, refetchInterval: 60_000 })
  const { data: scanStatus } = useQuery({ queryKey: ['scanStatus'], queryFn: fetchScanStatus, refetchInterval: 5_000 })

  const scan = useMutation({ mutationFn: triggerScan, onSuccess: () => qc.invalidateQueries({ queryKey: ['scanStatus'] }) })
  const ack  = useMutation({ mutationFn: acknowledgeSignal, onSuccess: () => qc.invalidateQueries({ queryKey: ['dashboard'] }) })

  if (isLoading) return <div className="p-6 text-gray-500">Lade…</div>

  const pnl      = dash?.total_pnl_abs ?? 0
  const pnlColor = pnl > 0 ? 'text-emerald-400' : pnl < 0 ? 'text-red-400' : 'text-gray-400'

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle={scanStatus?.last_completed ? `Letzter Scan: ${scanStatus.last_completed.slice(0, 16).replace('T', ' ')} UTC` : 'Noch kein Scan'}
        action={
          <button
            onClick={() => scan.mutate()}
            disabled={scanStatus?.running || scan.isPending}
            className="flex items-center gap-2 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm rounded-lg transition-colors"
          >
            {scanStatus?.running ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {scanStatus?.running ? `Scan läuft… ${scanStatus.progress}/${scanStatus.total}` : 'Scan starten'}
          </button>
        }
      />

      <div className="p-6 space-y-6">
        {/* KPIs */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Realisiertes P&L" value={`${pnl >= 0 ? '+' : ''}${pnl.toFixed(2)} €`} color={pnlColor} />
          <StatCard label="Offene Positionen" value={dash?.open_positions ?? 0} />
          <StatCard label="Exit-Warnungen" value={dash?.exit_alerts.length ?? 0} color={(dash?.exit_alerts.length ?? 0) > 0 ? 'text-red-400' : 'text-white'} />
          <StatCard label="Top-Signal Zone" value={dash?.top_signals[0] ? `Z${dash.top_signals[0].zone}` : '–'} sub={dash?.top_signals[0]?.ticker} />
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          {/* Top-5 Zone-1-Signale */}
          <Card title="Top-5 Signale (Zone 1)">
            {!dash?.top_signals.length ? (
              <p className="text-gray-600 text-sm">Noch keine Zone-1-Signale</p>
            ) : (
              <div className="space-y-3">
                {dash.top_signals.map(s => (
                  <button
                    key={s.ticker}
                    onClick={() => navigate(`/signal/${s.ticker}`)}
                    className="w-full text-left hover:bg-gray-800/60 rounded-lg p-2 -mx-2 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-white">{s.ticker}</span>
                        <ZoneBadge zone={s.zone} />
                      </div>
                      <div className="flex items-center gap-3 text-xs text-gray-500">
                        <DeltaBadge value={s.delta_7d} />
                        {s.strongest_signal && <span className="text-gray-600">{s.strongest_signal}</span>}
                      </div>
                    </div>
                    <ScoreBar score={s.total_score} zone={s.zone} />
                  </button>
                ))}
              </div>
            )}
          </Card>

          {/* Exit-Warnungen */}
          <Card title="Exit-Warnungen">
            {!dash?.exit_alerts.length ? (
              <div className="flex items-center gap-2 text-emerald-400 text-sm">
                <TrendingUp className="w-4 h-4" />
                Keine offenen Warnungen
              </div>
            ) : (
              <div className="space-y-3">
                {dash.exit_alerts.map(sig => (
                  <div key={sig.id} className="flex items-start justify-between gap-2 p-2 bg-gray-800/50 rounded-lg">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <AlertTriangle className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />
                        <span className="font-semibold text-sm text-white">{sig.ticker}</span>
                        <SeverityBadge severity={sig.severity} />
                      </div>
                      <p className="text-xs text-gray-400 truncate">{sig.message}</p>
                    </div>
                    <button
                      onClick={() => ack.mutate(sig.id)}
                      className="text-xs text-gray-500 hover:text-gray-300 flex-shrink-0"
                    >
                      Quittieren
                    </button>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
