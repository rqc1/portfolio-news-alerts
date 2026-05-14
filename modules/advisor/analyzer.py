"""
Analizador de cartera – compara la composición actual contra el perfil ideal del inversor.

Calcula:
  - Concentración (HHI)
  - Distribución sectorial y geográfica actual vs. ideal
  - Score de diversificación
  - Score de alineación con el perfil de riesgo
  - Advertencias de riesgo
"""

import logging
from collections import Counter

from modules.advisor.models import (
    InvestorProfile,
    RiskProfile,
    InvestmentHorizon,
    InvestmentGoal,
    PortfolioAnalysis,
    AllocationSlice,
)
from modules.portfolio.models import Portfolio

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Asignaciones ideales por perfil de riesgo
# ---------------------------------------------------------------------------
# Distribución sectorial ideal (simplificada) según perfil
SECTOR_ALLOCATION_BY_PROFILE: dict[RiskProfile, dict[str, float]] = {
    RiskProfile.VERY_CONSERVATIVE: {
        "Utilities": 20, "Financial Services": 20, "Healthcare": 15,
        "Consumer Defensive": 15, "Real Estate": 10, "Industrials": 10,
        "Technology": 5, "Other": 5,
    },
    RiskProfile.CONSERVATIVE: {
        "Utilities": 15, "Financial Services": 18, "Healthcare": 15,
        "Consumer Defensive": 12, "Real Estate": 10, "Industrials": 10,
        "Technology": 12, "Other": 8,
    },
    RiskProfile.MODERATE: {
        "Technology": 20, "Healthcare": 15, "Financial Services": 15,
        "Industrials": 12, "Consumer Cyclical": 10, "Consumer Defensive": 8,
        "Energy": 8, "Real Estate": 7, "Other": 5,
    },
    RiskProfile.AGGRESSIVE: {
        "Technology": 30, "Healthcare": 15, "Consumer Cyclical": 12,
        "Financial Services": 10, "Energy": 10, "Industrials": 8,
        "Communication Services": 8, "Other": 7,
    },
    RiskProfile.VERY_AGGRESSIVE: {
        "Technology": 40, "Consumer Cyclical": 15, "Healthcare": 12,
        "Communication Services": 10, "Energy": 8, "Financial Services": 8,
        "Other": 7,
    },
}

# Distribución geográfica ideal según perfil
GEO_ALLOCATION_BY_PROFILE: dict[RiskProfile, dict[str, float]] = {
    RiskProfile.VERY_CONSERVATIVE: {
        "United States": 40, "Europe": 30, "Asia": 15, "Other": 15,
    },
    RiskProfile.CONSERVATIVE: {
        "United States": 45, "Europe": 25, "Asia": 18, "Other": 12,
    },
    RiskProfile.MODERATE: {
        "United States": 50, "Europe": 22, "Asia": 18, "Other": 10,
    },
    RiskProfile.AGGRESSIVE: {
        "United States": 50, "Europe": 18, "Asia": 20, "Emerging Markets": 7, "Other": 5,
    },
    RiskProfile.VERY_AGGRESSIVE: {
        "United States": 45, "Asia": 25, "Europe": 15, "Emerging Markets": 10, "Other": 5,
    },
}

# Número mínimo de activos recomendado por perfil
MIN_ASSETS_BY_PROFILE: dict[RiskProfile, int] = {
    RiskProfile.VERY_CONSERVATIVE: 10,
    RiskProfile.CONSERVATIVE: 8,
    RiskProfile.MODERATE: 6,
    RiskProfile.AGGRESSIVE: 5,
    RiskProfile.VERY_AGGRESSIVE: 4,
}


def _normalize_sector(sector: str | None) -> str:
    """Normaliza nombres de sector a la taxonomía estándar."""
    if not sector:
        return "Other"
    sector = sector.strip()
    # Mapeo de variantes comunes
    mapping = {
        "technology": "Technology",
        "tech": "Technology",
        "information technology": "Technology",
        "healthcare": "Healthcare",
        "health care": "Healthcare",
        "financial services": "Financial Services",
        "financials": "Financial Services",
        "consumer cyclical": "Consumer Cyclical",
        "consumer discretionary": "Consumer Cyclical",
        "consumer defensive": "Consumer Defensive",
        "consumer staples": "Consumer Defensive",
        "energy": "Energy",
        "industrials": "Industrials",
        "real estate": "Real Estate",
        "utilities": "Utilities",
        "communication services": "Communication Services",
        "basic materials": "Basic Materials",
        "materials": "Basic Materials",
    }
    return mapping.get(sector.lower(), sector)


def _normalize_country(country: str | None) -> str:
    """Agrupa países en regiones."""
    if not country:
        return "Other"
    country_lower = country.lower().strip()

    us_variants = {"united states", "usa", "us", "united states of america"}
    if country_lower in us_variants:
        return "United States"

    europe = {"spain", "germany", "france", "united kingdom", "uk", "italy",
              "netherlands", "switzerland", "sweden", "ireland", "belgium",
              "portugal", "austria", "norway", "denmark", "finland"}
    if country_lower in europe:
        return "Europe"

    asia_developed = {"japan", "south korea", "singapore", "hong kong", "taiwan"}
    if country_lower in asia_developed:
        return "Asia"

    emerging = {"china", "india", "brazil", "mexico", "indonesia", "thailand",
                "south africa", "turkey", "russia", "argentina", "chile", "colombia"}
    if country_lower in emerging:
        return "Emerging Markets"

    return "Other"


def analyze_portfolio(portfolio: Portfolio, profile: InvestorProfile) -> PortfolioAnalysis:
    """Analiza la cartera actual contra el perfil ideal del inversor."""
    assets = portfolio.assets
    n_assets = len(assets)
    warnings: list[str] = []

    if n_assets == 0:
        return PortfolioAnalysis(
            concentration_risk=1.0,
            sector_allocation=[],
            geography_allocation=[],
            diversification_score=0,
            risk_alignment_score=0,
            warnings=["La cartera está vacía. No se puede analizar."],
        )

    # --- Normalizar pesos (si no suman 1, repartir equitativamente) ---
    total_weight = sum(a.weight for a in assets)
    if total_weight < 0.01:
        weights = {a.ticker: 1.0 / n_assets for a in assets}
    else:
        weights = {a.ticker: a.weight / total_weight for a in assets}

    # --- Concentración (HHI – Herfindahl-Hirschman Index) ---
    hhi = sum(w ** 2 for w in weights.values())

    # --- Distribución sectorial ---
    sector_weights: Counter[str] = Counter()
    for a in assets:
        sec = _normalize_sector(a.sector)
        sector_weights[sec] += weights[a.ticker] * 100

    ideal_sectors = SECTOR_ALLOCATION_BY_PROFILE.get(
        profile.risk_profile, SECTOR_ALLOCATION_BY_PROFILE[RiskProfile.MODERATE]
    )
    all_sectors = set(sector_weights.keys()) | set(ideal_sectors.keys())
    sector_allocation = []
    for sec in sorted(all_sectors):
        current = round(sector_weights.get(sec, 0.0), 1)
        ideal = round(ideal_sectors.get(sec, 0.0), 1)
        diff = round(current - ideal, 1)
        if abs(diff) <= 5:
            status = "equilibrado"
        elif diff > 0:
            status = "sobreexpuesto"
        else:
            status = "infraexpuesto"
        sector_allocation.append(AllocationSlice(
            category=sec, current_pct=current, ideal_pct=ideal,
            diff_pct=diff, status=status,
        ))

    # --- Distribución geográfica ---
    geo_weights: Counter[str] = Counter()
    for a in assets:
        geo = _normalize_country(a.country)
        geo_weights[geo] += weights[a.ticker] * 100

    ideal_geo = GEO_ALLOCATION_BY_PROFILE.get(
        profile.risk_profile, GEO_ALLOCATION_BY_PROFILE[RiskProfile.MODERATE]
    )
    all_geos = set(geo_weights.keys()) | set(ideal_geo.keys())
    geo_allocation = []
    for geo in sorted(all_geos):
        current = round(geo_weights.get(geo, 0.0), 1)
        ideal = round(ideal_geo.get(geo, 0.0), 1)
        diff = round(current - ideal, 1)
        if abs(diff) <= 5:
            status = "equilibrado"
        elif diff > 0:
            status = "sobreexpuesto"
        else:
            status = "infraexpuesto"
        geo_allocation.append(AllocationSlice(
            category=geo, current_pct=current, ideal_pct=ideal,
            diff_pct=diff, status=status,
        ))

    # --- Score de diversificación (0-100) ---
    # Basado en: número de activos, HHI, número de sectores, número de regiones
    n_sectors = len([s for s in sector_weights if sector_weights[s] > 0])
    n_regions = len([g for g in geo_weights if geo_weights[g] > 0])

    div_asset_score = min(n_assets / 15, 1.0) * 30         # max 30 pts por nº activos
    div_hhi_score = (1 - hhi) * 30                          # max 30 pts por baja concentración
    div_sector_score = min(n_sectors / 6, 1.0) * 20         # max 20 pts por sectores
    div_geo_score = min(n_regions / 4, 1.0) * 20            # max 20 pts por regiones
    diversification_score = round(div_asset_score + div_hhi_score + div_sector_score + div_geo_score)

    # --- Score de alineación con perfil (0-100) ---
    # Mide qué tan cerca está la distribución actual de la ideal
    sector_deviation = sum(
        abs(s.diff_pct) for s in sector_allocation
    ) / max(len(sector_allocation), 1)
    geo_deviation = sum(
        abs(g.diff_pct) for g in geo_allocation
    ) / max(len(geo_allocation), 1)

    alignment = 100 - (sector_deviation * 1.5 + geo_deviation * 1.5)
    risk_alignment_score = round(max(0, min(100, alignment)))

    # --- Advertencias ---
    min_assets = MIN_ASSETS_BY_PROFILE.get(profile.risk_profile, 6)
    if n_assets < min_assets:
        warnings.append(
            f"Tu cartera tiene {n_assets} activos. Para tu perfil ({profile.risk_profile.value}) "
            f"se recomiendan al menos {min_assets}."
        )

    if hhi > 0.25:
        top_asset = max(weights, key=weights.get)
        warnings.append(
            f"Alta concentración: {top_asset} representa el {weights[top_asset]*100:.0f}% de la cartera. "
            f"Considera diversificar."
        )

    over_sectors = [s.category for s in sector_allocation if s.diff_pct > 15]
    if over_sectors:
        warnings.append(
            f"Sobreexposición significativa en: {', '.join(over_sectors)}. "
            f"Esto aumenta el riesgo sectorial."
        )

    under_sectors = [s.category for s in sector_allocation if s.diff_pct < -15]
    if under_sectors:
        warnings.append(
            f"Infrarrepresentación significativa en: {', '.join(under_sectors)}. "
            f"Podrías estar perdiéndote oportunidades de diversificación."
        )

    if n_regions <= 1:
        warnings.append(
            "Toda tu cartera está concentrada en una sola región geográfica. "
            "La diversificación geográfica reduce el riesgo país."
        )

    return PortfolioAnalysis(
        concentration_risk=round(hhi, 4),
        sector_allocation=sector_allocation,
        geography_allocation=geo_allocation,
        diversification_score=diversification_score,
        risk_alignment_score=risk_alignment_score,
        warnings=warnings,
    )
