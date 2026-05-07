import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, XCircle, RefreshCw, Plus, Trash2, AlertTriangle, Info } from 'lucide-react'
import {
  fetchConfig, updateConfig, fetchApiStatus, fetchScanSchedule,
  fetchUniverse, searchUniverse, addTicker, deactivateTicker, refreshUniverse,
  fetchLogs, clearLogs,
} from '../api/client'
import type { AppConfig, LogEntry } from '../types/api'
import Card from '../components/Card'
import PageHeader from '../components/PageHeader'

type Tab = 'universe' | 'api' | 'weights' | 'scan' | 'alerts' | 'logs'

const TABS: { id: Tab; label: string }[] = [
  { id: 'universe', label: 'Universum' },
  { id: 'api', label: 'API-Status' },
  { id: 'weights', label: 'Gewichtungen' },
  { id: 'scan', label: 'Scan-Config' },
  { id: 'alerts', label: 'Alerts' },
  { id: 'logs',    label: 'Logs' },
]

// ── Universe Tab ─────────────────────────────────────────────────────────────
function UniverseTab() {
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [newTicker, setNewTicker] = useState('')
  const [searchResults, setSearchResults] = useState<Awaited<ReturnType<typeof searchUniverse>>>([])

  const { data: universe = [], isLoading } = useQuery({
    queryKey: ['universe'], queryFn: () => fetchUniverse({ active_only: true }),
  })

  const doSearch = useMutation({
    mutationFn: () => searchUniverse(search),
    onSuccess: data => setSearchResults(data),
  })

  const [addError, setAddError] = useState<string | null>(null)

  const add = useMutation({
    mutationFn: () => addTicker(newTicker.toUpperCase().trim()),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['universe'] }); setNewTicker(''); setAddError(null) },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setAddError(detail ?? 'Fehler beim Hinzufügen')
    },
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
              value={newTicker}
              onChange={e => { setNewTicker(e.target.value.toUpperCase()); setAddError(null) }}
              onKeyDown={e => { if (e.key === 'Enter' && newTicker && !add.isPending) add.mutate() }}
              placeholder="TSLA"
              className={`flex-1 bg-gray-800 border rounded-lg px-3 py-2 text-sm text-white focus:outline-none ${addError ? 'border-red-500 focus:border-red-500' : 'border-gray-700 focus:border-emerald-500'}`}
            />
            <button onClick={() => add.mutate()} disabled={!newTicker || add.isPending}
              className="px-3 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg">
              {add.isPending ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            </button>
          </div>
          {addError && <p className="text-xs text-red-400 mt-1">{addError}</p>}
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
            <div><span className="text-gray-500">Letzter Scan:</span> <span className="text-white">{schedule.last_scan_completed ? new Date(schedule.last_scan_completed + 'Z').toLocaleString('de-DE', { timeZone: 'Europe/Berlin', day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' }) : '–'}</span></div>
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

// ── Logs Tab ──────────────────────────────────────────────────────────────────
const LEVEL_COLORS: Record<string, string> = {
  DEBUG:    'text-gray-500',
  INFO:     'text-gray-300',
  WARNING:  'text-yellow-400',
  ERROR:    'text-red-400',
  CRITICAL: 'text-red-300',
}

const LEVEL_BG: Record<string, string> = {
  DEBUG:    '',
  INFO:     '',
  WARNING:  'bg-yellow-900/10',
  ERROR:    'bg-red-900/15',
  CRITICAL: 'bg-red-900/25',
}

function toDeTime(utcIso: string): string {
  const d = new Date(utcIso.endsWith('Z') ? utcIso : utcIso + 'Z')
  return d.toLocaleTimeString('de-DE', { timeZone: 'Europe/Berlin', hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function LogRow({ entry }: { entry: LogEntry }) {
  const [expanded, setExpanded] = useState(false)
  const isMultiline = entry.message.includes('\n')
  const preview = isMultiline ? entry.message.split('\n')[0] : entry.message

  return (
    <div
      className={`px-3 py-1.5 border-b border-gray-800/40 ${LEVEL_BG[entry.level] ?? ''} ${isMultiline ? 'cursor-pointer hover:bg-gray-800/20' : ''}`}
      onClick={() => isMultiline && setExpanded(e => !e)}
    >
      <div className="flex items-start gap-3 min-w-0">
        <span className="text-gray-600 font-mono text-xs flex-shrink-0 mt-0.5">
          {toDeTime(entry.timestamp)}
        </span>
        <span className={`text-xs font-semibold w-14 flex-shrink-0 ${LEVEL_COLORS[entry.level]}`}>
          {entry.level}
        </span>
        <span className="text-gray-600 text-xs w-36 flex-shrink-0 truncate hidden lg:block">
          {entry.logger}
        </span>
        <span className={`text-xs font-mono flex-1 min-w-0 ${LEVEL_COLORS[entry.level]} ${expanded ? 'whitespace-pre-wrap break-all' : 'truncate'}`}>
          {expanded ? entry.message : preview}
          {isMultiline && !expanded && <span className="text-gray-600 ml-1">▸</span>}
        </span>
      </div>
    </div>
  )
}

function LogsTab() {
  const qc = useQueryClient()
  const [level, setLevel] = useState<string>('INFO')
  const [module, setModule] = useState('')
  const [autoRefresh, setAutoRefresh] = useState(false)

  const { data, isLoading, dataUpdatedAt } = useQuery({
    queryKey: ['logs', level, module],
    queryFn: () => fetchLogs({ level: level || undefined, module: module || undefined, limit: 200 }),
    refetchInterval: autoRefresh ? 5_000 : false,
  })

  const clear = useMutation({
    mutationFn: clearLogs,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['logs'] }),
  })

  const LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR']

  return (
    <div className="space-y-3">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Level-Filter */}
        <div className="flex gap-1">
          {LEVELS.map(l => (
            <button key={l} onClick={() => setLevel(l)}
              className={`px-2.5 py-1 text-xs rounded font-medium transition-colors ${
                level === l
                  ? 'bg-emerald-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}>
              {l}
            </button>
          ))}
        </div>

        {/* Modul-Filter */}
        <input
          value={module} onChange={e => setModule(e.target.value)}
          placeholder="Modul-Filter (z.B. scoring)"
          className="bg-gray-800 border border-gray-700 rounded px-2.5 py-1 text-xs text-white focus:outline-none focus:border-emerald-500 w-44"
        />

        {/* Auto-Refresh */}
        <label className="flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer select-none">
          <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)}
            className="accent-emerald-500" />
          Auto-Refresh (5s)
        </label>

        <button onClick={() => qc.invalidateQueries({ queryKey: ['logs'] })}
          className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-200 ml-auto">
          <RefreshCw className="w-3 h-3" />
          Aktualisieren
        </button>
        <button onClick={() => clear.mutate()} disabled={clear.isPending}
          className="flex items-center gap-1.5 text-xs text-red-600 hover:text-red-400 disabled:opacity-50">
          <Trash2 className="w-3 h-3" />
          Leeren
        </button>
      </div>

      {/* Zusammenfassung */}
      {data && (
        <div className="flex gap-4 text-xs text-gray-500">
          <span>{data.total_returned} Einträge</span>
          {data.error_count > 0 && (
            <span className="flex items-center gap-1 text-red-400">
              <AlertTriangle className="w-3 h-3" /> {data.error_count} Fehler
            </span>
          )}
          {data.warning_count > 0 && (
            <span className="flex items-center gap-1 text-yellow-400">
              <Info className="w-3 h-3" /> {data.warning_count} Warnungen
            </span>
          )}
          {autoRefresh && (
            <span className="text-gray-600">
              Stand: {new Date(dataUpdatedAt).toLocaleTimeString('de-DE')}
            </span>
          )}
        </div>
      )}

      {/* Log-Einträge */}
      <div className="bg-gray-950 border border-gray-800 rounded-xl overflow-hidden max-h-[500px] overflow-y-auto font-mono">
        {isLoading ? (
          <p className="p-4 text-xs text-gray-500">Lade…</p>
        ) : !data?.entries.length ? (
          <p className="p-4 text-xs text-gray-500">Keine Einträge für diesen Filter</p>
        ) : (
          data.entries.map((entry, i) => <LogRow key={i} entry={entry} />)
        )}
      </div>
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
        <div className="flex overflow-x-auto gap-1 border-b border-gray-800 -mx-4 sm:-mx-6 px-4 sm:px-6 scrollbar-none">
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`flex-shrink-0 px-4 py-2 text-sm font-medium transition-colors rounded-t-lg -mb-px ${
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
          {tab === 'logs'   && <LogsTab />}
        </Card>
      </div>
    </div>
  )
}
