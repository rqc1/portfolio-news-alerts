"""
Módulo 1 – Modelado de cartera.

Gestiona las carteras de inversión del usuario: activos, sectores, geografías.
Normaliza tickers y proporciona el contexto necesario para calcular relevancia.
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class Asset(BaseModel):
    ticker: str = Field(..., description="Ticker normalizado (e.g. AAPL, SAN.MC)")
    name: str = Field(..., description="Nombre completo de la compañía")
    isin: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    weight: float = Field(0.0, ge=0.0, le=1.0, description="Peso en la cartera (0-1)")
    aliases: list[str] = Field(default_factory=list, description="Nombres alternativos para matching")


class Portfolio(BaseModel):
    user_id: str
    name: str = "Mi Cartera"
    assets: list[Asset] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def get_tickers(self) -> list[str]:
        return [a.ticker for a in self.assets]

    def get_sectors(self) -> set[str]:
        return {a.sector for a in self.assets if a.sector}

    def get_countries(self) -> set[str]:
        return {a.country for a in self.assets if a.country}

    def get_all_names(self) -> list[str]:
        names = []
        for a in self.assets:
            names.append(a.name.lower())
            names.append(a.ticker.lower())
            names.extend([alias.lower() for alias in a.aliases])
        return names
