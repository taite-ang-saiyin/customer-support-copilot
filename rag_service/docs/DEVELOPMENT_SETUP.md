# Development Setup

## Prerequisites

Install:

- Python 3.10 or newer
- Docker Desktop or Docker Engine
- Docker Compose
- Git

Optional tools:

- Postman or curl for API testing
- VS Code or another Python-friendly editor

## Python Virtual Environment

Create and activate a virtual environment.

macOS or Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

The backend application has not been implemented yet, but the dependency list is prepared for the planned FastAPI, PostgreSQL, Chroma, and embedding stack.

## PostgreSQL Setup With Docker Compose

Start PostgreSQL:

```bash
docker compose up -d
```

The local database settings are:

- Database: `support_copilot`
- User: `postgres`
- Password: `postgres`
- Port: `5432`

Stop services:

```bash
docker compose down
```

## Chroma Local Storage Setup

Chroma will use local persistent storage configured by:

```env
CHROMA_DB_PATH=./chroma_db
```

The `chroma_db/` directory is ignored by Git because it is generated local data.

## Environment Setup

Create a local `.env` file:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Review the values in `.env` before running the application.

## Running FastAPI

After the backend app is implemented, run:

```bash
uvicorn app.main:app --reload
```

The API should be available at:

```text
http://localhost:8000
```

## Testing API Using Swagger UI

After FastAPI routes are implemented, open:

```text
http://localhost:8000/docs
```

Use Swagger UI to test upload, reindex, search, document listing, document detail, and document deletion endpoints.

## Common Troubleshooting

If PostgreSQL fails to start, check whether another service is already using port `5432`.

If Python cannot import installed packages, confirm the virtual environment is activated.

If Chroma data appears stale, stop the app and remove the local `chroma_db/` directory only when it is safe to rebuild indexes.

If embedding model download fails, check internet access and retry. The model may be cached locally after the first successful download.

If `.env` values are not loading, confirm the file is named `.env` and is located at the repository root.
