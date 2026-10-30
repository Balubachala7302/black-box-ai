
import logging

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import IncidentRequest
from app.services.ingestion import normalize_incident_evidence
from app.services.investigator import investigate
from app.services import nemotron_agent

logger = logging.getLogger(__name__)

app = FastAPI(
    title="BLACK BOX AI",
    description="An AI-powered software incident investigator.",
    version="0.4.0",
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
        "version": "0.4.0",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "black-box-ai",
    }


@app.post("/evidence/normalize")
def normalize_evidence(incident: IncidentRequest):
    """Normalize application, Prometheus and OpenTelemetry evidence."""

    try:
        normalized = normalize_incident_evidence(incident)

        return {
            "status": "success",
            "evidence_count": len(normalized.normalized_evidence),
            "sources": sorted({
                item["source"]
                for item in normalized.normalized_evidence
            }),
            "metrics": {
                "error_rate": normalized.error_rate,
                "latency_ms": normalized.latency_ms,
            },
            "evidence": normalized.normalized_evidence,
        }

    except Exception:
        logger.exception("Evidence normalization failed")
        raise HTTPException(
            status_code=422,
            detail="Unable to normalize supplied evidence.",
        ) from None


@app.post("/incidents/investigate")
def investigate_incident(
    incident: IncidentRequest,
    mode: str = Query(
        default="baseline",
        pattern="^(baseline|nemotron)$",
    ),
):
    try:
        normalized_incident = normalize_incident_evidence(incident)

        if mode == "baseline":
            return investigate(normalized_incident)

        try:
            result = nemotron_agent.investigate_with_nemotron(
                normalized_incident
            )
        except Exception:
            logger.exception("Nemotron investigation failed")
            raise HTTPException(
                status_code=503,
                detail="Nemotron investigation is currently unavailable.",
            ) from None

        if result.get("status") == "error":
            raise HTTPException(
                status_code=503,
                detail="Nemotron investigation is currently unavailable.",
            )

        return result

    except HTTPException:
        raise

    except Exception:
        logger.exception("Incident investigation failed")
        raise HTTPException(
            status_code=500,
            detail="Incident investigation failed.",
        ) from None
