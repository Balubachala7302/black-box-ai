
from typing import Any, Optional

from app.schemas import IncidentRequest


def inspect_logs(
    incident: IncidentRequest,
    query: Optional[str] = None,
    categories: Optional[list[str]] = None,
    keywords: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Inspect incident logs using targeted, category-specific evidence."""

    raw_logs = [
        log for log in incident.logs
        if isinstance(log, str)
    ]

    ignored_context_patterns = [
        "example message:",
        "runbook explains",
        "is a possible cause to investigate",
        "documentation example",
        "for example:",
        "sample log:",
    ]

    operational_logs = [
        log for log in raw_logs
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
            "upstream service timeout",
            "service unavailable",
            "dependency timeout",
            "timeout calling payment provider",
            "payment provider connection refused",
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

    # Only search valid requested categories.
    if categories:
        selected_categories = [
            category for category in categories
            if category in patterns
        ]
    else:
        selected_categories = list(patterns.keys())

    # Generic keywords and queries are search hints,
    # NOT proof that a particular root cause exists.
    selected_keywords = [
        keyword.lower().strip()
        for keyword in (keywords or [])
        if isinstance(keyword, str) and keyword.strip()
    ]

    search_query = (
        query.lower().strip()
        if isinstance(query, str) and query.strip()
        else None
    )

    findings = []

    for category in selected_categories:
        category_patterns = patterns[category]

        matches = [
            log for log in operational_logs
            if any(
                pattern in log.lower()
                for pattern in category_patterns
            )
        ]

        contradictions = [
            log for log in operational_logs
            if any(
                pattern in log.lower()
                for pattern in contradictory_patterns.get(category, [])
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

    # Return generic search results separately.
    # Never assign them to a root-cause category automatically.
    search_terms = selected_keywords.copy()

    if search_query:
        search_terms.append(search_query)

    query_matches = [
        log for log in operational_logs
        if search_terms
        and any(term in log.lower() for term in search_terms)
    ]

    return {
        "tool": "inspect_logs",
        "query": query,
        "keywords_searched": selected_keywords,
        "categories_searched": selected_categories,
        "logs_examined": len(raw_logs),
        "query_matches": query_matches,
        "findings": findings,
    }



def inspect_metrics(
    incident: IncidentRequest,
    metrics: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Inspect requested incident metrics for threshold breaches."""

    findings = []

    available_metrics = {
        "error_rate": (
            incident.error_rate,
            5,
            "Error rate is elevated.",
        ),
        "latency_ms": (
            incident.latency_ms,
            1000,
            "Response latency is elevated.",
        ),
    }

    requested = set(metrics or available_metrics.keys())

    for metric_name in requested:
        if metric_name not in available_metrics:
            continue

        value, threshold, observation = available_metrics[metric_name]

        if value >= threshold:
            findings.append({
                "metric": metric_name,
                "value": value,
                "threshold": threshold,
                "observation": observation,
            })

    return {
        "tool": "inspect_metrics",
        "metrics_examined": list(
            requested.intersection(available_metrics)
        ),
        "findings": findings,
    }


    requested = set(metrics or available_metrics.keys())

    for metric_name in requested:
        if metric_name not in available_metrics:
            continue

        value, threshold, observation = available_metrics[metric_name]

        if value >= threshold:
            findings.append({
                "metric": metric_name,
                "value": value,
                "threshold": threshold,
                "observation": observation,
            })
        else:
            findings.append({
                "metric": metric_name,
                "value": value,
                "threshold": threshold,
                "observation": "Metric is below the configured alert threshold.",
            })

    return {
        "tool": "inspect_metrics",
        "metrics_examined": list(requested.intersection(available_metrics)),
        "findings": findings,
    }


def inspect_deployment(
    incident: IncidentRequest,
    focus: Optional[str] = None,
) -> dict[str, Any]:
    """Inspect deployment context without assuming causation."""

    if incident.recent_deployment:
        observation = (
            "A recent deployment was reported. "
            "Further evidence is needed to establish causation."
        )
    else:
        observation = "No recent deployment was reported."

    return {
        "tool": "inspect_deployment",
        "focus": focus,
        "recent_deployment": incident.recent_deployment,
        "observation": observation,
    }
