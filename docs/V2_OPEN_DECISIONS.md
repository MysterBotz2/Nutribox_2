# Nutri-Box V2 Open Decisions and Client Clarifications

These decisions are not approvals to implement. They prevent the V2 roadmap from silently changing safety, scientific, privacy, or synchronization behavior.

| ID | Topic / client requirement | Current behavior | Why open or conflicting | Possible interpretations | Question for client/researchers | Blocks |
| --- | --- | --- | --- | --- | --- | --- |
| DEC-NUTR-001 | Numerical nutrition authority: client material pairs AI identification + measured weight with nutrition estimation and also calls for USDA/local databases. | Food reference + measured weight deterministically calculate and snapshot five nutrients; AI only recognizes food. | These approaches yield different reproducibility, validation, and safety properties. | A database-first; B AI-estimated; C database-first with governed AI fallback; D AI ingredients then database calculation. | Which source is authoritative for every numeric nutrient, when no exact reference exists, and how is provenance disclosed? | R1, R4, diagnostics, research validation. |
| DEC-SYNC-001 | Roadmap says profile information is securely stored locally for personalization. | FastAPI/PostgreSQL is authoritative; web uses session token only. | “Local” could mean cache, offline authority, or a privacy-only mobile design. | Mobile cache + backend authority; local-only; conflict-resolution sync. | Is the mobile app expected to work offline? Which profile fields are cached, encrypted, and authoritative on conflict? | R2, R6, R8. |
| DEC-CALC-001 | Calorie Needs, BMR, TDEE, Macro Split, Water, EER, BMI and related calculators. | Targets are manual/researcher/professional assigned; no formula engine. | Calculator outputs can be informational or improperly become prescriptions. | Informational only; reviewed suggestions; auto-populate editable targets; research protocol only. | Which formulas/populations/sources are approved, and may outputs set a target automatically? | R2, R3, R5. |
| DEC-LOSS-001 | Device flow says re-scan leftovers, subtract from nutritional content, report nutritional loss. | No leftover capture/model. | Weight subtraction alone is invalid for mixed foods and “loss” could mean different concepts. | Unconsumed nutrients; consumed nutrients; cooking degradation; separate waste metric. | Is leftover weight measured again, is a second image required, how are mixed plates and per-food leftovers matched, and what exactly is reported? | R4, R7, R9. |
| DEC-DIAG-001 | Diagnostics names deficiency/excess indicators, condition flags, severity and recommendations. | Neutral intake-versus-configured-target arithmetic only. | Intake below a target is not a clinical nutrient deficiency; condition flags raise clinical risk. | Non-clinical intake indicators; validated research screening; clinician-reviewed feature. | Is any clinical meaning intended? Supply validated methodology, thresholds, evidence, audience, disclaimer, and escalation policy. | R3, R5, R10. |
| DEC-SYNC-002 | Device/mobile Wi-Fi or hotspot synchronization. | LAN API exists; no device identity, pairing, device auth, or sync model. | Connectivity does not specify trust, ownership, offline behavior, or conflict rules. | Device paired to one user; shared household device; QR/pin pairing; backend relay; LAN-only. | Define device identity, pairing UX, user-device association, credentials, revocation, last-seen/status, and offline sync expectations. | R6, R7, R8. |
| DEC-DEVICE-001 | Heater temperature/duration controls and powered device operation. | Mock sensor reading only; no control. | Flowchart presents operational choices but no engineering safety envelope. | UI configuration only; closed-loop controller; manual user confirmation with hard interlocks. | Provide hardware specification, certified limits, sensor fault behavior, cutoff/interlock, timeout, power-loss/startup state, emergency stop, and test protocol. | R7, R9. |
| DEC-PROF-001 | Medical conditions, pregnancy/postpartum, alcohol/smoking history, blood type/body type. | Not stored. | Sensitive data purpose and recommendation use are unspecified. | Optional research questionnaire; profile metadata never used for advice; clinician-mediated data. | For each field: why collect it, mandatory/optional status, consent, retention/deletion, access, and validated decision use. | R2, R5, R10. |
| DEC-AUTH-001 | Social login, guest account, 2FA, login activity/device list. | Local email/password JWT only. | Identity assurance and account conversion rules change security/data ownership. | Email-only; OAuth providers; limited guest account; device-bound guest mode. | Which providers/methods are required and what happens to guest data when an account is created? | R6, R8. |
| DEC-DATA-001 | USDA/local/canteen recipes, ingredients, allergen data, portion sizes, and menus. | Curated single-food CSV with source/verified flag and aliases. | Data source licensing, provenance, recipe ownership, and approval workflow unknown. | Imported curated references; researcher-admin CRUD; recipe versioning; canteen-menu import. | Identify authoritative datasets, licenses, localized foods, curation owner, review cadence, and recipe/menu source format. | R1, R4, R10. |
| DEC-NOTIF-001 | Water, meal, goal, streak, allergen/condition and motivational reminders. | No notification architecture. | Delivery and consent differ across mobile, backend, and device. | Mobile local notifications; backend push; device alerts; hybrid event model. | Which reminder types, channels, schedules, quiet hours, consent defaults, and safety escalation rules are required? | R6, R8. |
| DEC-SET-001 | Language, units, accessibility, theme/font, chat style, and device settings. | No setting model. | Some preferences should synchronize; some must remain device-local. | Account-synced language/units; client-local appearance; device-local accessibility; hybrid. | Confirm ownership/defaults and whether a setting applies to mobile, device, Coach, or all surfaces. | R6, R7, R8. |

## R2A-0 profile, privacy, and consent decisions

| ID | Decision | R2A-0 state | Required resolution before use |
| --- | --- | --- | --- |
| DEC-PROF-001 | Profile recommendation eligibility | **BLOCKED_BY_RESEARCH_METHOD** | Storage never authorizes a rule. Client-approved deterministic/research methodology is required for each field before recommendation use. |
| DEC-PROF-002 | Required versus optional onboarding fields | **OPEN** | Confirm exact mandatory profile fields, age versus DOB, sex/gender terminology, and conditional onboarding rules. |
| DEC-PROF-003 | Sensitive-field consent model | **DESIGN_DEFINED / IMPLEMENTATION_PENDING** | Separate product opt-ins for sensitive declarations; legal text, retention, evidence, and access policy are `LEGAL_REVIEW_REQUIRED`. |
| DEC-PROF-004 | AI profile-context permissions | **DESIGN_DEFINED / IMPLEMENTATION_PENDING** | Task-minimize context and require an explicit AI-context opt-in; do not forward whole profiles or methodology-restricted fields. |
| DEC-SYNC-003 | Profile offline mutation and conflict resolution | **OPEN** | Decide offline edits, queued writes, conflict rule, timestamps, and stale-write handling. Backend authority alone does not answer these. |
| DEC-HISTORY-001 | Current weight versus weight history ownership | **OPEN / DEFERRED TO R3** | R2 owns current/default profile weight only; approve a separate observation/history model before trend/history work. |
| DEC-GOAL-001 | General profile goal versus `NutritionTarget` versus goal history | **OPEN** | Keep the three concepts distinct; target range/min/max semantics remain DEC-TARGET-001. |

**R2A authorization update:** human approval authorizes only the existing
`age`, `height_cm`, `weight_kg`, `activity_level`, `nutrition_goal`,
`dietary_restrictions`, and `allergies` fields for core contract hardening.
This does not resolve the requiredness question in DEC-PROF-002 and does not
authorize any other proposed onboarding field.

The associated field register, consent model, personalization matrix, and
implementation boundary are documented in `V2_PROFILE_DATA_CLASSIFICATION.md`,
`V2_PROFILE_CONSENT_MODEL.md`, `V2_PROFILE_PERSONALIZATION_MATRIX.md`, and
`V2_R2_SCOPE_GATE.md`.

## R2B-0 sensitive-context gate

`DEC-PROF-001` remains **BLOCKED_BY_RESEARCH_METHOD** for recommendation use.
R2B-0 finds no field-specific authorization for sensitive storage, mobile cache,
or AI context. The blocking client questions are in
`V2_R2B_CLIENT_CLARIFICATIONS.md`; the proposed future boundary is recorded in
`V2_R2B_SCOPE_GATE.md`. Consent state, withdrawal, retention, and legal-policy
details remain separate decisions and `LEGAL_REVIEW_REQUIRED` where applicable.

## Immediate priority

**DEC-NUTR-001 is the immediate decision before R1.** It determines the V2 nutrition data model, provenance, snapshot semantics, food-data imports, calculator validity, diagnostics, and research evaluation. DEC-PROF-001 and DEC-DATA-001 should be answered before any sensitive-profile or extended-nutrient migration is proposed.

## R0.6 client-response update — August 12, 2026

This original R0 register is retained as the audit baseline. The client questionnaire updates its statuses as follows: **resolved:** DEC-NUTR-001, DEC-NUTR-002, DEC-NUTR-003, DEC-NUTR-004, DEC-NUTR-005, DEC-DIAG-001, DEC-LOSS-001, DEC-SYNC-001; **partially resolved:** DEC-CALC-001 and DEC-SYNC-002; **blocked:** DEC-PROF-001 by research method and DEC-DEVICE-001 by hardware specification; **deferred:** DEC-AUTH-001; **still open:** DEC-NOTIF-001 and DEC-SET-001.

The current client-controlled decision source is [V2 Client Decisions](V2_CLIENT_DECISIONS.md). R1 is governed by [V2 R1 Scope Gate](V2_R1_SCOPE_GATE.md), not by the earlier “immediate priority” wording above. In particular, DEC-NUTR-001 is now resolved as approved recipe/reference data plus deterministic scaling, with explicit AI-estimate fallback provenance only when no approved source resolves.
