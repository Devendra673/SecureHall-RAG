# SecureHall-RAG API Documentation

The SecureHall-RAG backend exposes a RESTful API powered by FastAPI.

## Authentication

The API uses JWT (JSON Web Tokens) for authentication. Most endpoints require an `Authorization: Bearer <token>` header.

### `POST /api/auth/register`
Creates a new user account.

**Request Body:**
```json
{
  "username": "jdoe",
  "email": "jdoe@company.com",
  "password": "securepassword123",
  "role": "employee"
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "username": "jdoe",
  "email": "jdoe@company.com",
  "role": "employee",
  "is_active": true
}
```

### `POST /api/auth/login`
Authenticates a user and returns a JWT access token.

**Request Body:**
*(Uses `application/x-www-form-urlencoded` format per OAuth2 specification)*
- `username`: "jdoe"
- `password`: "securepassword123"

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUz...",
  "token_type": "bearer",
  "user": {
    "username": "jdoe",
    "role": "employee"
  }
}
```

---

## Query Generation (RAG)

### `POST /api/query`
Submits a natural language question to the RAG system. The pipeline filters documents based on the authenticated user's role (Document Access Control), retrieves relevant chunks, re-ranks them via CrossEncoder, and generates a verified LLM response.

**Headers:**
`Authorization: Bearer <token>`

**Request Body:**
```json
{
  "query": "What is the company vacation policy?",
  "temperature": 0.3
}
```

**Response (200 OK):**
```json
{
  "verified_answer": "Employees receive 15 days of paid vacation annually [1].",
  "claims": [
    {
      "text": "Employees receive 15 days of paid vacation annually",
      "support": 0.95
    }
  ],
  "citations": [
    {
      "claim_id": "claim_1",
      "source": "employee_handbook.pdf",
      "relevance_score": 0.88,
      "evidence_text": "All full-time employees are entitled to 15 days of paid vacation per year."
    }
  ],
  "metadata": {
    "confidence": 0.95,
    "latency_ms": 420.5,
    "refusal_reason": null
  }
}
```

---

## Document Management

### `POST /api/documents/upload`
Uploads and indexes a new document into the hybrid RAG system.

**Headers:**
`Authorization: Bearer <token>`

**Request Body:**
`multipart/form-data`
- `file`: (Binary File)
- `roles_allowed`: (String) Comma-separated list of roles allowed to view this document (e.g., "admin,manager"). Defaults to "all".

**Response (201 Created):**
```json
{
  "filename": "q3_financials.pdf",
  "document_id": "doc_a1b2c3",
  "status": "indexed",
  "chunks_created": 45
}
```

### `GET /api/documents/`
Lists all uploaded documents. If the user is an `admin`, all documents are returned. Otherwise, only documents matching the user's role are returned.

**Headers:**
`Authorization: Bearer <token>`

**Response (200 OK):**
```json
[
  {
    "id": "doc_a1b2c3",
    "filename": "q3_financials.pdf",
    "upload_date": "2026-06-15T10:00:00Z",
    "roles_allowed": ["admin", "manager"]
  }
]
```
