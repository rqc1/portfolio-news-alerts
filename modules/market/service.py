"""
Servicio de datos de mercado – yfinance.

Proporciona:
  - Lookup de activos por ticker (auto-fill)
  - Precios actuales y variación diaria
  - Histórico de precios para analytics
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import yfinance as yf
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Modelos de respuesta
# ---------------------------------------------------------------------------
class AssetLookup(BaseModel):
    """Datos devueltos al buscar un ticker."""
    ticker: str
    name: str = ""
    sector: str = ""
    industry: str = ""
    country: str = ""
    currency: str = ""
    market_cap: Optional[float] = None
    isin: Optional[str] = None
    exchange: str = ""
    description: str = ""
    aliases: list[str] = Field(default_factory=list)


class PriceSnapshot(BaseModel):
    """Precio actual y variación de un activo."""
    ticker: str
    price: float
    currency: str = "USD"
    change_pct: float = 0.0
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    volume: Optional[int] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Servicio
# ---------------------------------------------------------------------------
class MarketService:
    """Wrapper estático sobre yfinance."""

    @staticmethod
    def lookup_ticker(symbol: str) -> Optional[AssetLookup]:
        """Busca información completa de un ticker.

        Retorna None si el ticker no existe o no se pueden obtener datos.
        """
        try:
            t = yf.Ticker(symbol.strip().upper())
            info = t.info or {}

            # yfinance devuelve un dict vacío o con "trailingPegRatio" si el
            # ticker no existe; comprobamos que haya nombre.
            name = info.get("longName") or info.get("shortName", "")
            if not name:
                logger.warning("Ticker %s no encontrado en Yahoo Finance", symbol)
                return None

            # Construir aliases útiles
            aliases: list[str] = []
            short = info.get("shortName", "")
            if short and short != name:
                aliases.append(short)

            # Intentar obtener ISIN (puede fallar en algunos mercados)
            isin = None
            try:
                isin = t.isin if t.isin and t.isin != "-" else None
            except Exception:
                pass

            return AssetLookup(
                ticker=symbol.strip().upper(),
                name=name,
                sector=info.get("sector", ""),
                industry=info.get("industry", ""),
                country=info.get("country", ""),
                currency=info.get("currency", ""),
                market_cap=info.get("marketCap"),
                isin=isin,
                exchange=info.get("exchange", ""),
                description=(info.get("longBusinessSummary") or "")[:500],
                aliases=aliases,
            )
        except Exception as exc:
            logger.error("Error al consultar ticker %s: %s", symbol, exc)
            return None

    @staticmethod
    def get_price(symbol: str) -> Optional[PriceSnapshot]:
        """Obtiene el precio actual y la variación diaria de un ticker."""
        try:
            t = yf.Ticker(symbol.strip().upper())
            info = t.info or {}

            price = info.get("currentPrice") or info.get("regularMarketPrice")
            prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")

            if price is None:
                return None

            change_pct = 0.0
            if prev_close and prev_close > 0:
                change_pct = round(((price - prev_close) / prev_close) * 100, 2)

            return PriceSnapshot(
                ticker=symbol.strip().upper(),
                price=round(price, 2),
                currency=info.get("currency", "USD"),
                change_pct=change_pct,
                day_high=info.get("dayHigh"),
                day_low=info.get("dayLow"),
                volume=info.get("volume"),
            )
        except Exception as exc:
            logger.error("Error al obtener precio de %s: %s", symbol, exc)
            return None

    @staticmethod
    def get_prices_batch(symbols: list[str]) -> dict[str, PriceSnapshot]:
        """Obtiene precios para múltiples tickers de forma eficiente."""
        results: dict[str, PriceSnapshot] = {}
        for sym in symbols:
            snap = MarketService.get_price(sym)
            if snap:
                results[sym.upper()] = snap
        return results

    @staticmethod
    def get_history(symbol: str, period: str = "1y") -> list[dict]:
        """Devuelve histórico de precios OHLCV.

        period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        """
        try:
            t = yf.Ticker(symbol.strip().upper())
            df = t.history(period=period)
            if df.empty:
                return []
            df.index = df.index.tz_localize(None) if df.index.tz is None else df.index.tz_convert("UTC").tz_localize(None)
            records = []
            for date, row in df.iterrows():
                records.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "open": round(row["Open"], 2),
                    "high": round(row["High"], 2),
                    "low": round(row["Low"], 2),
                    "close": round(row["Close"], 2),
                    "volume": int(row["Volume"]),
                })
            return records
        except Exception as exc:
            logger.error("Error al obtener histórico de %s: %s", symbol, exc)
            return []

    @staticmethod
    def get_fundamentals(symbol: str) -> Optional[dict]:
        """Obtiene métricas fundamentales clave de un ticker."""
        try:
            t = yf.Ticker(symbol.strip().upper())
            info = t.info or {}

            price = info.get("currentPrice") or info.get("regularMarketPrice")
            if price is None:
                return None

            prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
            change_pct = 0.0
            if prev_close and prev_close > 0:
                change_pct = round(((price - prev_close) / prev_close) * 100, 2)

            return {
                "ticker": symbol.strip().upper(),
                "price": round(price, 2),
                "change_pct": change_pct,
                "currency": info.get("currency", "USD"),
                "market_cap": info.get("marketCap"),
                "pe_trailing": info.get("trailingPE"),
                "pe_forward": info.get("forwardPE"),
                "eps_trailing": info.get("trailingEps"),
                "eps_forward": info.get("forwardEps"),
                "revenue": info.get("totalRevenue"),
                "profit_margin": info.get("profitMargins"),
                "dividend_yield": info.get("dividendYield"),
                "beta": info.get("beta"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
                "avg_volume": info.get("averageVolume"),
                "target_price": info.get("targetMeanPrice"),
                "recommendation": info.get("recommendationKey"),
            }
        except Exception as exc:
            logger.error("Error al obtener fundamentales de %s: %s", symbol, exc)
            return None
