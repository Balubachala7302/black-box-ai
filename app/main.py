
from fastapi import FastAPI, HTTPException, Query

from app.schemas import IncidentRequest
from app.services.investigator import investigate
from app.services import nemotron_agent

app = FastAPI(
    title="BLACK BOX AI",
    description="An AI-powered software incident investigator.",
    version="0.3.0",
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
def investigate_incident(
    incident: IncidentRequest,
    mode: str = Query(default="baseline", pattern="^(baseline|nemotron)$"),
):
    if mode == "baseline":
        return investigate(incident)

    try:
        return nemotron_agent.investigate_with_nemotron(incident)
    except Exception:
        raise HTTPException(
            status_code=503,
            detail=(
                "Nemotron investigation is currently unavailable. "
                "Retry or use mode=baseline."
            ),
        ) from None
