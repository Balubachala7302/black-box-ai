
from app.schemas import IncidentRequest
from app.services.investigator import investigate


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


def test_investigation_collects_all_evidence():
    result = investigate(create_incident())

    assert "logs" in result["evidence"]
    assert "metrics" in result["evidence"]
    assert "deployment" in result["evidence"]


def test_investigation_records_tool_trace():
    result = investigate(create_incident())

    tools = [
        step["tool"]
        for step in result["investigation_trace"]
    ]

    assert tools == [
        "inspect_logs",
        "inspect_metrics",
        "inspect_deployment",
    ]


def test_investigation_generates_hypotheses():
    result = investigate(create_incident())

    assert result["hypothesis_count"] > 0
    assert len(result["hypotheses"]) == result["hypothesis_count"]


def test_healthy_incident_reports_no_hypotheses():
    incident = create_incident(
        logs=["INFO: Request completed successfully"],
        error_rate=1.0,
        latency_ms=200.0,
        recent_deployment=False,
    )

    result = investigate(incident)

    assert result["hypothesis_count"] == 0
