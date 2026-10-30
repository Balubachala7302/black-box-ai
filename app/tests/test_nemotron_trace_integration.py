
from types import SimpleNamespace
from unittest.mock import patch

from app.schemas import IncidentRequest
from app.services import nemotron_agent


def create_trace_incident():
    return IncidentRequest(
        title="Checkout database failure",
        description=(
            "Checkout requests are failing because database operations "
            "are experiencing errors and high latency."
        ),
        logs=[
            "ERROR database connection pool exhausted",
            "ERROR checkout request failed: connection timeout",
        ],
        error_rate=12.5,
        latency_ms=2400,
        recent_deployment=True,
        normalized_evidence=[
            {
                "source": "opentelemetry",
                "kind": "trace",
                "name": "database_query",
                "trace_id": "trace-001",
                "span_id": "db-span",
                "parent_span_id": "checkout-span",
                "service_name": "database-service",
                "duration_ms": 2500,
                "status_code": 2,
                "status_message": "Database timeout",
                "failed": True,
                "attributes": {},
                "resource_attributes": {
                    "service.name": "database-service"
                },
            },
            {
                "source": "opentelemetry",
                "kind": "trace",
                "name": "checkout_request",
                "trace_id": "trace-001",
                "span_id": "checkout-span",
                "parent_span_id": None,
                "service_name": "checkout-service",
                "duration_ms": 2800,
                "status_code": 1,
                "status_message": None,
                "failed": False,
                "attributes": {},
                "resource_attributes": {
                    "service.name": "checkout-service"
                },
            },
        ],
    )


def test_inspect_traces_is_registered_as_nemotron_tool():
    tool_names = [
        tool["function"]["name"]
        for tool in nemotron_agent.TOOLS
    ]

    assert "inspect_traces" in tool_names


def test_nemotron_executes_trace_tool_and_receives_evidence():
    incident = create_trace_incident()

    result = nemotron_agent.execute_tool(
        "inspect_traces",
        {"service_name": "database-service"},
        incident,
    )

    assert result["tool"] == "inspect_traces"
    assert result["total_spans_examined"] == 2
    assert result["matching_spans"] == 1
    assert result["failed_span_count"] == 1

    assert result["failed_spans"][0]["span_id"] == "db-span"

    assert (
        result["failed_spans"][0]["parent_span_id"]
        == "checkout-span"
    )


def test_nemotron_agent_uses_trace_results_in_investigation():
    incident = create_trace_incident()

    final_message = SimpleNamespace(
        content=(
            "The database-service database_query span failed "
            "with a 2500 ms duration and a database timeout."
        ),
        tool_calls=None,
    )

    mock_response = SimpleNamespace(
        choices=[
            SimpleNamespace(message=final_message)
        ]
    )

    with patch.object(
        nemotron_agent.client.chat.completions,
        "create",
        return_value=mock_response,
    ) as mock_create:

        result = nemotron_agent.investigate_with_nemotron(
            incident
        )

    assert result["status"] == "completed"
    assert result["tool_calls_used"] == 4
    assert result["max_tool_calls"] == 4
    assert result["stop_reason"] == "tool_call_limit_reached"

    trace_steps = result["investigation_trace"]

    # All available evidence sources are inspected during preflight.
    assert len(trace_steps) == 4

    assert [
        step["tool"] for step in trace_steps
    ] == [
        "inspect_logs",
        "inspect_metrics",
        "inspect_deployment",
        "inspect_traces",
    ]

    assert all(
        step["source"] == "preflight"
        for step in trace_steps
    )

    trace_step = trace_steps[3]

    assert trace_step["tool"] == "inspect_traces"

    assert (
        trace_step["result"]["failed_span_count"] == 1
    )

    assert (
        trace_step["result"]["failed_spans"][0]["span_id"]
        == "db-span"
    )

    assert "database-service" in result["analysis"]
    assert "database timeout" in result["analysis"].lower()

    # Four preflight calls consume the budget, so only final synthesis runs.
    assert mock_create.call_count == 1

    final_call = mock_create.call_args.kwargs

    assert final_call["tool_choice"] == "none"

    # Verify that the actual trace evidence was supplied to Nemotron.
    messages = final_call["messages"]

    preflight_message = next(
        message
        for message in messages
        if (
            message["role"] == "user"
            and "mandatory preflight diagnostics" in message["content"]
        )
    )

    assert "inspect_traces" in preflight_message["content"]
    assert "db-span" in preflight_message["content"]
    assert "Database timeout" in preflight_message["content"]
