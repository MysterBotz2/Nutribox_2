# Nutri-Box API Integration (v1)

## Base URL and contract

The existing `/api/...` routes are the Nutri-Box **v1** contract. Breaking changes require a future versioning decision; clients must not assume an unannounced route rename. Configure the base URL in each client environment:

- Same computer: `http://127.0.0.1:8000`
- LAN example: `http://192.168.x.x:8000` (replace with the development computer's actual LAN address)

Swagger is at `/docs`, ReDoc is at `/redoc`, and the generated machine-readable contract is [`openapi.json`](openapi.json). FastAPI is the authoritative business layer: clients must not authoritatively calculate nutrients, totals, target comparisons, ownership, authentication, or food resolution.

## Authentication

`POST /api/auth/register` accepts JSON. `POST /api/auth/token` accepts `application/x-www-form-urlencoded`; its `username` field is the user's email. Login returns `access_token` and `token_type` (`bearer`). Send protected requests with:

```http
Authorization: Bearer <access_token>
```

Tokens expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (30 by default). Mobile clients should keep tokens in platform-secure storage, not ordinary plaintext storage. A `401` means a token is missing, invalid, or expired. A `404` for another user's meal is intentional privacy behavior.

## Contract inventory

| Method | Path | Auth | Content / input | Success | Important errors / behavior |
| --- | --- | --- | --- | --- | --- |
| GET | `/` | No | — | service status | `200` |
| GET | `/api/health` | No | — | health status | `200`; `503` when PostgreSQL is unavailable |
| POST | `/api/auth/register` | No | JSON `UserRegistrationRequest` | `201 PublicUser` | `409` duplicate email; `422` validation |
| POST | `/api/auth/token` | No | form `username`, `password` | `AccessTokenResponse` | `401` credentials; `503` auth configuration |
| GET | `/api/users/me` | Bearer | — | `PublicUser` | `401` |
| GET / PUT | `/api/users/me/profile` | Bearer | — / JSON `NutritionProfileUpdateRequest` | `NutritionProfileResponse` | `404` absent profile; `401`, `422` |
| GET / PUT | `/api/users/me/targets` | Bearer | — / JSON `NutritionTargetUpdateRequest` | `NutritionTargetResponse` | `404` absent targets; `401`, `422` |
| POST | `/api/device/simulate` | No | JSON `DeviceSimulationRequest` | `DeviceReadingResponse` | development simulation only; `422` |
| POST | `/api/ai/recognize-food` | No | multipart field `file` | `FoodRecognitionResponse` | `413` size; `415` MIME; `422` invalid image; provider `429`, `502`, `503`, `504` |
| POST | `/api/ai/coach` | Bearer | JSON `NutritionCoachRequest`; optional `timezone` | `NutritionCoachResponse` | `401`, `422` timezone |
| GET | `/api/nutrition/search` | No | query `q` | `FoodListResponse` | alias search returns canonical foods without duplicates; `422` |
| GET | `/api/nutrition/{food_id}` | No | path ID | `FoodResponse` | `404` |
| POST | `/api/nutrition/calculate` | No | JSON `PortionCalculationRequest` | `PortionCalculationResponse` | `404`; `422` |
| POST | `/api/meals/analyze` | No | multipart `file`, form `weight_grams` | `MealAnalysisResponse` | `413`, `415`, `422`, provider errors; domain outcome remains `200` |
| POST | `/api/meals` | Bearer | JSON `MealCreateRequest` | `201 MealResponse` | `401`, `404` food, `422` |
| GET | `/api/meals` | Bearer | `limit` 1–100, `offset` ≥0 | `MealListResponse` | newest first; `401`, `422` |
| GET | `/api/meals/{meal_id}` | Bearer | path ID | `MealResponse` | `404` for missing/unowned; `401` |
| GET | `/api/progress/today` | Bearer | optional IANA `timezone` | `DailyProgressResponse` | UTC default; `401`, `422` |
| GET | `/api/progress/daily` | Bearer | `date`, optional `timezone` | `DailyProgressResponse` | `401`, `422` |
| GET | `/api/progress/weekly` | Bearer | Monday `week_start`, optional `timezone` | `WeeklyProgressResponse` | seven entries; `401`, `422` |
| GET | `/api/progress/summary` | Bearer | `days` 1–365, optional `timezone` | `ProgressSummaryResponse` | `401`, `422` |
| GET | `/api/progress/target-status` | Bearer | optional `timezone` | `TargetStatusResponse` | `401`, `422` |

## Data representation

Nutrition values are Decimal-safe JSON strings where documented by the response schema, for example `"protein_g": "35.500"`. Do not assume nutrient values are JavaScript numbers. Convert only for presentation; backend calculations and stored snapshots remain authoritative.

`POST /api/ai/recognize-food` accepts JPEG, PNG, and WEBP in multipart field `file`; uploads are validated for MIME type, actual image format, corruption, and configured size. Its `source` is informational (`mock` or `gemini`), not a vendor-specific client workflow.

`POST /api/meals/analyze` accepts `file` plus a manual `weight_grams`. A `200` response can have `calculated`, `food_not_recognized`, `requires_food_selection`, or `nutrition_reference_not_found`. `requires_food_selection` means Nutri-Box did not divide a shared plate weight among foods; obtain or confirm an individual portion before creating a meal.

For `POST /api/meals`, submit only canonical `food_id` and positive `weight_grams`; never submit trusted nutrient totals or `user_id`.

## Progress and targets

`timezone` is an IANA identifier such as `Asia/Manila`; omitted timezone is UTC. Weeks run Monday–Sunday; weekly results always include seven zero-filled daily points. Summary `days` is bounded to 1–365 and `daily_average` divides by all calendar days in the period, including empty days. Target status is neutral arithmetic from stored meal snapshots and configured targets.

## Error contract

The stable safe error shape is normally `{"detail": "..."}`. FastAPI/Pydantic validation errors use `{"detail": [...]}` with HTTP `422`. Common client actions:

- `400`: malformed endpoint-specific request where applicable.
- `401`: obtain or refresh the bearer token, then retry once.
- `404`: do not infer existence of protected resources; ownership is enforced.
- `409`: correct duplicate registration data.
- `422`: correct request fields, dates, timezones, bounds, MIME type, or image.
- `429`: wait and retry provider calls conservatively.
- `502` / `503` / `504`: provider or service failure; show a safe retry state and do not expose secrets.

## LAN development

For a physical phone or device, start the native API with `scripts\start.ps1 -HostAddress 0.0.0.0 -Port 8000`. `127.0.0.1` works only on the development computer. Configure the phone with the computer's actual LAN address and allow inbound TCP on the selected port through Windows Firewall manually. Do not hard-code a LAN address into the mobile app or backend.
