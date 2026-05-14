/* ── Domain types matching the FastAPI backend ── */

export interface Asset {
  ticker: string;
  name: string;
  isin?: string | null;
  sector?: string | null;
  industry?: string | null;
  country?: string | null;
  weight: number;
  aliases: string[];
}

export interface Portfolio {
  _id: string;
  user_id: string;
  name: string;
  assets: Asset[];
  created_at?: string;
  updated_at?: string;
}

export interface NewsItem {
  _id: string;
  title: string;
  summary: string;
  content: string;
  url: string;
  source: string;
  source_type: string;
  published_at: string;
  language: string;
  author?: string | null;
  entities_raw?: string[];
  metadata?: Record<string, unknown>;
  ingested_at?: string;
}

export interface Alert {
  _id: string;
  portfolio_id: string;
  news_title: string;
  news_url: string;
  news_source: string;
  event_type: string;
  direction: "bajista" | "alcista" | "neutral";
  severity: number;
  severity_label?: string;
  confidence: number;
  matched_assets: string[];
  explanation: string;
  is_duplicate?: boolean;
  created_at: string;
}

export interface AlertStats {
  total: number;
  avg_severity: number;
  avg_confidence: number;
}

export interface BatchResult {
  processed: number;
  alerts_generated: number;
  duplicates: number;
  discarded: number;
}

export interface IngestResult {
  status: string;
  count?: number;
  stats?: Record<string, number>;
}

export interface ProcessResult {
  status: "alert_generated" | "no_alert";
  alert?: Alert;
  reason?: string;
}

/* ── Advisor types ── */

export interface QuestionOption {
  id: string;
  text: string;
  score: number;
}

export interface Question {
  id: string;
  category: string;
  text: string;
  description: string;
  options: QuestionOption[];
}

export interface AllocationSlice {
  category: string;
  current_pct: number;
  ideal_pct: number;
  diff_pct: number;
  status: "sobreexpuesto" | "infraexpuesto" | "equilibrado";
}

export interface PortfolioAnalysis {
  concentration_risk: number;
  sector_allocation: AllocationSlice[];
  geography_allocation: AllocationSlice[];
  diversification_score: number;
  risk_alignment_score: number;
  warnings: string[];
}

export interface Recommendation {
  action: string;
  ticker?: string | null;
  asset_name: string;
  sector: string;
  reason: string;
  priority: "alta" | "media" | "baja";
  current_weight?: number | null;
  suggested_weight?: number | null;
}

export interface InvestorProfile {
  user_id: string;
  portfolio_id: string;
  risk_score: number;
  risk_profile: string;
  horizon: string;
  goal: string;
  knowledge: string;
  esg_preference: boolean;
  sector_preferences: string[];
  loss_tolerance_pct: number;
}

export interface AdvisorReport {
  _id?: string;
  profile: InvestorProfile;
  analysis: PortfolioAnalysis;
  recommendations: Recommendation[];
  llm_summary: string;
  created_at?: string;
}

/* ── Market & Analytics types ── */

export interface AssetLookup {
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  country: string;
  currency: string;
  market_cap: number | null;
  isin: string | null;
  exchange: string;
  description: string;
  aliases: string[];
}

export interface PriceSnapshot {
  ticker: string;
  price: number;
  currency: string;
  change_pct: number;
  day_high: number | null;
  day_low: number | null;
  volume: number | null;
  timestamp: string;
}

export interface AssetPerformance {
  ticker: string;
  name: string;
  weight: number;
  return_pct: number;
  volatility_pct: number;
  sharpe: number;
  contribution_pct: number;
}

export interface PortfolioMetrics {
  total_return_pct: number;
  annualized_return_pct: number;
  ytd_return_pct: number;
  volatility_pct: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  calmar_ratio: number;
  max_drawdown_pct: number;
  var_95_pct: number;
  cvar_95_pct: number;
  best_day_pct: number;
  worst_day_pct: number;
  win_rate_pct: number;
  benchmark_ticker: string;
  benchmark_return_pct: number;
  alpha_pct: number;
  beta: number;
  period: string;
  data_points: number;
}

export interface PortfolioAnalyticsResult {
  metrics: PortfolioMetrics;
  asset_performance: AssetPerformance[];
  return_series: { date: string; value: number }[];
}

export type Direction = Alert["direction"];
