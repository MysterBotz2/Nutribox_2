# V2 R1 Scope Gate — Nutrition/Data Model Foundation

## Objective and decisions

R1 may establish the approved database/recipe-first nutrition foundation. It depends on resolved DEC-NUTR-001 through DEC-NUTR-005. It must preserve v1 users, Food records, aliases, meals, MealItems, targets, ownership, and known progress behavior.

## Nutrition contract

Mandatory nutrients: energy/calories, protein, carbohydrates, total fat, saturated fat, dietary fiber, sugars, sodium, cholesterol.

Optional when data exists: omega-3, omega-6, calcium, potassium, zinc, iron, magnesium, vitamins A/B12/C/D, folate.

Authority and priority: canteen recipe → local database → USDA → provenance-labelled AI estimate fallback. Deterministic matching and measured/confirmed weight scaling calculate approved values. AI may identify foods/ingredients/local names and estimate components; it must not silently replace approved data. `0` means source-confirmed zero; `NULL`/unavailable means source data is absent.

## Authorized for R1

- Mandatory nutrient expansion and optional nutrient availability strategy.
- Unknown-versus-zero representation and test coverage.
- Source hierarchy, source/provenance, importer contract, deterministic calculation extension.
- AI fallback provenance contract where no approved source resolves.
- Immutable historical snapshot compatibility.
- Expanded target/progress impact assessment and only approved compatibility extensions.
- Recipe-ready reference architecture only where needed for source selection/provenance, not full recipe workflows.

Expected model impact: `Food`, nutrition reference schemas/import contract, calculation schemas/services, and future-compatible MealItem nutrient/provenance snapshots. `NutritionTarget` and progress require an explicit impact assessment before change. User/auth/ownership, FoodAlias resolution, meal identity, and known historical snapshot values remain stable.

## Migration and compatibility invariants

1. Existing users, Foods, aliases, Meals, MealItems, and targets survive.
2. Known five-nutrient historical snapshot values stay unchanged.
3. New historical nutrient values remain `NULL`/unavailable unless a validated migration source supports deterministic values.
4. Reference updates never recalculate historical meals.
5. Known-nutrient progress stays compatible unless a documented V2 extension changes it.
6. Authentication/ownership and Decimal-safe arithmetic remain unchanged.

R1 likely needs Alembic migrations and compatible API/OpenAPI extensions for references, snapshots, and possibly target/progress representations. No breaking replacement occurs without an explicit versioning decision.

## Not authorized for R1

- Personal medical/dietary recommendation logic or unvalidated profile rules.
- BMR/TDEE/EER/BMI/macro/water formulas or automatic target application.
- Meal scheduling, diagnostics, post-scan/leftover runtime algorithms, persistent AI chat, notifications, device pairing, heating control, Raspberry Pi or React Native implementation.
- Full recipe/ingredient/menu management, alternative-food recommendations, social login, 2FA, or linked accounts.

## Exit criteria

1. Approved migration/backward-compatibility plan tested against existing records.
2. Mandatory/optional nutrient, zero/unknown, source hierarchy, provenance, and snapshot tests pass.
3. AI fallback cannot silently override approved data.
4. Importer, API, OpenAPI, and migration documentation are updated.
5. Existing backend/reference-web regressions pass without unauthorized feature work.
