"""Tests para módulo LLM (providers, analyzer)."""

from modules.llm.providers import PROVIDER_CONFIGS, LLMClient
from modules.llm.analyzer import _safe_parse_json, _clamp, _format_portfolio
from modules.portfolio.models import Portfolio, Asset


class TestProviderConfigs:
    def test_all_providers_defined(self):
        assert "openai" in PROVIDER_CONFIGS
        assert "github" in PROVIDER_CONFIGS
        assert "huggingface" in PROVIDER_CONFIGS
        assert "ollama" in PROVIDER_CONFIGS

    def test_provider_has_required_fields(self):
        for name, cfg in PROVIDER_CONFIGS.items():
            assert "base_url" in cfg, f"{name} missing base_url"
            assert "api_key_env" in cfg, f"{name} missing api_key_env"
            assert "default_model" in cfg, f"{name} missing default_model"

    def test_ollama_no_key_required(self):
        assert PROVIDER_CONFIGS["ollama"]["api_key_env"] == ""


class TestLLMClient:
    def test_create_client(self):
        client = LLMClient()
        assert client.provider in PROVIDER_CONFIGS

    def test_is_available_without_key(self):
        client = LLMClient()
        # Without any API key configured, is_available depends on provider
        available = client.is_available()
        assert isinstance(available, bool)


class TestSafeParseJson:
    def test_valid_json(self):
        result = _safe_parse_json('{"key": "value", "num": 42}')
        assert result == {"key": "value", "num": 42}

    def test_json_with_markdown(self):
        result = _safe_parse_json('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_json_embedded_in_text(self):
        result = _safe_parse_json('Here is the result: {"key": "value"} end')
        assert result == {"key": "value"}

    def test_invalid_json(self):
        result = _safe_parse_json("this is not json at all")
        assert result is None

    def test_empty_string(self):
        result = _safe_parse_json("")
        assert result is None


class TestClamp:
    def test_within_range(self):
        assert _clamp(0.5) == 0.5

    def test_below_range(self):
        assert _clamp(-0.5) == 0.0

    def test_above_range(self):
        assert _clamp(1.5) == 1.0

    def test_custom_range(self):
        assert _clamp(5.0, lo=0.0, hi=10.0) == 5.0
        assert _clamp(-1.0, lo=0.0, hi=10.0) == 0.0
        assert _clamp(15.0, lo=0.0, hi=10.0) == 10.0


class TestFormatPortfolio:
    def test_format(self, sample_portfolio):
        result = _format_portfolio(sample_portfolio)
        assert "AAPL" in result
        assert "Apple Inc." in result
        assert "Technology" in result

    def test_format_empty(self):
        p = Portfolio(user_id="empty")
        result = _format_portfolio(p)
        assert result == "Cartera vacía"
