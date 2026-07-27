# SecureHall-RAG Administrator Guide

This guide covers the deployment, configuration, and maintenance of the SecureHall-RAG system.

## 1. System Architecture

SecureHall-RAG relies on three core running components:
1. **Next.js Frontend:** React-based UI served on port 3000.
2. **FastAPI Backend:** Python REST API served on port 8000.
3. **Ollama LLM Engine:** Local language model server (Mistral 7B) running on port 11434.

Data is stored locally:
- **Relational Database:** `database.db` (SQLite) stores user accounts and document metadata.
- **Vector Index:** `faiss_index.bin` stores the dense embeddings.
- **BM25 Index:** `bm25_index.pkl` stores the sparse lexical data.
- **Documents:** Raw PDFs and DOCXs are stored in `uploaded_documents/`.

---

## 2. Configuration & Tuning

Configuration is managed in `src/api/core/config.py` and via `.env` files.

### Verification Thresholds
You can adjust how strict the system is about hallucinations by modifying the verification threshold in `src/verification/refusal_threshold.py`.

- **Conservative:** Extremely strict. Refuses to answer if it detects *any* ambiguity. Best for legal or critical compliance use cases.
- **Balanced (Default):** Accepts answers with strong evidence, refuses clear hallucinations.
- **Permissive:** Answers even if the evidence is weak. Higher risk of hallucination.

### Re-Ranking Configuration
CrossEncoder re-ranking drastically improves accuracy but requires more compute. You can disable it if you are running on CPU and need faster response times.

```env
# .env
ENABLE_RERANKING=true
RERANKER_MODEL="cross-encoder/ms-marco-MiniLM-L-6-v2"
RETRIEVAL_TOP_K=5
```

---

## 3. Deployment

### Local Server Setup (Bare Metal)

1. Start Ollama natively on the host machine:
```bash
ollama serve
ollama pull mistral
```

2. Start the Backend API (requires Python 3.10+):
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

3. Start the Frontend (requires Node 18+):
```bash
cd frontend
npm install
npm run build
npm run start
```

### Future Deployment (Docker)
A `production_readiness_report.md` has been drafted to migrate this architecture to Docker, PostgreSQL, and Celery for enterprise scale. 

---

## 4. Monitoring & Troubleshooting

### Log Locations
- Backend API logs are output to standard out (terminal). 
- To capture logs to a file, run `uvicorn src.api.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1`

### Common Issues

**Issue:** User receives "Error: Could not connect to LLM provider."
**Cause:** Ollama is not running, or the backend cannot reach port 11434.
**Fix:** Run `ollama serve`. If running via Docker later, ensure `host.docker.internal` is mapped correctly.

**Issue:** System returns "I cannot answer this question" for a document the user uploaded.
**Cause:** The Document Level Security metadata did not match the user's role.
**Fix:** Check `database.db` to ensure the document's `roles_allowed` column includes the querying user's role.

**Issue:** Memory usage spikes during document ingestion.
**Cause:** The FAISS index builds in RAM. If uploading a 10,000+ page document, the server may OOM (Out of Memory).
**Fix:** Chunk the uploads into smaller batches, or migrate to a disk-backed vector database like pgvector (PostgreSQL) or Pinecone.
