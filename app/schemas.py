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
        description="Relevant application log entries",
    )

    error_rate: float = Field(
        ge=0,
        le=100,
        description="Current error rate as a percentage",
    )

    latency_ms: float = Field(
        ge=0,
        description="Current response latency in milliseconds",
    )

    recent_deployment: bool = Field(
        default=False,
        description="Whether a recent deployment occurred",
    )