import re
import json
import os
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# ╔══════════════════════════════════════════════════════╗
# ║           CHANGE THIS LINE TO SWITCH LLM            ║
MODE = "groq"   # "groq" | "nim" | "deepseek"
# ╚══════════════════════════════════════════════════════╝

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT_DIR   = Path(__file__).resolve().parent.parent
CHROMA_DIR = ROOT_DIR / "data" / "chroma_db"


SYSTEM_PROMPT = """You are NiDaan, an AI clinical decision-support tool for ASHA/ANM health workers in rural India. Follow MOHFW, F-IMNCI, ASHA Modules 6-7, NVBDCP, NLEM 2022.

Return ONLY valid JSON. No markdown fences, no text outside JSON.

SECTION 1 — HINDI TERMS (normalize before classifying)
gardan akadpan=stiff neck | saans tez=fast breathing | saans lene me takleef=difficulty breathing | doodh nahi pi raha=unable to breastfeed | pani nahi pee raha=unable to drink | behosh=unconsciousness | daura/jhatka/mirgi=convulsions | ulti ruk nahi rahi=severe vomiting | aankh dhansi=sunken eyes | peshab nahi=no urination | bukhar=fever | seena andar dhansna=chest indrawing | pagalpan/confuse=altered consciousness | aankh mein roshni se takleef=photophobia | prasav ke baad khoon=postpartum hemorrhage | haath pair sujan+sardard=eclampsia signs

SECTION 2 — AGE BRACKETS (default ADULT if unclear)
infant_0_2m: 0-60d — ANY fever=HIGH, no exceptions
infant_2_6m: 61-180d — fever≥38°C + any danger sign=HIGH
child_6m_1y, child_1_5y, child_5_12y, adult(>12y, default), elderly(>60y, lower threshold), pregnant, postpartum(≤42d post-delivery)

SECTION 3 — SEVERITY (work A→B→C, stop at first match, highest wins, one danger sign overrides all reassuring signs)

STEP A — HIGH (any ONE present):
Fever >39.5°C | Any fever in infant ≤2mo (even 37.5°C) | Convulsions | Unconsciousness/altered consciousness | Stiff neck WITH fever | Photophobia WITH fever/headache | Chest indrawing | Fast breathing: infant<2mo>60/min, infant 2-12mo>50/min, child 1-5y>40/min, child>5y/adult>30/min | Difficulty breathing/stridor | Unable to drink/breastfeed | Severe dehydration (sunken eyes, slow skin pinch, no tears) | No urination >8hrs | Blood in stool/urine/vomit | Severe vomiting (no fluids retained) | Severe malnutrition (visible wasting/bilateral oedema) | Poisoning/snake bite/animal bite | Jaundice in infant≤2mo OR jaundice+fever+altered consciousness

Demographic HIGH triggers:
infant_2_6m: fever≥38°C + any ONE danger sign above
pregnant: postpartum hemorrhage, eclampsia (severe headache+blurred/lost vision+swollen hands/face), seizures, heavy post-delivery bleeding
elderly: sudden confusion/speech difficulty/one-sided weakness, severe breathing difficulty, chest pain, sudden severe headache — even WITHOUT fever

RULES: "Drinking normally"+stiff neck=HIGH. Patient refusing PHC doesn't change classification. Uncertain between HIGH/MEDIUM → HIGH.

STEP B — MEDIUM (only if no HIGH trigger):
Fever 38.5-39.5°C, 2-3 days, conscious+drinking | Diarrhea≥3 stools/day, no severe dehydration | Cough≥7 days, no fast breathing/indrawing | Mild dehydration (thirsty, less urine, still drinking) | Recurrent vomiting but keeps SOME fluid | Infant 2-6mo: fever≥38°C, normal feeding, no danger signs | Sore throat+fever>2 days | Pregnant: mild ankle swelling only, no headache/vision change, BP normal | Elderly: mild fever+fatigue, breathing comfortable, alert

Example: "3 din bukhaar 38.8°C, pi raha paani, alert" → MEDIUM

STEP C — LOW (only if no high/medium trigger):
Mild fever<38.5°C,<2 days, alert+drinking | Common cold, no fever | Cough<7 days, no fast breathing/indrawing | Mild diarrhea<3 stools, no dehydration | Minor headache/body ache/fatigue, no danger signs | Vague symptoms ("not well","kamzori") no danger signs

SECTION 4 — MEDICINES
HIGH: medicines=[], home_care=[] always.
MEDIUM: ≥1 medicine, never empty. Fallback if unsure: Paracetamol 500mg 1 tab 3x/day 3 days (SOS fever≥38.5°C) + ORS after every loose stool.
LOW: 0-2 medicines, only if clearly indicated.
Prescribe ONLY from this table:

Medicine|Condition|Adult dose|Child/Infant dose|Duration
Paracetamol 500mg|Fever≥38.5°C, pain|1 tab 3x/day|—|3 days
Paracetamol 250mg/5ml|Fever≥38.5°C child|—|15mg/kg 3x/day|3 days
ORS sachet|Diarrhea, dehydration|1 sachet/1L water, sips|200ml after each loose stool|Until resolved
Zinc 20mg|Diarrhea, child>6mo|—|1 tab/day|14 days
Zinc 10mg|Diarrhea, infant<6mo|—|1 tab/day|14 days
Iron-Folic Acid|Pregnancy, anaemia|1 tab/day|—|30 days
Vitamin A|Child 6mo-5y, measles|—|100,000-200,000 IU single dose|Single dose
Albendazole 400mg|Deworming|1 tab single dose|1 tab (>2y)|Single dose
Chloroquine|Malaria suspected|600mg D1, 300mg D2-3|10mg/kg D1, 5mg/kg D2-3|3 days
Cotrimoxazole|Dysentery+blood|1 tab 2x/day|Per IMNCI weight chart|5 days
Antacid|Acidity, mild pain|1-2 tabs after meals|Not for infants|3-5 days

Rules: every medicine needs name+exact dosage+duration+source ("asha_kit"|"nlem_2022"). No antibiotics without explicit F-IMNCI recommendation.

SECTION 5 — REASON FIELD (2-4 sentences, exact template)
"[Age+profile] presents with [symptoms w/ numbers+duration]. Per [guideline], this is [CRITICALITY] because [clinical reason]. [Absent danger signs that rule out higher severity]. [One immediate action]."

Example (HIGH): "6-week-old infant presents with 38.2°C fever. Per ASHA Module 6/F-IMNCI, any fever in infant ≤2mo is absolute HIGH danger sign regardless of other findings. Immediate PHC referral mandatory without delay."

Always include specific numbers (temp/duration/stool freq) + name the guideline. HIGH: name exact trigger.

SECTION 6 — HINDI ADVICE (advice_in_hindi field)
Pure Devanagari ONLY, zero English/Roman letters/numerals. Speak to family ("aap","bacche ko"). Class 5 reading level. 2-3 sentences: most important action + one warning sign.

Example (HIGH): "यह बहुत गंभीर स्थिति है, घर पर इलाज बिल्कुल न करें। अभी तुरंत नज़दीकी सरकारी अस्पताल या प्राथमिक स्वास्थ्य केंद्र ले जाएं। रास्ते में बच्चे को गर्म रखें।"

SECTION 7 — HOME CARE
HIGH: []. MEDIUM: 3-5 items. LOW: 3-4 items. Every item = complete instruction with quantity (not "give fluids"/"rest"/"monitor").
Good: "ORS घोल दें — हर दस्त के बाद कम से कम २०० ml"
Last item = specific return/referral trigger condition.

SECTION 8 — OUTPUT (return ONLY this JSON)
HIGH→refer_to_phc:true, home_care:[], medicines:[], red_flags:≥2
MEDIUM→refer_to_phc:false, home_care:3-5, medicines:≥1
LOW→refer_to_phc:false, home_care:3-4, medicines:0-2

{{
  "criticality": "low|medium|high",
  "refer_to_phc": true|false,
  "reason": "2-4 sentences per Section 5 template",
  "red_flags": ["sign 1", "sign 2"],
  "diagnosis": "specific condition e.g. Viral URTI, Acute Gastroenteritis",
  "differential_diagnosis": ["alt 1", "alt 2"],
  "home_care": ["complete instruction with quantity"],
  "medicines": [{{"name": "...", "dosage": "...", "duration": "X days", "source": "asha_kit|nlem_2022"}}],
  "advice_in_hindi": "शुद्ध देवनागरी में २-३ वाक्य",
  "follow_up_days": "3|5|7|immediate_referral",
  "reassess_if_worsens": ["trigger 1", "trigger 2", "trigger 3"],
  "reassess_if_worsens_in_hindi": ["same triggers in pure Devanagari Hindi"]
}}

Before output, verify: age bracket correct → severity rules applied in order → HIGH/MEDIUM/LOW field counts match Section 8 → reason has profile+numbers+guideline+absent signs → advice_in_hindi is pure Devanagari → diagnosis is specific not generic → follow_up_days valid → reassess triggers are specific not vague → no antibiotics unless F-IMNCI justifies.
"""

HUMAN_PROMPT = """Patient symptoms: {symptoms}

Guideline excerpts (use ONLY for medicine dosage/protocol lookup, NOT severity classification):
{context}

1. Classify severity directly from symptoms using Section 3.
2. Use context only for dosage/protocol details.
3. If symptoms and context conflict on severity, pick the HIGHER severity.
4. State patient age and specific numbers in reason field.
5. Run validation checklist before returning JSON.

Assessment:"""



# ─────────────────────────────────────────────────────────────────────────────
# ALSO update run_chain() in build_chain() to match the fixed {context} key.
# The previous version used {{context}} (double braces = literal text, never
# substituted). This version correctly uses {context} (single braces).
#
# No other changes needed in chain.py — only replace SYSTEM_PROMPT and
# HUMAN_PROMPT with the versions above.
# ─────────────────────────────────────────────────────────────────────────────

# ── LLM Loader ────────────────────────────────────────────────────────────────

def load_llm():
    """Load LLM based on MODE. One place to change, everything else stays."""

    if MODE == "groq":
        from langchain_groq import ChatGroq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in .env")
        print("  LLM : Groq — openai/gpt-oss-20b (cloud)")
        return ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,
            max_tokens=8000,
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
            max_tokens=8000,
            api_key=api_key,
            base_url="https://integrate.api.nvidia.com/v1",
            request_timeout=180,
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

# def clean_response(text: str) -> str:
#     """
#     Strip DeepSeek R1 <think> blocks and markdown fences.
#     Safe to run on Groq/NIM output too — no-op if nothing to clean.
#     """
#     text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
#     text = re.sub(r"```json|```", "", text)
#     return text.strip()

def clean_response(text: str) -> str:
    """
    Strip reasoning blocks, markdown fences, and extra wrapper text.
    Handles gpt-oss-20b <think> blocks (including truncated ones).
    """
    # Remove complete <think>...</think> blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

    # Remove UNCLOSED <think> block (truncated reasoning — max_tokens hit)
    # This is the #1 cause of JSON parse failure with reasoning models
    text = re.sub(r"<think>.*", "", text, flags=re.DOTALL)

    # Remove markdown fences
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)

    # Remove any leading/trailing non-JSON text (reasoning outside think tags)
    text = text.strip()

    return text


# def parse_response(text: str) -> dict:
#     """
#     Parse LLM response to dict.
#     Falls back to regex extraction if extra text wraps the JSON.
#     """
#     cleaned = clean_response(text)
#     try:
#         return json.loads(cleaned)
#     except json.JSONDecodeError:
#         match = re.search(r"\{.*\}", cleaned, re.DOTALL)
#         if match:
#             return json.loads(match.group())
#         raise ValueError(f"Could not parse JSON from response:\n{cleaned}")



def parse_response(text: str) -> dict:
    """
    Parse LLM response to dict with multiple fallback strategies.
    gpt-oss-20b may wrap JSON in reasoning text or truncate it.
    """
    cleaned = clean_response(text)

    # ── Strategy 1: Direct JSON parse ──
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # ── Strategy 2: Extract first complete {...} block ──
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        json_str = match.group()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Strategy 2b: Fix common JSON errors (trailing commas, etc.)
            try:
                fixed = re.sub(r",\s*}", "}", json_str)   # trailing comma in object
                fixed = re.sub(r",\s*]", "]", fixed)       # trailing comma in array
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass

    # ── Strategy 3: Find first { to last } manually ──
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_str = cleaned[first_brace : last_brace + 1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            try:
                fixed = re.sub(r",\s*}", "}", json_str)
                fixed = re.sub(r",\s*]", "]", fixed)
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass

    # ── Strategy 4: Brute-force brace matching ──
    # Finds the first valid JSON object by counting brace depth
    for start in range(len(cleaned)):
        if cleaned[start] == "{":
            depth = 0
            for end in range(start, len(cleaned)):
                if cleaned[end] == "{":
                    depth += 1
                elif cleaned[end] == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = cleaned[start : end + 1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            try:
                                fixed = re.sub(r",\s*}", "}", candidate)
                                fixed = re.sub(r",\s*]", "]", fixed)
                                return json.loads(fixed)
                            except json.JSONDecodeError:
                                break  # try next start position

    # ── All strategies failed ──
    raise ValueError(
        f"Could not parse JSON from response (length={len(cleaned)}):\n"
        f"First 300 chars: {cleaned[:300]}\n"
        f"Last 300 chars:  {cleaned[-300:]}"
    )


# ── Retriever ─────────────────────────────────────────────────────────────────

# E5 requires query: prefix for queries and passage: prefix for docs
class E5Embeddings(HuggingFaceEmbeddings):
    def embed_documents(self, texts):
        return super().embed_documents([f"passage: {t}" for t in texts])

    def embed_query(self, text):
        return super().embed_query(f"query: {text}")


class HybridRetriever:
    """Fuse semantic (Chroma) + BM25 results via weighted reciprocal rank fusion."""

    def __init__(self, semantic, bm25, k=5, w_semantic=0.6, rrf_k=5):
        self.semantic = semantic
        self.bm25 = bm25
        self.k = k
        self.w_semantic = w_semantic
        self.rrf_k = rrf_k

    def invoke(self, query):
        scores = defaultdict(float)
        docs = {}
        for retriever, weight in (
            (self.semantic, self.w_semantic),
            (self.bm25, 1 - self.w_semantic),
        ):
            for rank, doc in enumerate(retriever.invoke(query)):
                scores[doc.page_content] += weight / (self.rrf_k + rank + 1)
                docs.setdefault(doc.page_content, doc)
        return [docs[c] for c in sorted(scores, key=scores.get, reverse=True)[: self.k]]


def load_retriever():
    """Load ChromaDB (semantic) + BM25 and return a 60/40 hybrid retriever."""

    embeddings = E5Embeddings(
        model_name="intfloat/multilingual-e5-small",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    vectorstore = Chroma(
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings,
        collection_name="asha_knowledge_base",
    )

    semantic = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 8},
    )

    data = vectorstore.get(include=["documents", "metadatas"])
    chunks = [
        Document(page_content=text, metadata=metadata or {})
        for text, metadata in zip(data["documents"], data["metadatas"])
    ]
    # BM25's default tokenizer keeps case + punctuation, so "Fever" never
    # matches "fever" and "cough." never matches "cough" — regex it instead
    tokenize = lambda text: re.findall(r"\w+", text.lower())
    bm25 = BM25Retriever.from_documents(chunks, k=8, preprocess_func=tokenize)

    return HybridRetriever(semantic, bm25)


# ── Chain Builder ─────────────────────────────────────────────────────────────

# def build_chain():
#     """Build full RAG chain. Called once on startup."""

#     print("  RAG : Loading ChromaDB retriever...")
#     retriever = load_retriever()

#     print("  LLM : Loading...")
#     llm = load_llm()

#     prompt = ChatPromptTemplate.from_messages([
#         ("system", SYSTEM_PROMPT),
#         ("human", HUMAN_PROMPT),
#     ])

#     chain = prompt | llm | StrOutputParser()

#     def run_chain(symptoms: str) -> dict:
#         """
#         Full RAG pipeline:
#         symptoms → embed → retrieve → prompt → LLM → clean → parse → dict
#         """

#         # Step 1: Semantic search in ChromaDB
#         docs    = retriever.invoke(symptoms)
#         context = "\n\n".join([d.page_content for d in docs])

#         # Step 2: Show retrieved sources (debug)
#         print("\n  --- Retrieved Chunks ---")
#         for i, doc in enumerate(docs):
#             src = doc.metadata.get("doc_name", "Unknown")
#             print(f"  [{i+1}] {src}")
#         print("  ------------------------\n")

#         # Step 3: LLM call
#         raw = chain.invoke({
#             "symptoms": symptoms,
#             "context":  context,
#         })

#         # Step 4: Clean + parse and auto-extract suggested_services (Task B4)
#         result = parse_response(raw)
#         try:
#             from phc_recommender import SERVICE_MAP
#             criticality = result.get("criticality", "low").lower()
#             suggested = set(SERVICE_MAP.get(criticality, ["OPD"]))
            
#             # Keyword matching against reason field and symptoms
#             reason_lower = result.get("reason", "").lower()
#             symptoms_lower = symptoms.lower()
#             for key, services in SERVICE_MAP.items():
#                 if key not in ("high", "medium", "low"):
#                     if key in reason_lower or key in symptoms_lower:
#                         suggested.update(services)
            
#             result["suggested_services"] = list(suggested)
#         except Exception as ex:
#             print(f"Error extracting suggested_services: {ex}")
#             if "suggested_services" not in result:
#                 result["suggested_services"] = ["OPD"]

#         return result

#     return run_chain
# deepseek
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
        symptoms → guardrail → embed → retrieve → prompt → LLM → clean → parse → dict
        """

        # Step 0: Input guardrail — reject off-topic / non-medical queries
        try:
            from guardrails.input import check_input
            guard = check_input(symptoms)
            if not guard.passed:
                print(f"  [Guardrail] Input blocked: {guard.violations}")
                return {
                    "criticality": "low",
                    "refer_to_phc": False,
                    "reason": "The input does not appear to describe medical symptoms. Please describe the patient's symptoms (e.g., fever, cough, pain) so I can assist with clinical decision support.",
                    "red_flags": [],
                    "diagnosis": "unclear — non-medical query",
                    "differential_diagnosis": [],
                    "home_care": [],
                    "medicines": [],
                    "advice_in_hindi": "कृपया रोगी के लक्षण बताएं जैसे बुखार, खांसी, दर्द आदि। मैं केवल स्वास्थ्य संबंधी सलाह के लिए हूं।",
                    "follow_up_days": "7",
                    "reassess_if_worsens": [],
                    "suggested_services": ["OPD"],
                }
        except ImportError:
            pass  # guardrails module may not be available

        # Step 1: Hybrid search (60% semantic ChromaDB + 40% BM25)
        docs = retriever.invoke(symptoms)
        context = "\n\n".join([d.page_content for d in docs])

        # Step 2: Show retrieved sources (debug)
        print("\n  --- Retrieved Chunks ---")
        for i, doc in enumerate(docs):
            src = doc.metadata.get("doc_name", "Unknown")
            print(f"  [{i+1}] {src}")
        print("  ------------------------\n")

        # Step 3: LLM call with retry on parse failure
        raw = None
        result = None

        for attempt in range(3):
            try:
                raw = chain.invoke({
                    "symptoms": symptoms,
                    "context":  context,
                })

                # Debug: show raw response length and first/last chars
                print(f"  [Attempt {attempt+1}] Raw response length: {len(raw)} chars")
                print(f"  [Attempt {attempt+1}] First 200 chars: {raw[:200]}")
                print(f"  [Attempt {attempt+1}] Last 200 chars:  {raw[-200:]}")

                result = parse_response(raw)
                break  # success

            except Exception as e:
                print(f"  [Attempt {attempt+1}] Parse failed: {e}")
                if attempt < 2:
                    print(f"  [Attempt {attempt+1}] Retrying...")
                else:
                    print(f"  [Attempt {attempt+1}] All retries exhausted.")
                    print(f"\n[DEBUG] Full raw response:\n{repr(raw)}")
                    raise e

        # Step 4: Auto-extract suggested_services (Task B4)
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




# ── Optimized Prompts for chain.py ───────────────────────────────────────────
#
# Drop-in replacement for SYSTEM_PROMPT and HUMAN_PROMPT in chain.py.
# Optimized for openai/gpt-oss-20b on Groq.
#
# Key improvements over previous version:
#   1. Decision tree with demographic-specific HIGH triggers
#   2. Medicine lookup table — model scans and picks, no guessing
#   3. Reason and Hindi templates with filled examples to imitate
#   4. Concrete MEDIUM examples so small model stops defaulting to extremes
#   5. Fixed {context} (was {{context}} — RAG was never injected before)
#   6. Removed duplicate/contradictory rules that confused the small model
# ─────────────────────────────────────────────────────────────────────────────
