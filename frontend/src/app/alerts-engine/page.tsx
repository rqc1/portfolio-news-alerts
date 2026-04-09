"use client";

import { useState, useEffect, useMemo } from "react";
import { Zap, FileText, History, Briefcase } from "lucide-react";
import { useApp } from "@/hooks/use-app";
import {
  processBatch,
  processNews,
  getAlerts,
} from "@/lib/api";
import type { Alert, BatchResult } from "@/lib/types";
import { formatPercent, slugify } from "@/lib/utils";
import {
  PageHeader,
  Section,
  Card,
  EmptyState,
  Button,
  Input,
  Textarea,
  Skeleton,
  Badge,
} from "@/components/ui";
import { AlertCard } from "@/components/alerts/alert-card";
import { EventDistributionChart, SeverityHistogram } from "@/components/charts";

type Tab = "batch" | "manual" | "history";

function TabNav({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "batch", label: "Procesar Batch", icon: <Zap className="h-3.5 w-3.5" /> },
    { id: "manual", label: "Análisis Manual", icon: <FileText className="h-3.5 w-3.5" /> },
    { id: "history", label: "Historial", icon: <History className="h-3.5 w-3.5" /> },
  ];
  return (
    <div className="mb-6 flex gap-1 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-1">
      {tabs.map(({ id, label, icon }) => (
        <button
          key={id}
          onClick={() => onChange(id)}
          className={`flex items-center gap-2 rounded-[var(--radius-sm)] px-4 py-2 text-[12px] font-semibold transition-colors ${
            active === id
              ? "bg-[var(--accent-muted)] text-[var(--accent-hover)]"
              : "text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
          }`}
        >
          {icon}
          {label}
        </button>
      ))}
    </div>
  );
}

/* ── Batch Panel ──────────────────────────────────────────────────────── */

function BatchPanel() {
  const { activePortfolioId, activePortfolio } = useApp();
  const [limit, setLimit] = useState(50);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BatchResult | null>(null);
  const [newAlerts, setNewAlerts] = useState<Alert[]>([]);

  if (!activePortfolioId) {
    return (
      <EmptyState
        icon={<Briefcase className="h-8 w-8" />}
        title="Sin cartera seleccionada"
        description="Selecciona una cartera activa en la barra lateral."
      />
    );
  }

  async function run() {
    setLoading(true);
    setResult(null);
    try {
      const res = await processBatch(activePortfolioId, limit);
      setResult(res);
      if (res.alerts_generated > 0) {
        const alerts = await getAlerts(activePortfolioId, res.alerts_generated);
        setNewAlerts(alerts);
      }
    } catch {
      /* handled by UI */
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <Section
        label="Pipeline NLP"
        title={`Procesando para: ${activePortfolio?.name ?? "—"}`}
      />
      <p className="text-[12px] text-[var(--text-muted)]">
        Cada noticia pasa por: preprocesamiento → entidades → relevancia → clasificación → impacto → dedup → alerta.
      </p>

      <div className="flex items-end gap-4">
        <div>
          <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-[0.06em] text-[var(--text-muted)]">
            Noticias a procesar
          </label>
          <input
            type="range"
            min={10}
            max={200}
            step={10}
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="w-48 accent-[var(--accent)]"
          />
          <span className="ml-3 font-mono text-[13px] font-bold text-[var(--text-primary)]">
            {limit}
          </span>
        </div>
        <Button variant="primary" onClick={run} loading={loading}>
          <Zap className="h-3.5 w-3.5" />
          Ejecutar Pipeline
        </Button>
      </div>

      {result && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {[
            { label: "Procesadas", value: result.processed },
            { label: "Alertas", value: result.alerts_generated },
            { label: "Duplicados", value: result.duplicates },
            { label: "Descartadas", value: result.discarded },
          ].map(({ label, value }) => (
            <Card key={label} className="text-center">
              <span className="block text-[28px] font-extrabold text-[var(--text-primary)]">
                {value}
              </span>
              <span className="text-[10px] font-bold uppercase tracking-[0.08em] text-[var(--text-muted)]">
                {label}
              </span>
            </Card>
          ))}
        </div>
      )}

      {newAlerts.length > 0 && (
        <div className="space-y-4">
          <Section label="Generadas" title="Alertas de este batch" />
          {newAlerts.map((a) => (
            <AlertCard key={a._id} alert={a} />
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Manual Panel ─────────────────────────────────────────────────────── */

function ManualPanel() {
  const { activePortfolioId } = useApp();
  const [form, setForm] = useState({
    title: "",
    summary: "",
    source: "manual",
    url: "",
  });
  const [loading, setLoading] = useState(false);
  const [resultAlert, setResultAlert] = useState<Alert | null>(null);
  const [noAlert, setNoAlert] = useState("");

  function update(field: string, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title.trim() || !activePortfolioId) return;
    setLoading(true);
    setResultAlert(null);
    setNoAlert("");
    try {
      const res = await processNews({
        title: form.title,
        summary: form.summary,
        url: form.url,
        source: form.source,
        portfolio_id: activePortfolioId,
      });
      if (res.status === "alert_generated" && res.alert) {
        setResultAlert(res.alert);
      } else {
        setNoAlert(res.reason ?? "No superó los umbrales de relevancia o severidad.");
      }
    } catch {
      /* empty */
    } finally {
      setLoading(false);
    }
  }

  if (!activePortfolioId) {
    return (
      <EmptyState
        icon={<Briefcase className="h-8 w-8" />}
        title="Sin cartera seleccionada"
        description="Selecciona una cartera en la barra lateral."
      />
    );
  }

  return (
    <div className="space-y-6">
      <Section label="Manual" title="Analizar noticia individual" />
      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Titular"
            placeholder="Apple reports lower than expected Q2 earnings amid China slowdown"
            value={form.title}
            onChange={(e) => update("title", e.target.value)}
            required
          />
          <Textarea
            label="Cuerpo / Resumen"
            placeholder="Pega aquí el texto de la noticia..."
            rows={4}
            value={form.summary}
            onChange={(e) => update("summary", e.target.value)}
          />
          <div className="grid gap-4 md:grid-cols-2">
            <Input
              label="Fuente"
              value={form.source}
              onChange={(e) => update("source", e.target.value)}
            />
            <Input
              label="URL (opcional)"
              placeholder="https://..."
              value={form.url}
              onChange={(e) => update("url", e.target.value)}
            />
          </div>
          <Button type="submit" variant="primary" loading={loading}>
            Analizar Noticia
          </Button>
        </form>
      </Card>

      {resultAlert && <AlertCard alert={resultAlert} />}
      {noAlert && (
        <Card className="border-l-2 border-l-[var(--color-warning)]">
          <p className="text-[13px] text-[var(--color-warning)]">
            Sin alerta: {noAlert}
          </p>
        </Card>
      )}
    </div>
  );
}

/* ── History Panel ────────────────────────────────────────────────────── */

function HistoryPanel() {
  const { activePortfolioId } = useApp();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const data = await getAlerts(activePortfolioId || undefined, 200);
        setAlerts(data);
      } catch {
        /* empty */
      } finally {
        setLoading(false);
      }
    })();
  }, [activePortfolioId]);

  const eventData = useMemo(() => {
    const map: Record<string, number> = {};
    alerts.forEach((a) => {
      const key = slugify(a.event_type);
      map[key] = (map[key] ?? 0) + 1;
    });
    return Object.entries(map)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);
  }, [alerts]);

  const histogramData = useMemo(() => {
    const bins = 20;
    const counts = new Array(bins).fill(0);
    alerts.forEach((a) => {
      const idx = Math.min(Math.floor(a.severity * bins), bins - 1);
      counts[idx]++;
    });
    return counts.map((count, i) => ({
      range: `${(i / bins).toFixed(2)}`,
      count,
    }));
  }, [alerts]);

  if (loading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    );
  }

  if (alerts.length === 0) {
    return (
      <EmptyState
        icon={<History className="h-8 w-8" />}
        title="Sin historial"
        description="Ejecuta el pipeline para generar alertas."
      />
    );
  }

  return (
    <div className="space-y-6">
      <Section label="Historial" title="Todas las alertas generadas" />

      {/* Data Table */}
      <Card className="overflow-x-auto">
        <table className="w-full text-left text-[12px]">
          <thead>
            <tr className="border-b border-[var(--border-subtle)]">
              {["Titular", "Evento", "Dirección", "Severidad", "Confianza", "Activos", "Fuente"].map(
                (h) => (
                  <th
                    key={h}
                    className="pb-2 pr-4 text-[10px] font-bold uppercase tracking-[0.08em] text-[var(--text-muted)]"
                  >
                    {h}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            {alerts.slice(0, 50).map((a) => (
              <tr
                key={a._id}
                className="border-b border-[var(--border-subtle)] last:border-0"
              >
                <td className="max-w-xs truncate py-2.5 pr-4 text-[var(--text-primary)]">
                  {a.news_title}
                </td>
                <td className="py-2.5 pr-4">
                  <Badge variant="event">{slugify(a.event_type)}</Badge>
                </td>
                <td className="py-2.5 pr-4">
                  <Badge variant={a.direction}>{a.direction}</Badge>
                </td>
                <td className="py-2.5 pr-4 font-mono text-[var(--text-primary)]">
                  {formatPercent(a.severity)}
                </td>
                <td className="py-2.5 pr-4 font-mono text-[var(--text-primary)]">
                  {formatPercent(a.confidence)}
                </td>
                <td className="py-2.5 pr-4 text-[var(--text-secondary)]">
                  {a.matched_assets.join(", ")}
                </td>
                <td className="py-2.5 text-[var(--text-muted)]">
                  {a.news_source}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {/* Charts */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <p className="mb-3 text-[11px] font-bold uppercase tracking-[0.08em] text-[var(--text-muted)]">
            Distribución por Evento
          </p>
          <EventDistributionChart data={eventData} />
        </Card>
        <Card>
          <p className="mb-3 text-[11px] font-bold uppercase tracking-[0.08em] text-[var(--text-muted)]">
            Distribución de Severidad
          </p>
          <SeverityHistogram data={histogramData} />
        </Card>
      </div>
    </div>
  );
}

/* ── Main Page ────────────────────────────────────────────────────────── */

export default function AlertsEnginePage() {
  const [tab, setTab] = useState<Tab>("batch");

  return (
    <>
      <PageHeader
        title="Motor de Alertas NLP"
        subtitle="Pipeline: NLP → Relevancia → Clasificación → Impacto → Dedup → Alerta"
      />
      <TabNav active={tab} onChange={setTab} />
      {tab === "batch" && <BatchPanel />}
      {tab === "manual" && <ManualPanel />}
      {tab === "history" && <HistoryPanel />}
    </>
  );
}
