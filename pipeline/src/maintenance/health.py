"""Health monitoring and alerting (PLAYBOOK §4.3, SPEC.md §1.4).

Query pipeline_health view. Log all 14 metrics via structlog.
Check alert conditions:
  jobs_ingested_last_hour = 0 → CRITICAL
  jobs_in_dlq > 100 → WARNING
  ready_without_embedding > 0 → WARNING
"""

import structlog

logger = structlog.get_logger()


def evaluate_alerts(metrics: dict[str, int]) -> list[dict[str, str]]:
    """Check pipeline health metrics against alert thresholds.

    Args:
        metrics: Dict of 14 metrics from pipeline_health view.

    Returns:
        List of alert dicts with 'level' and 'message' keys.
        Empty list if all metrics are healthy.
    """
    alerts: list[dict[str, str]] = []

    # CRITICAL: Zero ingestion
    ingested = metrics.get("jobs_ingested_last_hour")
    ingested_val = int(ingested) if ingested is not None else 0
    if ingested_val == 0:
        alerts.append(
            {
                "level": "critical",
                "message": (
                    "jobs_ingested_last_hour = 0: "
                    "Check API keys, circuit breaker state, Modal logs"
                ),
            }
        )

    # WARNING: DLQ overflow (> 100, not >=)
    dlq_count = metrics.get("jobs_in_dlq")
    dlq_val = int(dlq_count) if dlq_count is not None else 0
    if dlq_val > 100:
        alerts.append(
            {
                "level": "warning",
                "message": (
                    f"jobs_in_dlq = {dlq_val}: "
                    "Check last_error patterns, investigate source quality"
                ),
            }
        )

    # WARNING: Ready jobs missing embeddings
    no_embed = metrics.get("ready_without_embedding")
    no_embed_val = int(no_embed) if no_embed is not None else 0
    if no_embed_val > 0:
        alerts.append(
            {
                "level": "warning",
                "message": (
                    f"ready_without_embedding = {no_embed_val}: "
                    "Check GOOGLE_API_KEY, Gemini API status, rate limits"
                ),
            }
        )

    return alerts


def log_health_metrics(metrics: dict[str, int]) -> None:
    """Log all pipeline health metrics and fire alerts.

    Args:
        metrics: Dict of metrics from pipeline_health view (up to 14 columns).
    """
    # Log all metrics at INFO level
    logger.info("pipeline_health", **{k: v for k, v in metrics.items()})

    # Evaluate and log alerts
    alerts = evaluate_alerts(metrics)
    for alert in alerts:
        if alert["level"] == "critical":
            logger.critical("health_alert", message=alert["message"])
        else:
            logger.warning("health_alert", message=alert["message"])

    if not alerts:
        logger.info("pipeline_health_ok", alert_count=0)
