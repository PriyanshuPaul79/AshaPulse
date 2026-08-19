import re
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Load environment variables
load_dotenv()

# ╔══════════════════════════════════════════════════════╗
# ║           CHANGE THIS LINE TO SWITCH LLM            ║
MODE = "groq"   # "groq" | "nim" | "deepseek"
# ╚══════════════════════════════════════════════════════╝

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT_DIR   = Path(__file__).resolve().parent.parent
CHROMA_DIR = ROOT_DIR / "data" / "chroma_db"

# ── Optimized & Reduced Prompts ──────────────────────────────────────────────
SYSTEM_PROMPT = """You are NiDaan, an AI clinical decision-support tool for ASHA/ANM workers in rural India. Follow MOHFW, F-IMNCI, ASHA Modules 6-7, NLEM 2022. Return ONLY valid JSON. No markdown, no extra text.

1. HINDI NORMALIZATION: gardan akadpan=stiff neck | saans tez=fast breathing | saans lene me takleef=difficulty breathing | doodh nahi pi raha=unable to breastfeed | pani nahi pee raha=unable to drink | behosh=unconscious | daura/jhatka=convulsions | ulti ruk nahi rahi=severe vomiting | aankh dhansi=sunken eyes | peshab nahi=no urination | bukhar=fever | seena andar dhansna=chest indrawing | prasav ke baad khoon=postpartum hemorrhage | haath pair sujan+sardard=eclampsia.

2. AGE BRACKETS: infant_0_2m (0-60d): ANY fever=HIGH | infant_2_6m (61-180d): fever≥38°C + danger sign=HIGH | child_6m_1y, child_1_5y, child_5_12y, adult (>12y), elderly (>60y: lower danger threshold), pregnant, postpartum (≤42d).

3. SEVERITY (A→B→C, stop at first match, highest wins):
A) HIGH (any ONE): Fever >39.5°C | Any fever in ≤2mo infant | Convulsions | Unconscious/altered consciousness | Stiff neck+fever | Photophobia+fever/headache | Chest indrawing | Fast breathing (>60/min if <2mo, >50 if 2-12mo, >40 if 1-5y, >30 if >5y/adult) | Stridor | Unable to drink/breastfeed | Severe dehydration (sunken eyes, slow pinch, no tears) | No urination >8h | Blood in stool/urine/vomit | Severe vomiting | Severe malnutrition | Poisoning/bite | Jaundice in ≤2mo or jaundice+fever+altered consciousness.
   - Pregnant: postpartum hemorrhage, eclampsia, seizures, heavy bleeding.
   - Elderly: sudden confusion/slurred speech/weakness, severe breathing difficulty, chest pain, sudden severe headache (even without fever).
   - RULES: Uncertain HIGH/MEDIUM → HIGH. Refusing PHC doesn't change severity.
B) MEDIUM: Fever 38.5-39.5°C (2-3d, conscious+drinking) | Diarrhea≥3/day (no severe dehydration) | Cough≥7d | Mild dehydration | Recurrent vomiting (keeps some fluid) | Infant 2-6mo fever≥38°C (normal feeding) | Sore throat+fever>2d | Pregnant mild ankle swelling.
C) LOW: Mild fever<38.5°C (<2d) | Common cold | Cough<7d | Mild diarrhea<3/day | Minor aches | Vague symptoms.

4. MEDICINES:
- HIGH: medicines=[], home_care=[]
- MEDIUM: ≥1 medicine. Fallback: Paracetamol 500mg 3x/day 3d + ORS.
- LOW: 0-2 medicines if clearly indicated.
Table:
- Paracetamol 500mg (Adult: 1tab 3x/d, 3d | Fever/Pain)
- Paracetamol 250mg/5ml (Child: 15mg/kg 3x/d, 3d | Fever)
- ORS (1L water sips/200ml per stool | Diarrhea)
- Zinc 20mg (>6mo: 1/day, 14d) / Zinc 10mg (<6mo: 1/day, 14d)
- Iron-Folic Acid (1/day, 30d | Pregnancy/Anaemia)
- Vitamin A (100k-200k IU single | Measles 6m-5y)
- Albendazole 400mg (Single dose | Deworming)
- Chloroquine (600mg D1, 300mg D2-3 | Malaria)
- Cotrimoxazole (1tab 2x/d, 5d | Dysentery)
- Antacid (1-2 tabs | Acidity)
Rule: Every med needs name, dosage, duration, source ("asha_kit"|"nlem_2022"). No antibiotics unless F-IMNCI recommends.

5. REASON (2-4 sentences): "[Age+profile] presents with [symptoms+numbers]. Per [guideline], this is [CRITICALITY] because [reason]. [Absent danger signs]. [Immediate action]."

6. ADVICE IN HINDI ("advice_in_hindi"): Pure Devanagari ONLY. Speak to family ("aap"). Class 5 reading level. 2-3 sentences: action + 1 warning sign.
Example HIGH: "यह बहुत गंभीर स्थिति है, घर पर इलाज बिल्कुल न करें। अभी तुरंत नज़दीकी सरकारी अस्पताल या प्राथमिक स्वास्थ्य केंद्र ले जाएं। रास्ते में बच्चे को गर्म रखें।"

7. HOME CARE: HIGH: [] | MEDIUM: 3-5 items | LOW: 3-4 items. Complete instructions with quantities. Last item = return trigger.
Example: "ORS घोल दें — हर दस्त के बाद कम से कम २०० ml"

8. OUTPUT FORMAT (Return ONLY this JSON):
{{
  "criticality": "low|medium|high",
  "refer_to_phc": true|false,
  "reason": "...",
  "red_flags": ["...", "..."],
  "diagnosis": "Specific condition e.g. Viral URTI",
  "differential_diagnosis": ["...", "..."],
  "home_care": ["...", "..."],
  "medicines": [{{"name": "...", "dosage": "...", "duration": "...", "source": "..."}}],
  "advice_in_hindi": "...",
  "follow_up_days": "3|5|7|immediate_referral",
  "reassess_if_worsens": ["...", "...", "..."],
  "reassess_if_worsens_in_hindi": ["...", "...", "..."]
}}
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


# ── LLM Loader ────────────────────────────────────────────────────────────────
def load_llm():
    if MODE == "groq":
        from langchain_groq import ChatGroq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in .env")
        print("  LLM : Groq — openai/gpt-oss-120b (cloud)")
        return ChatGroq(
            model="openai/gpt-oss-120b",
            temperature=0,
            max_tokens=2000,
            api_key=api_key,
        )

    elif MODE == "nim":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("NVIDIA_NIM_API_KEY")
        if not api_key:
            raise ValueError("NVIDIA_NIM_API_KEY not found in .env")
        print("  LLM : NVIDIA NIM — nvidia/nemotron-3.5-lightning-30b-a3b (cloud)")
        return ChatOpenAI(
            model="nvidia/nemotron-3.5-lightning-30b-a3b",
            temperature=0,
            max_tokens=2000,
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
        raise ValueError(f"Unknown MODE: '{MODE}'. Choose from: 'groq' | 'nim' | 'deepseek'")


# ── Helpers ───────────────────────────────────────────────────────────────────
def clean_response(text: str) -> str:
    """Strip reasoning blocks, markdown fences, and extra wrapper text."""
    # Remove complete or unclosed  Mild thinking blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"<think>.*", "", text, flags=re.DOTALL)
    
    # Remove markdown fences safely
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    return text.strip()


def _json_loads(s: str) -> dict:
    """Tolerant json.loads: allows literal newlines in strings + trailing commas."""
    try:
        return json.loads(s, strict=False)
    except json.JSONDecodeError:
        s = re.sub(r",\s*([}\]])", r"\1", s)
        return json.loads(s, strict=False)


def parse_response(text: str) -> dict:
    """Parse LLM response to dict with multiple fallback strategies."""
    cleaned = clean_response(text)

    # Strategy 1: Direct parse
    try:
        return _json_loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract the largest JSON object using string boundaries (O(N) Fast)
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start != -1 and end != -1 and end > start:
        candidate = cleaned[start:end+1]
        try:
            return _json_loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"Could not parse JSON from response (length={len(cleaned)}):\n"
        f"First 300 chars: {cleaned[:300]}\n"
        f"Last 300 chars:  {cleaned[-300:]}"
    )


# ── Retriever ─────────────────────────────────────────────────────────────────
class E5Embeddings(HuggingFaceEmbeddings):
    def embed_documents(self, texts):
        return super().embed_documents([f"passage: {t}" for t in texts])

    def embed_query(self, text):
        return super().embed_query(f"query: {text}")


def load_retriever():
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
    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 5},
    )


# ── Chain Builder ─────────────────────────────────────────────────────────────
def build_chain():
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
        # Step 0: Input guardrail
        try:
            from guardrails.input import check_input
            guard = check_input(symptoms)
            if not guard.passed:
                print(f"  [Guardrail] Input blocked: {guard.violations}")
                return {
                    "criticality": "low",
                    "refer_to_phc": False,
                    "reason": "The input does not appear to describe medical symptoms.",
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
        except Exception:
            pass  # guardrails module may not be available or failed gracefully

        # Step 1: Semantic search in ChromaDB
        docs = retriever.invoke(symptoms)
        context = "\n\n".join([d.page_content for d in docs])[:4000]

        print("\n  --- Retrieved Chunks ---")
        for i, doc in enumerate(docs):
            src = doc.metadata.get("doc_name", "Unknown")
            print(f"  [{i+1}] {src}")
        print("  ------------------------\n")

        # Step 2: LLM call with retry on parse failure
        raw = None
        result = None

        for attempt in range(3):
            try:
                raw = chain.invoke({
                    "symptoms": symptoms,
                    "context":  context,
                })
                result = parse_response(raw)
                break  # success
            except Exception as e:
                print(f"  [Attempt {attempt+1}] Parse failed: {e}")
                if attempt < 2:
                    print(f"  [Attempt {attempt+1}] Retrying in 20s...")
                    time.sleep(20)
                else:
                    print(f"  [Attempt {attempt+1}] All retries exhausted.")
                    raise e

        # Step 3: Auto-extract suggested_services
        try:
            from phc_recommender import SERVICE_MAP
            criticality = result.get("criticality", "low").lower()
            suggested = set(SERVICE_MAP.get(criticality, ["OPD"]))

            reason_lower = result.get("reason", "").lower()
            symptoms_lower = symptoms.lower()
            for key, services in SERVICE_MAP.items():
                if key not in ("high", "medium", "low"):
                    if key in reason_lower or key in symptoms_lower:
                        suggested.update(services)

            result["suggested_services"] = list(suggested)
        except Exception:
            if "suggested_services" not in result:
                result["suggested_services"] = ["OPD"]

        return result

    return run_chain


# ── Singleton ─────────────────────────────────────────────────────────────────
_chain = None

def get_chain():
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
        "bacche ko 3 din se bukhaar hai, khaana nahi kha raha",
        "mahila ko prasav ke baad bahut zyada khoon aa raha hai",
        "pet mein dard hai aur dast ho raha hai pichle 2 din se",
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