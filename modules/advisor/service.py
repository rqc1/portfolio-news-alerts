"""
Servicio principal del Advisor – Orquesta cuestionario, análisis y recomendaciones.

Usa el LLM para generar recomendaciones contextualizadas con profundo
conocimiento financiero, explicando el razonamiento detrás de cada sugerencia.
"""

import json
import logging
from typing import Optional

from bson import ObjectId
from datetime import datetime, timezone

from database.mongodb import MongoDB
from modules.advisor.models import (
    InvestorProfile,
    PortfolioAnalysis,
    Recommendation,
    AdvisorReport,
    QuestionnaireAnswer,
)
from modules.advisor.questionnaire import get_questions, compute_profile
from modules.advisor.analyzer import analyze_portfolio
from modules.llm.providers import get_llm_client
from modules.portfolio.models import Portfolio
from modules.market.service import MarketService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompts del sistema para el LLM
# ---------------------------------------------------------------------------
ADVISOR_SYSTEM_PROMPT = """\
Eres un asesor financiero senior con más de 20 años de experiencia en gestión de \
carteras, asset allocation y planificación financiera. Tienes certificación CFA, \
CAIA y CFP. Tu especialidad es analizar carteras de inversores particulares y \
proporcionar recomendaciones personalizadas basadas en su perfil de riesgo, \
horizonte temporal y objetivos.

REGLAS:
1. Tus recomendaciones deben ser específicas y accionables (comprar X, vender Y, \
   reducir Z al N%).
2. Cada recomendación debe explicar el PORQUÉ con fundamento financiero sólido \
   (ratios, teoría moderna de carteras, correlaciones, ciclo económico, etc.).
3. Nunca recomiendes productos que no se ajusten al nivel de conocimiento del inversor.
4. Prioriza la diversificación y la gestión del riesgo.
5. Considera el ciclo económico actual y las tendencias macroeconómicas.
6. Sé directo y honesto. Si la cartera tiene problemas graves, señálalos claramente.
7. Responde SIEMPRE en español.
8. NO des consejos genéricos tipo "diversifique más". Sé ESPECÍFICO.
9. Incluye un disclaimer final indicando que esto es orientativo y no sustituye \
   asesoramiento profesional regulado.

FORMATO de respuesta — JSON estricto:
{
  "resumen_ejecutivo": "Párrafo de 2-3 frases resumen de la situación",
  "diagnostico": "Análisis detallado de la cartera actual vs perfil",
  "recomendaciones": [
    {
      "action": "comprar|vender|reducir|aumentar|mantener",
      "ticker": "TICKER o null si es general",
      "asset_name": "Nombre descriptivo",
      "sector": "Sector",
      "reason": "Explicación detallada del porqué con fundamento financiero",
      "priority": "alta|media|baja",
      "suggested_weight": 0.XX
    }
  ],
  "estrategia_general": "Párrafo explicando la estrategia de conjunto recomendada",
  "disclaimer": "Texto de disclaimer"
}\
"""


def _build_user_prompt(profile: InvestorProfile, portfolio: Portfolio,
                       analysis: PortfolioAnalysis) -> str:
    """Construye el prompt de usuario con toda la información disponible."""

    # Obtener precios reales si es posible
    tickers = portfolio.get_tickers()
    prices = MarketService.get_prices_batch(tickers) if tickers else {}

    assets_desc = []
    total_w = sum(a.weight for a in portfolio.assets) or 1.0
    for a in portfolio.assets:
        w = (a.weight / total_w * 100) if total_w > 0 else 0
        line = (
            f"  - {a.ticker} ({a.name}): {w:.1f}% | Sector: {a.sector or 'N/A'} | "
            f"País: {a.country or 'N/A'} | Industria: {a.industry or 'N/A'}"
        )
        snap = prices.get(a.ticker.upper())
        if snap:
            line += f" | Precio: {snap.price} {snap.currency} ({snap.change_pct:+.2f}% hoy)"
        assets_desc.append(line)
    assets_text = "\n".join(assets_desc) if assets_desc else "  (cartera vacía)"

    sector_desc = "\n".join(
        f"  - {s.category}: actual {s.current_pct:.1f}% vs ideal {s.ideal_pct:.1f}% "
        f"({s.status}, diff {s.diff_pct:+.1f}%)"
        for s in analysis.sector_allocation
    )

    geo_desc = "\n".join(
        f"  - {g.category}: actual {g.current_pct:.1f}% vs ideal {g.ideal_pct:.1f}% "
        f"({g.status}, diff {g.diff_pct:+.1f}%)"
        for g in analysis.geography_allocation
    )

    warnings_text = "\n".join(f"  ⚠ {w}" for w in analysis.warnings) or "  Ninguna"

    return f"""\
=== PERFIL DEL INVERSOR ===
- Perfil de riesgo: {profile.risk_profile.value} (score {profile.risk_score}/100)
- Horizonte temporal: {profile.horizon.value}
- Objetivo principal: {profile.goal.value}
- Nivel de conocimiento: {profile.knowledge.value}
- Pérdida máxima tolerada: {profile.loss_tolerance_pct:.0f}% anual
- Preferencia ESG: {"Sí" if profile.esg_preference else "No"}
- Sectores favoritos: {", ".join(profile.sector_preferences) or "Sin preferencia"}

=== CARTERA ACTUAL ({len(portfolio.assets)} activos) ===
{assets_text}

=== ANÁLISIS DE DIVERSIFICACIÓN ===
- Índice de concentración (HHI): {analysis.concentration_risk:.4f} (0=perfecto, 1=concentrado)
- Score de diversificación: {analysis.diversification_score}/100
- Score de alineación perfil: {analysis.risk_alignment_score}/100

=== DISTRIBUCIÓN SECTORIAL (actual vs ideal para tu perfil) ===
{sector_desc}

=== DISTRIBUCIÓN GEOGRÁFICA (actual vs ideal para tu perfil) ===
{geo_desc}

=== ADVERTENCIAS DETECTADAS ===
{warnings_text}

Genera tu análisis completo y recomendaciones personalizadas en formato JSON.\
"""


def _generate_fallback_recommendations(profile: InvestorProfile, portfolio: Portfolio,
                                       analysis: PortfolioAnalysis) -> list[Recommendation]:
    """Genera recomendaciones deterministas sin LLM como fallback."""
    recommendations: list[Recommendation] = []

    # 1. Recomendar reducir posiciones sobreexpuestas
    for s in analysis.sector_allocation:
        if s.status == "sobreexpuesto" and s.diff_pct > 10:
            # Buscar activos de ese sector
            for a in portfolio.assets:
                if a.sector and a.sector.lower() in s.category.lower():
                    recommendations.append(Recommendation(
                        action="reducir",
                        ticker=a.ticker,
                        asset_name=a.name,
                        sector=s.category,
                        reason=f"El sector {s.category} está sobreexpuesto en tu cartera "
                               f"({s.current_pct:.0f}% actual vs {s.ideal_pct:.0f}% ideal para "
                               f"perfil {profile.risk_profile.value}). Reducir ayuda a equilibrar.",
                        priority="alta" if s.diff_pct > 20 else "media",
                    ))

    # 2. Recomendar aumentar posiciones infraexpuestas
    for s in analysis.sector_allocation:
        if s.status == "infraexpuesto" and s.diff_pct < -10:
            recommendations.append(Recommendation(
                action="comprar",
                asset_name=f"ETF/Fondo del sector {s.category}",
                sector=s.category,
                reason=f"El sector {s.category} está infraexpuesto en tu cartera "
                       f"({s.current_pct:.0f}% actual vs {s.ideal_pct:.0f}% ideal). "
                       f"Incorporar exposición mejora la diversificación.",
                priority="media",
            ))

    # 3. Concentración excesiva
    if analysis.concentration_risk > 0.25:
        total_w = sum(a.weight for a in portfolio.assets) or 1.0
        for a in portfolio.assets:
            pct = a.weight / total_w * 100
            if pct > 25:
                recommendations.append(Recommendation(
                    action="reducir",
                    ticker=a.ticker,
                    asset_name=a.name,
                    sector=a.sector or "",
                    reason=f"{a.ticker} representa el {pct:.0f}% de la cartera. "
                           f"Ningún activo debería superar el 15-20% para un perfil "
                           f"{profile.risk_profile.value}.",
                    priority="alta",
                    current_weight=round(pct, 1),
                    suggested_weight=15.0,
                ))

    # 4. Diversificación geográfica
    for g in analysis.geography_allocation:
        if g.status == "infraexpuesto" and g.diff_pct < -15:
            recommendations.append(Recommendation(
                action="comprar",
                asset_name=f"ETF/Fondo de {g.category}",
                sector="Diversificación geográfica",
                reason=f"Tu cartera tiene solo {g.current_pct:.0f}% en {g.category} "
                       f"vs {g.ideal_pct:.0f}% ideal. Añadir exposición internacional reduce "
                       f"el riesgo país.",
                priority="media",
            ))

    if not recommendations:
        recommendations.append(Recommendation(
            action="mantener",
            asset_name="Cartera actual",
            reason="Tu cartera está razonablemente alineada con tu perfil de riesgo. "
                   "Mantén la estrategia actual y revisa periódicamente.",
            priority="baja",
        ))

    return recommendations


class AdvisorService:
    """Servicio del asesor de inversiones."""

    @staticmethod
    def get_questions():
        return get_questions()

    @staticmethod
    def compute_profile(user_id: str, portfolio_id: str,
                        answers: list[QuestionnaireAnswer]) -> InvestorProfile:
        return compute_profile(user_id, portfolio_id, answers)

    @staticmethod
    async def generate_report(profile: InvestorProfile,
                              portfolio: Portfolio) -> AdvisorReport:
        """Genera el informe completo: análisis + recomendaciones + resumen LLM."""

        # 1. Análisis cuantitativo de la cartera
        analysis = analyze_portfolio(portfolio, profile)

        # 2. Intentar generar recomendaciones con LLM
        llm = get_llm_client()
        recommendations: list[Recommendation] = []
        llm_summary = ""

        if llm.is_available():
            try:
                user_prompt = _build_user_prompt(profile, portfolio, analysis)
                raw = await llm.chat(
                    system_prompt=ADVISOR_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    temperature=0.3,
                    max_tokens=2000,
                )

                # Parsear respuesta JSON del LLM
                # Limpiar posibles marcadores de código
                cleaned = raw.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()

                data = json.loads(cleaned)

                # Extraer recomendaciones
                for rec in data.get("recomendaciones", []):
                    recommendations.append(Recommendation(
                        action=rec.get("action", "mantener"),
                        ticker=rec.get("ticker"),
                        asset_name=rec.get("asset_name", ""),
                        sector=rec.get("sector", ""),
                        reason=rec.get("reason", ""),
                        priority=rec.get("priority", "media"),
                        suggested_weight=rec.get("suggested_weight"),
                    ))

                # Construir resumen
                parts = []
                if data.get("resumen_ejecutivo"):
                    parts.append(f"**Resumen ejecutivo**: {data['resumen_ejecutivo']}")
                if data.get("diagnostico"):
                    parts.append(f"\n**Diagnóstico**: {data['diagnostico']}")
                if data.get("estrategia_general"):
                    parts.append(f"\n**Estrategia recomendada**: {data['estrategia_general']}")
                if data.get("disclaimer"):
                    parts.append(f"\n---\n*{data['disclaimer']}*")
                llm_summary = "\n".join(parts)

                logger.info("Advisor: LLM generated %d recommendations", len(recommendations))
            except json.JSONDecodeError:
                logger.warning("Advisor: LLM response was not valid JSON, using as plain text")
                llm_summary = raw
            except Exception as e:
                logger.warning("Advisor: LLM analysis failed (%s), falling back to deterministic",
                               str(e))

        # 3. Fallback: recomendaciones deterministas si LLM no disponible/falló
        if not recommendations:
            recommendations = _generate_fallback_recommendations(profile, portfolio, analysis)
            if not llm_summary:
                llm_summary = (
                    "⚠ **Análisis generado sin LLM** — Las recomendaciones son deterministas "
                    "basadas en reglas de diversificación y alineación con tu perfil de riesgo. "
                    "Para un análisis más profundo y personalizado, configura un proveedor LLM "
                    "(GITHUB_TOKEN, OPENAI_API_KEY o Ollama local).\n\n"
                    "---\n*Este análisis es orientativo y no constituye asesoramiento financiero "
                    "profesional regulado. Consulta con un asesor certificado antes de tomar "
                    "decisiones de inversión.*"
                )

        report = AdvisorReport(
            profile=profile,
            analysis=analysis,
            recommendations=recommendations,
            llm_summary=llm_summary,
        )

        return report

    @staticmethod
    async def save_report(report: AdvisorReport) -> str:
        """Guarda el informe en MongoDB."""
        doc = report.model_dump()
        doc["created_at"] = datetime.now(timezone.utc)
        result = await MongoDB.db()["advisor_reports"].insert_one(doc)
        return str(result.inserted_id)

    @staticmethod
    async def get_report(report_id: str) -> Optional[dict]:
        """Obtiene un informe guardado."""
        doc = await MongoDB.db()["advisor_reports"].find_one({"_id": ObjectId(report_id)})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    @staticmethod
    async def get_reports_by_portfolio(portfolio_id: str, limit: int = 10) -> list[dict]:
        """Obtiene los informes de una cartera, más recientes primero."""
        cursor = (
            MongoDB.db()["advisor_reports"]
            .find({"profile.portfolio_id": portfolio_id})
            .sort("created_at", -1)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        for doc in docs:
            doc["_id"] = str(doc["_id"])
        return docs
