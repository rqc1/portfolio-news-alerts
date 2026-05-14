"""
Servicio de notificaciones – Email (SMTP) y Webhook.

Envía alertas generadas por el pipeline al usuario a través de:
  1. Email vía SMTP (compatible con Gmail, Outlook, SendGrid, Resend, etc.)
  2. Webhook configurable (Telegram, Slack, Discord, o custom)

Diseñado para funcionar en background sin bloquear el pipeline de alertas.
"""

import json
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import httpx

import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
class EmailNotifier:
    """Envía alertas por email vía SMTP."""

    @staticmethod
    def is_configured() -> bool:
        return bool(
            config.SMTP_HOST
            and config.SMTP_FROM
            and config.NOTIFICATION_EMAIL_TO
        )

    @staticmethod
    def send_alert(alert_data: dict) -> bool:
        """
        Envía un email con la alerta.

        Returns True si se envió correctamente, False si hubo error.
        """
        if not EmailNotifier.is_configured():
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = config.SMTP_FROM
            msg["To"] = config.NOTIFICATION_EMAIL_TO
            msg["Subject"] = _build_subject(alert_data)

            text_body = _build_text_body(alert_data)
            html_body = _build_html_body(alert_data)

            msg.attach(MIMEText(text_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10) as server:
                if config.SMTP_USE_TLS:
                    server.starttls()
                if config.SMTP_USER and config.SMTP_PASSWORD:
                    server.login(config.SMTP_USER, config.SMTP_PASSWORD)
                server.sendmail(
                    config.SMTP_FROM,
                    config.NOTIFICATION_EMAIL_TO,
                    msg.as_string(),
                )

            logger.info("Email enviado: %s → %s", msg["Subject"], config.NOTIFICATION_EMAIL_TO)
            return True

        except Exception:
            logger.exception("Error enviando email de alerta")
            return False


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------
class WebhookNotifier:
    """Envía alertas a un endpoint HTTP (Telegram, Slack, Discord, custom)."""

    @staticmethod
    def is_configured() -> bool:
        return bool(config.NOTIFICATION_WEBHOOK_URL)

    @staticmethod
    async def send_alert(alert_data: dict) -> bool:
        """
        Envía un POST JSON al webhook configurado.

        Returns True si la respuesta es 2xx, False en caso contrario.
        """
        if not WebhookNotifier.is_configured():
            return False

        payload = _build_webhook_payload(alert_data)

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    config.NOTIFICATION_WEBHOOK_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

            if response.status_code < 300:
                logger.info("Webhook enviado: %s (status %d)", config.NOTIFICATION_WEBHOOK_URL, response.status_code)
                return True
            else:
                logger.warning("Webhook respondió con status %d: %s", response.status_code, response.text[:200])
                return False

        except Exception:
            logger.exception("Error enviando webhook de alerta")
            return False


# ---------------------------------------------------------------------------
# Servicio unificado
# ---------------------------------------------------------------------------
class NotificationService:
    """Fachada que envía alertas por todos los canales configurados."""

    @staticmethod
    async def notify(alert_data: dict) -> dict:
        """
        Envía la alerta por todos los canales disponibles.

        Returns dict con el estado de cada canal.
        """
        if not config.NOTIFICATIONS_ENABLED:
            return {"enabled": False}

        results = {"enabled": True, "email": False, "webhook": False}

        # Email (sync — SMTP es rápido para un solo email)
        if EmailNotifier.is_configured():
            results["email"] = EmailNotifier.send_alert(alert_data)

        # Webhook (async)
        if WebhookNotifier.is_configured():
            results["webhook"] = await WebhookNotifier.send_alert(alert_data)

        return results

    @staticmethod
    def get_status() -> dict:
        """Devuelve qué canales están configurados."""
        return {
            "enabled": config.NOTIFICATIONS_ENABLED,
            "email_configured": EmailNotifier.is_configured(),
            "email_to": config.NOTIFICATION_EMAIL_TO if EmailNotifier.is_configured() else None,
            "webhook_configured": WebhookNotifier.is_configured(),
        }


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------
_SEVERITY_EMOJI = {
    "muy_alta": "🔴",
    "alta": "🟠",
    "media": "🟡",
    "baja": "🟢",
    "muy_baja": "⚪",
}

_DIRECTION_EMOJI = {
    "alcista": "📈",
    "bajista": "📉",
    "neutral": "➡️",
}


def _build_subject(alert: dict) -> str:
    severity = alert.get("severity_label", "media")
    direction = alert.get("direction", "neutral")
    emoji = _SEVERITY_EMOJI.get(severity, "🔔")
    assets = ", ".join(alert.get("matched_assets", [])) or "cartera"
    return f"{emoji} Alerta {direction} ({severity}) — {assets}"


def _build_text_body(alert: dict) -> str:
    lines = [
        f"ALERTA: {alert.get('news_title', 'Sin título')}",
        "",
        f"Dirección: {alert.get('direction', 'neutral')}",
        f"Severidad: {alert.get('severity_label', '?')} ({alert.get('severity', 0):.2f})",
        f"Confianza: {alert.get('confidence', 0):.2f}",
        f"Activos: {', '.join(alert.get('matched_assets', []))}",
        f"Evento: {alert.get('event_type', '?')}",
        f"Sentimiento: {alert.get('sentiment', '?')}",
        "",
        f"Explicación: {alert.get('explanation', '')}",
        "",
        f"Fuente: {alert.get('news_source', '?')}",
        f"URL: {alert.get('news_url', '')}",
    ]
    return "\n".join(lines)


def _build_html_body(alert: dict) -> str:
    severity = alert.get("severity_label", "media")
    direction = alert.get("direction", "neutral")
    dir_emoji = _DIRECTION_EMOJI.get(direction, "")
    sev_emoji = _SEVERITY_EMOJI.get(severity, "")

    assets = ", ".join(alert.get("matched_assets", [])) or "cartera general"

    return f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #1a1a2e; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
            <h2 style="margin: 0;">{sev_emoji} Alerta {direction} — {assets}</h2>
            <p style="margin: 8px 0 0; opacity: 0.8;">{alert.get('news_title', '')}</p>
        </div>
        <div style="background: #f8f9fa; padding: 20px; border: 1px solid #dee2e6;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="padding: 6px 0;"><strong>Dirección</strong></td><td>{dir_emoji} {direction}</td></tr>
                <tr><td style="padding: 6px 0;"><strong>Severidad</strong></td><td>{sev_emoji} {severity} ({alert.get('severity', 0):.2f})</td></tr>
                <tr><td style="padding: 6px 0;"><strong>Confianza</strong></td><td>{alert.get('confidence', 0):.2f}</td></tr>
                <tr><td style="padding: 6px 0;"><strong>Evento</strong></td><td>{alert.get('event_type', '?')}</td></tr>
                <tr><td style="padding: 6px 0;"><strong>Sentimiento</strong></td><td>{alert.get('sentiment', '?')}</td></tr>
            </table>
        </div>
        <div style="background: white; padding: 20px; border: 1px solid #dee2e6; border-top: none;">
            <p style="margin: 0 0 12px;"><strong>Explicación:</strong></p>
            <p style="margin: 0; color: #333;">{alert.get('explanation', '')}</p>
        </div>
        <div style="background: #e9ecef; padding: 12px 20px; border-radius: 0 0 8px 8px; font-size: 13px;">
            <a href="{alert.get('news_url', '#')}" style="color: #0066cc;">Ver noticia original</a>
            &nbsp;|&nbsp; Fuente: {alert.get('news_source', '?')}
        </div>
    </div>
    """


def _build_webhook_payload(alert: dict) -> dict:
    """Payload genérico para webhook. Compatible con la mayoría de servicios."""
    severity = alert.get("severity_label", "media")
    direction = alert.get("direction", "neutral")
    emoji = _SEVERITY_EMOJI.get(severity, "🔔")
    assets = ", ".join(alert.get("matched_assets", [])) or "cartera"

    # Formato compatible con Slack/Discord (campo "text" o "content")
    text = (
        f"{emoji} *Alerta {direction} ({severity})* — {assets}\n"
        f"📰 {alert.get('news_title', '')}\n"
        f"📊 Severidad: {alert.get('severity', 0):.2f} | Confianza: {alert.get('confidence', 0):.2f}\n"
        f"💡 {alert.get('explanation', '')}\n"
        f"🔗 {alert.get('news_url', '')}"
    )

    return {
        "text": text,          # Slack / generic
        "content": text,       # Discord
        "alert": alert,        # Full data for custom webhooks
    }
