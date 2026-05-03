import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Plus, X, TrendingDown } from 'lucide-react'
import { fetchPortfolio, createPosition, closePosition, deletePosition } from '../api/client'
import type { Position, PositionCreate } from '../types/api'
import Card from '../components/Card'
import PageHeader from '../components/PageHeader'
import SeverityBadge from '../components/SeverityBadge'

const STATUS_COLOR: Record<string, string> = {
  HALTEN: 'text-emerald-400',
  BEOBACHTEN: 'text-yellow-400',
  EXIT: 'text-red-400',
}

function PnlBadge({ pct }: { pct: number | null }) {
  if (pct === null) return <span className="text-gray-500">–</span>
  const color = pct > 0 ? 'text-emerald-400' : pct < 0 ? 'text-red-400' : 'text-gray-400'
  return <span className={`font-mono text-sm font-semibold ${color}`}>{pct > 0 ? '+' : ''}{pct.toFixed(1)}%</span>
}

function CloseModal({ pos, onClose }: { pos: Position; onClose: () => void }) {
  const qc = useQueryClient()
  const [price, setPrice] = useState('')
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
  const [notes, setNotes] = useState('')

  const close = useMutation({
    mutationFn: () => closePosition(pos.id, parseFloat(price), date, notes || undefined),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['portfolio'] }); onClose() },
  })

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-md p-6 space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-base font-semibold text-white">Position schließen – {pos.ticker}</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300"><X className="w-4 h-4" /></button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Verkaufspreis</label>
            <input
              type="number" step="0.01" value={price} onChange={e => setPrice(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
              placeholder="0.00"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Verkaufsdatum</label>
            <input
              type="date" value={date} onChange={e => setDate(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Notizen (optional)</label>
            <input
              value={notes} onChange={e => setNotes(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
              placeholder="z.B. Target erreicht"
            />
          </div>
        </div>
        <div className="flex gap-3 pt-2">
          <button onClick={onClose} className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg">Abbrechen</button>
          <button
            onClick={() => close.mutate()}
            disabled={!price || close.isPending}
            className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white text-sm rounded-lg"
          >
            {close.isPending ? 'Speichern…' : 'Position schließen'}
          </button>
        </div>
        {close.isError && <p className="text-xs text-red-400">{String(close.error)}</p>}
      </div>
    </div>
  )
}

function NewPositionForm({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient()
  const [form, setForm] = useState<Partial<PositionCreate>>({
    product_type: 'CALL_OS', direction: 'LONG', entry_date: new Date().toISOString().slice(0, 10),
  })

  const create = useMutation({
    mutationFn: () => createPosition(form as PositionCreate),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['portfolio'] }); onClose() },
  })

  const f = (k: keyof PositionCreate) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const val = e.target.type === 'number' ? parseFloat(e.target.value) || undefined : e.target.value
    setForm(prev => ({ ...prev, [k]: val }))
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-lg p-6 space-y-4 max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center">
          <h2 className="text-base font-semibold text-white">Neue Position</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300"><X className="w-4 h-4" /></button>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: 'Ticker *', key: 'ticker', type: 'text', placeholder: 'AAPL' },
            { label: 'ISIN', key: 'isin', type: 'text', placeholder: 'DE000…' },
            { label: 'Stückzahl *', key: 'quantity', type: 'number', placeholder: '100' },
            { label: 'Kaufkurs *', key: 'entry_price', type: 'number', placeholder: '0.00' },
            { label: 'Basispreis', key: 'underlying_at_entry', type: 'number', placeholder: '0.00' },
            { label: 'KO-Level', key: 'ko_level', type: 'number', placeholder: '0.00' },
            { label: 'Hebel', key: 'leverage', type: 'number', placeholder: '10' },
            { label: 'Kaufdatum *', key: 'entry_date', type: 'date', placeholder: '' },
            { label: 'Verfallsdatum', key: 'expiry_date', type: 'date', placeholder: '' },
          ].map(({ label, key, type, placeholder }) => (
            <div key={key} className={key === 'ticker' || key === 'entry_date' ? 'col-span-2' : ''}>
              <label className="text-xs text-gray-500 block mb-1">{label}</label>
              <input
                type={type} placeholder={placeholder}
                value={(form[key as keyof PositionCreate] as string | number | undefined) ?? ''}
                onChange={f(key as keyof PositionCreate)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
          ))}
          <div>
            <label className="text-xs text-gray-500 block mb-1">Typ</label>
            <select value={form.product_type} onChange={f('product_type')}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none">
              <option value="CALL_OS">Call OS</option>
              <option value="PUT_OS">Put OS</option>
              <option value="TURBO_LONG">Turbo Long</option>
              <option value="TURBO_SHORT">Turbo Short</option>
              <option value="AKTIE">Aktie</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Richtung</label>
            <select value={form.direction} onChange={f('direction')}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none">
              <option value="LONG">LONG</option>
              <option value="SHORT">SHORT</option>
            </select>
          </div>
        </div>
        <div className="flex gap-3 pt-2">
          <button onClick={onClose} className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg">Abbrechen</button>
          <button
            onClick={() => create.mutate()}
            disabled={!form.ticker || !form.quantity || !form.entry_price || create.isPending}
            className="flex-1 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-sm rounded-lg"
          >
            {create.isPending ? 'Speichern…' : 'Position anlegen'}
          </button>
        </div>
        {create.isError && <p className="text-xs text-red-400">{String(create.error)}</p>}
      </div>
    </div>
  )
}

function PositionRow({ pos }: { pos: Position }) {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [showClose, setShowClose] = useState(false)

  const del = useMutation({
    mutationFn: () => deletePosition(pos.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['portfolio'] }),
  })

  const statusColor = STATUS_COLOR[pos.status ?? ''] ?? 'text-gray-400'
  const openSignals = pos.exit_signals.filter(s => !s.is_acknowledged)

  return (
    <>
      {showClose && <CloseModal pos={pos} onClose={() => setShowClose(false)} />}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <button onClick={() => navigate(`/signal/${pos.ticker}`)}
                className="font-semibold text-white hover:text-emerald-400 transition-colors">
                {pos.ticker}
              </button>
              {pos.status && <span className={`text-xs font-medium ${statusColor}`}>{pos.status}</span>}
              <span className="text-xs text-gray-600">{pos.product_type}</span>
            </div>
            {pos.name && <p className="text-xs text-gray-500">{pos.name}</p>}
          </div>
          <PnlBadge pct={pos.unrealized_pnl_pct ?? null} />
        </div>

        <div className="grid grid-cols-3 gap-2 text-xs">
          <div>
            <p className="text-gray-600">Kaufkurs</p>
            <p className="text-white">{pos.entry_price.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-gray-600">Stück</p>
            <p className="text-white">{pos.quantity}</p>
          </div>
          <div>
            <p className="text-gray-600">Einstieg</p>
            <p className="text-white">{pos.entry_date.slice(0, 10)}</p>
          </div>
          {pos.ko_level !== null && (
            <div>
              <p className="text-gray-600">KO-Level</p>
              <p className="text-white">{pos.ko_level.toFixed(2)}</p>
            </div>
          )}
          {pos.ko_distance_pct !== null && (
            <div>
              <p className="text-gray-600">KO-Abstand</p>
              <p className={pos.ko_distance_pct < 10 ? 'text-red-400' : 'text-white'}>
                {pos.ko_distance_pct.toFixed(1)}%
              </p>
            </div>
          )}
          {pos.days_to_expiry !== null && (
            <div>
              <p className="text-gray-600">Restlaufzeit</p>
              <p className={pos.days_to_expiry < 14 ? 'text-yellow-400' : 'text-white'}>
                {pos.days_to_expiry}d
              </p>
            </div>
          )}
        </div>

        {openSignals.length > 0 && (
          <div className="space-y-1">
            {openSignals.map(sig => (
              <div key={sig.id} className="flex items-center gap-2 text-xs">
                <TrendingDown className="w-3 h-3 text-red-400 flex-shrink-0" />
                <SeverityBadge severity={sig.severity} />
                <span className="text-gray-400 truncate">{sig.message}</span>
              </div>
            ))}
          </div>
        )}

        <div className="flex gap-2 pt-1">
          <button onClick={() => setShowClose(true)}
            className="px-3 py-1.5 bg-red-600/20 hover:bg-red-600/30 text-red-400 text-xs rounded-lg transition-colors">
            Schließen
          </button>
          <button onClick={() => del.mutate()}
            className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-400 text-xs rounded-lg transition-colors">
            Löschen
          </button>
        </div>
      </div>
    </>
  )
}

export default function Portfolio() {
  const [showNew, setShowNew] = useState(false)
  const [showClosed, setShowClosed] = useState(false)

  const { data: positions = [], isLoading } = useQuery({
    queryKey: ['portfolio', showClosed],
    queryFn: () => fetchPortfolio(showClosed),
    refetchInterval: 60_000,
  })

  const open = positions.filter(p => p.is_open)
  const closed = positions.filter(p => !p.is_open)

  return (
    <div>
      {showNew && <NewPositionForm onClose={() => setShowNew(false)} />}
      <PageHeader
        title="Portfolio"
        subtitle={`${open.length} offene Position${open.length !== 1 ? 'en' : ''}`}
        action={
          <button onClick={() => setShowNew(true)}
            className="flex items-center gap-2 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-sm rounded-lg">
            <Plus className="w-4 h-4" /> Neue Position
          </button>
        }
      />

      <div className="p-6 space-y-6">
        {isLoading ? (
          <p className="text-gray-500">Lade…</p>
        ) : open.length === 0 ? (
          <Card>
            <p className="text-gray-500 text-sm text-center py-4">Keine offenen Positionen</p>
          </Card>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
            {open.map(pos => <PositionRow key={pos.id} pos={pos} />)}
          </div>
        )}

        {/* Geschlossene Positionen */}
        <div>
          <button onClick={() => setShowClosed(v => !v)}
            className="text-sm text-gray-500 hover:text-gray-300 transition-colors">
            {showClosed ? 'Geschlossene Positionen ausblenden' : `Geschlossene Positionen anzeigen (${closed.length})`}
          </button>
          {showClosed && closed.length > 0 && (
            <div className="mt-4 bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
              <table className="w-full text-sm">
                <thead className="border-b border-gray-800">
                  <tr className="text-xs text-gray-500 uppercase tracking-wider">
                    <th className="text-left px-4 py-3">Ticker</th>
                    <th className="text-left px-4 py-3">Einstieg</th>
                    <th className="text-left px-4 py-3">Ausstieg</th>
                    <th className="text-right px-4 py-3">P&L %</th>
                  </tr>
                </thead>
                <tbody>
                  {closed.map(pos => (
                    <tr key={pos.id} className="border-t border-gray-800/50">
                      <td className="px-4 py-3 font-medium text-white">{pos.ticker}</td>
                      <td className="px-4 py-3 text-gray-400">{pos.entry_date.slice(0, 10)}</td>
                      <td className="px-4 py-3 text-gray-400">–</td>
                      <td className="px-4 py-3 text-right"><PnlBadge pct={null} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
