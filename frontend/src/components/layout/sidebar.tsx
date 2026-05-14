"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  Briefcase,
  Newspaper,
  Zap,
  Settings,
  ChevronDown,
  Wifi,
  WifiOff,
  UserCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useApp } from "@/hooks/use-app";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/portfolio", label: "Cartera", icon: Briefcase },
  { href: "/news", label: "Noticias", icon: Newspaper },
  { href: "/alerts-engine", label: "Motor de Alertas", icon: Zap },
  { href: "/advisor", label: "Asesor Inversiones", icon: UserCheck },
  { href: "/settings", label: "Configuración", icon: Settings },
] as const;

export function Sidebar() {
  const pathname = usePathname();
  const {
    portfolios,
    activePortfolioId,
    setActivePortfolioId,
    backendOnline,
    loading,
  } = useApp();

  return (
    <aside className="fixed inset-y-0 left-0 z-40 flex w-[260px] flex-col border-r border-[var(--border-subtle)] bg-[var(--bg-primary)]">
      {/* ── Brand ─────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 px-6 pt-7 pb-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-[10px] bg-[var(--accent)] shadow-[0_0_20px_var(--accent-glow)]">
          <Zap className="h-4 w-4 text-white" />
        </div>
        <div>
          <span className="text-[15px] font-bold tracking-tight text-[var(--text-primary)]">
            Invest<span className="text-[var(--accent)]">AI</span>lert
          </span>
          <span className="block text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--text-muted)]">
            Inteligencia Financiera
          </span>
        </div>
      </div>

      {/* ── Navigation ────────────────────────────────────────── */}
      <nav className="flex-1 space-y-1 px-3">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "group relative flex items-center gap-3 rounded-[var(--radius-md)] px-3 py-2.5 text-[13px] font-medium transition-colors",
                active
                  ? "text-[var(--text-primary)]"
                  : "text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]",
              )}
            >
              {active && (
                <motion.div
                  layoutId="sidebar-active"
                  className="absolute inset-0 rounded-[var(--radius-md)] bg-[var(--accent-muted)] border border-[var(--border-accent)]"
                  transition={{ type: "spring", stiffness: 350, damping: 30 }}
                />
              )}
              <Icon
                className={cn(
                  "relative z-10 h-4 w-4 shrink-0",
                  active ? "text-[var(--accent-hover)]" : "text-[var(--text-muted)] group-hover:text-[var(--text-tertiary)]",
                )}
              />
              <span className="relative z-10">{label}</span>
            </Link>
          );
        })}
      </nav>

      {/* ── Portfolio Selector ────────────────────────────────── */}
      <div className="border-t border-[var(--border-subtle)] px-4 py-4">
        <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-[0.1em] text-[var(--text-muted)]">
          Cartera activa
        </label>
        {loading ? (
          <div className="h-9 animate-pulse rounded-[var(--radius-md)] bg-[var(--bg-surface)]" />
        ) : portfolios.length === 0 ? (
          <p className="text-[11px] text-[var(--text-muted)]">Sin carteras</p>
        ) : (
          <div className="relative">
            <select
              value={activePortfolioId}
              onChange={(e) => setActivePortfolioId(e.target.value)}
              className="w-full appearance-none rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2 pr-8 text-[12px] font-medium text-[var(--text-primary)] outline-none transition-colors hover:border-[var(--border-hover)] focus:border-[var(--accent)]"
            >
              {portfolios.map((p) => (
                <option key={p._id} value={p._id}>
                  {p.name}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute top-1/2 right-2.5 h-3.5 w-3.5 -translate-y-1/2 text-[var(--text-muted)]" />
          </div>
        )}
      </div>

      {/* ── Backend status ─────────────────────────────────────── */}
      <div className="flex items-center gap-2 border-t border-[var(--border-subtle)] px-5 py-3.5">
        <span
          className={cn(
            "h-1.5 w-1.5 rounded-full",
            backendOnline
              ? "bg-[var(--color-success)] shadow-[0_0_6px_var(--color-success)]"
              : "bg-[var(--color-danger)] shadow-[0_0_6px_var(--color-danger)]",
          )}
        />
        <span className="text-[11px] font-medium text-[var(--text-muted)]">
          {backendOnline ? "Backend conectado" : "Backend offline"}
        </span>
        {backendOnline ? (
          <Wifi className="ml-auto h-3 w-3 text-[var(--color-success)]" />
        ) : (
          <WifiOff className="ml-auto h-3 w-3 text-[var(--color-danger)]" />
        )}
      </div>

      {/* ── Footer ──────────────────────────────────────────────── */}
      <div className="px-5 pb-4 text-center">
        <span className="text-[10px] text-[var(--text-muted)]">
          InvestAlert v1.0 · TFM UNIR
        </span>
      </div>
    </aside>
  );
}
