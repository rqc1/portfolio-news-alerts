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

export type Direction = Alert["direction"];
