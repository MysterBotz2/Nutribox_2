# Nutri-Box V2 Requirements Traceability Matrix

## Baseline and source hierarchy

This R0 baseline is analysis only. Client-provided sources take precedence over the current implementation. The supplied source set was inspected outside the repository: **Nutri-Box V2 Development Roadmap.pdf**, **Nutri-Box Flowchart App.png**, **Nutri-Box Flowchart Device.png**, **Flowchart 4C.png** (Settings), **Flowchart 5.png** (Diagnostics), and **Nutri-Box Flowchart FINAL.png** (combined flow). The three full/combined charts duplicate and connect the focused flows. The roadmap PDF is recorded by title because the local PDF reader did not complete text extraction; its requirements are traced only where corroborated by the client flowcharts or explicitly stated in the R0 brief. No requirement was invented to fill an unreadable roadmap section.

**Surfaces:** Shared Backend (B), Companion Mobile (M), Raspberry Pi Device (P), Reference Web (W). “DB/API” state likely impact, not an approved design. Current implementation references actual repository code as of Alembic head `a13f00d4a1a3`.

| ID | Client source / location | Requirement statement | Primary | B / DB / API impact | Current mapping | Status | Risk | Clarification / notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AUTH-001 | App: Account creation/login | Register and authenticate an account. | B/M | Existing / existing / existing | JWT email/password registration and token routes; protected ownership. | IMPLEMENTED | MEDIUM | Mobile secure-token handling is a mobile concern. |
| AUTH-002 | App: Email/Social Media Login | Support email and social-media login. | M | API extension likely | Email/password exists; no social identity provider. | PARTIALLY_IMPLEMENTED | HIGH | Which social providers and account-linking rules? |
| AUTH-003 | App: Guest Account | Support a guest account. | M | New identity/session rules | No guest identity. | MISSING | HIGH | Must specify persistence, conversion, and device sync. |
| AUTH-004 | Settings: Account Security | Change password, login activity/devices, and 2FA. | B/M | New models/APIs | JWT login only. | MISSING | HIGH | 2FA method and retention/security policy needed. |
| PROF-001 | App: Survey/Questionnaire | Collect basic age, height, weight, sex, ethnicity, location, activity, and goal data. | M | Profile extension / migration / API | Age, height, weight, activity, nutrition goal exist; no sex, ethnicity, location. | PARTIALLY_IMPLEMENTED | HIGH | DOB vs age and required-field policy unresolved. |
| PROF-002 | App: Dietary Restrictions | Store allergies, lifestyle diets, and dietary restrictions. | B/M | Extend controlled values | Free-text allergies/restrictions exist; no lifestyle-diet taxonomy. | PARTIALLY_IMPLEMENTED | HIGH | Allergies must not be inferred; clinical use requires review. |
| PROF-003 | App: Medical Needs, pregnancy, drinking/smoking | Capture medical conditions, pregnancy/postpartum, alcohol and smoking history. | B/M | Sensitive-data models / migration / APIs | Not stored. | MISSING | CRITICAL | See DEC-PROF-001; purpose, consent, use, retention, and validated rules required. |
| PROF-004 | App: Medical Matrix | Capture body type, blood type, and budget allotment. | M | Profile extension likely | Not stored. | MISSING | HIGH | Clinical/personalization value is unspecified. |
| PROF-005 | Settings: Profile | Manage username, email, phone, sex, location, DOB, picture, units. | M | User/profile extension | Email and name exist; no username, phone, DOB, photo, units. | PARTIALLY_IMPLEMENTED | MEDIUM | Decide identity vs profile ownership and image storage/privacy. |
| PROF-006 | Roadmap / App: Terms and data privacy | Present terms of service and data-privacy clause before onboarding. | M | Consent/audit likely | No consent records. | MISSING | HIGH | Legal text/version and consent evidence required. |
| HOME-001 | App: Home Tab / Overall Goal Status | Show current intake, macro/micronutrient goal status, and description. | B/M | Extend nutrients/API | Progress and target comparison expose calories/protein/carbs/fat/fiber only. | PARTIALLY_IMPLEMENTED | HIGH | Extended nutrient scope unresolved. |
| HOME-002 | App: Home Tab / Meal Schedule | Show scheduled meals by day and breakfast/lunch/dinner status. | B/M | New schedule domain / migration / APIs | Logged meals exist; no expected meal schedule or slots. | MISSING | HIGH | Schedule is prerequisite for authoritative missed-meal metrics. |
| HOME-003 | App: Home Tab / Meal recommendation | Provide meal recommendations. | B/M | Recommendation domain/API | Coach is transient general guidance; no meal recommendation engine. | MISSING | HIGH | Depends on nutrition authority and safety decisions. |
| MEAL-001 | Device: Food analysis; App: meal status | Record user-owned meals with identified foods and measured weight. | B/P | Existing / existing / existing | Meal, MealItem snapshots, analysis and create APIs. | IMPLEMENTED | MEDIUM | Multi-food portions remain deliberately non-invented. |
| MEAL-002 | Device: food profile | Identify ingredients and offer alternative ingredient recommendations. | B/P/M | New ingredient/recommendation contracts | Food recognition returns names; canonical lookup exists; no ingredient or alternative engine. | PARTIALLY_IMPLEMENTED | HIGH | Recognition is not authoritative nutrition. |
| MEAL-003 | App: meal schedule / Diagnostics | Distinguish logged, missed, and scheduled meals. | B/M | New schedule/status data | Only recorded meals exist. | MISSING | HIGH | Requires MEAL-002 scheduling foundation. |
| NUTR-001 | Device: Macronutrients | Provide energy, protein, carbohydrate, total fat, saturated fat, fiber, and sugar. | B/P/M | Food/meal snapshot extension | Current per-100g and snapshots: calories, protein, carbs, fat, fiber. | PARTIALLY_IMPLEMENTED | HIGH | **Explicit roadmap minimum:** add saturated fat, sugars; source/units must be defined. |
| NUTR-002 | Device: Micronutrients | Support sodium, cholesterol, omega-3/6, calcium, potassium, zinc, iron, magnesium, vitamins A/B12/C/D, folate. | B/P/M | Major nutrition model migration/API | Not represented. | MISSING | HIGH | **Flowchart extended nutrient set:** confirm mandatory scope before R1. |
| NUTR-003 | Roadmap / Device: food database | Integrate USDA, local food data, school-canteen recipes, ingredients, portions, allergens, menus. | B | New/extended reference models/imports/APIs | Food, aliases, provenance, verified flag, curated CSV import exist. | PARTIALLY_IMPLEMENTED | HIGH | Recipe/menu/allergen/portion source governance is not defined. |
| NUTR-004 | Roadmap: AI + measured weight nutrition | Estimate nutritional content after AI identifies food and device measures weight. | B/P | Decision-dependent | Current implementation is database-first deterministic calculation. | CONFLICT_WITH_CURRENT_DESIGN | CRITICAL | DEC-NUTR-001 remains open. |
| NUTR-005 | Device: manual ingredient search | Permit manual food/ingredient search. | B/P/M | Existing food search can be reused | `/api/nutrition/search` resolves foods/aliases; no device/mobile UI yet. | PARTIALLY_IMPLEMENTED | MEDIUM | Ingredient-level result semantics need definition. |
| CALC-001 | App: Calculators | Provide Calorie Needs, BMR, TDEE, Macro Split, Water Intake, Portion Size, EER, BMI, Body Fat, Ideal Weight. | B/M | Calculator contracts likely | Portion calculation only; targets intentionally are not auto-derived. | MISSING | CRITICAL | DEC-CALC-001: informational vs target-setting authority. |
| DIAG-001 | Diagnostics: weekly reports | Report intake, macro trends, days over/under target, logging consistency, and weight/progress trend. | B/M | Extend analytics/history | Progress supports intake trends and targets; no weight history, schedules, or meal-type data. | PARTIALLY_IMPLEMENTED | HIGH | “Under target” is not deficiency. |
| DIAG-002 | Diagnostics: all-time usage | Report account activity, total meals, averages, frequent foods, streaks, and goal history. | B/M | New history/queries | Bounded meal/progress data and food snapshots exist; no streak, goal history, sign-up/activity analytics. | PARTIALLY_IMPLEMENTED | MEDIUM | Retention and definition of active day needed. |
| DIAG-003 | Diagnostics: nutritional loss | Report deficiency/excess indicators, condition flags, severity, and recommendations. | B/M | Scientific rules/models/API | Current target comparison is neutral arithmetic only. | NEEDS_CLARIFICATION | CRITICAL | DEC-DIAG-001; no clinical-diagnosis claim. |
| LOSS-001 | Device: Portion Analysis | Re-scan leftovers and produce “Nutritional_Loss.” | P/B | New capture/leftover domain | No leftover capture, matching, or calculation. | NEEDS_CLARIFICATION | CRITICAL | DEC-LOSS-001; current chart wording is not a sufficient formula. |
| AI-001 | Device: food analysis | Recognize food from a captured image through provider-neutral AI. | B/P | Existing abstraction/API; Pi capture adapter later | Mock and Gemini recognition providers; validated image endpoint. | PARTIALLY_IMPLEMENTED | HIGH | Device camera flow and confirmation UX are absent. |
| AI-002 | App: AI Chatbot | Provide nutrition Q&A, personalized assistance, history, organization, and clearing history. | B/M | New conversation models/APIs | Stateless provider-neutral Coach response only; no persistence/history. | PARTIALLY_IMPLEMENTED | HIGH | Medical safety, retention, and provider policy required. |
| AI-003 | App: Chat Preferences | Configure tone, response length, language, check-in frequency, and guidance style. | M/B | Settings/API depending ownership | No Coach preference model. | MISSING | MEDIUM | Separate client-local presentation from account-synced behavior. |
| SET-001 | Settings: Appearance | Manage language, font size, theme, instruction/manual/demo video. | M/P | Mostly client/device local | No persisted settings. | MISSING | MEDIUM | Accessibility settings may be device-specific. |
| SET-002 | Settings: notification settings | Configure sound/vibration and reminders for water, meal logging, goal check-in, streak, allergen/condition, motivation. | M/B/P | Notification preference/event architecture | No notification system. | MISSING | HIGH | Classify local/mobile/backend/device delivery before implementation. |
| SET-003 | Settings: user manual | Contact support, report bug, version/update information, logout. | M/P | Client support/version integration | Logout exists; other items absent. | PARTIALLY_IMPLEMENTED | LOW | Support channel and update distribution not specified. |
| DEV-001 | Device: preparation/operation | Enforce startup checks: battery, meal preparation, component security, compartment placement, power on/off. | P | New device controller/state | Mock reading only. | MISSING | CRITICAL | Hardware specification required. |
| DEV-002 | Device: startup navigation | Offer instructions/demo and start analysis. | P | Device UI only | No Pi UI. | INTENTIONALLY_DEFERRED | MEDIUM | Reference Web is not the Pi UI. |
| DEV-003 | Device: analysis | Capture image, obtain load-cell weight, allow image retake/confirmation, display nutritional content. | P/B | Pi adapters; existing API reusable | Browser scan uses manual weight/image; mock device endpoint. | PARTIALLY_IMPLEMENTED | HIGH | Need pairing/auth and capture transaction design. |
| DEV-004 | Device: current meal/heating | Display temperature and select heater temperature and duration. | P | New hardware command/safety domain | Mock temperature reads only; no heater control. | MISSING | CRITICAL | DEC-DEVICE-001; no safety thresholds invented. |
| DEV-005 | Device: diagnostics | Display food profile, macros/micros, alternatives, weight. | P | Existing meal/nutrition partly reusable | Five nutrient values and food data only. | PARTIALLY_IMPLEMENTED | HIGH | Depends on NUTR-001/002 and recommendation decisions. |
| SYNC-001 | Roadmap: local profile; Device: Sync Application | Synchronize account/profile/settings between mobile, device, and backend. | B/M/P | New pairing/sync contracts | Backend owns profile; LAN API is portable; no device identity/pairing. | CONFLICT_WITH_CURRENT_DESIGN | HIGH | DEC-SYNC-001 and DEC-SYNC-002. |
| SYNC-002 | Roadmap: Wi-Fi/mobile hotspot | Support Nutri-Box-to-mobile connectivity. | P/M/B | Deployment/pairing architecture | LAN-ready FastAPI only. | PARTIALLY_IMPLEMENTED | HIGH | Connectivity mode/offline behavior not specified. |
| DATA-001 | Roadmap: food references | Maintain traceable validated food references and aliases. | B | Existing / existing / existing | Food/FoodAlias, provenance/verified state, atomic CSV ingestion. | IMPLEMENTED | MEDIUM | Extend rather than replace. |
| DATA-002 | Roadmap: recipes/canteen/menu | Manage recipes, ingredients, allergen declarations, portions, and menu schedules. | B/M/P | New models/imports/APIs | No recipe, menu, or allergen-reference entities. | MISSING | HIGH | Ownership and source curation policy required. |
| WREF-001 | R0 scope | Keep React/Vite as reference/integration client, not official mobile deliverable. | W | No parity obligation | Completed 16A–16E web client. | REFERENCE_WEB_ONLY | LOW | Update only to preserve critical shared API integration. |

## Canonical counts

The matrix contains **42 canonical requirements**. Status totals: **IMPLEMENTED 3; PARTIALLY_IMPLEMENTED 17; MISSING 16; INTENTIONALLY_DEFERRED 1; REFERENCE_WEB_ONLY 1; NEEDS_CLARIFICATION 2; CONFLICT_WITH_CURRENT_DESIGN 2.** Surface totals: **Shared 29; Backend-only 2; Mobile-only 6; Raspberry Pi-only 4; Reference Web-only 1.** A “shared” requirement spans two or more official surfaces.

## Nutrition authority and scope

Current numeric nutrition authority is **database-first deterministic**: verified/permitted Food records on a per-100g basis plus measured weight create immutable MealItem snapshots. AI recognition is an input to food resolution only. The V2 roadmap description of AI-estimated nutritional content conflicts with this. **DEC-NUTR-001 is open**; no V2 implementation may silently switch authority.

The current five-nutrient scope is not the V2 scope. The **explicit roadmap minimum** appears to be energy/calories, protein, carbohydrates, total fat, saturated fat, dietary fiber, sugars, and sodium. The **flowchart extended set** includes cholesterol, omega-3/omega-6, calcium, potassium, zinc, iron, magnesium, vitamins A/B12/C/D, and folate. R1 must confirm the exact mandatory data dictionary, units, data sources, completeness semantics, and snapshot migration policy.

## R0.6 client-response reconciliation — August 12, 2026

The original rows above preserve R0 discovery status. The completed questionnaire supersedes ambiguity statuses without changing current implementation truth.

| Requirement(s) | R0.6 requirement status | Client-locked interpretation |
| --- | --- | --- |
| NUTR-001/002 | PARTIALLY_IMPLEMENTED / MISSING | Required: energy/calories, protein, carbohydrates, total fat, saturated fat, dietary fiber, sugars, sodium, cholesterol. Optional when data exists: omega-3/6, calcium, potassium, zinc, iron, magnesium, vitamins A/B12/C/D, folate. |
| NUTR-003/004, MEAL-001/002 | PARTIALLY_IMPLEMENTED | Approved source hierarchy is canteen recipe → local database → USDA → AI fallback. Database/recipe + deterministic scaling is authoritative; AI fallback and component estimates require provenance. |
| DIAG-003 | PARTIALLY_IMPLEMENTED | Non-clinical below/above target and persistent-imbalance indicators only; no clinical diagnosis/severity. |
| LOSS-001 | MISSING | Second image and weighing are required; future consumed nutrition is initial minus leftover nutrition. |
| SYNC-001 | PARTIALLY_IMPLEMENTED | Mobile keeps a secure cache; FastAPI/PostgreSQL is authoritative. |

**Revised canonical counts:** IMPLEMENTED **3**; PARTIALLY_IMPLEMENTED **20**; MISSING **17**; INTENTIONALLY_DEFERRED **1**; REFERENCE_WEB_ONLY **1**; NEEDS_CLARIFICATION **0**; CONFLICT_WITH_CURRENT_DESIGN **0**. A clarified requirement remains missing or partial until runtime work exists.

R0.6 makes the nutrition authority canonical: approved recipe/reference data plus deterministic weight scaling is authoritative; AI identification is an input and AI numerical estimation is a provenance-labelled fallback only when no approved source resolves. `0` requires explicit source support; unknown values remain unavailable/`NULL`.

## R2A-0 profile/onboarding reconciliation

R2A-0 does **not** change runtime status. `PROF-001` and `PROF-002` remain
partially implemented only for the existing narrow `NutritionProfile` fields;
`PROF-003`, `PROF-004`, and `PROF-006` remain missing. The client’s statement
that all fields should influence recommendations is constrained by Q15: some
validated rules exist and other fields are storage only, but no field-level
methodology was supplied. Therefore no new profile field is recommendation-
eligible merely from this requirement.

| Requirement(s) | R2A-0 design outcome | Runtime status remains | Blocking item |
| --- | --- | --- | --- |
| PROF-001, PROF-005 | Field register distinguishes existing account/current-profile fields from proposed identity/personal fields. | PARTIALLY_IMPLEMENTED | Requiredness, terminology, purpose, and ownership decisions. |
| PROF-002 | Allergies/restrictions are safety-relevant declarations, not an allergen-detection or medical guarantee. | PARTIALLY_IMPLEMENTED | Controlled taxonomy and approved filtering/recommendation method. |
| PROF-003, PROF-004 | Health/lifestyle and blood/body-type fields are storage-only candidates with P3/P4 handling. | MISSING | Sensitive consent plus approved field-level methodology. |
| PROF-006 | Consent must be explicit and purpose-specific. | MISSING | Product/legal text, version/audit, retention, and user-rights design (`LEGAL_REVIEW_REQUIRED`). |
| SYNC-001 | Backend authority and mobile secure cache are retained. | PARTIALLY_IMPLEMENTED | Offline mutation/conflict decision DEC-SYNC-003. |

## R2A core-profile contract hardening

Human approval authorizes only the already-existing `age`, `height_cm`,
`weight_kg`, `activity_level`, `nutrition_goal`, `dietary_restrictions`, and
`allergies` fields. R2A introduces no additional field requirement. The
existing profile resource is hardened to preserve null/unknown labels rather
than fabricating default empty arrays; all other onboarding and sensitive-field
requirements remain unresolved, missing, or deferred as recorded above.

## R1 completion status

R1 is complete. NUTR-001 and NUTR-002 now have an additive V2 reference,
calculation, immutable snapshot, and API foundation. NUTR-003 is partially
implemented: provenance categories and conflict-safe local ingestion exist, but
full source priority requires later FoodReference/Recipe modeling. NUTR-004 is
implemented within the R1 scope: approved reference data plus deterministic
Decimal scaling is authoritative; no live AI numerical fallback is used. The
completion evidence and deliberate deferrals are recorded in
[V2_R1_COMPLETION_REPORT.md](V2_R1_COMPLETION_REPORT.md).
