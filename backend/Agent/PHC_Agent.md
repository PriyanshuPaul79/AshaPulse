# AGENT.md — NiDaan PHC Recommendation System
# Model: DeepSeek V4
# Task: Build PHC recommendation into backend + frontend
# Read this entire file before writing a single line of code.

---

## WHO YOU ARE

You are a senior full-stack engineer building a PHC (Primary Health Centre)
recommendation feature for NiDaan — an AI diagnostic assistant for ASHA
workers in rural India. You write clean, typed, production-ready code.
You read existing files before modifying them. You never overwrite working
code without understanding it first.

---

## WHAT YOU ARE BUILDING

A PHC recommendation system that:
1. Takes the patient's district + the diagnosis result (criticality + services needed)
2. Queries the SQLite database of 19 PHCs across 5 West Bengal districts
3. Ranks PHCs by: service match score FIRST, then distance SECOND
4. Returns top 3 recommended PHCs to the frontend
5. Displays them on the existing /phc screen in Next.js

---

## PROJECT STRUCTURE — READ THESE FILES FIRST

Before writing any code, read these files in order:

```
STEP 1 — Read backend files:
  Langchain_ASHA/backend/schemas.py       ← existing Pydantic models
  Langchain_ASHA/backend/main.py          ← existing FastAPI app
  Langchain_ASHA/backend/chain.py         ← existing RAG chain
  Langchain_ASHA/data/phc_directory.db    ← SQLite DB (read schema)
  Langchain_ASHA/data/phc_directory/west_bengal/*.json  ← PHC raw data

STEP 2 — Read frontend files:
  asha/app/phc/page.tsx                   ← existing PHC screen
  asha/app/result/page.tsx                ← result screen (to add PHC button)
  asha/types/nidaan.ts                    ← existing TypeScript types
  asha/.env.example                       ← env variable names
```

Do NOT skip this step. The existing code is working — understand it before touching it.

---

## BACKEND TASKS

### TASK B1 — Add PHC types to schemas.py [COMPLETED]

Add these Pydantic models to the BOTTOM of schemas.py.
Do NOT modify existing models.

```python
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
```

---

### TASK B2 — Create backend/phc_recommender.py (NEW FILE) [COMPLETED]

Create this file from scratch. This is the core recommendation logic.

```
Location: Langchain_ASHA/backend/phc_recommender.py
```

Logic to implement:

**Step 1 — Service mapping**
Map criticality + symptoms to required services:
```python
SERVICE_MAP = {
    "high": ["OPD", "Delivery Services", "Basic Lab"],
    "medium": ["OPD", "Maternal & Child Health"],
    "low": ["OPD"],
    # Keyword-based additions (check criticality reason string):
    "malaria":      ["Malaria Testing"],
    "tb":           ["TB DOTS"],
    "snake":        ["Snake Bite Treatment"],
    "delivery":     ["Delivery Services", "Maternal & Child Health"],
    "pregnancy":    ["Maternal & Child Health", "Delivery Services"],
    "nutrition":    ["Nutrition Services"],
    "immunization": ["Immunization"],
    "hiv":          ["HIV Testing"],
}
```

**Step 2 — Query SQLite**
Query phc_directory.db for all PHCs in the given district.
Connection string: `sqlite:///data/phc_directory.db`
Handle missing district gracefully — return empty list, not error.

**Step 3 — Score each PHC**
For each PHC:
```
service_match_score = (matched_services / required_services) * 1.0
```
If open_24hr AND criticality == "high": add 0.2 bonus (cap at 1.0)
If ambulance AND criticality == "high": add 0.1 bonus (cap at 1.0)

**Step 4 — Calculate distance (haversine)**
Only if patient_lat and patient_lng are provided AND phc has coordinates.
```python
from math import radians, sin, cos, sqrt, atan2

def haversine(lat1, lng1, lat2, lng2) -> float:
    R = 6371  # Earth radius km
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))
```
If coordinates missing: distance_km = None, rank by score only.

**Step 5 — Rank**
Sort by: service_match_score DESC, then distance_km ASC (None last).
Return top 3 only.

**Step 6 — Generate match_reason**
Human-readable string for each PHC:
```python
# Examples:
"Matches 3/3 required services. 2.4 km away. Open 24 hours."
"Matches 2/3 required services. Nearest PHC in district."
"Partial match (1/3 services). Consider if closer PHCs unavailable."
```

---

### TASK B3 — Add endpoint to main.py [COMPLETED]

Add this endpoint to the EXISTING FastAPI app in main.py.
Import PHCRecommendationRequest, PHCRecommendationResponse from schemas.
Import recommend_phcs from phc_recommender.

```
POST /recommend-phc
Request:  PHCRecommendationRequest
Response: PHCRecommendationResponse
```

Also update the CORS allowed origins to include production if needed.
Keep existing /health and /diagnose endpoints completely untouched.

---

### TASK B4 — Update /diagnose response (optional enhancement) [COMPLETED]

If the criticality is "high" OR "medium", auto-extract required_services
from the diagnosis reason text and include it in the /diagnose response:

Add to ASHAResponse in schemas.py:
```python
suggested_services: List[str] = []   # new optional field, default empty
```

Populate it in chain.py after parsing the LLM response — use the SERVICE_MAP
keyword matching against the reason field. This way the frontend can pass
required_services directly to /recommend-phc without user input.

---

## FRONTEND TASKS

### TASK F1 — Add TypeScript types to types/nidaan.ts [COMPLETED]

Add to the BOTTOM of the existing types file:

```typescript
export interface PHCResult {
  id: string;
  name: string;
  block: string;
  address: string;
  contact: string | null;
  open_24hr: boolean;
  timing: string;
  services: string[];
  ambulance: boolean;
  latitude: number | null;
  longitude: number | null;
  distance_km: number | null;
  service_match_score: number;
  match_reason: string;
}

export interface PHCRecommendationRequest {
  district: string;
  criticality: CriticalityLevel;
  required_services: string[];
  patient_lat?: number;
  patient_lng?: number;
}

export interface PHCRecommendationResponse {
  success: boolean;
  district: string;
  recommendations: PHCResult[];
  error: string | null;
}
```

---

### TASK F2 — Create hooks/usePHCRecommend.ts (NEW FILE) [COMPLETED]

```typescript
// Calls POST /recommend-phc
// Returns: { recommend, isLoading, error, results }
// Timeout: 10 seconds (this is a DB query, not LLM — must be fast)
```

Handle these error states explicitly:
- No PHCs found for district → show "Koi PHC nahi mila" message
- Network error → show bilingual error
- Empty district → validate before calling

---

### TASK F3 — Update app/phc/page.tsx [COMPLETED]

READ THE EXISTING FILE FIRST. Then enhance it.

Replace any hardcoded PHC data with live API calls via usePHCRecommend hook.

**UI layout for the PHC screen:**

```
[District Selector Dropdown]
  Options: Paschim Bardhaman, Purba Bardhaman,
           Hooghly, Howrah, Kolkata

[Criticality context banner — only if navigated from result]
  "🔴 HIGH criticality — showing 24hr PHCs first"
  OR "🟡 MEDIUM — showing nearest PHCs"

[PHC Cards — top 3, ranked]

  ┌─────────────────────────────────────────┐
  │ 🏥 Andal Primary Health Centre          │
  │    📍 Andal Block, Paschim Bardhaman    │
  │    🕒 9AM–4PM Mon–Sat                   │
  │    📞 Not available                      │
  │                                          │
  │  Match Score: ████████░░ 80%            │
  │  "Matches 2/3 required services"         │
  │                                          │
  │  Services: [OPD] [MCH] [Malaria]        │
  │                                          │
  │  [🗺️ Directions] [📞 Call]              │
  └─────────────────────────────────────────┘

  Distance shown only if coordinates available.
  Match score shown as a colored progress bar:
    >0.7 → green bar
    0.4–0.7 → amber bar
    <0.4 → red bar

[Loading state: 3 skeleton PHC cards]
[Empty state: "Is district mein abhi data nahi hai"]
```

**Directions button:**
Opens Google Maps with PHC coordinates:
```typescript
const mapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${phc.latitude},${phc.longitude}`;
window.open(mapsUrl, '_blank');
```
If no coordinates: disable button, show tooltip "Location unavailable".

---

### TASK F4 — Update app/result/page.tsx [COMPLETED]

READ THE EXISTING FILE FIRST. Then add:

If criticality is "medium" or "high", show a button at the bottom of the
result screen:

```
[🏥 PHC Dhundhen / Find PHC →]   ← green for medium, red for high
```

On click: navigate to /phc and pass the following via URL search params:
```
/phc?district=Paschim+Bardhaman&criticality=high&services=OPD,Maternal+%26+Child+Health
```

The /phc page reads these params on load and auto-triggers the recommendation.

---

## EXECUTION ORDER

Follow this exact order. Do not skip steps or work in parallel.

```
1. Read all existing files (mandatory)
2. backend/schemas.py       — add new Pydantic models
3. backend/phc_recommender.py — create from scratch
4. backend/main.py          — add /recommend-phc endpoint
5. backend/chain.py         — add suggested_services extraction
6. TEST: POST /recommend-phc via curl or Postman
   {
     "district": "Paschim Bardhaman",
     "criticality": "high",
     "required_services": ["OPD", "Malaria Testing"]
   }
   Expected: 200 OK with 1-3 PHC results ranked by score
7. asha/types/nidaan.ts     — add new TS types
8. asha/hooks/usePHCRecommend.ts — create hook
9. asha/app/phc/page.tsx    — update PHC screen
10. asha/app/result/page.tsx — add Find PHC button
11. TEST: Full flow in browser
    Diagnose → result → click Find PHC → see ranked PHCs
```

---

## CONSTRAINTS — NEVER VIOLATE THESE

```
❌ Do NOT delete or modify existing /health or /diagnose endpoints
❌ Do NOT change ASHAResponse schema in a breaking way
❌ Do NOT install new npm packages without checking package.json first
❌ Do NOT hardcode PHC data in frontend — always fetch from /recommend-phc
❌ Do NOT show medicines or home_care for HIGH criticality (existing rule)
❌ Do NOT use any paid API for PHC lookup — SQLite only, fully offline
❌ Do NOT show distance if PHC has no coordinates — show null gracefully
❌ Do NOT break the existing diagnosis flow
```

---

## SQLITE DB SCHEMA (for reference)

The existing phc_directory.db has this structure:
```sql
CREATE TABLE phcs (
  id            TEXT PRIMARY KEY,
  name          TEXT,
  block         TEXT,
  district      TEXT,
  address       TEXT,
  pin_code      TEXT,
  contact       TEXT,
  open_24hr     INTEGER,   -- 0 or 1
  doctor_timing TEXT,
  services      TEXT,      -- JSON array stored as string
  ambulance     INTEGER,   -- 0 or 1
  latitude      REAL,
  longitude     REAL
);
```

When reading services: `json.loads(row['services'])` — it's a JSON string.
When reading open_24hr/ambulance: compare to 1, not True.

---

## ERROR HANDLING RULES

Every function must handle:
- Empty district query → return empty recommendations, not 500
- Missing DB file → log error, return friendly message
- PHC with null coordinates → skip distance, rank by score only
- All PHCs in district have 0 service match → return them anyway, score = 0.0
- Frontend fetch timeout → show retry button

---

## DONE SIGNAL

You are done when:
1. `POST /recommend-phc` returns ranked PHC JSON for Paschim Bardhaman
2. The /phc screen shows live data (not hardcoded)
3. The /result screen has a working "Find PHC" button for medium/high cases
4. No existing tests or endpoints are broken
5. No TypeScript errors in the frontend

---

*Project: NiDaan | Developer: Priyanshu Paul | Model: MiniMax*
*Backend: Langchain_ASHA/ | Frontend: asha/*