# RAG Pipeline

## Pipeline Steps

1. Upload knowledge documents.
2. Extract text from uploaded files.
3. Clean text.
4. Split text into meaningful chunks.
5. Add metadata to each chunk.
6. Generate embeddings.
7. Store metadata in PostgreSQL.
8. Store vectors in Chroma.
9. Search by user query.
10. Return top-k results with citations.
11. Log retrieval result.
12. Evaluate retrieval quality.

## 1. Upload Knowledge Documents

Documents may include policies, FAQs, troubleshooting guides, and past resolved tickets. During local development, the `sample_knowledge/` folder provides synthetic Markdown files for ingestion testing.

## 2. Extract Text

The document loader should extract readable text from each supported file type. For Markdown, headings should be preserved because they are useful for section-level citations.

## 3. Clean Text

Cleaning should remove extra whitespace, normalize line endings, preserve meaningful headings, and remove content that should not be indexed.

The cleaner should avoid changing the meaning of policy text.

## 4. Split Into Meaningful Chunks

Chunks should be short enough for retrieval and answer generation, but large enough to keep context. A good starting target is 200 to 500 tokens per chunk.

Markdown headings should guide chunk boundaries. For example, `Refund Policy > Duplicate Charges` should become a retrievable section.

## 5. Add Metadata

Each chunk should include:

- `doc_id`
- `chunk_id`
- `source`
- `section`
- `category`
- `language`
- `access_level`
- `chunk_index`

Metadata supports citations, filtering, evaluation, and document management.

## 6. Generate Embeddings

The embedding service should use `BAAI/bge-small-en-v1.5` through sentence-transformers. The same model should be used for document chunks and search queries.

## 7. Store Metadata In PostgreSQL

PostgreSQL stores document records, chunk text, chunk metadata, and retrieval logs. It provides reliable structured access for API responses and evaluation.

## 8. Store Vectors In Chroma

Chroma stores chunk embeddings in the `support_knowledge` collection. Each vector item should include the chunk ID, chunk text, and metadata needed for filtering.

## 9. Search By User Query

The search endpoint receives a query, generates a query embedding, searches Chroma, enriches results with PostgreSQL metadata, and returns the top-k chunks.

## 10. Return Top-K Results With Citations

Results should include:

- Chunk text
- Score
- Document title
- Section title
- Source file
- Citation string

Suggested citation format:

```text
{Document Title} > {Section Title}
```

Example:

```text
CloudDesk Refund Policy > Duplicate Charges
```

## 11. Log Retrieval Result

Each search should create a retrieval log with query text, returned chunk IDs, scores, and timestamp. Logs help debug poor retrieval and measure evaluation quality.

## 12. Evaluate Retrieval Quality

Evaluation should compare test queries with expected source documents and sections. The testing plan defines metrics such as Top-1 accuracy, Top-3 hit rate, MRR, context precision, and context recall.

## Chunking Strategy

Use heading-aware chunking for Markdown documents. Prefer splitting at `#`, `##`, and `###` headings before using size-based fallback splitting.

For past resolved tickets, each ticket should usually be one chunk because the ticket ID, root cause, resolution, and outcome are most useful together.

For long sections, split by paragraphs while preserving the section title in metadata.

## Metadata Strategy

Metadata should be consistent across documents so retrieval filters work. Suggested categories include:

- `billing`
- `login`
- `account_recovery`
- `enterprise_sla`
- `privacy`
- `known_issues`
- `past_tickets`

Use `language=en` for the current synthetic corpus. Use `access_level=support` unless a document is explicitly public or internal only.

## Similar Past Ticket Retrieval

Past resolved tickets should be indexed as searchable cases. When a new issue resembles a resolved ticket, the service should return the past ticket as supporting context.

Example:

Query: "Customer was charged twice after renewal."

Expected result: a duplicate charge ticket from `past_resolved_tickets.md` plus the refund policy section.

## Future Hybrid Search With BM25

Semantic search is useful for meaning-based matches, but exact terms like error codes and invoice IDs are also important. A future hybrid search design should combine vector search with BM25 keyword search.

Hybrid search can improve retrieval for queries containing:

- Error codes such as `CD-AUTH-LOCKED`
- Ticket IDs
- Invoice IDs
- Policy names
- Exact feature names
