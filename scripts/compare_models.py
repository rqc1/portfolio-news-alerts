"""
Comparación multi-modelo: envía las mismas noticias a distintos LLMs
y compara la calidad de su análisis contextual.

Ejecutar:
  python -m scripts.compare_models

Cada noticia pasa por el pipeline NLP local UNA sola vez (preprocessing,
relevancia, clasificación de evento con NLI/FinBERT), y luego se envía
a cada modelo LLM configurado para obtener el análisis contextual.

Los resultados se guardan en scripts/model_comparison_results.json.
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from database.mongodb import MongoDB
from modules.portfolio.models import Portfolio
from modules.portfolio.service import PortfolioService
from modules.ingestion.service import IngestionService
from modules.nlp.preprocessing import NLPService
from modules.relevance.service import RelevanceService
from modules.events.classifier import EventClassificationService
from modules.impact.estimator import ImpactEstimator
from modules.llm.prompts import CONTEXTUAL_ANALYSIS_SYSTEM, CONTEXTUAL_ANALYSIS_USER
from modules.llm.analyzer import _format_portfolio, _safe_parse_json, _clamp

from openai import AsyncOpenAI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("compare_models")

# ─── Configuración de la cartera ────────────────────────────────────────
PORTFOLIO_ID = "69fc7d75f62888639d7bb02f"

# ─── Modelos a comparar ─────────────────────────────────────────────────
# Cada entrada: (nombre_display, provider, base_url, api_key, model_id)
# Se construye dinámicamente según las API keys disponibles.

_GITHUB_URL = "https://models.inference.ai.azure.com"
_OPENAI_URL = "https://api.openai.com/v1"
_HF_URL = "https://api-inference.huggingface.co/v1"
_OLLAMA_URL = "http://localhost:11434/v1"

_VALID_EVENTS = set(config.EVENT_TAXONOMY)
_VALID_DIRECTIONS = {"alcista", "bajista", "neutral"}

# Timeout por llamada a modelo (segundos)
MODEL_CALL_TIMEOUT = 45
REASONING_MODEL_TIMEOUT = 90  # modelos de razonamiento (DeepSeek-R1, Phi-4-reasoning)

OUTPUT_FILE = Path(__file__).parent / "model_comparison_results.json"


def build_model_list() -> list[dict]:
    """Construye la lista de modelos disponibles según las API keys configuradas."""
    models = []

    # --- GitHub Models (gratuito con GITHUB_TOKEN) ---
    gh_token = config.GITHUB_TOKEN
    if gh_token:
        # Modelos estándar (timeout normal)
        for model_id, display in [
            ("gpt-4o-mini", "GPT-4o-mini (GitHub)"),
            ("gpt-4o", "GPT-4o (GitHub)"),
            ("Llama-3.3-70B-Instruct", "Llama-3.3-70B (GitHub)"),
            ("DeepSeek-V3-0324", "DeepSeek-V3 (GitHub)"),
        ]:
            models.append({
                "name": display,
                "model_id": model_id,
                "base_url": _GITHUB_URL,
                "api_key": gh_token,
                "reasoning": False,
            })
        # Modelos de razonamiento (timeout extendido, strip <think> tags)
        for model_id, display in [
            ("DeepSeek-R1", "DeepSeek-R1 (GitHub)"),
        ]:
            models.append({
                "name": display,
                "model_id": model_id,
                "base_url": _GITHUB_URL,
                "api_key": gh_token,
                "reasoning": True,
            })

    # --- OpenAI directa ---
    oai_key = config.OPENAI_API_KEY
    if oai_key and oai_key != gh_token:
        for model_id, display in [
            ("gpt-4o-mini", "GPT-4o-mini (OpenAI)"),
            ("gpt-4o", "GPT-4o (OpenAI)"),
        ]:
            models.append({
                "name": display,
                "model_id": model_id,
                "base_url": _OPENAI_URL,
                "api_key": oai_key,
                "reasoning": False,
            })

    # --- HuggingFace ---
    hf_token = config.HF_TOKEN
    if hf_token:
        models.append({
            "name": "Llama-3.1-8B (HuggingFace)",
            "model_id": "meta-llama/Llama-3.1-8B-Instruct",
            "base_url": _HF_URL,
            "api_key": hf_token,
            "reasoning": False,
        })

    if not models:
        logger.error("No hay API keys configuradas. Configura GITHUB_TOKEN, OPENAI_API_KEY o HF_TOKEN en .env")

    return models


import re
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


async def call_model(
    client: AsyncOpenAI,
    model_id: str,
    system_prompt: str,
    user_prompt: str,
    is_reasoning: bool = False,
) -> Optional[dict]:
    """Llama a un modelo y parsea la respuesta JSON (con timeout)."""
    timeout = REASONING_MODEL_TIMEOUT if is_reasoning else MODEL_CALL_TIMEOUT
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.15,
                max_tokens=1200 if is_reasoning else 600,
            ),
            timeout=timeout,
        )
        raw = response.choices[0].message.content.strip()
        # Modelos de razonamiento: eliminar tags <think>...</think>
        if is_reasoning:
            raw = _THINK_RE.sub("", raw).strip()
        result = _safe_parse_json(raw)
        if result is None:
            return {"error": "JSON parse failed", "raw": raw[:300]}

        event_type = result.get("event_type", "otro")
        if event_type not in _VALID_EVENTS:
            event_type = "otro"

        direction = result.get("direction", "neutral")
        if direction not in _VALID_DIRECTIONS:
            direction = "neutral"

        return {
            "event_type": event_type,
            "direction": direction,
            "severity": round(_clamp(float(result.get("severity", 0.5))), 4),
            "confidence": round(_clamp(float(result.get("confidence", 0.5))), 4),
            "explanation": result.get("explanation", ""),
            "reasoning": result.get("reasoning", ""),
        }
    except asyncio.TimeoutError:
        return {"error": f"Timeout ({timeout}s)"}
    except Exception as e:
        return {"error": str(e)[:120]}


async def analyze_news_with_all_models(
    news_item: dict,
    nlp_result: dict,
    relevance: dict,
    event_result: dict,
    portfolio: Portfolio,
    models: list[dict],
) -> dict:
    """Envía una noticia a todos los modelos y recoge resultados."""
    title = news_item.get("title", "")
    source = news_item.get("source", "")
    cleaned_text = nlp_result["cleaned_text"]
    matched_assets = relevance["matched_assets"]
    relevance_score = relevance["relevance_score"]

    portfolio_desc = _format_portfolio(portfolio)
    assets_str = (
        ", ".join(matched_assets)
        if matched_assets
        else "Ninguno (relevancia indirecta por sector/geografía)"
    )

    user_prompt = CONTEXTUAL_ANALYSIS_USER.format(
        title=title,
        source=source,
        text=cleaned_text[:1500],
        sentiment=event_result["sentiment"].get("sentiment", "neutral"),
        sentiment_confidence=event_result["sentiment"].get("confidence", 0.5),
        portfolio_description=portfolio_desc,
        matched_assets=assets_str,
        relevance_score=relevance_score,
    )

    # Ejecutar cada modelo secuencialmente para evitar rate-limits
    model_results = {}
    for m in models:
        client = AsyncOpenAI(
            base_url=m["base_url"],
            api_key=m["api_key"],
            timeout=MODEL_CALL_TIMEOUT,
        )
        t_start = time.time()
        res = await call_model(client, m["model_id"], CONTEXTUAL_ANALYSIS_SYSTEM, user_prompt, is_reasoning=m.get("reasoning", False))
        elapsed_m = time.time() - t_start
        if res:
            res["latency_s"] = round(elapsed_m, 2)
        model_results[m["name"]] = res

    return model_results


def print_comparison_table(news_title: str, model_results: dict):
    """Imprime una tabla comparativa por consola."""
    logger.info("")
    logger.info("─" * 90)
    logger.info("  📰 %s", news_title[:85])
    logger.info("─" * 90)
    logger.info("  %-30s │ %-12s │ %-8s │ %-5s │ %-5s │ %-5s │ Error?", "MODELO", "EVENTO", "DIR", "SEV", "CONF", "LAT")
    logger.info("  %s┼%s┼%s┼%s┼%s┼%s┼%s", "─" * 30, "─" * 14, "─" * 10, "─" * 7, "─" * 7, "─" * 7, "─" * 10)
    for model_name, res in model_results.items():
        if "error" in res:
            lat = res.get("latency_s", "—")
            logger.info("  %-30s │ %-12s │ %-8s │ %-5s │ %-5s │ %-5s │ %s",
                         model_name[:30], "—", "—", "—", "—", lat, res["error"][:40])
        else:
            logger.info("  %-30s │ %-12s │ %-8s │ %.3f │ %.3f │ %4.1fs │",
                         model_name[:30],
                         res["event_type"][:12],
                         res["direction"][:8],
                         res["severity"],
                         res["confidence"],
                         res.get("latency_s", 0))


def compute_agreement(all_results: list[dict]) -> dict:
    """Calcula métricas de acuerdo inter-modelo."""
    model_names = set()
    for entry in all_results:
        model_names.update(entry["model_results"].keys())
    model_names = sorted(model_names)

    if len(model_names) < 2:
        return {"note": "Se necesitan al menos 2 modelos para calcular acuerdo"}

    total = 0
    event_agree = {m: 0 for m in model_names}
    direction_agree = {m: 0 for m in model_names}
    severity_diffs = {m: [] for m in model_names}
    confidence_diffs = {m: [] for m in model_names}

    # Acuerdo entre cada par de modelos
    pair_agreement = {}
    for i, m1 in enumerate(model_names):
        for m2 in model_names[i + 1:]:
            pair_key = f"{m1} vs {m2}"
            pair_agreement[pair_key] = {
                "event_agree": 0, "direction_agree": 0,
                "severity_mae": [], "total": 0,
            }

    for entry in all_results:
        results = entry["model_results"]
        valid_models = [m for m in model_names if m in results and "error" not in results[m]]
        if len(valid_models) < 2:
            continue

        for i, m1 in enumerate(valid_models):
            for m2 in valid_models[i + 1:]:
                pair_key = f"{m1} vs {m2}"
                if pair_key not in pair_agreement:
                    pair_key = f"{m2} vs {m1}"
                if pair_key not in pair_agreement:
                    continue
                r1, r2 = results[m1], results[m2]
                pair_agreement[pair_key]["total"] += 1
                if r1["event_type"] == r2["event_type"]:
                    pair_agreement[pair_key]["event_agree"] += 1
                if r1["direction"] == r2["direction"]:
                    pair_agreement[pair_key]["direction_agree"] += 1
                pair_agreement[pair_key]["severity_mae"].append(
                    abs(r1["severity"] - r2["severity"])
                )

    # Consolidar
    summary = {}
    for pair_key, data in pair_agreement.items():
        if data["total"] == 0:
            continue
        summary[pair_key] = {
            "n": data["total"],
            "event_agreement": round(data["event_agree"] / data["total"], 3),
            "direction_agreement": round(data["direction_agree"] / data["total"], 3),
            "severity_mae": round(sum(data["severity_mae"]) / len(data["severity_mae"]), 4)
            if data["severity_mae"] else None,
        }

    return summary


async def run_comparison():
    await MongoDB.connect()
    logger.info("═" * 90)
    logger.info("COMPARACIÓN MULTI-MODELO — %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    logger.info("═" * 90)

    # 1. Cargar cartera
    portfolio_doc = await PortfolioService.get_portfolio(PORTFOLIO_ID)
    if not portfolio_doc:
        # Intentar buscar por user_id
        cursor = MongoDB.portfolios().find({})
        portfolios = await cursor.to_list(length=10)
        if portfolios:
            portfolio_doc = portfolios[0]
            portfolio_doc["_id"] = str(portfolio_doc["_id"])
            logger.info("Usando primera cartera encontrada: %s", portfolio_doc.get("name"))
        else:
            logger.error("No se encontró ninguna cartera. Ejecuta primero setup_my_portfolio.py")
            await MongoDB.close()
            return

    pid = portfolio_doc.pop("_id", "")
    portfolio = Portfolio(**portfolio_doc)
    logger.info("Cartera: %s — %d activos: %s",
                portfolio.name, len(portfolio.assets),
                [a.ticker for a in portfolio.assets])

    # 2. Modelos disponibles
    models = build_model_list()
    logger.info("Modelos a comparar (%d):", len(models))
    for m in models:
        logger.info("  • %s [%s]", m["name"], m["model_id"])

    if not models:
        await MongoDB.close()
        return

    # 3. Cargar modelos NLP locales
    logger.info("Cargando modelos NLP locales...")
    from modules.nlp.preprocessing import _load_spacy
    from modules.events.classifier import _load_finbert, _load_nli_pipeline
    from modules.relevance.service import _load_embedding_model
    _load_spacy()
    _load_finbert()
    _load_nli_pipeline()
    _load_embedding_model()
    logger.info("Modelos NLP cargados ✓")

    # 4. Obtener noticias
    news_items = await IngestionService.get_recent_news(limit=100)
    logger.info("Noticias en BD: %d", len(news_items))

    if not news_items:
        logger.warning("No hay noticias. Ejecuta primero el pipeline de ingesta.")
        await MongoDB.close()
        return

    # 5. Pipeline NLP local + enviar a modelos
    nlp_service = NLPService()
    relevance_service = RelevanceService()
    event_service = EventClassificationService()

    all_results = []
    relevant_count = 0
    t0 = time.time()

    for i, item in enumerate(news_items, 1):
        title = item.get("title", "")
        summary = item.get("summary", "")
        content = item.get("content", "")
        if not title:
            continue

        # NLP local (una sola vez por noticia)
        nlp_result = nlp_service.process(title, summary, content)
        cleaned_text = nlp_result["cleaned_text"]
        cleaned_text_en = nlp_result.get("cleaned_text_en", cleaned_text)
        org_names = nlp_result["org_names"]

        # Relevancia
        relevance = relevance_service.compute_relevance(cleaned_text, org_names, portfolio)

        if relevance["relevance_score"] < config.ALERT_RELEVANCE_BORDERLINE:
            continue  # No relevante, skip

        # Clasificación de evento (NLI + FinBERT)
        event_result = event_service.classify(cleaned_text_en)

        # Impacto determinista (referencia)
        impact_det = ImpactEstimator.estimate(
            sentiment=event_result["sentiment"],
            event_type=event_result["event_type"],
            event_confidence=event_result["event_confidence"],
            relevance_score=relevance["relevance_score"],
            matched_assets=relevance["matched_assets"],
        )

        relevant_count += 1
        logger.info("[%d/%d] Procesando: %s (rel=%.3f, assets=%s)",
                    i, len(news_items), title[:60],
                    relevance["relevance_score"],
                    relevance["matched_assets"])

        # Enviar a TODOS los modelos en paralelo
        model_results = await analyze_news_with_all_models(
            news_item=item,
            nlp_result=nlp_result,
            relevance=relevance,
            event_result=event_result,
            portfolio=portfolio,
            models=models,
        )

        print_comparison_table(title, model_results)

        all_results.append({
            "news_id": str(item.get("_id", "")),
            "title": title,
            "source": item.get("source", ""),
            "url": item.get("url", ""),
            "relevance_score": relevance["relevance_score"],
            "matched_assets": relevance["matched_assets"],
            "nlp_sentiment": event_result["sentiment"],
            "nlp_event_type": event_result["event_type"],
            "deterministic_impact": {
                "direction": impact_det["direction"],
                "severity": impact_det["severity"],
                "severity_label": impact_det["severity_label"],
            },
            "model_results": model_results,
        })

    elapsed = time.time() - t0

    # 6. Acuerdo inter-modelo
    logger.info("")
    logger.info("═" * 90)
    logger.info("MÉTRICAS DE ACUERDO INTER-MODELO")
    logger.info("═" * 90)
    agreement = compute_agreement(all_results)
    for pair, metrics in agreement.items():
        logger.info("  %s:", pair)
        logger.info("    Noticias comparadas:    %d", metrics["n"])
        logger.info("    Acuerdo tipo evento:    %.1f%%", metrics["event_agreement"] * 100)
        logger.info("    Acuerdo dirección:      %.1f%%", metrics["direction_agreement"] * 100)
        if metrics["severity_mae"] is not None:
            logger.info("    MAE severidad:          %.4f", metrics["severity_mae"])

    # 7. Resumen por modelo
    logger.info("")
    logger.info("═" * 90)
    logger.info("RESUMEN POR MODELO")
    logger.info("═" * 90)
    model_stats = {}
    for entry in all_results:
        for model_name, res in entry["model_results"].items():
            if model_name not in model_stats:
                model_stats[model_name] = {
                    "total": 0, "errors": 0,
                    "severities": [], "confidences": [],
                    "directions": {"alcista": 0, "bajista": 0, "neutral": 0},
                    "events": {},
                }
            stats = model_stats[model_name]
            stats["total"] += 1
            if "error" in res:
                stats["errors"] += 1
            else:
                stats["severities"].append(res["severity"])
                stats["confidences"].append(res["confidence"])
                stats["directions"][res["direction"]] = stats["directions"].get(res["direction"], 0) + 1
                stats["events"][res["event_type"]] = stats["events"].get(res["event_type"], 0) + 1

    for model_name, stats in model_stats.items():
        ok = stats["total"] - stats["errors"]
        logger.info("  %s:", model_name)
        logger.info("    Analizadas: %d | Errores: %d", stats["total"], stats["errors"])
        if ok > 0:
            avg_sev = sum(stats["severities"]) / ok
            avg_conf = sum(stats["confidences"]) / ok
            logger.info("    Severidad media: %.3f | Confianza media: %.3f", avg_sev, avg_conf)
            logger.info("    Direcciones: %s", stats["directions"])
            top_events = sorted(stats["events"].items(), key=lambda x: -x[1])[:5]
            logger.info("    Top eventos: %s", dict(top_events))

    # 8. Guardar resultados
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "portfolio": portfolio.name,
        "tickers": portfolio.get_tickers(),
        "models_compared": [m["name"] for m in models],
        "total_news": len(news_items),
        "relevant_news": relevant_count,
        "elapsed_seconds": round(elapsed, 1),
        "agreement_metrics": agreement,
        "model_summaries": {
            name: {
                "total": s["total"],
                "errors": s["errors"],
                "avg_severity": round(sum(s["severities"]) / max(len(s["severities"]), 1), 4),
                "avg_confidence": round(sum(s["confidences"]) / max(len(s["confidences"]), 1), 4),
                "directions": s["directions"],
                "event_distribution": s["events"],
            }
            for name, s in model_stats.items()
        },
        "results": all_results,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)

    # Guardar también en MongoDB para acceso desde frontend/API
    comparisons_col = MongoDB.get_db()["model_comparisons"]
    await comparisons_col.insert_one(output.copy())
    logger.info("Resultados guardados en MongoDB (colección: model_comparisons)")

    # Registrar en el documento histórico de resultados experimentales
    try:
        from scripts.experiment_log import append_experiment

        lines = [
            f"**Script:** `python -m scripts.compare_models` · {len(models)} modelos × "
            f"{relevant_count} noticias relevantes (de {len(news_items)}), {elapsed:.1f} s.",
            f"**Cartera:** {portfolio.name} ({', '.join(portfolio.get_tickers())}).",
            "**Artefactos:** `scripts/model_comparison_results.json` + colección MongoDB `model_comparisons`.",
            "",
            "| Modelo | Analizadas | Errores | Sev. media | Conf. media | Direcciones (alc/baj/neu) |",
            "|---|---|---|---|---|---|",
        ]
        for name, s in model_stats.items():
            ok = max(s["total"] - s["errors"], 1)
            avg_sev = sum(s["severities"]) / ok if s["severities"] else 0
            avg_conf = sum(s["confidences"]) / ok if s["confidences"] else 0
            d = s["directions"]
            lines.append(
                f"| {name} | {s['total']} | {s['errors']} | {avg_sev:.3f} | {avg_conf:.3f} | "
                f"{d.get('alcista', 0)} / {d.get('bajista', 0)} / {d.get('neutral', 0)} |"
            )
        doc = append_experiment("Comparación multi-modelo LLM", "\n".join(lines))
        logger.info("Registrado en documento experimental: %s", doc)
    except Exception as e:
        logger.warning("No se pudo registrar en RESULTADOS_EXPERIMENTALES.md: %s", e)

    logger.info("")
    logger.info("═" * 90)
    logger.info("Comparación finalizada en %.1fs", elapsed)
    logger.info("Noticias procesadas: %d relevantes de %d totales", relevant_count, len(news_items))
    logger.info("Resultados guardados en: %s", OUTPUT_FILE)
    logger.info("═" * 90)

    await MongoDB.close()


if __name__ == "__main__":
    asyncio.run(run_comparison())
