from app.schemas import IncidentRequest
from app.services.diagnostic_tools import (
    inspect_logs,
    inspect_metrics,
    inspect_deployment,
)


def create_incident(**overrides):
    data = {
        "title": "API errors increased after deployment",
        "description": "The API is experiencing errors and slow responses.",
        "logs": [
            "ERROR: Database connection timeout",
            "WARNING: Connection pool limit reached",
        ],
        "error_rate": 25.0,
        "latency_ms": 1800.0,
        "recent_deployment": True,
    }
    data.update(overrides)
    return IncidentRequest(**data)


def test_inspect_logs_detects_database_errors():
    incident = create_incident()

    result = inspect_logs(incident)

    categories = [
        finding["category"]
        for finding in result["findings"]
    ]

    assert result["logs_examined"] == 2
    assert "database_connection_saturation" in categories


def test_inspect_metrics_detects_high_error_rate_and_latency():
    incident = create_incident()

    result = inspect_metrics(incident)

    metrics = [
        finding["metric"]
        for finding in result["findings"]
    ]

    assert "error_rate" in metrics
    assert "latency_ms" in metrics


def test_inspect_deployment_reports_recent_deployment():
    incident = create_incident(recent_deployment=True)

    result = inspect_deployment(incident)

    assert result["recent_deployment"] is True
    assert "further evidence" in result["observation"].lower()


def test_healthy_metrics_produce_no_metric_findings():
    incident = create_incident(
        error_rate=1.0,
        latency_ms=200.0,
    )

    result = inspect_metrics(incident)

    assert result["findings"] == []