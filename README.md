# Nutri-Box API

Phase 4 provides the FastAPI, PostgreSQL, mock-device, and mock food-recognition foundations for Nutri-Box. External AI providers, application tables, hardware, authentication, Docker, and Flutter are intentionally deferred.

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
Copy-Item .env.example backend\.env
```

Edit `backend/.env` and replace all `DATABASE_URL` placeholders with the database, user, and password you created manually. Use the Psycopg 3-compatible format:

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
- `POST /api/device/simulate` accepts validated development-only simulated weight and temperature readings. Raspberry Pi sensor integration will be added in a later phase.
- `POST /api/ai/recognize-food` accepts JPEG, PNG, or WEBP uploads and returns a simulated food-recognition result. It uses `MockFoodRecognitionProvider`; the image is validated but is not analyzed by an external AI service.
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

`FOOD_RECOGNITION_PROVIDER` currently supports `mock` only. Future provider adapters will use the same provider-neutral endpoint and response schema.

## Run tests

```powershell
pytest backend/tests
```

## Alembic

Alembic uses the same `DATABASE_URL` from `backend/.env`; no credentials are stored in `alembic.ini`.

```powershell
# Check that Alembic can load the migration environment and show the current revision.
alembic -c alembic.ini current

# Display the migration history (there are no Nutri-Box migrations in Phase 2).
alembic -c alembic.ini history
```
