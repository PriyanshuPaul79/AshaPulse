import re
import numpy as np
from typing import Optional
from sentence_transformers import SentenceTransformer, util


_EMBEDDING_MODEL: Optional[SentenceTransformer] = None


def _get_embedder() -> SentenceTransformer:
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        _EMBEDDING_MODEL = SentenceTransformer("intfloat/multilingual-e5-small")
    return _EMBEDDING_MODEL


def _symptoms_to_english(symptoms: str) -> str:
    """Normalize Hindi + English symptoms into a clean English-like string for embedding."""
    symptom_text = symptoms.lower().strip()
    return symptom_text


def _extract_output_text(output: dict) -> str:
    """Concatenate clinically relevant output fields into a flat string."""
    parts = []
    if diagnosis := output.get("diagnosis"):
        parts.append(f"diagnosis: {diagnosis}")
    for dd in output.get("differential_diagnosis", []):
        parts.append(f"differential: {dd}")
    if reason := output.get("reason"):
        parts.append(f"reason: {reason}")
    if criticality := output.get("criticality"):
        parts.append(f"criticality: {criticality}")
    if follow_up := output.get("follow_up_days"):
        parts.append(f"follow_up: {follow_up}")
    for hc in output.get("home_care", []):
        parts.append(f"home_care: {hc}")
    for med in output.get("medicines", []):
        parts.append(f"medicine: {med.get('name', '')}")
    for rf in output.get("red_flags", []):
        parts.append(f"red_flag: {rf}")
    return " ".join(parts)


def answer_relevancy(
    context: str,
    symptoms: str,
    output: dict,
    embedder: Optional[SentenceTransformer] = None,
) -> dict:
    """
    Compute answer relevancy using cosine similarity between symptom embedding
    and output embedding.
    """
    try:
        embedder = embedder or _get_embedder()

        symptom_text = _symptoms_to_english(symptoms)
        output_text = _extract_output_text(output)

        if not symptom_text.strip() or not output_text.strip():
            return {"score": 0.0, "error": "Empty symptoms or output"}

        emb_symptom = embedder.encode(f"query: {symptom_text}", convert_to_tensor=True)
        emb_output = embedder.encode(f"passage: {output_text}", convert_to_tensor=True)

        cosine_score = float(util.cos_sim(emb_symptom, emb_output)[0][0])

        normalized = max(0.0, min(1.0, (cosine_score + 1.0) / 2.0))

        return {
            "score": round(normalized, 4),
            "raw_cosine": round(float(cosine_score), 4),
            "symptom_length": len(symptom_text.split()),
            "output_length": len(output_text.split()),
            "error": None,
        }

    except Exception as e:
        return {"score": 0.0, "error": str(e)}
