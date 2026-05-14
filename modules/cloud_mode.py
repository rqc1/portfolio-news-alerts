"""
Cloud-mode classifiers – Reemplazan modelos ML locales por llamadas LLM.

Cuando CLOUD_MODE=true, el sistema NO carga FinBERT, BART-NLI ni
sentence-transformers, reduciendo el uso de RAM de ~2GB a <200MB.
Ideal para deploys en Render free tier (512MB).
"""

import json
import logging
import re

from modules.llm.providers import get_llm_client
from modules.portfolio.models import Portfolio
import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cloud NLP Service (reemplaza spaCy)
# ---------------------------------------------------------------------------
class CloudNLPService:
    """NLP ligero sin spaCy: regex para limpieza, sin NER local."""

    _HTML_TAG = re.compile(r"<[^>]+>")
    _MULTI_SPACE = re.compile(r"\s+")
    _URL = re.compile(r"https?://\S+")

    def process(self, title: str, summary: str, content: str = "") -> dict:
        full_text = f"{title}. {summary}. {content}".strip(". ")
        cleaned = self._clean(full_text)
        language = self._detect_language_simple(cleaned)

        # Extracción simple de orgs: buscar palabras capitalizadas consecutivas
        org_names = self._extract_orgs_simple(cleaned)

        return {
            "cleaned_text": cleaned,
            "cleaned_text_en": cleaned,  # Asumimos inglés (RSS feeds son en inglés)
            "language": language,
            "entities": [],
            "org_names": org_names,
            "char_count": len(cleaned),
        }

    def _clean(self, text: str) -> str:
        text = self._HTML_TAG.sub(" ", text)
        text = self._URL.sub("", text)
        text = self._MULTI_SPACE.sub(" ", text)
        return text.strip()

    @staticmethod
    def _detect_language_simple(text: str) -> str:
        spanish_words = {"de", "la", "el", "en", "que", "los", "las", "del", "por", "una", "con"}
        words = text.lower().split()[:50]
        spanish_count = sum(1 for w in words if w in spanish_words)
        return "es" if spanish_count > 5 else "en"

    @staticmethod
    def _extract_orgs_simple(text: str) -> list[str]:
        """Extrae posibles nombres de organizaciones por heurísticas."""
        # Buscar secuencias de palabras capitalizadas (2+ palabras)
        pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
        matches = re.findall(pattern, text)
        # Filtrar comunes
        stop_orgs = {"The", "This", "That", "These", "Those", "Monday", "Tuesday",
                     "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
        return [m for m in set(matches) if m.split()[0] not in stop_orgs][:10]


class LLMSentiment:
    """Análisis de sentimiento vía LLM (reemplaza FinBERT)."""

    async def predict(self, text: str) -> dict:
        client = get_llm_client()
        prompt = f"""Analyze the financial sentiment of this text. Respond with ONLY a JSON object:
{{"sentiment": "positive"|"negative"|"neutral", "confidence": 0.0-1.0}}

Text: {text[:500]}"""

        try:
            response = await client.chat(
                system_prompt="You are a financial sentiment analyzer. Respond only with valid JSON.",
                user_prompt=prompt,
                temperature=0.1,
                max_tokens=100,
            )
            data = json.loads(_extract_json(response))
            return {
                "sentiment": data.get("sentiment", "neutral"),
                "confidence": float(data.get("confidence", 0.5)),
                "probabilities": {},
            }
        except Exception:
            logger.warning("LLM sentiment failed, defaulting to neutral")
            return {"sentiment": "neutral", "confidence": 0.5, "probabilities": {}}


class LLMEventClassifier:
    """Clasificación de eventos vía LLM (reemplaza BART zero-shot NLI)."""

    async def classify(self, text: str) -> dict:
        client = get_llm_client()
        events_list = ", ".join(config.EVENT_TAXONOMY)
        prompt = f"""Classify this financial news into ONE event type.
Valid types: {events_list}

Respond with ONLY a JSON object:
{{"event_type": "<type>", "confidence": 0.0-1.0}}

News: {text[:500]}"""

        try:
            response = await client.chat(
                system_prompt="You are a financial event classifier. Respond only with valid JSON.",
                user_prompt=prompt,
                temperature=0.1,
                max_tokens=100,
            )
            data = json.loads(_extract_json(response))
            event_type = data.get("event_type", "otro")
            if event_type not in config.EVENT_TAXONOMY:
                event_type = "otro"
            return {
                "event_type": event_type,
                "confidence": float(data.get("confidence", 0.5)),
                "reasoning": "LLM classification",
            }
        except Exception:
            logger.warning("LLM event classification failed, defaulting to otro")
            return {"event_type": "otro", "confidence": 0.3, "reasoning": "LLM fallback"}


class LLMRelevanceScorer:
    """Relevancia semántica vía LLM (reemplaza sentence-transformers embeddings)."""

    async def compute(self, news_text: str, portfolio: Portfolio) -> dict:
        client = get_llm_client()
        tickers = portfolio.get_tickers()
        assets_desc = ", ".join(
            f"{a.ticker} ({a.name}, {a.sector})" for a in portfolio.assets
        )
        prompt = f"""Given this portfolio: {assets_desc}

Rate the relevance of this news to the portfolio (0.0 to 1.0).
Consider direct mentions, sector impact, and indirect effects.

Respond with ONLY a JSON object:
{{"relevance_score": 0.0-1.0, "matched_assets": ["TICKER1"], "reason": "brief reason"}}

News: {news_text[:400]}"""

        try:
            response = await client.chat(
                system_prompt="You are a portfolio relevance analyzer. Respond only with valid JSON.",
                user_prompt=prompt,
                temperature=0.1,
                max_tokens=200,
            )
            data = json.loads(_extract_json(response))
            matched = [t for t in data.get("matched_assets", []) if t in tickers]
            return {
                "semantic_score": float(data.get("relevance_score", 0.0)),
                "matched_assets": matched,
                "portfolio_description": assets_desc[:200],
            }
        except Exception:
            logger.warning("LLM relevance scoring failed")
            return {"semantic_score": 0.0, "matched_assets": [], "portfolio_description": ""}


class CloudEventClassificationService:
    """Servicio combinado cloud: sentimiento + evento vía LLM."""

    def __init__(self):
        self.sentiment = LLMSentiment()
        self.event_classifier = LLMEventClassifier()

    async def classify(self, cleaned_text: str) -> dict:
        sentiment = await self.sentiment.predict(cleaned_text)
        event = await self.event_classifier.classify(cleaned_text)
        return {
            "sentiment": sentiment,
            "event_type": event.get("event_type", "otro"),
            "event_confidence": event.get("confidence", 0.0),
            "event_reasoning": event.get("reasoning", ""),
        }


class CloudRelevanceService:
    """Servicio de relevancia cloud: reglas + LLM (sin embeddings locales)."""

    def __init__(self):
        from modules.relevance.service import RuleBasedRelevance
        self.rule_engine = RuleBasedRelevance()
        self.llm_scorer = LLMRelevanceScorer()

    async def compute_relevance(
        self, cleaned_text: str, org_names: list[str], portfolio: Portfolio
    ) -> dict:
        text_lower = cleaned_text.lower()

        # Capa 1: Reglas (rápido, sin coste)
        rule_result = self.rule_engine.compute(text_lower, org_names, portfolio)
        direct = rule_result["direct_score"]

        # Si ya hay match directo fuerte, no gastar LLM en relevancia
        if direct >= 0.8:
            return {
                "relevance_score": direct,
                "matched_assets": rule_result["matched_assets"],
                "sector_match": rule_result["sector_match"],
            }

        # Capa 2: LLM (para casos sin match directo)
        llm_result = await self.llm_scorer.compute(cleaned_text, portfolio)
        semantic = llm_result["semantic_score"]

        # Combinar
        if direct >= 0.5:
            combined = 0.5 * direct + 0.5 * semantic
        else:
            combined = 0.3 * direct + 0.7 * semantic

        # Merge matched assets
        matched = list(set(rule_result["matched_assets"] + llm_result.get("matched_assets", [])))

        return {
            "relevance_score": combined,
            "matched_assets": matched,
            "sector_match": rule_result["sector_match"],
        }


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def _extract_json(text: str) -> str:
    """Extrae JSON de una respuesta LLM que puede contener markdown."""
    # Try to find JSON in code blocks
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        return match.group(1)
    # Try raw JSON
    match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    return text
