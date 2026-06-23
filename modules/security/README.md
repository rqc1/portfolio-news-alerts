# Módulo — Security (Capa de producción: seguridad y observabilidad)

## Propósito

Añade la capa operativa necesaria para un despliegue **seguro y observable**, elevando el
prototipo a un sistema apto para producción. Cubre autenticación, registro estructurado,
métricas, limitación de tasa, CORS y sondas de salud.

Todos los componentes siguen el principio de **degradación elegante**: están desactivados o
en modo permisivo por defecto y se habilitan mediante variables de configuración, de modo que
el sistema sigue siendo ejecutable en local sin infraestructura adicional.

## Archivos

| Archivo | Qué contiene |
|---------|-------------|
| `auth.py` | Autenticación JWT + hash de contraseñas + `AuthService` y `get_current_user` |
| `logging_config.py` | Configuración de `structlog` (logging estructurado) |
| `metrics.py` | Métricas Prometheus (HTTP y consumo de LLM) |

## Autenticación (`auth.py`)

- **JWT HS256** (`python-jose`): `create_access_token()` / `decode_token()`, expiración
  configurable (`JWT_EXPIRE_MINUTES`).
- **Hash de contraseñas con `bcrypt`** directamente (ver decisión de diseño abajo).
- **Modelos Pydantic**: `UserCreate`, `UserPublic`, `TokenResponse`, `CurrentUser`.
- **`AuthService`**: `register()` (409 si el email ya existe) y `authenticate()`.
- **`get_current_user()`**: devuelve un usuario anónimo si `AUTH_ENABLED=false`; en caso
  contrario exige un Bearer válido (401 si falta o es inválido).

### Decisión de diseño: bcrypt directo (no passlib)

`passlib 1.7.4` es **incompatible con `bcrypt 5.0.0`** (lee el atributo eliminado
`bcrypt.__about__` y lanza `ValueError` con contraseñas de más de 72 bytes). Por ello se usa
la librería `bcrypt` **directamente**, truncando explícitamente la contraseña a 72 bytes
UTF-8 antes de `hashpw`/`checkpw`.

### Endpoints (en `main.py`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/auth/register` | Alta de usuario → `UserPublic` |
| `POST` | `/api/auth/login` | Login OAuth2 password → `TokenResponse` |
| `GET` | `/api/auth/me` | Usuario actual |

## Logging estructurado (`logging_config.py`)

- `configure_logging(json_logs, level)` — `structlog` con `merge_contextvars`, nivel de log,
  marca de tiempo ISO; `JSONRenderer` o `ConsoleRenderer` según `LOG_JSON`.
- `get_logger(name="investailert")`.
- Un **`request-id`** se genera por petición y se propaga por contexto, añadiéndose además
  como cabecera `X-Request-ID` en la respuesta.

## Métricas Prometheus (`metrics.py`)

| Métrica | Etiquetas | Descripción |
|---------|-----------|-------------|
| `HTTP_REQUESTS` | method, path, status | Volumen de peticiones HTTP |
| `HTTP_LATENCY` | method, path | Latencia de peticiones |
| `LLM_REQUESTS` | provider, model, status | Peticiones al LLM |
| `LLM_TOKENS` | provider, model, type | Tokens consumidos (prompt/completion) |
| `LLM_COST` | provider, model | Coste estimado |
| `ALERTS_GENERATED` | — | Alertas generadas |

- `record_http(...)`, `record_llm(...)`, `render_latest()`.
- Se exponen en el endpoint **`/metrics`** (404 si `METRICS_ENABLED=false`).
- El consumo de LLM se registra automáticamente desde `modules/llm/providers.py`.

## Otras protecciones (configuradas en `main.py`)

| Protección | Detalle |
|------------|---------|
| **Rate limiting** | `slowapi` por IP (`RATE_LIMIT_DEFAULT`, `RATE_LIMIT_ENABLED`); responde 429 |
| **CORS restringido** | `CORS_ORIGINS` explícitos en lugar de comodín |
| **Health probes** | `/health/live`, `/health/ready` (503 si DB caída), `/health/db` |

## Variables de configuración (`config.py`)

`CORS_ORIGINS`, `AUTH_ENABLED` (default `false`), `JWT_SECRET`, `JWT_ALGORITHM` (HS256),
`JWT_EXPIRE_MINUTES` (1440), `RATE_LIMIT_DEFAULT` (`120/minute`), `RATE_LIMIT_AUTH`
(`10/minute`), `RATE_LIMIT_ENABLED`, `LOG_JSON`, `LOG_LEVEL`, `METRICS_ENABLED`,
`LLM_COST_PER_1K_PROMPT`, `LLM_COST_PER_1K_COMPLETION`, `SEVERITY_CALIBRATOR_PATH`.

## Pruebas

`tests/test_security.py` (14 tests): hashing de contraseñas, tokens (roundtrip, inválido,
expirado), `get_current_user` (anónimo/401/válido) y métricas.

> ⚠️ **Seguridad**: el archivo `.env` contiene credenciales reales. Asegúrate de que está en
> `.gitignore` y rota cualquier secreto que se haya compartido.
