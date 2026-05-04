// TypeScript-Typen – spiegeln backend/schemas.py wider

export interface ScoreBreakdown {
  pe_vs_sector: number
  eps_beat_streak: number
  revenue_growth: number
  fcf_score: number
  debt_equity: number
  insider_net: number
  earnings_proximity: number
  vcp_score: number
  volume_contraction: number
  price_vs_resistance: number
  rsi_zone: number
  relative_strength: number
  macd_signal: number
  bollinger_squeeze: number
  news_sentiment: number
  stocktwits_ratio: number
  reddit_momentum: number
  analyst_delta: number
  sentiment_suppressed: boolean
}

export interface OptionsRec {
  direction: string
  leverage_min: number
  leverage_max: number
  duration_weeks: number
  ko_distance_pct: number
  entry_trigger: number | null
  stop_loss: number | null
  base_price_at_rec: number | null
  atr_at_rec: number | null
}

export interface StockScore {
  ticker: string
  name: string | null
  sector: string | null
  total_score: number
  l1_fundamentals: number
  l2_technicals: number
  l3_sentiment: number
  zone: number
  delta_1d: number | null
  delta_7d: number | null
  delta_30d: number | null
  strongest_signal: string | null
  next_catalyst: string | null
  catalyst_days: number | null
  score_date: string
  close_price: number | null
  currency: string | null
  breakdown: ScoreBreakdown | null
  options_rec: OptionsRec | null
}

export interface ScoreHistoryPoint {
  score_date: string
  total_score: number
  zone: number
}

// Portfolio
export interface ExitSignal {
  id: number
  position_id: number
  ticker: string
  signal_type: string
  severity: string
  trigger_value: number | null
  message: string | null
  recommendation: string | null
  current_pnl_pct: number | null
  is_acknowledged: boolean
  signal_date: string
}

export interface Position {
  id: number
  ticker: string
  name: string | null
  product_type: string
  direction: string
  isin: string | null
  quantity: number
  entry_price: number
  entry_date: string
  entry_score: number | null
  entry_zone: number | null
  ko_level: number | null
  expiry_date: string | null
  leverage: number | null
  underlying_at_entry: number | null
  is_open: boolean
  current_score: number | null
  current_zone: number | null
  current_underlying: number | null
  ko_distance_pct: number | null
  days_to_expiry: number | null
  unrealized_pnl_pct: number | null
  status: string | null
  exit_signals: ExitSignal[]
}

export interface PositionCreate {
  ticker: string
  product_type?: string
  direction?: string
  isin?: string
  quantity: number
  entry_price: number
  entry_date: string
  ko_level?: number
  expiry_date?: string
  leverage?: number
  underlying_at_entry?: number
  notes?: string
}

export interface Transaction {
  id: number
  position_id: number | null
  ticker: string
  tx_type: string
  quantity: number
  price: number
  tx_date: string
  score_at_tx: number | null
  pnl_abs: number | null
  pnl_pct: number | null
  hold_days: number | null
  notes: string | null
}

// Dashboard
export interface Dashboard {
  total_pnl_abs: number
  total_pnl_pct: number | null
  open_positions: number
  top_signals: StockScore[]
  exit_alerts: ExitSignal[]
}

// History
export interface SignalQuality {
  signal_type: string
  total_trades: number
  profitable: number
  win_rate_pct: number
  avg_pnl_pct: number
}

export interface HistorySummary {
  total_trades: number
  profitable: number
  win_rate_pct: number | null
  avg_pnl_pct: number | null
  avg_hold_days: number | null
  total_pnl_abs: number
}

// Config
export interface AppConfig {
  weight_fundamental: number
  weight_technical: number
  weight_sentiment: number
  zone1_min_score: number
  zone2_min_score: number
  zone3_min_score: number
  alert_delta_1d: number
  exit_score_drop: number
  exit_ko_distance: number
  exit_expiry_weeks: number
  exit_bull_ratio: number
}

export interface ApiStatus {
  [service: string]: {
    status: 'ok' | 'missing'
    note?: string
    remaining_today?: number
    key_2_active?: boolean
  }
}

export interface ScanSchedule {
  scan_time_utc: string
  zone4_batch_size: number
  zone4_active_tickers: number
  zone4_cycle_days: number | null
  last_scan_completed: string | null
  last_duration_sec: number | null
  scan_running: boolean
}

// Scan
export interface ScanStatus {
  running: boolean
  started_at: string | null
  progress: number
  total: number
  current_ticker: string | null
  last_completed: string | null
  last_duration_sec: number | null
  error: string | null
  tickers_failed: string[]
}

// Universe
export interface UniverseTicker {
  ticker: string
  name: string | null
  sector: string | null
  industry: string | null
  exchange: string | null
  universe_source: string | null
  is_active: boolean
  added_at: string | null
}

export interface ZoneSummary {
  date: string | null
  total: number
  zones: Record<number, number>
}

// Logs
export interface LogEntry {
  timestamp: string
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'
  logger: string
  message: string
}

export interface LogResponse {
  total_returned: number
  error_count: number
  warning_count: number
  entries: LogEntry[]
}

// Backtesting
export interface BacktestDataPoint {
  date: string
  close: number
  score: number
  zone: number
  delta_1d: number | null
  delta_7d: number | null
}

export interface BacktestSignalEvent {
  date: string
  event_type: string
  from_zone: number | null
  to_zone: number | null
  score: number
  delta_1d: number | null
  delta_7d: number | null
  description: string
}

export interface BacktestSummary {
  total_trading_days: number
  total_signals: number
  zone1_entries: number
  zone1_days: number
  zone1_days_pct: number
  max_score: number | null
  min_score: number | null
  avg_score: number | null
  delta_spikes: number
  streaks_7d: number
  zone_changes: number
}

export interface BacktestResult {
  ticker: string
  from_date: string
  to_date: string
  price_data: BacktestDataPoint[]
  signals: BacktestSignalEvent[]
  total_signals: number
  zone1_entries: number
  summary: BacktestSummary | null
}
