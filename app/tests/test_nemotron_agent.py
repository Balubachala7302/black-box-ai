from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.schemas import IncidentRequest
from app.services import nemotron_agent


def create_incident():
    return IncidentRequest(
        title="API errors increased after deployment",
        description="The API is experiencing errors and slow responses.",
        logs=["ERROR: Database connection timeout"],
        error_rate=25.0,
        latency_ms=1800.0,
        recent_deployment=True,
    )


def make_response(content=None, tool_calls=None):
    message = SimpleNamespace(
        content=content,
        tool_calls=tool_calls,
    )

    return SimpleNamespace(
        choices=[
            SimpleNamespace(message=message)
        ]
    )


def test_agent_returns_final_analysis_without_tool_calls(monkeypatch):
    monkeypatch.setattr(
        nemotron_agent,
        "client",
        Mock(),
    )

    nemotron_agent.client.chat.completions.create.return_value = (
        make_response(
            content="Database connection saturation is a possible cause.",
            tool_calls=None,
        )
    )

    result = nemotron_agent.investigate_with_nemotron(
        create_incident()
    )

    assert result["status"] == "completed"
    assert result["tool_calls_used"] == 0
    assert "Database connection saturation" in result["analysis"]


def test_agent_executes_a_requested_diagnostic_tool(monkeypatch):
    monkeypatch.setattr(
        nemotron_agent,
        "client",
        Mock(),
    )

    tool_call = SimpleNamespace(
        id="call_123",
        function=SimpleNamespace(
            name="inspect_logs",
            arguments="{}",
        ),
    )

    nemotron_agent.client.chat.completions.create.side_effect = [
        make_response(
            content=None,
            tool_calls=[tool_call],
        ),
        make_response(
            content="The logs indicate possible database connection saturation.",
            tool_calls=None,
        ),
    ]

    result = nemotron_agent.investigate_with_nemotron(
        create_incident()
    )

    assert result["status"] == "completed"
    assert result["tool_calls_used"] == 1
    assert result["investigation_trace"][0]["tool"] == "inspect_logs"


def test_agent_handles_a_diagnostic_tool_failure(monkeypatch):
    monkeypatch.setattr(
        nemotron_agent,
        "client",
        Mock(),
    )

    tool_call = SimpleNamespace(
        id="call_456",
        function=SimpleNamespace(
            name="inspect_logs",
            arguments="{}",
        ),
    )

    nemotron_agent.client.chat.completions.create.side_effect = [
        make_response(
            content=None,
            tool_calls=[tool_call],
        ),
        make_response(
            content="The diagnostic tool failed; further investigation is needed.",
            tool_calls=None,
        ),
    ]

    monkeypatch.setitem(
        nemotron_agent.TOOL_FUNCTIONS,
        "inspect_logs",
        Mock(side_effect=RuntimeError("Simulated failure")),
    )

    result = nemotron_agent.investigate_with_nemotron(
        create_incident()
    )

    assert result["tool_calls_used"] == 1
    assert "failed" in str(
        result["investigation_trace"][0]["result"]
    ).lower()