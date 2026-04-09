import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

/* ── Page Header ──────────────────────────────────────────────────────── */

export function PageHeader({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children?: ReactNode;
}) {
  return (
    <div className="mb-8 flex items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
          {title}
        </h1>
        {subtitle && (
          <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
            {subtitle}
          </p>
        )}
      </div>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </div>
  );
}

/* ── Section ──────────────────────────────────────────────────────────── */

export function Section({
  label,
  title,
  children,
  className,
}: {
  label?: string;
  title: string;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("space-y-4", className)}>
      <div>
        {label && (
          <span className="mb-1 block text-[10px] font-bold uppercase tracking-[0.1em] text-[var(--accent)]">
            {label}
          </span>
        )}
        <h2 className="text-[17px] font-bold tracking-tight text-[var(--text-primary)]">
          {title}
        </h2>
      </div>
      {children}
    </div>
  );
}

/* ── Card ─────────────────────────────────────────────────────────────── */

export function Card({
  children,
  className,
  hover = false,
}: {
  children: ReactNode;
  className?: string;
  hover?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5",
        hover &&
          "transition-all duration-200 hover:border-[var(--border-hover)] hover:shadow-[0_4px_24px_var(--accent-glow)]",
        className,
      )}
    >
      {children}
    </div>
  );
}

/* ── KPI Metric Card ──────────────────────────────────────────────────── */

export function KpiCard({
  label,
  value,
  subtext,
  accent,
}: {
  label: string;
  value: string | number;
  subtext?: string;
  accent?: "default" | "success" | "danger" | "warning";
}) {
  const accentColors = {
    default: "text-[var(--text-primary)]",
    success: "text-[var(--color-success)]",
    danger: "text-[var(--color-danger)]",
    warning: "text-[var(--color-warning)]",
  };

  return (
    <Card hover>
      <span className="block text-[10px] font-bold uppercase tracking-[0.1em] text-[var(--text-muted)]">
        {label}
      </span>
      <span
        className={cn(
          "mt-1 block text-[28px] font-extrabold leading-none tracking-tight",
          accentColors[accent ?? "default"],
        )}
      >
        {value}
      </span>
      {subtext && (
        <span className="mt-1.5 block text-[11px] font-medium text-[var(--text-muted)]">
          {subtext}
        </span>
      )}
    </Card>
  );
}

/* ── Empty State ──────────────────────────────────────────────────────── */

export function EmptyState({
  icon,
  title,
  description,
  children,
}: {
  icon?: ReactNode;
  title: string;
  description?: string;
  children?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-[var(--radius-xl)] border-2 border-dashed border-[var(--border-subtle)] bg-[var(--bg-surface)] px-8 py-16 text-center">
      {icon && <div className="mb-4 text-4xl opacity-30">{icon}</div>}
      <h3 className="text-[15px] font-bold text-[var(--text-primary)]">
        {title}
      </h3>
      {description && (
        <p className="mt-1.5 max-w-xs text-[13px] leading-relaxed text-[var(--text-muted)]">
          {description}
        </p>
      )}
      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}

/* ── Badge / Pill ─────────────────────────────────────────────────────── */

const badgeVariants: Record<string, string> = {
  bajista:
    "bg-[var(--color-danger-muted)] text-[var(--color-danger)] border-[var(--color-danger)]/20",
  alcista:
    "bg-[var(--color-success-muted)] text-[var(--color-success)] border-[var(--color-success)]/20",
  neutral:
    "bg-[var(--color-warning-muted)] text-[var(--color-warning)] border-[var(--color-warning)]/20",
  event:
    "bg-purple-500/10 text-purple-400 border-purple-500/20",
  source:
    "bg-[var(--color-info-muted)] text-[var(--color-info)] border-[var(--color-info)]/20",
  default:
    "bg-[var(--bg-elevated)] text-[var(--text-secondary)] border-[var(--border-default)]",
};

export function Badge({
  variant = "default",
  children,
  className,
}: {
  variant?: keyof typeof badgeVariants | string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-[6px] border px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.04em]",
        badgeVariants[variant] ?? badgeVariants.default,
        className,
      )}
    >
      {children}
    </span>
  );
}

/* ── Skeleton Loader ──────────────────────────────────────────────────── */

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-[var(--radius-md)] bg-[var(--bg-elevated)]",
        className,
      )}
    />
  );
}

/* ── Button ───────────────────────────────────────────────────────────── */

export function Button({
  children,
  variant = "default",
  size = "md",
  loading: isLoading = false,
  className,
  ...props
}: {
  children: ReactNode;
  variant?: "default" | "primary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  className?: string;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const variants: Record<string, string> = {
    default:
      "border border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:border-[var(--border-hover)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-hover)]",
    primary:
      "bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)] shadow-[0_2px_12px_var(--accent-glow)]",
    ghost:
      "text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)]",
    danger:
      "border border-[var(--color-danger)]/20 bg-[var(--color-danger-muted)] text-[var(--color-danger)] hover:bg-[var(--color-danger)]/20",
  };

  const sizes: Record<string, string> = {
    sm: "h-8 px-3 text-[11px]",
    md: "h-9 px-4 text-[12px]",
    lg: "h-10 px-5 text-[13px]",
  };

  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-[var(--radius-md)] font-semibold transition-all duration-150 disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        sizes[size],
        className,
      )}
      disabled={isLoading || props.disabled}
      {...props}
    >
      {isLoading && (
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
      )}
      {children}
    </button>
  );
}

/* ── Input ────────────────────────────────────────────────────────────── */

export function Input({
  label,
  className,
  ...props
}: {
  label?: string;
} & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className="space-y-1.5">
      {label && (
        <label className="block text-[11px] font-semibold uppercase tracking-[0.06em] text-[var(--text-muted)]">
          {label}
        </label>
      )}
      <input
        className={cn(
          "w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2 text-[13px] text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)] transition-colors hover:border-[var(--border-hover)] focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]/20",
          className,
        )}
        {...props}
      />
    </div>
  );
}

/* ── Textarea ─────────────────────────────────────────────────────────── */

export function Textarea({
  label,
  className,
  ...props
}: {
  label?: string;
} & React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <div className="space-y-1.5">
      {label && (
        <label className="block text-[11px] font-semibold uppercase tracking-[0.06em] text-[var(--text-muted)]">
          {label}
        </label>
      )}
      <textarea
        className={cn(
          "w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2.5 text-[13px] text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)] transition-colors hover:border-[var(--border-hover)] focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]/20 resize-none",
          className,
        )}
        {...props}
      />
    </div>
  );
}
