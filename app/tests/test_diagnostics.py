
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


def test_hypotheses_include_verification_details():
    incident = IncidentRequest(
        title="Database connection failures",
        description=(
            "Requests are failing due to database connection timeouts."
        ),
        logs=[
            "ERROR: Database connection timeout",
            "WARNING: Connection pool limit reached",
        ],
        error_rate=25.0,
        latency_ms=1800.0,
        recent_deployment=False,
    )

    result = analyze_incident(incident)

    assert result["hypothesis_count"] > 0

    for hypothesis in result["hypotheses"]:
        assert hypothesis["verification_status"] == "unverified"
        assert "supporting_evidence" in hypothesis
        assert "missing_evidence" in hypothesis
        assert len(hypothesis["missing_evidence"]) > 0


def test_upstream_dependency_failure_is_detected():
    incident = IncidentRequest(
        title="Payment provider timeout",
        description="Payment requests are failing due to provider timeouts.",
        logs=[
            "ERROR: Upstream timeout calling payment provider",
            "WARNING: Service unavailable from dependency",
        ],
        error_rate=12.0,
        latency_ms=2400.0,
        recent_deployment=False,
    )

    result = analyze_incident(incident)

    causes = [item["cause"] for item in result["hypotheses"]]

    assert "Upstream dependency failure" in causes

    hypothesis = next(
        item
        for item in result["hypotheses"]
        if item["cause"] == "Upstream dependency failure"
    )

    assert hypothesis["verification_status"] == "unverified"
    assert len(hypothesis["evidence"]) == 2
    assert len(hypothesis["missing_evidence"]) > 0


def test_latency_hypothesis_includes_missing_evidence():
    incident = IncidentRequest(
        title="Application latency spike",
        description="The application is responding slowly.",
        logs=["INFO: Request completed successfully"],
        error_rate=0.5,
        latency_ms=1800.0,
        recent_deployment=False,
    )

    result = analyze_incident(incident)

    hypothesis = next(
        item
        for item in result["hypotheses"]
        if item["cause"] == "Elevated application latency"
    )

    assert hypothesis["verification_status"] == "unverified"
    assert hypothesis["missing_evidence"]
    assert hypothesis["recommended_check"]


def test_confidence_scores_are_sorted_descending():
    incident = IncidentRequest(
        title="Multiple service symptoms",
        description="Database errors and latency increased.",
        logs=[
            "ERROR: Database connection timeout",
            "ERROR: Upstream timeout calling payment provider",
        ],
        error_rate=25.0,
        latency_ms=1800.0,
        recent_deployment=True,
    )

    result = analyze_incident(incident)

    scores = [
        item["confidence"]
        for item in result["hypotheses"]
    ]

    assert scores == sorted(scores, reverse=True)


def test_confidence_note_explains_uncertainty():
    incident = IncidentRequest(
        title="Database connection failures",
        description="Requests are failing due to database timeouts.",
        logs=["ERROR: Database connection timeout"],
        error_rate=25.0,
        latency_ms=1800.0,
        recent_deployment=False,
    )

    result = analyze_incident(incident)
    note = result["note"].lower()

    assert "not calibrated" in note
    assert "root cause" in note
    assert "verification" in note or "verify" in note
