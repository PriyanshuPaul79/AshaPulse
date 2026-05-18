

# backend/chain.py
# RAG + DeepSeek R1:7b + Structured Output chain

import re
import json
from pathlib import Path
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from schemas import ASHAResponse

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT_DIR   = Path(__file__).resolve().parent.parent
CHROMA_DIR = ROOT_DIR / "data" / "chroma_db"

# ── Prompt ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are NiDaan — an AI assistant helping ASHA (Accredited Social Health Activist)
workers in rural India. ASHA workers have basic medical training and carry a limited drug kit.

Your job is to analyze patient symptoms and return a structured JSON assessment.

STRICT RULES:
1. Only recommend medicines from the ASHA drug kit:
   ORS, Zinc, Paracetamol, IFA (Iron Folic Acid), Vitamin A, Cotrimoxazole,
   Oral Contraceptive Pills, Misoprostol, Chlorhexidine, Albendazole
2. HIGH criticality → refer_to_phc must be true, home_care can be empty
3. LOW criticality  → refer_to_phc must be false, give detailed home_care
4. MEDIUM          → refer_to_phc false, monitor at home, visit if worsens
5. red_flags must be specific danger signs ASHA should watch for
6. advice_in_hindi must be simple Hindi, no medical jargon
7. Use the provided medical context to guide your assessment
8. Return ONLY raw JSON — no explanation, no markdown, no text before or after

CONTEXT FROM MEDICAL GUIDELINES:
{context}

Return this exact JSON structure:
{{
  "criticality": "low" | "medium" | "high",
  "refer_to_phc": true | false,
  "reason": "one line explanation of criticality level",
  "red_flags": ["danger sign 1", "danger sign 2"],
  "home_care": ["step 1", "step 2", "step 3"],
  "medicines": [
    {{
      "name": "medicine name and strength",
      "dosage": "how much and how often",
      "duration": "for how many days"
    }}
  ],
  "advice_in_hindi": "सरल हिंदी में मरीज के लिए सलाह"
}}"""

HUMAN_PROMPT = "Patient symptoms: {symptoms}"


# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_response(text: str) -> str:
    """
    Remove DeepSeek R1 <think>...</think> blocks
    and any markdown fences before JSON parsing.
    """
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"```json|```", "", text)
    return text.strip()


def parse_response(text: str) -> dict:
    """Parse cleaned LLM response into dict."""
    cleaned = clean_response(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse JSON from response:\n{cleaned}")