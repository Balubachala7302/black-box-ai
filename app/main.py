from fastapi import FastAPI
from app.schemas import IncidentRequest
from app.services.diagnostics import analyze_incident

app = FastAPI(
    title="BLACK BOX AI",
    description="An AI-powered software incident investigator.",
    version="0.2.0",
)


@app.get("/")
def root():
    return {
        "project": "BLACK BOX AI",
        "message": "AI Incident Investigator API is running!",
        "status": "operational",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "black-box-ai",
    }


@app.post("/incidents/investigate")
def investigate_incident(incident: IncidentRequest):
    diagnosis = analyze_incident(incident)

    return {
        "incident_title": incident.title,
        "status": "analyzed",
        "evidence_summary": {
            "description": incident.description,
            "log_count": len(incident.logs),
            "error_rate": incident.error_rate,
            "latency_ms": incident.latency_ms,
            "recent_deployment": incident.recent_deployment,
        },
        "diagnosis": diagnosis,
    }