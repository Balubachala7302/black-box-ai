
from typing import Any

from pydantic import BaseModel, Field


class IncidentRequest(BaseModel):
    title: str = Field(
        min_length=3,
        max_length=200,
        description="Short description of the incident",
    )

    description: str = Field(
        min_length=10,
        max_length=2000,
        description="What went wrong?",
    )

    logs: list[str] = Field(
        default_factory=list,
        max_length=100,
        description="Application log entries",
    )

    error_rate: float = Field(
        default=0,
        ge=0,
        le=100,
        description="Current error rate as a percentage",
    )

    latency_ms: float = Field(
        default=0,
        ge=0,
        description="Current response latency in milliseconds",
    )

    recent_deployment: bool = Field(
        default=False,
        description="Whether a recent deployment occurred",
    )

    # Optional Prometheus query API response.
    prometheus_payload: dict[str, Any] | None = Field(
        default=None,
        description="Prometheus query API JSON payload",
    )

    # Optional OpenTelemetry OTLP JSON payloads.
    otel_traces_payload: dict[str, Any] | None = Field(
        default=None,
        description="OpenTelemetry traces export payload",
    )

    otel_logs_payload: dict[str, Any] | None = Field(
        default=None,
        description="OpenTelemetry logs export payload",
    )

    # Populated internally during evidence normalization.
    normalized_evidence: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Normalized evidence collected from all sources",
    )
