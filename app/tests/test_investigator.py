from app.schemas import IncidentRequest
from app.services.investigator import (
    investigate,
    decide_root_cause,
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


# Investigation pipeline tests


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
        "identify_evidence_gaps",
        "decide_root_cause",
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


def test_database_candidate_reports_missing_independent_telemetry():
    result = investigate(
        create_incident(recent_deployment=False)
    )

    database_hypotheses = [
        hypothesis
        for hypothesis in result["hypotheses"]
        if hypothesis["cause"] == "Database connection saturation"
    ]

    assert database_hypotheses

    database_candidate = database_hypotheses[0]

    assert database_candidate["verification_status"] == "supported"
    assert any(
        "Independent database telemetry" in item
        for item in database_candidate["missing_evidence"]
    )

    assert any(
        gap["cause"] == "Database connection saturation"
        and any(
            "Independent database telemetry" in item
            for item in gap["missing_evidence"]
        )
        for gap in result["evidence_gaps"]["gaps"]
    )


def test_database_candidate_is_reported_as_provisional():
    result = investigate(
        create_incident(recent_deployment=False)
    )

    decision = result["root_cause_decision"]

    assert decision["status"] == "candidate_supported"
    assert decision["root_cause"] == "Database connection saturation"
    assert "not definitive proof" in decision["reason"]


# Root-cause decision tests


def test_decision_selects_one_supported_database_candidate():
    hypotheses = [
        {
            "cause": "Database connection saturation",
            "verification_status": "supported",
        }
    ]

    result = decide_root_cause(hypotheses)

    assert result["status"] == "candidate_supported"
    assert result["root_cause"] == "Database connection saturation"


def test_decision_abstains_when_only_latency_is_supported():
    hypotheses = [
        {
            "cause": "Elevated application latency",
            "verification_status": "supported",
        }
    ]

    result = decide_root_cause(hypotheses)

    assert result["status"] == "abstained_insufficient_evidence"
    assert result["root_cause"] is None


def test_decision_abstains_on_inconclusive_deployment():
    hypotheses = [
        {
            "cause": "Deployment-related regression",
            "verification_status": "inconclusive",
        }
    ]

    result = decide_root_cause(hypotheses)

    assert result["status"] == "abstained_insufficient_evidence"
    assert result["root_cause"] is None


def test_decision_abstains_on_conflicting_evidence():
    hypotheses = [
        {
            "cause": "Database connection saturation",
            "verification_status": "conflicting",
        }
    ]

    result = decide_root_cause(hypotheses)

    assert result["status"] == "abstained_conflicting_evidence"
    assert result["root_cause"] is None


def test_decision_abstains_when_multiple_causes_are_supported():
    hypotheses = [
        {
            "cause": "Database connection saturation",
            "verification_status": "supported",
        },
        {
            "cause": "Upstream dependency failure",
            "verification_status": "supported",
        },
    ]

    result = decide_root_cause(hypotheses)

    assert result["status"] == "abstained_multiple_candidates"
    assert result["root_cause"] is None


def test_decision_abstains_when_no_hypotheses_exist():
    result = decide_root_cause([])

    assert result["status"] == "abstained_insufficient_evidence"
    assert result["root_cause"] is None


def test_conflicting_database_logs_prevent_root_cause_selection():
    incident = create_incident(
        logs=[
            "ERROR: Database connection timeout",
            "WARNING: Connection pool limit reached",
            "INFO: Database active connections are within normal range",
        ],
        recent_deployment=False,
    )

    result = investigate(incident)

    database_hypotheses = [
        hypothesis
        for hypothesis in result["hypotheses"]
        if hypothesis["cause"] == "Database connection saturation"
    ]

    assert database_hypotheses
    assert (
        database_hypotheses[0]["verification_status"]
        == "conflicting"
    )
    assert (
        result["root_cause_decision"]["status"]
        == "abstained_conflicting_evidence"
    )
    assert result["root_cause_decision"]["root_cause"] is None