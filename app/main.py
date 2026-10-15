from fastapi import FastAPI
from app.schemas import IncidentRequest
from app.services.investigator import investigate

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
    return investigate(incident)