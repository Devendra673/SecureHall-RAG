# Verification RAG System - UI Architecture

## System Overview

The Verification RAG System UI is built on a modular architecture connecting:
1. **RAG Pipeline** - Document retrieval and answer generation
2. **Verification Pipeline** - Claim extraction and verification
3. **Response Builder** - Standardization of output
4. **Streamlit Frontend** - User interface

## Architecture Diagram

```
User Query Input
       |
       v
RAG Pipeline (retrieval + generation)
       |
       +-> HybridRetriever (dense + sparse search)
       +-> LLMInference (answer generation)
       |
       v
Raw Answer Output
       |
       v
Verification Pipeline
       |
       +-> ClaimSplitter (extract claims)
       +-> ClaimExtractor (extract metadata)
       +-> EvidenceRetriever (find supporting evidence)
       +-> SupportScorer (score claims)
       +-> RefusalThreshold (make decisions)
       +-> AnswerAssembler (assemble verified answer)
       |
       v
VerifiedAnswer (internal representation)
       |
       v
Response Builder
       |
       +-> VerificationResponse (standardized API format)
       |
       v
Streamlit UI Display
       |
       +-> Answer section
       +-> Metrics display
       +-> Claims with citations
       +-> Evidence snippets
```

## Component Responsibilities

### 1. RAG Pipeline (`src/rag_pipeline.py`)
**Purpose**: Retrieve relevant documents and generate initial answer

**Key Methods**:
- `ingest_documents()` - Index uploaded documents
- `retrieve()` - Find relevant documents for query
- `generate()` - Generate answer using LLM with context

**Outputs**: Raw answer text

### 2. Verification Pipeline

#### ClaimSplitter (`src/verification/claim_splitter.py`)
Breaks answer into individual claims at sentence/clause boundaries.

#### ClaimExtractor (`src/verification/claim_extractor.py`)
Extracts metadata from claims:
- Named entities
- Claim type (factual, procedural, etc.)
- Complexity scoring
- Main predicates

#### EvidenceRetriever (`src/verification/evidence_retriever.py`)
For each claim, retrieves supporting evidence chunks.

#### SupportScorer (`src/verification/support_scorer.py`)
Scores support for each claim using:
- BM25 keyword overlap (30%)
- Semantic similarity (40%)
- Optional NLI scoring (30%)

**Output**: Support scores and conflict detection

#### RefusalThreshold (`src/verification/refusal_threshold.py`)
Makes accept/partial/refuse decisions based on:
- Support scores
- Configured threshold strategy
- Conflict detection

**Output**: Verification decisions

#### AnswerAssembler (`src/verification/answer_assembler.py`)
Combines all information into VerifiedAnswer:
- Filters claims by decision
- Generates citations with spans
- Calculates confidence metrics

**Output**: `VerifiedAnswer` dataclass

### 3. Response Builder (`src/ui/response_builder.py`)
Converts `VerifiedAnswer` to standardized `VerificationResponse` format:

**Responsibilities**:
- Flatten nested claim structures
- Convert enums to strings
- Collect evidence snippets
- Add metadata

**Output**: `VerificationResponse` dataclass

### 4. Streamlit UI (`src/ui/app.py`)
Main user interface coordinating all components.

**Key Sections**:
- Query input area
- Configuration sidebar
- Answer display with metrics
- Claims with decision indicators
- Evidence snippets viewer
- Citation details

## Data Flow

### Query Processing Flow

```
1. User enters query in UI
   |
2. VerificationRAGApp.process_query() called
   |
3. RAG Pipeline retrieval phase
   ├─ retrieve(query) -> list[SearchResult]
   └─ generate(context, query) -> str (raw answer)
   |
4. Verification phase
   ├─ claim_splitter.split_sentences() -> list[str]
   ├─ For each claim:
   │  ├─ claim_extractor.extract() -> ClaimMetadata
   │  ├─ evidence_retriever.retrieve_for_claim() -> EvidenceSet
   │  ├─ support_scorer.score() -> SupportScore
   │  └─ refusal_threshold.decide() -> (SupportLevel, Decision)
   |
5. Answer assembly phase
   └─ answer_assembler.assemble_answer() -> VerifiedAnswer
   |
6. Response standardization
   └─ response_builder.build_verification_response() -> VerificationResponse
   |
7. UI display phase
   └─ app.display_response(response)
```

## Key Data Structures

### Citation (`src/verification/data_structures.py`)
```python
@dataclass
class Citation:
    claim_id: str
    evidence_chunk_id: str
    evidence_text: str
    source: str
    relevance_score: float
    span_start: Optional[int] = None
    span_end: Optional[int] = None
```

### VerificationResponse
```python
@dataclass
class VerificationResponse:
    answer_text: str
    claims: List[Dict]  # Serialized claim data
    citations: List[Dict]  # Flattened citations
    evidence_snippets: Dict[str, str]  # chunk_id -> text
    metadata: Dict[str, Any]
```

## Integration Points

### Document Ingestion
1. UI displays file upload in sidebar
2. `RAGPipeline.ingest_documents(file_paths)` processes files
3. Documents are chunked, embedded, and indexed

### Query Processing
1. User submits query via UI text area
2. `VerificationRAGApp.process_query(query)` orchestrates pipeline
3. All components execute in sequence
4. Response returned to UI for display

### Response Display
1. `VerificationResponse.to_dict()` serializes response
2. `display_response()` renders each component
3. Claims color-coded by decision
4. Citations expandable for detail viewing

## Error Handling

**Query Processing Errors**:
- Caught in `process_query()` and displayed to user
- Includes error message and troubleshooting suggestions

**Invalid Response Format**:
- Caught during response building
- Falls back to minimal response structure

**UI Display Errors**:
- Handled at component level
- Missing fields gracefully omitted

## Performance Characteristics

### Latency Targets
- Retrieval: <150ms
- Answer generation: <5s
- Verification pipeline: <500ms
- Total end-to-end: <10s

### Scalability
- Handles up to 1000 documents in knowledge base
- Supports queries with up to 100+ claims
- Response display optimized for 50+ claims

## Extension Points

### Custom Verification Strategies
1. Create new threshold configuration in `RefusalThreshold`
2. Register strategy in UI sidebar dropdown
3. Pass strategy to `decide()` method

### Alternative LLM Models
1. Update `LLMInference` with new model adapter
2. Select model in UI sidebar
3. System handles rest of pipeline

### Custom Highlighting
1. Extend `highlight_engine.py` with new matching algorithms
2. Update UI evidence snippet rendering
3. Customize CSS classes for styling

## Testing Strategy

### Unit Tests
- Individual component testing (claim splitter, scorers, etc.)
- Response builder serialization
- Citation format validation

### Integration Tests (`tests/test_ui_integration.py`)
- Mock response structure validation
- Decision mapping consistency
- Evidence snippet mapping

### End-to-End Testing (Planned)
- Full query-to-display pipeline
- UI interaction testing with Selenium
- Performance benchmarking

## Configuration

### Streamlit Config (`src/ui/app.py`)
```python
st.set_page_config(
    page_title="Verification RAG System",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)
```

### Verification Strategy
Selectable in UI sidebar with options:
- Balanced (default)
- Conservative
- Permissive
- High Recall

### Model Selection
Configurable LLM in sidebar:
- Mistral (default)
- Llama2
- Custom models

## Deployment

### Local Deployment
```bash
python scripts/run_ui.py
```

### Docker Deployment (Future)
```dockerfile
FROM python:3.10
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "src/ui/app.py"]
```

## Future Enhancements

### Phase 5.6 - Confidence Indicators
- Visual confidence scale (red/yellow/green)
- Warning badges for low-confidence claims
- Refusal reason explanations

### Phase 5.7 - Evidence Highlighting
- Highlight evidence text within source documents
- Show surrounding context
- Support for multi-page evidence display

### Phase 5.8 - Document Management
- View indexed documents
- Delete/update documents
- Search indexed content

### Phase 5.9 - Admin Dashboard
- Threshold configuration interface
- Model performance metrics
- Query history and analytics

---

**Version**: 1.0  
**Last Updated**: May 31, 2026  
**Status**: Production Ready
