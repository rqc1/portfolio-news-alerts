"use client";

import { motion } from "framer-motion";
import {
  TrendingDown,
  TrendingUp,
  Minus,
  ExternalLink,
  Clock,
} from "lucide-react";
import type { Alert } from "@/lib/types";
import { Badge, Card } from "@/components/ui";
import { formatPercent, formatRelativeTime, slugify, cn } from "@/lib/utils";

const directionConfig = {
  bajista: {
    icon: TrendingDown,
    border: "border-l-[var(--color-danger)]",
    iconColor: "text-[var(--color-danger)]",
  },
  alcista: {
    icon: TrendingUp,
    border: "border-l-[var(--color-success)]",
    iconColor: "text-[var(--color-success)]",
  },
  neutral: {
    icon: Minus,
    border: "border-l-[var(--color-warning)]",
    iconColor: "text-[var(--color-warning)]",
  },
} as const;

function SeverityBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    value < 0.35
      ? "bg-[var(--color-success)]"
      : value < 0.65
        ? "bg-[var(--color-warning)]"
        : "bg-[var(--color-danger)]";

  return (
    <div className="flex flex-1 items-center gap-3">
      <div className="h-1.5 flex-1 rounded-full bg-[var(--bg-elevated)]">
        <motion.div
          className={cn("h-full rounded-full", color)}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}

export function AlertCard({ alert }: { alert: Alert }) {
  const dir = directionConfig[alert.direction] ?? directionConfig.neutral;
  const DirIcon = dir.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <Card
        className={cn(
          "border-l-[3px] transition-all duration-200 hover:border-[var(--border-hover)]",
          dir.border,
        )}
        hover
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <h3 className="flex-1 text-[14px] font-semibold leading-snug text-[var(--text-primary)]">
            {alert.news_title}
          </h3>
          <div className="flex items-center gap-1.5 whitespace-nowrap text-[11px] text-[var(--text-muted)]">
            <Clock className="h-3 w-3" />
            {formatRelativeTime(alert.created_at)}
          </div>
        </div>

        {/* Badges */}
        <div className="mt-3 flex flex-wrap gap-1.5">
          <Badge variant={alert.direction}>
            <DirIcon className={cn("h-3 w-3", dir.iconColor)} />
            {alert.direction.toUpperCase()}
          </Badge>
          <Badge variant="event">{slugify(alert.event_type)}</Badge>
          {alert.news_source && (
            <Badge variant="source">{alert.news_source}</Badge>
          )}
        </div>

        {/* Metrics row */}
        <div className="mt-4 flex items-center gap-6">
          <div className="text-center">
            <div className="text-[18px] font-extrabold text-[var(--text-primary)]">
              {formatPercent(alert.severity)}
            </div>
            <div className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--text-muted)]">
              Severidad
            </div>
          </div>
          <SeverityBar value={alert.severity} />
          <div className="text-center">
            <div className="text-[18px] font-extrabold text-[var(--text-primary)]">
              {formatPercent(alert.confidence)}
            </div>
            <div className="text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--text-muted)]">
              Confianza
            </div>
          </div>
        </div>

        {/* Explanation */}
        {alert.explanation && (
          <div className="mt-4 rounded-[var(--radius-md)] border-l-2 border-[var(--border-accent)] bg-[var(--bg-primary)] px-4 py-3 text-[13px] leading-relaxed text-[var(--text-secondary)]">
            {alert.explanation}
          </div>
        )}

        {/* Footer */}
        <div className="mt-4 flex items-center justify-between border-t border-[var(--border-subtle)] pt-3">
          <div className="text-[12px] text-[var(--text-muted)]">
            <span className="font-semibold text-[var(--text-secondary)]">Activos: </span>
            {alert.matched_assets.join(", ")}
          </div>
          {alert.news_url && (
            <a
              href={alert.news_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[12px] font-semibold text-[var(--accent)] transition-colors hover:text-[var(--accent-hover)]"
            >
              Ver fuente
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      </Card>
    </motion.div>
  );
}
