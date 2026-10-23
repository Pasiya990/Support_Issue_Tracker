# Support Issue Management System

A beginner-friendly FastAPI REST API for creating and managing support issues. It uses SQLite for persistent storage and SQLAlchemy 2.0 for database access.

## Technology

Python 3.12+, FastAPI, Uvicorn, SQLAlchemy 2, Pydantic 2, SQLite, Pytest, and HTTPX.

## Project structure

```text
backend/
  main.py                 FastAPI application and CORS
  database.py             Engine, session factory, request dependency
  models.py               SQLAlchemy issue table
  schemas.py              Pydantic request and response validation
  crud.py                 Database operations and query composition
  services.py             UTC normalization and overdue business rule
  routers/issues.py       Issue REST endpoints
  tests/                  API and business rule tests with temporary SQLite
frontend/                 Reserved for the frontend application
requirements.txt
```

The backend implementation is contained in `backend/`, matching the existing project layout. `schema.py` remains as a compatibility module that re-exports the models in `schemas.py`.

## Setup and run (macOS)

Use Python 3.12 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

The SQLite database file `support_issues.db` is created in the current working directory when the application starts. Records persist across restarts. Set `DATABASE_URL` to use another SQLAlchemy database URL.

Open interactive API docs at <http://127.0.0.1:8000/docs>. The health endpoint is `GET /api/health`.

## CORS configuration

By default, browser requests are accepted from `http://localhost:3000`, `http://localhost:5173`, and `http://127.0.0.1:5173`. Set `CORS_ORIGINS` to a comma-separated list to add or replace origins, for example:

```bash
export CORS_ORIGINS="http://localhost:3000,https://my-frontend.example"
```

Credentials are enabled only for these explicitly listed origins. Common REST methods and JSON request headers are allowed.

## API endpoints

All issue endpoints are under `/api/issues`.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/issues` | Create an issue (201). ID, status, and UTC reporting timestamp are generated/defaulted by the backend. |
| GET | `/api/issues?skip=0&limit=20` | List newest first; supports `skip`, `limit` (maximum 100), `q`, `priority`, and `status` together. |
| GET | `/api/issues/{issue_id}` | Retrieve one issue. |
| PUT | `/api/issues/{issue_id}` | Replace editable fields: client name, title, description, priority, and status. |
| PATCH | `/api/issues/{issue_id}/status` | Change only the status. |
| DELETE | `/api/issues/{issue_id}` | Permanently delete an issue (204). |
| GET | `/api/issues/search?q=account` | Case-insensitive partial search in client name and title. Supports pagination. |
| GET | `/api/issues/filter?priority=High&status=Open` | Filter by priority and/or status; also accepts `q`, `skip`, and `limit`. |
| GET | `/api/issues/overdue` | High priority, unresolved issues older than 24 hours, oldest first. |
| GET | `/api/issues/stats` | Dashboard counts. |

Priority values are `Low`, `Medium`, and `High`; status values are `Open`, `In Progress`, and `Resolved`.

Example create request:

```bash
curl -X POST http://127.0.0.1:8000/api/issues \
  -H 'Content-Type: application/json' \
  -d '{"client_name":"ABC Solutions","issue_title":"Unable to access account","description":"The client cannot log in.","priority":"High"}'
```

The response contains all issue fields, including `is_overdue_high_priority`. The API rejects blank required text and invalid enum values with HTTP 422, and returns 404 for missing issue IDs.

## Overdue rule

An issue is overdue only when it is High priority, is not Resolved, and its reporting time is more than 24 hours ago. Exactly 24 hours does not qualify. The flag is calculated when returning issues and is not stored. Timestamps are generated in UTC; SQLite may load a timestamp without timezone metadata, so the service layer interprets those values as UTC before comparison.

## Run tests

```bash
pytest -v backend/tests
```

Tests use a separate in-memory SQLite database and do not modify `support_issues.db`.
