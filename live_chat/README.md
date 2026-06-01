# Member 3 README

Member 3 implements the LLM response and live chat layer for the AI Customer Support Copilot.

It covers:

- Gemini-based structured generation
- Ticket draft generation
- Live chat suggestion generation
- Confidence scoring
- Escalation rules
- Output validation and fallback handling
- FastAPI routers
- Unit tests with mocked Gemini calls

## Main Files

- `llm/gemini_client.py`: Gemini provider wrapper
- `llm/schemas.py`: structured JSON schemas
- `prompts/`: prompt builders for ticket and live chat
- `generation/`: generation pipelines
- `confidence/scorer.py`: confidence scoring formula
- `escalation/rules.py`: escalation triggers
- `evaluation/draft_evaluation.py`: validation and hallucination reduction
- `api/`: FastAPI routers
- `tests/`: unit tests

## Requirements

- Python 3.10+
- packages from [`requirements.txt`](</c:/Users/Msi GF66/Desktop/Customer Support AI/requirements.txt:1>)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment Variables

Create environment variables based on [`.env.example`](</c:/Users/Msi GF66/Desktop/Customer Support AI/.env.example:1>):

```env
GEMINI_API_KEY=your_google_ai_studio_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

Rules:

- Do not hardcode API keys
- `GEMINI_MODEL` is optional
- default model is `gemini-2.5-flash`
- the app now loads `.env` automatically with `python-dotenv`

## Exposed Functions

Ticket generation:

```python
generate_ticket_draft(input_data: dict) -> dict
```

Live chat generation:

```python
generate_livechat_suggestion(input_data: dict) -> dict
```

Confidence scoring:

```python
calculate_confidence(
    retrieval_score: float,
    classification_confidence: float,
    missing_info_count: int,
    escalation_required: bool
) -> float
```

Escalation:

```python
should_escalate(input_data: dict) -> dict
```

## API Routes

If you include the routers in a FastAPI app, these routes are available:

- `POST /tickets/{ticket_id}/draft`
- `POST /chat/conversations/{conversation_id}/suggest`

Example:

```python
from fastapi import FastAPI
from live_chat.api.ticket_draft_api import router as ticket_router
from live_chat.api.livechat_suggestion_api import router as livechat_router

app = FastAPI()
app.include_router(ticket_router)
app.include_router(livechat_router)
```

## Safety Behavior

The implementation enforces these rules:

- use only retrieved evidence
- block unsupported citations
- block unsupported refund promises
- block unsupported legal, privacy, and security claims
- detect missing information for common billing and login cases
- escalate risky or weakly grounded responses
- never auto-send customer replies

## Running Tests

Run:

```bash
python -m pytest live_chat/tests -q
```

Tests do not call the real Gemini API. Gemini generation is mocked in unit tests.

## Run With Docker

Build the image from the project root:

```bash
docker build -t customer-support-ai-api .
```

Run the container and pass your environment variables from `.env`:

```bash
docker run --env-file .env -p 8000:8000 customer-support-ai-api
```

The API will listen on:

```text
http://localhost:8000
```

Because the container starts Uvicorn with `--host 0.0.0.0`, other devices on the same Wi-Fi network can reach it using your computer's local IP address:

```text
http://YOUR_LOCAL_IP:8000
```

Example:

```text
http://192.168.1.25:8000
```

Important notes:

- your computer and your teammates' devices must be on the same local network
- Windows Firewall may prompt you to allow Docker or Python network access
- keep port `8000` open on your machine if the firewall asks
- use `docker run --env-file .env ...` so the API key stays outside the image

Useful endpoints once the container is running:

- `http://YOUR_LOCAL_IP:8000/docs`
- `http://YOUR_LOCAL_IP:8000/tickets/TCK-001/draft`
- `http://YOUR_LOCAL_IP:8000/chat/conversations/CHAT-101/suggest`

## Run With Docker Compose

The repo also includes [`docker-compose.yml`](</c:/Users/Msi GF66/Desktop/Customer Support AI/docker-compose.yml:1>) so you can start the API with one command.

From the project root:

```bash
docker compose up --build
```

This will:

- build the image from the local `Dockerfile`
- load variables from `.env`
- expose the API on port `8000`
- start the container as `customer-support-ai-api`

To run it in the background:

```bash
docker compose up --build -d
```

To stop it:

```bash
docker compose down
```

After startup, access:

- `http://localhost:8000/docs`
- `http://YOUR_LOCAL_IP:8000/docs`

## Testing With Real Input Data

To test against the real Gemini API, first set environment variables.

Recommended approach: create a project-root `.env` file:

```env
GEMINI_API_KEY=your_google_ai_studio_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

The app and Gemini client now load this file automatically with `python-dotenv`.

Alternative PowerShell approach:

```powershell
$env:GEMINI_API_KEY="your_google_ai_studio_api_key_here"
$env:GEMINI_MODEL="gemini-2.5-flash"
```

### Real Ticket Test

Run this from the project root:

```powershell
@'
from pprint import pprint
from live_chat.generation.ticket_generator import generate_ticket_draft

input_data = {
    "ticket_id": "TCK-001",
    "customer_message": "I was charged twice yesterday and I still have not received my refund.",
    "intent": "refund_request",
    "category": "Billing",
    "priority": "High",
    "sentiment": "Frustrated",
    "classification_confidence": 0.86,
    "entities": {
        "issue": "duplicate charge",
        "time": "yesterday"
    },
    "retrieved_context": [
        {
            "source": "Refund Policy",
            "section": "Duplicate Charges",
            "text": "Duplicate charges are eligible for refund after payment verification.",
            "score": 0.91
        }
    ]
}

pprint(generate_ticket_draft(input_data))
'@ | python -
```

Expected result shape:

- `reply_draft`
- `agent_notes`
- `citations`
- `confidence`
- `missing_info`
- `escalation_required`
- `escalation_reason`

### Real Live Chat Test

```powershell
@'
from pprint import pprint
from live_chat.generation.livechat_generator import generate_livechat_suggestion

input_data = {
    "conversation_id": "CHAT-101",
    "conversation_history": [
        {"sender": "customer", "message": "My account was charged twice."},
        {"sender": "agent", "message": "I am sorry to hear that."},
        {"sender": "customer", "message": "I need this fixed now."}
    ],
    "latest_message": "I need this fixed now.",
    "intent": "refund_request",
    "category": "Billing",
    "priority": "High",
    "sentiment": "Frustrated",
    "classification_confidence": 0.84,
    "retrieved_context": [
        {
            "source": "Refund Policy",
            "section": "Duplicate Charges",
            "text": "Duplicate charges are eligible for refund after payment verification.",
            "score": 0.88
        }
    ]
}

pprint(generate_livechat_suggestion(input_data))
'@ | python -
```

Expected result shape:

- `suggested_reply`
- `agent_notes`
- `citations`
- `confidence`
- `missing_info`
- `escalation_required`
- `escalation_reason`

### Real API Test

The repo already includes `app.py` with both routers mounted.

Run the server:

```bash
uvicorn app:app --reload
```

Then send a real ticket request:

```powershell
$body = @{
  customer_message = "I was charged twice yesterday and I still have not received my refund."
  intent = "refund_request"
  category = "Billing"
  priority = "High"
  sentiment = "Frustrated"
  classification_confidence = 0.86
  entities = @{
    issue = "duplicate charge"
    time = "yesterday"
  }
  retrieved_context = @(
    @{
      source = "Refund Policy"
      section = "Duplicate Charges"
      text = "Duplicate charges are eligible for refund after payment verification."
      score = 0.91
    }
  )
} | ConvertTo-Json -Depth 6

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/tickets/TCK-001/draft" -ContentType "application/json" -Body $body
```

And a real live chat request:

```powershell
$body = @{
  conversation_history = @(
    @{ sender = "customer"; message = "My account was charged twice." },
    @{ sender = "agent"; message = "I am sorry to hear that." },
    @{ sender = "customer"; message = "I need this fixed now." }
  )
  latest_message = "I need this fixed now."
  intent = "refund_request"
  category = "Billing"
  priority = "High"
  sentiment = "Frustrated"
  classification_confidence = 0.84
  retrieved_context = @(
    @{
      source = "Refund Policy"
      section = "Duplicate Charges"
      text = "Duplicate charges are eligible for refund after payment verification."
      score = 0.88
    }
  )
} | ConvertTo-Json -Depth 6

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/chat/conversations/CHAT-101/suggest" -ContentType "application/json" -Body $body
```

### Testing `app.py` With Postman

1. Start the API server from the project root:

```bash
uvicorn app:app --reload
```

2. Open Postman.

3. Create a new `POST` request for ticket draft generation:

- URL: `http://127.0.0.1:8000/tickets/TCK-001/draft`
- Header: `Content-Type: application/json`
- Body type: `raw`
- Format: `JSON`

Use this request body:

```json
{
  "customer_message": "I was charged twice yesterday and I still have not received my refund.",
  "intent": "refund_request",
  "category": "Billing",
  "priority": "High",
  "sentiment": "Frustrated",
  "classification_confidence": 0.86,
  "entities": {
    "issue": "duplicate charge",
    "time": "yesterday"
  },
  "retrieved_context": [
    {
      "source": "Refund Policy",
      "section": "Duplicate Charges",
      "text": "Duplicate charges are eligible for refund after payment verification.",
      "score": 0.91
    }
  ]
}
```

Expected response fields:

- `reply_draft`
- `agent_notes`
- `citations`
- `confidence`
- `missing_info`
- `escalation_required`
- `escalation_reason`

4. Create a second `POST` request for live chat suggestions:

- URL: `http://127.0.0.1:8000/chat/conversations/CHAT-101/suggest`
- Header: `Content-Type: application/json`
- Body type: `raw`
- Format: `JSON`

Use this request body:

```json
{
  "conversation_history": [
    {
      "sender": "customer",
      "message": "My account was charged twice."
    },
    {
      "sender": "agent",
      "message": "I am sorry to hear that."
    },
    {
      "sender": "customer",
      "message": "I need this fixed now."
    }
  ],
  "latest_message": "I need this fixed now.",
  "intent": "refund_request",
  "category": "Billing",
  "priority": "High",
  "sentiment": "Frustrated",
  "classification_confidence": 0.84,
  "retrieved_context": [
    {
      "source": "Refund Policy",
      "section": "Duplicate Charges",
      "text": "Duplicate charges are eligible for refund after payment verification.",
      "score": 0.88
    }
  ]
}
```

Expected response fields:

- `suggested_reply`
- `agent_notes`
- `citations`
- `confidence`
- `missing_info`
- `escalation_required`
- `escalation_reason`

5. Optional checks in Postman:

- `GET http://127.0.0.1:8000/docs` to open Swagger UI
- confirm every citation matches the evidence you passed in `retrieved_context`
- confirm billing/refund replies stay conditional and do not promise unsupported refunds
- confirm risky inputs return `escalation_required: true`

### Postman Troubleshooting

- If you get an API key error, the app process does not have `GEMINI_API_KEY` available.
- The app now loads the project-root `.env` file automatically.
- If needed, you can still set the variables in the same terminal before running `uvicorn app:app --reload`.

### What To Check In Real Responses

- citations should match retrieved evidence
- refund promises should stay conditional unless evidence clearly supports them
- `missing_info` should include items like `transaction_id` and `payment_receipt` for duplicate charge cases
- risky cases should trigger `escalation_required = true`
- the output should always be valid JSON-like Python data with the expected keys

## Documentation

For the full implementation explanation, see [IMPLEMENTATION.md](</c:/Users/Msi GF66/Desktop/Customer Support AI/live_chat/IMPLEMENTATION.md:1>).
