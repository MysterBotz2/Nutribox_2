# Nutri-Box API

Phase 2 provides the FastAPI and PostgreSQL foundation for Nutri-Box. It includes SQLAlchemy 2.x, Psycopg 3, Alembic, and a database-aware health check. Application tables, hardware, OpenAI, authentication, Docker, and Flutter are intentionally deferred.

## Prerequisites

- Python 3.11 or newer
- Windows PowerShell

## Setup (Windows PowerShell)

From the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and replace all `DATABASE_URL` placeholders with the database, user, and password you created manually. Use the Psycopg 3-compatible format:

```text
DATABASE_URL=postgresql+psycopg://YOUR_USERNAME:YOUR_PASSWORD@YOUR_HOST:YOUR_PORT/YOUR_DATABASE
```

If PowerShell prevents activation for your user account, run this once in a PowerShell window:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Run the API

```powershell
uvicorn app.main:app --app-dir backend --reload
```

The API will be available at `http://127.0.0.1:8000`.

- `GET /` returns the API name and running status.
- `GET /api/health` verifies database connectivity. It returns `200` with `{"status": "healthy", "database": "connected"}` when PostgreSQL is available, otherwise a safe `503` response.
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Run tests

```powershell
pytest backend/tests
```

## Alembic

Alembic uses the same `DATABASE_URL` from `.env`; no credentials are stored in `alembic.ini`.

```powershell
# Check that Alembic can load the migration environment and show the current revision.
alembic -c alembic.ini current

# Display the migration history (there are no Nutri-Box migrations in Phase 2).
alembic -c alembic.ini history
```
