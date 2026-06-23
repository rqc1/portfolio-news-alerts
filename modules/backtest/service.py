"""
Servicio de backtesting de alertas y feedback loop.

Backtesting
-----------
Toma las alertas almacenadas y mide, mediante el estudio de eventos (CAR),
si anticiparon el movimiento real del precio. Permite contrastar la dirección
predicha y la severidad asignada con el retorno anormal observado.

Feedback loop
-------------
Registra la valoración del usuario sobre cada alerta (útil / no útil) y expone
estadísticos agregados. Estas señales alimentan la mejora continua del sistema
(ajuste de umbrales, datos para reentrenamiento).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field

from database.mongodb import MongoDB
from modules.backtest.event_study import (
    EventSpec,
    EventStudyConfig,
    YFinancePriceProvider,
    run_single_event,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------
class AlertFeedback(BaseModel):
    alert_id: str
    user_id: str = "default"
    useful: bool
    comment: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FeedbackService:
    """Gestiona la valoración de alertas por parte del usuario."""

    @staticmethod
    async def record(feedback: AlertFeedback) -> None:
        await MongoDB.alert_feedback().update_one(
            {"alert_id": feedback.alert_id, "user_id": feedback.user_id},
            {
                "$set": {
                    "useful": feedback.useful,
                    "comment": feedback.comment,
                    "updated_at": datetime.now(timezone.utc),
                },
                "$setOnInsert": {
                    "alert_id": feedback.alert_id,
                    "user_id": feedback.user_id,
                    "created_at": feedback.created_at,
                },
            },
            upsert=True,
        )
        # Propagar la señal a la alerta para facilitar consultas/filtrado.
        try:
            await MongoDB.alerts().update_one(
                {"_id": ObjectId(feedback.alert_id)},
                {"$set": {"feedback_useful": feedback.useful}},
            )
        except Exception:
            logger.debug("No se pudo anotar feedback en la alerta %s", feedback.alert_id)

    @staticmethod
    async def stats(portfolio_id: str = "") -> dict:
        query: dict = {}
        if portfolio_id:
            # alert_feedback no guarda portfolio_id directamente salvo que se anote.
            query["portfolio_id"] = portfolio_id
        useful = await MongoDB.alert_feedback().count_documents({**query, "useful": True})
        not_useful = await MongoDB.alert_feedback().count_documents({**query, "useful": False})
        total = useful + not_useful
        return {
            "total": total,
            "useful": useful,
            "not_useful": not_useful,
            "useful_rate": round(useful / total, 4) if total else 0.0,
        }


# ---------------------------------------------------------------------------
# Backtesting de alertas
# ---------------------------------------------------------------------------
class AlertBacktestService:
    """Evalúa retrospectivamente la calidad predictiva de las alertas."""

    @staticmethod
    def _event_date(alert: dict) -> Optional[date]:
        raw = alert.get("created_at")
        if isinstance(raw, datetime):
            return raw.date()
        if isinstance(raw, str):
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
            except ValueError:
                return None
        return None

    @classmethod
    async def backtest(
        cls,
        portfolio_id: str = "",
        limit: int = 100,
        config: Optional[EventStudyConfig] = None,
        persist: bool = True,
    ) -> dict:
        config = config or EventStudyConfig()
        query: dict = {}
        if portfolio_id:
            query["portfolio_id"] = portfolio_id

        cursor = MongoDB.alerts().find(query).sort("created_at", -1).limit(limit)
        alerts = await cursor.to_list(length=limit)

        provider = YFinancePriceProvider()
        per_alert: list[dict] = []
        # Acumuladores para hit-rate y CAR por severidad.
        primary_window = config.event_windows[0]
        cars: list[float] = []
        dir_hits = 0
        dir_total = 0
        sev_bucket: dict[str, list[float]] = {}
        # Pares (score_severidad, |CAR|) para calibración empírica.
        calib_scores: list[float] = []
        calib_abs_cars: list[float] = []

        for alert in alerts:
            ev_date = cls._event_date(alert)
            tickers = alert.get("matched_assets") or []
            direction = alert.get("direction")
            severity_label = alert.get("severity_label", "")
            severity_score = alert.get("severity")
            if ev_date is None or not tickers:
                continue

            alert_results = []
            for ticker in tickers:
                res = run_single_event(
                    ticker=ticker,
                    event_date=ev_date,
                    provider=provider,
                    config=config,
                    predicted_direction=direction,
                )
                if not res.ok:
                    alert_results.append({"ticker": ticker, "error": res.error})
                    continue

                car = res.car(primary_window) or 0.0
                cars.append(car)
                # Acierto direccional sobre la ventana primaria.
                if direction in ("alcista", "bajista", "neutral"):
                    realized = (
                        "alcista" if car > config.neutral_band
                        else "bajista" if car < -config.neutral_band
                        else "neutral"
                    )
                    dir_total += 1
                    if realized == direction:
                        dir_hits += 1
                sev_bucket.setdefault(severity_label, []).append(abs(car))
                if isinstance(severity_score, (int, float)):
                    calib_scores.append(float(severity_score))
                    calib_abs_cars.append(abs(car))
                alert_results.append(res.to_dict())

            record = {
                "alert_id": str(alert.get("_id", "")),
                "portfolio_id": alert.get("portfolio_id", ""),
                "event_date": ev_date.isoformat(),
                "direction": direction,
                "severity_label": severity_label,
                "results": alert_results,
            }
            per_alert.append(record)

            if persist:
                try:
                    await MongoDB.backtest_results().update_one(
                        {"alert_id": record["alert_id"]},
                        {"$set": {**record, "created_at": datetime.now(timezone.utc)}},
                        upsert=True,
                    )
                except Exception:
                    logger.debug("No se pudo persistir backtest de %s", record["alert_id"])

        import numpy as np

        agg = {
            "n_alerts": len(per_alert),
            "n_car_observations": len(cars),
            "mean_car": round(float(np.mean(cars)), 6) if cars else 0.0,
            "mean_abs_car": round(float(np.mean(np.abs(cars))), 6) if cars else 0.0,
            "directional_hit_rate": round(dir_hits / dir_total, 4) if dir_total else None,
            "n_directional": dir_total,
            "primary_window": list(primary_window),
            "car_by_severity": {
                sev: {
                    "n": len(vals),
                    "mean_abs_car": round(float(np.mean(vals)), 6),
                }
                for sev, vals in sorted(sev_bucket.items())
            },
        }

        return {
            "aggregate": agg,
            "per_alert": per_alert,
            "_calibration_pairs": {"scores": calib_scores, "abs_cars": calib_abs_cars},
        }

    @classmethod
    async def fit_calibrator(
        cls,
        portfolio_id: str = "",
        limit: int = 500,
        save_path: Optional[str] = None,
    ) -> dict:
        """Ajusta el calibrador de severidad con datos reales de backtesting.

        Recolecta pares (score de severidad, |CAR| observado) de las alertas
        almacenadas y ajusta una regresión isotónica. Persiste el resultado
        para que el estimador lo use en futuras predicciones.
        """
        from modules.impact.calibration import SeverityCalibrator

        bt = await cls.backtest(portfolio_id=portfolio_id, limit=limit, persist=False)
        pairs = bt["_calibration_pairs"]
        cal = SeverityCalibrator()
        fitted = cal.fit(pairs["scores"], pairs["abs_cars"])
        if fitted and save_path:
            cal.save(save_path)
        return {
            "fitted": fitted,
            "n_samples": cal.n_samples,
            "calibration": cal.to_dict() if fitted else None,
            "saved_to": save_path if (fitted and save_path) else None,
        }
