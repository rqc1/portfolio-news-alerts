"use client";

import { useEffect, useState, useMemo } from "react";
import { Activity, TrendingDown, TrendingUp, Shield, Target, BarChart3, Loader2 } from "lucide-react";
import { useApp } from "@/hooks/use-app";
import { getAlerts, getAlertStats, getPortfolioAnalytics } from "@/lib/api";
import type { Alert, AlertStats, PortfolioAnalyticsResult } from "@/lib/types";
import { formatPercent, slugify } from "@/lib/utils";
import {
  PageHeader,
  Section,
  KpiCard,
  EmptyState,
  Skeleton,
  Card,
} from "@/components/ui";
import { AlertCard } from "@/components/alerts/alert-card";
import {
  EventDistributionChart,
  DirectionPieChart,
  SeverityConfidenceScatter,
  ReturnAreaChart,
  AssetPerformanceChart,
} from "@/components/charts";

export default function DashboardPage() {
  const { activePortfolioId, activePortfolio } = useApp();
  const [stats, setStats] = useState<AlertStats | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [analytics, setAnalytics] = useState<PortfolioAnalyticsResult | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [s, a] = await Promise.all([
          getAlertStats(activePortfolioId || undefined),
          getAlerts(activePortfolioId || undefined, 200),
        ]);
        setStats(s);
        setAlerts(a);
      } catch {
        /* handled by empty states */
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [activePortfolioId]);

  // Load portfolio analytics separately (slower due to yfinance calls)
  useEffect(() => {
    if (!activePortfolioId || !activePortfolio || activePortfolio.assets.length === 0) {
      setAnalytics(null);
      return;
    }
    const hasWeights = activePortfolio.assets.some((a) => a.weight > 0);
    if (!hasWeights) {
      setAnalytics(null);
      return;
    }
    setAnalyticsLoading(true);
    getPortfolioAnalytics(activePortfolioId)
      .then(setAnalytics)
      .catch(() => setAnalytics(null))
      .finally(() => setAnalyticsLoading(false));
  }, [activePortfolioId, activePortfolio]);

  const directionCounts = useMemo(() => {
    const counts = { bajista: 0, alcista: 0, neutral: 0 };
    alerts.forEach((a) => {
      if (a.direction in counts) counts[a.direction as keyof typeof counts]++;
    });
    return counts;
  }, [alerts]);

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

  const pieData = useMemo(
    () =>
      Object.entries(directionCounts)
        .filter(([, v]) => v > 0)
        .map(([name, value]) => ({ name, value })),
    [directionCounts],
  );

  const scatterData = useMemo(
    () =>
      alerts.map((a) => ({
        severity: a.severity,
        confidence: a.confidence,
        direction: a.direction,
        title: a.news_title,
      })),
    [alerts],
  );

  const total = stats?.total ?? 0;

  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle={
          activePortfolio
            ? `Cartera activa: ${activePortfolio.name}`
            : "Monitorización en tiempo real"
        }
      />

      {/* KPI Row */}
      {loading ? (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-[100px]" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
          <KpiCard
            label="Total Alertas"
            value={total}
            subtext="Acumulado"
          />
          <KpiCard
            label="Bajistas"
            value={directionCounts.bajista}
            subtext={`${total ? Math.round((directionCounts.bajista / total) * 100) : 0}% del total`}
            accent="danger"
          />
          <KpiCard
            label="Alcistas"
            value={directionCounts.alcista}
            subtext={`${total ? Math.round((directionCounts.alcista / total) * 100) : 0}% del total`}
            accent="success"
          />
          <KpiCard
            label="Severidad Media"
            value={formatPercent(stats?.avg_severity)}
            subtext="Promedio ponderado"
            accent="warning"
          />
          <KpiCard
            label="Confianza Media"
            value={formatPercent(stats?.avg_confidence)}
            subtext="Promedio del modelo"
          />
        </div>
      )}

      {/* Charts */}
      {!loading && alerts.length > 0 && (
        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          <Card>
            <Section label="Análisis" title="Distribución por Evento" />
            <div className="mt-4">
              <EventDistributionChart data={eventData} />
            </div>
          </Card>
          <Card>
            <Section label="Dirección" title="Impacto en Cartera" />
            <div className="mt-4">
              <DirectionPieChart data={pieData} />
            </div>
          </Card>
        </div>
      )}

      {!loading && scatterData.length > 0 && (
        <div className="mt-6">
          <Card>
            <Section label="Correlación" title="Severidad vs. Confianza" />
            <div className="mt-4">
              <SeverityConfidenceScatter data={scatterData} />
            </div>
          </Card>
        </div>
      )}

      {/* Portfolio Analytics */}
      {analyticsLoading && (
        <div className="mt-8 space-y-4">
          <Section label="Analytics" title="Métricas de Cartera" />
          <div className="flex items-center gap-2 text-[13px] text-[var(--text-muted)]">
            <Loader2 className="h-4 w-4 animate-spin" />
            Calculando métricas de rendimiento y riesgo…
          </div>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-[100px]" />
            ))}
          </div>
        </div>
      )}

      {analytics && !analyticsLoading && (
        <div className="mt-8 space-y-6">
          <Section label="Analytics" title="Métricas de Cartera (quantstats)" />

          {/* Risk / Return KPIs */}
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <KpiCard
              label="Retorno Total"
              value={`${analytics.metrics.total_return_pct >= 0 ? "+" : ""}${analytics.metrics.total_return_pct}%`}
              subtext={`Período: ${analytics.metrics.period}`}
              accent={analytics.metrics.total_return_pct >= 0 ? "success" : "danger"}
            />
            <KpiCard
              label="Sharpe Ratio"
              value={analytics.metrics.sharpe_ratio}
              subtext="Retorno ajustado a riesgo"
              accent={analytics.metrics.sharpe_ratio >= 1 ? "success" : analytics.metrics.sharpe_ratio >= 0 ? "warning" : "danger"}
            />
            <KpiCard
              label="Máx. Drawdown"
              value={`${analytics.metrics.max_drawdown_pct}%`}
              subtext="Peor caída desde máximos"
              accent="danger"
            />
            <KpiCard
              label="Volatilidad"
              value={`${analytics.metrics.volatility_pct}%`}
              subtext="Anualizada"
              accent="warning"
            />
          </div>

          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <KpiCard
              label="Sortino"
              value={analytics.metrics.sortino_ratio}
              subtext="Solo riesgo bajista"
            />
            <KpiCard
              label="VaR 95%"
              value={`${analytics.metrics.var_95_pct}%`}
              subtext="Pérdida máxima esperada (diaria)"
            />
            <KpiCard
              label="Alpha vs {analytics.metrics.benchmark_ticker}"
              value={`${analytics.metrics.alpha_pct >= 0 ? "+" : ""}${analytics.metrics.alpha_pct}%`}
              accent={analytics.metrics.alpha_pct >= 0 ? "success" : "danger"}
            />
            <KpiCard
              label="Win Rate"
              value={`${analytics.metrics.win_rate_pct}%`}
              subtext="Días positivos"
            />
          </div>

          {/* Charts */}
          <div className="grid gap-6 lg:grid-cols-2">
            {analytics.return_series.length > 0 && (
              <Card>
                <Section label="Rendimiento" title="Retorno Acumulado" />
                <div className="mt-4">
                  <ReturnAreaChart data={analytics.return_series} />
                </div>
              </Card>
            )}
            {analytics.asset_performance.length > 0 && (
              <Card>
                <Section label="Activos" title="Rendimiento por Activo" />
                <div className="mt-4">
                  <AssetPerformanceChart
                    data={analytics.asset_performance.map((a) => ({
                      ticker: a.ticker,
                      return_pct: a.return_pct,
                    }))}
                  />
                </div>
              </Card>
            )}
          </div>

          {/* Asset table */}
          {analytics.asset_performance.length > 0 && (
            <Card>
              <Section label="Detalle" title="Rendimiento Individual" />
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-[12px]">
                  <thead>
                    <tr className="border-b border-[var(--border-subtle)]">
                      {["Ticker", "Peso", "Retorno", "Volatilidad", "Sharpe", "Contribución"].map((h) => (
                        <th key={h} className="pb-2 text-[10px] font-bold uppercase tracking-[0.08em] text-[var(--text-muted)]">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {analytics.asset_performance.map((a) => (
                      <tr key={a.ticker} className="border-b border-[var(--border-subtle)] last:border-0">
                        <td className="py-2.5 font-semibold text-[var(--accent)]">{a.ticker}</td>
                        <td className="py-2.5 font-mono text-[var(--text-primary)]">{a.weight}%</td>
                        <td className={`py-2.5 font-mono font-semibold ${a.return_pct >= 0 ? "text-[var(--color-success)]" : "text-[var(--color-danger)]"}`}>
                          {a.return_pct >= 0 ? "+" : ""}{a.return_pct}%
                        </td>
                        <td className="py-2.5 font-mono text-[var(--text-secondary)]">{a.volatility_pct}%</td>
                        <td className="py-2.5 font-mono text-[var(--text-secondary)]">{a.sharpe}</td>
                        <td className={`py-2.5 font-mono font-semibold ${a.contribution_pct >= 0 ? "text-[var(--color-success)]" : "text-[var(--color-danger)]"}`}>
                          {a.contribution_pct >= 0 ? "+" : ""}{a.contribution_pct}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Recent Alerts */}
      <div className="mt-10">
        <Section label="Últimas Alertas" title="Actividad Reciente" />
        <div className="mt-4 space-y-4">
          {loading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-[200px]" />
            ))
          ) : alerts.length > 0 ? (
            alerts.slice(0, 8).map((a) => <AlertCard key={a._id} alert={a} />)
          ) : (
            <EmptyState
              icon={<Activity className="h-8 w-8" />}
              title="Sin alertas todavía"
              description="Ingesta noticias y procésalas desde el Motor de Alertas para generar señales."
            />
          )}
        </div>
      </div>
    </>
  );
}
