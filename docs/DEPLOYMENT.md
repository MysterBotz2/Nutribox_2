# Native Deployment (Windows PowerShell)

Nutri-Box runs natively with Python and PostgreSQL; Docker is not required for this deployment path.

1. Install Python 3.11+ and PostgreSQL on the target computer.
2. Create a least-privilege PostgreSQL application user and database using local administrator tooling.
3. Copy `.env.example` to `backend/.env`; configure `DATABASE_URL`, `JWT_SECRET_KEY`, and the desired provider settings. Never commit this file.
4. Run `scripts\setup.ps1`, then `scripts\migrate.ps1`.
5. Run `scripts\start.ps1` and verify `GET /api/health`.

The development default bind address is `0.0.0.0:8000`; command-line overrides remain available. For web-companion development, open `http://<server-lan-ip>:5173`: the browser uses relative `/api/...` requests and Vite proxies them locally to FastAPI at `127.0.0.1:8000`. The browser therefore does not need a compiled LAN API address. Allow development access only through Windows Firewall Private networks when needed.

For a client installation, use a router DHCP reservation to give the Nutri-Box server PC a stable LAN identity rather than editing source code with an address. Backend secrets and provider settings remain private installation-specific environment configuration. Future Raspberry Pi software will use one private backend-base setting, not a hard-coded address.

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
