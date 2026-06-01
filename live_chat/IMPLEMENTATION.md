# Member 3 Implementation

This document explains the `live_chat` implementation for the AI Customer Support Copilot project.

## Purpose

Member 3 owns:

- LLM prompt engineering
- Ticket reply draft generation
- Live chat reply suggestion generation
- Confidence scoring
- Escalation decision support
- Output validation and fallback behavior

The implementation uses **Google Gemini** through the official `google-genai` SDK and keeps Gemini-specific code isolated so the provider can be swapped later.

## Folder Structure

```text
live_chat/
├── api/
│   ├── livechat_suggestion_api.py
│   └── ticket_draft_api.py
├── confidence/
│   └── scorer.py
├── escalation/
│   └── rules.py
├── evaluation/
│   └── draft_evaluation.py
├── generation/
│   ├── json_formatter.py
│   ├── livechat_generator.py
│   └── ticket_generator.py
├── llm/
│   ├── gemini_client.py
│   └── schemas.py
├── prompts/
│   ├── livechat_prompt.py
│   └── ticket_prompt.py
└── tests/
```

## Design Overview

The generation pipeline is intentionally split into small modules:

1. Prompt builder creates grounded instructions from the input payload.
2. Gemini client sends the prompt and requests structured JSON output.
3. Evaluation layer validates the model output.
4. Escalation rules check whether the case is risky or unsupported.
5. Confidence scorer calculates the final confidence score.
6. API layer exposes the functionality through FastAPI routers.

This separation keeps the LLM call thin and moves business rules into deterministic Python code.

## Gemini Integration

File: `live_chat/llm/gemini_client.py`

Responsibilities:

- Read `GEMINI_API_KEY` from environment variables
- Read `GEMINI_MODEL` from environment variables
- Default to `gemini-2.5-flash` when `GEMINI_MODEL` is missing
- Request JSON output from Gemini
- Parse the returned JSON safely
- Raise a clear error if the API key is missing

Public function:

```python
generate_structured_response(
    prompt: str,
    response_schema: dict,
    temperature: float = 0.2
) -> dict
```

Why this matters:

- Gemini is the only LLM provider used here
- The rest of the codebase does not depend directly on SDK details
- Replacing Gemini later only requires changes in one module

## Response Schemas

File: `live_chat/llm/schemas.py`

Two JSON schemas are defined:

- `TICKET_DRAFT_SCHEMA`
- `LIVECHAT_SUGGESTION_SCHEMA`

These schemas enforce the required output fields such as:

- generated reply text
- agent notes
- citations
- confidence
- missing information
- escalation flags

The schemas are passed into Gemini so the model is asked for structured JSON instead of free-form text.

## Prompt Builders

Files:

- `live_chat/prompts/ticket_prompt.py`
- `live_chat/prompts/livechat_prompt.py`

### Ticket Prompt

The ticket prompt includes:

- customer message
- ticket metadata
- classification output from Member 1
- retrieved evidence from Member 2
- safety rules
- JSON output instructions

### Live Chat Prompt

The live chat prompt includes:

- conversation history
- latest customer message
- known details
- missing details
- classification context
- retrieved evidence
- safety rules
- JSON output instructions

### Shared Safety Rules

The prompts explicitly instruct the model to:

- use only retrieved evidence
- avoid invented policy claims
- avoid promising refunds unless evidence supports it
- avoid legal, privacy, security, or billing decisions
- ask for missing information
- recommend escalation when needed
- never auto-send a reply
- keep the human agent in control

## Generation Pipelines

Files:

- `live_chat/generation/ticket_generator.py`
- `live_chat/generation/livechat_generator.py`

### Ticket Flow

`generate_ticket_draft(input_data: dict) -> dict`

Steps:

1. Build the ticket prompt.
2. Call Gemini with the ticket schema.
3. Validate and sanitize the returned JSON.
4. Apply escalation rules.
5. Recalculate the final confidence score.
6. Return a stable response object.

### Live Chat Flow

`generate_livechat_suggestion(input_data: dict) -> dict`

Steps:

1. Build the live chat prompt.
2. Call Gemini with the live chat schema.
3. Validate and sanitize the returned JSON.
4. Apply escalation rules.
5. Recalculate the final confidence score.
6. Return a stable response object.

## Validation and Hallucination Reduction

Files:

- `live_chat/evaluation/draft_evaluation.py`
- `live_chat/generation/json_formatter.py`

This layer handles output cleanup and safety checks after Gemini responds.

### What gets validated

- Response must be a dictionary
- Main reply field must exist
- Citations must be present
- Citations must match `retrieved_context`
- Unsupported refund promises are blocked
- Restricted legal, privacy, and security claims are blocked
- Missing information is merged with heuristic detection

### Malformed Output Behavior

If Gemini returns malformed or unusable output:

- the system creates a safe fallback response
- the case is escalated
- confidence is kept low
- the agent still receives a structured JSON response

This prevents the API from returning unstable or partially broken data.

## Missing Information Detection

The implementation adds heuristic missing-info detection for common cases.

Examples:

- duplicate charge or refund issues
  - `transaction_id`
  - `payment_receipt`
- login or access issues
  - `error_message`
  - `account_email`

This logic supplements the model output rather than trusting the model alone.

## Confidence Scoring

File: `live_chat/confidence/scorer.py`

Function:

```python
calculate_confidence(
    retrieval_score: float,
    classification_confidence: float,
    missing_info_count: int,
    escalation_required: bool
) -> float
```

Formula:

```text
confidence =
  retrieval_score * 0.5 +
  classification_confidence * 0.3 +
  completeness_score * 0.2
```

Rules:

- `completeness_score` starts at `1.0`
- subtract `0.15` for each missing info item
- minimum completeness score is `0.0`
- subtract `0.2` if escalation is required
- clamp final confidence to `0.0` through `1.0`

If validation fails, the final confidence is capped so malformed output does not appear highly trustworthy.

## Escalation Rules

File: `live_chat/escalation/rules.py`

Function:

```python
should_escalate(input_data: dict) -> dict
```

Escalation is triggered when:

- category is `Security`, `Legal`, or `Privacy`
- priority is `Urgent`
- sentiment is `Angry`
- retrieval score is below `0.55`
- no retrieved evidence exists
- customer is `enterprise` or `vip` and issue is high impact
- text indicates account takeover, outage, payment dispute, legal complaint, privacy request, or large refund
- validation failed after model output review

The function returns:

```python
{
    "escalation_required": True,
    "escalation_reason": "..."
}
```

## FastAPI Endpoints

Files:

- `live_chat/api/ticket_draft_api.py`
- `live_chat/api/livechat_suggestion_api.py`

Available routes:

- `POST /tickets/{ticket_id}/draft`
- `POST /chat/conversations/{conversation_id}/suggest`

These routers are standalone and can be included in a larger FastAPI application.

Example:

```python
from fastapi import FastAPI
from live_chat.api.ticket_draft_api import router as ticket_router
from live_chat.api.livechat_suggestion_api import router as livechat_router

app = FastAPI()
app.include_router(ticket_router)
app.include_router(livechat_router)
```

## Environment Configuration

File: `.env.example`

```env
GEMINI_API_KEY=your_google_ai_studio_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

Notes:

- API keys are never hardcoded
- tests do not call the real Gemini API

## Testing

Test files:

- `live_chat/tests/test_gemini_client.py`
- `live_chat/tests/test_ticket_generator.py`
- `live_chat/tests/test_livechat_generator.py`
- `live_chat/tests/test_confidence_scorer.py`
- `live_chat/tests/test_escalation_rules.py`

Covered cases:

- missing API key error
- ticket generation for duplicate charge flow
- live chat billing suggestion flow
- confidence score clamping
- low retrieval confidence escalation
- security issue escalation
- citation validation
- malformed Gemini output fallback
- missing information detection
- FastAPI response shape

## Key Implementation Decisions

- Gemini-specific logic is isolated in one module
- Structured JSON is used instead of plain text responses
- Business rules are enforced outside the model
- Validation can override model output when evidence is weak
- Fallback responses remain structured and safe

## Current Assumptions

- This workspace did not contain an existing backend app, so Member 3 was built as a standalone package
- The API routers are ready to plug into a larger FastAPI service
- Citation matching currently expects labels in `Source - Section` format derived from `retrieved_context`

## Next Integration Step

To connect this into the full system:

1. Feed Member 1 classification output into the generator input payload
2. Feed Member 2 retrieval output into `retrieved_context`
3. Mount the FastAPI routers inside the main backend app
4. Add request models and authentication when the full service structure exists
