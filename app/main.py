
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import IncidentRequest
from app.services.investigator import investigate
from app.services import nemotron_agent
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="BLACK BOX AI",
    description="An AI-powered software incident investigator.",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        logger.exception("Nemotron investigation failed")
        raise HTTPException(
            status_code=503,
            detail=(
                "Nemotron investigation is currently unavailable. "
                "Check the backend terminal for the underlying error."
            ),
        ) from None
