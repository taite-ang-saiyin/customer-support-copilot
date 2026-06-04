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
| DELETE | `/knowledge/docs/{doc_id}` | Remove a document and related chunks |

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
