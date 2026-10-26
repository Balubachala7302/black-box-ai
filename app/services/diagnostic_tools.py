from typing import Any

from app.schemas import IncidentRequest


def inspect_logs(incident: IncidentRequest) -> dict[str, Any]:
    """Inspect incident logs for supporting and contradictory signals."""

    raw_logs = [
        log for log in incident.logs
        if isinstance(log, str)
    ]

    # Exclude documentation and illustrative examples from operational
    # evidence so that quoted keywords do not automatically trigger findings.
    ignored_context_patterns = [
        "example message:",
        "runbook explains",
        "is a possible cause to investigate",
        "documentation example",
        "for example:",
        "sample log:",
    ]

    operational_logs = [
        log.lower()
        for log in raw_logs
        if not any(
            marker in log.lower()
            for marker in ignored_context_patterns
        )
    ]

    patterns = {
        "database_connection_saturation": [
            "database connection timeout",
            "connection pool limit",
            "too many connections",
            "database connection exhausted",
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
            "timeout calling payment provider",
            "connection refused by upstream",
        ],
        "memory_pressure": [
            "out of memory",
            "memory limit exceeded",
            "oomkilled",
        ],
    }

    contradictory_patterns = {
        "database_connection_saturation": [
            "database active connections are within normal range",
            "database connections are healthy",
            "connection pool utilization is normal",
            "database connection pool is healthy",
            "database connection saturation ruled out",
        ],
    }

    findings = []

    for category, keywords in patterns.items():
        matches = [
            log
            for log in operational_logs
            if any(keyword in log for keyword in keywords)
        ]

        contradictions = [
            log
            for log in operational_logs
            if any(
                keyword in log
                for keyword in contradictory_patterns.get(category, [])
            )
        ]

        if matches or contradictions:
            findings.append({
                "category": category,
                "matching_logs": matches,
                "match_count": len(matches),
                "contradictory_logs": contradictions,
                "contradictory_count": len(contradictions),
                "evidence_status": (
                    "conflicting"
                    if matches and contradictions
                    else "supporting"
                    if matches
                    else "contradictory"
                ),
            })

    return {
        "tool": "inspect_logs",
        "logs_examined": len(raw_logs),
        "raw_logs": raw_logs,
        "findings": findings,
    }


def inspect_metrics(incident: IncidentRequest) -> dict[str, Any]:
    """Inspect incident metrics for unusual values."""

    findings = []

    if incident.error_rate >= 5:
        findings.append({
            "metric": "error_rate",
            "value": incident.error_rate,
            "threshold": 5,
            "observation": "Error rate is elevated.",
        })

    if incident.latency_ms >= 1000:
        findings.append({
            "metric": "latency_ms",
            "value": incident.latency_ms,
            "threshold": 1000,
            "observation": "Response latency is elevated.",
        })

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