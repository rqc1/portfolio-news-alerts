"""
Script para crear la cartera de validación en MongoDB Atlas.
Ejecutar una vez: python -m scripts.setup_portfolio
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.mongodb import MongoDB
from modules.portfolio.models import Portfolio, Asset
from modules.portfolio.service import PortfolioService


ASSETS = [
    Asset(
        ticker="V",
        name="Visa Inc.",
        sector="Financial Services",
        industry="Credit Services",
        country="US",
        weight=0.34,
        aliases=["visa", "visa inc", "visa international"],
    ),
    Asset(
        ticker="NVDA",
        name="NVIDIA Corporation",
        sector="Technology",
        industry="Semiconductors",
        country="US",
        weight=0.33,
        aliases=["nvidia", "nvidia corp", "nvda", "geforce", "jensen huang"],
    ),
    Asset(
        ticker="GLD",
        name="SPDR Gold Shares",
        sector="Commodities",
        industry="Gold",
        country="US",
        weight=0.33,
        aliases=["gold", "oro", "spdr gold", "gold etf", "precio del oro"],
    ),
]


async def main():
    await MongoDB.connect()

    # Verificar si ya existe una cartera para este user
    existing = await PortfolioService.get_portfolios_by_user("rquerol")
    if existing:
        print(f"Ya existe(n) {len(existing)} cartera(s) para 'rquerol':")
        for p in existing:
            tickers = [a["ticker"] for a in p.get("assets", [])]
            print(f"  - {p['_id']}: {p['name']} → {tickers}")
        print("\nSi quieres recrearla, borra la existente primero.")
        await MongoDB.close()
        return

    portfolio = Portfolio(
        user_id="rquerol",
        name="Cartera Validación TFM",
        assets=ASSETS,
    )

    portfolio_id = await PortfolioService.create_portfolio(portfolio)
    print(f"Cartera creada con ID: {portfolio_id}")
    print(f"  Activos: {[a.ticker for a in ASSETS]}")
    print(f"  Sectores: {portfolio.get_sectors()}")

    await MongoDB.close()


if __name__ == "__main__":
    asyncio.run(main())
