"""Tests para módulo Notifications (service)."""

from modules.notifications.service import (
    WebhookNotifier,
    NotificationService,
    _build_subject,
    _build_text_body,
    _build_webhook_payload,
)


class TestWebhookNotifier:
    def test_not_configured_by_default(self):
        assert WebhookNotifier.is_configured() is False


class TestBuildSubject:
    def test_subject_with_assets(self):
        subject = _build_subject({
            "severity_label": "alta",
            "direction": "bajista",
            "matched_assets": ["AAPL", "TSLA"],
        })
        assert "bajista" in subject
        assert "alta" in subject
        assert "AAPL" in subject

    def test_subject_without_assets(self):
        subject = _build_subject({
            "severity_label": "media",
            "direction": "neutral",
            "matched_assets": [],
        })
        assert "cartera" in subject


class TestBuildTextBody:
    def test_body_contains_all_fields(self):
        body = _build_text_body({
            "news_title": "Apple earnings beat",
            "direction": "alcista",
            "severity_label": "alta",
            "severity": 0.75,
            "confidence": 0.85,
            "matched_assets": ["AAPL"],
            "event_type": "resultados_empresariales",
            "sentiment": "positive",
            "explanation": "Strong results for your portfolio",
            "news_source": "reuters",
            "news_url": "https://example.com",
        })
        assert "Apple earnings beat" in body
        assert "alcista" in body
        assert "AAPL" in body
        assert "reuters" in body


class TestBuildWebhookPayload:
    def test_payload_structure(self):
        payload = _build_webhook_payload({
            "severity_label": "alta",
            "direction": "bajista",
            "matched_assets": ["AAPL"],
            "news_title": "Test alert",
            "severity": 0.7,
            "confidence": 0.8,
            "explanation": "Test explanation",
            "news_url": "https://example.com",
        })
        assert "text" in payload     # Slack
        assert "content" in payload  # Discord
        assert "alert" in payload    # Raw data
        assert "AAPL" in payload["text"]


class TestNotificationService:
    def test_get_status(self):
        status = NotificationService.get_status()
        assert "enabled" in status
        assert "email_configured" in status
        assert "webhook_configured" in status
