# Nutri-Box API

Phase 8 provides the FastAPI, PostgreSQL, mock-device, provider-neutral mock food-recognition, canonical nutrition, meal analysis, and local meal-persistence foundations for Nutri-Box. External AI providers, hardware, authentication, Docker, and Flutter are intentionally deferred.

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
- `GET /api/nutrition/search?q=...` searches canonical food reference data.
- `GET /api/nutrition/{food_id}` returns one canonical food reference record.
- `POST /api/nutrition/calculate` calculates a measured food portion from stored per-100g reference values without saving a meal.
- `POST /api/meals/analyze` combines a validated image, a manual development weight, canonical food lookup, and deterministic nutrient calculation without saving a meal.
- `POST /api/meals` saves a confirmed, server-calculated meal from canonical food IDs and positive manual weights.
- `GET /api/meals` lists persisted local prototype meals, newest first, with pagination.
- `GET /api/meals/{meal_id}` returns one persisted meal and its immutable food and nutrition snapshots.
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

`FOOD_RECOGNITION_PROVIDER` currently supports `mock` only. Future provider adapters will use the same provider-neutral endpoint and response schema.

## Nutrition reference data

Food nutrition reference data is stored in PostgreSQL on a per-100-gram basis. No external nutrition provider is connected and the application does not seed unverified nutrition data. Real food records must include validated source provenance. Deterministic portion-based nutrient calculations are available in Phase 6.

The public nutrition endpoints are read-only in this phase:

```text
GET /api/nutrition/search?q=rice
GET /api/nutrition/{food_id}
POST /api/nutrition/calculate
```

Portion calculation uses Python `Decimal`, never binary float conversion of stored nutrition data. Each calculated nutrient is rounded once to three decimal places with round-half-up behavior. A `0 g` portion is valid and returns zero values. The calculation does not create a meal or persist any result.

Meal analysis uses the configured provider-neutral food-recognition provider and manually supplied weight during hardware-free development. Nutrition always comes from canonical PostgreSQL Food records, not AI output. Multiple recognized foods require user selection; their shared plate weight is never divided automatically. Analysis results are transient and are not persisted.

Confirmed meals are persisted only through `POST /api/meals`. The backend resolves every requested food, calculates all item nutrients and totals, and stores snapshots so later food-reference updates do not change recorded history. These endpoints are for local prototype records only; user accounts, authentication, and user-scoped history remain future work.

## Run tests

```powershell
pytest backend/tests
```

## Alembic

Alembic uses the same `DATABASE_URL` from `backend/.env`; no credentials are stored in `alembic.ini`.

```powershell
# Check that Alembic can load the migration environment and show the current revision.
alembic -c alembic.ini current

# Display the migration history.
alembic -c alembic.ini history
```

## Database integration tests

Database integration tests require a separate PostgreSQL database configured through `TEST_DATABASE_URL`. They will skip when it is absent, and refuse to run if it matches `DATABASE_URL`. Test data runs inside transactions that are rolled back after each test.
