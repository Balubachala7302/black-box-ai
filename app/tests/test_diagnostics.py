from app.schemas import IncidentRequest
from app.services.diagnostics import analyze_incident


def test_database_connection_saturation():
    incident = IncidentRequest(
        title="Database connection failures",
        description="Requests are failing due to database timeouts.",
        logs=[
            "ERROR: Database connection timeout",
            "WARNING: Connection pool limit reached",
        ],
        error_rate=25.0,
        latency_ms=1800,
        recent_deployment=False,
    )

    result = analyze_incident(incident)

    causes = [item["cause"] for item in result["hypotheses"]]

    assert "Database connection saturation" in causes
    assert result["hypothesis_count"] >= 1


def test_deployment_regression():
    incident = IncidentRequest(
        title="Errors after deployment",
        description="Error rate increased after the latest deployment.",
        logs=["ERROR: Request failed with status 500"],
        error_rate=25.0,
        latency_ms=300,
        recent_deployment=True,
    )

    result = analyze_incident(incident)

    causes = [item["cause"] for item in result["hypotheses"]]

    assert "Deployment-related regression" in causes


def test_healthy_incident_produces_no_hypotheses():
    incident = IncidentRequest(
        title="Normal application operation",
        description="The application is operating within expected limits.",
        logs=["INFO: Request completed successfully"],
        error_rate=0.5,
        latency_ms=150,
        recent_deployment=False,
    )

    result = analyze_incident(incident)

    assert result["hypothesis_count"] == 0
    assert result["investigation_status"] == "insufficient_evidence"