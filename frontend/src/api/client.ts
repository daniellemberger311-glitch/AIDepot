import axios from 'axios'
import type {
  StockScore, ScoreHistoryPoint, Dashboard, Position, PositionCreate,
  Transaction, SignalQuality, HistorySummary, AppConfig, ApiStatus,
  ScanStatus, ScanSchedule, UniverseTicker, ZoneSummary,
  BacktestResult, LogResponse,
} from '../types/api'

const api = axios.create({ baseURL: '/api', timeout: 30_000 })

// ── Watchlist ──────────────────────────────────────────────────────────────
export const fetchWatchlist = (params?: {
  zone?: number; sort?: string; limit?: number; breakdown?: boolean
}) => api.get<StockScore[]>('/watchlist', { params }).then(r => r.data)

export const fetchZoneSummary = () =>
  api.get<ZoneSummary>('/watchlist/zones/summary').then(r => r.data)

// ── Signale ────────────────────────────────────────────────────────────────
export const fetchSignal = (ticker: string) =>
  api.get<StockScore>(`/signals/${ticker}`).then(r => r.data)

export const fetchSignalHistory = (ticker: string, days = 30) =>
  api.get<ScoreHistoryPoint[]>(`/signals/${ticker}/history`, { params: { days } }).then(r => r.data)

// ── Dashboard ──────────────────────────────────────────────────────────────
export const fetchDashboard = () =>
  api.get<Dashboard>('/dashboard').then(r => r.data)

// ── Portfolio ──────────────────────────────────────────────────────────────
export const fetchPortfolio = (includeClosed = false) =>
  api.get<Position[]>('/portfolio', { params: { include_closed: includeClosed } }).then(r => r.data)

export const fetchPosition = (id: number) =>
  api.get<Position>(`/portfolio/${id}`).then(r => r.data)

export const createPosition = (data: PositionCreate) =>
  api.post<Position>('/portfolio', data).then(r => r.data)

export const closePosition = (id: number, sell_price: number, sell_date: string, notes?: string) =>
  api.put<Position>(`/portfolio/${id}/close`, { sell_price, sell_date, notes }).then(r => r.data)

export const deletePosition = (id: number) =>
  api.delete(`/portfolio/${id}`)

export const acknowledgeSignal = (signalId: number) =>
  api.put(`/portfolio/signals/${signalId}/acknowledge`).then(r => r.data)

export const checkExitSignals = (positionId: number) =>
  api.post(`/portfolio/${positionId}/check-exits`).then(r => r.data)

export const fetchTransactions = (positionId: number) =>
  api.get<Transaction[]>(`/portfolio/${positionId}/transactions`).then(r => r.data)

// ── Historie ───────────────────────────────────────────────────────────────
export const fetchTrades = (params?: { ticker?: string; limit?: number }) =>
  api.get<Transaction[]>('/history/trades', { params }).then(r => r.data)

export const fetchSignalQuality = () =>
  api.get<SignalQuality[]>('/history/signal-quality').then(r => r.data)

export const fetchHistorySummary = () =>
  api.get<HistorySummary>('/history/summary').then(r => r.data)

// ── Scan ───────────────────────────────────────────────────────────────────
export const triggerScan = () =>
  api.post('/scan/trigger').then(r => r.data)

export const fetchScanStatus = () =>
  api.get<ScanStatus>('/scan/status').then(r => r.data)

export const scanTicker = (ticker: string) =>
  api.post(`/scan/ticker/${ticker}`).then(r => r.data)

// ── Konfiguration ──────────────────────────────────────────────────────────
export const fetchConfig = () =>
  api.get<AppConfig>('/config').then(r => r.data)

export const updateConfig = (data: Partial<AppConfig>) =>
  api.put<AppConfig>('/config', data).then(r => r.data)

export const fetchApiStatus = () =>
  api.get<ApiStatus>('/config/status').then(r => r.data)

export const fetchScanSchedule = () =>
  api.get<ScanSchedule>('/config/scan-schedule').then(r => r.data)

// ── Universum ──────────────────────────────────────────────────────────────
export const fetchUniverse = (params?: { active_only?: boolean; source?: string }) =>
  api.get<UniverseTicker[]>('/universe', { params }).then(r => r.data)

export const searchUniverse = (q: string) =>
  api.get<UniverseTicker[]>('/universe/search', { params: { q } }).then(r => r.data)

export const addTicker = (ticker: string, name?: string) =>
  api.post<UniverseTicker>('/universe/add', { ticker, name }).then(r => r.data)

export const deactivateTicker = (ticker: string) =>
  api.delete(`/universe/${ticker}`)

export const refreshUniverse = () =>
  api.post('/universe/refresh').then(r => r.data)

// ── Backtesting ────────────────────────────────────────────────────────────
export const runBacktest = (ticker: string, from_date: string, to_date: string) =>
  api.post<BacktestResult>('/backtest', { ticker, from_date, to_date }).then(r => r.data)

// ── Logs ───────────────────────────────────────────────────────────────────
export const fetchLogs = (params?: { level?: string; module?: string; limit?: number }) =>
  api.get<LogResponse>('/logs', { params }).then(r => r.data)

export const clearLogs = () =>
  api.delete('/logs').then(r => r.data)
