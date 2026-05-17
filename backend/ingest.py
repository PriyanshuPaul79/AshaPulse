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

