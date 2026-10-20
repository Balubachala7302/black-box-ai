from typing import Any

from app.schemas import IncidentRequest
from app.services.diagnostic_tools import (
    inspect_logs,
    inspect_metrics,
    inspect_deployment,
)
from app.services.diagnostics import analyze_incident
from app.services.verification import verify_hypotheses


def investigate(incident: IncidentRequest) -> dict[str, Any]:
    """
    Run a structured incident investigation using diagnostic tools.
    """

    # Step 1: Gather evidence from each diagnostic tool.
    log_evidence = inspect_logs(incident)
    metric_evidence = inspect_metrics(incident)
    deployment_evidence = inspect_deployment(incident)

    # Step 2: Record the investigation trace.
    investigation_trace = [
        {
            "step": 1,
            "tool": "inspect_logs",
            "reason": "Search incident logs for known error patterns.",
            "result": log_evidence,
        },
        {
            "step": 2,
            "tool": "inspect_metrics",
            "reason": "Check error rate and latency against thresholds.",
            "result": metric_evidence,
        },
        {
            "step": 3,
            "tool": "inspect_deployment",
            "reason": "Check whether a recent deployment may be relevant.",
            "result": deployment_evidence,
        },
    ]

    # Step 3: Generate candidate root-cause hypotheses.
    diagnosis = analyze_incident(incident)


    # Step 4: Verify hypotheses against collected evidence.
    evidence = {
        "logs": log_evidence,
        "metrics": metric_evidence,
        "deployment": deployment_evidence,
    }

    verified_hypotheses = verify_hypotheses(
        diagnosis["hypotheses"],
        evidence,
    )

    # Step 5: Return findings and verification results.
    return {
        "incident_title": incident.title,
        "investigation_status": diagnosis["investigation_status"],
        "evidence": evidence,
        "hypotheses": verified_hypotheses,
        "hypothesis_count": len(verified_hypotheses),
        "investigation_trace": investigation_trace,
        "limitations": [
            "Diagnostic tools currently use rule-based checks.",
            "Verification statuses indicate evidence support, not confirmed root causes.",
            "Database-side metrics and historical deployment comparisons are not yet integrated.",
            "Thresholds are fixed and are not learned from historical data.",
        ],
    }
