from typing import Any

from app.schemas import IncidentRequest


def inspect_logs(incident: IncidentRequest) -> dict[str, Any]:
    """Inspect incident logs for known error patterns."""

    logs = [log.lower() for log in incident.logs]

    patterns = {
        "database_connection_saturation": [
            "database connection timeout",
            "connection pool limit",
            "too many connections",
        ],
        "deployment_regression": [
            "deployment failed",
            "new release",
            "after deployment",
        ],
        "upstream_dependency_failure": [
            "upstream timeout",
            "service unavailable",
            "dependency timeout",
        ],
        "memory_pressure": [
            "out of memory",
            "memory limit exceeded",
            "oomkilled",
        ],
    }

    findings = []

    for category, keywords in patterns.items():
        matches = [
            log
            for log in logs
            if any(keyword in log for keyword in keywords)
        ]

        if matches:
            findings.append(
                {
                    "category": category,
                    "matching_logs": matches,
                    "match_count": len(matches),
                }
            )

    return {
        "tool": "inspect_logs",
        "logs_examined": len(logs),
        "findings": findings,
    }


def inspect_metrics(incident: IncidentRequest) -> dict[str, Any]:
    """Inspect incident metrics for unusual values."""

    findings = []

    if incident.error_rate >= 5:
        findings.append(
            {
                "metric": "error_rate",
                "value": incident.error_rate,
                "threshold": 5,
                "observation": "Error rate is elevated.",
            }
        )

    if incident.latency_ms >= 1000:
        findings.append(
            {
                "metric": "latency_ms",
                "value": incident.latency_ms,
                "threshold": 1000,
                "observation": "Response latency is elevated.",
            }
        )

    return {
        "tool": "inspect_metrics",
        "findings": findings,
    }


def inspect_deployment(incident: IncidentRequest) -> dict[str, Any]:
    """Inspect whether a recent deployment may be relevant."""

    if incident.recent_deployment:
        observation = (
            "A recent deployment was reported. "
            "Further evidence is needed to establish causation."
        )
    else:
        observation = "No recent deployment was reported."

    return {
        "tool": "inspect_deployment",
        "recent_deployment": incident.recent_deployment,
        "observation": observation,
    }