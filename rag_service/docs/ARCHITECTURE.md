# Architecture

## High-Level Flow

```text
Knowledge Files
-> Document Loader
-> Text Cleaner
-> Chunker
-> Embedding Service
-> Chroma Vector DB
-> PostgreSQL Metadata DB
-> Retrieval API
-> Ticket/Chat Copilot Service
```

## Component Overview

Knowledge files include Markdown documents, FAQs, policies, and past resolved tickets. Files may come from `sample_knowledge/` during development or from uploads after the API is implemented.

The document loader reads uploaded files from local storage and extracts text. The text cleaner removes unnecessary spacing, normalizes headings, and prepares content for chunking.

The chunker splits documents into short, meaningful sections. Chunks should preserve source document, section title, category, language, and access level metadata.

The embedding service uses `BAAI/bge-small-en-v1.5` through sentence-transformers to generate vector embeddings for each chunk.

Chroma stores vector embeddings for semantic similarity search. PostgreSQL stores document metadata, chunk metadata, and retrieval logs.

The Retrieval API exposes search endpoints to the ticket copilot and live chat assistant services.

## Why Use PostgreSQL And Chroma

PostgreSQL is used for structured metadata that needs reliability and clear relationships. It stores document records, chunk records, versions, file paths, creation timestamps, and retrieval logs.

Chroma is used for vector search. It stores embeddings and vector metadata in a collection optimized for similarity retrieval.

Using both keeps the design simple:

- PostgreSQL answers questions about documents, chunks, versions, and logs.
- Chroma answers semantic search questions such as "which chunks are closest to this user query?"

## Local File Storage

Uploaded documents are stored in a local directory configured by `UPLOAD_DIR`. This is suitable for internship development and local testing.

The database stores the file path and document metadata. The file itself remains in local storage so the ingestion pipeline can reprocess or reindex it when needed.

## Retrieval Request Flow

1. A ticket or chat service sends a search query to `/knowledge/search`.
2. The service cleans the query.
3. The embedding service generates a query embedding.
4. Chroma returns the most similar chunks.
5. PostgreSQL metadata is used to enrich results.
6. The API returns chunk text, scores, and citations.
7. The retrieval event is written to `retrieval_logs`.

## Future Production Upgrade Options

Chroma can be replaced with Qdrant or pgvector if the project needs managed deployment, larger scale, advanced filtering, or stronger production operations.

Local file storage can be replaced with S3, MinIO, or another object storage service for durability and multi-instance deployment.

Redis can be added for async indexing queues, background job status, caching repeated searches, and rate limiting.

Additional production upgrades may include authentication, role-based document access, observability, background workers, and CI/CD deployment.
