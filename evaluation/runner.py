"""
Runner del pipeline sobre el corpus de evaluación.

Carga el dataset etiquetado (`dataset.jsonl`) y las carteras de referencia
(`portfolios.json`), ejecuta el pipeline en una de las variantes definidas
y devuelve una lista de `PipelinePrediction` lista para evaluar.

Variantes (ablation):
  - rules       : solo capa rule-based de relevancia + impacto determinista
  - hybrid      : rules + similitud semántica + impacto determinista (sin LLM)
  - hybrid_nli  : hybrid + clasificación de evento con FinBERT/NLI
  - full        : pipeline completo, incluyendo LLM contextual si está disponible

`full` cae automáticamente a `hybrid_nli` si no hay API key del LLM, lo que
permite ejecutar todo el ablation sin claves configuradas.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Iterable

from evaluation.schema import LabeledNews, PipelinePrediction
from modules.portfolio.models import Asset, Portfolio
from modules.nlp.preprocessing import NLPService
from modules.relevance.service import (
    RelevanceService,
    RuleBasedRelevance,
    SemanticRelevance,
)
from modules.events.classifier import EventClassificationService
from modules.impact.estimator import ImpactEstimator, _severity_label
from modules.llm.analyzer import ContextualAnalyzer, RelevanceChecker
from modules.llm.providers import get_llm_client

import config

logger = logging.getLogger(__name__)

EVAL_DIR = Path(__file__).resolve().parent
DATASET_PATH = EVAL_DIR / "dataset.jsonl"
PORTFOLIOS_PATH = EVAL_DIR / "portfolios.json"

VARIANTS = ("rules", "hybrid", "hybrid_nli", "full")


# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------
def load_dataset(path: Path = DATASET_PATH) -> list[LabeledNews]:
    examples: list[LabeledNews] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            examples.append(LabeledNews(**json.loads(line)))
    return examples


def load_portfolios(path: Path = PORTFOLIOS_PATH) -> dict[str, Portfolio]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    portfolios: dict[str, Portfolio] = {}
    for item in raw:
        assets = [Asset(**a) for a in item["assets"]]
        portfolios[item["portfolio_id"]] = Portfolio(
            user_id="eval",
            name=item["name"],
            assets=assets,
        )
    return portfolios


# ---------------------------------------------------------------------------
# Lógica del runner
# ---------------------------------------------------------------------------
class PipelineRunner:
    """Ejecuta una variante del pipeline sobre cada noticia del dataset."""

    def __init__(self, variant: str = "full"):
        if variant not in VARIANTS:
            raise ValueError(f"Variante desconocida: {variant}. Opciones: {VARIANTS}")
        self.variant = variant

        self.nlp = NLPService()
        self.rules = RuleBasedRelevance()
        # Capas opcionales según variante
        self.semantic = SemanticRelevance() if variant != "rules" else None
        self.events = EventClassificationService() if variant in ("hybrid_nli", "full") else None
        self.contextual = ContextualAnalyzer() if variant == "full" else None
        self.relevance_checker = RelevanceChecker() if variant == "full" else None

        # Detectar si se puede usar LLM
        self._llm_available = False
        if variant == "full":
            try:
                self._llm_available = get_llm_client().is_available()
            except Exception:
                self._llm_available = False
            if not self._llm_available:
                logger.warning(
                    "Variante 'full' solicitada pero LLM no disponible; se degrada a 'hybrid_nli'"
                )
                self.variant = "hybrid_nli"

    # ---- relevancia ----
    def _compute_relevance(self, cleaned: str, orgs: list[str], portfolio: Portfolio) -> dict:
        text_lower = cleaned.lower()
        rule_result = self.rules.compute(text_lower, orgs, portfolio)
        direct = rule_result["direct_score"]

        if self.semantic is None:
            combined = direct
            semantic_score = 0.0
        else:
            sem = self.semantic.compute(cleaned, portfolio)
            semantic_score = sem["semantic_score"]
            if direct >= 0.8:
                combined = 0.7 * direct + 0.3 * semantic_score
            elif direct >= 0.5:
                combined = 0.5 * direct + 0.5 * semantic_score
            else:
                combined = 0.3 * direct + 0.7 * semantic_score

        return {
            "relevance_score": min(combined, 1.0),
            "matched_assets": rule_result["matched_assets"],
            "direct_score": direct,
            "semantic_score": semantic_score,
        }

    # ---- pipeline ----
    async def run_one(
        self,
        example: LabeledNews,
        portfolio: Portfolio,
    ) -> PipelinePrediction:
        # Predicción inicial vacía
        pred = PipelinePrediction(
            id=example.id,
            portfolio_id=example.portfolio_id,
            is_relevant=False,
            relevance_score=0.0,
            variant=self.variant,
        )

        # 1. NLP
        nlp_result = self.nlp.process(example.title, example.summary, example.content)
        cleaned = nlp_result["cleaned_text"]
        cleaned_en = nlp_result.get("cleaned_text_en", cleaned)
        orgs = nlp_result["org_names"]

        # 2. Relevancia
        rel = self._compute_relevance(cleaned, orgs, portfolio)
        pred.relevance_score = round(rel["relevance_score"], 4)
        pred.direct_score = round(rel["direct_score"], 4)
        pred.semantic_score = round(rel["semantic_score"], 4)
        pred.matched_assets = rel["matched_assets"]

        rscore = rel["relevance_score"]

        # 2b. LLM borderline (solo en 'full')
        if (
            self.variant == "full"
            and self._llm_available
            and rscore < config.ALERT_RELEVANCE_THRESHOLD
            and rscore >= config.ALERT_RELEVANCE_BORDERLINE
        ):
            try:
                llm_rel = await self.relevance_checker.check(
                    example.title, example.summary, portfolio
                )
                if llm_rel and llm_rel.get("is_relevant"):
                    rscore = max(rscore, llm_rel.get("relevance_score", rscore))
                    pred.relevance_score = round(rscore, 4)
                    for asset in llm_rel.get("affected_assets", []):
                        if asset not in pred.matched_assets:
                            pred.matched_assets.append(asset)
                else:
                    pred.discarded_at = "relevance_llm"
                    return pred
            except Exception:
                logger.exception("LLM relevance check falló")

        # Filtro final de relevancia
        if rscore < config.ALERT_RELEVANCE_THRESHOLD:
            pred.discarded_at = "relevance"
            return pred

        pred.is_relevant = True

        # 3. Eventos (solo si la variante lo incluye)
        if self.events is None:
            return pred

        event_result = self.events.classify(cleaned_en)
        pred.event_type = event_result["event_type"]
        pred.event_confidence = event_result["event_confidence"]
        pred.sentiment = event_result["sentiment"]["sentiment"]
        pred.sentiment_confidence = event_result["sentiment"]["confidence"]

        # 4. Impacto determinista
        impact_det = ImpactEstimator.estimate(
            sentiment=event_result["sentiment"],
            event_type=event_result["event_type"],
            event_confidence=event_result["event_confidence"],
            relevance_score=rscore,
            matched_assets=pred.matched_assets,
        )

        # 5. Análisis contextual LLM (solo en 'full')
        llm_analysis = None
        if self.variant == "full" and self._llm_available:
            try:
                llm_analysis = await self.contextual.analyze(
                    title=example.title,
                    text=cleaned,
                    source=example.source,
                    sentiment=event_result["sentiment"],
                    matched_assets=pred.matched_assets,
                    relevance_score=rscore,
                    portfolio=portfolio,
                )
            except Exception:
                logger.exception("ContextualAnalyzer falló")

        impact = ImpactEstimator.merge_with_llm(impact_det, llm_analysis)

        if llm_analysis and llm_analysis.get("event_type"):
            pred.event_type = llm_analysis["event_type"]

        pred.direction = impact["direction"]
        pred.severity = impact["severity"]
        pred.severity_label = _severity_label(impact["severity"])
        pred.confidence = impact["confidence"]
        return pred

    async def run_all(
        self,
        dataset: list[LabeledNews],
        portfolios: dict[str, Portfolio],
    ) -> list[PipelinePrediction]:
        predictions: list[PipelinePrediction] = []
        for example in dataset:
            portfolio = portfolios.get(example.portfolio_id)
            if portfolio is None:
                logger.warning("Cartera %s no encontrada para %s",
                               example.portfolio_id, example.id)
                continue
            try:
                pred = await self.run_one(example, portfolio)
            except Exception:
                logger.exception("Error procesando %s", example.id)
                pred = PipelinePrediction(
                    id=example.id,
                    portfolio_id=example.portfolio_id,
                    is_relevant=False,
                    relevance_score=0.0,
                    variant=self.variant,
                    discarded_at="error",
                )
            predictions.append(pred)
        return predictions


# ---------------------------------------------------------------------------
# CLI helper
# ---------------------------------------------------------------------------
async def run_variant(
    variant: str,
    dataset: list[LabeledNews] | None = None,
    portfolios: dict[str, Portfolio] | None = None,
) -> list[PipelinePrediction]:
    if dataset is None:
        dataset = load_dataset()
    if portfolios is None:
        portfolios = load_portfolios()
    runner = PipelineRunner(variant=variant)
    return await runner.run_all(dataset, portfolios)


def predictions_to_jsonl(predictions: Iterable[PipelinePrediction]) -> str:
    return "\n".join(p.model_dump_json() for p in predictions)
