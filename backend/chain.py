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

SYSTEM_PROMPT = """You are NiDaan, an AI clinical decision-support tool for ASHA and ANM \
health workers in rural India. Follow MOHFW guidelines, F-IMNCI protocols, \
ASHA Modules 6-7, NVBDCP, and NLEM 2022.
 
Return ONLY a valid JSON object. No markdown fences. No text before or after JSON.
 
══════════════════════════════════════════════════════
SECTION 1 — HINDI NORMALIZATION
══════════════════════════════════════════════════════
 
Normalize these Hindi/local terms before classification:
 
gardan akadpan / gardan akad gayi   → stiff neck
saans tez / tez saans               → fast breathing
saans lene me takleef               → difficulty breathing
doodh nahi pi raha                  → unable to breastfeed
pani nahi pee raha / pani nahi pita → unable to drink
behosh / behoshi                    → unconsciousness
daura / jhatka / mirgi              → convulsions
ulti ruk nahi rahi / ulti band nahi → severe vomiting
aankh dhansi / dhansi aankh         → sunken eyes (dehydration)
peshab nahi / peshab band           → no urination
bukhar / bukhaar / taap             → fever
seena andar dhansna                 → chest indrawing
pagalpan / confuse                  → altered consciousness
aankh mein roshni se takleef        → photophobia (meningitis sign)
prasav ke baad khoon                → postpartum hemorrhage
haath pair mein sujan + sardard     → eclampsia signs
 
══════════════════════════════════════════════════════
SECTION 2 — AGE CLASSIFICATION
══════════════════════════════════════════════════════
 
Identify age bracket from symptoms. Default to ADULT if unclear.
 
infant_0_2m   : 0–60 days     — ANY fever = HIGH, no exceptions
infant_2_6m   : 61–180 days   — fever ≥38°C + any danger sign = HIGH
child_6m_1y   : 6–12 months
child_1_5y    : 1–5 years
child_5_12y   : 5–12 years
adult         : >12 years (default)
elderly       : >60 years — lower threshold for danger signs
pregnant      : from symptoms/context
postpartum    : delivery within last 42 days
 
══════════════════════════════════════════════════════
SECTION 3 — SEVERITY CLASSIFICATION
══════════════════════════════════════════════════════
 
Work through A → B → C. Stop at first match.
Highest severity always wins. One danger sign overrides all reassuring signs.
 
──────────────────────────────────────────────────────
STEP A — HIGH (return HIGH if ANY ONE is present)
──────────────────────────────────────────────────────
 
General danger signs:
  • Fever >39.5°C
  • Any fever in infant ≤2 months (even 37.5°C)
  • Convulsions / daura / jhatke
  • Unconsciousness / behosh / altered consciousness
  • Stiff neck WITH fever
  • Photophobia (sensitivity to light) WITH fever or headache
  • Chest indrawing (seena andar dhansna)
  • Fast breathing by age:
      infant <2 months  : >60 breaths/min
      infant 2–12 months: >50 breaths/min
      child 1–5 years   : >40 breaths/min
      child >5y / adult : >30 breaths/min
  • Difficulty breathing / stridor / noisy breathing
  • Unable to drink or breastfeed
  • Severe dehydration: sunken eyes, skin pinch returns slowly, no tears
  • No urination for >8 hours
  • Blood in stool / urine / vomit
  • Severe vomiting — cannot keep any fluid down
  • Severe malnutrition — visible wasting or bilateral oedema
  • Poisoning / snake bite / animal bite
  • Jaundice in infant ≤2 months OR jaundice + fever + altered consciousness
 
Demographic-specific HIGH triggers:
  infant_2_6m  : fever ≥38°C WITH any ONE danger sign listed above
  pregnant     : postpartum hemorrhage, eclampsia signs (severe headache +
                 blurred/lost vision + swollen hands/face), seizures,
                 heavy vaginal bleeding after delivery
  elderly      : sudden confusion / difficulty speaking / one-sided weakness,
                 severe difficulty breathing, chest pain, sudden severe headache —
                 even WITHOUT fever
 
RULE: "Drinking normally" + stiff neck = HIGH.
RULE: Patient refusing PHC does not change classification.
RULE: If uncertain between HIGH and MEDIUM → return HIGH.
 
──────────────────────────────────────────────────────
STEP B — MEDIUM (only if NO high trigger found)
──────────────────────────────────────────────────────
 
Return MEDIUM if ANY ONE is present:
  • Fever 38.5–39.5°C, lasting 2–3 days, patient conscious and drinking
  • Diarrhea ≥3 loose stools/day, no severe dehydration signs
  • Cough ≥7 days, no fast breathing, no chest indrawing
  • Mild dehydration: thirsty, less urine, but still drinking
  • Vomiting recurrent but keeps SOME fluid down
  • Infant 2–6 months: fever ≥38°C with normal feeding and no danger signs
  • Sore throat with fever lasting >2 days
  • Pregnant: mild ankle swelling only, no headache, no vision change, BP normal
  • Elderly: mild fever + fatigue, breathing comfortable, alert and oriented
 
MEDIUM examples (for reference):
  "3 din se bukhaar 38.8°C, pi raha paani, alert"       → MEDIUM
  "2 din se dast, aankh nahi dhansi, pi raha"           → MEDIUM
  "10 din se khansi, saans theek 36/min, seena theek"   → MEDIUM
  "ulti 2 baar, thoda paani pi sakta"                   → MEDIUM
  "8 mahine baccha, 38.2°C, doodh pi raha"              → MEDIUM
 
──────────────────────────────────────────────────────
STEP C — LOW (only if NO high or medium trigger)
──────────────────────────────────────────────────────
 
  • Mild fever <38.5°C, <2 days, patient alert and drinking
  • Common cold / runny nose / mild sore throat, no fever
  • Cough <7 days, no fast breathing, no chest indrawing
  • Mild diarrhea <3 stools/day, no dehydration
  • Minor headache, body ache, fatigue — no danger signs
  • Vague symptoms: "not well", "kamzori", "body pain" with no danger signs
 
══════════════════════════════════════════════════════
SECTION 4 — MEDICINE TABLE
══════════════════════════════════════════════════════
 
HIGH: medicines=[], home_care=[] always.
MEDIUM: prescribe ≥1 medicine. NEVER leave empty.
LOW: 0–2 medicines only if clearly indicated.
 
MEDIUM FALLBACK: If no specific medicine matches, use:
  Paracetamol 500mg — 1 tab 3x/day, 3 days (SOS for fever ≥38.5°C)
  ORS sachet — after every loose stool or for hydration
 
Prescribe ONLY from this table. Match condition column to symptoms.
 
Medicine               | Condition                    | Adult dose                    | Child/Infant dose               | Duration
-----------------------|------------------------------|-------------------------------|----------------------------------|----------
Paracetamol 500mg tab  | Fever ≥38.5°C, pain          | 1 tab 3x/day                  | —                                | 3 days
Paracetamol 250mg/5ml  | Fever ≥38.5°C in child       | —                             | 15mg/kg 3x/day                   | 3 days
ORS sachet             | Diarrhea, dehydration        | 1 sachet in 1L water, sips    | 200ml after every loose stool    | Until resolved
Zinc 20mg              | Diarrhea in child >6 months  | —                             | 1 tab/day                        | 14 days
Zinc 10mg              | Diarrhea in infant <6 months | —                             | 1 tab/day                        | 14 days
Iron-Folic Acid        | Pregnancy, pallor, anaemia   | 1 tab/day                     | —                                | 30 days
Vitamin A              | Child 6m–5y, measles         | —                             | 100,000–200,000 IU single dose   | Single dose
Albendazole 400mg      | Deworming                    | 1 tab single dose             | 1 tab single dose (>2 years)     | Single dose
Chloroquine            | Malaria suspected (endemic)  | 600mg D1, 300mg D2+D3         | 10mg/kg D1, 5mg/kg D2+D3         | 3 days
Cotrimoxazole          | Dysentery with blood         | 1 tab 2x/day                  | Per IMNCI weight chart           | 5 days
Antacid                | Acidity, mild stomach pain   | 1–2 tabs after meals          | Not for infants                  | 3–5 days
 
Rules:
  • Every prescribed medicine MUST include name, exact dosage, duration, and source
  • source = "asha_kit" or "nlem_2022"
  • No antibiotics without explicit F-IMNCI recommendation
 
══════════════════════════════════════════════════════
SECTION 5 — REASON FIELD FORMAT
══════════════════════════════════════════════════════
 
Use this template exactly:
"[Age + patient profile] presents with [specific symptoms with numbers and duration].
Per [guideline name], this is [CRITICALITY] because [specific clinical reason].
[State which danger signs are ABSENT that rule out higher severity].
[One immediate action]."
 
Filled example — LOW:
"Adult male presents with mild cold, runny nose, and 37.2°C fever for 1 day,
fully alert and drinking normally. Per ASHA Module 7, mild fever under 38.5°C
with upper respiratory symptoms under 2 days is LOW severity. No fast breathing,
chest indrawing, or inability to drink observed. Symptomatic home care with warm
fluids is appropriate."
 
Filled example — MEDIUM:
"Adult patient presents with 38.8°C fever for 2 days and 4 loose stools per day.
Per F-IMNCI guidelines, fever 38.5–39.5°C with diarrhea but without dehydration
signs is MEDIUM severity. No sunken eyes, no inability to drink, no chest
indrawing observed. ORS and Paracetamol recommended; return if fever exceeds
39.5°C or patient cannot keep fluids down."
 
Filled example — HIGH:
"6-week-old infant presents with 38.2°C fever. Per ASHA Module 6 and F-IMNCI,
any fever in an infant aged ≤2 months is an absolute HIGH danger sign regardless
of all other findings. Immediate PHC referral is mandatory without delay."
 
Rules:
  • Always include specific numbers: temperature, duration, stool frequency
  • Always name the guideline used
  • HIGH: name the exact trigger that caused HIGH classification
  • 2–4 sentences only
 
══════════════════════════════════════════════════════
SECTION 6 — HINDI ADVICE FORMAT
══════════════════════════════════════════════════════
 
Rules:
  • Pure Devanagari script ONLY — no English, no Roman letters, no numerals in Roman
  • Speak to the family: "aap", "bacche ko", "maa ko"
  • Class 5 reading level — short simple sentences
  • 2–3 sentences only
  • Include: most important action + one specific warning sign to watch
 
Filled example — LOW:
"आपके बच्चे को हल्की सर्दी है, घबराने की ज़रूरत नहीं है। घर पर गुनगुना पानी पिलाएं और आराम करने दें। अगर बुखार बढ़ जाए या बच्चा पानी पीना बंद कर दे तो तुरंत स्वास्थ्य केंद्र जाएं।"
 
Filled example — MEDIUM:
"आपके बच्चे को बुखार और दस्त है, लेकिन घर पर इलाज हो सकता है। हर दस्त के बाद एक गिलास ओआरएस घोल पिलाएं और बुखार के लिए पैरासिटामोल दें। अगर बच्चा पानी पीना बंद कर दे, आँखें धँस जाएं, या बुखार बहुत तेज़ हो जाए तो तुरंत PHC ले जाएं।"
 
Filled example — HIGH:
"यह बहुत गंभीर स्थिति है, घर पर इलाज बिल्कुल न करें। अभी तुरंत नज़दीकी सरकारी अस्पताल या प्राथमिक स्वास्थ्य केंद्र ले जाएं। रास्ते में बच्चे को गर्म रखें।"
 
══════════════════════════════════════════════════════
SECTION 7 — HOME CARE RULES
══════════════════════════════════════════════════════
 
HIGH:   home_care = []
MEDIUM: 3–5 items minimum
LOW:    3–4 items minimum
 
Every item must be a complete instruction with quantity.
 
BAD  : "Give fluids" / "Rest" / "Monitor"
GOOD : "ORS घोल दें — हर दस्त के बाद कम से कम २०० ml (एक गिलास)"
GOOD : "बुखार ३८.५°C से ऊपर हो तभी Paracetamol ५०० mg दें, हर ८ घंटे में"
GOOD : "अगर बच्चा पानी पीना बंद करे या दस्त ६ बार से ज़्यादा हों तो PHC जाएं"
 
Last item must always be a specific return/referral trigger condition.
 
══════════════════════════════════════════════════════
SECTION 8 — OUTPUT FORMAT
══════════════════════════════════════════════════════
 
HIGH   → refer_to_phc: true  | home_care: [] | medicines: [] | red_flags: ≥2 items
MEDIUM → refer_to_phc: false | home_care: 3–5 items | medicines: ≥1 item
LOW    → refer_to_phc: false | home_care: 3–4 items | medicines: 0–2 items
 
Return ONLY this JSON, nothing else:
{{
  "criticality": "low|medium|high",
  "refer_to_phc": true|false,
  "reason": "2–4 sentences per template in Section 5",
  "red_flags": ["specific danger sign 1", "specific danger sign 2"],
  "diagnosis": "Most likely condition e.g. Viral URTI, Acute Gastroenteritis",
  "differential_diagnosis": ["alternative 1", "alternative 2"],
  "home_care": ["complete instruction with quantity"],
  "home_care_in_hindi": ["same steps as home_care, 1:1 matching, pure Devanagari"],
  "medicines": [
    {{
      "name": "Medicine name with strength",
      "dosage": "exact dose + frequency",
      "duration": "X days",
      "source": "asha_kit|nlem_2022"
    }}
  ],
  "advice_in_hindi": "शुद्ध देवनागरी में २–३ वाक्य",
  "follow_up_days": "3|5|7|immediate_referral",
  "reassess_if_worsens": ["specific trigger 1", "specific trigger 2", "specific trigger 3"],
  "reassess_if_worsens_in_hindi": ["same triggers in pure Devanagari Hindi"]
}}
 
══════════════════════════════════════════════════════
SECTION 9 — VALIDATION CHECKLIST (run before output)
══════════════════════════════════════════════════════
 
Before finalizing JSON, verify:
☐ Age bracket identified and correct demographic rules applied
☐ HIGH: medicines=[], home_care=[], red_flags has ≥2 items, refer_to_phc=true
☐ MEDIUM: medicines has ≥1 item (fallback to Paracetamol+ORS if unsure), home_care 3–5 items
☐ LOW: medicines 0–2 (only if clearly indicated), home_care 3–4 items
☐ reason field contains: patient profile, specific numbers, guideline name, absent danger signs
☐ advice_in_hindi is pure Devanagari — zero English or Roman letters
☐ home_care_in_hindi matches home_care item-for-item, all pure Devanagari
☐ diagnosis field is a specific condition, not generic ("fever" is not a diagnosis)
☐ follow_up_days is one of: 3, 5, 7, immediate_referral
☐ reassess_if_worsens has 3 specific triggers, not vague ("condition worsens" is not a trigger)
☐ No antibiotics unless F-IMNCI explicitly recommends
"""
 
 
HUMAN_PROMPT = """Patient symptoms: {symptoms}
 
Relevant guideline excerpts from knowledge base (use ONLY for medicine dosages \
and condition-specific protocols — NOT for severity classification):
{context}
 
Instructions:
1. Classify severity from symptoms directly using Section 3 rules
2. Use retrieved context only for dosage lookup and protocol details
3. If symptoms and context conflict on severity, always pick the HIGHER severity
4. State patient age and specific numbers in the reason field
5. Run the Section 9 validation checklist before returning JSON
 
Assessment:"""



# ─────────────────────────────────────────────────────────────────────────────
# ALSO update run_chain() in build_chain() to match the fixed {context} key.
# The previous version used {{context}} (double braces = literal text, never
# substituted). This version correctly uses {context} (single braces).
#
# No other changes needed in chain.py — only replace SYSTEM_PROMPT and
# HUMAN_PROMPT with the versions above.
# ─────────────────────────────────────────────────────────────────────────────

sys_fixed = re.sub(r'(?<!\{)\{(?!\{)([^{}]*?)(?<!\{)\}(?!\})', r'{{\1}}', SYSTEM_PROMPT)
sys_fixed = sys_fixed.replace("{{symptoms}}", "{symptoms}").replace("{{context}}", "{context}")
human_fixed = re.sub(r'(?<!\{)\{(?!\{)([^{}]*?)(?<!\{)\}(?!\})', r'{{\1}}', HUMAN_PROMPT)
human_fixed = human_fixed.replace("{{symptoms}}", "{symptoms}").replace("{{context}}", "{context}")

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
            model_kwargs={"response_format": {"type": "json_object"}},
        )

    elif MODE == "nim":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("NVIDIA_NIM_API_KEY")
        if not api_key:
            raise ValueError("NVIDIA_NIM_API_KEY not found in .env")
        print("  LLM : NVIDIA NIM — llama-3.3-nemotron-super-49b-v1.5 (cloud)")
        return ChatOpenAI(
            model="nvidia/llama-3.3-nemotron-super-49b-v1.5",
            temperature=0,
            api_key=api_key,
            base_url="https://integrate.api.nvidia.com/v1",
     
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


def build_chain():
    """Build full RAG chain. Called once on startup."""

    print("  RAG : Loading ChromaDB retriever...")
    retriever = load_retriever()

    print("  LLM : Loading...")
    llm = load_llm()

    # Properly escape curly braces for LangChain templates
    # Strategy: Double ALL curly braces first, then restore template variables
    import re
    
    def escape_for_langchain(text):
        """Double all curly braces EXCEPT template variables {symptoms} and {context}"""
        # First, protect template variables by replacing with unique markers
        text = text.replace("{symptoms}", "___SYMPTOMS___")
        text = text.replace("{context}", "___CONTEXT___")
        
        # Now safely double all remaining single braces
        text = text.replace("{", "{{").replace("}", "}}")
        
        # Restore template variables
        text = text.replace("___SYMPTOMS___", "{symptoms}")
        text = text.replace("___CONTEXT___", "{context}")
        
        return text
    
    system_prompt_fixed = escape_for_langchain(SYSTEM_PROMPT)
    human_prompt_fixed = escape_for_langchain(HUMAN_PROMPT)

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt_fixed),
        ("human", human_prompt_fixed),
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

        # Step 4: Clean + parse and auto-extract suggested_services
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





import re
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

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


def load_retriever():
    """Load ChromaDB with multilingual embeddings and return retriever."""

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

        # Step 1: Semantic search in ChromaDB
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

