"""Tests para módulo Scheduler (service)."""

from modules.scheduler.service import get_scheduler_status


class TestSchedulerStatus:
    def test_status_when_not_started(self):
        status = get_scheduler_status()
        # Scheduler no está arrancado en tests
        assert "running" in status
        assert "jobs" in status
