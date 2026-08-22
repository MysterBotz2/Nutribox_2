# V2 R2B Scope Gate — Sensitive Context and Consent

## 1. Objective

R2B may implement a separately bounded sensitive-context and purpose-specific
consent system only after the client clarifications in
`V2_R2B_CLIENT_CLARIFICATIONS.md` are resolved and accepted.

## 2–4. Field authorization and unknown semantics

The exact sensitive-field inventory is in `V2_R2B_SENSITIVE_FIELD_REGISTER.md`.
R2B1 authorizes storage only for medical conditions, pregnancy/postpartum,
smoking, drinking, body build, ethnicity, and medical needs. Blood type is
still unresolved. Absence, decline, explicit none, and an actual declaration
must never collapse into one value.

## 5–6. Consent and withdrawal

Consent must be separate for sensitive storage, personalization use, and AI
context. `NOT_ASKED`, `GRANTED`, `DECLINED`, and `WITHDRAWN` are distinct
product states. Withdrawal must immediately stop the relevant future use, but
whether it retains, clears, or prompts over stored data is unresolved. Legal
wording, evidence, retention, and user-rights handling are
`LEGAL_REVIEW_REQUIRED`.

## 7–10. Authority, cache, AI, and recommendations

FastAPI/PostgreSQL remains authoritative. Sensitive fields are
`MOBILE_CACHE_BLOCKED` until field-level mobile permission is granted. All
sensitive AI context is blocked; all recommendation use is blocked by missing
research methodology. No diagnosis, treatment, disease-specific diet, blood-
type diet, body-type diet, risk score, or pregnancy calculation is permitted.

## 11. Methodology blockers

The client says some profile fields may have validated methods but supplied no
field-level rules. Generic AI reasoning and user consent cannot substitute for
an approved methodology.

## 12–13. Proposed API and database boundaries

If later authorized, use a separate authenticated sensitive-context resource,
not `/api/users/me/profile`, and a dedicated one-to-one sensitive-context table
with a user foreign key/uniqueness invariant. Keep purpose/consent records
separate from declarations. This isolates ordinary profile reads, field-level
AI filtering, and future consent changes without duplicating authentication.

## 14–16. Expected impact and compatibility

R2B would require additive migration(s), protected API/OpenAPI contracts, and
ownership/unknown/clear/consent tests. R2A fields and routes remain compatible;
existing Coach context remains unchanged.

## 17. Authorized runtime scope

R2B1 is authorized only for storage/consent runtime. It must not infer
authorization for AI context, recommendations, legal retention, or R2C work.

## 18. Prohibited scope

No sensitive fields, consent runtime, AI-context expansion, recommendations,
medical logic, mobile storage/UI, history, diagnostics, notifications, devices,
or account-deletion implementation.

## 19. Unresolved decisions

Field selection/data shape, requiredness, storage purpose, edit/clear behavior,
withdrawal behavior, mobile cache, AI task permission, recommendation method,
retention, legal policy, and offline conflict behavior remain open.

## 20. Exit criteria

Before R2B begins, each persisted field must have explicit client approval for
storage, a data shape, requiredness, clear/withdrawal behavior, mobile cache
permission, and AI permission. Any recommendation use additionally needs a
field-level approved methodology. Legal/policy topics require review without
claiming compliance.

## R2B1 completion and R2B2 deferral

R2B1 is complete as a storage-and-consent foundation. It persists only the
approved declaration set behind owner authentication and `sensitive_storage`.
Storage withdrawal clears the active sensitive context; personalization and
AI-context withdrawal preserve it. R2B2 is not authorized: no sensitive field
may be transmitted to an AI provider or used for recommendations until separate
task-minimization, consent, and validated methodology decisions are approved.
