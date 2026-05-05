import { useQuery } from '@tanstack/react-query'
import { TrendingUp } from 'lucide-react'
import { fetchTrades, fetchSignalQuality, fetchHistorySummary } from '../api/client'
import Card from '../components/Card'
import PageHeader from '../components/PageHeader'

function PnlCell({ v }: { v: number | null }) {
  if (v === null) return <span className="text-gray-500">–</span>
  const color = v > 0 ? 'text-emerald-400' : v < 0 ? 'text-red-400' : 'text-gray-400'
  return <span className={`font-mono ${color}`}>{v > 0 ? '+' : ''}{v.toFixed(2)}</span>
}

export default function History() {
  const { data: trades = [], isLoading: loadingTrades } = useQuery({
    queryKey: ['trades'], queryFn: () => fetchTrades({ limit: 100 }),
  })
  const { data: quality = [] } = useQuery({ queryKey: ['signalQuality'], queryFn: fetchSignalQuality })
  const { data: summary } = useQuery({ queryKey: ['historySummary'], queryFn: fetchHistorySummary })

  const sellTrades = trades.filter(t => t.tx_type === 'SELL')
  const hasData = sellTrades.length > 0

  return (
    <div>
      <PageHeader title="Trade-Archiv" subtitle={summary ? `${summary.total_trades} abgeschlossene Trades` : undefined} />

      <div className="p-6 space-y-6">
        {/* Empty State */}
        {!hasData && !loadingTrades && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="w-14 h-14 rounded-full bg-gray-800 flex items-center justify-center mb-4">
              <TrendingUp className="w-7 h-7 text-gray-600" />
            </div>
            <p className="text-gray-400 font-medium">Noch keine abgeschlossenen Trades</p>
            <p className="text-sm text-gray-600 mt-1 max-w-xs">
              Sobald du eine Portfolio-Position schließt, erscheinen hier P&L, Win-Rate und Signalqualität.
            </p>
          </div>
        )}

        {/* Zusammenfassung */}
        {hasData && summary && (
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            {[
              { label: 'Trades', value: summary.total_trades },
              { label: 'Profitable', value: summary.profitable },
              { label: 'Win-Rate', value: summary.win_rate_pct !== null ? `${summary.win_rate_pct.toFixed(1)}%` : '–' },
              { label: 'Ø P&L', value: summary.avg_pnl_pct !== null ? `${summary.avg_pnl_pct > 0 ? '+' : ''}${summary.avg_pnl_pct.toFixed(1)}%` : '–',
                color: (summary.avg_pnl_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400' },
              { label: 'Gesamt P&L', value: `${summary.total_pnl_abs >= 0 ? '+' : ''}${summary.total_pnl_abs.toFixed(2)} €`,
                color: summary.total_pnl_abs >= 0 ? 'text-emerald-400' : 'text-red-400' },
            ].map(c => (
              <div key={c.label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <p className="text-xs text-gray-500 uppercase tracking-wider">{c.label}</p>
                <p className={`text-2xl font-bold mt-1 ${c.color ?? 'text-white'}`}>{c.value}</p>
              </div>
            ))}
          </div>
        )}

        {hasData && <div className="grid lg:grid-cols-2 gap-6">
          {/* Signalqualität */}
          <Card title="Signalqualität">
            {quality.length === 0 ? (
              <p className="text-sm text-gray-500">Noch keine Daten</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-gray-500 uppercase tracking-wider border-b border-gray-800">
                    <th className="text-left pb-2">Signaltyp</th>
                    <th className="text-right pb-2">Trades</th>
                    <th className="text-right pb-2">Win-Rate</th>
                    <th className="text-right pb-2">Ø P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {quality.map(q => (
                    <tr key={q.signal_type} className="border-t border-gray-800/50">
                      <td className="py-2 text-gray-300">{q.signal_type}</td>
                      <td className="py-2 text-right text-gray-400">{q.total_trades}</td>
                      <td className="py-2 text-right">
                        <span className={q.win_rate_pct >= 50 ? 'text-emerald-400' : 'text-red-400'}>
                          {q.win_rate_pct.toFixed(1)}%
                        </span>
                      </td>
                      <td className="py-2 text-right">
                        <PnlCell v={q.avg_pnl_pct} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>

          {/* Haltezeiten */}
          {summary?.avg_hold_days !== null && (
            <Card title="Haltezeiten">
              <div className="flex items-center justify-center h-full min-h-[100px]">
                <div className="text-center">
                  <p className="text-4xl font-bold text-white">{summary!.avg_hold_days?.toFixed(0)}</p>
                  <p className="text-sm text-gray-500 mt-1">Ø Haltetage</p>
                </div>
              </div>
            </Card>
          )}
        </div>}

        {/* Trade-Tabelle */}
        {hasData && <Card title="Transaktionen">
          {loadingTrades ? (
            <p className="text-sm text-gray-500">Lade…</p>
          ) : sellTrades.length === 0 ? (
            <p className="text-sm text-gray-500">Noch keine abgeschlossenen Trades</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-gray-500 uppercase tracking-wider border-b border-gray-800">
                    <th className="text-left pb-2">Ticker</th>
                    <th className="text-right pb-2">Preis</th>
                    <th className="text-right pb-2">Stück</th>
                    <th className="text-right pb-2">P&L abs.</th>
                    <th className="text-right pb-2">P&L %</th>
                    <th className="text-right pb-2 hidden md:table-cell">Haltetage</th>
                    <th className="text-right pb-2">Datum</th>
                  </tr>
                </thead>
                <tbody>
                  {sellTrades.map(t => (
                    <tr key={t.id} className="border-t border-gray-800/50 hover:bg-gray-800/20">
                      <td className="py-2 font-medium text-white">{t.ticker}</td>
                      <td className="py-2 text-right text-gray-300">{t.price.toFixed(2)}</td>
                      <td className="py-2 text-right text-gray-400">{t.quantity}</td>
                      <td className="py-2 text-right"><PnlCell v={t.pnl_abs} /></td>
                      <td className="py-2 text-right"><PnlCell v={t.pnl_pct} /></td>
                      <td className="py-2 text-right text-gray-400 hidden md:table-cell">
                        {t.hold_days ?? '–'}
                      </td>
                      <td className="py-2 text-right text-gray-500 text-xs">{t.tx_date.slice(0, 10)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>}
      </div>
    </div>
  )
}
