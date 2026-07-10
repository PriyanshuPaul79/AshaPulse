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
import uvicorn
sys.path.append(os.path.dirname(__file__))
os.environ["HF_TOKEN"] = os.getenv("HUGGINGFACEHUB_API_TOKEN", "")


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import traceback

from chain import get_chain
from guardrails.input import check_input
from guardrails.output import check_output
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
    get_chain()   # initialise once — cached for all subsequent requests
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

    # Guardrail: validate input
    input_check = check_input(request.symptoms)

    if not input_check.passed:
        error_msg = "; ".join(input_check.violations)
        if input_check.has_prompt_injection:
            error_msg = "Input contains potentially unsafe content. Please describe medical symptoms only."
        elif input_check.is_empty:
            error_msg = "Symptoms cannot be empty."
        elif input_check.is_irrelevant:
            error_msg = "कृपया केवल चिकित्सा लक्षण बताएं। यह उपकरण केवल स्वास्थ्य निर्णय सहायता के लिए है।\nPlease describe medical symptoms only."
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        chain  = get_chain()
        result = chain(input_check.sanitized)

        # Guardrail: validate output structure
        output_check = check_output(result)
        if not output_check.passed:
            print(f"[guardrail] Output violations: {output_check.violations}")
            # ponytail: log violations but still return — blocking a valid diagnosis
            # for formatting issues is worse UX

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
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
