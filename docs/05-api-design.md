# API Design Guide

**Project:** Enterprise AI Knowledge Platform  
**API Version:** v1  
**Base URL:** `http://localhost:8000/api/v1`  
**Last Updated:** July 2026

---

## 1. Design Principles

This API follows these principles:

1. **RESTful resources** — URLs identify resources; HTTP verbs express actions
2. **Consistent error envelopes** — every error has the same JSON shape
3. **Versioning via URL prefix** — `/api/v1/...` protects consumers from breaking changes
4. **Pagination on all list endpoints** — never return unbounded collections
5. **UUID identifiers** — no sequential IDs; safe to generate client-side
6. **UTC timestamps** — all datetimes in ISO 8601 with UTC timezone marker

---

## 2. Base URL & Versioning

```
https://api.yourdomain.com/api/v1
```

The `/api/v1` prefix is intentional:
- `/api` — separates API from static file serving (nginx can route them differently)
- `/v1` — allows breaking changes to ship as `/api/v2` without removing v1

---

## 3. Authentication

> Phase 1: No authentication. All endpoints are open.  
> Phase 4: Bearer JWT token in `Authorization` header.

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 4. Request & Response Conventions

### Content Type

All requests and responses use `application/json`.  
File uploads use `multipart/form-data`.

### Pagination

List endpoints accept:

| Parameter | Type | Default | Max | Description |
|---|---|---|---|---|
| `limit` | integer | 50 | 200 | Number of items per page |
| `offset` | integer | 0 | — | Number of items to skip |

Pagination envelope (Phase 2+):
```json
{
  "data": [...],
  "pagination": {
    "total": 1247,
    "limit": 50,
    "offset": 0,
    "has_more": true
  }
}
```

### Timestamps

All timestamps are ISO 8601 strings in UTC:
```json
"created_at": "2026-07-31T14:32:10.123Z"
```

### Identifiers

All resource IDs are UUIDs v4:
```json
"id": "550e8400-e29b-41d4-a716-446655440000"
```

---

## 5. Error Responses

All errors follow the same envelope. Never inspect HTTP status code alone.

### Error envelope

```json
{
  "error": {
    "message": "Human-readable description suitable for logging or display.",
    "code":    "MACHINE_READABLE_CODE",
    "detail":  {}
  }
}
```

### Error codes

| HTTP Status | Code | When |
|---|---|---|
| 400 | `BAD_REQUEST` | Malformed JSON, invalid query params |
| 404 | `NOT_FOUND` | Resource with given ID does not exist |
| 409 | `CONFLICT` | Duplicate resource (unique constraint violation) |
| 422 | `VALIDATION_ERROR` | Request body fails schema validation |
| 429 | `RATE_LIMITED` | Too many requests (Phase 4) |
| 500 | `INTERNAL_ERROR` | Unexpected server error |
| 503 | `SERVICE_UNAVAILABLE` | Dependency check failed (readiness probe) |

### Example error response

```http
HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "error": {
    "message": "Document '550e8400-e29b-41d4-a716-446655440000' was not found.",
    "code":    "NOT_FOUND",
    "detail":  {}
  }
}
```

---

## 6. Current Endpoints (Phase 1)

### Health — Liveness Probe

```http
GET /api/v1/health
```

Returns 200 if the process is alive. No authentication required. No external I/O.

**Response 200:**
```json
{
  "status": "healthy",
  "environment": "development",
  "version": "0.1.0",
  "uptime_seconds": 128.5
}
```

---

### Health — Readiness Probe

```http
GET /api/v1/health/ready
```

Returns 200 only if all critical dependencies are reachable. Returns 503 otherwise.
No authentication required.

**Response 200:**
```json
{
  "status": "ready",
  "dependencies": {
    "api": {
      "status": "healthy",
      "detail": null,
      "latency_ms": null
    }
  }
}
```

**Response 503:**
```json
{
  "status": "not_ready",
  "dependencies": {
    "api":      { "status": "healthy" },
    "database": { "status": "unhealthy", "detail": "Connection timeout after 5000ms" }
  }
}
```

---

## 7. Planned Endpoints (Phase 2+)

> These are planned. Schemas are subject to change during implementation.

### Knowledge Bases

```http
POST   /api/v1/knowledge-bases          Create a knowledge base
GET    /api/v1/knowledge-bases          List knowledge bases
GET    /api/v1/knowledge-bases/{id}     Get a knowledge base
PATCH  /api/v1/knowledge-bases/{id}     Update a knowledge base
DELETE /api/v1/knowledge-bases/{id}     Delete a knowledge base
```

### Documents

```http
POST   /api/v1/documents                Upload a document (multipart)
GET    /api/v1/documents                List documents
GET    /api/v1/documents/{id}           Get document + processing status
DELETE /api/v1/documents/{id}           Delete a document
```

### Query (Phase 3)

```http
POST   /api/v1/query                    Submit a natural language query
GET    /api/v1/query/{id}               Retrieve a stored query + answer
```

Query request body:
```json
{
  "query":             "What is the on-call rotation policy?",
  "knowledge_base_id": "550e8400-e29b-41d4-a716-446655440000",
  "top_k":             5,
  "stream":            false
}
```

Query response body:
```json
{
  "id":        "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "answer":    "The on-call rotation follows a weekly schedule...",
  "citations": [
    {
      "chunk_id":    "...",
      "document_id": "...",
      "title":       "Engineering On-Call Handbook",
      "page":        3,
      "excerpt":     "Rotations are assigned each Monday at 09:00 UTC..."
    }
  ],
  "latency_ms":     1823,
  "tokens_used":    412
}
```

---

## 8. OpenAPI Documentation

Interactive API documentation is available at runtime:

| Environment | URL |
|---|---|
| Development | `http://localhost:8000/api/docs` (Swagger UI) |
| Development | `http://localhost:8000/api/redoc` (ReDoc) |
| Production | Disabled (reduces attack surface) |

The OpenAPI JSON schema is served at `/api/openapi.json` in development.
