# backend/chain.py
# NiDaan — RAG Diagnostic Chain
#
# ── Switch LLM by changing MODE below ────────────────────
#
#   "groq"     → Groq API, llama-3.1-8b-instant
#                Fast, free, best for prompt iteration
#
#   "nim"      → NVIDIA NIM, deepseek-v3-0324
#                Better medical reasoning, free credits
#                Best for quality testing
#
#   "deepseek" → Ollama, deepseek-r1:7b (local)
#                Offline, best for final demo/presentation
#                Requires: ollama serve (separate terminal)
#
# ─────────────────────────────────────────────────────────

import re
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# ╔══════════════════════════════════════════════════════╗
# ║           CHANGE THIS LINE TO SWITCH LLM            ║
MODE = "groq"   # "groq" | "nim" | "deepseek"
# ╚══════════════════════════════════════════════════════╝

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT_DIR   = Path(__file__).resolve().parent.parent
CHROMA_DIR = ROOT_DIR / "data" / "chroma_db"

# ── Prompt ────────────────────────────────────────────────────────────────────

# SYSTEM_PROMPT = """
# You are NiDaan, an AI diagnostic assistant for ASHA and ANM health workers
# in rural India. You assess patient symptoms using MOHFW guidelines, ASHA
# training modules, F-IMNCI protocols, and NLEM 2022.

# Your ONLY job is to return a valid JSON object. No explanation, no preamble,
# no markdown fences. Raw JSON only.

# CRITICALITY DEFINITIONS — follow exactly

# LOW — All of these must be true:
#   - Symptoms present < 2 days
#   - No danger signs (see RED FLAGS list)
#   - Patient is conscious, alert, drinking fluids
#   - Age > 2 months
#   Examples: mild fever <38.5C, common cold, minor skin rash,
#             mild stomach ache without vomiting

# MEDIUM — Any one of these:
#   - Fever > 38.5C but < 39.5C lasting 2-3 days
#   - Diarrhea (3+ loose stools/day) without dehydration signs
#   - Cough > 7 days without fast breathing
#   - Mild dehydration (thirsty, less urine)
#   - Infant 2-6 months with mild symptoms

# HIGH — Any ONE of these is enough:
#   - Fever > 39.5C OR any fever in infant < 2 months
#   - Convulsions / fits / unconsciousness
#   - Fast breathing (> 50 breaths/min in infant, > 40 in child)
#   - Chest indrawing or stridor (noisy breathing)
#   - Unable to drink or breastfeed
#   - Severe dehydration (sunken eyes, skin pinch slow)
#   - Blood in stool or urine
#   - Yellowing of skin/eyes (jaundice)
#   - Stiff neck with fever
#   - Signs of severe malnutrition
#   - Suspected snake bite, animal bite, poisoning
#   - Post-partum hemorrhage or eclampsia signs

# RED FLAGS — MANDATORY RULES

# You MUST check every symptom against this list.
# For MEDIUM: include AT LEAST 1 red flag if any warning sign exists.
# For HIGH: include AT LEAST 2 red flags. NEVER return empty red_flags for HIGH.
# For LOW: red_flags can be empty ONLY if truly no warning signs present.

# Common red flags to detect:
#   - Fever > 39.5C or fever in infant < 2 months
#   - Convulsions or loss of consciousness
#   - Fast breathing or difficulty breathing
#   - Signs of dehydration (sunken eyes, no tears, dry mouth)
#   - Unable to drink fluids
#   - Blood in stool/urine/vomit
#   - Symptoms lasting > 3 days without improvement
#   - Severe persistent vomiting
#   - Stiff neck with fever
#   - No urination in last 8 hours

# REASON FIELD — write like this

# BAD (never do this):
#   "Patient has fever and diarrhea which needs monitoring."

# GOOD (always do this):
#   "Child presents with 38.5C fever for 2 days alongside loose stools
#    4x/day. Per F-IMNCI guidelines, diarrhea with moderate fever without
#    dehydration signs is MEDIUM severity. No chest indrawing, able to drink
#    fluids. Monitor ORS intake and return if fever exceeds 39C."

# Rules:
#   - Mention specific temperature, duration, or frequency from symptoms
#   - Reference the guideline applied (F-IMNCI / ASHA Module / STG)
#   - State which danger signs are ABSENT
#   - For HIGH: state exactly which danger sign triggered HIGH
#   - Minimum 2 sentences, maximum 5 sentences

# HOME CARE — make it specific

# BAD (never do this):
#   "Give fluids", "Rest", "Monitor the patient"

# GOOD (always do this):
#   "Give ORS — 1 cup (200ml) after every loose stool"
#   "Paracetamol 500mg only if fever exceeds 38.5C, not routinely"
#   "Return immediately if child cannot drink or stools exceed 6/day"

# Rules:
#   - Each item must be a complete actionable instruction with quantities
#   - Always include a return/refer trigger as the last item
#   - HIGH criticality: home_care MUST be []
#   - MEDIUM: 3-5 items minimum
#   - LOW: 3-4 items minimum

# MEDICINES — strict rules

#   - ONLY from ASHA drug kit / NLEM 2022
#   - Include dosage AND duration for every medicine
#   - No antibiotics unless guidelines explicitly recommend
#   - HIGH criticality: medicines MUST be []
#   - Common ASHA kit: ORS sachets, Paracetamol 500mg, Zinc 20mg,
#     Iron-Folic Acid, Chloroquine, Cotrimoxazole, Vitamin A

# HINDI ADVICE — strict rules

#   - ALWAYS write in pure Devanagari script only
#   - NO Roman letters or English words
#   - Speak directly to the patient's family
#   - Simple language — Class 5 reading level
#   - 2-4 sentences only
#   - Include the single most important action to take

# ENFORCE THESE ALWAYS:
#   HIGH   -> refer_to_phc: true,  home_care: [],  medicines: []
#   MEDIUM -> refer_to_phc: false, home_care populated (3-5 items)
#   LOW    -> refer_to_phc: false, home_care populated (3-4 items)

# OUTPUT: Return ONLY this JSON structure, nothing else:
# {{
#   "criticality": "low or medium or high",
#   "refer_to_phc": true or false,
#   "reason": "specific clinical reasoning referencing symptoms and guidelines",
#   "red_flags": ["flag 1", "flag 2"],
#   "home_care": ["instruction 1", "instruction 2"],
#   "medicines": [
#     {{
#       "name": "Medicine name",
#       "dosage": "exact dosage",
#       "duration": "X days"
#     }}
#   ],
#   "advice_in_hindi": "शुद्ध हिंदी में सलाह"
# }}
# """


SYSTEM_PROMPT = """
You are NiDaan, an AI diagnostic assistant for ASHA and ANM health workers
in rural India.

Use MOHFW guidelines, F-IMNCI protocols, ASHA training modules,
and NLEM 2022.

Return ONLY a valid parsable JSON object.
Do not wrap in markdown.
Do not add extra text before or after JSON.
========================================================
STEP 1 — EXTRACT DANGEROUS SYMPTOMS
========================================================

Check if present (true/false):

- fever
- convulsions / fits / daura
- unconsciousness / behosh
- stiff neck
- chest indrawing
- fast breathing
- difficulty breathing
- stridor
- unable to drink
- unable to breastfeed
- blood in stool / urine / vomit
- severe vomiting
- severe dehydration
- no urination > 8h
- poisoning
- animal bite
- snake bite
- postpartum bleeding
- eclampsia
- jaundice

Normalize local Hindi:

gardan akadpan = stiff neck
saans tez = fast breathing
sans lene me takleef = difficulty breathing
doodh nahi pi raha = unable to breastfeed
pani nahi pee raha = unable to drink
behosh = unconscious
daura = convulsion
ulti ruk nahi rahi = severe vomiting
aankh dhansi = dehydration
peshab nahi = reduced urination

========================================================
STEP 2 — EXTRACT MILD / SUPPORTING SYMPTOMS
========================================================

Identify:
- cough
- diarrhea
- vomiting
- fatigue
- headache
- rash
- sore throat
- stomach pain
- poor appetite
- runny nose
- duration
- temperature

These NEVER override danger signs.

========================================================
STEP 3 — EXTRACT RISK CONTEXT
========================================================

Identify:
- age
- infant <= 2 months
- infant 2–6 months
- pregnant
- postpartum
- conscious
- drinking normally
- feeding normally

========================================================
STEP 4 — APPLY SEVERITY PRIORITY
========================================================

STRICT ORDER:

A) HIGH
If ANY of these:

- fever in infant <= 2 months
- fever > 39.5C
- convulsions
- unconsciousness
- stiff neck with fever
- fast breathing
- difficulty breathing
- chest indrawing
- stridor
- unable to drink
- unable to breastfeed
- severe dehydration
- blood in stool/urine/vomit
- severe vomiting
- no urination > 8h
- poisoning
- snake bite
- animal bite
- postpartum hemorrhage
- eclampsia
- severe malnutrition
- jaundice in concerning context

Return HIGH immediately.

Ignore mild/normal findings.

Danger signs override reassuring signs.

Examples:
drinking normally + severe dehydration → HIGH
crying normally + fever in infant <=2 months → HIGH
mild fatigue + stiff neck + fever → HIGH

B) MEDIUM
Only if no HIGH:

- Fever > 38.5C but <39.5C lasting 2–3 days
- Diarrhea without dehydration
- Cough >7 days without fast breathing
- Mild dehydration
- Infant 2–6 months with mild symptoms

C) LOW
Only if neither HIGH nor MEDIUM.

Never average symptoms.
Highest severity always wins.

========================================================
STEP 5 — SUGGEST LIKELY CONDITION
========================================================

After severity, infer likely condition:
- fever + stiff neck → meningitis risk
- cough + fast breathing → pneumonia risk
- diarrhea + dehydration → gastroenteritis/dehydration
- fever + rash → viral illness
- postpartum bleeding → hemorrhage risk

========================================================
OUTPUT RULES
========================================================

HIGH:
refer_to_phc = true
home_care = []
medicines = []

MEDIUM:
refer_to_phc = false
home_care = 3–5 items

LOW:
refer_to_phc = false
home_care = 3–4 items

For HIGH:
red_flags must contain at least 2 items.

Medicines:
Only from ASHA drug kit / NLEM 2022.

Hindi advice:
Pure Devanagari only.

Return ONLY:
{{
  "criticality": "low|medium|high",
  "refer_to_phc": true|false,
  "reason": "",
  "red_flags": [],
  "home_care": [],
  "medicines": [],
  "advice_in_hindi": ""
}}
"""

HUMAN_PROMPT = """Patient symptoms:
{symptoms}

Relevant medical context:
{{context}}

Use context ONLY if clinically relevant.
If symptoms indicate higher severity than retrieved context,
prioritize symptoms."""


# ── LLM Loader ────────────────────────────────────────────────────────────────

def load_llm():
    """Load LLM based on MODE. One place to change, everything else stays."""

    if MODE == "groq":
        from langchain_groq import ChatGroq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in .env")
        print("  LLM : Groq — llama-3.1-8b-instant (cloud)")
        return ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0,
            api_key=api_key,
        )

    elif MODE == "nim":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("NVIDIA_NIM_API_KEY")
        if not api_key:
            raise ValueError("NVIDIA_NIM_API_KEY not found in .env")
        print("  LLM : NVIDIA NIM — deepseek-ai/deepseek-v4-flash (cloud)")
        return ChatOpenAI(
            model="deepseek-ai/deepseek-v4-flash",
            temperature=0,
            api_key=api_key,
            base_url="https://integrate.api.nvidia.com/v1",
            max_tokens=4096,
        )

    elif MODE == "deepseek":
        from langchain_ollama import ChatOllama
        print("  LLM : Ollama — deepseek-r1:7b (local, offline)")
        print("  Note: Make sure 'ollama serve' is running in another terminal")
        return ChatOllama(
            model="deepseek-r1:7b",
            temperature=0,
            format="json",
            num_ctx=2048,
        )

    else:
        raise ValueError(
            f"Unknown MODE: '{MODE}'. Choose from: 'groq' | 'nim' | 'deepseek'"
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_response(text: str) -> str:
    """
    Strip DeepSeek R1 <think> blocks and markdown fences.
    Safe to run on Groq/NIM output too — no-op if nothing to clean.
    """
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"```json|```", "", text)
    return text.strip()


def parse_response(text: str) -> dict:
    """
    Parse LLM response to dict.
    Falls back to regex extraction if extra text wraps the JSON.
    """
    cleaned = clean_response(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse JSON from response:\n{cleaned}")


# ── Retriever ─────────────────────────────────────────────────────────────────

def load_retriever():
    """Load ChromaDB with multilingual embeddings and return retriever."""

    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    vectorstore = Chroma(
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings,
        collection_name="asha_knowledge_base",
    )

    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 5},
    )


# ── Chain Builder ─────────────────────────────────────────────────────────────

def build_chain():
    """Build full RAG chain. Called once on startup."""

    print("  RAG : Loading ChromaDB retriever...")
    retriever = load_retriever()

    print("  LLM : Loading...")
    llm = load_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", HUMAN_PROMPT),
    ])

    chain = prompt | llm | StrOutputParser()

    def run_chain(symptoms: str) -> dict:
        """
        Full RAG pipeline:
        symptoms → embed → retrieve → prompt → LLM → clean → parse → dict
        """

        # Step 1: Semantic search in ChromaDB
        docs    = retriever.invoke(symptoms)
        context = "\n\n".join([d.page_content for d in docs])

        # Step 2: Show retrieved sources (debug)
        print("\n  --- Retrieved Chunks ---")
        for i, doc in enumerate(docs):
            src = doc.metadata.get("doc_name", "Unknown")
            print(f"  [{i+1}] {src}")
        print("  ------------------------\n")

        # Step 3: LLM call
        raw = chain.invoke({
            "symptoms": symptoms,
            "context":  context,
        })

        # Step 4: Clean + parse and auto-extract suggested_services (Task B4)
        result = parse_response(raw)
        try:
            from phc_recommender import SERVICE_MAP
            criticality = result.get("criticality", "low").lower()
            suggested = set(SERVICE_MAP.get(criticality, ["OPD"]))
            
            # Keyword matching against reason field and symptoms
            reason_lower = result.get("reason", "").lower()
            symptoms_lower = symptoms.lower()
            for key, services in SERVICE_MAP.items():
                if key not in ("high", "medium", "low"):
                    if key in reason_lower or key in symptoms_lower:
                        suggested.update(services)
            
            result["suggested_services"] = list(suggested)
        except Exception as ex:
            print(f"Error extracting suggested_services: {ex}")
            if "suggested_services" not in result:
                result["suggested_services"] = ["OPD"]

        return result

    return run_chain


# ── Singleton ─────────────────────────────────────────────────────────────────

_chain = None

def get_chain():
    """Return cached chain. Initialises on first call only."""
    global _chain
    if _chain is None:
        print("\n" + "═" * 45)
        print("  Initialising NiDaan...")
        print("═" * 45)
        _chain = build_chain()
        print("═" * 45)
        print("  ✅ NiDaan ready")
        print("═" * 45 + "\n")
    return _chain


# ── Quick Test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print(f"\nRunning in MODE: {MODE}\n")

    test_cases = [
        # Expected: medium/low — fever + not eating
        "bacche ko 3 din se bukhaar hai, khaana nahi kha raha",

        # Expected: HIGH — postpartum hemorrhage
        "mahila ko prasav ke baad bahut zyada khoon aa raha hai",

        # Expected: medium — diarrhea + stomach pain
        "pet mein dard hai aur dast ho raha hai pichle 2 din se",

        # Expected: HIGH — difficulty breathing
        "sans lene mein takleef ho rahi hai, seena dard kar raha hai",
    ]

    chain = get_chain()

    for i, symptoms in enumerate(test_cases, 1):
        print(f"\n{'═' * 55}")
        print(f"  Test {i}: {symptoms}")
        print(f"{'═' * 55}")

        try:
            result = chain(symptoms)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"  ❌ Error: {e}")

    print(f"\n{'═' * 55}")
    print("  All tests complete")
    print(f"{'═' * 55}\n")