

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





        # ── Chain Builder ─────────────────────────────────────────────────────────────

def load_retriever():
    """Load ChromaDB and return retriever."""

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
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
        search_kwargs={"k": 4},
    )


def build_chain():
    """Build and return the full RAG chain function."""

    retriever = load_retriever()

    llm = ChatOllama(
        model="deepseek-r1:7b",
        temperature=0,
        format="json",
        num_ctx=4096,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", HUMAN_PROMPT),
    ])

    chain = prompt | llm | StrOutputParser()

    def run_chain(symptoms: str) -> dict:
        """
        Full pipeline:
        symptoms → retrieve context → LLM → clean → parse → dict
        """

        # Step 1: Retrieve relevant medical context
        docs    = retriever.invoke(symptoms)
        print("\n--- Retrieved Chunks ---")
        for i, doc in enumerate(docs):
            print(f"Chunk {i+1}: {doc.metadata.get('doc_name')}")
            print(f"Preview: {doc.page_content[:100]}")
        print("------------------------\n")
        context = "\n\n".join([d.page_content for d in docs])

        # Step 2: Run chain
        raw_response = chain.invoke({
            "symptoms": symptoms,
            "context":  context,
        })

        # Step 3: Clean + parse
        result = parse_response(raw_response)

        return result

    return run_chain


# ── Singleton ─────────────────────────────────────────────────────────────────
# Load once, reuse across all API requests
# Prevents reloading embeddings + ChromaDB on every call

_chain = None

def get_chain():
    global _chain
    if _chain is None:
        print("Initialising NiDaan RAG chain (first request only)...")
        _chain = build_chain()
        print("✅ Chain ready.\n")
    return _chain


# ── Quick Test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    test_cases = [
        "bacche ko 3 din se bukhaar hai, khaana nahi kha raha",
        "mahila ko prasav ke baad bahut zyada khoon aa raha hai",
        "pet mein dard hai aur dast ho raha hai",
    ]

    chain = get_chain()

    for symptoms in test_cases:
        print(f"{'─'*55}")
        print(f"Input : {symptoms}")
        print(f"{'─'*55}")

        result = chain(symptoms)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()