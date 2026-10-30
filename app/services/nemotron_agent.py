
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
)

load_dotenv()

logger = logging.getLogger(__name__)

MODEL = "nvidia/nemotron-3-super-120b-a12b"
MAX_TOOL_CALLS = 4

api_key = os.getenv("NEBIUS_API_KEY")

client = (
    OpenAI(
        api_key=api_key,
        base_url="https://api.tokenfactory.nebius.com/v1/",
        timeout=120.0,
        max_retries=1,
    )
    if api_key
    else None
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "inspect_logs",
            "description": (
                "Search incident logs for specific error patterns. "
                "Use categories, keywords or a query to investigate "
                "particular evidence. Can be called repeatedly."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Optional text to search for in logs."
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
                        "description": "Categories to investigate."
                    },
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional search keywords."
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
                "Inspect incident metrics. Select the metrics "
                "needed for the current investigation."
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
                "Inspect recent deployment context. A deployment "
                "alone does not prove it caused the incident."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "focus": {
                        "type": "string",
                        "description": (
                            "Specific deployment question to investigate."
                        ),
                    }
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
) -> dict:
    """Execute only approved diagnostic tools."""

    if name == "inspect_logs":
        return inspect_logs(incident, **arguments)

    if name == "inspect_metrics":
        return inspect_metrics(incident, **arguments)

    if name == "inspect_deployment":
        return inspect_deployment(incident, **arguments)

    return {"error": "Tool is not allowed."}


def investigate_with_nemotron(
    incident: IncidentRequest,
) -> dict:

    if client is None:
        raise RuntimeError("NEBIUS_API_KEY is not configured.")

    messages = [
        {
            "role": "system",
            "content": (
                "You are BLACK BOX AI, an evidence-driven software "
                "incident investigation agent.\n\n"

                "Your task is to investigate incidents through "
                "iterative diagnostic tool calls.\n\n"

                "INVESTIGATION PROCESS:\n"
                "1. Examine the supplied incident information.\n"
                "2. Identify suspicious signals and possible causes.\n"
                "3. Select diagnostic tools based on the evidence.\n"
                "4. Supply targeted arguments to investigate specific "
                "categories, metrics and log patterns.\n"
                "5. Examine tool results before deciding what to do next.\n"
                "6. If important evidence is missing, make another "
                "targeted tool call when useful.\n"
                "7. Compare competing explanations and contradictory "
                "evidence.\n"
                "8. Stop when sufficient evidence is collected or "
                "the tool-call limit is reached.\n\n"

                "IMPORTANT RULES:\n"
                "- Never invent diagnostic tool results.\n"
                "- Distinguish observations from hypotheses.\n"
                "- A recent deployment alone does not establish causation.\n"
                "- Do not claim access to historical logs or external "
                "monitoring systems.\n"
                "- Do not treat missing evidence as proof of absence.\n"
                "- Explain uncertainty and conflicting signals.\n"
                "- Recommend safe, actionable diagnostic steps.\n"
                "- Use only the available diagnostic tools."
            ),
        },
        {
            "role": "user",
            "content": (
                "Investigate this incident. Begin by assessing the "
                "available information and choose the most useful "
                "diagnostic actions.\n\nIncident data:\n"
                + json.dumps(incident.model_dump(), default=str)
            ),
        },
    ]

    trace = []
    tool_calls_used = 0
    stop_reason = "model_completed"

    while tool_calls_used < MAX_TOOL_CALLS:

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=700,
        )

        message = response.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            analysis = message.content or (
                "The model returned no final analysis."
            )

            return {
                "incident_title": incident.title,
                "agent": MODEL,
                "status": "completed",
                "tool_calls_used": tool_calls_used,
                "stop_reason": stop_reason,
                "investigation_trace": trace,
                "analysis": analysis,
            }

        for call in message.tool_calls:

            if tool_calls_used >= MAX_TOOL_CALLS:
                stop_reason = "tool_call_limit_reached"

                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps({
                        "error": "Investigation tool-call limit reached."
                    }),
                })
                continue

            name = call.function.name

            try:
                arguments = json.loads(
                    call.function.arguments or "{}"
                )

                if not isinstance(arguments, dict):
                    raise ValueError("Tool arguments must be an object.")

                result = execute_tool(
                    name,
                    arguments,
                    incident,
                )

            except (ValueError, TypeError, json.JSONDecodeError):
                result = {
                    "error": "Invalid diagnostic tool arguments."
                }

            except Exception:
                logger.exception(
                    "Diagnostic tool execution failed: %s",
                    name,
                )
                result = {
                    "error": "The diagnostic tool failed."
                }

            tool_calls_used += 1

            trace.append({
                "step": tool_calls_used,
                "tool": name,
                "arguments": arguments if "arguments" in locals() else {},
                "result": result,
            })

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result, default=str),
            })

    if tool_calls_used >= MAX_TOOL_CALLS:
        stop_reason = "tool_call_limit_reached"

    messages.append({
        "role": "user",
        "content": (
            "The investigation tool-call limit has been reached. "
            "Provide your final incident assessment using only the "
            "evidence already collected. Explain supporting and "
            "contradictory evidence, uncertainty, likely hypotheses "
            "and safe next diagnostic steps. Do not request more tools."
        ),
    })

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tool_choice="none",
        max_tokens=700,
    )

    analysis = response.choices[0].message.content or (
        "The model returned no final analysis."
    )

    return {
        "incident_title": incident.title,
        "agent": MODEL,
        "status": "completed_with_tool_limit",
        "tool_calls_used": tool_calls_used,
        "stop_reason": stop_reason,
        "investigation_trace": trace,
        "analysis": analysis,
    }
