# Nutri-Box Web Companion

This React + TypeScript + Vite client is a Phase 16A browser client of the FastAPI backend. It implements registration, login, bearer authentication, current-user loading, protected routing, logout, and a minimal authenticated shell only.

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

Set only the browser-visible backend address in `.env`:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
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

Open the Vite URL printed by the terminal, normally `http://localhost:5173`. The backend must allow that exact origin through `CORS_ALLOWED_ORIGINS` in `backend/.env`, for example:

```text
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

The backend allows only explicitly configured origins. It does not use wildcard CORS or cookie credentials; browser requests send bearer tokens in the `Authorization` header.

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
