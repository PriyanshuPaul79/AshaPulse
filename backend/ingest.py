import os
import sys
import shutil
from pathlib import Path

from dotenv import load_dotenv

from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# ── Load Environment Variables ────────────────────────────────────────────────

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT_DIR   = Path(__file__).resolve().parent.parent
DOCS_DIR   = ROOT_DIR / "Docs"
CHROMA_DIR = ROOT_DIR / "data" / "chroma_db"

# ── Document Metadata ─────────────────────────────────────────────────────────
# Maps filename → readable label (used in retrieval source tracking)

DOC_METADATA = {
    "nlem2022.pdf":                        "NLEM 2022 - Essential Medicines",
    "guidelines-Insecticides-NVBDCP.pdf": "NVBDCP Insecticide Guidelines",
    "standard-treatment-guidelines.pdf":  "Standard Treatment Guidelines",
    "asha_book_no-6.pdf":                 "ASHA Module 6 - Skills that Save Lives",
    "asha_book_no-7.pdf":                 "ASHA Module 7",
    "imnci_chart_booklet.pdf":            "F-IMNCI Chart Booklet",
}

# ── Chunking Configuration ────────────────────────────────────────────────────

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def load_pdfs(docs_dir: Path) -> list:
    """Load all PDFs from Docs/ folder."""
    
    all_docs = []

    pdf_files = list(docs_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"❌ No PDFs found in {docs_dir}")
        sys.exit(1)

    print(f"Found {len(pdf_files)} PDF(s):\n")

    for pdf_path in pdf_files:

        filename = pdf_path.name
        label = DOC_METADATA.get(filename, filename)

        print(f"  Loading: {filename}")

        try:
            loader = PyMuPDFLoader(str(pdf_path))
            docs = loader.load()

            # Attach metadata to every page
            for doc in docs:
                doc.metadata["source"] = filename
                doc.metadata["doc_name"] = label

            all_docs.extend(docs)

            print(f"  ✅ {len(docs)} pages loaded — {label}\n")

        except Exception as e:
            print(f"  ❌ Failed to load {filename}: {e}\n")

    return all_docs


def split_documents(docs: list) -> list:
    """Split pages into chunks for embedding."""

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " "],
    )

    chunks = splitter.split_documents(docs)

    print(f"  ✅ {len(docs)} pages → {len(chunks)} chunks\n")

    return chunks


def build_vectorstore(chunks: list) -> Chroma:
    """Embed chunks and store in ChromaDB."""

    print("Loading embedding model...")
    print("Using Hugging Face Inference API\n")

    # embeddings = HuggingFaceEndpointEmbeddings(
    #     model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    #     task="feature-extraction",
    #     huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
    # )

    embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

    print("Building ChromaDB vector store...")
    print(f"Location: {CHROMA_DIR}\n")

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR),
        collection_name="asha_knowledge_base",
    )

    return vectorstore


def verify_vectorstore(vectorstore: Chroma) -> None:
    """Quick sanity check."""

    print("Running verification query...\n")

    test_query = "child fever home treatment"

    test_results = vectorstore.similarity_search(
        test_query,
        k=2
    )

    if test_results:

        print("  ✅ Retrieval working\n")

        print(f"     Source : {test_results[0].metadata.get('doc_name')}")
        print(f"     Preview: {test_results[0].page_content[:120]}...\n")

    else:
        print("  ⚠️ No results returned — check your PDFs\n")


def main():

    print("\n" + "═" * 55)
    print("  ASHA Knowledge Base — Document Ingestion")
    print("═" * 55 + "\n")

    # ── STEP 1: Load PDFs ────────────────────────────────────────────────────

    print("STEP 1 — Loading PDFs")
    print("─" * 40)

    docs = load_pdfs(DOCS_DIR)

    print(f"Total pages loaded: {len(docs)}\n")

    # ── STEP 2: Split Documents ─────────────────────────────────────────────

    print("STEP 2 — Splitting into chunks")
    print("─" * 40)

    chunks = split_documents(docs)

    # ── STEP 3: Clear Existing ChromaDB ─────────────────────────────────────

    print("STEP 3 — Cleaning old ChromaDB")
    print("─" * 40)

    if CHROMA_DIR.exists():
        print("Deleting existing ChromaDB...")
        shutil.rmtree(CHROMA_DIR)

    print("  ✅ Old DB cleared\n")

    # ── STEP 4: Embed + Store ───────────────────────────────────────────────

    print("STEP 4 — Embedding + storing in ChromaDB")
    print("─" * 40)

    vectorstore = build_vectorstore(chunks)

    print(f"  ✅ {len(chunks)} chunks stored in ChromaDB\n")

    # ── STEP 5: Verification ────────────────────────────────────────────────

    print("STEP 5 — Verification")
    print("─" * 40)

    verify_vectorstore(vectorstore)

    print("═" * 55)
    print("  ✅ Ingestion complete — ready for RAG")
    print(f"  DB location: {CHROMA_DIR}")
    print("═" * 55 + "\n")


if __name__ == "_main_":
    main()