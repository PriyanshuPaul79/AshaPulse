// export type CriticalityLevel = "low" | "medium" | "high";

// export interface Medicine {
//   name: string;
//   dosage: string;
//   duration: string;
// }

// export interface DiagnosisResult {
//   criticality: CriticalityLevel;
//   refer_to_phc: boolean;
//   reason: string;
//   red_flags: string[];
//   home_care: string[];
//   medicines: Medicine[];
//   advice_in_hindi: string;
// }

// export interface DiagnosisRecord {
//   id: string;
//   symptoms: string;
//   result: DiagnosisResult;
//   timestamp: string;  // ISO string
// }



// types/nidaan.ts
// Matches backend/schemas.py Pydantic models exactly

export type CriticalityLevel = "low" | "medium" | "high";

export interface Medicine {
  name: string;
  dosage: string;
  duration: string;
  source?: "asha_kit" | "nlem_2022";
}

export interface DiagnosisResult {
  criticality: CriticalityLevel;
  refer_to_phc: boolean;
  reason: string;
  red_flags: string[];
  home_care: string[];
  medicines: Medicine[];
  advice_in_hindi: string;
  suggested_services?: string[];
  diagnosis?: string;
  differential_diagnosis?: string[];
  follow_up_days?: string;
  reassess_if_worsens?: string[];
}

export interface DiagnosisAPIResponse {
  success: boolean;
  data: DiagnosisResult | null;
  error: string | null;
}

export interface HealthResponse {
  status: string;
  mode: "groq" | "nim" | "deepseek";
}

// Stored in localStorage for history
export interface DiagnosisRecord {
  id: string;
  symptoms: string;
  result: DiagnosisResult;
  timestamp: string; // ISO string
}

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