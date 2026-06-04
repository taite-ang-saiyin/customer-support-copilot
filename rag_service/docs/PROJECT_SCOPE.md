# Project Scope

## Module Purpose

This repository contains the RAG and Knowledge Base service for the AI Customer Support Copilot. The module is responsible for preparing trusted support knowledge and returning relevant sources to the wider copilot system.

The service supports both issued ticket copilot workflows and real-time live chat assistant workflows by retrieving relevant policy, FAQ, troubleshooting, and past ticket information.

## Included In This Module

This module includes:

- Document upload
- Document parsing
- FAQ ingestion
- Policy ingestion
- Past resolved ticket ingestion
- Text cleaning
- Chunking
- Embedding generation
- Vector database storage
- Knowledge search
- Similar past ticket retrieval
- Source citations
- Retrieval logs
- Retrieval evaluation

## Not Included In This Module

This module does not include:

- Frontend dashboard
- LLM response generation
- Ticket classification
- Live chat UI
- Authentication
- Production deployment
- Agent handoff workflows
- Customer account management
- Payment processing

## Main Responsibilities

The service should accept knowledge documents, convert them into clean retrievable chunks, generate embeddings, store metadata, and return top matching knowledge sources for a query.

It should make retrieval behavior measurable through logs and evaluation scripts.

## Boundary With Other Services

The ticket copilot service and live chat assistant service may call this module for context. Those services are responsible for conversation handling and LLM answer generation.

This module should return retrieved chunks, citations, metadata, and scores. It should not decide the final customer-facing answer.

## Current Status

Status: Planning / Initial Setup

The repository currently contains documentation, sample synthetic knowledge files, and preparation files. Backend implementation is planned for later phases.
