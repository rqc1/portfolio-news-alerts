"""
Módulo 4 – Relevancia por cartera.

Capa híbrida: reglas explícitas + similitud semántica con embeddings.
Calcula un score continuo de relevancia contextual noticia ↔ cartera.
"""

import logging
import re
from functools import lru_cache

import numpy as np

import config
from modules.portfolio.models import Portfolio

logger = logging.getLogger(__name__)

# Tickers o nombres cortos que son palabras comunes en inglés/español
_COMMON_WORDS = {"a", "an", "it", "ai", "us", "or", "all", "on", "at", "am", "be", "do", "go", "no", "so"}


@lru_cache(maxsize=1)
def _load_embedding_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(config.EMBEDDING_MODEL)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(dot / norm)


def _is_name_match(name: str, text_lower: str) -> bool:
    """Match con word boundaries para evitar falsos positivos con nombres cortos."""
    if not name:
        return False
    name_lower = name.lower()
    # Nombres de ≤3 caracteres o que son palabras comunes requieren word-boundary match
    if len(name_lower) <= 3 or name_lower in _COMMON_WORDS:
        pattern = r'\b' + re.escape(name_lower) + r'\b'
        return bool(re.search(pattern, text_lower))
    return name_lower in text_lower


class RuleBasedRelevance:
    """Capa 1: reglas explícitas de matching directo."""

    @staticmethod
    def compute(
        text_lower: str,
        org_names: list[str],
        portfolio: Portfolio,
    ) -> dict:
        matched_assets = []
        direct_score = 0.0

        for asset in portfolio.assets:
            names_to_check = [asset.ticker, asset.name]
            names_to_check.extend(asset.aliases)

            for name in names_to_check:
                if _is_name_match(name, text_lower):
                    matched_assets.append(asset.ticker)
                    direct_score = max(direct_score, 0.9)
                    break

            # Check NER-extracted orgs against asset names
            for org in org_names:
                org_lower = org.lower()
                if org_lower in asset.name.lower() or asset.name.lower() in org_lower:
                    if asset.ticker not in matched_assets:
                        matched_assets.append(asset.ticker)
                        direct_score = max(direct_score, 0.8)

        # Sector-level matching
        portfolio_sectors = portfolio.get_sectors()
        sector_match = False
        for sector in portfolio_sectors:
            if sector.lower() in text_lower:
                sector_match = True
                direct_score = max(direct_score, 0.5)

        # Country-level matching
        portfolio_countries = portfolio.get_countries()
        country_match = False
        for country in portfolio_countries:
            if _is_name_match(country, text_lower):
                country_match = True
                direct_score = max(direct_score, 0.3)

        return {
            "matched_assets": matched_assets,
            "direct_score": direct_score,
            "sector_match": sector_match,
            "country_match": country_match,
        }


class SemanticRelevance:
    """Capa 2: similitud semántica con embeddings."""

    def __init__(self):
        self.model = _load_embedding_model()

    def compute(self, news_text: str, portfolio: Portfolio) -> dict:
        # Crear descripción semántica de la cartera
        portfolio_desc_parts = []
        for asset in portfolio.assets:
            parts = [asset.name, asset.ticker]
            if asset.sector:
                parts.append(asset.sector)
            if asset.industry:
                parts.append(asset.industry)
            if asset.country:
                parts.append(asset.country)
            portfolio_desc_parts.append(", ".join(parts))

        portfolio_text = ". ".join(portfolio_desc_parts)

        # Truncar para embedding
        news_truncated = news_text[:512]
        portfolio_truncated = portfolio_text[:512]

        emb_news = self.model.encode(news_truncated)
        emb_portfolio = self.model.encode(portfolio_truncated)

        similarity = _cosine_similarity(emb_news, emb_portfolio)

        return {
            "semantic_score": float(similarity),
            "portfolio_description": portfolio_text[:200],
        }


class RelevanceService:
    """Fachada que combina reglas y semántica para un score final de relevancia."""

    def __init__(self):
        self.rule_engine = RuleBasedRelevance()
        self.semantic_engine = SemanticRelevance()

    def compute_relevance(
        self,
        cleaned_text: str,
        org_names: list[str],
        portfolio: Portfolio,
    ) -> dict:
        text_lower = cleaned_text.lower()

        # Capa 1: Reglas
        rule_result = self.rule_engine.compute(text_lower, org_names, portfolio)

        # Capa 2: Semántica
        semantic_result = self.semantic_engine.compute(cleaned_text, portfolio)

        # Score combinado (ponderado)
        # Si hay match directo, priorizarlo; semántica como complemento
        direct = rule_result["direct_score"]
        semantic = semantic_result["semantic_score"]

        if direct >= 0.8:
            combined = 0.7 * direct + 0.3 * semantic
        elif direct >= 0.5:
            combined = 0.5 * direct + 0.5 * semantic
        else:
            combined = 0.3 * direct + 0.7 * semantic

        combined = min(combined, 1.0)

        return {
            "relevance_score": round(combined, 4),
            "matched_assets": rule_result["matched_assets"],
            "direct_score": round(direct, 4),
            "semantic_score": round(semantic, 4),
            "sector_match": rule_result["sector_match"],
            "country_match": rule_result["country_match"],
        }
