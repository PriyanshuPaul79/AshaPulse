/// <reference types="vite/client" />

// Central API layer — all backend calls go through here
// Components never call fetch() directly

import type {
  DiagnosisAPIResponse,
  DiagnosisResult,
  HealthResponse,
  PHCRecommendationRequest,
  PHCRecommendationResponse,
  PHCResult,
} from "../types/nidaan";

const API_BASE =
  import.meta.env.VITE_API_URL || "http://localhost:8000";

const SESSION_KEY = "nidaan_session";

// ─── Health check ────────────────────────────────────────────────
export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`, {
    method: "GET",
    signal: AbortSignal.timeout(5000), // 5s timeout for health check
  });

  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`);
  }

  return res.json();
}

// ─── Main diagnosis call ─────────────────────────────────────────
export async function diagnose(symptoms: string): Promise<DiagnosisResult> {
  const res = await fetch(`${API_BASE}/diagnose`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symptoms }),
    signal: AbortSignal.timeout(300_000), // 300s — covers Ollama local inference
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Diagnosis failed (${res.status}): ${errorText}`);
  }

  const json: DiagnosisAPIResponse = await res.json();

  if (!json.success || !json.data) {
    throw new Error(json.error || "Unknown error from backend");
  }

  return json.data;
}

// ─── Session storage helpers ─────────────────────────────────────
// Used to pass result from home page → result page

const RESULT_KEY = "nidaan_last_result";
const SYMPTOMS_KEY = "nidaan_last_symptoms";

export function saveResultToSession(
  symptoms: string,
  result: DiagnosisResult,
  isRevisit = false   // ← new flag
): void {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify({ symptoms, result, isRevisit }));
}


export function loadResultFromSession(): {
  symptoms: string;
  result: DiagnosisResult;
  isRevisit: boolean;
} | null {
  const raw = sessionStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

// ─── localStorage history helpers ────────────────────────────────

import type { DiagnosisRecord } from "../types/nidaan";

const HISTORY_KEY = "nidaan_history";
const MAX_HISTORY = 20;

export function getHistory(): DiagnosisRecord[] {
  if (typeof window === "undefined") return [];
  const raw = localStorage.getItem(HISTORY_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as DiagnosisRecord[];
  } catch {
    return [];
  }
}

  export function saveToHistory(
  symptoms: string,
  result: DiagnosisResult
): void {
  const history = getHistory();

  // Deduplicate: skip if identical symptoms saved within last 60 seconds
  const alreadySaved = history.some(r =>
    r.symptoms.trim() === symptoms.trim() &&
    Date.now() - new Date(r.timestamp).getTime() < 60_000
  );
  if (alreadySaved) return;

  const newRecord: DiagnosisRecord = {
    id: crypto.randomUUID(),
    symptoms,
    result,
    timestamp: new Date().toISOString(),
  };
  const updated = [newRecord, ...history].slice(0, MAX_HISTORY);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
}
// export function saveToHistory(
//   symptoms: string,
//   result: DiagnosisResult
// ): void {
//   const history = getHistory();

//   const newRecord: DiagnosisRecord = {
//     id: crypto.randomUUID(),
//     symptoms,
//     result,
//     timestamp: new Date().toISOString(),
//   };

//   // Prepend new record, evict oldest if over limit
//   const updated = [newRecord, ...history].slice(0, MAX_HISTORY);
//   localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
// }

export function clearHistory(): void {
  localStorage.removeItem(HISTORY_KEY);
}

export async function recommendPHCs(
  request: PHCRecommendationRequest
): Promise<PHCResult[]> {
  const res = await fetch(`${API_BASE}/recommend-phc`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal: AbortSignal.timeout(10000), // 10s timeout
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`PHC Recommendation failed (${res.status}): ${errorText}`);
  }

  const json: PHCRecommendationResponse = await res.json();

  if (!json.success || !json.recommendations) {
    throw new Error(json.error || "Unknown error from backend during PHC lookup");
  }

  return json.recommendations;
}