from app.schemas import IncidentRequest


def analyze_incident(incident: IncidentRequest) -> dict:
    """Generate explainable diagnostic hypotheses from incident evidence."""

    hypotheses = []
    logs = "\n".join(incident.logs).lower()

    # Hypothesis 1: Database connection saturation
    if (
        "database connection timeout" in logs
        or "connection pool limit" in logs
    ):
        hypotheses.append(
            {
                "cause": "Database connection saturation",
                "confidence": 0.85,
                "evidence": [
                    log
                    for log in incident.logs
                    if "connection" in log.lower()
                    or "database" in log.lower()
                ],
                "recommended_check": (
                    "Inspect database connection-pool usage, "
                    "active connections, and connection timeouts."
                ),
            }
        )

    # Hypothesis 2: Deployment-related regression
    if incident.recent_deployment and incident.error_rate >= 5:
        hypotheses.append(
            {
                "cause": "Deployment-related regression",
                "confidence": 0.70,
                "evidence": [
                    "A recent deployment was reported.",
                    f"Current error rate is {incident.error_rate}%.",
                ],
                "recommended_check": (
                    "Compare error rates before and after deployment "
                    "and inspect the release changes."
                ),
            }
        )

    # Hypothesis 3: Elevated latency
    if incident.latency_ms >= 1000:
        hypotheses.append(
            {
                "cause": "Elevated application latency",
                "confidence": 0.60,
                "evidence": [
                    f"Reported latency is {incident.latency_ms} ms."
                ],
                "recommended_check": (
                    "Inspect endpoint latency, dependency response times, "
                    "and resource utilization."
                ),
            }
        )

    hypotheses.sort(
        key=lambda hypothesis: hypothesis["confidence"],
        reverse=True,
    )

    return {
        "hypotheses": hypotheses,
        "hypothesis_count": len(hypotheses),
        "investigation_status": (
            "hypotheses_generated" if hypotheses else "insufficient_evidence"
        ),
        "note": (
            "Confidence values are provisional rule-based scores, "
            "not statistically calibrated probabilities. "
            "Hypotheses require further verification."
        ),
    }