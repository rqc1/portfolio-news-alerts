# Módulo — Backtest (Validación financiera y bucle de retroalimentación)

## Propósito

Cierra el bucle entre la **evaluación lingüística** del sistema (¿la alerta coincide con
la etiqueta humana?) y su **validez económica** (¿la alerta anticipa un movimiento real
del mercado?). Aporta tres capacidades:

1. **Estudio de evento (event study)** — Cuantifica el retorno anormal (AR) y el retorno
   anormal acumulado (CAR) alrededor de la fecha de cada alerta, siguiendo la metodología
   clásica de mercado (MacKinlay, 1997).
2. **Backtesting de alertas** — Reproduce el historial de alertas de una cartera y mide su
   capacidad direccional agregada.
3. **Bucle de retroalimentación + autocalibración** — Recoge feedback del usuario y reajusta
   los umbrales de decisión a partir de la evidencia acumulada.

Todo el módulo sigue el principio de **degradación elegante**: si no hay datos de precios o
historial suficiente, devuelve resultados vacíos sin romper el sistema.

## Archivos

| Archivo | Qué contiene |
|---------|-------------|
| `event_study.py` | Estudio de evento: AR/CAR, modelo de mercado, agregación |
| `service.py` | `FeedbackService`, `AlertBacktestService` (backtest + calibración) |

## Estudio de evento (`event_study.py`)

### Metodología

Para cada evento (alerta sobre un activo en una fecha) se estima un **modelo de mercado**
sobre una ventana de estimación previa al evento:

```
R_activo,t = α + β · R_mercado,t + ε_t
```

A partir de α y β se calcula el **retorno anormal** en la ventana de evento:

```
AR_t = R_activo,t − (α + β · R_mercado,t)
CAR[t1, t2] = Σ AR_t   (t = t1 … t2)
```

El signo y la magnitud del CAR permiten contrastar si la **dirección predicha** por el
sistema (alcista/bajista) se corresponde con el comportamiento posterior del activo.

### Componentes principales

| Símbolo | Descripción |
|---------|-------------|
| `EventStudyConfig` | Ventanas de estimación y de evento (días relativos al evento) |
| `PriceProvider` (Protocol) | Interfaz para obtener retornos diarios de un ticker |
| `YFinancePriceProvider` | Implementación por defecto basada en `yfinance` |
| `estimate_market_model()` | Estima α y β del modelo de mercado |
| `run_single_event()` | Calcula AR/CAR de un único evento |
| `run_event_study()` | Ejecuta el estudio sobre una lista de `EventSpec` y agrega resultados |
| `EventResult` / `AggregateWindowStats` | Resultados por evento y agregados por ventana |

## Backtesting y feedback (`service.py`)

| Clase / método | Descripción |
|----------------|-------------|
| `AlertFeedback` | Modelo Pydantic del feedback de una alerta (útil/no útil) |
| `FeedbackService.record()` | Persiste el feedback del usuario en MongoDB |
| `FeedbackService.stats()` | Estadísticas agregadas de feedback por cartera |
| `AlertBacktestService.backtest()` | Reproduce el historial de alertas y mide la capacidad direccional vía estudio de evento |
| `AlertBacktestService.fit_calibrator()` | Reajusta umbrales de relevancia/severidad que maximizan la utilidad direccional |

## Endpoints expuestos (en `main.py`)

| Método | Ruta | Descripción | Protegido |
|--------|------|-------------|:---------:|
| `GET` | `/api/backtest/{portfolio_id}` | Backtest direccional de las alertas de la cartera | ✅ (auth) |
| `POST` | `/api/backtest/{portfolio_id}/calibrate` | Recalibra umbrales con la evidencia acumulada | ✅ (auth) |

> Los endpoints quedan protegidos por la capa de autenticación (`modules/security/`).
> Con `AUTH_ENABLED=false` (por defecto) operan en modo anónimo.

## Pruebas

`tests/test_evaluation.py` y los tests del módulo cubren la estimación del modelo de
mercado, el cálculo de AR/CAR, la agregación de eventos y el backtesting direccional.

## Referencias

- MacKinlay, A. C. (1997). *Event Studies in Economics and Finance.* Journal of Economic
  Literature, 35(1), 13–39.
