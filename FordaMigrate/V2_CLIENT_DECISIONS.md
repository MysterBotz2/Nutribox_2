# Nutri-Box V2 Client Decision Register

**Client response date:** August 12, 2026. **Primary source:** `Nutri-Box_V2_Answers_Technical_Clarification_Questionnaire_Pre-R1_responce.docx`, sections 2–6, supplied by the client/research team. The questionnaire final decision summary controls where it clearly resolves an earlier ambiguous checkbox. This register retains the conflicting answers in its audit notes.

| Decision | Original R0 status | Client response and engineering interpretation | R0.6 status | Affected requirements/domains | DB/API impact | Remaining blocker / audit note |
| --- | --- | --- | --- | --- | --- |
| DEC-NUTR-001 — nutrition authority | OPEN | Approved recipe/reference data is authoritative when available. Deterministic matching plus measured/confirmed weight calculate values. AI identifies food, ingredients and local names; numeric AI estimation is fallback only when no approved reference resolves and must be marked estimated. | RESOLVED | NUTR-003/004, MEAL-001/002; Food, Reference, Meal, Analysis | R1 migration/API extension expected | Q2 selected “AI-estimated value,” but its written clarification says database-and-portion calculation; Q1 and final summary say “Databases + Defined Rules.” Final summary controls. |
| DEC-NUTR-002 — nutrient scope | New | Mandatory: energy/calories, protein, carbohydrates, total fat, saturated fat, dietary fiber, sugars, sodium, cholesterol. Optional when data exists: omega-3, omega-6, calcium, potassium, zinc, iron, magnesium, vitamins A/B12/C/D, folate. | RESOLVED | NUTR-001/002, HOME-001, DEV-005; Food, snapshots, targets, progress | R1 expected | Optional micronutrients are intentionally deprioritized for token/cost efficiency. |
| DEC-NUTR-003 — source priority | New | Use canteen recipe → local database → USDA → AI estimate. Prefer local/recipe-specific data, not most recently verified data. Recipes require composition and final per-serving nutrition. | RESOLVED | NUTR-003/004, DATA-001/002; Food, Recipe, Reference | R1 reference/provenance; R4 full recipe work | Final SQL schema is deferred. |
| DEC-NUTR-004 — unknown vs zero | New | `0` is valid only when the source explicitly reports zero. Source-absent nutrients are `NULL`/unavailable, never fabricated as zero. | RESOLVED | NUTR-001/002, Food, snapshots, import, API | R1 expected | Mandatory integrity invariant. |
| DEC-NUTR-005 — mixed meals, provenance, snapshots | Implicit | Whole load-cell weight is **MEASURED**; AI-derived component weights are **ESTIMATED**. Never equal-split or call estimated components measured. Whole meal is primary, ingredient view optional. Preserve `canteen_recipe`, `local_database`, `USDA`, `AI_estimate` provenance and immutable logged snapshots. | RESOLVED | MEAL-001/002, NUTR-004, LOSS-001 | R1 provenance/snapshot work; R4 workflow | Existing MealItem snapshot behavior is KEEP/EXTEND. |
| DEC-CALC-001 — calculators | OPEN | Calculators may calculate/display estimates automatically and independently, but may not silently overwrite NutritionTargets. Applying an estimate requires explicit action. | PARTIALLY_RESOLVED | CALC-001, Target | Later work | Formula/reference/population methodology remains open; second priority. |
| DEC-PROF-001 — personalization | OPEN | R2 may store accepted fields after privacy design. A field influences recommendations only with approved research rule/methodology; storage alone authorizes no inference. | BLOCKED_BY_RESEARCH_METHOD | PROF-001–006, AI-002 | Later work | Q14 says all fields influence recommendations; Q15 says some are storage only. Does not block R1. |
| DEC-DIAG-001 — deficiency/excess | OPEN | Use below/above target, consistent imbalance, and frequency/duration. Do not diagnose clinical deficiency or severity. | RESOLVED | DIAG-001/003 | Later work | Consultation wording needs later product approval. |
| DEC-LOSS-001 — leftovers | OPEN | Required second image and second weighing. `consumed_nutrition = initial_nutrition - leftover_nutrition`; do not call consumed value `Nutritional_Loss`. | RESOLVED | LOSS-001 | R4/R7 work | Mixed leftover components may be estimated with provenance; no algorithm is approved now. |
| DEC-SYNC-001 — mobile profile authority | OPEN | React Native secure local storage is a cache; FastAPI/PostgreSQL is authoritative and synchronized. | RESOLVED | SYNC-001, Profile | Later work | Offline mutation/conflict semantics remain open. |
| DEC-SYNC-002 — device pairing/sync | OPEN | First-priority/required, but no pairing/security protocol is specified. | PARTIALLY_RESOLVED | SYNC-001/002, Device | Later work | Identity, credentials, association, revocation, offline/conflict rules are open; does not block R1. |
| DEC-DEVICE-001 — heating safety | OPEN | First-priority/required, but product priority is not a hardware safety specification. | BLOCKED_BY_HARDWARE_SPEC | DEV-001/004 | Later work | Heater/power/sensor specs, interlocks, fault/emergency/timeout/startup behavior required. |
| DEC-AUTH-001 | OPEN | Password/2FA/linked accounts are second priority. | DEFERRED | AUTH-002–004 | Later work | Provider, guest conversion and 2FA method open. |
| DEC-NOTIF-001 | OPEN | Notifications are first priority/required. | OPEN | SET-002 | Later work | Delivery, consent, channel, schedule and quiet hours open. |
| DEC-SET-001 | OPEN | Settings ownership was not resolved. | OPEN | SET-001–003, AI-003 | Later work | Account-synced versus client/device-local ownership open. |

## Client MVP priority

**First priority / required:** expanded nutrition/micronutrients; USDA/local/canteen databases; mobile onboarding; meal scheduling; weekly diagnostics; leftover analysis; ingredient identification; AI chatbot/personalization; chat history; notifications; device pairing/sync; Raspberry Pi heating controls.

**Second priority:** nutrition calculators; alternative-food recommendations; password change/2FA/linked accounts.

## DEC-TARGET-001 — V2 nutrient target semantics

**Status:** OPEN / DEFERRED TO DIAGNOSTICS-TARGET DESIGN

**Question:** For each V2 targetable nutrient, does a configured value mean a
goal, minimum, maximum/upper limit, or range? How should remaining amount,
percentage, and status be interpreted for that meaning?

This decision does not block compatible V2 nutrition API exposure. It blocks
generic expansion of `NutritionTarget` and target-status comparison to
saturated fat, sugars, sodium, cholesterol, or optional micronutrients.

The questionnaire leaves pairing/heating checkboxes visually unmarked but labels both “1st priority; required”; the final summary independently confirms heating priority. R0.6 records priority, not technical readiness.
