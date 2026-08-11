# Nutri-Box API

Nutri-Box is a FastAPI and PostgreSQL backend for authenticated meal persistence, deterministic nutrient calculation, progress analytics, food recognition, and nutrition-data administration. The existing `/api/...` routes are the documented v1 integration contract.

## Integration and deployment

- [API integration contract](docs/API_INTEGRATION.md)
- [Native Windows deployment](docs/DEPLOYMENT.md)
- [Integration checklist](docs/INTEGRATION_CHECKLIST.md)
- [Generated OpenAPI schema](docs/openapi.json)
- [REST Client examples](docs/http/nutribox.http)

React Native/Expo and physical-device software are separate clients of this backend. They submit inputs and display results; the backend remains authoritative for authentication, ownership, food resolution, nutrients, totals, and progress.

## Native setup (Windows PowerShell)

```powershell
.\scripts\setup.ps1
Copy-Item .env.example backend\.env
notepad backend\.env
.\scripts\migrate.ps1
.\scripts\start.ps1
```

Configure `DATABASE_URL` and `JWT_SECRET_KEY` in the ignored `backend/.env` file. Generate a local JWT secret with:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

For LAN development, use a configured client base URL and start the backend explicitly on all interfaces:

```powershell
.\scripts\start.ps1 -HostAddress 0.0.0.0 -Port 8000
```

Open `http://127.0.0.1:8000/docs` on the host computer. A physical phone must use the host computer's LAN address; Windows Firewall may require a manual inbound TCP rule. Do not hard-code an address in source code.

## Checks and contract export

```powershell
.\scripts\check.ps1 -RunTests
Push-Location backend
..\.venv\Scripts\python.exe -m app.cli.export_openapi
Pop-Location
```

The export is generated from the FastAPI application and does not require Gemini or a running server.

## Providers

Food recognition defaults to `mock`; Gemini is opt-in through the ignored `backend/.env` file. The AI Coach remains mock-only. See the API integration document for provider-neutral response behavior and safe provider errors.

## Nutrition ingestion

Curated nutrition imports are explicit, validated, transactional administrative commands. See [deployment documentation](docs/DEPLOYMENT.md#curated-nutrition-import) for dry-run and real-import steps. No food data is seeded automatically.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

Docker is intentionally not part of the current native deployment workflow.
