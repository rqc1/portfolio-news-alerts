"""
Módulo 5 – Clasificación de eventos financieros.

Taxonomía de eventos y clasificación híbrida:
  - FinBERT (sentiment baseline)
  - LLM (OpenAI API) para clasificación de tipo de evento
"""

import json
import logging
from functools import lru_cache

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

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
# LLM – Clasificación de tipo de evento
# ---------------------------------------------------------------------------
class LLMEventClassifier:
    """Clasificación de tipo de evento usando OpenAI API."""

    SYSTEM_PROMPT = """Eres un analista financiero experto. Tu tarea es clasificar noticias financieras 
según el tipo de evento que describen. Debes responder SOLO con un JSON válido.

Categorías posibles:
{categories}

Responde con este formato exacto:
{{"event_type": "<categoría>", "confidence": <0.0-1.0>, "reasoning": "<explicación breve>"}}"""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=config.OPENAI_API_KEY)
        return self._client

    def classify(self, text: str) -> dict:
        if not config.OPENAI_API_KEY:
            return self._fallback_classify(text)

        categories = "\n".join(
            f"- {k}: {v}" for k, v in EVENT_DESCRIPTIONS.items()
        )
        system = self.SYSTEM_PROMPT.format(categories=categories)

        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"Clasifica esta noticia:\n\n{text[:1000]}"},
                ],
                temperature=0.1,
                max_tokens=200,
            )
            content = response.choices[0].message.content.strip()
            # Parsear JSON de la respuesta
            result = json.loads(content)
            if result.get("event_type") not in EVENT_LABELS:
                result["event_type"] = "otro"
            return result

        except Exception:
            logger.exception("Error en clasificación LLM, usando fallback")
            return self._fallback_classify(text)

    def _fallback_classify(self, text: str) -> dict:
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
    """Combina FinBERT (sentiment) con LLM (tipo de evento)."""

    def __init__(self):
        self.sentiment_model = FinBERTSentiment()
        self.event_classifier = LLMEventClassifier()

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
