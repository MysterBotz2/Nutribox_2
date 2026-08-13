# Nutri-Box V2 Domain Impact Map

This is a domain impact assessment, not a final SQL design. “Likely” indicates that client requirements imply a domain boundary; no model or migration is approved by this document.

| Domain | Current model(s) / capability | Reuse | Likely extension or new model | Migration | API | Primary clients |
| --- | --- | --- | --- | --- | --- | --- |
| Identity/Auth | `User`, JWT access token, ownership dependency | KEEP | Password lifecycle, consent, guest/OAuth/2FA only after decisions | Likely | Likely | B/M |
| Profile | `NutritionProfile` | EXTEND | DOB/sex/location/units, controlled diet fields; sensitive context separated | Likely | Likely | B/M/P |
| Health/Dietary Context | allergies/restrictions JSON arrays | REFACTOR | Consent-aware health declarations and usage boundaries | Likely | Likely | B/M |
| Food | `Food`, provenance, verified flag | EXTEND | Extended nutrients, portions, allergens, localized source metadata | Likely | Likely | B/M/P |
| Food Alias | `FoodAlias` | KEEP | May add language/source governance | Possible | Possible | B/M/P |
| Ingredient/Recipe/Menu | none | NEW | Ingredient, recipe version, recipe ingredient, canteen menu/schedule | Likely | Likely | B/M/P |
| Nutrition Reference | five fixed nutrient columns | REFACTOR | Confirmed V2 nutrient dictionary and provenance/completeness strategy | Likely | Likely | B/M/P |
| Meal | `Meal`, `MealItem` immutable snapshots | KEEP | Meal type/slot and capture metadata only if requirements approved | Possible | Likely | B/M/P |
| Meal Schedule | none | NEW | Planned meal, slot, expected intake, completion/missed status | Likely | Likely | B/M |
| Meal Analysis | `MealAnalysisService`, image validation | EXTEND | Device capture transaction, confirmation, multi-food portion workflow | Possible | Likely | B/P/M |
| Portion/Leftover | manual measured portion only | NEW | Leftover scan/measurement/matching after DEC-LOSS-001 | Likely | Likely | B/P |
| Nutrition Target | `NutritionTarget`, source type | KEEP | History/versioning, possibly broader nutrient scope | Likely | Likely | B/M |
| Weight/Goal History | current profile weight and current target only | NEW | Timestamped observations and goal versions | Likely | Likely | B/M |
| Progress/Diagnostics | `ProgressService`, target comparison | EXTEND | Non-clinical reports, streaks, schedule-aware metrics; validated flags only | Possible | Likely | B/M |
| Recommendations | transient Coach result only | NEW | Evidence/provenance-aware suggestions and alternatives | Likely | Likely | B/M/P |
| AI Conversation | provider-neutral stateless Coach | EXTEND | Conversation/thread/message and clear-history semantics | Likely | Likely | B/M |
| AI Preferences | none | NEW | Account-synced coaching behavior vs local rendering preferences | Likely | Likely | B/M |
| Notifications | none | NEW | Preferences, scheduled/event delivery records, consent | Likely | Likely | B/M/P |
| Device | `DeviceService`, `MockDeviceService` reading | EXTEND | Device identity, state/capabilities, safe command boundary | Likely | Likely | B/P |
| Device Pairing/Sync | LAN portability only | NEW | Pairing, association, credentials, status, conflict handling | Likely | Likely | B/M/P |
| Settings | none | NEW | Account preferences and separate client/device-local settings | Possible | Likely | M/P |

## Reuse boundary

Keep existing meal snapshots as historical facts. If V2 extends nutrient scope, the migration plan must state whether historical rows retain known five-nutrient values with unavailable values omitted, or whether a validated backfill source exists. Historical values must never be silently re-estimated from changed Food records.

## R0.6 decision impact

R1 must extend Food/Nutrition Reference and future MealItem snapshots for nine mandatory nutrients, optional nutrient availability, source hierarchy, and richer provenance. Unknown nutrients remain unavailable rather than zero. Recipes are now confirmed as a future domain requiring both composition and final per-serving nutrition; full recipe/ingredient behavior remains R4 work. AI estimate is a fallback data mode, not the numerical authority. Whole meal weight is measured while AI component weights are estimated. Existing snapshots retain their original known values; new historical nutrient values are unavailable unless a validated migration source exists.
