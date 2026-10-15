
from app.schemas import IncidentRequest
from app.services.nemotron_agent import investigate_with_nemotron

incident = IncidentRequest(
    title="API errors increased after deployment",
    description=(
        "The API error rate increased sharply after a recent release. "
        "Response latency is also elevated."
    ),
    logs=[
        "ERROR: Database connection timeout",
        "WARNING: Connection pool limit reached",
        "ERROR: Request failed with status 503",
    ],
    error_rate=25.0,
    latency_ms=1800.0,
    recent_deployment=True,
)

print("Starting BLACK BOX AI investigation...\n")

try:
    result = investigate_with_nemotron(incident)

    print("Status:", result["status"])
    print("Tool calls:", result["tool_calls_used"])

    print("\nInvestigation trace:")
    for step in result["investigation_trace"]:
        print(f"\nTool: {step['tool']}")
        print(step["result"])

    print("\nNemotron's analysis:")
    print(result["analysis"])

except Exception as exc:
    print(f"Investigation failed: {type(exc).__name__}: {exc}")
