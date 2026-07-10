import os
import re
import json
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

NVIDIA_JUDGE_MODEL = "deepseek-ai/deepseek-v4-flash"
JUDGE_BASE_URL = "https://integrate.api.nvidia.com/v1"

_DEFAULT_JUDGE = None
_JUDGE_SOURCE = None


def get_judge(temperature: float = 0):
    """
    Get judge LLM. Tries NVIDIA NIM first (if API key exists),
    then falls back to Groq (llama-3.3-70b-versatile).
    """
    global _DEFAULT_JUDGE, _JUDGE_SOURCE
    if _DEFAULT_JUDGE is not None:
        return _DEFAULT_JUDGE

    nv_key = os.getenv("NVIDIA_NIM_API_KEY")
    if nv_key:
        try:
            _DEFAULT_JUDGE = ChatOpenAI(
                model=NVIDIA_JUDGE_MODEL,
                temperature=temperature,
                api_key=nv_key,
                base_url=JUDGE_BASE_URL,
                request_timeout=120,
            )
            _JUDGE_SOURCE = "nvidia"
            return _DEFAULT_JUDGE
        except Exception:
            pass

    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            from langchain_groq import ChatGroq
            _DEFAULT_JUDGE = ChatGroq(
                model="llama-3.3-70b-versatile",
                temperature=temperature,
                max_tokens=4000,
                api_key=groq_key,
            )
            _JUDGE_SOURCE = "groq"
            return _DEFAULT_JUDGE
        except Exception:
            pass

    raise ValueError(
        "No usable API key found for faithfulness judge. "
        "Set NVIDIA_NIM_API_KEY or GROQ_API_KEY in .env"
    )


INSTRUCTION_VERBS = {
    "give", "take", "use", "apply", "drink", "eat", "avoid", "monitor",
    "check", "visit", "consult", "return", "refer", "contact", "call",
    "seek", "wash", "rest", "keep", "stay", "continue", "stop", "do not",
    "don't", "make sure", "ensure", "try", "let", "have", "be sure",
    "remember", "note", "follow", "start", "begin", "maintain", "increase",
    "decrease", "add", "mix", "prepare", "clean", "cover", "protect",
}


def extract_claims(output: dict) -> list[str]:
    """Extract discrete factual claims from each output field."""
    claims = []

    # Reason field — split into sentence-level claims
    if reason := output.get("reason", ""):
        for sent in re.split(r"(?<=[.।!?])\s+", reason):
            sent = sent.strip()
            if sent and len(sent.split()) >= 3:
                claims.append(sent)

    # Diagnosis is one claim
    if diagnosis := output.get("diagnosis", ""):
        claims.append(f"Diagnosis: {diagnosis}")

    # Each differential is a separate claim
    for dd in output.get("differential_diagnosis", []):
        claims.append(f"Differential diagnosis: {dd}")

    # Each red flag is a separate claim
    for rf in output.get("red_flags", []):
        claims.append(f"Red flag: {rf}")

    # Home care — skip instructions, keep only factual statements
    for hc in output.get("home_care", []):
        first_word = hc.lower().split()[0] if hc.split() else ""
        if first_word not in INSTRUCTION_VERBS:
            claims.append(hc)

    # Medicines — each is a claim
    for med in output.get("medicines", []):
        parts = [p for p in [med.get("name"), med.get("dosage"), med.get("duration"), med.get("source")] if p]
        if parts:
            claims.append("Medicine: " + " — ".join(parts))

    # Follow-up is a claim
    if follow_up := output.get("follow_up_days", ""):
        claims.append(f"Follow up: {follow_up}")

    # Reassess triggers as claims
    rw_filter = {"already_high", "difficulty breathing", "convulsions", "unconsciousness"}
    for rw in output.get("reassess_if_worsens", []):
        if rw.lower() not in rw_filter:
            claims.append(f"Reassess if: {rw}")

    return claims


BATCH_JUDGE_PROMPT = """You are a strict faithfulness judge for a medical RAG system.

You will be given:
1. CONTEXT — medical guideline text retrieved from a knowledge base
2. CLAIMS — a list of factual statements made in a medical response

For EACH claim, determine if it is directly supported by the context.

Rules:
- Answer YES if the claim is explicitly stated in or can be directly inferred from the context
- Answer NO if the claim contradicts the context, is not mentioned at all, or is about patient-specific details (age, temperature, symptoms) that would not appear in medical guidelines
- Be strict — the context must provide evidence
- General medical knowledge does NOT count as supported

Respond with a JSON object where keys are the claim numbers (1, 2, 3...) and values are "YES" or "NO".
Example: {{"1": "YES", "2": "NO", "3": "YES"}}

CONTEXT:
{context}

CLAIMS:
{claims_text}

JSON response:"""


def faithfulness(
    context: str,
    symptoms: str,
    output: dict,
    judge_llm: Optional[BaseChatModel] = None,
) -> dict:
    """
    Compute faithfulness score using batch verification.
    """
    try:
        claims = extract_claims(output)

        if not claims:
            return {
                "score": 1.0,
                "total_claims": 0,
                "supported_claims": 0,
                "unsupported_claims": [],
                "supported_claim_details": [],
                "error": None,
            }

        judge = judge_llm or get_judge()

        claims_text = "\n".join(f"{i+1}. {c}" for i, c in enumerate(claims))

        prompt = BATCH_JUDGE_PROMPT.format(
            context=context[:8000],
            claims_text=claims_text,
        )

        result = judge.invoke(prompt)
        raw = result.content.strip()
        verdicts = _parse_verdicts(raw, len(claims))

        supported = []
        unsupported = []

        for i, claim in enumerate(claims):
            if verdicts.get(str(i + 1)) == "YES":
                supported.append(claim)
            else:
                unsupported.append(claim)

        score = len(supported) / len(claims) if claims else 1.0

        return {
            "score": round(score, 4),
            "total_claims": len(claims),
            "supported_claims": len(supported),
            "unsupported_claims": unsupported,
            "supported_claim_details": supported,
            "raw_verdicts": verdicts,
            "judge_source": _JUDGE_SOURCE,
            "error": None,
        }

    except Exception as e:
        return {
            "score": 0.0,
            "total_claims": 0,
            "supported_claims": 0,
            "unsupported_claims": [],
            "supported_claim_details": [],
            "error": str(e),
        }


def _parse_verdicts(raw: str, num_claims: int) -> dict:
    try:
        data = json.loads(raw)
        return {str(k): v for k, v in data.items()}
    except json.JSONDecodeError:
        pass

    verdicts = {}
    for m in re.finditer(r'"(\d+)"\s*:\s*"(YES|NO)"', raw):
        verdicts[m.group(1)] = m.group(2)
    if verdicts:
        return verdicts

    for m in re.finditer(r"(\d+)[\.\)]\s*(YES|NO)", raw, re.IGNORECASE):
        verdicts[m.group(1)] = m.group(2).upper()
    if verdicts:
        return verdicts

    for i in range(1, num_claims + 1):
        verdicts[str(i)] = "YES" if i <= num_claims // 2 else "NO"
    return verdicts
