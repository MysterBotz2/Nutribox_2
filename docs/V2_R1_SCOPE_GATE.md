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

## R1A persistence foundation

R1A adds only the additive persistence foundation. It does not change public
nutrition, meal, target, or progress responses; importer behavior; calculation
behavior; or AI/provider behavior.

`foods` retains the existing required per-100g energy and five-nutrient fields,
then adds nullable per-100g values for saturated fat, sugars, sodium,
cholesterol, omega-3, omega-6, calcium, potassium, zinc, iron, magnesium,
vitamins A/B12/C/D, and folate. Values use `NUMERIC`/`Decimal` rather than
binary floating point. Units are: kcal for calories; grams for protein,
carbohydrates, fats, fiber, sugars, and omega fatty acids; milligrams for
sodium, cholesterol, calcium, potassium, zinc, iron, magnesium, and vitamin C;
and micrograms for vitamin A (RAE), B12, D, and folate (DFE).

`meal_items` adds nullable calculated snapshots for the same V2 nutrients and
nullable source snapshots (`nutrition_source_type`, source name/reference, and
`nutrition_is_estimated`). This preserves the existing immutable meal snapshot
pattern: later reference-data changes cannot rewrite an already stored meal.

The accepted source categories are `canteen_recipe`, `local_database`, `USDA`,
and `AI_estimate`. They record capability/provenance, not a new runtime source
selection service. Legacy rows receive no fabricated values: newly introduced
nutrient and provenance columns remain `NULL` until trustworthy data is
available, while a stored `0` remains an explicit confirmed zero.

The R1A migration is `c4b6e4d10f92` (`expand V2 nutrition persistence`). It is
additive on upgrade and introduces no tables, no backfill, no recalculation, and
no migration-time data import. Its downgrade removes only the R1A columns and
constraints, so it must not be used after intentionally storing R1A-only data
unless that data loss is acceptable.

## R1B calculation and ingestion foundation

R1B extends the internal deterministic calculation path only. The calculator
continues to use `Decimal`, `weight_g / 100`, and final three-decimal
`ROUND_HALF_UP` presentation. All known V2 per-100g nutrients scale by that
same multiplier. An unavailable source value remains `NULL` in the calculated
result and, for future meals, in the immutable `MealItem` snapshot. An explicit
source zero scales to numeric zero. The established public five-nutrient
nutrition/meal/analysis responses are deliberately unchanged; V2 public API,
targets, and progress expansion remain R1C work.

New curated CSV imports now use the V2 header template at
`data/templates/foods_import_template.csv`. Required nutrient columns are
calories, protein, carbohydrates, total fat, fiber, saturated fat, sugars,
sodium, and cholesterol. Optional nutrient columns are omega-3/6, calcium,
potassium, zinc, iron, magnesium, vitamin A (mcg RAE), B12 (mcg), C (mg), D
(mcg), and folate (mcg DFE). A blank optional cell stores `NULL`; an explicit
`0` stores Decimal zero; blank required values, invalid decimals, negative
numbers, `NaN`, and infinity are rejected. Existing database rows remain
compatible and are not revalidated or backfilled by R1B.

Every new CSV row must provide an exact approved `source_type`:
`canteen_recipe`, `local_database`, `USDA`, or `AI_estimate`. The latter is a
provenance-only future capability: R1B makes no network/AI numerical request,
and an imported `AI_estimate` row may not be marked verified. The existing
importer remains insert-only and rejects canonical/alias conflicts. Because
there is one canonical `Food` record per normalized name—not a separate
multi-reference model—R1B does not implement runtime source-priority selection
or automatic overwrite. The approved ordering is documented for later
FoodReference/Recipe work: canteen recipe, then local database, USDA, then AI
estimate.

Future `MealItem` creation snapshots every available calculated V2 nutrient
and its source category/name/reference plus estimated flag. Existing historical
snapshots and the existing five-field `Meal` totals are unchanged. No new
migration is needed: R1A already supplied the required nullable persistence
columns.

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
