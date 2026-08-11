# Native Deployment (Windows PowerShell)

Nutri-Box runs natively with Python and PostgreSQL; Docker is not required for this deployment path.

1. Install Python 3.11+ and PostgreSQL on the target computer.
2. Create a least-privilege PostgreSQL application user and database using local administrator tooling.
3. Copy `.env.example` to `backend/.env`; configure `DATABASE_URL`, `JWT_SECRET_KEY`, and the desired provider settings. Never commit this file.
4. Run `scripts\setup.ps1`, then `scripts\migrate.ps1`.
5. Run `scripts\start.ps1` and verify `GET /api/health`.

The local default bind address is `127.0.0.1`. For a LAN client, use `scripts\start.ps1 -HostAddress 0.0.0.0 -Port 8000`, configure the client base URL to the host's LAN address, and manually allow the port through Windows Firewall if needed.

## Configuration

Required operational settings are documented in `.env.example`: `DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, food-recognition settings, Gemini settings, and `NUTRITION_COACH_PROVIDER`. Keep food recognition and coaching set to `mock` unless explicitly opting in to Gemini. Native deployment does not require a Gemini key for mock operation.

## Database migration

Run only committed migrations:

```powershell
.\scripts\migrate.ps1
```

This invokes `python -m alembic -c alembic.ini upgrade head`; it never generates or downgrades migrations. Verify current revision with `.\scripts\check.ps1`.

## Backup and restore

Back up the configured PostgreSQL database with PostgreSQL's `pg_dump`, using a connection method appropriate for your installation:

```powershell
pg_dump --format=custom --file .\nutribox-backup.dump --dbname "$env:DATABASE_URL"
```

The backup contains the Nutri-Box database schema and data. Restore can overwrite data. Stop the API, confirm the target database is correct, then use PostgreSQL's restore tooling; for an intentionally replaced database, a typical workflow is:

```powershell
# Destructive: restore into the selected target database.
pg_restore --clean --if-exists --no-owner --dbname "$env:DATABASE_URL" .\nutribox-backup.dump
```

Set `DATABASE_URL` only in the current PowerShell session if using these commands; do not put passwords into command history. Depending on PostgreSQL permissions, restoration may require an administrator-managed target database.

## Curated nutrition import

Imports are explicit administrative operations, never startup work. Create a reviewed UTF-8 CSV from `data/templates/foods_import_template.csv`, include provenance and explicit verification state, then run:

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m app.cli.import_foods ..\data\import\foods.csv --dry-run
..\.venv\Scripts\python.exe -m app.cli.import_foods ..\data\import\foods.csv
Pop-Location
```

Dry-run validates source provenance, decimals, aliases, and conflicts without writes. A real import is atomic; no automatic seeding occurs.
