# Módulo 3 — NLP (Preprocesado de Texto)

## Propósito

Normaliza y enriquece el texto de las noticias antes de que entre en las fases de
scoring (relevancia, clasificación, impacto). Realiza tres tareas:

1. **Limpieza de texto** — elimina HTML, URLs, saltos múltiples, caracteres de control.
2. **Extracción de entidades nombradas (NER)** — identifica organizaciones, personas, países, cantidades monetarias, etc.
3. **Detección de idioma** — clasifica si es `en`, `es` u otro.
4. **Traducción ES→EN** — traduce automáticamente noticias en español (ej. CNMV) para compatibilidad con FinBERT y BART-MNLI.

## Archivos

| Archivo | Qué contiene |
|---------|-------------|
| `preprocessing.py` | `TextPreprocessor`, `EntityExtractor`, `NLPService` |

## Componentes

### `TextPreprocessor`

Transforma texto crudo en texto limpio:

| Paso | Operación | Ejemplo |
|------|-----------|---------|
| 1 | Strip HTML tags | `<b>Apple</b> reports` → `Apple reports` |
| 2 | Remove URLs | `See https://... for details` → `See for details` |
| 3 | Normalize whitespace | `Apple    reports` → `Apple reports` |
| 4 | Strip leading/trailing spaces | — |

### `EntityExtractor`

Usa **spaCy** (`en_core_web_sm`) para extraer entidades relevantes:

| Label spaCy | Qué representa | Ejemplo |
|-------------|----------------|---------|
| `ORG` | Organizaciones | `Apple Inc.`, `BCE`, `SEC` |
| `PERSON` | Personas | `Tim Cook`, `Jerome Powell` |
| `GPE` | Geopolíticas (países, ciudades) | `Spain`, `United States` |
| `NORP` | Nacionalidades, grupos | `European`, `American` |
| `MONEY` | Cantidades monetarias | `$1.2 billion` |
| `PERCENT` | Porcentajes | `15%`, `3.5 percent` |
| `DATE` | Fechas | `Q4 2025`, `last quarter` |
| `LAW` | Leyes, regulaciones | `GDPR`, `Dodd-Frank Act` |

Sólo extrae entidades con labels en `FINANCIAL_LABELS` (las 8 de arriba).

### `NLPService`

Fachada que combina ambos:

```python
class NLPService:
    def process(text: str) → dict:
        return {
            "clean_text": TextPreprocessor.clean(text),
            "entities": EntityExtractor.extract(text),
            "language": langdetect.detect(text),
            "cleaned_text_en": translated_text  # solo si idioma == "es"
        }
```

Si el idioma detectado es español, traduce el texto limpio a inglés usando
`deep_translator.GoogleTranslator(source="es", target="en")` (límite: 5000 chars).
El campo `cleaned_text_en` se pasa al clasificador de eventos para que FinBERT
y BART-MNLI reciban siempre texto en inglés.

## Dependencias

- `spacy` + modelo `en_core_web_sm` (descargable con `python -m spacy download en_core_web_sm`)
- `langdetect` — detección de idioma por n-gramas
- `re` — expresiones regulares para limpieza

## Relación con otros módulos

```
Ingestion ──▸ NLP ──▸ Relevance   (usa texto limpio + entidades para scoring)
                  ──▸ Events      (usa texto limpio para clasificación FinBERT + LLM)
```
