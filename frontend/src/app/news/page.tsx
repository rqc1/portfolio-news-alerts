"use client";

import { useState } from "react";
import {
  Globe,
  Rss,
  Search,
  TrendingUp,
  Newspaper,
  Loader2,
} from "lucide-react";
import {
  ingestAll,
  ingestRss,
  ingestCnmv,
  ingestNewsApi,
  ingestAlphaVantage,
  getNews,
} from "@/lib/api";
import type { NewsItem, IngestResult } from "@/lib/types";
import {
  PageHeader,
  Section,
  Card,
  EmptyState,
  Button,
  Input,
  Skeleton,
} from "@/components/ui";
import { NewsCard } from "@/components/news/news-card";

type Tab = "ingest" | "explore";

function TabNav({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  const tabs: { id: Tab; label: string }[] = [
    { id: "ingest", label: "Ingestar Fuentes" },
    { id: "explore", label: "Explorar Noticias" },
  ];
  return (
    <div className="mb-6 flex gap-1 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-1">
      {tabs.map(({ id, label }) => (
        <button
          key={id}
          onClick={() => onChange(id)}
          className={`rounded-[var(--radius-sm)] px-4 py-2 text-[12px] font-semibold transition-colors ${
            active === id
              ? "bg-[var(--accent-muted)] text-[var(--accent-hover)]"
              : "text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

/* ── Source Card ───────────────────────────────────────────────────────── */

function SourceCard({
  icon,
  name,
  desc,
  children,
}: {
  icon: React.ReactNode;
  name: string;
  desc: string;
  children: React.ReactNode;
}) {
  return (
    <Card hover>
      <div className="mb-3 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-md)] bg-[var(--accent-muted)] text-[var(--accent)]">
          {icon}
        </div>
        <div>
          <p className="text-[13px] font-bold text-[var(--text-primary)]">{name}</p>
          <p className="text-[11px] text-[var(--text-muted)]">{desc}</p>
        </div>
      </div>
      {children}
    </Card>
  );
}

/* ── Ingest Panel ─────────────────────────────────────────────────────── */

function IngestPanel() {
  const [loading, setLoading] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [newsapiQuery, setNewsapiQuery] = useState("");
  const [avTickers, setAvTickers] = useState("");

  async function run(key: string, fn: () => Promise<IngestResult>) {
    setLoading(key);
    setResult(null);
    try {
      const res = await fn();
      const count = res.count ?? Object.values(res.stats ?? {}).reduce((a, b) => a + b, 0);
      setResult(`✓ ${count} noticias ingestadas`);
    } catch (e) {
      setResult(`Error: ${e instanceof Error ? e.message : "desconocido"}`);
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="space-y-6">
      <Section label="Sin API Key" title="Fuentes Primarias" />
      <div className="grid gap-4 md:grid-cols-3">
        <SourceCard
          icon={<Globe className="h-5 w-5" />}
          name="Todas las fuentes"
          desc="RSS + SEC EDGAR + CNMV"
        >
          <Button
            variant="primary"
            size="sm"
            className="w-full"
            loading={loading === "all"}
            onClick={() => run("all", ingestAll)}
          >
            Ingestar todo
          </Button>
        </SourceCard>

        <SourceCard
          icon={<Rss className="h-5 w-5" />}
          name="RSS Feeds"
          desc="22 feeds · Finanzas, macro, cyber"
        >
          <Button
            size="sm"
            className="w-full"
            loading={loading === "rss"}
            onClick={() => run("rss", ingestRss)}
          >
            Solo RSS
          </Button>
        </SourceCard>

        <SourceCard
          icon={<span className="text-lg">🇪🇸</span>}
          name="CNMV"
          desc="Hechos relevantes · Info privilegiada"
        >
          <Button
            size="sm"
            className="w-full"
            loading={loading === "cnmv"}
            onClick={() => run("cnmv", ingestCnmv)}
          >
            Solo CNMV
          </Button>
        </SourceCard>
      </div>

      <Section label="Con API Key" title="Fuentes Enriquecidas" />
      <div className="grid gap-4 md:grid-cols-2">
        <SourceCard
          icon={<Search className="h-5 w-5" />}
          name="NewsAPI.org"
          desc="+150k fuentes globales · Texto completo"
        >
          <div className="space-y-2">
            <Input
              placeholder="Apple earnings OR Tesla regulation"
              value={newsapiQuery}
              onChange={(e) => setNewsapiQuery(e.target.value)}
            />
            <Button
              size="sm"
              className="w-full"
              loading={loading === "newsapi"}
              onClick={() => {
                if (newsapiQuery.trim()) {
                  run("newsapi", () => ingestNewsApi(newsapiQuery.trim()));
                }
              }}
            >
              Buscar NewsAPI
            </Button>
          </div>
        </SourceCard>

        <SourceCard
          icon={<TrendingUp className="h-5 w-5" />}
          name="Alpha Vantage"
          desc="Tickers anotados · Sentiment pre-calculado"
        >
          <div className="space-y-2">
            <Input
              placeholder="AAPL,MSFT,TSLA"
              value={avTickers}
              onChange={(e) => setAvTickers(e.target.value)}
            />
            <Button
              size="sm"
              className="w-full"
              loading={loading === "av"}
              onClick={() => {
                if (avTickers.trim()) {
                  run("av", () => ingestAlphaVantage(avTickers.trim()));
                }
              }}
            >
              Buscar Alpha Vantage
            </Button>
          </div>
        </SourceCard>
      </div>

      {result && (
        <p
          className={`text-[12px] font-medium ${
            result.startsWith("✓")
              ? "text-[var(--color-success)]"
              : "text-[var(--color-danger)]"
          }`}
        >
          {result}
        </p>
      )}
    </div>
  );
}

/* ── Explore Panel ────────────────────────────────────────────────────── */

function ExplorePanel() {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [limit, setLimit] = useState(50);
  const [loaded, setLoaded] = useState(false);

  async function loadNews() {
    setLoading(true);
    try {
      const data = await getNews(limit);
      setNews(data);
      setLoaded(true);
    } catch {
      /* empty */
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <Section label="Explorar" title="Noticias almacenadas" />

      <div className="flex items-end gap-4">
        <div className="flex items-center gap-3">
          <label className="text-[11px] font-semibold uppercase tracking-[0.06em] text-[var(--text-muted)]">
            Límite
          </label>
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2 text-[12px] text-[var(--text-primary)] outline-none"
          >
            {[20, 50, 100, 200].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>
        <Button onClick={loadNews} loading={loading}>
          {loaded ? "Refrescar" : "Cargar noticias"}
        </Button>
      </div>

      {loading && !loaded ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-[200px]" />
          ))}
        </div>
      ) : news.length > 0 ? (
        <>
          <p className="text-[12px] text-[var(--text-muted)]">
            Mostrando <span className="font-semibold text-[var(--text-secondary)]">{news.length}</span> noticias
          </p>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {news.map((item, i) => (
              <NewsCard key={item._id} item={item} index={i} />
            ))}
          </div>
        </>
      ) : loaded ? (
        <EmptyState
          icon={<Newspaper className="h-8 w-8" />}
          title="Sin noticias"
          description="Usa la pestaña Ingestar para adquirir noticias desde las fuentes configuradas."
        />
      ) : null}
    </div>
  );
}

/* ── Main Page ────────────────────────────────────────────────────────── */

export default function NewsPage() {
  const [tab, setTab] = useState<Tab>("ingest");

  return (
    <>
      <PageHeader
        title="Centro de Noticias"
        subtitle="Adquiere, explora y monitoriza noticias financieras globales"
      />
      <TabNav active={tab} onChange={setTab} />
      {tab === "ingest" ? <IngestPanel /> : <ExplorePanel />}
    </>
  );
}
