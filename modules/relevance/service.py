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
from modules.nlp.entity_resolver import EntityResolver, normalize_company_name

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
    """Capa 1: reglas explícitas de matching directo.

    Usa un `EntityResolver` que normaliza nombres a forma canónica (eliminando
    sufijos societarios, acentos y puntuación) y aplica guardas de ambigüedad,
    en lugar del matching por substring ingenuo. Esto reduce tanto los falsos
    negativos por variantes del nombre («Apple Inc.» vs «Apple») como los
    falsos positivos por tickers cortos que coinciden con palabras comunes.
    """

    # Caché de resolvers por firma de cartera (construirlos es barato pero
    # recurrente en el pipeline).
    _resolver_cache: dict[str, EntityResolver] = {}

    @classmethod
    def _get_resolver(cls, portfolio: Portfolio) -> EntityResolver:
        sig = str(hash(tuple(
            (a.ticker, a.name, tuple(a.aliases)) for a in portfolio.assets
        )))
        resolver = cls._resolver_cache.get(sig)
        if resolver is None:
            resolver = EntityResolver.from_portfolio(portfolio)
            if len(cls._resolver_cache) > 64:
                cls._resolver_cache.clear()
            cls._resolver_cache[sig] = resolver
        return resolver

    @classmethod
    def compute(
        cls,
        text_lower: str,
        org_names: list[str],
        portfolio: Portfolio,
    ) -> dict:
        matched_assets: list[str] = []
        direct_score = 0.0

        # --- Resolución canónica de entidades sobre el texto completo ---
        resolver = cls._get_resolver(portfolio)
        resolved = resolver.resolve(text_lower)
        for r in resolved:
            if r["ticker"] not in matched_assets:
                matched_assets.append(r["ticker"])
            direct_score = max(direct_score, r["score"])

        # --- Resolución canónica de las organizaciones extraídas por NER ---
        if org_names:
            org_text = " . ".join(org_names)
            for r in resolver.resolve(org_text):
                if r["ticker"] not in matched_assets:
                    matched_assets.append(r["ticker"])
                direct_score = max(direct_score, min(r["score"], 0.85))

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
    """Capa 2: similitud semántica con embeddings.

    Mejoras frente a la versión ingenua (un único embedding de toda la
    cartera concatenada):

      - Embedding POR ACTIVO: cada activo se describe y embebe por separado,
        de modo que una noticia muy relevante para un único valor no queda
        diluida por el resto de la cartera.
      - MAX-POOLING: el score de relevancia semántica es la máxima similitud
        coseno noticia ↔ activo (señal "¿es relevante para ALGÚN activo?"),
        complementada con la media como señal de relevancia transversal.
      - CACHÉ de embeddings de cartera: los embeddings por activo se cachean
        por firma de cartera, evitando recodificar en cada noticia.
      - Sin truncado arbitrario a 512 caracteres: se usa una ventana
        representativa y se delega el truncado a nivel de token en el modelo.
    """

    # Ventana de caracteres de la noticia a codificar. El modelo trunca
    # internamente a nivel de token (max_seq_length); este límite evita
    # codificar textos patológicamente largos.
    _NEWS_CHAR_LIMIT = 1200

    def __init__(self):
        self.model = _load_embedding_model()
        # Caché: firma de cartera -> (lista de tickers, matriz de embeddings).
        self._portfolio_cache: dict[str, tuple[list[str], np.ndarray]] = {}

    @staticmethod
    def _asset_description(asset) -> str:
        parts = [asset.name, asset.ticker]
        if asset.sector:
            parts.append(asset.sector)
        if asset.industry:
            parts.append(asset.industry)
        if asset.country:
            parts.append(asset.country)
        return ", ".join(p for p in parts if p)

    @staticmethod
    def _portfolio_signature(portfolio: Portfolio) -> str:
        items = tuple(
            (a.ticker, a.name, a.sector or "", a.industry or "", a.country or "")
            for a in portfolio.assets
        )
        return str(hash(items))

    def _portfolio_embeddings(self, portfolio: Portfolio) -> tuple[list[str], np.ndarray]:
        sig = self._portfolio_signature(portfolio)
        cached = self._portfolio_cache.get(sig)
        if cached is not None:
            return cached
        tickers = [a.ticker for a in portfolio.assets]
        descriptions = [self._asset_description(a) for a in portfolio.assets]
        if not descriptions:
            embeddings = np.zeros((0, 0), dtype="float32")
        else:
            embeddings = self.model.encode(
                descriptions, normalize_embeddings=True, show_progress_bar=False
            )
            embeddings = np.asarray(embeddings, dtype="float32")
        result = (tickers, embeddings)
        # Acotar el tamaño de la caché.
        if len(self._portfolio_cache) > 64:
            self._portfolio_cache.clear()
        self._portfolio_cache[sig] = result
        return result

    def compute(self, news_text: str, portfolio: Portfolio) -> dict:
        tickers, asset_embeddings = self._portfolio_embeddings(portfolio)
        if asset_embeddings.size == 0:
            return {
                "semantic_score": 0.0,
                "semantic_mean_score": 0.0,
                "best_asset": None,
                "portfolio_description": "",
            }

        news_chunk = news_text[: self._NEWS_CHAR_LIMIT]
        emb_news = self.model.encode(
            news_chunk, normalize_embeddings=True, show_progress_bar=False
        )
        emb_news = np.asarray(emb_news, dtype="float32")

        # Embeddings normalizados -> coseno = producto escalar.
        sims = asset_embeddings @ emb_news
        best_idx = int(np.argmax(sims))
        max_sim = float(sims[best_idx])
        mean_sim = float(np.mean(sims))

        return {
            # Max-pooling: relevante si lo es para ALGÚN activo.
            "semantic_score": max(max_sim, 0.0),
            "semantic_mean_score": max(mean_sim, 0.0),
            "best_asset": tickers[best_idx],
            "portfolio_description": self._asset_description(
                portfolio.assets[best_idx]
            )[:200],
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
            "semantic_mean_score": round(semantic_result.get("semantic_mean_score", 0.0), 4),
            "best_semantic_asset": semantic_result.get("best_asset"),
            "sector_match": rule_result["sector_match"],
            "country_match": rule_result["country_match"],
        }
