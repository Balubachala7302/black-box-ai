"""Synthetic incidents with known or intentionally uncertain targets."""

from app.schemas import IncidentRequest


BENCHMARK_CASES = [
    {
        "case_id": "db-001",
        "expected_cause": "Database connection saturation",
        "incident": IncidentRequest(
            title="Database connection timeouts",
            description="Requests are waiting for database connections.",
            logs=[
                "ERROR: Database connection timeout",
                "WARNING: Connection pool limit reached",
            ],
            error_rate=25.0,
            latency_ms=1800.0,
            recent_deployment=False,
        ),
    },
    {
        "case_id": "deploy-001",
        "expected_cause": "Deployment-related regression",
        "incident": IncidentRequest(
            title="Release-specific API regression",
            description=(
                "A release-specific error began immediately after version "
                "2.4.1 was deployed. The error rate was 1% before deployment "
                "and increased to 25% afterward. An unaffected control "
                "service remained at 1%."
            ),
            logs=[
                "ERROR: Release 2.4.1: payment_handler returned HTTP 500",
                "ERROR: New response validation failure introduced in release 2.4.1",
                "INFO: Error rate before deployment: 1%",
                "INFO: Error rate after deployment: 25%",
                "INFO: Unaffected control service error rate remains 1%",
            ],
            error_rate=25.0,
            latency_ms=300.0,
            recent_deployment=True,
        ),
    },
    {
        "case_id": "latency-001",
        "expected_cause": None,
        "incident": IncidentRequest(
            title="Application latency spike",
            description="The service is responding slowly.",
            logs=["INFO: Requests are completing successfully"],
            error_rate=0.5,
            latency_ms=1800.0,
            recent_deployment=False,
        ),
    },
    {
        "case_id": "healthy-001",
        "expected_cause": None,
        "incident": IncidentRequest(
            title="Normal service operation",
            description="The service is operating within expected limits.",
            logs=["INFO: Request completed successfully"],
            error_rate=0.5,
            latency_ms=150.0,
            recent_deployment=False,
        ),
    },
    {
        "case_id": "conflict-001",
        "expected_cause": None,
        "incident": IncidentRequest(
            title="Database errors with healthy connection telemetry",
            description=(
                "Application logs report connection timeouts, but a "
                "separate telemetry report says database connections "
                "are healthy. The evidence conflicts."
            ),
            logs=[
                "ERROR: Database connection timeout",
                "WARNING: Connection pool limit reached",
                "INFO: Database active connections are within normal range",
            ],
            error_rate=15.0,
            latency_ms=1400.0,
            recent_deployment=False,
        ),
    },
    {
        "case_id": "ambiguous-001",
        "expected_cause": None,
        "incident": IncidentRequest(
            title="Slow service with insufficient evidence",
            description=(
                "Latency is high, but there are no dependency traces, "
                "historical baselines, or relevant error logs."
            ),
            logs=["INFO: Request completed"],
            error_rate=1.0,
            latency_ms=2200.0,
            recent_deployment=False,
        ),
    },
    {
        "case_id": "upstream-001",
        "expected_cause": "Upstream dependency failure",
        "incident": IncidentRequest(
            title="Payment provider requests timing out",
            description=(
                "Payment requests are failing while calling an external "
                "provider. The provider's own health has not been checked."
            ),
            logs=[
                "ERROR: Upstream timeout calling payment provider",
                "WARNING: Service unavailable from dependency",
            ],
            error_rate=12.0,
            latency_ms=2400.0,
            recent_deployment=False,
        ),
    },
    {
        "case_id": "deploy-correlation-001",
        "expected_cause": None,
        "incident": IncidentRequest(
            title="Errors observed after an unrelated release",
            description=(
                "A deployment occurred recently, but there is no "
                "before-and-after comparison or evidence linking it "
                "to the errors."
            ),
            logs=[
                "ERROR: Request failed with status 500",
                "INFO: No release-specific error identified",
            ],
            error_rate=8.0,
            latency_ms=300.0,
            recent_deployment=True,
        ),
    },
    {
        "case_id": "unknown-001",
        "expected_cause": None,
        "incident": IncidentRequest(
            title="Unclassified service warning",
            description=(
                "An unusual warning appeared, but there is not enough "
                "information to identify its cause."
            ),
            logs=[
                "WARNING: Event QX-17 observed in subsystem amber",
            ],
            error_rate=0.5,
            latency_ms=180.0,
            recent_deployment=False,
        ),
    },

    # Edge case 1: Deployment correlation without causal evidence.
    {
        "case_id": "deploy-misleading-001",
        "expected_cause": None,
        "incident": IncidentRequest(
            title="Errors increased around a deployment",
            description=(
                "A deployment occurred near the time of elevated errors, "
                "but there is no release-specific evidence, before-and-after "
                "comparison, or confirmed underlying cause."
            ),
            logs=[
                "INFO: Deployment completed successfully",
                "ERROR: Request failed with status 500",
                "WARNING: Elevated response latency detected",
            ],
            error_rate=18.0,
            latency_ms=1600.0,
            recent_deployment=True,
        ),
    },

    # Edge case 2: Deployment signals that require careful verification.
    {
        "case_id": "deploy-conflict-001",
        "expected_cause": None,
        "incident": IncidentRequest(
            title="Conflicting release regression evidence",
            description=(
                "Some logs suggest a release-specific regression, "
                "while other logs report no measurable change after release."
            ),
            logs=[
                "ERROR: Release 3.1.0: checkout_handler returned HTTP 500",
                "ERROR: New response validation failure introduced in release 3.1.0",
                "INFO: Error rate before deployment: 2%",
                "INFO: Error rate after deployment: 2%",
                "INFO: Unaffected control service error rate remains 2%",
            ],
            error_rate=2.0,
            latency_ms=350.0,
            recent_deployment=True,
        ),
    },

    # Edge case 3: Missing or incomplete incident evidence.
    {
        "case_id": "missing-evidence-001",
        "expected_cause": None,
        "incident": IncidentRequest(
            title="Incomplete incident report",
            description=(
                "An alert was received, but logs do not identify a cause "
                "and the reported measurements are nominal."
            ),
            logs=[],
            error_rate=0.0,
            latency_ms=0.0,
            recent_deployment=False,
        ),
    },

    # Edge case 4: Two competing underlying causes have log evidence.
    {
        "case_id": "multiple-causes-001",
        "expected_cause": None,
        "incident": IncidentRequest(
            title="Database and upstream failures",
            description=(
                "Database connection errors and payment-provider timeouts "
                "appear during the same incident. Their causal relationship "
                "has not been established."
            ),
            logs=[
                "ERROR: Database connection timeout",
                "WARNING: Connection pool limit reached",
                "ERROR: Upstream timeout calling payment provider",
                "WARNING: Service unavailable from dependency",
            ],
            error_rate=30.0,
            latency_ms=2500.0,
            recent_deployment=False,
        ),
    },

    # Edge case 5: Documentation-like text should not trigger a cause.
    {
        "case_id": "noisy-logs-001",
        "expected_cause": None,
        "incident": IncidentRequest(
            title="Noisy logs with misleading keywords",
            description=(
                "Logs mention database and deployment terms as examples "
                "in diagnostic documentation, not as observed failures."
            ),
            logs=[
                "INFO: Example message: database connection timeout",
                "INFO: Runbook explains the phrase connection pool limit",
                "INFO: Deployment regression is a possible cause to investigate",
                "INFO: All requests completed successfully",
            ],
            error_rate=0.2,
            latency_ms=120.0,
            recent_deployment=False,
        ),
    },
]