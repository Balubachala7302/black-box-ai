
import json
from types import SimpleNamespace

import pytest

from app.schemas import IncidentRequest
from app.services import nemotron_agent


@pytest.fixture
def incident():
    return IncidentRequest(
        title="Payment Provider Timeout",
        description=(
            "Requests are failing because the payment provider "
            "is timing out."
        ),
        logs=[
            "ERROR: Upstream service timeout",
            "WARNING: Payment provider connection refused",
            "INFO: Database connections are healthy",
        ],
        error_rate=12,
        latency_ms=1500,
        recent_deployment=False,
    )


class FakeMessage:
    def __init__(self, tool_calls=None, content=None):
        self.tool_calls = tool_calls
        self.content = content

    def model_dump(self, exclude_none=True):
        result = {
            "role": "assistant",
            "content": self.content,
        }

        if self.tool_calls:
            result["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in self.tool_calls
            ]

        return result


def make_tool_response(name, call_id="call_1"):
    call = SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(
            name=name,
            arguments="{}",
        ),
    )

    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=FakeMessage(tool_calls=[call])
            )
        ]
    )


def make_final_response(content="Investigation completed."):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=FakeMessage(
                    tool_calls=None,
                    content=content,
                )
            )
        ]
    )


class FakeCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append({
            **kwargs,
            "messages": list(kwargs["messages"]),
        })

        if not self.responses:
            raise AssertionError("Unexpected model API call.")

        return self.responses.pop(0)


class FakeClient:
    def __init__(self, responses):
        self.chat = SimpleNamespace(
            completions=FakeCompletions(responses)
        )


def install_fake_executor(monkeypatch, results, calls):
    def fake_execute_tool(name, arguments, incident):
        calls.append({
            "tool": name,
            "arguments": arguments,
        })

        return results.get(
            name,
            {"error": "Unexpected tool"},
        )

    monkeypatch.setattr(
        nemotron_agent,
        "execute_tool",
        fake_execute_tool,
    )


def install_fake_client(monkeypatch, responses):
    fake_client = FakeClient(responses)

    monkeypatch.setattr(
        nemotron_agent,
        "client",
        fake_client,
    )

    return fake_client


# --------------------------------------------------
# Test 1: Sequential tool execution and cache reuse
# --------------------------------------------------

def test_agent_uses_multiple_tools_sequentially(
    monkeypatch,
    incident,
):
    calls = []

    install_fake_executor(
        monkeypatch,
        {
            "inspect_logs": {
                "findings": ["payment provider timeout"]
            },
            "inspect_metrics": {
                "error_rate": 12,
                "latency_ms": 1500,
            },
        },
        calls,
    )

    install_fake_client(
        monkeypatch,
        [
            make_tool_response("inspect_logs"),
            make_tool_response("inspect_metrics", "call_2"),
            make_final_response("Final investigation report."),
        ],
    )

    result = nemotron_agent.investigate_with_nemotron(incident)

    # The actual diagnostic functions execute only during preflight.
    assert [item["tool"] for item in calls] == [
        "inspect_logs",
        "inspect_metrics",
    ]

    # Nemotron's repeated requests reuse cached results.
    assert result["tool_calls_used"] == 4
    assert len(result["investigation_trace"]) == 4
    assert result["status"] == "completed"

    assert [
        item["source"] for item in result["investigation_trace"]
    ] == [
        "preflight",
        "preflight",
        "nemotron",
        "nemotron",
    ]

    assert [
        item["duplicate"] for item in result["investigation_trace"]
    ] == [
        False,
        False,
        True,
        True,
    ]


# --------------------------------------------------
# Test 2: Previous tool results reach the model
# --------------------------------------------------

def test_previous_tool_results_are_sent_to_model(
    monkeypatch,
    incident,
):
    calls = []

    install_fake_executor(
        monkeypatch,
        {
            "inspect_logs": {
                "finding": "payment provider connection refused"
            },
            "inspect_metrics": {
                "error_rate": 12,
                "latency_ms": 1500,
            },
        },
        calls,
    )

    fake_client = install_fake_client(
        monkeypatch,
        [
            make_tool_response("inspect_logs"),
            make_final_response("Upstream provider is suspected."),
            make_final_response("Final investigation report."),
        ],
    )

    nemotron_agent.investigate_with_nemotron(incident)

    second_request = fake_client.chat.completions.requests[1]

    tool_messages = [
        message
        for message in second_request["messages"]
        if isinstance(message, dict)
        and message.get("role") == "tool"
    ]

    assert len(tool_messages) == 1

    evidence = json.loads(tool_messages[0]["content"])

    assert evidence["finding"] == (
        "payment provider connection refused"
    )


# --------------------------------------------------
# Test 3: Contradictory evidence reaches the model
# --------------------------------------------------

def test_contradictory_evidence_is_forwarded_to_model(
    monkeypatch,
    incident,
):
    contradiction = {
        "supporting_signal": "database connection timeout",
        "contradictory_signal": "database connections are healthy",
    }

    calls = []

    install_fake_executor(
        monkeypatch,
        {
            "inspect_logs": contradiction,
            "inspect_metrics": {
                "error_rate": 12,
                "latency_ms": 1500,
            },
        },
        calls,
    )

    fake_client = install_fake_client(
        monkeypatch,
        [
            make_tool_response("inspect_logs"),
            make_final_response(
                "Database root cause remains inconclusive."
            ),
            make_final_response("Final investigation report."),
        ],
    )

    nemotron_agent.investigate_with_nemotron(incident)

    second_request = fake_client.chat.completions.requests[1]

    tool_messages = [
        message
        for message in second_request["messages"]
        if isinstance(message, dict)
        and message.get("role") == "tool"
    ]

    assert len(tool_messages) == 1

    evidence = json.loads(tool_messages[0]["content"])

    assert evidence["supporting_signal"]
    assert evidence["contradictory_signal"]


# --------------------------------------------------
# Test 4: Early stopping after preflight
# --------------------------------------------------

def test_agent_stops_when_model_returns_final_answer(
    monkeypatch,
    incident,
):
    calls = []

    install_fake_executor(
        monkeypatch,
        {
            "inspect_logs": {"finding": "log evidence"},
            "inspect_metrics": {"finding": "metric evidence"},
        },
        calls,
    )

    fake_client = install_fake_client(
        monkeypatch,
        [
            make_final_response(
                "Evidence is insufficient for a conclusion."
            ),
            make_final_response("Final investigation report."),
        ],
    )

    result = nemotron_agent.investigate_with_nemotron(incident)

    # Logs and metrics are inspected before Nemotron responds.
    assert result["tool_calls_used"] == 2

    assert [
        item["tool"] for item in result["investigation_trace"]
    ] == [
        "inspect_logs",
        "inspect_metrics",
    ]

    assert all(
        item["source"] == "preflight"
        for item in result["investigation_trace"]
    )

    assert len(calls) == 2
    assert len(fake_client.chat.completions.requests) == 2


# --------------------------------------------------
# Test 5: Four-call limit
# --------------------------------------------------

def test_agent_respects_four_tool_call_limit(
    monkeypatch,
    incident,
):
    calls = []

    install_fake_executor(
        monkeypatch,
        {
            "inspect_logs": {"finding": "log evidence"},
            "inspect_metrics": {"finding": "metric evidence"},
            "inspect_deployment": {"finding": "deployment evidence"},
        },
        calls,
    )

    install_fake_client(
        monkeypatch,
        [
            make_tool_response("inspect_logs", "call_1"),
            make_tool_response("inspect_metrics", "call_2"),
            make_final_response(
                "Investigation completed within the tool limit."
            ),
        ],
    )

    result = nemotron_agent.investigate_with_nemotron(incident)

    assert result["tool_calls_used"] == 4
    assert len(result["investigation_trace"]) == 4

    # Only the two preflight diagnostic functions actually execute.
    assert len(calls) == 2

    assert result["tool_calls_used"] <= (
        nemotron_agent.MAX_TOOL_CALLS
    )

    assert result["stop_reason"] == "tool_call_limit_reached"
