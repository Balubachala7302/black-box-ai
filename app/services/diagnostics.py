
from app.schemas import IncidentRequest


def analyze_incident(incident: IncidentRequest) -> dict:
    """Generate explainable root-cause hypotheses from incident evidence.

    These are heuristic candidates, not confirmed root causes.
    Confidence values are provisional ranking scores, not probabilities.
    """

    hypotheses = []
    logs = [log.lower() for log in incident.logs]

    # 1. Database connection saturation
    database_patterns = (
        "database connection timeout",
        "connection pool limit",
        "too many connections",
        "database connection exhausted",
    )

    database_evidence = [
        original
        for original, normalized in zip(incident.logs, logs)
        if any(pattern in normalized for pattern in database_patterns)
    ]

    if database_evidence:
        hypotheses.append(
            {
                "cause": "Database connection saturation",
                "confidence": 0.85,
                "evidence": database_evidence,
                "supporting_evidence": database_evidence,
                "verification_status": "unverified",
                "missing_evidence": [
                    "Current database connection count",
                    "Database maximum connection limit",
                    "Connection-pool wait and timeout metrics",
                ],
                "recommended_check": (
                    "Inspect database connection-pool usage, active "
                    "connections, and connection timeouts."
                ),
            }
        )

    # 2. Upstream dependency failure
    upstream_patterns = (
        "upstream timeout",
        "dependency timeout",
        "service unavailable from dependency",
        "upstream service unavailable",
        "timeout calling payment provider",
        "connection refused by upstream",
    )

    upstream_evidence = [
        original
        for original, normalized in zip(incident.logs, logs)
        if any(pattern in normalized for pattern in upstream_patterns)
    ]

    if upstream_evidence:
        hypotheses.append(
            {
                "cause": "Upstream dependency failure",
                "confidence": 0.82,
                "evidence": upstream_evidence,
                "supporting_evidence": upstream_evidence,
                "verification_status": "unverified",
                "missing_evidence": [
                    "Upstream dependency health and availability",
                    "Dependency request latency and error rate",
                    "Distributed traces showing the failing dependency",
                    "Network and timeout metrics",
                ],
                "recommended_check": (
                    "Check the dependency's health, request latency, "
                    "error rate, and distributed traces."
                ),
            }
        )

    # 3. Deployment-related regression
    # A recent deployment and elevated errors are correlation, not proof.
    if incident.recent_deployment and incident.error_rate >= 5:
        deployment_evidence = [
            "A recent deployment was reported.",
            f"Current error rate is {incident.error_rate}%.",
        ]

        hypotheses.append(
            {
                "cause": "Deployment-related regression",
                "confidence": 0.55,
                "evidence": deployment_evidence,
                "supporting_evidence": [],
                "verification_status": "unverified",
                "missing_evidence": [
                    "Error rate before and after deployment",
                    "Deployment timestamp and release changes",
                    "Evidence linking the changed code or configuration "
                    "to the observed failures",
                    "Comparison with a baseline or unaffected service",
                ],
                "recommended_check": (
                    "Compare incident timing and error rates with the "
                    "deployment timeline, release changes, and an "
                    "unaffected baseline before attributing causation."
                ),
            }
        )

    # 4. Elevated application latency
    # This detects a symptom; it does not identify its underlying cause.
    if incident.latency_ms >= 1000:
        latency_evidence = [
            f"Reported latency is {incident.latency_ms} ms."
        ]

        hypotheses.append(
            {
                "cause": "Elevated application latency",
                "confidence": 0.60,
                "evidence": latency_evidence,
                "supporting_evidence": [],
                "verification_status": "unverified",
                "missing_evidence": [
                    "Historical latency baseline",
                    "Endpoint-level latency measurements",
                    "Dependency response times",
                    "CPU, memory, and connection-pool utilization",
                ],
                "recommended_check": (
                    "Compare latency against its historical baseline, "
                    "then inspect endpoint timings, dependencies, "
                    "and resource utilization."
                ),
            }
        )

    # Rank candidates by provisional score.
    hypotheses.sort(
        key=lambda hypothesis: hypothesis["confidence"],
        reverse=True,
    )

    return {
        "hypotheses": hypotheses,
        "hypothesis_count": len(hypotheses),
        "investigation_status": (
            "hypotheses_generated"
            if hypotheses
            else "insufficient_evidence"
        ),
        "note": (
            "These hypotheses are generated by fixed heuristic rules. "
            "Scores are provisional ranking values, not calibrated "
            "probabilities. A detected symptom or temporal correlation "
            "does not establish a root cause. Collect and verify further "
            "evidence before deciding on remediation."
        ),
    }
