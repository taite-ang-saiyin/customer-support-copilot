# Testing Plan

## Overview

Testing should verify that the RAG and Knowledge Base service can ingest documents, create useful chunks, retrieve expected sources, return citations, and log retrieval results.

## Unit Tests

Unit tests should cover:

- Text cleaning
- Markdown heading parsing
- Chunk creation
- Metadata assignment
- Embedding service wrapper behavior
- Citation formatting
- Database model validation

## API Tests

API tests should cover:

- Uploading a knowledge document
- Reindexing a document
- Searching the knowledge base
- Listing documents
- Retrieving document details
- Deleting a document
- Handling invalid requests

## Retrieval Tests

Retrieval tests should use known queries and expected source documents. The goal is to confirm that relevant chunks appear in the top results.

The curated retrieval dataset is stored at:

```text
eval/retrieval_test_cases.json
```

Run the FastAPI service first, then evaluate retrieval:

```bash
python scripts/evaluate_retrieval.py --base-url http://127.0.0.1:8000
```

The script calls the existing `/knowledge/search` endpoint and reports Top-1 accuracy, Top-k hit rate, MRR, and failed cases.

## Example Test Queries

| Query | Expected Source |
| --- | --- |
| I was charged twice yesterday | Refund Policy > Duplicate Charges |
| I cannot log in and see CD-AUTH-LOCKED | Login Troubleshooting > Account Locked |
| Our SSO login fails with CD-SSO-403 | Login Troubleshooting > SSO Login Failure |
| How fast should enterprise urgent issues be handled? | Enterprise SLA Policy |
| I want my data deleted | Privacy Policy Summary > Data Deletion Requests |
| My card payment failed with CD-PAY-402 | Billing FAQ > Failed Payments |
| Email notifications are delayed | Known Issues > Delayed Email Notifications |
| I lost access to my authenticator app | Login Troubleshooting > Two-Factor Authentication Issue |
| A former employee owned our billing account | Account Recovery Policy > Admin Account Recovery |
| My invoice PDF will not download | Billing FAQ > Invoice Download |

## Metrics

Top-1 accuracy measures whether the first retrieved result is the expected source.

Top-3 hit rate measures whether the expected source appears anywhere in the top three results.

MRR, or mean reciprocal rank, measures how highly the correct result appears across multiple queries.

Context precision measures how much retrieved context is relevant to the query.

Context recall measures whether the retrieved context includes enough information to answer the query.

## Ingestion Quality Tests

Run ingestion quality and chunking tests with:

```bash
pytest
```

The ingestion quality analyzer checks for common PDF ingestion problems:

- low extracted text
- no headings detected
- too few chunks
- too many tiny chunks
- oversized chunks
- possible scanned PDF
- missing citations

## Inspecting Cleaned Markdown

When a PDF is uploaded and indexed, the cleaned Markdown artifact is saved to:

```text
uploads/processed/{original_file_stem}.cleaned.md
```

Inspect this file when retrieval quality is poor. Good cleaned Markdown should have useful headings such as:

```text
# Refund Policy
## Duplicate Charges
## Refund Processing Time
```

If the cleaned Markdown has very little text, the PDF may be scanned and may require OCR before ingestion.

## Acceptance Targets For Initial Demo

Suggested initial targets:

- Top-1 accuracy: 70% or higher on the curated test set
- Top-3 hit rate: 90% or higher on the curated test set
- MRR: 0.80 or higher on the curated test set

These targets are for internship demonstration only and should be revised after real evaluation data exists.

## Manual Review Checklist

For each retrieval result, check:

- The source document is relevant.
- The section title is useful.
- The chunk is short enough for answer generation.
- The citation is clear.
- The result does not include unrelated private or unsafe content.
- The retrieval log stores the query, chunk IDs, and scores.
