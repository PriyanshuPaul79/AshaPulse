# backend/schemas.py
# Pydantic models for structured LLM output

from pydantic import BaseModel
from typing import List, Optional
from enum import Enum


class CriticalityLevel(str, Enum):
    LOW    = "low"     # Home care sufficient
    MEDIUM = "medium"  # Monitor, visit PHC if worsens
    HIGH   = "high"    # Refer to PHC immediately


class Medicine(BaseModel):
    name:     str   # "Paracetamol 500mg"
    dosage:   str   # "1 tablet 3x daily"
    duration: str   # "3 days"


class ASHAResponse(BaseModel):
    criticality:    CriticalityLevel
    refer_to_phc:   bool
    reason:         str           # why this criticality level
    red_flags:      List[str]     # danger signs ASHA must watch for
    home_care:      List[str]     # steps if not referring (empty if refer=True)
    medicines:      List[Medicine] # only ASHA drug kit medicines
    advice_in_hindi: str          # plain Hindi summary for patient
    suggested_services: List[str] = [] # new optional field, default empty


class PHCRecommendationRequest(BaseModel):
    district: str                    # "Paschim Bardhaman"
    criticality: str                 # "low" | "medium" | "high"
    required_services: List[str]     # derived from diagnosis
    patient_lat: Optional[float] = None   # if available
    patient_lng: Optional[float] = None   # if available

class PHCResult(BaseModel):
    id: str
    name: str
    block: str
    address: str
    contact: Optional[str]
    open_24hr: bool
    timing: str
    services: List[str]
    ambulance: bool
    latitude: Optional[float]
    longitude: Optional[float]
    distance_km: Optional[float]     # None if no patient coords
    service_match_score: float       # 0.0 to 1.0
    match_reason: str                # human-readable why this PHC

class PHCRecommendationResponse(BaseModel):
    success: bool
    district: str
    recommendations: List[PHCResult]
    error: Optional[str] = None