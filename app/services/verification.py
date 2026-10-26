from typing import Any


def verify_hypotheses(
    hypotheses: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    """Assess hypotheses using supporting, contradictory, and missing evidence."""

    verified = []

    logs_data = evidence.get("logs", {})
    log_findings = logs_data.get("findings", [])
    raw_logs = [
        log.lower()
        for log in logs_data.get("raw_logs", [])
        if isinstance(log, str)
    ]

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
            database_findings = [
                finding
                for finding in log_findings
                if finding.get("category")
                == "database_connection_saturation"
            ]

            database_logs = [
                log
                for finding in database_findings
                for log in finding.get("matching_logs", [])
            ]

            healthy_database_logs = [
                log
                for finding in database_findings
                for log in finding.get("contradictory_logs", [])
            ]

            # Log matches are supporting signals, not independent
            # confirmation that connection saturation is the root cause.
            if database_logs:
                supporting_evidence.extend(database_logs)
            elif "database_connection_saturation" in log_categories:
                supporting_evidence.append(
                    "Diagnostic logs identified database connection saturation."
                )
            else:
                missing_evidence.append(
                    "Matching database connection errors in application logs"
                )

            missing_evidence.append(
                "Independent database telemetry confirming connection saturation"
            )

            if healthy_database_logs:
                contradictory_evidence.extend(healthy_database_logs)

            active_connections = database_telemetry.get("active_connections")
            max_connections = database_telemetry.get("max_connections")
            pool_waits = database_telemetry.get("pool_waits")

            valid_connection_counts = (
                isinstance(active_connections, (int, float))
                and not isinstance(active_connections, bool)
                and isinstance(max_connections, (int, float))
                and not isinstance(max_connections, bool)
                and max_connections > 0
                and active_connections >= 0
            )

            valid_pool_waits = (
                isinstance(pool_waits, (int, float))
                and not isinstance(pool_waits, bool)
                and pool_waits >= 0
            )

            if (
                valid_connection_counts
                and valid_pool_waits
                and active_connections < max_connections * 0.5
                and pool_waits == 0
            ):
                contradictory_evidence.append(
                    "Database telemetry reports low connection usage "
                    "and zero connection-pool waits."
                )

            if supporting_evidence and contradictory_evidence:
                status = "conflicting"
            elif contradictory_evidence:
                status = "contradicted"
            elif supporting_evidence:
                status = "supported"

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

            release_specific = any(
                "release-specific" in log
                or "introduced in release" in log
                or (
                    "release " in log
                    and "http 500" in log
                )
                for log in raw_logs
            )

            before_after_evidence = (
                any(
                    "error rate before deployment" in log
                    for log in raw_logs
                )
                and any(
                    "error rate after deployment" in log
                    for log in raw_logs
                )
            )

            control_service_evidence = any(
                "unaffected control service" in log
                or "control service error rate" in log
                for log in raw_logs
            )

            if recent_deployment:
                supporting_evidence.append(
                    "A recent deployment was reported."
                )
            else:
                missing_evidence.append(
                    "Evidence that a deployment occurred near the incident"
                )

            if release_specific:
                supporting_evidence.append(
                    "Logs contain a release-specific error signal."
                )
            else:
                missing_evidence.append(
                    "Release-specific error evidence"
                )

            if before_after_evidence:
                supporting_evidence.append(
                    "Logs report error rates before and after deployment."
                )
            else:
                missing_evidence.append(
                    "Error-rate measurements before and after deployment"
                )

            if control_service_evidence:
                supporting_evidence.append(
                    "Logs report an unaffected control service."
                )
            else:
                missing_evidence.append(
                    "Comparison with an unaffected control service"
                )

            if (
                recent_deployment
                and release_specific
                and before_after_evidence
                and control_service_evidence
            ):
                status = "supported"
            else:
                status = "inconclusive"

            missing_evidence.extend([
                "Independently verified deployment timestamp and release changes",
                "Validated telemetry for before-and-after error rates",
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

        # Hypothesis 4: Upstream dependency failure
        elif "upstream dependency failure" in cause:
            upstream_findings = [
                finding
                for finding in log_findings
                if finding.get("category")
                == "upstream_dependency_failure"
            ]

            upstream_logs = [
                log
                for finding in upstream_findings
                for log in finding.get("matching_logs", [])
            ]

            upstream_contradictions = [
                log
                for finding in upstream_findings
                for log in finding.get("contradictory_logs", [])
            ]

            if upstream_logs:
                supporting_evidence.extend(upstream_logs)
            else:
                missing_evidence.append(
                    "Matching upstream dependency errors in application logs"
                )

            if upstream_contradictions:
                contradictory_evidence.extend(upstream_contradictions)

            if supporting_evidence and contradictory_evidence:
                status = "conflicting"
            elif contradictory_evidence:
                status = "contradicted"
            elif upstream_logs:
                status = "supported"

            missing_evidence.extend([
                "Independent health check of the upstream provider",
                "Request-level traces showing failures at the dependency boundary",
                "Comparison with upstream latency and error-rate baselines",
            ])

        # Hypothesis 5: Other causes without verification rules
        else:
            missing_evidence.append(
                "A verification rule for this hypothesis"
            )

        # Remove duplicate evidence requests while preserving order.
        hypothesis["verification_status"] = status
        hypothesis["supporting_evidence"] = supporting_evidence
        hypothesis["contradictory_evidence"] = contradictory_evidence
        hypothesis["missing_evidence"] = list(dict.fromkeys(missing_evidence))

        verified.append(hypothesis)

    return verified