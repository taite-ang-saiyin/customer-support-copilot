# Sample Knowledge Files

## Overview

This folder contains synthetic demo knowledge files for the AI Customer Support Copilot RAG and Knowledge Base service.

The files are fictional and safe for testing. They do not represent a real company, real customer data, real internal policy, or confidential documentation.

## Intended Use

These Markdown files are used for RAG ingestion and retrieval tests. They provide realistic support scenarios for document parsing, text cleaning, chunking, embedding generation, vector storage, citation generation, and retrieval evaluation.

The files should help test whether the service can retrieve trusted knowledge before the wider copilot system drafts a response.

## Expected Files

- `refund_policy.md`
- `billing_faq.md`
- `login_troubleshooting.md`
- `account_recovery_policy.md`
- `enterprise_sla_policy.md`
- `privacy_policy_summary.md`
- `known_issues.md`
- `past_resolved_tickets.md`

## Example Retrieval Queries

- I was charged twice yesterday.
- I cannot log in and see CD-AUTH-LOCKED.
- Our SSO login is failing with CD-SSO-403.
- How long does an enterprise urgent issue take?
- I want my account data deleted.
- My invoice is missing.
- Email notifications are delayed.

## Notes

This folder is for local development and internship demonstration only. The knowledge files can be uploaded into the planned ingestion pipeline once the backend service is implemented.
