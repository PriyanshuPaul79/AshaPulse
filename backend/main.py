# backend/main.py
# NiDaan — FastAPI Backend
#
# Endpoints:
#   POST /diagnose       → main diagnosis endpoint
#   GET  /health         → server status check
#
# Usage:
#   cd Langchain_ASHA
#   uvicorn backend.main:app --reload --port 8000
import sys
import os
sys.path.append(os.path.dirname(__file__))
os.environ["HF_TOKEN"] = os.getenv("HUGGINGFACEHUB_API_TOKEN", "")


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import traceback

from chain import get_chain
from schemas import (
    ASHAResponse,
    PHCRecommendationRequest,
    PHCRecommendationResponse,
    PHCResult
)
from phc_recommender import recommend_phcs

# ── Lifespan — load chain once on startup ─────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load RAG chain on startup. Keeps it in memory for all requests."""
    print("\nStarting NiDaan API...")
    #get_chain()   # initialise once — cached for all subsequent requests
    yield
    print("\nShutting down NiDaan API...")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="NiDaan API",
    description="AI Diagnostic Assistant for ASHA Workers — Rural India",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow Streamlit frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Models ─────────────────────────────────────────────────

class DiagnoseRequest(BaseModel):
    symptoms: str

    class Config:
        json_schema_extra = {
            "example": {
                "symptoms": "bacche ko 3 din se bukhaar hai, khaana nahi kha raha"
            }
        }


class DiagnoseResponse(BaseModel):
    success:  bool
    data:     dict | None = None
    error:    str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    """Check if API and chain are ready."""
    return {
        "status":  "ok",
        "service": "NiDaan API",
        "version": "1.0.0",
    }


@app.post("/diagnose", response_model=DiagnoseResponse)
def diagnose(request: DiagnoseRequest):
    """
    Main diagnosis endpoint.

    Takes Hinglish/Hindi symptom description.
    Returns structured diagnosis with criticality,
    home care advice, medicines, and PHC referral decision.
    """

    # Basic input validation
    if not request.symptoms.strip():
        raise HTTPException(
            status_code=400,
            detail="Symptoms cannot be empty"
        )

    if len(request.symptoms.strip()) < 5:
        raise HTTPException(
            status_code=400,
            detail="Please describe symptoms in more detail"
        )

    try:
        chain  = get_chain()
        result = chain(request.symptoms.strip())

        return DiagnoseResponse(
            success=True,
            data=result,
        )

    except Exception as e:
        traceback.print_exc()
        return DiagnoseResponse(
            success=False,
            error=str(e),
        )


@app.post("/recommend-phc", response_model=PHCRecommendationResponse)
def recommend_phc(request: PHCRecommendationRequest):
    """
    Recommend the top 3 PHCs based on district, criticality,
    required services, and optional patient coordinates.
    """
    try:
        recommendations_data = recommend_phcs(
            district=request.district,
            criticality=request.criticality,
            required_services=request.required_services,
            patient_lat=request.patient_lat,
            patient_lng=request.patient_lng
        )
        
        # Map list of dicts to Pydantic PHCResult models
        recommendations = [PHCResult(**rec) for rec in recommendations_data]
        
        return PHCRecommendationResponse(
            success=True,
            district=request.district,
            recommendations=recommendations
        )
    except Exception as e:
        traceback.print_exc()
        return PHCRecommendationResponse(
            success=False,
            district=request.district,
            recommendations=[],
            error=str(e)
        )