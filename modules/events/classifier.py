"""
Módulo 5 – Clasificación de eventos financieros.

Taxonomía de eventos y clasificación híbrida:
  - FinBERT (sentiment baseline)
  - Zero-shot NLI (tipo de evento — local, sin coste API)
  - Fallback por keywords (cuando NLI no está disponible)
"""

import logging
from functools import lru_cache

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Taxonomía
# ---------------------------------------------------------------------------
EVENT_LABELS = config.EVENT_TAXONOMY

EVENT_DESCRIPTIONS = {
    "resultados_empresariales": "Earnings reports, quarterly results, revenue figures, EPS",
    "guidance_profit_warning": "Profit warnings, guidance updates, outlook revisions, downgrades",
    "regulacion": "Regulatory actions, fines, policy changes, sanctions, compliance",
    "litigio": "Lawsuits, legal disputes, settlements, court rulings, investigations",
    "fusion_adquisicion": "Mergers, acquisitions, takeovers, buyouts, joint ventures",
    "ciberincidente": "Data breaches, cyberattacks, security incidents, ransomware",
    "incidencia_operativa": "Supply disruptions, outages, recalls, operational failures",
    "macroeconomia": "Central bank decisions, interest rates, inflation, GDP, employment",
    "cadena_suministro": "Supply chain issues, logistics, raw materials, shipping delays",
    "cambio_directivo": "CEO changes, board appointments, executive departures, governance",
    "dividendo_recompra": "Dividend announcements, share buybacks, capital returns",
    "otro": "Other financial events not categorized above",
}


# ---------------------------------------------------------------------------
# FinBERT – Sentiment Analysis
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _load_finbert():
    tokenizer = AutoTokenizer.from_pretrained(config.FINBERT_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(config.FINBERT_MODEL)
    model.eval()
    return tokenizer, model


class FinBERTSentiment:
    """Análisis de sentimiento financiero con FinBERT."""

    LABELS = ["positive", "negative", "neutral"]

    def __init__(self):
        self.tokenizer, self.model = _load_finbert()

    def predict(self, text: str) -> dict:
        inputs = self.tokenizer(
            text[:512], return_tensors="pt", truncation=True, max_length=512
        )
        with torch.no_grad():
            outputs = self.model(**inputs)
        probs = torch.softmax(outputs.logits, dim=-1).squeeze().tolist()

        label_idx = int(torch.argmax(outputs.logits, dim=-1))
        return {
            "sentiment": self.LABELS[label_idx],
            "confidence": round(probs[label_idx], 4),
            "probabilities": {
                label: round(p, 4)
                for label, p in zip(self.LABELS, probs)
            },
        }


# ---------------------------------------------------------------------------
# Zero-shot NLI – Clasificación de tipo de evento (local, sin coste API)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _load_nli_pipeline():
    logger.info("Cargando modelo NLI: %s", config.NLI_MODEL)
    return pipeline(
        "zero-shot-classification",
        model=config.NLI_MODEL,
        device=-1,  # CPU; cambiar a 0 para GPU
    )


class ZeroShotEventClassifier:
    """Clasificación de tipo de evento financiero mediante zero-shot NLI."""

    def __init__(self):
        self._pipeline = None

    def _get_pipeline(self):
        if self._pipeline is None:
            self._pipeline = _load_nli_pipeline()
        return self._pipeline

    def classify(self, text: str) -> dict:
        try:
            clf = self._get_pipeline()
            # Usar las descripciones en inglés como hipótesis (más precisas)
            candidate_labels = list(EVENT_DESCRIPTIONS.values())
            label_to_event = {v: k for k, v in EVENT_DESCRIPTIONS.items()}

            result = clf(
                text[:512],
                candidate_labels=candidate_labels,
                multi_label=False,
            )

            top_label = result["labels"][0]
            top_score = result["scores"][0]
            event_type = label_to_event.get(top_label, "otro")

            return {
                "event_type": event_type,
                "confidence": round(top_score, 4),
                "reasoning": f"Zero-shot NLI: {top_label} (score: {top_score:.3f})",
            }

        except Exception:
            logger.exception("Error en zero-shot NLI, usando fallback por keywords")
            return self._fallback_classify(text)

    @staticmethod
    def _fallback_classify(text: str) -> dict:
        """Clasificación basada en keywords cuando LLM no está disponible."""
        text_lower = text.lower()
        keyword_map = {
            "resultados_empresariales": ["earnings", "revenue", "profit", "quarterly results", "eps", "resultados", "beneficio"],
            "guidance_profit_warning": ["guidance", "outlook", "profit warning", "downgrade", "forecast"],
            "regulacion": ["regulatory", "regulation", "fine", "sanction", "compliance", "regulación", "sanción", "multa"],
            "litigio": ["lawsuit", "litigation", "court", "settlement", "investigation", "demanda", "litigio"],
            "fusion_adquisicion": ["merger", "acquisition", "takeover", "buyout", "deal", "fusión", "adquisición", "opa"],
            "ciberincidente": ["cyber", "breach", "hack", "ransomware", "data leak", "ciberataque"],
            "incidencia_operativa": ["outage", "recall", "failure", "disruption", "operational"],
            "macroeconomia": ["interest rate", "inflation", "gdp", "central bank", "fed", "bce", "tipos de interés"],
            "cadena_suministro": ["supply chain", "logistics", "shipping", "shortage", "cadena de suministro"],
            "cambio_directivo": ["ceo", "board", "executive", "appointed", "resign", "consejero", "directivo"],
            "dividendo_recompra": ["dividend", "buyback", "share repurchase", "dividendo", "recompra"],
        }

        best_match = "otro"
        best_count = 0
        for event, keywords in keyword_map.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count > best_count:
                best_count = count
                best_match = event

        confidence = min(0.3 + best_count * 0.15, 0.85) if best_count > 0 else 0.1
        return {
            "event_type": best_match,
            "confidence": round(confidence, 4),
            "reasoning": f"Keyword fallback: {best_count} matches for '{best_match}'",
        }


# ---------------------------------------------------------------------------
# Servicio combinado
# ---------------------------------------------------------------------------
class EventClassificationService:
    """Combina FinBERT (sentiment) con zero-shot NLI (tipo de evento)."""

    def __init__(self):
        self.sentiment_model = FinBERTSentiment()
        self.event_classifier = ZeroShotEventClassifier()

    def classify(self, cleaned_text: str) -> dict:
        # Sentiment con FinBERT
        sentiment = self.sentiment_model.predict(cleaned_text)

        # Tipo de evento con LLM (o fallback)
        event = self.event_classifier.classify(cleaned_text)

        return {
            "sentiment": sentiment,
            "event_type": event.get("event_type", "otro"),
            "event_confidence": event.get("confidence", 0.0),
            "event_reasoning": event.get("reasoning", ""),
        }
