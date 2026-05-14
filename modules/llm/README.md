# Módulo Transversal — LLM (Multi-proveedor)

## Propósito

Proporciona una **capa de abstracción sobre múltiples proveedores de LLM** usando
la API compatible con OpenAI como interfaz común. Se usa en dos puntos del pipeline:

1. **Análisis contextual de impacto** — Una única llamada LLM que produce tipo de evento,
   dirección, severidad, confianza y explicación, todo contextualizado a la cartera
   del usuario. Reemplaza los análisis deterministas cuando el LLM está disponible.

2. **Filtro de relevancia de segundo nivel** — Para noticias en la zona borderline
   (score entre 0.3 y 0.5), el LLM evalúa si existe relevancia indirecta que los
   filtros automáticos no captan (competidores, proveedores, regulación sectorial).

> **Diseño clave:** El LLM es un **enhancement layer** opcional. Sin él, el sistema
> funciona al 100% con modelos locales (FinBERT, NLI, embeddings) y fallbacks
> deterministas.

## Archivos

| Archivo | Qué contiene |
|---------|-------------|
| `providers.py` | `LLMClient` — cliente unificado multi-proveedor |
| `prompts.py` | Templates de prompts para análisis contextual y relevancia |
| `analyzer.py` | `ContextualAnalyzer` + `RelevanceChecker` |

## Proveedores Soportados

Todos usan la librería `openai` de Python (`AsyncOpenAI`), cambiando `base_url` y `api_key`.
El método `chat()` es `async def` y usa `await client.chat.completions.create()`:

| Proveedor | Variable de entorno | Coste | Modelos default | Ideal para |
|-----------|--------------------:|:-----:|-----------------|------------|
| **GitHub Models** | `GITHUB_TOKEN` | Gratuito | `meta-llama-3.1-8b-instruct` | Desarrollo, prototipado |
| **HuggingFace** | `HF_TOKEN` | Tier gratuito | `meta-llama/Llama-3.1-8B-Instruct` | Alternativa gratuita |
| **OpenAI** | `OPENAI_API_KEY` | ~$0.15/1M tok | `gpt-4o-mini` | Producción, máxima calidad |
| **Ollama** | (ninguna) | Gratuito | `llama3.1` | Offline, privacidad |

### Configuración

En `.env`:

```bash
# GitHub Models (recomendado para empezar — gratuito)
LLM_PROVIDER=github
GITHUB_TOKEN=ghp_tu_token_aqui

# HuggingFace (alternativa gratuita)
# LLM_PROVIDER=huggingface
# HF_TOKEN=hf_tu_token_aqui

# Ollama (local, sin internet)
# LLM_PROVIDER=ollama
# LLM_MODEL=llama3.1

# OpenAI (de pago)
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...
```

## Componentes

### `LLMClient` (`providers.py`)

Singleton que expone un método `chat(system_prompt, user_prompt)` compatible
con cualquier proveedor:

```python
client = get_llm_client()

if client.is_available():
    response = client.chat(
        system_prompt="Eres un analista financiero...",
        user_prompt="Analiza esta noticia: ...",
        temperature=0.15,
        max_tokens=600,
    )
```

- `is_available()` → `True` si el proveedor tiene API key (o es Ollama).
- Lazy loading: el cliente se crea al primer uso.
- Singleton: una sola instancia reutilizada.

### `ContextualAnalyzer` (`analyzer.py`)

Análisis unificado impacto + explicación en una sola llamada:

**Input:**
- Título y texto de la noticia
- Sentimiento de FinBERT
- Assets matcheados y score de relevancia
- Cartera completa del usuario

**Output:**
```python
{
    "event_type": "litigio",
    "direction": "bajista",
    "severity": 0.75,
    "confidence": 0.82,
    "explanation": "Apple enfrenta una demanda colectiva que podría...",
    "reasoning": "Lawsuit against major holding, direct exposure...",
    "source": "llm",
}
```

**Fallback:** Si `is_available() == False` o la llamada falla → devuelve `None`.
El motor de alertas (engine.py) usa entonces la estimación determinista.

### `RelevanceChecker` (`analyzer.py`)

Filtro de segundo nivel para noticias borderline (relevance_score ∈ [0.3, 0.5)):

**Input:**
- Título y resumen de la noticia
- Cartera del usuario

**Output:**
```python
{
    "is_relevant": True,
    "relevance_score": 0.7,
    "reason": "La noticia afecta a TSMC, proveedor principal de chips para Apple",
    "affected_assets": ["AAPL"],
}
```

### Prompt Templates (`prompts.py`)

Dos templates principales:

| Template | Propósito | Tokens estimados |
|----------|-----------|:----------------:|
| `CONTEXTUAL_ANALYSIS_*` | Impacto + explicación contextualizada | ~400-600 input + ~300 output |
| `RELEVANCE_CHECK_*` | Filtro de relevancia indirecta | ~200 input + ~100 output |

Los prompts están diseñados para:
- Pedir respuesta en **JSON estricto** (parseable sin ambigüedad).
- Evaluar desde la **perspectiva del inversor** (no del mercado general).
- Considerar **efectos indirectos** (competidores, proveedores, cadena de valor).
- Generar explicaciones **en español** y personalizadas.

## Relación con otros módulos

```
                                  ┌─── RelevanceChecker
                                  │    (noticias borderline)
                                  │
Relevance ──▸ ¿borderline? ──────┤
                                  │
Events + Impact (determinista) ───┼──▸ ContextualAnalyzer
                                  │    (impacto + explicación)
Portfolio ────────────────────────┘
```

## Dependencias

- `openai` — librería cliente async (`AsyncOpenAI`, usada para TODOS los proveedores)
- `config.py` — `LLM_PROVIDER`, `LLM_MODEL`, tokens
- `modules.portfolio.models.Portfolio` — contexto de la cartera
