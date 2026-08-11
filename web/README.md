# Nutri-Box Web Companion

This React + TypeScript + Vite client is a browser companion for the FastAPI backend. It implements registration, login, bearer authentication, and the Phase 16B account experience: Dashboard, Nutrition Profile, and configured Nutrition Targets.

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

Set only the browser-visible backend address in the private, ignored `web/.env` file. For this development PC's current LAN address:

```text
VITE_API_BASE_URL=http://192.168.8.35:8000
```

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

The standard development scripts listen on all local network interfaces. Use these addresses while both devices are on the same Wi-Fi network:

- On this PC: `http://localhost:5173` (or `http://127.0.0.1:5173`)
- From a phone or another LAN device: `http://192.168.8.35:5173`
- FastAPI on the LAN: `http://192.168.8.35:8000` (Swagger: `http://192.168.8.35:8000/docs`)

The backend must allow every browser origin used through the private, ignored `backend/.env` file:

```text
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://192.168.8.35:5173
```

The backend allows only explicitly configured origins. It does not use wildcard CORS or cookie credentials; browser requests send bearer tokens in the `Authorization` header.

If Windows Firewall prompts for Python or Node/Vite access, allow it on **Private networks** only for this development workflow. Ensure the PC and test device are connected to the same Wi-Fi network; guest Wi-Fi and client isolation can prevent LAN access. `192.168.8.35` is the current DHCP address and may change after reconnecting or restarting the router unless a DHCP reservation is configured. If it changes, update the private `web/.env` API URL and the private `backend/.env` CORS allowlist, then restart both servers.

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
