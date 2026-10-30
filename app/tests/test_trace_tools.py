
import pytest

from app.schemas import IncidentRequest
from app.services.diagnostic_tools import inspect_traces


def create_incident(normalized_evidence=None):
    return IncidentRequest(
        title="Payment Service Incident",
        description="Payment requests are experiencing failures and latency.",
        logs=[],
        error_rate=8.5,
        latency_ms=1500,
        recent_deployment=False,
        normalized_evidence=normalized_evidence or [],
    )


def create_span(
    name="payment_request",
    service_name="payment-service",
    duration_ms=200,
    failed=False,
    trace_id="trace-001",
    span_id="span-001",
    parent_span_id=None,
):
    return {
        "source": "opentelemetry",
        "kind": "trace",
        "name": name,
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "service_name": service_name,
        "duration_ms": duration_ms,
        "status_code": 2 if failed else 1,
        "status_message": "Internal error" if failed else None,
        "failed": failed,
        "attributes": {},
        "resource_attributes": {
            "service.name": service_name,
        },
    }


def test_inspect_traces_detects_failed_spans():
    incident = create_incident([
        create_span(failed=True),
    ])

    result = inspect_traces(incident)

    assert result["total_spans_examined"] == 1
    assert result["failed_span_count"] == 1
    assert result["slow_span_count"] == 0
    assert result["failed_spans"][0]["span_name"] == "payment_request"


def test_inspect_traces_detects_slow_spans():
    incident = create_incident([
        create_span(duration_ms=1800),
    ])

    result = inspect_traces(
        incident,
        min_duration_ms=1000,
    )

    assert result["slow_span_count"] == 1
    assert result["failed_span_count"] == 0
    assert result["slow_spans"][0]["duration_ms"] == 1800



def test_inspect_traces_does_not_classify_healthy_spans():
    incident = create_incident([
        create_span(duration_ms=200, failed=False),
    ])

    result = inspect_traces(incident)

    assert result["total_spans_examined"] == 1
    assert result["matching_spans"] == 1

    assert result["failed_span_count"] == 0
    assert result["slow_span_count"] == 0

    assert result["failed_spans"] == []
    assert result["slow_spans"] == []

    assert (
        result["trace_evidence"][0]["evidence_status"]
        == "normal"
    )



def test_inspect_traces_filters_by_service_name():
    incident = create_incident([
        create_span(
            service_name="payment-service",
            failed=True,
        ),
        create_span(
            service_name="inventory-service",
            failed=True,
            trace_id="trace-002",
            span_id="span-002",
        ),
    ])

    result = inspect_traces(
        incident,
        service_name="payment-service",
    )

    assert result["total_spans_examined"] == 2
    assert result["matching_spans"] == 1
    assert result["failed_span_count"] == 1
    assert (
        result["trace_evidence"][0]["service_name"]
        == "payment-service"
    )


def test_inspect_traces_errors_only_returns_failed_spans():
    incident = create_incident([
        create_span(
            name="successful_request",
            duration_ms=200,
            failed=False,
        ),
        create_span(
            name="failed_request",
            duration_ms=300,
            failed=True,
            trace_id="trace-002",
            span_id="span-002",
        ),
    ])

    result = inspect_traces(
        incident,
        errors_only=True,
    )

    assert result["matching_spans"] == 1
    assert result["failed_span_count"] == 1
    assert result["trace_evidence"][0]["span_name"] == "failed_request"


def test_inspect_traces_returns_empty_result_without_trace_data():
    incident = create_incident()

    result = inspect_traces(incident)

    assert result["total_spans_examined"] == 0
    assert result["matching_spans"] == 0
    assert result["failed_span_count"] == 0
    assert result["slow_span_count"] == 0
    assert result["trace_evidence"] == []


def test_inspect_traces_preserves_parent_span_relationship():
    incident = create_incident([
        create_span(
            name="payment_request",
            span_id="child-span",
            parent_span_id="parent-span",
            failed=True,
        ),
    ])

    result = inspect_traces(incident)

    assert result["trace_evidence"][0]["span_id"] == "child-span"
    assert (
        result["trace_evidence"][0]["parent_span_id"]
        == "parent-span"
    )


def test_inspect_traces_supports_targeted_query():
    incident = create_incident([
        create_span(
            name="payment_provider_request",
            failed=True,
        ),
        create_span(
            name="inventory_lookup",
            failed=True,
            trace_id="trace-002",
            span_id="span-002",
        ),
    ])

    result = inspect_traces(
        incident,
        query="payment_provider",
    )

    assert result["matching_spans"] == 1
    assert (
        result["trace_evidence"][0]["span_name"]
        == "payment_provider_request"
    )
