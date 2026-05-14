"use client";

import { useCallback, useEffect, useState } from "react";
import {
  CheckCircle,
  ChevronRight,
  ChevronLeft,
  Loader2,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Shield,
  Target,
  UserCheck,
} from "lucide-react";
import { useApp } from "@/hooks/use-app";
import { PageHeader, Section, Card, Badge, EmptyState } from "@/components/ui";
import {
  getAdvisorQuestions,
  generateAdvisorReport,
  getAdvisorReports,
} from "@/lib/api";
import type {
  Question,
  AdvisorReport,
  AllocationSlice,
  Recommendation,
} from "@/lib/types";

/* ── Helpers ──────────────────────────────────────────────────────────── */

const PROFILE_LABELS: Record<string, string> = {
  very_conservative: "Muy Conservador",
  conservative: "Conservador",
  moderate: "Moderado",
  aggressive: "Agresivo",
  very_aggressive: "Muy Agresivo",
};

const PROFILE_COLORS: Record<string, string> = {
  very_conservative: "text-blue-400",
  conservative: "text-cyan-400",
  moderate: "text-yellow-400",
  aggressive: "text-orange-400",
  very_aggressive: "text-red-400",
};

const PRIORITY_MAP: Record<string, string> = {
  alta: "bg-red-500/10 text-red-400 border-red-500/20",
  media: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  baja: "bg-green-500/10 text-green-400 border-green-500/20",
};

function pctBar(value: number, max = 100) {
  const w = Math.min(Math.abs(value), max);
  const color =
    value > 5 ? "bg-red-500" : value < -5 ? "bg-blue-500" : "bg-green-500";
  return (
    <div className="h-2 w-full rounded-full bg-[var(--bg-elevated)]">
      <div
        className={`h-2 rounded-full ${color}`}
        style={{ width: `${w}%` }}
      />
    </div>
  );
}

/* ── Step components ──────────────────────────────────────────────────── */

function QuestionStep({
  question,
  selected,
  onSelect,
}: {
  question: Question;
  selected: string | null;
  onSelect: (optionId: string) => void;
}) {
  return (
    <div className="space-y-4">
      <div>
        <span className="mb-1 block text-[10px] font-bold uppercase tracking-[0.1em] text-[var(--accent)]">
          {question.category}
        </span>
        <h3 className="text-[17px] font-bold text-[var(--text-primary)]">
          {question.text}
        </h3>
        {question.description && (
          <p className="mt-1 text-[13px] text-[var(--text-muted)]">
            {question.description}
          </p>
        )}
      </div>
      <div className="space-y-2">
        {question.options.map((opt) => (
          <button
            key={opt.id}
            onClick={() => onSelect(opt.id)}
            className={`w-full rounded-[var(--radius-lg)] border p-4 text-left text-[14px] transition-all duration-200 ${
              selected === opt.id
                ? "border-[var(--accent)] bg-[var(--accent)]/10 text-[var(--text-primary)]"
                : "border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:border-[var(--border-hover)]"
            }`}
          >
            {opt.text}
          </button>
        ))}
      </div>
    </div>
  );
}

function AllocationTable({
  title,
  slices,
}: {
  title: string;
  slices: AllocationSlice[];
}) {
  return (
    <Card>
      <h4 className="mb-3 text-[14px] font-bold text-[var(--text-primary)]">
        {title}
      </h4>
      <div className="space-y-3">
        {slices.map((s) => (
          <div key={s.category}>
            <div className="flex items-center justify-between text-[12px]">
              <span className="text-[var(--text-secondary)]">{s.category}</span>
              <span className="text-[var(--text-muted)]">
                {s.current_pct.toFixed(1)}% → {s.ideal_pct.toFixed(1)}%
                <span
                  className={`ml-2 font-semibold ${
                    s.status === "sobreexpuesto"
                      ? "text-red-400"
                      : s.status === "infraexpuesto"
                        ? "text-blue-400"
                        : "text-green-400"
                  }`}
                >
                  ({s.diff_pct > 0 ? "+" : ""}
                  {s.diff_pct.toFixed(1)}%)
                </span>
              </span>
            </div>
            {pctBar(s.diff_pct)}
          </div>
        ))}
      </div>
    </Card>
  );
}

function RecommendationCard({ rec }: { rec: Recommendation }) {
  const isReduce = rec.action.toLowerCase().includes("reducir") || rec.action.toLowerCase().includes("vender");
  return (
    <Card hover>
      <div className="flex items-start gap-3">
        <div className="mt-0.5">
          {isReduce ? (
            <TrendingDown className="h-5 w-5 text-red-400" />
          ) : (
            <TrendingUp className="h-5 w-5 text-green-400" />
          )}
        </div>
        <div className="flex-1 space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-[14px] font-bold text-[var(--text-primary)]">
              {rec.action}
            </span>
            <span
              className={`inline-block rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase ${
                PRIORITY_MAP[rec.priority] ?? PRIORITY_MAP.baja
              }`}
            >
              {rec.priority}
            </span>
          </div>
          <p className="text-[13px] text-[var(--text-secondary)]">
            {rec.asset_name}
            {rec.ticker && (
              <span className="ml-1 text-[var(--text-muted)]">
                ({rec.ticker})
              </span>
            )}
            {" · "}
            <span className="text-[var(--text-muted)]">{rec.sector}</span>
          </p>
          <p className="text-[12px] leading-relaxed text-[var(--text-muted)]">
            {rec.reason}
          </p>
          {(rec.current_weight != null || rec.suggested_weight != null) && (
            <p className="text-[11px] text-[var(--text-muted)]">
              Peso: {rec.current_weight?.toFixed(1) ?? "—"}% →{" "}
              {rec.suggested_weight?.toFixed(1) ?? "—"}%
            </p>
          )}
        </div>
      </div>
    </Card>
  );
}

function ReportView({ report }: { report: AdvisorReport }) {
  const { profile, analysis, recommendations, llm_summary } = report;
  return (
    <div className="space-y-8">
      {/* Profile summary */}
      <Section label="Perfil del inversor" title="Tu perfil">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Card>
            <span className="block text-[10px] font-bold uppercase tracking-[0.1em] text-[var(--text-muted)]">
              Perfil de riesgo
            </span>
            <span
              className={`mt-1 block text-[22px] font-extrabold ${
                PROFILE_COLORS[profile.risk_profile] ?? ""
              }`}
            >
              {PROFILE_LABELS[profile.risk_profile] ?? profile.risk_profile}
            </span>
            <span className="text-[11px] text-[var(--text-muted)]">
              Score: {profile.risk_score}/100
            </span>
          </Card>
          <Card>
            <span className="block text-[10px] font-bold uppercase tracking-[0.1em] text-[var(--text-muted)]">
              Horizonte
            </span>
            <span className="mt-1 block text-[18px] font-bold text-[var(--text-primary)]">
              {profile.horizon === "short" ? "Corto plazo" : profile.horizon === "medium" ? "Medio plazo" : "Largo plazo"}
            </span>
          </Card>
          <Card>
            <span className="block text-[10px] font-bold uppercase tracking-[0.1em] text-[var(--text-muted)]">
              Objetivo
            </span>
            <span className="mt-1 block text-[18px] font-bold text-[var(--text-primary)] capitalize">
              {profile.goal.replace(/_/g, " ")}
            </span>
          </Card>
          <Card>
            <span className="block text-[10px] font-bold uppercase tracking-[0.1em] text-[var(--text-muted)]">
              Tolerancia pérdida
            </span>
            <span className="mt-1 block text-[22px] font-extrabold text-[var(--text-primary)]">
              {profile.loss_tolerance_pct}%
            </span>
          </Card>
        </div>
      </Section>

      {/* Analysis */}
      <Section label="Análisis de cartera" title="Diagnóstico">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Card>
            <span className="block text-[10px] font-bold uppercase text-[var(--text-muted)]">
              Diversificación
            </span>
            <span className="mt-1 block text-[28px] font-extrabold text-[var(--text-primary)]">
              {analysis.diversification_score}
            </span>
          </Card>
          <Card>
            <span className="block text-[10px] font-bold uppercase text-[var(--text-muted)]">
              Alineación riesgo
            </span>
            <span className="mt-1 block text-[28px] font-extrabold text-[var(--text-primary)]">
              {analysis.risk_alignment_score}
            </span>
          </Card>
          <Card>
            <span className="block text-[10px] font-bold uppercase text-[var(--text-muted)]">
              Concentración (HHI)
            </span>
            <span className="mt-1 block text-[28px] font-extrabold text-[var(--text-primary)]">
              {analysis.concentration_risk.toFixed(0)}
            </span>
          </Card>
          <Card>
            <span className="block text-[10px] font-bold uppercase text-[var(--text-muted)]">
              Avisos
            </span>
            <span className="mt-1 block text-[28px] font-extrabold text-[var(--color-warning)]">
              {analysis.warnings.length}
            </span>
          </Card>
        </div>

        {analysis.warnings.length > 0 && (
          <Card className="border-[var(--color-warning)]/30 bg-[var(--color-warning)]/5">
            <div className="space-y-2">
              {analysis.warnings.map((w, i) => (
                <div key={i} className="flex items-start gap-2 text-[13px]">
                  <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-[var(--color-warning)]" />
                  <span className="text-[var(--text-secondary)]">{w}</span>
                </div>
              ))}
            </div>
          </Card>
        )}

        <div className="grid gap-4 md:grid-cols-2">
          <AllocationTable
            title="Asignación por sector"
            slices={analysis.sector_allocation}
          />
          <AllocationTable
            title="Asignación geográfica"
            slices={analysis.geography_allocation}
          />
        </div>
      </Section>

      {/* Recommendations */}
      <Section label="Recomendaciones" title="Plan de acción">
        <div className="space-y-3">
          {recommendations.map((rec, i) => (
            <RecommendationCard key={i} rec={rec} />
          ))}
        </div>
      </Section>

      {/* LLM Summary */}
      {llm_summary && (
        <Section label="Análisis del modelo" title="Resumen inteligente">
          <Card>
            <div className="whitespace-pre-wrap text-[13px] leading-relaxed text-[var(--text-secondary)]">
              {llm_summary}
            </div>
          </Card>
        </Section>
      )}
    </div>
  );
}

/* ── Main page ────────────────────────────────────────────────────────── */

export default function AdvisorPage() {
  const { portfolios } = useApp();

  const [selectedPortfolio, setSelectedPortfolio] = useState<string>("");
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [step, setStep] = useState(0); // 0 = select portfolio, 1..N = questions, N+1 = loading/results
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<AdvisorReport | null>(null);
  const [pastReports, setPastReports] = useState<AdvisorReport[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [viewingPast, setViewingPast] = useState<AdvisorReport | null>(null);

  // Load questions on mount
  useEffect(() => {
    getAdvisorQuestions()
      .then(setQuestions)
      .catch(() => setError("No se pudieron cargar las preguntas"));
  }, []);

  // Load past reports when portfolio changes
  useEffect(() => {
    if (!selectedPortfolio) return;
    getAdvisorReports(selectedPortfolio)
      .then(setPastReports)
      .catch(() => {});
  }, [selectedPortfolio]);

  const totalSteps = questions.length + 1; // +1 for portfolio selection
  const currentQuestion = step >= 1 && step <= questions.length ? questions[step - 1] : null;
  const allAnswered = questions.length > 0 && questions.every((q) => answers[q.id]);

  const handleSubmit = useCallback(async () => {
    if (!selectedPortfolio) return;
    setLoading(true);
    setError(null);
    try {
      const submission = {
        user_id: "default",
        portfolio_id: selectedPortfolio,
        answers: Object.entries(answers).map(([question_id, selected_option_id]) => ({
          question_id,
          selected_option_id,
        })),
      };
      const result = await generateAdvisorReport(submission);
      setReport(result);
      setStep(totalSteps + 1);
    } catch {
      setError("Error al generar el informe. Revisa la conexión con el backend.");
    } finally {
      setLoading(false);
    }
  }, [answers, selectedPortfolio, totalSteps]);

  const handleRestart = () => {
    setAnswers({});
    setStep(0);
    setReport(null);
    setViewingPast(null);
    setError(null);
  };

  /* ── Viewing a past report ── */
  if (viewingPast) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Informe anterior"
          subtitle={viewingPast.created_at ? `Generado: ${new Date(viewingPast.created_at).toLocaleString("es-ES")}` : undefined}
        >
          <button
            onClick={() => setViewingPast(null)}
            className="rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-2 text-[13px] font-medium text-[var(--text-secondary)] transition hover:border-[var(--border-hover)]"
          >
            Volver
          </button>
        </PageHeader>
        <ReportView report={viewingPast} />
      </div>
    );
  }

  /* ── Results view ── */
  if (report && step > totalSteps) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Asesor de Inversiones"
          subtitle="Informe personalizado generado"
        >
          <button
            onClick={handleRestart}
            className="rounded-[var(--radius-lg)] border border-[var(--accent)]/30 bg-[var(--accent)]/10 px-4 py-2 text-[13px] font-medium text-[var(--accent)] transition hover:bg-[var(--accent)]/20"
          >
            Nuevo análisis
          </button>
        </PageHeader>
        <ReportView report={report} />
      </div>
    );
  }

  /* ── Questionnaire flow ── */
  return (
    <div className="space-y-6">
      <PageHeader
        title="Asesor de Inversiones"
        subtitle="Responde al cuestionario para recibir recomendaciones personalizadas"
      />

      {error && (
        <Card className="border-red-500/30 bg-red-500/5">
          <div className="flex items-center gap-2 text-[13px] text-red-400">
            <AlertTriangle className="h-4 w-4" />
            {error}
          </div>
        </Card>
      )}

      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-[11px] text-[var(--text-muted)]">
          <span>Paso {step + 1} de {totalSteps + 1}</span>
          <span>{Math.round((step / totalSteps) * 100)}%</span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-[var(--bg-elevated)]">
          <div
            className="h-1.5 rounded-full bg-[var(--accent)] transition-all duration-300"
            style={{ width: `${(step / totalSteps) * 100}%` }}
          />
        </div>
      </div>

      <Card>
        {/* Step 0: Portfolio selection */}
        {step === 0 && (
          <div className="space-y-4">
            <h3 className="text-[17px] font-bold text-[var(--text-primary)]">
              Selecciona la cartera a analizar
            </h3>
            {portfolios.length === 0 ? (
              <EmptyState
                icon={<Shield className="h-8 w-8" />}
                title="Sin carteras"
                description="Crea una cartera primero en la sección Cartera"
              />
            ) : (
              <div className="space-y-2">
                {portfolios.map((p) => (
                  <button
                    key={p._id}
                    onClick={() => setSelectedPortfolio(p._id)}
                    className={`w-full rounded-[var(--radius-lg)] border p-4 text-left transition-all duration-200 ${
                      selectedPortfolio === p._id
                        ? "border-[var(--accent)] bg-[var(--accent)]/10"
                        : "border-[var(--border-subtle)] bg-[var(--bg-surface)] hover:border-[var(--border-hover)]"
                    }`}
                  >
                    <span className="text-[14px] font-bold text-[var(--text-primary)]">
                      {p.name}
                    </span>
                    <span className="ml-2 text-[12px] text-[var(--text-muted)]">
                      {p.assets.length} activos
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Question steps */}
        {currentQuestion && (
          <QuestionStep
            question={currentQuestion}
            selected={answers[currentQuestion.id] ?? null}
            onSelect={(optId) =>
              setAnswers((prev) => ({ ...prev, [currentQuestion.id]: optId }))
            }
          />
        )}

        {/* Navigation */}
        <div className="mt-6 flex justify-between">
          <button
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            disabled={step === 0}
            className="flex items-center gap-1 rounded-[var(--radius-lg)] border border-[var(--border-subtle)] px-4 py-2 text-[13px] font-medium text-[var(--text-secondary)] transition hover:border-[var(--border-hover)] disabled:opacity-30"
          >
            <ChevronLeft className="h-4 w-4" /> Anterior
          </button>

          {step < totalSteps ? (
            <button
              onClick={() => setStep((s) => s + 1)}
              disabled={
                (step === 0 && !selectedPortfolio) ||
                (currentQuestion && !answers[currentQuestion.id])
              }
              className="flex items-center gap-1 rounded-[var(--radius-lg)] bg-[var(--accent)] px-4 py-2 text-[13px] font-bold text-white transition hover:opacity-90 disabled:opacity-30"
            >
              Siguiente <ChevronRight className="h-4 w-4" />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!allAnswered || loading}
              className="flex items-center gap-2 rounded-[var(--radius-lg)] bg-[var(--accent)] px-6 py-2 text-[13px] font-bold text-white transition hover:opacity-90 disabled:opacity-30"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" /> Analizando…
                </>
              ) : (
                <>
                  <Target className="h-4 w-4" /> Generar informe
                </>
              )}
            </button>
          )}
        </div>
      </Card>

      {/* Past reports */}
      {pastReports.length > 0 && (
        <Section label="Historial" title="Informes anteriores">
          <div className="space-y-2">
            {pastReports.map((r, i) => (
              <button
                key={r._id ?? i}
                onClick={() => setViewingPast(r)}
                className="flex w-full items-center justify-between rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 text-left transition hover:border-[var(--border-hover)]"
              >
                <div>
                  <span className="text-[13px] font-bold text-[var(--text-primary)]">
                    {PROFILE_LABELS[r.profile.risk_profile] ?? r.profile.risk_profile}
                  </span>
                  <span className="ml-2 text-[12px] text-[var(--text-muted)]">
                    Score: {r.profile.risk_score} · Diversificación: {r.analysis.diversification_score}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {r.created_at && (
                    <span className="text-[11px] text-[var(--text-muted)]">
                      {new Date(r.created_at).toLocaleDateString("es-ES")}
                    </span>
                  )}
                  <ChevronRight className="h-4 w-4 text-[var(--text-muted)]" />
                </div>
              </button>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}
