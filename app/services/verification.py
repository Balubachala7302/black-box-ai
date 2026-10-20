
from typing import Any


def verify_hypotheses(
    hypotheses: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    """Assess hypotheses against collected evidence without claiming certainty."""

    verified = []

    log_findings = evidence.get("logs", {}).get("findings", [])
    metric_findings = evidence.get("metrics", {}).get("findings", [])
    deployment_data = evidence.get("deployment", {})

    log_categories = {
        finding.get("category")
        for finding in log_findings
    }

    observed_metrics = {
        finding.get("metric"): finding
        for finding in metric_findings
    }

    for original in hypotheses:
        hypothesis = dict(original)
        cause = hypothesis.get("cause", "").lower()

        supporting_evidence = []
        missing_evidence = []
        status = "inconclusive"

        if "database connection saturation" in cause:
            database_logs = [
                log
                for finding in log_findings
                if finding.get("category")
                == "database_connection_saturation"
                for log in finding.get("matching_logs", [])
            ]

            if database_logs:
                supporting_evidence.extend(database_logs)

            if "database_connection_saturation" in log_categories:
                status = "supported"
            else:
                missing_evidence.append(
                    "Matching database connection errors in application logs"
                )

            missing_evidence.extend([
                "Database active-connection count",
                "Database maximum connection limit",
                "Connection-pool wait and timeout metrics",
            ])

        elif "deployment-related regression" in cause:
            recent_deployment = deployment_data.get(
                "recent_deployment", False
            )

            if recent_deployment:
                supporting_evidence.append(
                    "A recent deployment was reported."
                )
            else:
                missing_evidence.append(
                    "Evidence that a deployment occurred near the incident"
                )

            error_rate = observed_metrics.get("error_rate")
            if error_rate:
                supporting_evidence.append(
                    f"Observed error rate: {error_rate.get('value')}%."
                )

            # Temporal correlation alone cannot establish causation.
            status = "inconclusive"

            missing_evidence.extend([
                "Error rate before and after deployment",
                "Deployment timestamp and release changes",
                "Comparison with a baseline or unaffected service",
            ])

        elif "elevated application latency" in cause:
            latency = observed_metrics.get("latency_ms")

            if latency is None:
                missing_evidence.append(
                    "A measured latency value and its threshold"
                )
            else:
                value = latency.get("value")
                threshold = latency.get("threshold")

                if (
                    isinstance(value, (int, float))
                    and isinstance(threshold, (int, float))
                    and value >= threshold
                ):
                    supporting_evidence.append(
                        f"Observed latency: {value} ms "
                        f"(threshold: {threshold} ms)."
                    )
                    status = "supported"
                else:
                    missing_evidence.append(
                        "Evidence that latency exceeds the configured threshold"
                    )

            missing_evidence.extend([
                "Historical latency baseline",
                "Endpoint and dependency latency measurements",
            ])

        else:
            missing_evidence.append(
                "A verification rule for this hypothesis"
            )

        hypothesis["verification_status"] = status
        hypothesis["supporting_evidence"] = supporting_evidence
        hypothesis["missing_evidence"] = missing_evidence
        verified.append(hypothesis)

    return verified
