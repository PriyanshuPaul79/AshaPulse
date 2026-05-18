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