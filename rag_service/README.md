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

Uploaded files keep a sanitized readable filename. If the name already exists, the service adds a numeric suffix such as `known_issues_2.md` instead of overwriting it.

Reranking is optional and disabled by default:

```env
RERANKING_ENABLED=false
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
RERANK_CANDIDATE_MULTIPLIER=5
RERANK_MAX_CANDIDATES=25
```

When enabled, search retrieves a larger Chroma candidate pool, scores each `(query, chunk)` pair with the reranker, and returns the best `top_k` results. For example, `top_k=5` with multiplier `5` reranks up to 25 candidates. If the reranker fails, search falls back to the original vector order.

## Ragas Evaluation

The service supports manual and post-upload Ragas evaluation using the existing Supabase tables:

- `evaluation_runs`
- `evaluation_metrics`
- `error_analysis`
- `agent_feedback`

Knowledge documents, chunks, and retrieval logs remain in the local PostgreSQL service. Evaluation records are sent separately to Supabase through its REST API:

```env
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

The service-role key is server-side only. Never expose it to a browser or commit it.

The fixed dataset is stored at `evals/datasets/support_eval_v1.json`. Because this service does not generate LLM answers, evaluation uses the first retrieved chunk as a clearly separated extractive answer and sends all retrieved chunks to Ragas as contexts.

Configure an evaluator LLM through an OpenAI-compatible endpoint:

```env
RAGAS_DATASET_PATH=./evals/datasets/support_eval_v1.json
RAGAS_AUTO_EVAL_ENABLED=true
RAGAS_EVALUATOR_MODEL=your-evaluator-model
RAGAS_EVALUATOR_PROVIDER=openai
RAGAS_EVALUATOR_API_KEY=
RAGAS_EVALUATOR_BASE_URL=http://host.docker.internal:11434/v1
RAGAS_EVALUATOR_MAX_TOKENS=2048
RAGAS_PROMPT_VERSION=rag_prompt_v1
RAGAS_RETRIEVAL_VERSION=chroma_v1
RAGAS_EVAL_TOP_K=5
```

For a hosted OpenAI-compatible provider, set its API key and omit `RAGAS_EVALUATOR_BASE_URL`. For a local compatible endpoint, set the base URL; the service supplies a non-secret placeholder API key when the client requires one.
If a local evaluator fails with incomplete output because of a token limit, increase `RAGAS_EVALUATOR_MAX_TOKENS`.

Start a manual run:

```bash
curl -X POST http://localhost:8000/evaluations/ragas/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me-dev-key" \
  -d "{\"started_by_agent_id\":\"agent_001\",\"started_by_agent_name\":\"Support Manager\",\"notes\":\"Manual dashboard run\"}"
```

The endpoint returns immediately with a run ID. Use:

```text
GET /evaluations/ragas/runs
GET /evaluations/ragas/runs/{run_id}
GET /evaluations/ragas/runs/{run_id}/metrics
GET /evaluations/ragas/runs/{run_id}/errors
```

After a document indexes successfully, an automatic run starts when `RAGAS_AUTO_EVAL_ENABLED=true`. Missing evaluator configuration or evaluator crashes are stored as `metadata.status="error"` with `metadata.error_message`.

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
| GET | `/knowledge/help-articles` | List public indexed documents as customer-facing help articles |
| GET | `/knowledge/help-articles/{doc_id}` | View one public indexed document as a help article |

All `/knowledge` endpoints require `X-API-Key`.

Customer-facing help articles are extractive: the service only returns stored document metadata and public chunk text. Optional filters:

```bash
curl "http://localhost:8000/knowledge/help-articles?category=billing&q=refund" \
  -H "X-API-Key: change-me-dev-key"

curl http://localhost:8000/knowledge/help-articles/doc_001 \
  -H "X-API-Key: change-me-dev-key"
```

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
