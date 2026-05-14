"""Fixtures compartidos para todos los tests."""

import sys
from pathlib import Path

import pytest

# Asegurar que el directorio raíz está en el path para imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.portfolio.models import Portfolio, Asset


@pytest.fixture
def sample_portfolio() -> Portfolio:
    """Cartera de ejemplo con 3 activos diversificados."""
    return Portfolio(
        user_id="test_user",
        name="Test Portfolio",
        assets=[
            Asset(
                ticker="AAPL",
                name="Apple Inc.",
                sector="Technology",
                industry="Consumer Electronics",
                country="US",
                weight=0.4,
                aliases=["Apple"],
            ),
            Asset(
                ticker="SAN.MC",
                name="Banco Santander",
                sector="Financials",
                industry="Banking",
                country="Spain",
                weight=0.3,
                aliases=["Santander"],
            ),
            Asset(
                ticker="TSLA",
                name="Tesla Inc.",
                sector="Consumer Discretionary",
                industry="Electric Vehicles",
                country="US",
                weight=0.3,
                aliases=["Tesla"],
            ),
        ],
    )


@pytest.fixture
def sample_news_apple() -> dict:
    """Noticia de ejemplo sobre Apple (match directo)."""
    return {
        "title": "Apple reports record quarterly revenue of $124 billion",
        "summary": "Apple Inc. posted record quarterly results driven by strong iPhone sales and services growth.",
        "content": "Apple Inc. reported fiscal first-quarter revenue of $124 billion, surpassing analyst expectations. iPhone revenue grew 6% year-over-year.",
        "url": "https://example.com/apple-earnings",
        "source": "reuters_business",
    }


@pytest.fixture
def sample_news_irrelevant() -> dict:
    """Noticia sin relación con la cartera."""
    return {
        "title": "New species of deep-sea fish discovered in Pacific Ocean",
        "summary": "Marine biologists have identified a new species of bioluminescent fish at depths of 4000 meters.",
        "content": "The discovery was made during a research expedition near the Mariana Trench.",
        "url": "https://example.com/fish-discovery",
        "source": "generic_news",
    }


@pytest.fixture
def sample_news_cyber() -> dict:
    """Noticia sobre ciberataque (match por sector tech)."""
    return {
        "title": "Major ransomware attack hits technology companies worldwide",
        "summary": "A sophisticated ransomware campaign has disrupted operations at several major tech firms including data breaches at cloud providers.",
        "content": "Security researchers report that the attack exploits a zero-day vulnerability in enterprise software.",
        "url": "https://example.com/ransomware-attack",
        "source": "the_hacker_news",
    }
