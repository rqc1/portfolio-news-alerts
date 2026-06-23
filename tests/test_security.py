"""
Tests de la capa de seguridad/producción (weakness g).

Cubren:
  - Hash/verificación de contraseñas (bcrypt).
  - Emisión y verificación de JWT (roundtrip, token inválido, expiración).
  - `get_current_user`: anónimo cuando AUTH_ENABLED=false, 401 cuando está
    activado sin token, identidad válida con token correcto.
  - Métricas Prometheus (registro de HTTP/LLM y render).

No dependen de MongoDB: AuthService.register/authenticate se prueban por
separado solo si hay base de datos (se omiten en su ausencia).
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

import config
from modules.security import auth
from modules.security import metrics as obs_metrics


# ---------------------------------------------------------------------------
# Contraseñas
# ---------------------------------------------------------------------------
class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = auth.hash_password("supersecret123")
        assert hashed != "supersecret123"
        assert hashed.startswith("$2")  # prefijo bcrypt

    def test_verify_correct(self):
        hashed = auth.hash_password("supersecret123")
        assert auth.verify_password("supersecret123", hashed) is True

    def test_verify_wrong(self):
        hashed = auth.hash_password("supersecret123")
        assert auth.verify_password("wrong", hashed) is False

    def test_verify_invalid_hash_returns_false(self):
        assert auth.verify_password("x", "not-a-hash") is False

    def test_salts_differ(self):
        h1 = auth.hash_password("same-password")
        h2 = auth.hash_password("same-password")
        assert h1 != h2  # sal distinta por usuario


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
class TestTokens:
    def test_roundtrip(self):
        token, expires_in = auth.create_access_token("user-123", "a@b.com")
        assert isinstance(token, str) and token
        assert expires_in == config.JWT_EXPIRE_MINUTES * 60
        payload = auth.decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["email"] == "a@b.com"

    def test_invalid_token(self):
        assert auth.decode_token("garbage.token.value") is None

    def test_expired_token(self):
        from jose import jwt
        expired = datetime.now(timezone.utc) - timedelta(minutes=5)
        token = jwt.encode(
            {"sub": "u", "exp": expired},
            config.JWT_SECRET,
            algorithm=config.JWT_ALGORITHM,
        )
        assert auth.decode_token(token) is None


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------
class TestCurrentUser:
    def test_anonymous_when_auth_disabled(self, monkeypatch):
        monkeypatch.setattr(config, "AUTH_ENABLED", False)
        user = asyncio.run(auth.get_current_user(token=None))
        assert user.is_anonymous is True
        assert user.id == "anonymous"

    def test_401_when_enabled_no_token(self, monkeypatch):
        monkeypatch.setattr(config, "AUTH_ENABLED", True)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(auth.get_current_user(token=None))
        assert exc.value.status_code == 401

    def test_401_when_enabled_bad_token(self, monkeypatch):
        monkeypatch.setattr(config, "AUTH_ENABLED", True)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(auth.get_current_user(token="bad.token"))
        assert exc.value.status_code == 401

    def test_valid_token_when_enabled(self, monkeypatch):
        monkeypatch.setattr(config, "AUTH_ENABLED", True)
        token, _ = auth.create_access_token("user-9", "x@y.com")
        user = asyncio.run(auth.get_current_user(token=token))
        assert user.is_anonymous is False
        assert user.id == "user-9"
        assert user.email == "x@y.com"


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------
class TestMetrics:
    def test_record_http_and_render(self):
        obs_metrics.record_http("GET", "/test", 200, 0.012)
        payload, content_type = obs_metrics.render_latest()
        text = payload.decode()
        assert "http_requests_total" in text
        assert "text/plain" in content_type

    def test_record_llm(self):
        obs_metrics.record_llm(
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            cost_usd=0.001,
        )
        payload, _ = obs_metrics.render_latest()
        text = payload.decode()
        assert "llm_tokens_total" in text
        assert "llm_requests_total" in text
