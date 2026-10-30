
from typing import Any

from app.schemas import IncidentRequest


def _attributes_to_dict(attributes: list[dict]) -> dict:
    """Convert OTLP key/value attributes into a regular dictionary."""

    result = {}

    for item in attributes or []:
        key = item.get("key")
        value = item.get("value", {})

        if not key or not isinstance(value, dict):
            continue

        extracted = next(
            (
                value[field]
                for field in (
                    "stringValue",
                    "intValue",
                    "doubleValue",
                    "boolValue",
                )
                if field in value
            ),
            value,
        )

        result[key] = extracted

    return result


def _parse_prometheus(payload: dict) -> tuple[list[dict], dict]:
    """Extract metric evidence from a Prometheus query API response."""

    evidence = []
    metrics = {}

    results = (
        payload.get("data", {})
        .get("result", [])
    )

    for item in results:
        labels = item.get("metric", {})
        metric_name = labels.get("__name__", "")

        value_data = item.get("value") or item.get("values")

        if not value_data:
            continue

        # Instant query: [timestamp, value]
        # Range query: [[timestamp, value], ...]
        if (
            isinstance(value_data, list)
            and len(value_data) == 2
            and not isinstance(value_data[0], list)
        ):
            sample = value_data

        elif isinstance(value_data, list):
            sample = value_data[-1] if value_data else None

        else:
            sample = None

        if not sample or len(sample) < 2:
            continue

        try:
            numeric_value = float(sample[1])
        except (TypeError, ValueError):
            continue

        normalized_name = metric_name.lower()

        if any(
            term in normalized_name
            for term in (
                "error_rate",
                "error_percentage",
                "http_errors_percent",
            )
        ):
            metrics["error_rate"] = numeric_value

        elif any(
            term in normalized_name
            for term in (
                "latency_ms",
                "response_time_ms",
                "duration_ms",
            )
        ):
            metrics["latency_ms"] = numeric_value

        elif (
            "latency" in normalized_name
            or "duration" in normalized_name
        ):
            if normalized_name.endswith("_seconds"):
                metrics["latency_ms"] = numeric_value * 1000

        evidence.append({
            "source": "prometheus",
            "kind": "metric",
            "name": metric_name or "unknown_metric",
            "value": numeric_value,
            "labels": labels,
            "timestamp": sample[0],
        })

    return evidence, metrics


def _parse_otel_traces(
    payload: dict,
) -> tuple[list[dict], list[str]]:
    """Extract normalized spans and failed-span evidence from OTLP."""

    evidence = []
    log_entries = []

    for resource in payload.get("resourceSpans", []):

        resource_attributes = _attributes_to_dict(
            resource.get("resource", {}).get("attributes", [])
        )

        service_name = (
            resource_attributes.get("service.name")
            or "unknown_service"
        )

        for scope in resource.get("scopeSpans", []):

            for span in scope.get("spans", []):

                attributes = _attributes_to_dict(
                    span.get("attributes", [])
                )

                # Calculate span duration.
                try:
                    start = int(span.get("startTimeUnixNano", 0))
                    end = int(span.get("endTimeUnixNano", 0))

                    duration_ms = max(
                        0,
                        end - start,
                    ) / 1_000_000

                except (TypeError, ValueError):
                    duration_ms = None

                status_info = span.get("status") or {}
                status = status_info.get("code", 0)

                failed = str(status) in (
                    "2",
                    "STATUS_CODE_ERROR",
                )

                # Resolve service identity.
                current_service = (
                    attributes.get("service.name")
                    or service_name
                )

                record = {
                    "source": "opentelemetry",
                    "kind": "trace",
                    "name": span.get("name", "unknown_span"),
                    "trace_id": span.get("traceId"),
                    "span_id": span.get("spanId"),
                    "parent_span_id": span.get("parentSpanId"),
                    "service_name": current_service,
                    "duration_ms": duration_ms,
                    "start_time_unix_nano": span.get(
                        "startTimeUnixNano"
                    ),
                    "end_time_unix_nano": span.get(
                        "endTimeUnixNano"
                    ),
                    "status_code": status,
                    "status_message": status_info.get("message"),
                    "failed": failed,
                    "attributes": attributes,
                    "resource_attributes": resource_attributes,
                }

                evidence.append(record)

                if failed:
                    log_entries.append(
                        "OTEL TRACE ERROR: "
                        f"service={current_service}; "
                        f"span={record['name']}; "
                        f"trace_id={record['trace_id']}; "
                        f"duration_ms={duration_ms}; "
                        f"status={status}; "
                        f"message={record['status_message']}; "
                        f"attributes={attributes}"
                    )

    return evidence, log_entries


def _parse_otel_logs(
    payload: dict,
) -> tuple[list[dict], list[str]]:
    """Extract log records from an OTLP logs payload."""

    evidence = []
    log_entries = []

    for resource in payload.get("resourceLogs", []):

        resource_attributes = _attributes_to_dict(
            resource.get("resource", {}).get("attributes", [])
        )

        for scope in resource.get("scopeLogs", []):

            for record in scope.get("logRecords", []):

                attributes = _attributes_to_dict(
                    record.get("attributes", [])
                )

                body = record.get("body", {})

                message = (
                    body.get("stringValue", str(body))
                    if isinstance(body, dict)
                    else str(body)
                )

                severity = record.get(
                    "severityText",
                    "UNSPECIFIED",
                )

                item = {
                    "source": "opentelemetry",
                    "kind": "log",
                    "message": message,
                    "severity": severity,
                    "timestamp": record.get("timeUnixNano"),
                    "trace_id": record.get("traceId"),
                    "span_id": record.get("spanId"),
                    "attributes": attributes,
                    "resource_attributes": resource_attributes,
                }

                evidence.append(item)

                log_entries.append(
                    f"OTEL LOG [{severity}]: {message}"
                )

    return evidence, log_entries


def normalize_incident_evidence(
    incident: IncidentRequest,
) -> IncidentRequest:
    """
    Merge application logs, Prometheus metrics and OpenTelemetry
    traces/logs into the existing incident investigation model.
    """

    normalized = []
    logs = list(incident.logs)

    error_rate = incident.error_rate
    latency_ms = incident.latency_ms

    # Application logs.
    for entry in incident.logs:
        normalized.append({
            "source": "application_logs",
            "kind": "log",
            "message": entry,
        })

    # Prometheus metrics.
    if incident.prometheus_payload:

        prometheus_evidence, metrics = _parse_prometheus(
            incident.prometheus_payload
        )

        normalized.extend(prometheus_evidence)

        if "error_rate" in metrics:
            error_rate = metrics["error_rate"]

        if "latency_ms" in metrics:
            latency_ms = metrics["latency_ms"]

    # OpenTelemetry traces.
    if incident.otel_traces_payload:

        trace_evidence, trace_logs = _parse_otel_traces(
            incident.otel_traces_payload
        )

        normalized.extend(trace_evidence)
        logs.extend(trace_logs)

    # OpenTelemetry logs.
    if incident.otel_logs_payload:

        otel_evidence, otel_logs = _parse_otel_logs(
            incident.otel_logs_payload
        )

        normalized.extend(otel_evidence)
        logs.extend(otel_logs)

    # Preserve the existing incident interface.
    return incident.model_copy(
        update={
            "logs": logs[:100],
            "error_rate": error_rate,
            "latency_ms": latency_ms,
            "normalized_evidence": normalized,
        }
    )
