"""Tests for health monitoring (GATES.md M9, PLAYBOOK §4.3).

TDD: Write tests first, confirm they fail, then implement.
"""

from src.maintenance.health import evaluate_alerts, log_health_metrics


def _healthy_metrics() -> dict[str, int]:
    """Return a set of healthy pipeline metrics."""
    return {
        "jobs_ingested_last_hour": 50,
        "jobs_ingested_last_24h": 1200,
        "queue_raw": 0,
        "queue_parsed": 0,
        "queue_normalized": 0,
        "queue_geocoded": 0,
        "total_ready": 5000,
        "total_expired": 200,
        "jobs_with_retries": 10,
        "jobs_in_dlq": 5,
        "ready_without_embedding": 0,
        "ready_without_salary": 100,
        "ready_without_location": 20,
        "db_size_bytes": 500_000_000,
    }


# ── M9: Alert conditions ──


class TestEvaluateAlerts:
    def test_healthy_no_alerts(self) -> None:
        """Healthy metrics should produce no alerts."""
        alerts = evaluate_alerts(_healthy_metrics())
        assert len(alerts) == 0

    def test_zero_ingestion_critical(self) -> None:
        """jobs_ingested_last_hour = 0 → CRITICAL alert."""
        metrics = _healthy_metrics()
        metrics["jobs_ingested_last_hour"] = 0
        alerts = evaluate_alerts(metrics)
        assert any(a["level"] == "critical" for a in alerts)
        assert any("jobs_ingested_last_hour" in a["message"] for a in alerts)

    def test_dlq_overflow_warning(self) -> None:
        """jobs_in_dlq > 100 → WARNING alert."""
        metrics = _healthy_metrics()
        metrics["jobs_in_dlq"] = 150
        alerts = evaluate_alerts(metrics)
        assert any(a["level"] == "warning" for a in alerts)
        assert any("jobs_in_dlq" in a["message"] for a in alerts)

    def test_dlq_at_threshold_no_alert(self) -> None:
        """jobs_in_dlq = 100 should not trigger alert (must be > 100)."""
        metrics = _healthy_metrics()
        metrics["jobs_in_dlq"] = 100
        alerts = evaluate_alerts(metrics)
        dlq_alerts = [a for a in alerts if "jobs_in_dlq" in a["message"]]
        assert len(dlq_alerts) == 0

    def test_ready_without_embedding_warning(self) -> None:
        """ready_without_embedding > 0 → WARNING alert."""
        metrics = _healthy_metrics()
        metrics["ready_without_embedding"] = 5
        alerts = evaluate_alerts(metrics)
        assert any(a["level"] == "warning" for a in alerts)
        assert any("ready_without_embedding" in a["message"] for a in alerts)

    def test_multiple_alerts(self) -> None:
        """Multiple alert conditions can fire simultaneously."""
        metrics = _healthy_metrics()
        metrics["jobs_ingested_last_hour"] = 0
        metrics["jobs_in_dlq"] = 200
        metrics["ready_without_embedding"] = 10
        alerts = evaluate_alerts(metrics)
        assert len(alerts) == 3


# ── log_health_metrics ──


class TestLogHealthMetrics:
    def test_log_health_does_not_crash(self) -> None:
        """Logging healthy metrics should not raise."""
        log_health_metrics(_healthy_metrics())

    def test_log_health_empty_metrics(self) -> None:
        """Empty metrics dict should not crash."""
        log_health_metrics({})


# ── Sad paths ──


class TestHealthEdgeCases:
    def test_missing_keys_no_crash(self) -> None:
        """Missing metric keys should not crash evaluate_alerts."""
        alerts = evaluate_alerts({})
        # With all metrics missing/zero, ingestion alert should fire
        assert any(a["level"] == "critical" for a in alerts)

    def test_none_values_treated_as_zero(self) -> None:
        """None values should be treated as 0."""
        metrics = _healthy_metrics()
        metrics["jobs_ingested_last_hour"] = None  # type: ignore[assignment]
        alerts = evaluate_alerts(metrics)
        assert any(a["level"] == "critical" for a in alerts)

    def test_negative_values_no_crash(self) -> None:
        """Negative values should not crash (shouldn't happen, but be safe)."""
        metrics = _healthy_metrics()
        metrics["jobs_in_dlq"] = -1
        alerts = evaluate_alerts(metrics)
        # Negative shouldn't trigger > 100 alert
        dlq_alerts = [a for a in alerts if "jobs_in_dlq" in a["message"]]
        assert len(dlq_alerts) == 0
