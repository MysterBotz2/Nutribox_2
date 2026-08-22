# Nutri-Box Development Instructions

## Project
Nutri-Box is an AI-powered mealbox for food recognition,
portion measurement, nutrient analysis, progress tracking,
and personalized nutrition guidance.

## Core Stack
- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Psycopg 3
- Alembic
- OpenAI API
- pytest
- Docker / Docker Compose later
- Flutter later

## Development Environment
The physical Raspberry Pi and sensors are not currently available.

Use mock/simulated hardware during development.

The production system will later run on or communicate with
a Raspberry Pi-based Nutri-Box.

Never write application logic that depends specifically on
the developer's Windows computer.

## Portability
Never hard-code:
- database credentials
- API keys
- absolute paths
- IP addresses
- ports
- usernames
- Raspberry Pi-specific paths

Use environment variables.

The same source code must be portable between development
and client deployment.

## Database
Use PostgreSQL from the beginning.

Do not use SQLite as the primary application database.

Use:
- SQLAlchemy
- Psycopg 3
- Alembic

Database configuration must come from DATABASE_URL.

## AI
Use the OpenAI API.

OpenAI responsibilities:
- identify visible foods
- normalize food names
- provide AI Coach explanations/recommendations

OpenAI must NOT be treated as the authoritative source for
numerical nutrient values.

Nutrition calculations must use verified database values
and deterministic backend calculations.

## Nutrient Calculation
Nutrition records should use a standardized per-100g basis.

portion_multiplier = weight_grams / 100

portion_nutrient =
    nutrient_per_100g * portion_multiplier

Do not invent nutrition values.

## Hardware Architecture
Hardware must be abstracted behind services/adapters.

Development:
MockDeviceService

Future:
RaspberryPiDeviceService

Core business logic must not directly depend on HX711,
DS18B20, Picamera2, or Raspberry Pi GPIO libraries.

## Food Recognition
Initially accept food images through FastAPI/Swagger.

Later replace image upload source with Raspberry Pi camera input.

Never fabricate AI confidence scores.

Users should eventually be able to confirm or correct food recognition.

## Multiple Foods
Never divide the total measured plate weight equally between
detected foods unless there is actual evidence supporting that.

Initially support manual portion weights or individual food scanning.

## Security
Never commit:
- .env
- API keys
- database passwords
- JWT secrets

OpenAI API requests must originate from backend code.

## Architecture
Prefer:
- routers
- services
- schemas
- models
- repositories where justified
- centralized configuration
- clear dependency boundaries

Avoid:
- giant main.py
- giant classes
- business logic in API routers
- duplicated database logic
- premature microservices
- unnecessary abstractions

## Development Workflow
Work incrementally.

Do not implement multiple major phases unless explicitly requested.

For each task:
1. Inspect existing code first.
2. State what will change.
3. Make focused changes.
4. Run relevant tests.
5. Report what was changed.
6. Report tests/results.
7. Do not start the next major phase automatically.

When debugging:
- inspect the actual error
- determine root cause
- make the smallest appropriate fix
- preserve unrelated working code

## Remaining Development Roadmap
15. API Integration Hardening & Native Deployment Readiness
16. Raspberry Pi / Physical Device Integration
17. Full-System Integration, Calibration, Research Validation & Client Handoff

React Native/Expo mobile development remains external to this repository/team. The browser web companion is an explicitly requested FastAPI client; do not implement additional mobile source here unless explicitly requested.

Do not skip major prerequisites unless explicitly instructed.

## V2 re-baseline

R0, R0.6, and R1 are complete. R1 established the V2 nutrition/data-model foundation; its completion report is `docs/V2_R1_COMPLETION_REPORT.md`. R2 requires explicit authorization and its own profile/onboarding, privacy, and consent decisions. Phase 16E remains the frozen Web Reference Client checkpoint and Phase 16F is postponed. Client V2 sources remain primary; the official companion app is future React Native/Expo, the Raspberry Pi UI/controller is separate, and cloud remains only a possible future deployment option.

R2 is complete through R2D hardening and closure. R2A established the
owner-only ordinary profile contract; R2B1 established separately stored,
purpose-specific consent-gated sensitive declarations; and R2C established
derived onboarding metadata only. R2D records migration, API, privacy, and
integration evidence. R2B2 (sensitive AI context or recommendation use) remains
explicitly deferred: it requires separate authorization and approved methodology.
Blood type, somatotype, BMI, offline mutation/sync, and medical or personalized
recommendation behavior remain out of scope. Any R3 work needs its own approved
scope and must not reinterpret R2 storage as authorization for downstream use.
