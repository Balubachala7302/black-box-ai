from app.schemas import IncidentRequest


def analyze_incident(incident: IncidentRequest) -> dict:
    """Generate explainable diagnostic hypotheses from incident evidence."""

    hypotheses = []
    logs = "\n".join(incident.logs).lower()

    # Hypothesis 1: Database connection saturation
    database_patterns = (
        "database connection timeout",
        "connection pool limit",
        "too many connections",
    )

    database_evidence = [
        log
        for log in incident.logs
        if any(pattern in log.lower() for pattern in database_patterns)
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
                    "Inspect database connection-pool usage, "
                    "active connections, and connection timeouts."
                ),
            }
        )

    # Hypothesis 2: Deployment-related regression
    if incident.recent_deployment and incident.error_rate >= 5:
        deployment_evidence = [
            "A recent deployment was reported.",
            f"Current error rate is {incident.error_rate}%.",
        ]

        hypotheses.append(
            {
                "cause": "Deployment-related regression",
                "confidence": 0.70,
                "evidence": deployment_evidence,
                "supporting_evidence": deployment_evidence,
                "verification_status": "unverified",
                "missing_evidence": [
                    "Error rate before deployment",
                    "Error rate after deployment",
                    "Deployment timestamp and release changes",
                ],
                "recommended_check": (
                    "Compare error rates before and after deployment "
                    "and inspect the release changes."
                ),
            }
        )

    # Hypothesis 3: Elevated application latency
    if incident.latency_ms >= 1000:
        latency_evidence = [
            f"Reported latency is {incident.latency_ms} ms."
        ]

        hypotheses.append(
            {
                "cause": "Elevated application latency",
                "confidence": 0.60,
                "evidence": latency_evidence,
                "supporting_evidence": latency_evidence,
                "verification_status": "unverified",
                "missing_evidence": [
                    "Historical latency baseline",
                    "Endpoint-level latency measurements",
                    "Dependency response times and resource utilization",
                ],
                "recommended_check": (
                    "Inspect endpoint latency, dependency response times, "
                    "and resource utilization."
                ),
            }
        )

    # Rank hypotheses by provisional rule-based score
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
            "Confidence values are provisional rule-based scores, "
            "not statistically calibrated probabilities. "
            "All hypotheses remain unverified until additional "
            "evidence is collected."
        ),
    }