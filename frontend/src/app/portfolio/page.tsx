"use client";

import { useState, useMemo } from "react";
import { Briefcase, Plus, Link2, Search, Loader2 } from "lucide-react";
import { useApp } from "@/hooks/use-app";
import { createPortfolio, addAsset, lookupTicker } from "@/lib/api";
import type { Portfolio, Asset } from "@/lib/types";
import {
  PageHeader,
  Section,
  Card,
  EmptyState,
  Button,
  Input,
  Badge,
} from "@/components/ui";
import { WeightPieChart, SectorBarChart } from "@/components/charts";

/* ── Tab Navigation ───────────────────────────────────────────────────── */

type Tab = "view" | "create" | "add-asset";

function TabNav({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "view", label: "Mis Carteras", icon: <Briefcase className="h-3.5 w-3.5" /> },
    { id: "create", label: "Nueva Cartera", icon: <Plus className="h-3.5 w-3.5" /> },
    { id: "add-asset", label: "Añadir Activo", icon: <Link2 className="h-3.5 w-3.5" /> },
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

/* ── Portfolio View ───────────────────────────────────────────────────── */

function PortfolioView({ portfolios }: { portfolios: Portfolio[] }) {
  if (portfolios.length === 0) {
    return (
      <EmptyState
        icon={<Briefcase className="h-8 w-8" />}
        title="Sin carteras creadas"
        description="Crea tu primera cartera desde la pestaña Nueva Cartera."
      />
    );
  }

  return (
    <div className="space-y-8">
      {portfolios.map((p) => (
        <PortfolioCard key={p._id} portfolio={p} />
      ))}
    </div>
  );
}

function PortfolioCard({ portfolio }: { portfolio: Portfolio }) {
  const assets = portfolio.assets;

  const pieData = useMemo(
    () => assets.filter((a) => a.weight > 0).map((a) => ({ name: a.ticker, value: a.weight })),
    [assets],
  );

  const sectorData = useMemo(() => {
    const map: Record<string, number> = {};
    assets.forEach((a) => {
      if (a.sector && a.weight) map[a.sector] = (map[a.sector] ?? 0) + a.weight;
    });
    return Object.entries(map).map(([sector, weight]) => ({ sector, weight }));
  }, [assets]);

  return (
    <Card>
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-[17px] font-bold text-[var(--text-primary)]">
            {portfolio.name}
          </h3>
          <span className="mt-0.5 block font-mono text-[11px] text-[var(--text-muted)]">
            {portfolio._id}
          </span>
        </div>
        <Badge>{assets.length} activos</Badge>
      </div>

      {assets.length > 0 ? (
        <>
          {/* Table */}
          <div className="mt-5 overflow-x-auto">
            <table className="w-full text-left text-[12px]">
              <thead>
                <tr className="border-b border-[var(--border-subtle)]">
                  {["Ticker", "Nombre", "Sector", "País", "Peso"].map((h) => (
                    <th
                      key={h}
                      className="pb-2 text-[10px] font-bold uppercase tracking-[0.08em] text-[var(--text-muted)]"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {assets.map((a) => (
                  <tr
                    key={a.ticker}
                    className="border-b border-[var(--border-subtle)] last:border-0"
                  >
                    <td className="py-2.5 font-semibold text-[var(--accent)]">
                      {a.ticker}
                    </td>
                    <td className="py-2.5 text-[var(--text-primary)]">{a.name}</td>
                    <td className="py-2.5 text-[var(--text-secondary)]">
                      {a.sector ?? "—"}
                    </td>
                    <td className="py-2.5 text-[var(--text-secondary)]">
                      {a.country ?? "—"}
                    </td>
                    <td className="py-2.5 font-mono font-semibold text-[var(--text-primary)]">
                      {(a.weight * 100).toFixed(0)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Charts */}
          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            {pieData.length > 1 && (
              <div>
                <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.08em] text-[var(--text-muted)]">
                  Distribución por Activo
                </p>
                <WeightPieChart data={pieData} />
              </div>
            )}
            {sectorData.length > 0 && (
              <div>
                <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.08em] text-[var(--text-muted)]">
                  Peso por Sector
                </p>
                <SectorBarChart data={sectorData} />
              </div>
            )}
          </div>
        </>
      ) : (
        <p className="mt-4 text-[12px] text-[var(--text-muted)]">
          Sin activos todavía. Añade activos desde la pestaña correspondiente.
        </p>
      )}
    </Card>
  );
}

/* ── Create Form ──────────────────────────────────────────────────────── */

function CreatePortfolioForm({ onCreated }: { onCreated: () => void }) {
  const { userId } = useApp();
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    try {
      await createPortfolio(userId, name.trim());
      setSuccess(`Cartera «${name}» creada correctamente.`);
      setName("");
      onCreated();
    } catch {
      setSuccess("");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <Section label="Nueva" title="Crear cartera de inversión" />
      <form onSubmit={handleSubmit} className="mt-4 space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <Input
            label="Nombre"
            placeholder="Mi Cartera Tecnológica"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <Input label="User ID" value={userId} disabled />
        </div>
        <Button type="submit" variant="primary" loading={loading}>
          Crear Cartera
        </Button>
        {success && (
          <p className="text-[12px] font-medium text-[var(--color-success)]">
            ✓ {success}
          </p>
        )}
      </form>
    </Card>
  );
}

/* ── Add Asset Form ───────────────────────────────────────────────────── */

/*
 * TODO: Auto-fill de activos
 * Cuando el usuario introduce ticker + nombre y pulsa un botón "Buscar",
 * el sistema debe auto-rellenar: sector, industry, country, ISIN y aliases.
 *
 * Implementación prevista:
 *   1. Nuevo endpoint backend: GET /api/assets/lookup?ticker=AAPL
 *      - Fuente primaria: Yahoo Finance API (yfinance) — sector, industry, country, currency
 *      - Fuente secundaria: Alpha Vantage OVERVIEW endpoint (si hay key)
 *      - Devuelve: { sector, industry, country, isin, aliases }
 *   2. En este formulario: botón "Auto-completar" al lado del ticker/nombre.
 *      - Llama al endpoint, rellena los campos automáticamente.
 *      - El usuario solo ajusta el peso manualmente.
 *   3. Los campos auto-rellenados siguen siendo editables por si el usuario
 *      quiere corregir algo.
 *
 * El peso en la cartera NO se auto-rellena (decisión del inversor).
 */

function AddAssetForm({ onAdded }: { onAdded: () => void }) {
  const { activePortfolioId, activePortfolio } = useApp();
  const [form, setForm] = useState({
    ticker: "",
    name: "",
    sector: "",
    country: "",
    weight: "0.10",
    aliases: "",
  });
  const [loading, setLoading] = useState(false);
  const [lookingUp, setLookingUp] = useState(false);
  const [success, setSuccess] = useState("");
  const [lookupError, setLookupError] = useState("");

  function update(field: string, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleLookup() {
    if (!form.ticker.trim()) return;
    setLookingUp(true);
    setLookupError("");
    try {
      const info = await lookupTicker(form.ticker.trim());
      setForm((prev) => ({
        ...prev,
        name: info.name || prev.name,
        sector: info.sector || prev.sector,
        country: info.country || prev.country,
        aliases: info.aliases.length > 0 ? info.aliases.join(", ") : prev.aliases,
      }));
    } catch {
      setLookupError(`No se encontró el ticker "${form.ticker}"`);
    } finally {
      setLookingUp(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!activePortfolioId || !form.ticker.trim()) return;
    setLoading(true);
    try {
      await addAsset(activePortfolioId, {
        ticker: form.ticker.trim(),
        name: form.name.trim(),
        sector: form.sector.trim() || undefined,
        country: form.country.trim() || undefined,
        weight: parseFloat(form.weight) || 0,
        aliases: form.aliases
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      });
      setSuccess(`${form.ticker} añadido correctamente.`);
      setForm({ ticker: "", name: "", sector: "", country: "", weight: "0.10", aliases: "" });
      onAdded();
    } catch {
      setSuccess("");
    } finally {
      setLoading(false);
    }
  }

  if (!activePortfolioId) {
    return (
      <EmptyState
        icon={<Briefcase className="h-8 w-8" />}
        title="Sin cartera seleccionada"
        description="Selecciona una cartera activa en la barra lateral."
      />
    );
  }

  return (
    <Card>
      <Section label="Añadir" title="Agregar activo a cartera activa" />
      {activePortfolio && (
        <p className="mt-1 text-[12px] text-[var(--text-tertiary)]">
          Cartera: <span className="font-semibold text-[var(--accent)]">{activePortfolio.name}</span>
        </p>
      )}
      <form onSubmit={handleSubmit} className="mt-4 space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="flex gap-2">
            <div className="flex-1">
              <Input
                label="Ticker"
                placeholder="AAPL"
                value={form.ticker}
                onChange={(e) => update("ticker", e.target.value)}
                required
              />
            </div>
            <button
              type="button"
              onClick={handleLookup}
              disabled={lookingUp || !form.ticker.trim()}
              className="mt-[22px] flex h-[38px] items-center gap-1.5 rounded-[var(--radius-md)] border border-[var(--accent)]/30 bg-[var(--accent)]/10 px-3 text-[12px] font-semibold text-[var(--accent)] transition hover:bg-[var(--accent)]/20 disabled:opacity-30"
            >
              {lookingUp ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
              Auto-fill
            </button>
          </div>
          <Input
            label="Nombre"
            placeholder="Apple Inc."
            value={form.name}
            onChange={(e) => update("name", e.target.value)}
            required
          />
        </div>
        {lookupError && (
          <p className="text-[12px] text-[var(--color-danger)]">{lookupError}</p>
        )}
        <div className="grid gap-4 md:grid-cols-3">
          <Input
            label="Sector"
            placeholder="Technology"
            value={form.sector}
            onChange={(e) => update("sector", e.target.value)}
          />
          <Input
            label="País (ISO 2)"
            placeholder="US"
            value={form.country}
            onChange={(e) => update("country", e.target.value)}
          />
          <Input
            label="Peso (0–1)"
            type="number"
            min="0"
            max="1"
            step="0.05"
            value={form.weight}
            onChange={(e) => update("weight", e.target.value)}
          />
        </div>
        <Input
          label="Aliases (separados por coma)"
          placeholder="Apple, AAPL US Equity"
          value={form.aliases}
          onChange={(e) => update("aliases", e.target.value)}
        />
        <Button type="submit" variant="primary" loading={loading}>
          Añadir Activo
        </Button>
        {success && (
          <p className="text-[12px] font-medium text-[var(--color-success)]">
            ✓ {success}
          </p>
        )}
      </form>
    </Card>
  );
}

/* ── Main Page ────────────────────────────────────────────────────────── */

export default function PortfolioPage() {
  const { portfolios, refresh } = useApp();
  const [tab, setTab] = useState<Tab>("view");

  return (
    <>
      <PageHeader
        title="Gestión de Cartera"
        subtitle="Administra activos, pesos y composición sectorial"
      />

      <TabNav active={tab} onChange={setTab} />

      {tab === "view" && <PortfolioView portfolios={portfolios} />}
      {tab === "create" && <CreatePortfolioForm onCreated={refresh} />}
      {tab === "add-asset" && <AddAssetForm onAdded={refresh} />}
    </>
  );
}
