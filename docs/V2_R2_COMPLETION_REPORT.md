# Nutri-Box V2 R2 Completion Report

## Status

R2 is complete through R2D hardening and closure. The Alembic head is
`7e3f1a2b4c5d` (`add_sensitive_profiles_and_consent`). No R2D migration was
needed: the audit found no schema defect.

## Delivered R2 boundaries

- R2A: bearer-authenticated, owner-only ordinary `NutritionProfile` persistence
  for `age`, `height_cm`, `weight_kg`, `activity_level`, `nutrition_goal`,
  `dietary_restrictions`, `allergies`, and `budget_allotment`.
- R2B1: separately persisted `SensitiveProfileContext` and independent
  `ProfileConsent` states (`not_asked`, `granted`, `declined`, `withdrawn`) for
  sensitive storage, personalization, and AI context.
- R2C: `GET /api/users/me/onboarding-status`, derived at request time with only
  `completed` and `missing_required_fields`.
- R2D: API, OpenAPI, migration, security/privacy, and client-handoff checks.

The three resources remain intentionally separate: ordinary profile data is not
sensitive context, consent is not a declaration, and onboarding is not a stored
completion flag. All routes operate on the bearer-token owner and expose no
arbitrary user selector.

## Consent, onboarding, and privacy

Sensitive-profile writes require `sensitive_storage=granted`. Withdrawing that
purpose clears the active sensitive context. Withdrawing personalization or AI
context does not clear stored declarations. This is product-state behavior, not
a legal/compliance claim.

Required onboarding concepts are medical conditions, smoking history, drinking
history, body build, allergies, medical needs, lifestyle diets, activity level,
budget allotment, and nutrition goal. Pregnancy/postpartum and ethnicity are
optional. `null` is unknown/incomplete; explicit empty label arrays represent a
deliberate none selection where the contract permits it. Sensitive requirements
count only while sensitive storage is granted.

Sensitive values are not included in onboarding status, food, meal, progress,
or public responses. Existing Coach assembly remains limited to ordinary,
non-sensitive profile context; R2 creates no sensitive AI path.

## Migration and compatibility

The additive migration chain preserves the pre-R2 profile contract. The
`f2d8b6a1c943` profile-nullability migration precedes
`7e3f1a2b4c5d`; the latter adds the consent and sensitive-context tables without
fabricating values for existing users. R2D validates the upgrade/downgrade path
on the isolated test database. Existing R1 nutrition APIs remain covered by the
regression suite.

## Mobile integration

FastAPI/PostgreSQL is the system of record. Medical conditions,
pregnancy/postpartum, smoking, drinking, and ethnicity are backend-only and
must not be cached on mobile. Body build, allergies, medical needs, lifestyle
diets, activity level, budget allotment, and nutrition goal are only future
cache-eligible; offline edits and conflicts are not implemented. See
`API_INTEGRATION.md` for the route-level handoff.

`lifestyle_diets` is represented by the existing `dietary_restrictions` field.
This is explicit technical debt retained for compatibility; R2 does not rename
or duplicate the field.

## Deferred work

R2 does not implement blood type, somatotype, BMI, medical logic, diagnosis,
recommendations, sensitive AI context, legal retention/evidence, account
deletion, offline synchronization, or mobile UI. R2B2 is specifically deferred
until task-specific consent, task-minimized provider design, and validated
methodology are separately approved. R3 requires its own scope authorization.
