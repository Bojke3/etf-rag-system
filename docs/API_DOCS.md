# API Documentation

## 🌐 Web API

### Base URL
```
http://localhost:8000/api/v1
```

### Authentication

Currently no authentication required (dev mode).

---

## Endpoints

### 1. Query - Ask a Question

**Endpoint**: `POST /query`

**Request**:
```json
{
  "question": "Koja je trajanje osnovnih studija?",
  "context_window": 5,
  "model": "mistral",
  "prompt_strategy": "few-shot",
  "include_sources": true
}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "answer": "Osnovne studije traju 4 godine.",
  "confidence": 0.92,
  "sources": [
    {
      "document": "study_program_2024.pdf",
      "page": 5,
      "excerpt": "Trajanje osnovnih studija je 4 godine...",
      "relevance_score": 0.95
    }
  ],
  "processing_time_ms": 1250,
  "retrieved_chunks": 5
}
```

---

### 2. Batch Query - Multiple Questions

**Endpoint**: `POST /batch-query`

**Request**:
```json
{
  "questions": [
    "Koja je trajanje osnovnih studija?",
    "Koji su uslovi za upis na master?"
  ],
  "context_window": 5
}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "results": [
    {"question": "...", "answer": "...", "sources": []},
    {"question": "...", "answer": "...", "sources": []}
  ],
  "total_time_ms": 2500
}
```

---

### 3. Search Documents

**Endpoint**: `POST /search`

**Request**:
```json
{
  "query": "master studije",
  "top_k": 5,
  "threshold": 0.7
}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "results": [
    {
      "rank": 1,
      "document": "master_program_2024.pdf",
      "chunk_id": "chunk_001",
      "score": 0.95,
      "text": "Master program u trajanju od 1-2 godine..."
    }
  ],
  "search_time_ms": 45
}
```

---

### 4. Document Upload

**Endpoint**: `POST /documents/upload`

**Request** (multipart/form-data):
```
File: document.pdf
Category: studies
Metadata: {"year": 2024}
```

**Response** (201 Created):
```json
{
  "status": "success",
  "document_id": "doc_12345",
  "filename": "study_program_2024.pdf",
  "chunks_created": 24,
  "processing_time_ms": 5000
}
```

---

### 5. List Documents

**Endpoint**: `GET /documents`

**Query Parameters**:
- `category`: Filter by category (studies, master, phd, other)
- `limit`: Number of results (default: 20)
- `offset`: Pagination offset (default: 0)

**Response** (200 OK):
```json
{
  "status": "success",
  "documents": [
    {
      "id": "doc_001",
      "filename": "study_program_2024.pdf",
      "category": "studies",
      "uploaded_at": "2026-05-11T10:30:00Z",
      "chunks": 24,
      "size_bytes": 2500000
    }
  ],
  "total": 15,
  "limit": 20,
  "offset": 0
}
```

---

### 6. Get Models

**Endpoint**: `GET /models`

**Response** (200 OK):
```json
{
  "status": "success",
  "llm_models": [
    {"name": "mistral", "size": "7B", "available": true},
    {"name": "llama2", "size": "7B", "available": true}
  ],
  "embedding_models": [
    {"name": "all-MiniLM-L6-v2", "size": "22MB", "available": true}
  ]
}
```

---

### 7. Health Check

**Endpoint**: `GET /health`

**Response** (200 OK):
```json
{
  "status": "healthy",
  "components": {
    "database": "ok",
    "vector_store": "ok",
    "llm_service": "ok",
    "embedding_service": "ok"
  }
}
```

---

## Error Handling

### Error Response Format

```json
{
  "status": "error",
  "error_code": "INVALID_QUERY",
  "message": "Query is empty",
  "details": "Query parameter is required and must not be empty"
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| INVALID_QUERY | 400 | Query is invalid or empty |
| NOT_FOUND | 404 | Resource not found |
| UNAUTHORIZED | 401 | Authentication required |
| FORBIDDEN | 403 | Access denied |
| SERVICE_UNAVAILABLE | 503 | LLM service unavailable |
| INTERNAL_ERROR | 500 | Internal server error |

---

## Rate Limiting

- **Free tier**: 100 requests/day
- **Pro tier**: 1000 requests/day (planned)
- **Enterprise**: Unlimited (planned)

**Response Header**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1620000000
```

---

## Examples

### Python Client

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# Ask a question
response = requests.post(
    f"{BASE_URL}/query",
    json={
        "question": "Koja je trajanje osnovnih studija?",
        "include_sources": True
    }
)

data = response.json()
print(f"Answer: {data['answer']}")
print(f"Confidence: {data['confidence']}")
for source in data['sources']:
    print(f"Source: {source['document']} (p. {source['page']})")
```

### cURL

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Koja je trajanje osnovnih studija?",
    "include_sources": true
  }'
```

### JavaScript/Node.js

```javascript
const fetch = require('node-fetch');

const response = await fetch('http://localhost:8000/api/v1/query', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    question: 'Koja je trajanje osnovnih studija?',
    include_sources: true
  })
});

const data = await response.json();
console.log('Answer:', data.answer);
```

---

## WebSocket API (Real-time)

**Connection**: `ws://localhost:8000/ws`

**Subscribe to query stream**:
```json
{
  "action": "subscribe_query",
  "question": "Koja je trajanje osnovnih studija?"
}
```

**Real-time updates**:
```json
{
  "event": "retrieval_complete",
  "chunks": 5,
  "processing_time_ms": 45
}
```

```json
{
  "event": "generation_start",
  "model": "mistral"
}
```

```json
{
  "event": "generation_complete",
  "answer": "Osnovne studije traju 4 godine.",
  "total_time_ms": 1250
}
```

---

## Versioning

API versioning is done via URL path:
- `/api/v1` - Current version
- `/api/v2` - Future version (TBD)

---

## Changelog

### v1.0.0 (2026-06-01)
- Initial API release
- Query endpoint
- Search endpoint
- Document management

---

## Support

For API issues, please:
1. Check this documentation
2. Open a GitHub issue: https://github.com/Bojke3/etf-rag-system/issues
3. Contact the team
