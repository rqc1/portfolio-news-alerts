"""
Resolución canónica de entidades.

Problema: el matching directo noticia ↔ cartera fallaba por variantes
superficiales del nombre de una empresa («Apple Inc.», «Apple Inc», «Apple»,
«AAPL», «Apple Computer») y producía falsos positivos con tickers cortos que
coinciden con palabras comunes.

Este módulo normaliza nombres de empresa a una forma canónica y construye, a
partir de la cartera, un índice de búsqueda robusto que:

  - Elimina sufijos societarios (Inc., Corp., S.A., plc, AG, N.V., Ltd, …).
  - Normaliza puntuación, acentos y espacios.
  - Expande alias declarados y deriva la «raíz» del nombre (primer token
    significativo) para captar menciones abreviadas.
  - Aplica guardas de ambigüedad: las claves cortas o que son palabras
    comunes solo casan con límites de palabra; las raíces ambiguas
    (compartidas por varios activos) no se usan como clave de desambiguación.

El resolver es determinista, sin dependencias de red ni de modelos.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

# Sufijos societarios habituales (multi-idioma). Orden: se eliminan todos.
_CORPORATE_SUFFIXES = {
    "inc", "incorporated", "corp", "corporation", "co", "company",
    "ltd", "limited", "llc", "lp", "llp", "plc", "ag", "nv", "sa",
    "sas", "spa", "srl", "gmbh", "kg", "ab", "oyj", "asa", "as",
    "bv", "se", "pte", "pty", "holdings", "holding", "group", "grp",
    "se", "the", "class",
}

# Palabras comunes que, usadas como clave corta, generan falsos positivos.
_COMMON_WORDS = {
    "a", "an", "it", "ai", "us", "or", "all", "on", "at", "am", "be",
    "do", "go", "no", "so", "is", "by", "to", "of", "in", "as", "we",
}

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_MULTISPACE = re.compile(r"\s+")


def strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_company_name(name: str) -> str:
    """Forma canónica: minúsculas, sin acentos, sin puntuación ni sufijos."""
    if not name:
        return ""
    text = strip_accents(name.lower())
    # Eliminar puntos primero para colapsar abreviaturas tipo «S.A.» → «sa»
    # antes de tokenizar (si no, se partiría en «s a»).
    text = text.replace(".", "")
    text = _PUNCT.sub(" ", text)
    text = _MULTISPACE.sub(" ", text).strip()
    tokens = [t for t in text.split(" ") if t and t not in _CORPORATE_SUFFIXES]
    return " ".join(tokens)


def company_root(name: str) -> str:
    """Primer token significativo del nombre normalizado (p.ej. 'apple')."""
    norm = normalize_company_name(name)
    return norm.split(" ")[0] if norm else ""


@dataclass
class _Key:
    """Clave de búsqueda con metadatos para aplicar guardas."""

    text: str            # texto normalizado de la clave
    ticker: str          # activo al que resuelve
    requires_boundary: bool  # exigir límite de palabra (claves cortas/ambiguas)
    weight: float        # confianza de la resolución (0–1)


@dataclass
class EntityResolver:
    """Resuelve menciones de texto a tickers de una cartera."""

    keys: list[_Key] = field(default_factory=list)
    _root_counts: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_portfolio(cls, portfolio) -> "EntityResolver":
        resolver = cls()
        # Primero contar raíces para detectar ambigüedad entre activos.
        roots: dict[str, set[str]] = {}
        for asset in portfolio.assets:
            candidates = [asset.name, *asset.aliases]
            for cand in candidates:
                root = company_root(cand)
                if root:
                    roots.setdefault(root, set()).add(asset.ticker)
        resolver._root_counts = {r: len(t) for r, t in roots.items()}

        for asset in portfolio.assets:
            resolver._add_asset_keys(asset)
        return resolver

    def _add_key(self, text: str, ticker: str, weight: float) -> None:
        norm = normalize_company_name(text) if " " in text or len(text) > 5 else \
            strip_accents(text.lower()).strip()
        if not norm:
            return
        requires_boundary = (
            len(norm) <= 3
            or norm in _COMMON_WORDS
            or self._root_counts.get(norm, 0) > 1
        )
        # Evitar duplicados exactos.
        for k in self.keys:
            if k.text == norm and k.ticker == ticker:
                if weight > k.weight:
                    k.weight = weight
                return
        self.keys.append(_Key(norm, ticker, requires_boundary, weight))

    def _add_asset_keys(self, asset) -> None:
        ticker = asset.ticker
        # Ticker exacto: clave fuerte pero con límite de palabra (suelen ser cortos).
        self._add_key(ticker, ticker, weight=0.95)
        # Nombre completo canónico.
        self._add_key(asset.name, ticker, weight=0.95)
        # Raíz del nombre, solo si no es ambigua entre activos.
        root = company_root(asset.name)
        if root and self._root_counts.get(root, 0) == 1 and root != normalize_company_name(asset.name):
            self._add_key(root, ticker, weight=0.85)
        # Alias declarados.
        for alias in asset.aliases:
            self._add_key(alias, ticker, weight=0.9)

    def resolve(self, text: str) -> list[dict]:
        """Devuelve activos detectados en el texto con su confianza.

        Resultado: lista de {ticker, score, matched_key} ordenada por score.
        """
        norm_text = " " + _MULTISPACE.sub(
            " ", _PUNCT.sub(" ", strip_accents(text.lower()))
        ).strip() + " "

        best: dict[str, dict] = {}
        for key in self.keys:
            # Siempre se exige límite de palabra: evita falsos positivos por
            # substring (p.ej. «apple» dentro de «pineapple»). Las claves
            # multi-palabra también casan correctamente con esta estrategia.
            pattern = r"(?<![\w])" + re.escape(key.text) + r"(?![\w])"
            found = re.search(pattern, norm_text) is not None
            if not found:
                continue
            prev = best.get(key.ticker)
            if prev is None or key.weight > prev["score"]:
                best[key.ticker] = {
                    "ticker": key.ticker,
                    "score": key.weight,
                    "matched_key": key.text,
                }

        return sorted(best.values(), key=lambda d: d["score"], reverse=True)

    def resolve_tickers(self, text: str) -> list[str]:
        return [r["ticker"] for r in self.resolve(text)]
