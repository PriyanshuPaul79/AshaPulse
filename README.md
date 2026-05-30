# 🚑 AshaPulse – AI Diagnostic Assistant for Rural Healthcare

AshaPulse is an AI-assisted decision support system for ASHA/ANM frontline workers.
It combines **symptom triage**, **RAG-based protocol grounding**, **multilingual interaction** (Hindi/Hinglish/English), and **PHC discovery** to support faster and safer primary-care decisions.

---

## 🌟 Frontend Screenshots

### 1) Diagnose Screen
![AshaPulse Diagnose Screen](https://github.com/user-attachments/assets/3ce5948d-d436-4a06-a281-3240b4ad12e5)

### 2) Diagnosis Workflow Screen
![AshaPulse Frontend Screenshot 2](https://github.com/user-attachments/assets/c2ae8f68-170c-470a-b8f3-36235ea1fccb)

### 3) PHC/History Experience Screen
![AshaPulse Frontend Screenshot 3](https://github.com/user-attachments/assets/9087d4d0-b490-4ccc-b260-853efc851548)

---

## ✨ Key Features

- 🧠 AI-based symptom triage with **Red / Yellow / Green** risk classification
- 📚 **RAG (Retrieval-Augmented Generation)** over F-IMNCI and healthcare guideline PDFs
- 🌐 Multilingual diagnosis support (Hindi, Hinglish, English)
- 🗺️ PHC nearest-center recommendation using geospatial distance (Haversine)
- 💾 Persistent diagnosis history in MongoDB
- ⚠️ Practical immediate actions and referral guidance for ASHA/ANM workflows

---

## 🧱 Architecture Overview

- **Frontend:** React + TypeScript + Vite + Framer Motion + Leaflet
- **Backend API:** FastAPI
- **RAG Pipeline:** LangChain + ChromaDB + sentence-transformers + Ollama (mistral:7b)
- **Datastores:**
  - SQLite (`data/phc_directory.db`) for PHC master directory
  - Chroma persistent vector DB (`data/chroma_db`) for protocol retrieval

---

## 📂 Repository Structure

```text
AshaPulse/
├── frontend/                 # React app (diagnose UI, history, PHC map)
├── backend/
│   ├── main.py               # FastAPI app + API routes
│   ├── chain.py              # RAG + LLM diagnosis chain
│   ├── ingest.py             # PDF -> chunks -> Chroma ingestion
│   ├── phc_recommender.py    # Nearest PHC lookup logic
│   └── schemas.py            # Request schema models
├── Docs/                     # Clinical guideline PDFs (RAG source docs)
├── data/
│   ├── chroma_db/            # Persisted vector store
│   └── phc_directory.db      # PHC directory SQLite DB
└── README.md
```

---

## 🔎 RAG Pipeline (How it works)

1. PDF clinical guidelines in `Docs/` are parsed with `pypdf`.
2. Text is chunked (`RecursiveCharacterTextSplitter`).
3. Chunks are embedded using `sentence-transformers/all-MiniLM-L6-v2`.
4. Embeddings are stored in Chroma (`data/chroma_db`).
5. On `/diagnose`, relevant chunks are retrieved (`k=4`) for symptom query.
6. Prompt + retrieved context are sent to local Ollama model (`mistral:7b`).
7. Backend enforces strict JSON output schema for frontend rendering.

---

## ⚙️ Setup Instructions

### 1) Clone repository

```bash
git clone https://github.com/PriyanshuPaul79/AshaPulse.git
cd AshaPulse
```

### 2) Backend setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env` file inside the `backend/` directory:

```env
MONGO_URI=mongodb://localhost:27017
DB_NAME=ashapulse
COLLECTION_NAME=history
```

Run backend:

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

### 3) Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000` and calls backend at `http://localhost:5000`.

---

## 🧪 Build / Validation Commands

### Frontend

```bash
cd frontend
npm run lint
npm run build
```

### Backend sanity check

```bash
python -m compileall backend
```

---

## 🌐 API Endpoints

Base URL: `http://localhost:5000`

- `GET /` → health message
- `POST /diagnose` → generate AI triage response
- `POST /history` → store diagnosis history
- `GET /history` → fetch diagnosis history
- `GET /phc?lat=<value>&lon=<value>&k=<int>` → nearest PHC recommendations

### `POST /diagnose` request body

```json
{
  "symptoms": "2 days fever with breathing difficulty",
  "language": "hinglish"
}
```

### Response shape

```json
{
  "riskLevel": "Red|Yellow|Green",
  "primaryDiagnosis": "...",
  "confidence": 85,
  "immediateActions": ["..."],
  "referralNeeded": "...",
  "recommendedMedicines": ["..."]
}
```

`confidence` is returned as a numeric score in the 0-100 range.

---

## 🗺️ PHC Recommendation Flow

- User searches/selects location on map in frontend.
- Frontend calls `/phc` with coordinates.
- Backend computes nearest PHCs using Haversine distance over SQLite directory.
- Results are shown as map markers + sorted distance list.

---

## 📌 Roadmap Ideas

- Voice input for field workers
- Better offline mode and sync queue
- District analytics dashboard
- Authentication and role-based supervisor panel

---

## 📄 License

MIT License
