"""
Módulo 3 – Preprocesado NLP.

Limpieza de texto, detección de idioma, tokenización y NER financiero.
"""

import logging
import re
from functools import lru_cache

import spacy
from langdetect import detect

import config

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_spacy():
    try:
        return spacy.load(config.SPACY_MODEL)
    except OSError:
        logger.warning("Modelo spaCy '%s' no encontrado. Descargando...", config.SPACY_MODEL)
        from spacy.cli import download
        download(config.SPACY_MODEL)
        return spacy.load(config.SPACY_MODEL)


class TextPreprocessor:
    """Limpieza y normalización de texto financiero."""

    _HTML_TAG = re.compile(r"<[^>]+>")
    _MULTI_SPACE = re.compile(r"\s+")
    _URL = re.compile(r"https?://\S+")

    @staticmethod
    def clean(text: str) -> str:
        text = TextPreprocessor._HTML_TAG.sub(" ", text)
        text = TextPreprocessor._URL.sub("", text)
        text = TextPreprocessor._MULTI_SPACE.sub(" ", text)
        return text.strip()

    @staticmethod
    def detect_language(text: str) -> str:
        try:
            return detect(text)
        except Exception:
            return "unknown"


class EntityExtractor:
    """Reconocimiento de entidades nombradas con spaCy."""

    FINANCIAL_LABELS = {"ORG", "PERSON", "GPE", "NORP", "MONEY", "PERCENT", "DATE", "LAW"}

    def __init__(self):
        self.nlp = _load_spacy()

    def extract(self, text: str) -> list[dict]:
        doc = self.nlp(text[:100_000])  # limitar longitud
        entities = []
        seen = set()
        for ent in doc.ents:
            if ent.label_ in self.FINANCIAL_LABELS:
                key = (ent.text.lower(), ent.label_)
                if key not in seen:
                    seen.add(key)
                    entities.append({
                        "text": ent.text,
                        "label": ent.label_,
                        "start": ent.start_char,
                        "end": ent.end_char,
                    })
        return entities

    def extract_org_names(self, text: str) -> list[str]:
        doc = self.nlp(text[:100_000])
        orgs = set()
        for ent in doc.ents:
            if ent.label_ == "ORG":
                orgs.add(ent.text)
        return list(orgs)


class NLPService:
    """Fachada para el preprocesado NLP completo."""

    def __init__(self):
        self.preprocessor = TextPreprocessor()
        self.entity_extractor = EntityExtractor()

    def process(self, title: str, summary: str, content: str = "") -> dict:
        full_text = f"{title}. {summary}. {content}".strip(". ")
        cleaned = self.preprocessor.clean(full_text)
        language = self.preprocessor.detect_language(cleaned[:500])
        entities = self.entity_extractor.extract(cleaned)
        org_names = [e["text"] for e in entities if e["label"] == "ORG"]

        return {
            "cleaned_text": cleaned,
            "language": language,
            "entities": entities,
            "org_names": org_names,
            "char_count": len(cleaned),
        }
