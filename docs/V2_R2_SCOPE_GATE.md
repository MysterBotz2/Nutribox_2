# V2 R2 Scope Gate — Profile and Onboarding

## 1. Objective

R2 may establish a consent-aware, backend-authoritative profile/onboarding
foundation without inventing medical, nutrition-target, or AI methodology.

## 2. Source requirements

The completed client questionnaire is primary. Roadmap/flowchart fields are
traced in `V2_REQUIREMENTS_TRACEABILITY.md`; existing runtime behavior is an
implementation baseline, not a source of new requirements.

## 3–7. Domains, classification, requiredness, sensitivity, and unknowns

The canonical register is `V2_PROFILE_DATA_CLASSIFICATION.md`. Specific
onboarding requiredness is **UNRESOLVED** except for current account-auth
invariants. P3/P4 declarations require separate product consent. Absent,
declined, empty, cleared, and declared values must remain distinguishable.

## 8–10. Authority, mobile caching, and consent

FastAPI/PostgreSQL is authoritative; React Native/Expo is a secure local cache.
No offline profile mutation/conflict behavior is authorized until `DEC-SYNC-003`
is resolved. Consent must be explicit and purpose-specific as defined in
`V2_PROFILE_CONSENT_MODEL.md`; legal policy text and retention are
`LEGAL_REVIEW_REQUIRED`.

## 11–13. Personalization and AI boundary

Storage eligibility is not recommendation eligibility. A deterministic rule or
client-approved research methodology is required before a field influences
nutrition recommendations. AI context is task-minimized and needs its own
opt-in. Medical, pregnancy/postpartum, smoking, drinking, blood type, and body
type are blocked from recommendation and AI use pending a validated method.

## 14–16. Expected impacts

R2A is expected to assess/add only approved profile, consent/preference,
repository, authenticated API, OpenAPI, migration, and mobile-contract work.
It must preserve `User`, JWT ownership, existing profile/target behavior,
immutable meals, and backwards-compatible clients. It does not establish final
SQL tables in this gate.

## 17. Backward compatibility

Existing profile fields and endpoints remain supported. A future additive
contract must avoid treating existing missing values as answers, avoid exposing
another user’s data, and avoid automatically transmitting old profile data to
AI providers.

## 18. Out of scope

No recommendation/medical rules; blood/body-type diet; BMR/TDEE/EER; target
semantics; weight/goal history; account deletion; offline sync; React Native or
reference-web UI; chat persistence; diagnostics; notifications; device pairing;
Raspberry Pi; or cloud work.

## 19. Open decisions

DEC-PROF-001 through DEC-PROF-004, DEC-SYNC-003, DEC-HISTORY-001,
DEC-GOAL-001, DEC-TARGET-001, and DEC-SET-001 remain as listed in
`V2_OPEN_DECISIONS.md`.

## 20. R2A authorization gate

**Human-approved R2A field set:** `age`, `height_cm`, `weight_kg`,
`activity_level`, `nutrition_goal`, `dietary_restrictions`, and `allergies`.
This is complete and exclusive. R2A adds no new profile-field requirement;
every other proposed onboarding field remains unresolved or deferred.

| Category | Scope |
| --- | --- |
| AUTHORIZED FOR R2A | Only the seven human-approved fields above, through the existing backend-authoritative profile resource; explicit nullable/clear semantics, ownership, OpenAPI, and regression tests. No consent runtime. |
| AUTHORIZED FOR STORAGE ONLY | User-declared health/lifestyle context only after separate sensitive-consent design is accepted; no rule, automated advice, or AI context. |
| BLOCKED FROM PERSONALIZATION | All medical/lifestyle declarations, allergies as a safety guarantee, blood type, body type, derived calculator values, and any unvalidated profile rule. |
| DEFERRED | Weight/goal history, account deletion, mobile UI/offline sync, target semantics, notifications, device work, chat persistence. |
| UNRESOLVED | Field mandatory status; age vs DOB; sex terminology; image/phone/units ownership; cache list; conflict policy; budget semantics; legal policy. |

## 21. R2 exit criteria

R2 is complete only when approved field/consent decisions are implemented with
authentication and ownership tests, explicit unknown/clear behavior, reviewed
migration/API compatibility, documented mobile contract, and no unauthorized
personalization or AI context. R2A specifically needs a separate human
authorization after this documentation is accepted.
