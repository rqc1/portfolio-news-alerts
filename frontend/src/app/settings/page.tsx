"use client";

import {
  Brain,
  Cpu,
  Database,
  Gauge,
  Globe,
  Hash,
  Layers,
  Rss,
  Server,
  Wifi,
  WifiOff,
} from "lucide-react";
import { useApp } from "@/hooks/use-app";
import { PageHeader, Section, Card, Badge } from "@/components/ui";

/* ── Static config mirroring python config.py ─────────────────────────── */

const nlpModels = [
  {
    name: "FinBERT",
    model: "ProsusAI/finbert",
    description: "Sentiment analysis fine-tuned para texto financiero",
    icon: <Brain className="h-4 w-4 text-[var(--accent)]" />,
  },
  {
    name: "spaCy NER",
    model: "en_core_web_sm",
    description: "Named Entity Recognition (ORG, GPE, MONEY…)",
    icon: <Cpu className="h-4 w-4 text-[var(--color-info)]" />,
  },
  {
    name: "Sentence-Transformers",
    model: "all-MiniLM-L6-v2",
    description: "Embeddings para deduplicación semántica (cosine similarity)",
    icon: <Layers className="h-4 w-4 text-[var(--color-success)]" />,
  },
];

const thresholds = [
  { label: "Umbral Relevancia", value: "0.50", description: "Mínimo score de relevancia para continuar el pipeline" },
  { label: "Umbral Severidad", value: "0.30", description: "Mínimo de severidad para emitir alerta" },
  { label: "Similitud Dedup", value: "0.85", description: "Cosine similarity para considerar duplicado" },
  { label: "Máx. Alertas / hora", value: "20", description: "Límite anti-spam por hora" },
];

const eventTaxonomy = [
  "resultados_empresariales",
  "guidance_profit_warning",
  "regulacion",
  "litigio",
  "fusion_adquisicion",
  "ciberincidente",
  "incidencia_operativa",
  "macroeconomia",
  "cadena_suministro",
  "cambio_directivo",
  "dividendo_recompra",
  "otro",
];

const rssSources: Record<string, string[]> = {
  "Noticias generales": [
    "Reuters Business",
    "Yahoo Finance",
    "Financial Times",
    "Seeking Alpha",
    "Investing.com",
  ],
  "Bancos centrales / Macro": [
    "ECB Press",
    "Federal Reserve Press",
    "Bank of England News",
    "IMF News",
  ],
  "Prensa española": ["Expansión", "Cinco Días", "El Economista"],
  Ciberseguridad: ["Bleeping Computer", "The Hacker News", "Security Week"],
  "Cadena de suministro": ["Supply Chain Dive", "FreightWaves"],
};

const apiSources = [
  { name: "NewsAPI", description: "Búsqueda por keywords con extracción de texto completo" },
  { name: "Alpha Vantage", description: "Noticias por ticker con sentimiento pre-calculado" },
  { name: "CNMV", description: "Hechos relevantes, información privilegiada y notas de prensa" },
  { name: "SEC EDGAR", description: "Filings corporativos (10-K, 10-Q, 8-K)" },
];

/* ── Page ─────────────────────────────────────────────────────────────── */

export default function SettingsPage() {
  const { backendOnline } = useApp();

  return (
    <>
      <PageHeader
        title="Configuración"
        subtitle="Modelos NLP, umbrales del pipeline y fuentes de datos configuradas"
      />

      {/* Backend status */}
      <Card className="mb-6 flex items-center gap-3">
        {backendOnline ? (
          <>
            <Wifi className="h-4 w-4 text-[var(--color-success)]" />
            <span className="text-[13px] font-semibold text-[var(--color-success)]">
              Backend conectado
            </span>
            <span className="text-[12px] text-[var(--text-muted)]">
              http://localhost:8000
            </span>
          </>
        ) : (
          <>
            <WifiOff className="h-4 w-4 text-[var(--color-danger)]" />
            <span className="text-[13px] font-semibold text-[var(--color-danger)]">
              Backend desconectado
            </span>
          </>
        )}
      </Card>

      {/* NLP Models */}
      <Section label="Modelos" title="Stack NLP" />
      <div className="mb-8 grid gap-3 lg:grid-cols-3">
        {nlpModels.map((m) => (
          <Card key={m.name}>
            <div className="mb-2 flex items-center gap-2">
              {m.icon}
              <span className="text-[13px] font-bold text-[var(--text-primary)]">{m.name}</span>
            </div>
            <code className="mb-1 block rounded bg-[var(--bg-root)] px-2 py-1 font-mono text-[11px] text-[var(--accent)]">
              {m.model}
            </code>
            <p className="text-[11px] text-[var(--text-muted)]">{m.description}</p>
          </Card>
        ))}
      </div>

      {/* Thresholds */}
      <Section label="Pipeline" title="Umbrales del Motor de Alertas" />
      <div className="mb-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {thresholds.map((t) => (
          <Card key={t.label}>
            <span className="block text-[10px] font-bold uppercase tracking-[0.08em] text-[var(--text-muted)]">
              {t.label}
            </span>
            <span className="my-1 block font-mono text-[24px] font-extrabold text-[var(--text-primary)]">
              {t.value}
            </span>
            <p className="text-[10px] text-[var(--text-muted)]">{t.description}</p>
          </Card>
        ))}
      </div>

      {/* Event Taxonomy */}
      <Section label="Taxonomía" title="Tipos de evento reconocidos" />
      <Card className="mb-8">
        <div className="flex flex-wrap gap-2">
          {eventTaxonomy.map((ev) => (
            <Badge key={ev} variant="event">
              {ev}
            </Badge>
          ))}
        </div>
      </Card>

      {/* Data Sources */}
      <Section label="Fuentes" title="Feeds RSS configurados" />
      <div className="mb-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {Object.entries(rssSources).map(([category, feeds]) => (
          <Card key={category}>
            <div className="mb-2 flex items-center gap-2">
              <Rss className="h-3.5 w-3.5 text-[var(--accent)]" />
              <span className="text-[12px] font-bold text-[var(--text-primary)]">
                {category}
              </span>
            </div>
            <ul className="space-y-1">
              {feeds.map((f) => (
                <li
                  key={f}
                  className="text-[11px] text-[var(--text-secondary)]"
                >
                  • {f}
                </li>
              ))}
            </ul>
          </Card>
        ))}
      </div>

      {/* API sources */}
      <Section label="APIs" title="Fuentes de noticias enriquecidas" />
      <div className="mb-8 grid gap-3 sm:grid-cols-2">
        {apiSources.map((s) => (
          <Card key={s.name}>
            <div className="mb-1 flex items-center gap-2">
              <Globe className="h-3.5 w-3.5 text-[var(--accent)]" />
              <span className="text-[13px] font-bold text-[var(--text-primary)]">{s.name}</span>
            </div>
            <p className="text-[11px] text-[var(--text-muted)]">{s.description}</p>
          </Card>
        ))}
      </div>

      {/* Database */}
      <Section label="Infraestructura" title="Base de datos" />
      <Card className="mb-8 flex items-center gap-3">
        <Database className="h-4 w-4 text-[var(--accent)]" />
        <div>
          <span className="block text-[13px] font-bold text-[var(--text-primary)]">
            MongoDB
          </span>
          <code className="text-[11px] text-[var(--text-muted)]">
            mongodb://localhost:27017 → portfolio_alerts
          </code>
        </div>
      </Card>
    </>
  );
}
