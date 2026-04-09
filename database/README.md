# Database — Capa de Acceso a MongoDB

## Propósito

Proporciona una capa de abstracción asíncrona sobre MongoDB usando **Motor**
(wrapper async de PyMongo). Gestiona el ciclo de vida de la conexión, la creación de
índices y las operaciones genéricas de lectura/escritura que consumen el resto de módulos.

## Modelo de Datos (colecciones)

| Colección | Contenido | Índices clave |
|-----------|-----------|---------------|
| `portfolios` | Carteras de inversión (activos, sectores, pesos) | — |
| `news` | Noticias ingestadas (título, resumen, URL, fuente) | `url` (unique), text index en `title` + `summary`, `published_at` desc |
| `alerts` | Alertas generadas por el pipeline | `portfolio_id`, `created_at` desc |
| `events` | Eventos clasificados (opcional, para auditoría) | `created_at` desc |

## Archivos

| Archivo | Qué contiene |
|---------|-------------|
| `mongodb.py` | Clase `MongoDB` — singleton async con Motor |

## Clase `MongoDB`

```python
class MongoDB:
    async def connect()         # Abre conexión + crea índices
    async def close()           # Cierra la conexión

    # Acceso a colecciones
    @property portfolios        # motor.AsyncIOMotorCollection
    @property news
    @property alerts
    @property events

    # Helpers genéricos
    async def insert_one(collection_name, document) → str  # Devuelve inserted_id
    async def find(collection_name, query, limit, sort)    # Devuelve lista de docs
```

## Índices Creados Automáticamente

Al llamar a `connect()`, se crean:

1. **`news.url`** — unique; evita duplicados de noticias por URL.
2. **`news.title + summary`** — text index; permite búsqueda full-text desde Mongo.
3. **`news.published_at`** — descendente; para consultar noticias recientes.
4. **`alerts.portfolio_id`** — para filtrar alertas por cartera.
5. **`alerts.created_at`** — descendente; para listar más recientes primero.

## Uso desde otros módulos

```python
from database.mongodb import MongoDB

db = MongoDB()
await db.connect()

# Insertar una noticia
news_id = await db.insert_one("news", {"title": "...", "url": "..."})

# Recuperar alertas recientes
alerts = await db.find("alerts", {"portfolio_id": pid}, limit=20, sort=[("created_at", -1)])

await db.close()
```

## Dependencias

- `motor` (AsyncIO driver para MongoDB)
- `pymongo` (usado internamente por Motor)
- Variable de entorno `MONGO_URI` (default: `mongodb://localhost:27017`)
- Variable de entorno `MONGO_DB_NAME` (default: `portfolio_alerts`)
