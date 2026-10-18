
from fastapi.testclient import TestClient

from app.main import app
from app.services import nemotron_agent

client = TestClient(app)


def sample_incident():
    return {
        "title": "API errors increased after deployment",
        "description": (
            "The API error rate increased after a recent release."
        ),
        "logs": ["ERROR: Database connection timeout"],
        "error_rate": 25.0,
        "latency_ms": 1800.0,
        "recent_deployment": True,
    }


def test_baseline_mode_is_the_default():
    response = client.post(
        "/incidents/investigate",
        json=sample_incident(),
    )

    assert response.status_code == 200
    assert "hypotheses" in response.json()


def test_nemotron_mode_calls_the_agent(monkeypatch):
    def fake_investigation(incident):
        return {
            "incident_title": incident.title,
            "agent": "test-model",
            "status": "completed",
            "tool_calls_used": 1,
            "investigation_trace": [],
            "analysis": "Test analysis",
        }

    monkeypatch.setattr(
        nemotron_agent,
        "investigate_with_nemotron",
        fake_investigation,
    )

    response = client.post(
        "/incidents/investigate?mode=nemotron",
        json=sample_incident(),
    )

    assert response.status_code == 200
    assert response.json()["agent"] == "test-model"


def test_nemotron_failure_returns_service_unavailable(monkeypatch):
    def fail_investigation(incident):
        raise RuntimeError("Simulated provider failure")

    monkeypatch.setattr(
        nemotron_agent,
        "investigate_with_nemotron",
        fail_investigation,
    )

    response = client.post(
        "/incidents/investigate?mode=nemotron",
        json=sample_incident(),
    )

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()


def test_invalid_mode_is_rejected():
    response = client.post(
        "/incidents/investigate?mode=unknown",
        json=sample_incident(),
    )

    assert response.status_code == 422
