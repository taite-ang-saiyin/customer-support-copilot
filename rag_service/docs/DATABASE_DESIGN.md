# Database Design

## Overview

The service uses PostgreSQL for structured metadata and Chroma for vector search. PostgreSQL is the source of truth for document records, chunk records, and retrieval logs. Chroma stores embeddings for semantic retrieval.

## PostgreSQL Table: knowledge_docs

Stores one record per uploaded or managed knowledge document.

| Column | Type | Description |
| --- | --- | --- |
| `doc_id` | UUID or text primary key | Unique document identifier |
| `title` | text | Human-readable document title |
| `source_type` | text | Source type such as `policy`, `faq`, `ticket_history`, or `troubleshooting` |
| `file_name` | text | Original uploaded file name |
| `file_path` | text | Local storage path for the file |
| `version` | integer | Document version number |
| `created_at` | timestamp | Record creation time |
| `updated_at` | timestamp | Last update time |

## PostgreSQL Table: knowledge_chunks

Stores metadata and text for each searchable chunk.

| Column | Type | Description |
| --- | --- | --- |
| `chunk_id` | UUID or text primary key | Unique chunk identifier |
| `doc_id` | UUID or text foreign key | Parent document identifier |
| `chunk_text` | text | Cleaned chunk content |
| `section_title` | text | Heading or section name |
| `category` | text | Retrieval category such as `billing`, `login`, or `privacy` |
| `language` | text | Language code, default `en` |
| `access_level` | text | Access level such as `support`, `internal`, or `public` |
| `chunk_index` | integer | Position of the chunk within the document |
| `created_at` | timestamp | Chunk creation time |

## PostgreSQL Table: retrieval_logs

Stores search activity for debugging and evaluation.

| Column | Type | Description |
| --- | --- | --- |
| `log_id` | UUID or text primary key | Unique log identifier |
| `query` | text | User or service query |
| `retrieved_chunk_ids` | JSONB or text array | Chunk IDs returned by retrieval |
| `scores` | JSONB or numeric array | Similarity scores for returned chunks |
| `created_at` | timestamp | Retrieval time |

## Chroma Collection: support_knowledge

Chroma collection name: `support_knowledge`

Each vector item should include:

- `chunk_id`
- Chunk text
- Embedding
- Metadata

Metadata fields:

- `doc_id`
- `source`
- `section`
- `category`
- `language`
- `access_level`

## Relationship Between PostgreSQL And Chroma

`chunk_id` links PostgreSQL chunk metadata to Chroma vector records. Search results from Chroma can be enriched by looking up document and chunk metadata in PostgreSQL.

When a document is deleted, the service should delete its records from `knowledge_docs`, related rows from `knowledge_chunks`, and related vector items from the `support_knowledge` collection.

## Indexing Considerations

PostgreSQL should index:

- `knowledge_docs.source_type`
- `knowledge_chunks.doc_id`
- `knowledge_chunks.category`
- `knowledge_chunks.access_level`
- `retrieval_logs.created_at`

Chroma should store metadata needed for filtering so the retrieval endpoint can restrict search results by category, language, or access level.
