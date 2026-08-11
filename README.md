# Nutri-Box API

Phase 11 provides the FastAPI, PostgreSQL, mock-device, provider-neutral mock food recognition, canonical nutrition, meal analysis, local meal persistence, local accounts, deterministic progress analytics, and explicit nutrition-target foundations for Nutri-Box. External AI providers, hardware, Docker, and Flutter are intentionally deferred.

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

Generate a development JWT secret locally and put it in `backend/.env`; never commit it or reuse it for production:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

```text
JWT_SECRET_KEY=PASTE_THE_GENERATED_VALUE_HERE
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
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
- `POST /api/auth/register` creates a local account with an Argon2 password hash.
- `POST /api/auth/token` accepts OAuth2 form fields; its `username` field is the account email and it returns an expiring bearer access token.
- `GET /api/users/me`, `GET /api/users/me/profile`, and `PUT /api/users/me/profile` require bearer authentication.
- `GET /api/users/me/targets` and `PUT /api/users/me/targets` require bearer authentication and manage one explicit target set for the current user.
- `POST /api/meals`, `GET /api/meals`, and `GET /api/meals/{meal_id}` require bearer authentication and are scoped to the current user.
- `GET /api/progress/today`, `GET /api/progress/daily`, `GET /api/progress/weekly`, and `GET /api/progress/summary` require bearer authentication and return deterministic analytics from stored meal snapshots.
- `GET /api/progress/target-status` requires bearer authentication and compares today's stored totals with configured targets.
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

Confirmed meals are persisted only through `POST /api/meals`. The backend resolves every requested food, calculates all item nutrients and totals, and stores snapshots so later food-reference updates do not change recorded history. These endpoints are local prototype records scoped to the authenticated account.

## Progress analytics

Progress is derived from the authenticated user's stored `Meal.total_*` snapshots; it does not recalculate food nutrition, call an AI provider, or use an external nutrition API. Legacy meals with no owner and meals belonging to other users are excluded. Dates use an IANA `timezone` query parameter and default to `UTC`.

- `GET /api/progress/today?timezone=Asia/Manila`
- `GET /api/progress/daily?date=2026-08-10&timezone=Asia/Manila`
- `GET /api/progress/weekly?week_start=2026-08-10&timezone=Asia/Manila`
- `GET /api/progress/summary?days=30&timezone=Asia/Manila`

Weekly periods are Monday through Sunday, and `week_start` must be a Monday. Weekly and summary responses contain zero-filled daily entries for charting. Summary `daily_average` divides totals by every requested calendar day, including days without meals. Values use `Decimal` and are presented to three decimal places. This phase does not calculate BMR, TDEE, calorie targets, macro targets, or medical recommendations.

## Nutrition targets

Nutrition targets are explicit configured values, not automatically calculated recommendations. Each target set stores a required provenance type (`manual`, `researcher_assigned`, or `professional_assigned`) and may optionally store a protocol/plan reference and short notes. Individual calorie, protein, carbohydrate, fat, and fiber targets may be omitted, but at least one positive target is required when saving a set.

Use authenticated endpoints:

- `GET /api/users/me/targets`
- `PUT /api/users/me/targets`
- `GET /api/progress/target-status?timezone=Asia/Manila`

Target status uses the stored historical Meal totals. For every configured nutrient, `remaining = target - consumed`, so it can be negative when consumption exceeds the configured target. `percent_of_target = consumed / target * 100`; absent individual targets produce `null` comparison values. No target record produces `null` target/comparison sections. These are neutral numeric values only: Nutri-Box does not prescribe medical diets, generate targets with AI, or calculate BMR/TDEE/calorie needs in this phase. A later validated methodology may introduce calculated targets explicitly.

Passwords are stored only as Argon2 hashes. Access tokens are signed JWTs that contain only a user identifier and expiry; they expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (30 by default). Do not place JWT secrets in source control. Legacy meals created before Phase 9 remain valid with `user_id = NULL`; new persisted meals always use the authenticated user. The foreign key is `ON DELETE SET NULL`, so a future user deletion would preserve historical prototype/research meals. Nutrition profiles store optional preferences only; they do not calculate calorie targets, BMR, TDEE, or medical guidance.

## Swagger authentication workflow

1. Start the API and open `http://127.0.0.1:8000/docs`.
2. Use `POST /api/auth/register` to create an account. The password must be 12–128 characters.
3. Use `POST /api/auth/token` with form data: put the email in `username` and the password in `password` if you need a token outside Swagger.
4. In Swagger, click **Authorize**, enter the email as `username` and the password, then authorize; Swagger obtains the bearer token through `/api/auth/token`.
5. Call `GET /api/users/me`, then create or replace the optional profile with `PUT /api/users/me/profile`.
6. Call `POST /api/meals` with canonical food IDs and positive weights. `GET /api/meals` returns only the authorized account's meals.
7. Call an authenticated progress endpoint, for example `GET /api/progress/weekly?week_start=2026-08-10&timezone=UTC`.
8. Configure targets with `PUT /api/users/me/targets`, then call `GET /api/progress/target-status` for neutral target comparisons.

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
