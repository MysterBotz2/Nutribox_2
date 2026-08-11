# Nutri-Box Web Companion

This React + TypeScript + Vite client is a browser companion for the FastAPI backend. It implements registration, login, bearer authentication, Dashboard, Nutrition Profile, Nutrition Targets, read-only Meal History, and detailed Progress analytics.

## Prerequisites

- Node.js 20.19+ or newer (the current project was validated with Node 24)
- npm
- Nutri-Box backend with PostgreSQL configured

## Setup

```powershell
Copy-Item .env.example .env
npm install
npm run generate:api
```

`VITE_*` variables are browser-visible. Normal Vite development uses same-origin relative API requests, so leave the private, ignored `web/.env` setting blank:

```text
VITE_API_BASE_URL=
```

An explicit origin is optional only for a deliberately separate web/API deployment. Never put backend secrets in a Vite environment file.

Never put database URLs, JWT secrets, Gemini keys, or other backend secrets in Vite environment files. `VITE_*` values are included in browser JavaScript.

## Start the backend and web client

From the repository root, start FastAPI:

```powershell
.\scripts\start.ps1
```

For browser development in `web/`:

```powershell
npm run dev
```

The standard development scripts listen on all local network interfaces. During Vite development, the browser requests `/api/...` from the same browser origin and Vite proxies only `/api` internally to `http://127.0.0.1:8000`. The browser never needs a compiled server LAN IP or a direct `:8000` API URL.

Use these addresses while both devices are on the same Wi-Fi network:

- On this PC: `http://localhost:5173` (or `http://127.0.0.1:5173`)
- From a phone or another LAN device: `http://<server-lan-ip>:5173`
- FastAPI on the LAN: `http://<server-lan-ip>:8000` (Swagger: `http://<server-lan-ip>:8000/docs`)

The normal proxied flow does not require a LAN origin in backend CORS because FastAPI receives the Vite server's local proxy request. CORS remains explicit/configurable for separately hosted browser clients:

```text
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

The backend allows only explicitly configured origins. It does not use wildcard CORS or cookie credentials; browser requests send bearer tokens in the `Authorization` header. If Windows Firewall prompts for Python or Node/Vite access, allow it on **Private networks** only for this trusted development workflow. Ensure the PC and test device are connected to the same Wi-Fi network; guest Wi-Fi and client isolation can prevent LAN access.

For a client installation, reserve a stable LAN address for the Nutri-Box server PC through the router's DHCP reservation feature. Do not embed that numeric address in source code. Installation-specific backend values—such as `DATABASE_URL`, `JWT_SECRET_KEY`, Gemini credentials, and provider configuration—remain private configuration. A future Raspberry Pi controller will similarly use one private deployment setting such as `NUTRIBOX_API_BASE_URL=http://<nutribox-server>:8000`; no Pi code is included here.

Future production hosting should preferably serve the web companion and `/api` under the same browser origin where practical. Static production hosting is not implemented in this development checkpoint.

## Commands

```powershell
npm run dev
npm run test
npm run lint
npm run typecheck
npm run build
npm run generate:api
```

`npm run generate:api` regenerates `src/api/generated/schema.ts` from `../docs/openapi.json`. Do not hand-edit the generated file.

## Authentication behavior

Registration uses JSON. Login uses FastAPI's OAuth2 form encoding and sends the email as `username`. After login, the access token is stored only in `sessionStorage`, then `GET /api/users/me` loads the authoritative current-user record.

`sessionStorage` is cleared when the browser session ends and on logout. It is still readable by JavaScript and therefore is not equivalent to an HttpOnly cookie against XSS; this is the explicit Phase 16A trade-off. A protected API `401` clears the token and authenticated query state without automatic retry.

## Phase 16B routes and data behavior

- `/app/dashboard` uses backend-authoritative `GET /api/progress/today` and `GET /api/progress/target-status`, passing the browser IANA timezone detected through `Intl` (falling back to `UTC`). It displays stored Decimal API values without recalculating nutrition client-side. A small recent-meal list uses the bounded `GET /api/meals?limit=3` contract.
- `/app/profile` views or creates/replaces the separate NutritionProfile through `/api/users/me/profile`. A missing profile (`404`) is a normal setup state.
- `/app/targets` views or creates/replaces NutritionTarget through `/api/users/me/targets`. Targets are explicitly configured values, never automatically calculated from profile data. A missing target (`404`) is a normal setup state; changing targets refreshes dashboard target-status data.

The dashboard treats negative remaining values neutrally (for example, “Above configured target by …”) and preserves percentages above 100%; only the visual fill is capped for layout. No target is presented as a clinical recommendation.

The browser companion is account-oriented. The future Raspberry Pi touchscreen will be a separate, device-oriented application; this client intentionally has no hardware, live-weight, tare, heating, camera, or device-control UI.

## Phase 16C meals and progress

- `/app/meals` uses bounded `GET /api/meals?limit&offset` pagination and displays stored meal totals; it never loads all history at once.
- `/app/meals/:mealId` uses `GET /api/meals/{meal_id}` and displays stored Meal and MealItem nutrient snapshots. A `404` is shown neutrally as “Meal not found.” without exposing ownership details.
- `/app/progress` uses backend `today`, `daily`, `weekly`, `summary`, and `target-status` endpoints. Browser IANA timezone detection is sent with each request, with the existing `UTC` fallback.
- The selected daily date is sent to FastAPI unchanged. Weekly navigation requests Monday `week_start` values; backend-provided Monday–Sunday daily series are displayed directly.
- Rolling summaries offer 7, 30, and 90 day backend-bounded periods. The displayed daily average is the backend value, calculated over all calendar days in the selected period.

Progress charts are responsive CSS visualizations of the backend daily series. Decimal strings are converted to JavaScript numbers only at the chart-display boundary; the authoritative API values are not mutated or used for client-side nutrition calculations. Numerical values remain visible alongside every chart.
