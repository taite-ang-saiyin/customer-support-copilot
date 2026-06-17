# API Specification

## Overview

This document describes the internal API for the RAG and Knowledge Base service.

All `/knowledge` endpoints require:

```http
X-API-Key: your-internal-key
```

Missing or invalid API keys return `401`.

Set `API_KEY_AUTH_ENABLED=false` only for local debugging if you need to temporarily disable this check.

## POST /knowledge/upload

### Purpose

Upload a knowledge document for storage and later indexing.

### Request

Content type: `multipart/form-data`

Parameters:

- `file`: Markdown, text, or supported document file.
- `title`: Human-readable document title.
- `source_type`: Type such as `policy`, `faq`, `ticket_history`, or `troubleshooting`.
- `category`: Optional category for retrieval filtering.
- `access_level`: Optional value such as `internal`, `support`, or `public`.

### Example Request

```bash
curl -X POST http://localhost:8000/knowledge/upload \
  -H "X-API-Key: change-me-dev-key" \
  -F "file=@sample_knowledge/refund_policy.md" \
  -F "title=CloudDesk Refund Policy" \
  -F "source_type=policy" \
  -F "category=billing" \
  -F "access_level=support"
```

### Example Response

```json
{
  "doc_id": "doc_001",
  "title": "CloudDesk Refund Policy",
  "source_type": "policy",
  "file_name": "refund_policy.md",
  "version": 1,
  "status": "pending",
  "chunk_count": 0,
  "indexing_error": null
}
```

Supported extensions are `.md`, `.markdown`, `.txt`, and `.pdf`. Oversized files are rejected according to `MAX_UPLOAD_SIZE_BYTES`.

The upload endpoint stores the file and schedules indexing in a FastAPI background task. Use `/knowledge/docs/{doc_id}/status` to check progress.

## POST /knowledge/reindex

### Purpose

Rebuild chunks, embeddings, and vector records for one document or all documents.

### Request Body

```json
{
  "doc_id": "doc_001",
  "force": true
}
```

If `doc_id` is omitted, the service may reindex all documents.

### Example Request

```bash
curl -X POST http://localhost:8000/knowledge/reindex \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me-dev-key" \
  -d "{\"doc_id\":\"doc_001\",\"force\":true}"
```

### Example Response

```json
{
  "status": "completed",
  "indexed_documents": 1
}
```

## POST /knowledge/search

### Purpose

Search the knowledge base and return top matching chunks with citations and scores.

### Request Body

```json
{
  "query": "I was charged twice yesterday",
  "top_k": 3,
  "filters": {
    "category": "billing",
    "access_level": "support"
  }
}
```

### Example Request

```bash
curl -X POST http://localhost:8000/knowledge/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me-dev-key" \
  -d "{\"query\":\"I was charged twice yesterday\",\"top_k\":3}"
```

The server enforces `INTERNAL_ALLOWED_ACCESS_LEVELS` during search. Client-provided `access_level` filters are ignored and replaced by the server-side allowed levels.

If `RERANKING_ENABLED=true`, the service retrieves a larger vector candidate set, reranks the candidate chunks with `RERANKER_MODEL`, and returns the best `top_k` results. If reranking fails, the response falls back to vector-search order.

### Example Response

```json
{
  "query": "I was charged twice yesterday",
  "results": [
    {
      "chunk_id": "chunk_001",
      "doc_id": "doc_001",
      "title": "CloudDesk Refund Policy",
      "section": "Duplicate Charges",
      "score": 0.91,
      "text": "A duplicate charge occurs when the same workspace is billed twice...",
      "citation": "CloudDesk Refund Policy > Duplicate Charges"
    }
  ],
  "top_k": 3
}
```

## GET /knowledge/docs

### Purpose

List indexed or uploaded knowledge documents.

### Parameters

- `source_type`: Optional filter.
- `category`: Optional filter.
- `limit`: Optional number of records.
- `offset`: Optional pagination offset.

### Example Request

```bash
curl "http://localhost:8000/knowledge/docs?source_type=policy" \
  -H "X-API-Key: change-me-dev-key"
```

### Example Response

```json
{
  "items": [
    {
      "doc_id": "doc_001",
      "title": "CloudDesk Refund Policy",
      "source_type": "policy",
      "file_name": "refund_policy.md",
      "version": 1,
      "indexing_status": "indexed",
      "indexing_error": null,
      "created_at": "2026-06-01T10:00:00Z",
      "updated_at": "2026-06-01T10:00:00Z"
    }
  ],
  "total": 1
}
```

## GET /knowledge/help-articles

### Purpose

List customer-facing help articles extracted from uploaded and indexed RAG documents.

Only documents with `indexing_status="indexed"` and explicit public chunks are returned. The response is extractive only and uses stored document and chunk text.

### Parameters

- `q`: Optional text search over document title, chunk category, and chunk text.
- `category`: Optional category filter.

### Example Request

```bash
curl "http://localhost:8000/knowledge/help-articles?category=billing&q=refund" \
  -H "X-API-Key: change-me-dev-key"
```

### Example Response

```json
{
  "articles": [
    {
      "id": "doc_001",
      "title": "CloudDesk Refund Policy",
      "category": "billing",
      "summary": "A duplicate charge occurs when the same workspace is billed twice.",
      "updatedDate": "2026-06-01",
      "helpfulCount": 0,
      "unhelpfulCount": 0,
      "contentSections": [
        {
          "title": "Duplicate Charges",
          "body": "A duplicate charge occurs when the same workspace is billed twice."
        }
      ]
    }
  ]
}
```

## GET /knowledge/help-articles/{doc_id}

### Purpose

Return one customer-facing help article with all public content sections extracted from stored chunks.

Returns `404` if the document does not exist, is not indexed, or does not have explicit public chunks.

### Example Request

```bash
curl http://localhost:8000/knowledge/help-articles/doc_001 \
  -H "X-API-Key: change-me-dev-key"
```

## GET /knowledge/docs/{doc_id}

### Purpose

Return metadata for one knowledge document.

### Parameters

- `doc_id`: Document identifier.

### Example Request

```bash
curl http://localhost:8000/knowledge/docs/doc_001 \
  -H "X-API-Key: change-me-dev-key"
```

### Example Response

```json
{
  "doc_id": "doc_001",
  "title": "CloudDesk Refund Policy",
  "source_type": "policy",
  "file_name": "refund_policy.md",
  "file_path": "./uploads/refund_policy.md",
  "version": 1,
  "indexing_status": "indexed",
  "indexing_error": null,
  "chunk_count": 8,
  "created_at": "2026-06-01T10:00:00Z",
  "updated_at": "2026-06-01T10:00:00Z"
}
```

## GET /knowledge/docs/{doc_id}/status

### Purpose

Return the latest indexing status for one document.

Statuses:

- `pending`
- `processing`
- `indexed`
- `failed`

### Example Request

```bash
curl http://localhost:8000/knowledge/docs/doc_001/status \
  -H "X-API-Key: change-me-dev-key"
```

### Example Response

```json
{
  "doc_id": "doc_001",
  "indexing_status": "indexed",
  "indexing_error": null,
  "chunk_count": 8,
  "updated_at": "2026-06-01T10:00:00Z"
}
```

## DELETE /knowledge/docs/{doc_id}

### Purpose

Delete a document record, related chunks, vector entries, the uploaded source file, and any generated cleaned Markdown artifact.

### Parameters

- `doc_id`: Document identifier.

### Example Request

```bash
curl -X DELETE http://localhost:8000/knowledge/docs/doc_001 \
  -H "X-API-Key: change-me-dev-key"
```

### Example Response

```json
{
  "doc_id": "doc_001",
  "status": "deleted",
  "deleted_chunks": 8
}
```

## Ragas Evaluations

All evaluation endpoints require `X-API-Key`.

### POST /evaluations/ragas/run

Starts a manual Ragas evaluation in a FastAPI background task.

```json
{
  "started_by_agent_id": "agent_001",
  "started_by_agent_name": "Support Manager",
  "notes": "Manual run from dashboard"
}
```

Response:

```json
{
  "message": "Evaluation started",
  "run_id": "eval_20260615_120000_ab12cd34"
}
```

### GET /evaluations/ragas/runs

Returns recent `evaluation_runs` rows where `module="rag_service"`.

### GET /evaluations/ragas/runs/{run_id}

Returns one evaluation run and its status metadata.

### GET /evaluations/ragas/runs/{run_id}/metrics

Returns the run's average `faithfulness`, `answer_relevancy`, `context_precision`, and `context_recall` rows.

### GET /evaluations/ragas/runs/{run_id}/errors

Returns failed evaluation cases stored in `error_analysis`.

### PATCH /evaluations/ragas/errors/{error_id}/resolve

```json
{
  "resolution_notes": "Updated prompt to avoid unsupported answer."
}
```

Marks the error resolved and records the current timestamp.

### POST /evaluations/ragas/errors/{error_id}/feedback

```json
{
  "action": "needs_fix",
  "rating": 2,
  "feedback_note": "The generated answer mentions email but tracking is done by code.",
  "edited_text": "Customer can track the ticket using the generated tracking code.",
  "agent_id": "agent_001",
  "agent_name": "Support Manager"
}
```

Creates an `agent_feedback` row with `object_type="error_analysis"`.
