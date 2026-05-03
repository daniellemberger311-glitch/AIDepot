import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, XCircle, RefreshCw, Plus, Trash2 } from 'lucide-react'
import {
  fetchConfig, updateConfig, fetchApiStatus, fetchScanSchedule,
  fetchUniverse, searchUniverse, addTicker, deactivateTicker, refreshUniverse,
} from '../api/client'
import type { AppConfig } from '../types/api'
import Card from '../components/Card'
import PageHeader from '../components/PageHeader'

type Tab = 'universe' | 'api' | 'weights' | 'scan' | 'alerts'

const TABS: { id: Tab; label: string }[] = [
  { id: 'universe', label: 'Universum' },
  { id: 'api', label: 'API-Status' },
  { id: 'weights', label: 'Gewichtungen' },
  { id: 'scan', label: 'Scan-Config' },
  { id: 'alerts', label: 'Alerts' },
]

// ── Universe Tab ─────────────────────────────────────────────────────────────
function UniverseTab() {
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [newTicker, setNewTicker] = useState('')
  const [searchResults, setSearchResults] = useState<Awaited<ReturnType<typeof searchUniverse>>>([])

  const { data: universe = [], isLoading } = useQuery({
    queryKey: ['universe'], queryFn: () => fetchUniverse({ active_only: false }),
  })

  const doSearch = useMutation({
    mutationFn: () => searchUniverse(search),
    onSuccess: data => setSearchResults(data),
  })

  const add = useMutation({
    mutationFn: () => addTicker(newTicker.toUpperCase().trim()),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['universe'] }); setNewTicker('') },
  })

  const deactivate = useMutation({
    mutationFn: (ticker: string) => deactivateTicker(ticker),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['universe'] }),
  })

  const refresh = useMutation({
    mutationFn: refreshUniverse,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['universe'] }),
  })

  const active = universe.filter(u => u.is_active)
  const display = search && searchResults.length ? searchResults : active.slice(0, 50)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-[180px]">
          <label className="text-xs text-gray-500 block mb-1">Ticker hinzufügen</label>
          <div className="flex gap-2">
            <input
              value={newTicker} onChange={e => setNewTicker(e.target.value.toUpperCase())}
              placeholder="TSLA"
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
            />
            <button onClick={() => add.mutate()} disabled={!newTicker || add.isPending}
              className="px-3 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg">
              <Plus className="w-4 h-4" />
            </button>
          </div>
        </div>
        <div className="flex-1 min-w-[180px]">
          <label className="text-xs text-gray-500 block mb-1">Suchen</label>
          <div className="flex gap-2">
            <input
              value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Apple…"
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
            />
            <button onClick={() => doSearch.mutate()} disabled={!search}
              className="px-3 py-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white rounded-lg text-sm">
              Suchen
            </button>
          </div>
        </div>
        <button onClick={() => refresh.mutate()} disabled={refresh.isPending}
          className="flex items-center gap-2 px-3 py-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white text-sm rounded-lg">
          <RefreshCw className={`w-4 h-4 ${refresh.isPending ? 'animate-spin' : ''}`} />
          Universum aktualisieren
        </button>
      </div>

      <div className="text-xs text-gray-500">{active.length} aktive Ticker</div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden max-h-[400px] overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-gray-900 border-b border-gray-800">
            <tr className="text-xs text-gray-500 uppercase tracking-wider">
              <th className="text-left px-4 py-3">Ticker</th>
              <th className="text-left px-4 py-3 hidden md:table-cell">Name</th>
              <th className="text-left px-4 py-3 hidden lg:table-cell">Quelle</th>
              <th className="text-left px-4 py-3">Status</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-500">Lade…</td></tr>
            ) : display.map(u => (
              <tr key={u.ticker} className="border-t border-gray-800/50 hover:bg-gray-800/20">
                <td className="px-4 py-2 font-medium text-white">{u.ticker}</td>
                <td className="px-4 py-2 text-gray-400 text-xs hidden md:table-cell truncate max-w-[140px]">{u.name ?? '–'}</td>
                <td className="px-4 py-2 text-gray-500 text-xs hidden lg:table-cell">{u.universe_source ?? '–'}</td>
                <td className="px-4 py-2">
                  <span className={`text-xs ${u.is_active ? 'text-emerald-400' : 'text-gray-600'}`}>
                    {u.is_active ? 'aktiv' : 'inaktiv'}
                  </span>
                </td>
                <td className="px-4 py-2 text-right">
                  {u.is_active && (
                    <button onClick={() => deactivate.mutate(u.ticker)}
                      className="text-gray-600 hover:text-red-400 transition-colors">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── API Status Tab ────────────────────────────────────────────────────────────
function ApiStatusTab() {
  const { data: status, isLoading, refetch } = useQuery({ queryKey: ['apiStatus'], queryFn: fetchApiStatus })

  return (
    <div className="space-y-3">
      <button onClick={() => refetch()} className="flex items-center gap-2 text-sm text-gray-400 hover:text-gray-200">
        <RefreshCw className="w-3.5 h-3.5" /> Aktualisieren
      </button>
      {isLoading ? <p className="text-gray-500">Lade…</p> : (
        <div className="space-y-2">
          {Object.entries(status ?? {}).map(([name, info]) => (
            <div key={name} className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
              <div className="flex items-center gap-3">
                {info.status === 'ok'
                  ? <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                  : <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                }
                <div>
                  <p className="text-sm font-medium text-white">{name}</p>
                  {info.note && <p className="text-xs text-gray-500">{info.note}</p>}
                </div>
              </div>
              <div className="text-right text-xs text-gray-500">
                {info.remaining_today !== undefined && <p>Verbleibend heute: {info.remaining_today}</p>}
                {info.key_2_active && <p className="text-emerald-600">Key 2 aktiv</p>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Weights Tab ───────────────────────────────────────────────────────────────
function WeightsTab() {
  const qc = useQueryClient()
  const { data: cfg } = useQuery({ queryKey: ['config'], queryFn: fetchConfig })
  const [form, setForm] = useState<Partial<AppConfig>>({})

  const current = { ...cfg, ...form }

  const save = useMutation({
    mutationFn: () => updateConfig(form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['config'] }); setForm({}) },
  })

  const f = (k: keyof AppConfig) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm(prev => ({ ...prev, [k]: parseFloat(e.target.value) }))
  }

  const sum = (current.weight_fundamental ?? 0) + (current.weight_technical ?? 0) + (current.weight_sentiment ?? 0)

  return (
    <div className="space-y-4 max-w-md">
      <div className="space-y-3">
        {[
          { label: 'Fundamental-Gewichtung (%)', key: 'weight_fundamental' as const },
          { label: 'Technisch-Gewichtung (%)', key: 'weight_technical' as const },
          { label: 'Sentiment-Gewichtung (%)', key: 'weight_sentiment' as const },
        ].map(({ label, key }) => (
          <div key={key}>
            <label className="text-xs text-gray-500 block mb-1">{label}</label>
            <input type="number" min={0} max={100}
              value={(current[key] as number | undefined) ?? ''}
              onChange={f(key)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
            />
          </div>
        ))}
        <p className={`text-xs ${sum === 100 ? 'text-emerald-400' : 'text-red-400'}`}>
          Summe: {sum.toFixed(0)}% {sum !== 100 && '(muss 100 ergeben)'}
        </p>
      </div>
      <button
        onClick={() => save.mutate()}
        disabled={sum !== 100 || Object.keys(form).length === 0 || save.isPending}
        className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-sm rounded-lg"
      >
        {save.isPending ? 'Speichern…' : 'Speichern'}
      </button>
      {save.isError && <p className="text-xs text-red-400">{String(save.error)}</p>}
    </div>
  )
}

// ── Scan Config Tab ───────────────────────────────────────────────────────────
function ScanConfigTab() {
  const qc = useQueryClient()
  const { data: cfg } = useQuery({ queryKey: ['config'], queryFn: fetchConfig })
  const { data: schedule } = useQuery({ queryKey: ['scanSchedule'], queryFn: fetchScanSchedule })
  const [form, setForm] = useState<Partial<AppConfig>>({})

  const current = { ...cfg, ...form }

  const save = useMutation({
    mutationFn: () => updateConfig(form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['config'] }); setForm({}) },
  })

  const f = (k: keyof AppConfig) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm(prev => ({ ...prev, [k]: parseFloat(e.target.value) }))
  }

  const fields: { label: string; key: keyof AppConfig; step?: string; hint?: string }[] = [
    { label: 'Zone-1-Mindestscore', key: 'zone1_min_score', hint: '≥ 76' },
    { label: 'Zone-2-Mindestscore', key: 'zone2_min_score', hint: '≥ 61' },
    { label: 'Zone-3-Mindestscore', key: 'zone3_min_score', hint: '≥ 41' },
  ]

  return (
    <div className="space-y-6">
      {schedule && (
        <div className="bg-gray-800/50 rounded-xl p-4 space-y-2">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Scan-Zeitplan</p>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><span className="text-gray-500">Uhrzeit (UTC):</span> <span className="text-white">{schedule.scan_time_utc}</span></div>
            <div><span className="text-gray-500">Zone-4-Batch:</span> <span className="text-white">{schedule.zone4_batch_size}</span></div>
            <div><span className="text-gray-500">Zone-4-Ticker:</span> <span className="text-white">{schedule.zone4_active_tickers}</span></div>
            <div><span className="text-gray-500">Zyklus-Tage:</span> <span className="text-white">{schedule.zone4_cycle_days ?? '–'}</span></div>
            <div><span className="text-gray-500">Letzter Scan:</span> <span className="text-white">{schedule.last_scan_completed?.slice(0, 16).replace('T', ' ') ?? '–'} UTC</span></div>
            <div><span className="text-gray-500">Dauer:</span> <span className="text-white">{schedule.last_duration_sec !== null ? `${schedule.last_duration_sec}s` : '–'}</span></div>
          </div>
        </div>
      )}
      <div className="space-y-3 max-w-sm">
        {fields.map(({ label, key, step, hint }) => (
          <div key={key}>
            <label className="text-xs text-gray-500 block mb-1">{label} {hint && <span className="text-gray-600">({hint})</span>}</label>
            <input type="number" step={step ?? '1'}
              value={(current[key] as number | undefined) ?? ''}
              onChange={f(key)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
            />
          </div>
        ))}
        <button
          onClick={() => save.mutate()}
          disabled={Object.keys(form).length === 0 || save.isPending}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-sm rounded-lg"
        >
          {save.isPending ? 'Speichern…' : 'Speichern'}
        </button>
      </div>
    </div>
  )
}

// ── Alerts Tab ────────────────────────────────────────────────────────────────
function AlertsTab() {
  const qc = useQueryClient()
  const { data: cfg } = useQuery({ queryKey: ['config'], queryFn: fetchConfig })
  const [form, setForm] = useState<Partial<AppConfig>>({})

  const current = { ...cfg, ...form }

  const save = useMutation({
    mutationFn: () => updateConfig(form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['config'] }); setForm({}) },
  })

  const f = (k: keyof AppConfig) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm(prev => ({ ...prev, [k]: parseFloat(e.target.value) }))
  }

  const fields: { label: string; key: keyof AppConfig; step?: string; hint?: string }[] = [
    { label: 'Δ1T-Alarm ab (Punkte)', key: 'alert_delta_1d', hint: 'z.B. 15' },
    { label: 'Exit: Score-Einbruch (Punkte)', key: 'exit_score_drop', hint: 'Differenz zum Entry-Score' },
    { label: 'Exit: KO-Abstand Minimum (%)', key: 'exit_ko_distance', step: '0.1' },
    { label: 'Exit: Restlaufzeit Warnung (Wochen)', key: 'exit_expiry_weeks' },
    { label: 'Exit: Sentiment Bull-Ratio Min.', key: 'exit_bull_ratio', step: '0.1', hint: '0.0–1.0' },
  ]

  return (
    <div className="space-y-4 max-w-sm">
      <p className="text-xs text-gray-500">Telegram-Bot: noch nicht konfiguriert (.env)</p>
      <div className="space-y-3">
        {fields.map(({ label, key, step, hint }) => (
          <div key={key}>
            <label className="text-xs text-gray-500 block mb-1">{label} {hint && <span className="text-gray-600">({hint})</span>}</label>
            <input type="number" step={step ?? '1'}
              value={(current[key] as number | undefined) ?? ''}
              onChange={f(key)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
            />
          </div>
        ))}
      </div>
      <button
        onClick={() => save.mutate()}
        disabled={Object.keys(form).length === 0 || save.isPending}
        className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-sm rounded-lg"
      >
        {save.isPending ? 'Speichern…' : 'Speichern'}
      </button>
      {save.isError && <p className="text-xs text-red-400">{String(save.error)}</p>}
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────
export default function Config() {
  const [tab, setTab] = useState<Tab>('universe')

  return (
    <div>
      <PageHeader title="Einstellungen" />

      <div className="p-6 space-y-4">
        <div className="flex gap-1 border-b border-gray-800 pb-0">
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`px-4 py-2 text-sm font-medium transition-colors rounded-t-lg -mb-px ${
                tab === t.id
                  ? 'text-white border-b-2 border-emerald-500'
                  : 'text-gray-500 hover:text-gray-300'
              }`}>
              {t.label}
            </button>
          ))}
        </div>

        <Card>
          {tab === 'universe' && <UniverseTab />}
          {tab === 'api' && <ApiStatusTab />}
          {tab === 'weights' && <WeightsTab />}
          {tab === 'scan' && <ScanConfigTab />}
          {tab === 'alerts' && <AlertsTab />}
        </Card>
      </div>
    </div>
  )
}
