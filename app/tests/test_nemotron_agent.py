
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from app.schemas import IncidentRequest
from app.services.diagnostic_tools import (
    inspect_logs,
    inspect_metrics,
    inspect_deployment,
)
from app.services.diagnostics import analyze_incident
from app.services.verification import verify_hypotheses

load_dotenv()

MODEL = "nvidia/nemotron-3-super-120b-a12b"
MAX_TOOL_CALLS = 4

api_key = os.getenv("NEBIUS_API_KEY")

client = (
    OpenAI(
        api_key=api_key,
        base_url="https://api.tokenfactory.nebius.com/v1/",
        timeout=30.0,
        max_retries=0,
    )
    if api_key
    else None
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "inspect_logs",
            "description": "Search incident logs for known error patterns.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_metrics",
            "description": "Check the incident error rate and latency.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_deployment",
            "description": "Check whether a recent deployment may be relevant.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

TOOL_FUNCTIONS = {
    "inspect_logs": inspect_logs,
    "inspect_metrics": inspect_metrics,
    "inspect_deployment": inspect_deployment,
}


def _build_verified_evidence(incident: IncidentRequest) -> dict:
    """Collect deterministic evidence and verify rule-based hypotheses."""

    log_evidence = inspect_logs(incident)
    metric_evidence = inspect_metrics(incident)
    deployment_evidence = inspect_deployment(incident)

    evidence = {
        "logs": log_evidence,
        "metrics": metric_evidence,
        "deployment": deployment_evidence,
    }

    diagnosis = analyze_incident(incident)
    hypotheses = verify_hypotheses(
        diagnosis["hypotheses"],
        evidence,
    )

    return {
        "evidence": evidence,
        "hypotheses": hypotheses,
        "hypothesis_count": len(hypotheses),
        "investigation_status": diagnosis["investigation_status"],
    }


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
                "incident investigator. Choose diagnostic tools based "
                "on the evidence available. Never invent tool results. "
                "Distinguish observations from hypotheses. A recent "
                "deployment does not by itself prove causation. Explain "
                "uncertainty and recommend safe next diagnostic steps."
            ),
        },
        {
            "role": "user",
            "content": (
                "Investigate this incident using the available tools. "
                "Incident data:\n"
                + json.dumps(incident.model_dump(), default=str)
            ),
        },
    ]

    trace = []
    tool_calls_used = 0
    executed_tools = set()

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
            verified = _build_verified_evidence(incident)

            return {
                "incident_title": incident.title,
                "agent": MODEL,
                "status": "completed",
                "tool_calls_used": tool_calls_used,
                "investigation_trace": trace,
                "evidence": verified["evidence"],
                "hypotheses": verified["hypotheses"],
                "hypothesis_count": verified["hypothesis_count"],
                "investigation_status": verified["investigation_status"],
                "analysis": message.content or (
                    "The model returned no final analysis."
                ),
                "limitations": [
                    "Diagnostic tools currently use rule-based checks.",
                    "Verification indicates evidence support, not a confirmed root cause.",
                    "Database telemetry and historical deployment comparisons are not integrated.",
                    "The rule-based evidence summary is computed independently of the model's narrative.",
                ],
            }

        for call in message.tool_calls:
            if tool_calls_used >= MAX_TOOL_CALLS:
                break

            name = call.function.name

            if name not in TOOL_FUNCTIONS:
                result = {"error": "Tool is not allowed."}
            elif name in executed_tools:
                result = {
                    "error": (
                        "This diagnostic tool has already been executed "
                        "for this incident. Use the collected evidence."
                    )
                }
            else:
                try:
                    result = TOOL_FUNCTIONS[name](incident)
                    executed_tools.add(name)
                except Exception:
                    result = {
                        "error": "The diagnostic tool failed."
                    }

            tool_calls_used += 1

            trace.append({
                "step": tool_calls_used,
                "tool": name,
                "result": result,
            })

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result, default=str),
            })

    messages.append({
        "role": "user",
        "content": (
            "The diagnostic tool-call limit has been reached. "
            "Summarize only the evidence collected, state uncertainty, "
            "and recommend the next safe diagnostic step. Do not "
            "request more tools."
        ),
    })

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=700,
    )

    verified = _build_verified_evidence(incident)

    return {
        "incident_title": incident.title,
        "agent": MODEL,
        "status": "completed_with_tool_limit",
        "tool_calls_used": tool_calls_used,
        "investigation_trace": trace,
        "evidence": verified["evidence"],
        "hypotheses": verified["hypotheses"],
        "hypothesis_count": verified["hypothesis_count"],
        "investigation_status": verified["investigation_status"],
        "analysis": response.choices[0].message.content or (
            "The model returned no final analysis."
        ),
        "limitations": [
            "Diagnostic tools currently use rule-based checks.",
            "Verification indicates evidence support, not a confirmed root cause.",
            "Database telemetry and historical deployment comparisons are not integrated.",
            "The rule-based evidence summary is computed independently of the model's narrative.",
        ],
    }
