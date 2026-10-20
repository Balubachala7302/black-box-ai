
from typing import Any


def verify_hypotheses(
    hypotheses: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    """Assess hypotheses using supporting, contradictory, and missing evidence."""

    verified = []

    log_findings = evidence.get("logs", {}).get("findings", [])
    metric_findings = evidence.get("metrics", {}).get("findings", [])
    deployment_data = evidence.get("deployment", {})
    database_telemetry = evidence.get("database", {})

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
        contradictory_evidence = []
        missing_evidence = []
        status = "inconclusive"

        # Hypothesis 1: Database connection saturation
        if "database connection saturation" in cause:
            database_logs = [
                log
                for finding in log_findings
                if finding.get("category")
                == "database_connection_saturation"
                for log in finding.get("matching_logs", [])
            ]

            if "database_connection_saturation" in log_categories:
                status = "supported"
                supporting_evidence.extend(database_logs)

                if not database_logs:
                    supporting_evidence.append(
                        "Diagnostic logs identified database connection saturation."
                    )
            else:
                missing_evidence.append(
                    "Matching database connection errors in application logs"
                )

            active_connections = database_telemetry.get(
                "active_connections"
            )
            max_connections = database_telemetry.get(
                "max_connections"
            )
            pool_waits = database_telemetry.get("pool_waits")

            # Only treat explicit, valid telemetry as contradictory evidence.
            if (
                isinstance(active_connections, (int, float))
                and not isinstance(active_connections, bool)
                and isinstance(max_connections, (int, float))
                and not isinstance(max_connections, bool)
                and max_connections > 0
                and 0 <= active_connections < max_connections * 0.5
                and pool_waits == 0
            ):
                contradictory_evidence.append(
                    "Database telemetry reports low connection usage "
                    "and zero connection-pool waits."
                )

            if contradictory_evidence and supporting_evidence:
                status = "conflicting"
            elif contradictory_evidence:
                status = "contradicted"

            missing_evidence.extend([
                "Database active-connection count",
                "Database maximum connection limit",
                "Connection-pool wait and timeout metrics",
            ])

        # Hypothesis 2: Deployment-related regression
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

            if error_rate is not None:
                supporting_evidence.append(
                    f"Observed error rate: {error_rate.get('value')}%."
                )

            # A deployment and elevated errors alone cannot prove causation.
            status = "inconclusive"

            missing_evidence.extend([
                "Error rate before and after deployment",
                "Deployment timestamp and release changes",
                "Comparison with a baseline or unaffected service",
            ])

        # Hypothesis 3: Elevated application latency
        elif "elevated application latency" in cause:
            latency = observed_metrics.get("latency_ms")

            if latency is None:
                missing_evidence.append(
                    "A measured latency value and its threshold"
                )
            else:
                value = latency.get("value")
                threshold = latency.get("threshold")

                valid_numbers = (
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and isinstance(threshold, (int, float))
                    and not isinstance(threshold, bool)
                )

                if not valid_numbers:
                    missing_evidence.append(
                        "A valid latency value and numeric threshold"
                    )
                elif value >= threshold:
                    supporting_evidence.append(
                        f"Observed latency: {value} ms "
                        f"(threshold: {threshold} ms)."
                    )
                    status = "supported"
                else:
                    contradictory_evidence.append(
                        f"Observed latency: {value} ms is below "
                        f"the configured threshold of {threshold} ms."
                    )
                    status = "contradicted"

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
        hypothesis["contradictory_evidence"] = contradictory_evidence
        hypothesis["missing_evidence"] = missing_evidence

        verified.append(hypothesis)

    return verified
