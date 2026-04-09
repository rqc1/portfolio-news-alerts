import type {
  Portfolio,
  Alert,
  AlertStats,
  BatchResult,
  IngestResult,
  ProcessResult,
  NewsItem,
} from "@/lib/types";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/* ── Generic fetcher ─────────────────────────────────────────────────── */

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${BASE}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(res.status, body || res.statusText);
  }
  return res.json() as Promise<T>;
}

function qs(params: Record<string, string | number | undefined | null>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v != null && v !== "") sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

/* ── Health ───────────────────────────────────────────────────────────── */

export async function checkHealth(): Promise<boolean> {
  try {
    await request<{ status: string }>("/health");
    return true;
  } catch {
    return false;
  }
}

/* ── Portfolio ────────────────────────────────────────────────────────── */

export async function getPortfolios(userId: string): Promise<Portfolio[]> {
  return request<Portfolio[]>(`/api/portfolios${qs({ user_id: userId })}`);
}

export async function getPortfolio(id: string): Promise<Portfolio> {
  return request<Portfolio>(`/api/portfolios/${id}`);
}

export async function createPortfolio(userId: string, name: string): Promise<{ portfolio_id: string }> {
  return request<{ portfolio_id: string }>("/api/portfolios", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, name }),
  });
}

export async function addAsset(
  portfolioId: string,
  asset: {
    ticker: string;
    name: string;
    sector?: string;
    country?: string;
    weight: number;
    aliases: string[];
  },
): Promise<{ status: string }> {
  return request(`/api/portfolios/${portfolioId}/assets`, {
    method: "POST",
    body: JSON.stringify(asset),
  });
}

export async function removeAsset(
  portfolioId: string,
  ticker: string,
): Promise<{ status: string }> {
  return request(`/api/portfolios/${portfolioId}/assets/${ticker}`, {
    method: "DELETE",
  });
}

/* ── Ingestion ────────────────────────────────────────────────────────── */

export async function ingestAll(): Promise<IngestResult> {
  return request("/api/ingest", { method: "POST" });
}

export async function ingestRss(): Promise<IngestResult> {
  return request("/api/ingest/rss", { method: "POST" });
}

export async function ingestCnmv(): Promise<IngestResult> {
  return request("/api/ingest/cnmv", { method: "POST" });
}

export async function ingestNewsApi(query: string): Promise<IngestResult> {
  return request(`/api/ingest/newsapi${qs({ query })}`, { method: "POST" });
}

export async function ingestAlphaVantage(tickers: string): Promise<IngestResult> {
  return request(`/api/ingest/alphavantage${qs({ tickers })}`, { method: "POST" });
}

export async function getNews(limit = 50): Promise<NewsItem[]> {
  return request<NewsItem[]>(`/api/news${qs({ limit })}`);
}

/* ── Alerts ───────────────────────────────────────────────────────────── */

export async function getAlerts(portfolioId?: string, limit = 50): Promise<Alert[]> {
  return request<Alert[]>(`/api/alerts${qs({ portfolio_id: portfolioId, limit })}`);
}

export async function getAlertStats(portfolioId?: string): Promise<AlertStats> {
  return request<AlertStats>(`/api/alerts/stats${qs({ portfolio_id: portfolioId })}`);
}

export async function processBatch(portfolioId: string, limit = 50): Promise<BatchResult> {
  return request<BatchResult>(
    `/api/alerts/process-batch/${portfolioId}${qs({ limit })}`,
    { method: "POST" },
  );
}

export async function processNews(data: {
  title: string;
  summary?: string;
  content?: string;
  url?: string;
  source?: string;
  portfolio_id: string;
}): Promise<ProcessResult> {
  return request<ProcessResult>("/api/alerts/process", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
