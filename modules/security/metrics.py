"""
Métricas Prometheus para la capa de producción.

Expone contadores e histogramas estándar de observabilidad:

  - `http_requests_total{method,path,status}`: tráfico por endpoint y código.
  - `http_request_duration_seconds{method,path}`: latencia (histograma).
  - `llm_requests_total{provider,model,status}`: llamadas al LLM.
  - `llm_tokens_total{provider,model,type}`: tokens prompt/completion.
  - `llm_cost_usd_total{provider,model}`: coste estimado acumulado.
  - `alerts_generated_total`: alertas emitidas por el pipeline.

`render_latest()` devuelve el texto en formato de exposición Prometheus para
servirlo en `/metrics`.
"""

from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Counter,
    Histogram,
    generate_latest,
)

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total de peticiones HTTP",
    ["method", "path", "status"],
)

HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Latencia de las peticiones HTTP en segundos",
    ["method", "path"],
)

LLM_REQUESTS = Counter(
    "llm_requests_total",
    "Total de llamadas al LLM",
    ["provider", "model", "status"],
)

LLM_TOKENS = Counter(
    "llm_tokens_total",
    "Tokens consumidos por el LLM",
    ["provider", "model", "type"],  # type: prompt | completion
)

LLM_COST = Counter(
    "llm_cost_usd_total",
    "Coste estimado acumulado del LLM en USD",
    ["provider", "model"],
)

ALERTS_GENERATED = Counter(
    "alerts_generated_total",
    "Alertas generadas por el pipeline",
)


def record_http(method: str, path: str, status: int, duration: float) -> None:
    HTTP_REQUESTS.labels(method=method, path=path, status=str(status)).inc()
    HTTP_LATENCY.labels(method=method, path=path).observe(duration)


def record_llm(
    provider: str,
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cost_usd: float = 0.0,
    status: str = "ok",
) -> None:
    LLM_REQUESTS.labels(provider=provider, model=model, status=status).inc()
    if prompt_tokens:
        LLM_TOKENS.labels(provider=provider, model=model, type="prompt").inc(prompt_tokens)
    if completion_tokens:
        LLM_TOKENS.labels(provider=provider, model=model, type="completion").inc(completion_tokens)
    if cost_usd:
        LLM_COST.labels(provider=provider, model=model).inc(cost_usd)


def render_latest() -> tuple[bytes, str]:
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
