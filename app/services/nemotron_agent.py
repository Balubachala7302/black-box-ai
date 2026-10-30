
import json
import logging
import os

from dotenv import load_dotenv
from openai import OpenAI

from app.schemas import IncidentRequest
from app.services.diagnostic_tools import (
    inspect_logs,
    inspect_metrics,
    inspect_deployment,
    inspect_traces,
)

load_dotenv()

logger = logging.getLogger(__name__)

MODEL = "nvidia/nemotron-3-super-120b-a12b"
MAX_TOOL_CALLS = 4

API_KEY = os.getenv("NEBIUS_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "NEBIUS_API_KEY is missing from environment variables."
    )

client = OpenAI(
    base_url="https://api.tokenfactory.nebius.com/v1/",
    api_key=API_KEY,
    timeout=120,
    max_retries=1,
)


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "inspect_logs",
            "description": (
                "Search application logs for evidence related to a suspected "
                "root cause. Use categories and keywords to narrow the search. "
                "You may call this tool multiple times with different targeted "
                "arguments when previous evidence justifies further investigation. "
                "Do not assume a category is confirmed merely because it was searched."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Optional targeted search query.",
                    },
                    "categories": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "database_connection_saturation",
                                "deployment_regression",
                                "upstream_dependency_failure",
                                "memory_pressure",
                            ],
                        },
                        "description": "Specific evidence categories to inspect.",
                    },
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional keywords to search for.",
                    },
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_metrics",
            "description": (
                "Inspect operational metrics such as error rate and latency. "
                "Use this to validate or challenge hypotheses suggested by logs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "metrics": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["error_rate", "latency_ms"],
                        },
                        "description": "Specific metrics to inspect.",
                    }
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_deployment",
            "description": (
                "Inspect deployment events and determine whether a recent "
                "deployment could explain the incident."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "focus": {
                        "type": "string",
                        "description": "Optional deployment investigation focus.",
                    }
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_traces",
            "description": (
                "Inspect normalized OpenTelemetry distributed traces for "
                "failed spans, slow operations, service names, and parent-child "
                "relationships. Use targeted queries and service names to "
                "investigate a suspected failure. A slow span alone does not "
                "prove root cause. Use this tool when trace evidence is available."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Optional search term for trace evidence.",
                    },
                    "service_name": {
                        "type": "string",
                        "description": "Optional service name filter.",
                    },
                    "errors_only": {
                        "type": "boolean",
                        "description": "Return only failed spans when true.",
                    },
                    "min_duration_ms": {
                        "type": "number",
                        "description": "Threshold for identifying slow spans.",
                    },
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
]


def execute_tool(
    name: str,
    arguments: dict,
    incident: IncidentRequest,
):
    """Execute an allowed diagnostic tool with validated arguments."""

    if not isinstance(arguments, dict):
        return {"error": "Tool arguments must be a JSON object."}

    allowed_tools = {
        "inspect_logs": inspect_logs,
        "inspect_metrics": inspect_metrics,
        "inspect_deployment": inspect_deployment,
        "inspect_traces": inspect_traces,
    }

    tool = allowed_tools.get(name)

    if tool is None:
        return {"error": f"Unknown diagnostic tool: {name}"}

    try:
        return tool(incident, **arguments)

    except TypeError as exc:
        logger.warning(
            "Invalid arguments for %s: %s",
            name,
            exc,
        )
        return {
            "error": f"Invalid arguments for {name}: {str(exc)}"
        }

    except Exception:
        logger.exception(
            "Diagnostic tool %s failed",
            name,
        )
        return {
            "error": f"Diagnostic tool {name} failed."
        }


def _serialize_result(result):
    """Convert tool results into JSON-safe data."""

    try:
        return json.loads(json.dumps(result, default=str))

    except (TypeError, ValueError):
        return {"result": str(result)}


def _get_required_diagnostics(incident: IncidentRequest):
    """
    Identify available evidence sources that must be inspected
    before Nemotron starts its reasoning process.
    """

    required = []

    if incident.logs:
        required.append(("inspect_logs", {}))

    if incident.error_rate != 0 or incident.latency_ms != 0:
        required.append(("inspect_metrics", {}))

    if incident.recent_deployment:
        required.append(("inspect_deployment", {}))

    has_traces = any(
        isinstance(item, dict) and item.get("kind") == "trace"
        for item in (incident.normalized_evidence or [])
    )

    if has_traces:
        required.append(("inspect_traces", {}))

    return required


def _run_preflight_diagnostics(
    incident: IncidentRequest,
    investigation_trace: list,
    executed_calls: set,
    tool_result_cache: dict,
):
    """
    Execute evidence-coverage diagnostics before LLM reasoning.

    Preflight and model-requested calls share MAX_TOOL_CALLS.
    """

    tool_calls_used = 0

    required_diagnostics = _get_required_diagnostics(incident)

    for tool_name, arguments in required_diagnostics:

        if tool_calls_used >= MAX_TOOL_CALLS:
            break

        call_signature = json.dumps(
            {
                "tool": tool_name,
                "arguments": arguments,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

        result = _serialize_result(
            execute_tool(
                tool_name,
                arguments,
                incident,
            )
        )

        executed_calls.add(call_signature)
        tool_result_cache[call_signature] = result

        tool_calls_used += 1

        investigation_trace.append(
            {
                "step": tool_calls_used,
                "tool": tool_name,
                "arguments": arguments,
                "duplicate": False,
                "source": "preflight",
                "result": result,
            }
        )

    return tool_calls_used


def investigate_with_nemotron(incident: IncidentRequest):
    """Run an evidence-driven investigation using Nemotron."""

    messages = [
        {
            "role": "system",
            "content": """
You are BLACK BOX AI, an evidence-driven incident investigation agent.

Your objective is to investigate software incidents using diagnostic tools.

INVESTIGATION RULES:

1. Start by identifying the most plausible areas to investigate.
2. Select diagnostic tools based on the incident description and available evidence.
3. Use targeted categories, metrics, and keywords instead of repeatedly searching everything.
4. Carefully inspect every tool result before deciding what to do next.
5. Every follow-up tool call MUST be informed by previous tool results.
6. If logs suggest a failure, use metrics or deployment evidence to validate it.
7. If evidence contradicts a hypothesis, reduce confidence in that hypothesis.
8. Never claim that a searched category is a confirmed root cause.
9. Do not invent evidence, metrics, deployment events, or tool results.
10. If evidence is insufficient or contradictory, explicitly state that the root cause is inconclusive.
11. Avoid redundant tool calls.
12. You MAY call the same tool multiple times when arguments differ
    and previous results justify a targeted follow-up.
13. Each follow-up must investigate a specific unresolved question.
14. Stop investigating when sufficient evidence is available.

PREFLIGHT EVIDENCE:

Some diagnostic tools may already have been executed before you receive
the investigation request.

Their results will be provided in a separate message.

Treat these results as observed diagnostic evidence.
Do not repeat the same diagnostic call without a specific reason.
Use the preflight results to decide whether additional targeted investigation
is necessary.

You have a maximum of four diagnostic tool calls in total.
This includes preflight calls and any additional tool calls you request.

Only use remaining tool-call capacity for additional investigation.

OPENTELEMETRY TRACE INVESTIGATION:

15. When normalized OpenTelemetry traces are available, inspect their
    preflight results before forming a final hypothesis.
16. Use service names and trace identifiers to investigate relevant spans.
17. Examine failed spans and slow spans separately.
18. Use parent-span relationships to understand service dependencies
    when the available evidence supports that relationship.
19. Do not infer causation from latency alone.
20. Do not claim traces were inspected if no trace data was available
    or the trace inspection result reports an error.

FINAL REPORT FORMAT:

- Incident summary
- Most likely root cause
- Supporting evidence
- Contradictory or missing evidence
- Confidence: Low, Medium, or High
- Recommended diagnostic actions

Distinguish observed facts from hypotheses.
Do not present heuristic confidence as a statistical probability.
""",
        },
        {
            "role": "user",
            "content": (
                "Investigate this incident using the available diagnostic tools.\n\n"
                f"Incident details:\n{incident.model_dump_json(indent=2)}"
            ),
        },
    ]

    investigation_trace = []
    tool_calls_used = 0
    stop_reason = "model_finished"

    executed_calls = set()
    tool_result_cache = {}

    try:
        # STEP 1: Execute mandatory evidence-coverage diagnostics.
        tool_calls_used = _run_preflight_diagnostics(
            incident=incident,
            investigation_trace=investigation_trace,
            executed_calls=executed_calls,
            tool_result_cache=tool_result_cache,
        )

        # STEP 2: Give Nemotron the collected evidence.
        if investigation_trace:

            preflight_results = [
                {
                    "tool": item["tool"],
                    "arguments": item["arguments"],
                    "result": item["result"],
                }
                for item in investigation_trace
                if item.get("source") == "preflight"
            ]

            messages.append(
                {
                    "role": "user",
                    "content": (
                        "The following mandatory preflight diagnostics have "
                        "already been executed by the investigation system.\n\n"
                        "Review these results before deciding whether any "
                        "additional targeted tool calls are necessary.\n\n"
                        f"{json.dumps(preflight_results, indent=2, default=str)}"
                    ),
                }
            )

        # STEP 3: Nemotron performs targeted follow-up investigation.
        while tool_calls_used < MAX_TOOL_CALLS:

            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.1,
                max_tokens=700,
            )

            message = response.choices[0].message

            if not message.tool_calls:
                stop_reason = "model_finished"
                break

            messages.append(
                message.model_dump(exclude_none=True)
            )

            for call in message.tool_calls:

                if tool_calls_used >= MAX_TOOL_CALLS:
                    stop_reason = "tool_call_limit_reached"
                    break

                tool_name = call.function.name
                arguments = {}

                try:
                    parsed_arguments = json.loads(
                        call.function.arguments or "{}"
                    )

                    if not isinstance(parsed_arguments, dict):
                        raise ValueError(
                            "Arguments must be a JSON object."
                        )

                    arguments = parsed_arguments

                    call_signature = json.dumps(
                        {
                            "tool": tool_name,
                            "arguments": arguments,
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    )

                    duplicate = call_signature in executed_calls

                    if duplicate:
                        logger.info(
                            "Reusing cached diagnostic result for %s",
                            call_signature,
                        )

                        result = tool_result_cache[call_signature]

                    else:
                        executed_calls.add(call_signature)

                        result = execute_tool(
                            tool_name,
                            arguments,
                            incident,
                        )

                        result = _serialize_result(result)
                        tool_result_cache[call_signature] = result

                except (json.JSONDecodeError, ValueError) as exc:
                    logger.warning(
                        "Invalid arguments from Nemotron for %s: %s",
                        tool_name,
                        exc,
                    )

                    duplicate = False

                    result = {
                        "error": f"Invalid tool arguments: {str(exc)}"
                    }

                except Exception:
                    logger.exception(
                        "Unexpected error executing tool %s",
                        tool_name,
                    )

                    duplicate = False

                    result = {
                        "error": "Unexpected diagnostic tool error."
                    }

                result = _serialize_result(result)

                tool_calls_used += 1

                investigation_trace.append(
                    {
                        "step": tool_calls_used,
                        "tool": tool_name,
                        "arguments": arguments,
                        "duplicate": duplicate,
                        "source": "nemotron",
                        "result": result,
                    }
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(
                            result,
                            default=str,
                        ),
                    }
                )

            if tool_calls_used >= MAX_TOOL_CALLS:
                stop_reason = "tool_call_limit_reached"
                break

        else:
            stop_reason = "tool_call_limit_reached"

        # STEP 4: Generate the final investigation report.
        messages.append(
            {
                "role": "user",
                "content": (
                    "Complete your investigation now. Review the incident "
                    "details and all preflight and follow-up diagnostic results. "
                    "Do not request any additional tools. Clearly distinguish "
                    "observed evidence from hypotheses and mention contradictions "
                    "or missing evidence."
                ),
            }
        )

        final_response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tool_choice="none",
            temperature=0.1,
            max_tokens=900,
        )

        final_analysis = (
            final_response.choices[0].message.content
            or "Unable to generate the final investigation report."
        )

        return {
            "agent": MODEL,
            "status": "completed",
            "tool_calls_used": tool_calls_used,
            "max_tool_calls": MAX_TOOL_CALLS,
            "stop_reason": stop_reason,
            "investigation_trace": investigation_trace,
            "analysis": final_analysis,
        }

    except Exception as exc:
        logger.exception("Nemotron investigation failed")

        return {
            "agent": MODEL,
            "status": "error",
            "tool_calls_used": tool_calls_used,
            "max_tool_calls": MAX_TOOL_CALLS,
            "stop_reason": "investigation_error",
            "investigation_trace": investigation_trace,
            "analysis": f"Nemotron investigation failed: {str(exc)}",
        }
