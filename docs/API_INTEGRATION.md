# Nutri-Box API Integration (v1)

## Base URL and contract

The existing `/api/...` routes are the Nutri-Box **v1** contract. Breaking changes require a future versioning decision; clients must not assume an unannounced route rename. Non-browser clients configure an installation-specific API base URL in their own environment:

- Same computer: `http://127.0.0.1:8000`
- LAN example: `http://192.168.x.x:8000` (replace with the development computer's actual LAN address)

Swagger is at `/docs`, ReDoc is at `/redoc`, and the generated machine-readable contract is [`openapi.json`](openapi.json). FastAPI is the authoritative business layer: clients must not authoritatively calculate nutrients, totals, target comparisons, ownership, authentication, or food resolution.

## Authentication

## R2B1 sensitive profile and consent

All routes below require a bearer token and operate only on the token owner:

| Method | Route | Purpose |
| --- | --- | --- |
| GET / PUT | `/api/users/me/profile-consent` | Read or fully replace `sensitive_storage`, `personalization`, and `ai_context`. |
| GET / PUT | `/api/users/me/sensitive-profile` | Read or fully replace active sensitive declarations. PUT requires `sensitive_storage: granted` and otherwise returns `403`. |

Missing consent reads as `not_asked` for all three purposes. Storage withdrawal
deletes the active sensitive context; personalization/AI-context withdrawal does
not. `null` means unknown or cleared, while a medical condition of `none` is an
explicit declaration. Sensitive data is never included in food, meal, progress,
or public APIs, and R2B1 does not pass it to the Coach.

Blood type, somatotype, and BMI fields are unsupported. `budget_allotment` is a
nullable tier on the ordinary profile; lifestyle diets use existing
`dietary_restrictions`. R2B1 implements no clinical rules, medical thresholds,
recommendation logic, or sensitive AI transmission.

## R2C mobile onboarding status

`GET /api/users/me/onboarding-status` is an authenticated, read-only,
backend-authoritative completion contract for the future React Native/Expo
client. It returns only:

```json
{
  "completed": false,
  "missing_required_fields": ["medical_conditions", "smoking_history"]
}
```

It never returns profile values, consent values, or any sensitive declaration.
The deterministic required concepts are `medical_conditions`,
`smoking_history`, `drinking_history`, `body_build`, `allergies`,
`medical_needs`, `lifestyle_diets`, `activity_level`, `budget_allotment`, and
`nutrition_goal`. `pregnancy_postpartum` and `ethnicity` are optional.

`null` means missing/unknown and is incomplete. Existing explicitly empty label
arrays mean “none selected” for allergies, lifestyle diets, and medical needs.
Medical conditions require a non-empty valid declaration, so explicit `none`
counts as complete. Sensitive requirements count only while
`sensitive_storage` is `granted`; withdrawal clears active sensitive values and
can make onboarding incomplete without affecting login or ordinary account use.
Clients must not calculate or persist their own authoritative completion flag.

## R2 profile handoff and mobile-cache boundary

All R2 profile, consent, and onboarding routes require the same bearer token as
the rest of the owner-only `/api/users/me/...` API. No request accepts a
`user_id`; the token subject is the sole resource owner. `PUT` profile,
consent, and sensitive-profile requests are full replacements, so a client must
read the current resource before changing only one field.

| Data group | Route/resource | Mobile-cache status |
| --- | --- | --- |
| Medical conditions, pregnancy/postpartum, smoking, drinking, ethnicity | Sensitive profile | Backend-only; do not cache in the mobile client. |
| Body build, allergies, medical needs, lifestyle diets, activity level, budget allotment, nutrition goal | Profile/sensitive profile | Future cache eligible only; FastAPI/PostgreSQL remains authoritative and offline writes are not defined. |
| Consent states | Profile consent | Read/write only through the backend; do not infer permission from stored declarations. |
| Completion | Onboarding status | Derived backend metadata only; never persist a client-authoritative completion flag. |

`lifestyle_diets` is the onboarding concept but currently uses the ordinary
profile field `dietary_restrictions`. This is deliberate R2 technical debt;
clients should use the documented field today and must not introduce a parallel
field without a later compatibility decision. No R2 route passes sensitive data
to the Coach or supports medical recommendations, BMR/TDEE, or target
prescription.

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

## Core profile contract (R2A)

FastAPI/PostgreSQL is the authoritative profile system of record. The future
React Native client may retain only a secure local cache; it is not an
independent profile authority.

`GET /api/users/me/profile` and `PUT /api/users/me/profile` remain the only
ordinary-user profile routes. They are bearer-authenticated and always operate
on the token subject; clients cannot supply another `user_id`.

The complete R2A field set is `age`, `height_cm`, `weight_kg` (current profile
state only), `activity_level`, `nutrition_goal`, `dietary_restrictions`, and
`allergies`. No other onboarding, sensitive-health, consent, history, or AI
permission field is accepted in R2A.

`PUT` is a full replacement: an omitted or `null` scalar/label-list value is
stored and returned as `null`/unknown. It does not mean false, no, unrestricted,
or no allergies. An explicit `[]` is the deliberate empty value for either
label list. Existing physical sanity validation applies to age, height, and
weight; label lists contain at most 20 normalized labels of at most 100
characters. Unsupported fields are rejected with `422`.

R2A does not add consent runtime, sensitive health/lifestyle fields,
recommendation logic, weight/goal history, or additional AI Coach context.

## Progress and targets

### V2 additive nutrition fields

`FoodResponse.nutrition_per_100g`, `PortionCalculationResponse.nutrition`, and
the `calculated` meal-analysis nutrition contain the existing five fields plus
nullable V2 fields: `saturated_fat_g`, `sugars_g`, `sodium_mg`,
`cholesterol_mg`, `omega_3_g`, `omega_6_g`, `calcium_mg`, `potassium_mg`,
`zinc_mg`, `iron_mg`, `magnesium_mg`, `vitamin_a_mcg_rae`,
`vitamin_b12_mcg`, `vitamin_c_mg`, `vitamin_d_mcg`, and `folate_mcg_dfe`.
Units are kcal for calories; grams for macros and omega fats; milligrams for
sodium, cholesterol, minerals, and vitamin C; and micrograms for vitamin A
(RAE), B12, D, and folate (DFE). `fat_g` is the backward-compatible public name
for total fat.

`null` is not zero: it means the authoritative source did not provide a value.
An explicit decimal zero is a known zero. The backend performs authoritative
Decimal calculation; React Native/Expo—the future official companion client—and
other clients must not calculate or replace nutrient values locally.

Food `source.category` is nullable for legacy records and otherwise one of
`canteen_recipe`, `local_database`, `USDA`, or `AI_estimate`. The latter is
provenance only and is distinguishable from verified database data. Automatic
priority among competing sources is not yet available because one canonical
Food record exists per normalized name; FoodReference/Recipe modeling is later
work.

`POST /api/meals` and `GET /api/meals/{meal_id}` expose immutable V2 item
snapshots and `additional_totals`. Each `additional_totals` nutrient is numeric
only if every item has a known snapshot; otherwise it is `null`, never a partial
sum. `GET /api/meals` stays compact and exposes its legacy five-nutrient item
shape. Existing progress and target-status APIs remain five-nutrient contracts;
V2 target meanings are not defined yet, so clients must not infer targets for
the new fields.

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

The web companion follows a different same-origin development model: the browser opens `http://<server-lan-ip>:5173`, requests `/api/...`, and Vite proxies `/api` to FastAPI at `127.0.0.1:8000` on the same PC. No LAN IP is compiled into the web application and Vite proxies no unrelated paths.

For a physical non-browser client, start the native API with `scripts\start.ps1` (default `0.0.0.0:8000`) and configure that client with the computer's actual LAN address through its private deployment settings. `127.0.0.1` works only on the development computer. Allow inbound TCP on the selected port through Windows Firewall manually on Private networks. Do not hard-code a LAN address into a client or backend.
