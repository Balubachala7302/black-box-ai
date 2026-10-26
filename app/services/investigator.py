from typing import Any

from app.schemas import IncidentRequest
from app.services.diagnostic_tools import (
    inspect_logs,
    inspect_metrics,
    inspect_deployment,
)
from app.services.diagnostics import analyze_incident
from app.services.verification import verify_hypotheses


def identify_evidence_gaps(
    hypotheses: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize missing evidence needed to investigate candidates further."""

    gaps = []

    for hypothesis in hypotheses:
        cause = hypothesis.get("cause", "Unknown hypothesis")
        missing = hypothesis.get("missing_evidence", [])

        if missing:
            gaps.append({
                "cause": cause,
                "missing_evidence": list(dict.fromkeys(missing)),
            })

    return {
        "tool": "identify_evidence_gaps",
        "gaps": gaps,
        "gap_count": sum(len(item["missing_evidence"]) for item in gaps),
        "note": (
            "These are evidence requests, not evidence already collected. "
            "No additional telemetry source is queried by this step."
        ),
    }


def decide_root_cause(
    hypotheses: list[dict[str, Any]],
) -> dict[str, Any]:
    """Select a root-cause candidate conservatively."""

    symptom_only_causes = {
        "elevated application latency",
    }

    conflicting = [
        hypothesis
        for hypothesis in hypotheses
        if hypothesis.get("verification_status") in {
            "conflicting",
            "contradicted",
        }
    ]

    if conflicting:
        return {
            "status": "abstained_conflicting_evidence",
            "root_cause": None,
            "reason": (
                "Evidence contradicts at least one candidate hypothesis."
            ),
        }

    supported_causes = [
        hypothesis
        for hypothesis in hypotheses
        if hypothesis.get("verification_status") == "supported"
        and hypothesis.get("cause", "").lower()
        not in symptom_only_causes
    ]

    if len(supported_causes) == 1:
        selected = supported_causes[0]
        return {
            "status": "candidate_supported",
            "root_cause": selected["cause"],
            "reason": (
                "One candidate has supporting evidence and no recorded "
                "contradiction. This is not definitive proof of causation."
            ),
        }

    if len(supported_causes) > 1:
        return {
            "status": "abstained_multiple_candidates",
            "root_cause": None,
            "reason": (
                "Multiple causes have supporting evidence; "
                "further investigation is needed."
            ),
        }

    return {
        "status": "abstained_insufficient_evidence",
        "root_cause": None,
        "reason": (
            "No underlying cause has sufficient verified support."
        ),
    }


def investigate(incident: IncidentRequest) -> dict[str, Any]:
    """Run a structured, evidence-based incident investigation."""

    # Step 1: Gather evidence from the currently implemented tools.
    log_evidence = inspect_logs(incident)
    metric_evidence = inspect_metrics(incident)
    deployment_evidence = inspect_deployment(incident)

    evidence = {
        "logs": log_evidence,
        "metrics": metric_evidence,
        "deployment": deployment_evidence,
    }

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
            "reason": (
                "Check whether a recent deployment may be relevant."
            ),
            "result": deployment_evidence,
        },
    ]

    # Step 2: Generate and verify candidate hypotheses.
    diagnosis = analyze_incident(incident)

    verified_hypotheses = verify_hypotheses(
        diagnosis["hypotheses"],
        evidence,
    )

    # Step 3: Identify what is still missing before making a decision.
    evidence_gaps = identify_evidence_gaps(verified_hypotheses)

    investigation_trace.append({
        "step": 4,
        "tool": "identify_evidence_gaps",
        "reason": (
            "List missing evidence needed to strengthen or reject "
            "each candidate hypothesis."
        ),
        "result": evidence_gaps,
    })

    # Step 4: Make a conservative decision using verified evidence.
    root_cause_decision = decide_root_cause(verified_hypotheses)

    investigation_trace.append({
        "step": 5,
        "tool": "decide_root_cause",
        "reason": (
            "Evaluate verification statuses and abstain when evidence "
            "is conflicting or insufficient."
        ),
        "result": root_cause_decision,
    })

    return {
        "incident_title": incident.title,
        "investigation_status": diagnosis["investigation_status"],
        "evidence": evidence,
        "hypotheses": verified_hypotheses,
        "hypothesis_count": len(verified_hypotheses),
        "root_cause_decision": root_cause_decision,
        "investigation_trace": investigation_trace,
        "evidence_gaps": evidence_gaps,
        "limitations": [
            "Diagnostic tools currently use rule-based checks.",
            "Evidence-gap identification does not itself collect new evidence.",
            "Supporting evidence does not prove definitive causation.",
            "Database-side metrics and historical deployment comparisons "
            "are not yet integrated.",
            "Thresholds are fixed and are not learned from historical data.",
            "Contradictory evidence can only be evaluated when diagnostic "
            "tools expose it in a structured form.",
        ],
    }