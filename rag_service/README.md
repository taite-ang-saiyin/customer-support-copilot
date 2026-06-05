# AI Customer Support Copilot - RAG and Knowledge Base Service

## Overview

This repository contains the RAG and Knowledge Base service for the AI Customer Support Copilot internship project.

The full copilot system supports issued ticket assistance and real-time live chat assistance. This repository is focused only on the retrieval layer that prepares, stores, searches, and returns trusted knowledge sources for those modes.

The AI assistant should not answer customer questions from memory. It should first retrieve relevant knowledge, policies, FAQs, and past resolved tickets, then use those sources to support grounded answers with citations.

## Main Features

- Knowledge document ingestion
- FAQ and policy ingestion
- Past resolved ticket ingestion
- Text cleaning and normalization
- Chunking for retrieval
- Embedding generation with `BAAI/bge-small-en-v1.5`
- Vector storage in Chroma
- Metadata storage in PostgreSQL
- Retrieval API for ticket and chat copilot services
- Source citation support
- Retrieval logging and evaluation planning
- Local file storage for uploaded documents

## Tech Stack

- Python
- FastAPI
- PostgreSQL
- Chroma
- sentence-transformers
- Embedding model: `BAAI/bge-small-en-v1.5`
- Docker Compose for local development
- Local file storage for uploaded documents

## Folder Structure

```text
.
├── docs/
│   ├── API_SPEC.md
│   ├── ARCHITECTURE.md
│   ├── CODEX_TASKS.md
│   ├── DATABASE_DESIGN.md
│   ├── DEVELOPMENT_SETUP.md
│   ├── PROJECT_SCOPE.md
│   ├── RAG_PIPELINE.md
│   └── TESTING_PLAN.md
├── sample_knowledge/
│   ├── refund_policy.md
│   ├── billing_faq.md
│   ├── login_troubleshooting.md
│   ├── account_recovery_policy.md
│   ├── enterprise_sla_policy.md
│   ├── privacy_policy_summary.md
│   ├── known_issues.md
│   ├── past_resolved_tickets.md
│   └── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Quick Start

Use these commands to run the initial local service:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
docker compose up -d
uvicorn app.main:app --reload
```

Set `INTERNAL_API_KEY` in `.env` before using any `/knowledge` endpoint. Clients must send it with:

```bash
X-API-Key: your-internal-key
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
docker compose up -d
uvicorn app.main:app --reload
```

## Environment Variables

Create a local `.env` file from `.env.example`:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/support_copilot
CHROMA_DB_PATH=./chroma_db
UPLOAD_DIR=./uploads
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
TOP_K=3
APP_NAME=AI Customer Support Copilot RAG Service
ENV=development
INTERNAL_API_KEY=change-me-dev-key
INTERNAL_ALLOWED_ACCESS_LEVELS=support,public
MAX_UPLOAD_SIZE_BYTES=10485760
```

`API_KEY_AUTH_ENABLED=true` protects all `/knowledge` endpoints with `X-API-Key`. Set it to `false` only for local debugging or trusted temporary demos, then restart the service.

`INTERNAL_ALLOWED_ACCESS_LEVELS` is enforced by the server during search. Clients may send normal filters such as `category`, but the API does not trust client-provided `access_level` filters.

`MAX_UPLOAD_SIZE_BYTES` defaults to 10 MB. Supported upload extensions are `.md`, `.markdown`, `.txt`, and `.pdf`.

## Docker Compose

Create `.env` from `.env.example`, change `INTERNAL_API_KEY`, then run:

```bash
docker compose up --build
```

The Compose setup starts:

- `rag-api` on `http://localhost:8000`
- PostgreSQL on port `5432`
- persistent volumes for uploads, Chroma data, and model cache

Health check:

```bash
curl http://localhost:8000/health
```

Authenticated search example:

```bash
curl -X POST http://localhost:8000/knowledge/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me-dev-key" \
  -d "{\"query\":\"I was charged twice yesterday\",\"top_k\":3}"
```

## API Endpoint Summary

Implemented endpoints:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/knowledge/upload` | Upload a knowledge document for ingestion |
| POST | `/knowledge/reindex` | Rebuild embeddings and vector records |
| POST | `/knowledge/search` | Retrieve relevant chunks for a query |
| GET | `/knowledge/docs` | List indexed knowledge documents |
| GET | `/knowledge/docs/{doc_id}` | View one knowledge document record |
| GET | `/knowledge/docs/{doc_id}/status` | View document indexing status |
| DELETE | `/knowledge/docs/{doc_id}` | Remove a document and related chunks |

All `/knowledge` endpoints require `X-API-Key`.

## Indexing Status

Documents use a simple status field:

- `pending`: upload is stored and indexing has not started
- `processing`: text extraction, chunking, embedding, or vector upsert is running
- `indexed`: chunks and vectors were written successfully
- `failed`: indexing failed; `indexing_error` contains the latest error

Uploads through the API return quickly with `pending` and run indexing in a FastAPI background task. Reindexing keeps old chunks and vectors usable until the new index succeeds.

This project still uses `create_all` plus a small startup compatibility check for the new status columns. Add Alembic migrations before treating the database schema as production-managed.

## Tests

Run the test suite from `rag_service/`:

```bash
pytest
```

## Demo Scenario

A support ticket says: "I was charged twice yesterday."

The service should retrieve sources such as:

- `refund_policy.md` > Duplicate Charges
- `billing_faq.md` > Duplicate Billing FAQ
- Relevant entries from `past_resolved_tickets.md`

The copilot service can then draft a grounded response asking for invoice numbers, billing email, charge dates, amount, currency, and last four card digits, without promising a refund before verification.

## Project Status

Status: Initial Backend Implementation

Current repository contents include documentation, sample synthetic knowledge files, local development preparation files, and the first FastAPI implementation for upload, indexing, vector search, citations, document management, and retrieval logging.

The LLM response generation layer and frontend are intentionally out of scope for this repository.

## Team Note

This repository is prepared for an internship project module owned by the RAG and Knowledge Engineer. The goal is to keep the service scope clear, reviewable, and ready for incremental implementation.
