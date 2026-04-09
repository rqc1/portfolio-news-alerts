"use client";

import { useEffect, useState, useMemo } from "react";
import { Activity, TrendingDown, TrendingUp, Shield, Target } from "lucide-react";
import { useApp } from "@/hooks/use-app";
import { getAlerts, getAlertStats } from "@/lib/api";
import type { Alert, AlertStats } from "@/lib/types";
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
} from "@/components/charts";

export default function DashboardPage() {
  const { activePortfolioId, activePortfolio } = useApp();
  const [stats, setStats] = useState<AlertStats | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);

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
