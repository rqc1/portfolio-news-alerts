"""
Multi-provider LLM client.

Todos los proveedores usan el formato compatible con OpenAI API,
por lo que basta con cambiar base_url y api_key para alternar entre ellos.

Proveedores:
  - openai:      API de OpenAI (gpt-4o-mini, gpt-4o)
  - github:      GitHub Models — gratuito con GITHUB_TOKEN
  - huggingface: HuggingFace Inference API — tier gratuito con HF_TOKEN
  - ollama:      Modelos locales (llama3, mistral, phi3) — sin coste, sin internet
"""

import logging
from functools import lru_cache
from typing import Optional

from openai import AsyncOpenAI

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuración por proveedor
# ---------------------------------------------------------------------------
PROVIDER_CONFIGS = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "default_model": "gpt-4o-mini",
    },
    "github": {
        "base_url": "https://models.github.ai/inference",
        "api_key_env": "GITHUB_TOKEN",
        "default_model": "openai/gpt-4o-mini",
    },
    "huggingface": {
        "base_url": "https://api-inference.huggingface.co/v1",
        "api_key_env": "HF_TOKEN",
        "default_model": "meta-llama/Llama-3.1-8B-Instruct",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "api_key_env": "",
        "default_model": "llama3.1",
    },
}


class LLMClient:
    """Cliente LLM unificado. Soporta múltiples proveedores con API compatible OpenAI."""

    def __init__(self):
        self._client: Optional[AsyncOpenAI] = None
        self.provider = config.LLM_PROVIDER
        self.model = config.LLM_MODEL

    def _get_client(self) -> AsyncOpenAI:
        if self._client is not None:
            return self._client

        provider_cfg = PROVIDER_CONFIGS.get(self.provider)
        if provider_cfg is None:
            raise ValueError(f"Proveedor LLM desconocido: {self.provider}. "
                             f"Opciones: {list(PROVIDER_CONFIGS.keys())}")

        base_url = config.LLM_BASE_URL or provider_cfg["base_url"]
        api_key = config.LLM_API_KEY or self._resolve_api_key(provider_cfg)

        if not self.model:
            self.model = provider_cfg["default_model"]

        self._client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key or "not-needed",  # Ollama no requiere key
        )
        logger.info("LLM client initialized: provider=%s, model=%s, base_url=%s",
                     self.provider, self.model, base_url)
        return self._client

    @staticmethod
    def _resolve_api_key(provider_cfg: dict) -> str:
        env_var = provider_cfg.get("api_key_env", "")
        if env_var == "OPENAI_API_KEY":
            return config.OPENAI_API_KEY
        elif env_var == "GITHUB_TOKEN":
            return config.GITHUB_TOKEN
        elif env_var == "HF_TOKEN":
            return config.HF_TOKEN
        return ""

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> str:
        """Envía un chat completion y devuelve el texto de respuesta."""
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self._track_usage(response)
        return response.choices[0].message.content.strip()

    def _track_usage(self, response) -> None:
        """Registra tokens y coste estimado en las métricas Prometheus.

        Nunca debe romper la llamada principal: cualquier error se ignora.
        """
        try:
            from modules.security.metrics import record_llm

            usage = getattr(response, "usage", None)
            prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
            completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
            cost = (
                prompt_tokens / 1000.0 * config.LLM_COST_PER_1K_PROMPT
                + completion_tokens / 1000.0 * config.LLM_COST_PER_1K_COMPLETION
            )
            record_llm(
                provider=self.provider,
                model=self.model or "",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=cost,
                status="ok",
            )
        except Exception:  # noqa: BLE001
            logger.debug("No se pudieron registrar métricas LLM", exc_info=True)

    def is_available(self) -> bool:
        """Comprueba si el proveedor está configurado (tiene API key o es local)."""
        if self.provider == "ollama":
            return True
        provider_cfg = PROVIDER_CONFIGS.get(self.provider, {})
        api_key = config.LLM_API_KEY or self._resolve_api_key(provider_cfg)
        return bool(api_key)


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    """Singleton del cliente LLM."""
    return LLMClient()
