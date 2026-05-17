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

ROOT_DIR   = Path(_file_).resolve().parent.parent
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

CHUNK_SIZE    = 1000
CHUNK_OVERLAP = 200


def split_documents(docs: list) -> list:
    """Split pages into chunks for embedding."""

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " "],
    )

    log.info("Splitting documents into chunks...")

    chunks = splitter.split_documents(docs)

    log.info(f"{len(docs)} pages → {len(chunks)} chunks")

    return chunks


def build_vectorstore(chunks: list) -> Chroma:
    """Embed chunks and store in ChromaDB."""

    log.info("Loading embedding model...")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    log.info(f"Building ChromaDB vector store at {CHROMA_DIR}...")

    vectorstore = Chroma.from_documents(
        documents=list(tqdm(chunks, desc="  Embedding chunks")),
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR),
        collection_name="asha_knowledge_base",
    )

    return vectorstore