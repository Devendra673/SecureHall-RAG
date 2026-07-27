# Phase 1, Task 1.7: System Design Document

**Project**: SecureHall-RAG - Trustworthy Document Question-Answering System  
**Task**: Design system architecture with security, transparency, and local LLM focus  
**Date**: May 2026

---

## Executive Summary

SecureHall-RAG is a **modular, security-hardened RAG system** designed for enterprise policy Q&A. It integrates:

1. **Document Ingestion Pipeline** — Parse DOCX → Extract text → Chunk intelligently
2. **Hybrid Retrieval** — Dense embeddings (semantic) + Sparse BM25 (keyword) search
3. **Multi-Layer Verification** — Entailment checking, self-verification, confidence calibration
4. **Security Layer** — Prompt injection detection, content filtering, audit logging
5. **Local LLM Integration** — Support Mistral, NeuralChat, OpenHermes; no cloud dependency
6. **Explainability Engine** — Citation tracking, evidence chains, refusal explanations
7. **User Interface** — Streamlit web app + REST API for integration

**Design Principles**:
- ✓ **Security-First**: Treat document content as potentially hostile
- ✓ **Transparency**: Complete evidence chains, explainable decisions
- ✓ **Privacy**: Local deployment, no data leakage
- ✓ **Reliability**: Multi-layer verification reduces hallucinations
- ✓ **Modularity**: Pluggable components for flexibility
- ✓ **Open-Source**: Auditable, community-driven

---

## 1. System Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SECUREHALL-RAG SYSTEM                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐      ┌──────────────────┐      ┌───────────────┐ │
│  │   Document Input │      │  User Interface  │      │   REST API    │ │
│  │  - DOCX files    │      │ - Streamlit Web  │      │  - JSON I/O   │ │
│  │  - File browser  │      │ - Chat history   │      │  - Auth/Rate  │ │
│  └────────┬─────────┘      └────────┬─────────┘      └───────┬───────┘ │
│           │                         │                        │        │
│           ▼                         ▼                        ▼        │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │              CORE RAG PROCESSING ENGINE                        │   │
│  ├────────────────────────────────────────────────────────────────┤   │
│  │                                                                │   │
│  │  ┌─────────────────┐  ┌──────────────────┐  ┌────────────┐   │   │
│  │  │ Ingestion Layer │──│ Security Filter  │──│ Chunking & │   │   │
│  │  │ - Parse DOCX    │  │ - Pattern match  │  │ Embedding  │   │   │
│  │  │ - Extract text  │  │ - Content scan   │  │ - Dense    │   │   │
│  │  │ - Preserve refs │  │ - Log threats    │  │ - Sparse   │   │   │
│  │  └─────────────────┘  └──────────────────┘  └────────────┘   │   │
│  │           │                                        │           │   │
│  │           └─────────────────┬─────────────────────┘           │   │
│  │                             ▼                                 │   │
│  │                    ┌─────────────────┐                        │   │
│  │                    │ Vector Database │                        │   │
│  │                    │ - FAISS/Chroma  │                        │   │
│  │                    │ - Metadata idx  │                        │   │
│  │                    │ - BM25 index    │                        │   │
│  │                    └────────┬────────┘                        │   │
│  │                             │                                 │   │
│  └─────────────────────────────┼─────────────────────────────────┘   │
│                                │                                     │
│                    ┌───────────▼────────────┐                       │
│                    │  Retrieval Pipeline    │                       │
│                    │ - Hybrid search        │                       │
│                    │ - Reranking (optional) │                       │
│                    │ - Injection detection  │                       │
│                    └───────────┬────────────┘                       │
│                                │                                     │
│        ┌───────────────────────┼───────────────────────┐            │
│        ▼                        ▼                       ▼            │
│  ┌──────────────┐  ┌────────────────────┐  ┌────────────────────┐  │
│  │  Self-Check  │  │  Entailment Check  │  │  Confidence Score  │  │
│  │ - Re-prompt  │  │  - NLI model       │  │  - Calibration     │  │
│  │ - Fact check │  │  - Verify claims   │  │  - Decision rule   │  │
│  └──────┬───────┘  └────────┬───────────┘  └────────┬───────────┘  │
│         │                   │                       │              │
│         └───────────────────┼───────────────────────┘              │
│                             ▼                                      │
│                    ┌────────────────────┐                         │
│                    │  Decision Module   │                         │
│                    │ - Should answer?   │                         │
│                    │ - Should refuse?   │                         │
│                    │ - Build response   │                         │
│                    └────────┬───────────┘                         │
│                             ▼                                      │
│                    ┌────────────────────┐                         │
│                    │  LLM Inference     │                         │
│                    │ - Mistral/Chat/HH  │                         │
│                    │ - Constrained gen. │                         │
│                    │ - Citation inject  │                         │
│                    └────────┬───────────┘                         │
│                             ▼                                      │
│                    ┌────────────────────┐                         │
│                    │ Post-Processing    │                         │
│                    │ - Format answer    │                         │
│                    │ - Add citations    │                         │
│                    │ - Score confidence │                         │
│                    │ - Build evidence   │                         │
│                    └────────┬───────────┘                         │
│                             ▼                                      │
│                    ┌────────────────────┐                         │
│                    │  Audit & Storage   │                         │
│                    │ - Log Q&A          │                         │
│                    │ - Track decisions  │                         │
│                    │ - Security events  │                         │
│                    └────────┬───────────┘                         │
│                             ▼                                      │
│                    ┌────────────────────┐                         │
│                    │  Final Response    │                         │
│                    │ - Answer text      │                         │
│                    │ - Citations        │                         │
│                    │ - Confidence score │                         │
│                    │ - Evidence chains  │                         │
│                    │ - Refusal reason   │                         │
│                    └────────────────────┘                         │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Components

### 2.1 Document Ingestion Layer

**Responsibility**: Parse DOCX files, extract text, maintain structure

**Key Classes**:
```python
class DocumentIngester:
    def ingest(doc_path: str) -> Document
    def extract_text() -> str
    def preserve_structure() -> List[Section]
    def validate() -> bool
    def log_ingestion() -> None

class Document:
    path: str
    name: str
    content: str
    sections: List[Section]
    metadata: Dict
    ingestion_date: datetime
```

**Implementation**:
- Use `python-docx` library for DOCX parsing
- Extract text while preserving section hierarchy
- Store document metadata (name, ingestion date, size, hash)
- Log all ingestion operations

**Dependencies**:
- `python-docx` (MIT license)

---

### 2.2 Security Filter Layer

**Responsibility**: Detect and flag potentially malicious content before indexing

**Key Components**:
```python
class SecurityFilter:
    def scan_content(text: str) -> SecurityReport
    def detect_injections(text: str) -> List[Injection]
    def detect_harmful_patterns(text: str) -> List[Pattern]
    def score_risk(text: str) -> float  # 0-1
    def log_threat(threat: Threat) -> None

class Injection:
    type: str  # "explicit", "implicit", "obfuscated"
    pattern: str
    location: str  # [doc, section, position]
    risk_score: float
    recommendation: str  # "block", "flag", "reduce_weight"
```

**Detection Strategies**:
1. **Pattern Matching**: Known injection keywords
   - "Ignore previous", "System prompt", "Instructions override", etc.
2. **Semantic Analysis**: Use small NLP model to detect instruction-like text
3. **Formatting Anomalies**: Unusual capitalization, hidden characters, suspicious formatting
4. **Obfuscation Detection**: ROT13, base64, reversed text, substitution ciphers

**Output**:
- ✓ Flag suspicious chunks
- ✓ Log threats with source location
- ✓ Reduce retrieval weight for risky chunks

**Dependencies**:
- Custom pattern database
- Small NLP model for semantic detection (optional)

---

### 2.3 Chunking & Embedding Layer

**Responsibility**: Split documents into semantic chunks, generate embeddings

**Key Classes**:
```python
class Chunker:
    def chunk_document(doc: Document, 
                      chunk_size: int = 300,
                      overlap: int = 50) -> List[Chunk]

class Chunk:
    id: str  # unique
    document_name: str
    section_path: str  # hierarchical reference
    text: str
    start_pos: int  # char position in doc
    page_num: int  # optional
    metadata: Dict

class EmbeddingGenerator:
    def __init__(model_name: str = "all-MiniLM-L6-v2")
    def embed_chunks(chunks: List[Chunk]) -> List[Embedding]
    def embed_query(query: str) -> Embedding

class Embedding:
    chunk_id: str
    vector: np.array  # 384-dim for all-MiniLM-L6-v2
    model: str
    timestamp: datetime
```

**Chunking Strategy**:
- Semantic chunking: Split on sentence/paragraph boundaries
- Fixed size: 300 tokens (~1000 chars) per chunk
- Overlap: 50 tokens for context preservation
- Preserve metadata: Document name, section, position

**Embedding Models** (options):
- `all-MiniLM-L6-v2` (384-dim, 22M params, fastest)
- `e5-small-v2` (384-dim, more accurate, slightly slower)
- `all-mpnet-base-v2` (768-dim, higher quality, slower)

**Dependencies**:
- `sentence-transformers` (MIT)
- `nltk` or `spacy` for tokenization

---

### 2.4 Vector Database & Retrieval

**Responsibility**: Store embeddings, enable fast semantic search

**Key Classes**:
```python
class VectorDB:
    def __init__(backend: str = "faiss")  # or "chroma"
    def add_chunks(chunks: List[Chunk], embeddings: List[np.array])
    def search(query_embedding: np.array, k: int = 5) -> List[RetrievalResult]
    def update_chunk(chunk_id: str, embedding: np.array)
    def save(path: str)
    def load(path: str)

class BM25Index:
    def __init__()
    def add_chunks(chunks: List[Chunk])
    def search(query: str, k: int = 5) -> List[RetrievalResult]

class RetrievalResult:
    chunk: Chunk
    dense_score: float  # cosine similarity
    sparse_score: float  # BM25 score
    combined_score: float  # weighted average
    rank: int
```

**Hybrid Retrieval Strategy**:
```
Dense Score = Cosine Similarity (query embedding vs. chunk embedding)
Sparse Score = BM25(query tokens vs. chunk tokens)
Combined Score = α × Dense_Score + (1-α) × Sparse_Score
               = 0.7 × Dense_Score + 0.3 × Sparse_Score  # default weights
```

**Benefits**:
- Dense: Captures semantic meaning
- Sparse: Matches keywords directly
- Hybrid: Best of both worlds

**Dependencies**:
- `faiss-cpu` or `faiss-gpu` (MIT)
- `rank-bm25` (MIT)
- Alternative: `chroma` (Apache 2.0, simpler API)

---

### 2.5 Retrieval Pipeline

**Responsibility**: Execute hybrid search, apply security filters, rank results

**Key Classes**:
```python
class RetrievalPipeline:
    def retrieve(query: str, k: int = 5, 
                 security_filter: bool = True) -> List[RetrievedChunk]
    def rank_results(results: List[RetrievalResult]) -> List[RetrievedChunk]
    def apply_security_filter(chunk: Chunk) -> float  # weight multiplier

class RetrievedChunk:
    chunk: Chunk
    score: float
    security_risk: float  # 0-1
    rank: int
    reasoning: str  # why this chunk was retrieved
```

**Execution Steps**:
1. **Embed Query**: Convert query to embedding vector
2. **Hybrid Search**: Run dense + sparse search, combine scores
3. **Security Filter**: Check for injections, reduce weight if risky
4. **Ranking**: Sort by combined score × security weight
5. **Top-K Selection**: Return top 3-5 chunks

---

### 2.6 Verification Layer

**Responsibility**: Check claims against evidence, detect hallucinations

**Key Components**:

#### 2.6.1 Entailment Checker
```python
class EntailmentChecker:
    def __init__(model_name: str = "microsoft/deberta-large-mnli")
    def check_entailment(claim: str, evidence: str) -> float  # 0-1
    def batch_check(claims: List[str], 
                   evidence_text: str) -> List[float]
```

**Model Options**:
- `microsoft/deberta-large-mnli` (high accuracy, larger)
- `roberta-large-mnli` (balanced)
- `cross-encoder/qnli-distilroberta-base` (smaller, faster)

#### 2.6.2 Self-Verification
```python
class SelfVerifier:
    def verify_answer(question: str, 
                     answer: str, 
                     evidence: str, 
                     llm: LLM) -> VerificationResult
    
class VerificationResult:
    claims: List[Claim]
    hallucination_detected: bool
    hallucination_count: int
    faithfulness_score: float  # 0-1
    reasoning: str
```

**Process**:
1. Extract claims from generated answer
2. For each claim, check entailment with evidence
3. Flag unsupported or contradictory claims
4. Compute overall faithfulness score

---

### 2.7 Decision Module

**Responsibility**: Decide whether to answer, refuse, or modify

**Key Classes**:
```python
class DecisionModule:
    def should_answer(confidence: float, 
                     hallucination_risk: float,
                     injection_risk: float) -> bool
    def should_refuse(question: str, 
                     retrieved_chunks: List[Chunk]) -> bool
    def get_refusal_reason(context: Dict) -> str

class Decision:
    action: str  # "answer", "refuse", "modify"
    confidence: float
    reasoning: str
    recommended_refusal_reason: str  # if refusing
```

**Decision Logic**:
```python
if injection_risk > 0.5:
    decision = "refuse"
    reason = "Potential injection detected in content"
elif hallucination_risk > 0.3:
    decision = "refuse"
    reason = "Insufficient confidence in answer"
elif confidence < 0.7:
    decision = "refuse"
    reason = "Low confidence in retrieved evidence"
elif relevance_score < 0.5:
    decision = "refuse"
    reason = "Question outside document scope"
else:
    decision = "answer"
```

---

### 2.8 LLM Inference Engine

**Responsibility**: Generate answers using local LLM, with safety constraints

**Key Classes**:
```python
class LLMEngine:
    def __init__(model_name: str, 
                 device: str = "cuda",  # or "cpu"
                 quantization: str = "int4"):
    def generate_answer(question: str, 
                       context: str,
                       prompt_template: str) -> GenerationResult
    def constrain_generation(constraints: Dict) -> None

class GenerationResult:
    answer: str
    generation_tokens: int
    inference_time: float
    temperature: float
    top_p: float
```

**Supported Models**:
- `mistralai/Mistral-7B-Instruct-v0.2`
- `Intel/neural-chat-7b-v3-1`
- `teknium/OpenHermes-2.5-Mistral-7B`

**Quantization Options**:
- `int4`: 4-bit, ~3.5-4GB VRAM, fast
- `int8`: 8-bit, ~5-6GB VRAM, balanced
- `float16`: Full precision, ~14GB VRAM, highest quality

**Prompt Template**:
```
[Context about policy documents]

Retrieved relevant information:
{retrieved_chunks_text}

Question: {question}

Instructions:
- Answer based ONLY on the provided information
- If information is not available, say "I don't have that information"
- Be precise and concise
- Always cite your sources

Answer:
```

**Generation Parameters**:
- `temperature: 0.3` (low, for consistency)
- `top_p: 0.9` (high quality)
- `max_new_tokens: 300` (reasonable length)
- `repetition_penalty: 1.1` (avoid repetition)

**Dependencies**:
- `transformers` (Apache 2.0)
- `torch` (BSD)
- `bitsandbytes` (optional, for int4 quantization)
- `llama-cpp-python` (optional, for CPU optimization)

---

### 2.9 Post-Processing & Citation Engine

**Responsibility**: Format answer, add citations, build evidence chains

**Key Classes**:
```python
class CitationEngine:
    def generate_citations(answer: str, 
                          retrieved_chunks: List[Chunk],
                          evidence: Dict) -> List[Citation]
    def build_evidence_chain(answer: str) -> EvidenceChain

class Citation:
    claim: str
    source_doc: str
    section: str
    quote: str
    confidence: float

class EvidenceChain:
    question: str
    answer: str
    citations: List[Citation]
    alternative_evidence: List[Chunk]  # other relevant chunks
    refusal_reason: str  # if refused
```

**Post-Processing Steps**:
1. **Extract Claims**: Identify all factual statements in answer
2. **Link to Evidence**: Match each claim to retrieved chunks
3. **Build Citations**: Create structured citations with doc/section/quote
4. **Format Output**: Inline citations in answer text
5. **Confidence Calibration**: Compute final confidence score

---

### 2.10 Audit & Logging Layer

**Responsibility**: Maintain immutable log of all system operations

**Key Classes**:
```python
class AuditLogger:
    def log_qa(qa_entry: QAEntry) -> None
    def log_security_event(event: SecurityEvent) -> None
    def log_refusal(refusal: Refusal) -> None
    def query_logs(filters: Dict) -> List[LogEntry]

class QAEntry:
    timestamp: datetime
    question: str
    answer: str
    confidence: float
    decision: str  # "answered", "refused"
    refusal_reason: str  # if applicable
    retrieved_chunks: List[Chunk]
    citations: List[Citation]
    user_id: str  # if available
    session_id: str

class SecurityEvent:
    timestamp: datetime
    event_type: str  # "injection_detected", "harmful_content"
    severity: str  # "low", "medium", "high"
    document: str
    chunk_id: str
    pattern: str
    action_taken: str
    user_id: str
```

**Storage**:
- File-based: JSON log file (simple, audit-friendly)
- Database: SQLite or PostgreSQL (queryable, scalable)

---

## 3. Data Flow Diagrams

### 3.1 Document Ingestion Flow

```
User Uploads DOCX File
    ↓
[Validation] → Valid? → Yes ↓
                    → No → Error Message
                           ↓
                      [Skip File]
                           │
                           ↓
                    [Security Scan] → Threats Found?
                           │               │
                           ├─ Yes → Log Threat, Reduce Weight
                           │
                           No (or Flagged)
                           ↓
                    [Extract Text]
                           ↓
                    [Split into Sections]
                           ↓
                    [Create Chunks]
                           ↓
                    [Generate Embeddings]
                           ↓
                    [Add to Vector DB]
                           ↓
                    [Index with BM25]
                           ↓
                    [Log Ingestion]
                           ↓
                    Success Confirmation
```

---

### 3.2 Question Answering Flow

```
User Input: Question
    ↓
[Embed Question]
    ↓
[Hybrid Retrieval: Dense + Sparse] → Retrieve Top 5
    ↓
[Security Filter] → Check for injections → Apply weights
    ↓
[Rank by Score + Security]
    ↓
[Extract Claims from Question]
    ↓
╔════════════════════════════════════╗
║  Verification Layer (Parallel)      ║
║  ┌─────────────────────────────────┐║
║  │ 1. Entailment Check             ││
║  │    Check: Evidence supports?    ││
║  │    Output: Faithfulness score   ││
║  └─────────────────────────────────┘║
║  ┌─────────────────────────────────┐║
║  │ 2. Self-Verification            ││
║  │    Re-prompt: Fact-check answer ││
║  │    Output: Hallucination flags  ││
║  └─────────────────────────────────┘║
║  ┌─────────────────────────────────┐║
║  │ 3. Relevance Scoring            ││
║  │    Check: Evidence relevant?    ││
║  │    Output: Relevance score      ││
║  └─────────────────────────────────┘║
╚════════════════════════════════════╝
    ↓
[Decision Module]
    ├─ High Injection Risk? → REFUSE
    ├─ Low Confidence? → REFUSE
    ├─ Out of Scope? → REFUSE
    └─ Otherwise → ANSWER
    ↓
[IF REFUSE]
    ├─ Explain Reason
    ├─ Suggest Clarification
    └─ Log Refusal
        ↓
      Return Refusal Response
    ↓
[IF ANSWER]
    ├─ Generate with LLM
    ├─ Add Citations
    ├─ Build Evidence Chains
    ├─ Compute Confidence
    └─ Log Q&A Entry
        ↓
      Return Full Response
```

---

## 4. Technology Stack

### 4.1 Backend & Core

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Language** | Python 3.10+ | Best NLP ecosystem; easy deployment |
| **Package Mgmt** | Poetry or pip | Lock files for reproducibility |
| **Async** | FastAPI | Modern, async-capable REST API |
| **Logging** | `logging` + structured logs | Built-in; audit-friendly |

### 4.2 Document Processing

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **DOCX Parse** | `python-docx` (MIT) | Handles Word structure |
| **Tokenization** | `nltk` or `spacy` | Standard NLP tools |
| **Text Cleaning** | Custom utilities | Remove artifacts, normalize |

### 4.3 Embeddings & Retrieval

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Embeddings** | `sentence-transformers` (MIT) | Lightweight, fast, effective |
| **Vector DB** | FAISS or Chroma (MIT/Apache) | FAISS for speed; Chroma for simplicity |
| **Sparse Search** | `rank-bm25` (MIT) | Simple, effective keyword search |

### 4.4 LLM & Inference

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **LLM Framework** | `transformers` (Apache 2.0) | Standard, flexible, well-supported |
| **Quantization** | `bitsandbytes` (optional) | Enable int4 for memory efficiency |
| **Inference** | PyTorch or ONNX | Standard formats; good performance |

### 4.5 Verification & NLP

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Entailment** | `microsoft/deberta-large-mnli` | State-of-the-art NLI |
| **Fact Check** | Custom verification pipeline | Re-prompt LLM + entailment |

### 4.6 API & UI

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **REST API** | FastAPI | Modern, automatic docs, async support |
| **Web UI** | Streamlit (Apache 2.0) | Simple, interactive, great for demos |
| **Authentication** | FastAPI Security + JWT | Standard, easy to implement |

### 4.7 Storage

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Logs** | JSON files or SQLite | Local storage; audit-friendly |
| **Config** | YAML/JSON + Pydantic | Type-safe configuration |
| **Vector Index** | FAISS binary files | Efficient storage and loading |

---

## 5. Security Architecture

### 5.1 Threat Model

**Threats Addressed**:
1. **Direct Prompt Injection**: Malicious instructions in documents
2. **Indirect Injection**: Hidden instructions in content
3. **Data Extraction**: Attempting to leak unrelated information
4. **Adversarial Input**: Crafted questions to trigger misbehavior
5. **Unauthorized Access**: API accessed without credentials

### 5.2 Defense Mechanisms

| Threat | Defense Mechanism |
|--------|-------------------|
| **Injection** | Content filtering, pattern detection, weighted reduction |
| **Extraction** | Scope limiting, refusal when outside domain |
| **Adversarial Input** | Input validation, confidence thresholds, refusal |
| **Unauthorized Access** | API authentication (API key), rate limiting |
| **Data Leakage** | Local-only deployment, no cloud upload |

---

## 6. Deployment Architecture

### 6.1 Self-Hosted Deployment

```
┌─────────────────────────────────────────────┐
│         Organization Server / PC             │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │     SecureHall-RAG Application       │  │
│  │  ┌────────────────────────────────┐  │  │
│  │  │ FastAPI Server (Port 5000)     │  │  │
│  │  │ - REST API Endpoints           │  │  │
│  │  │ - Authentication               │  │  │
│  │  │ - Rate Limiting                │  │  │
│  │  └────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────┐  │  │
│  │  │ Streamlit UI (Port 8501)       │  │  │
│  │  │ - Web Interface                │  │  │
│  │  │ - Document Management          │  │  │
│  │  │ - Q&A Interface                │  │  │
│  │  └────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────┐  │  │
│  │  │ RAG Engine (Core Logic)        │  │  │
│  │  │ - Ingestion, Retrieval, LLM    │  │  │
│  │  │ - Verification, Logging        │  │  │
│  │  └────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────┐  │  │
│  │  │ Local Storage                  │  │  │
│  │  │ - Vector DB (FAISS)            │  │  │
│  │  │ - Config files                 │  │  │
│  │  │ - Audit logs                   │  │  │
│  │  │ - Model weights (quantized)    │  │  │
│  │  └────────────────────────────────┘  │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  Optional Hardware:                         │
│  - GPU (4GB+ VRAM, e.g., NVIDIA A10)       │
│  - CPU Fallback (for deployments w/o GPU) │
│  - SSD (for fast index loading)            │
│                                             │
└─────────────────────────────────────────────┘
```

### 6.2 Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 4 cores | 8+ cores |
| **RAM** | 8 GB | 16+ GB |
| **GPU** | None (CPU only) | 4GB VRAM (e.g., GTX 1050) |
| **Storage** | 20 GB | 50+ GB |
| **Network** | None (local) | Optional for updates |

### 6.3 Network Isolation

**Default**: Fully local (no external connections)

**Optional**: 
- Intranet deployment (within organization)
- VPN-gated access
- No internet required (offline capable)

---

## 7. Integration Points

### 7.1 REST API for External Systems

```python
# Example: Slack Bot Integration
POST /api/v1/query
{
    "question": "How many days of PTO do I get?",
    "context": {"user_id": "slack_user_123", "session": "slack"}
}

Response:
{
    "answer": "You are entitled to 20 days of PTO annually...",
    "citations": [
        {"doc": "Leave_Policy.docx", "section": "1. Annual Leave", "quote": "..."}
    ],
    "confidence": 0.94,
    "refusal_reason": null
}
```

### 7.2 Admin Dashboard

Metrics and insights:
- System health (uptime, performance)
- Q&A statistics (volume, success rate)
- Security events (injections detected)
- Document corpus status
- Top questions

---

## 8. Scalability Considerations

### 8.1 Horizontal Scaling

- Multiple API servers behind load balancer
- Shared FAISS index (read-only replicas)
- Redis for caching and rate limiting

### 8.2 Vertical Scaling

- Larger GPU (8GB, 16GB)
- More CPU cores for parallel processing
- Larger models (13B instead of 7B)

### 8.3 Index Scaling

- Sharding: Multiple FAISS indices per document set
- Incremental indexing: Add documents without full reindex
- Compression: Store embeddings efficiently

---

## 9. Testing Strategy

### 9.1 Unit Tests

- Chunking logic
- Embedding generation
- Citation generation
- Refusal decision logic

### 9.2 Integration Tests

- Document ingestion → embedding → retrieval
- Q&A pipeline end-to-end
- Security filter effectiveness
- API endpoints

### 9.3 Evaluation Tests

- Citation accuracy (>95%)
- Hallucination rate (<5%)
- Prompt injection detection (>95% precision)
- Refusal F1 (>0.85)

---

## 10. Success Criteria (Phase 1)

✅ **Architecture Designed**: All components specified with rationale  
✅ **Data Flows Clear**: Ingestion and Q&A flows documented  
✅ **Tech Stack Chosen**: Justified decisions for all components  
✅ **Security Integrated**: Threat model and defenses defined  
✅ **Feasibility Confirmed**: Can be implemented in Phase 2  

---

## Next Steps

→ Task 1.8: GitHub Repository Setup (code structure, CI/CD)  
→ Task 1.9: Project Timeline & Milestones  
→ Task 1.10: Phase 1 Report (comprehensive summary)  
→ Phase 2: Implementation (build the system)
