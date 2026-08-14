# V2 R1 Completion Report — Nutrition/Data Model Foundation

## Status

R1 is complete at Alembic head `c4b6e4d10f92`. It establishes a portable,
database-first nutrition reference pipeline without a live external nutrition
or AI numerical service.

## Delivered subphases

| Subphase | Result |
| --- | --- |
| R1A | Additive nullable V2 nutrient and provenance persistence on `Food` and immutable `MealItem` snapshots. |
| R1B | Decimal deterministic V2 calculation, validated V2 CSV ingestion, and future meal snapshot creation. |
| R1C | Additive Food/calculation/analysis/detail API exposure, generated OpenAPI, and compact list compatibility. |
| R1D | Compatibility, OpenAPI, migration, importer, calculator, provenance, snapshot, and reference-client closure audit. |

## Nutrition contract

New V2-complete references require calories, protein, carbohydrates, total fat,
saturated fat, fiber, sugars, sodium, and cholesterol. Optional fields are
omega-3/6, calcium, potassium, zinc, iron, magnesium, vitamins A/B12/C/D, and
folate. Storage and calculation use `Decimal`: calories use kcal; macros and
omega fats use grams; sodium, cholesterol, minerals, and vitamin C use
milligrams; vitamins A (RAE), B12, D, and folate (DFE) use micrograms.

`NULL` means unknown or unavailable. Numeric zero means a source-confirmed
zero. This distinction is preserved by CSV import, calculation, snapshots,
API responses, OpenAPI, and client documentation.

## Provenance and snapshots

Approved categories are `canteen_recipe`, `local_database`, `USDA`, and
`AI_estimate`. API responses expose these as a nullable enum for legacy data.
`AI_estimate` remains estimated provenance; R1 has no numerical AI fallback.
Future meals save immutable calculated nutrient and source snapshots. Reading a
meal never recalculates from the current Food row. Legacy snapshots legitimately
return `null` for V2 values that were not known when recorded.

## Aggregate behavior

The established five Meal totals and all progress/target-status responses remain
five-nutrient contracts. Detailed meal `additional_totals` are derived from
immutable item snapshots and use strict completeness: a nutrient is summed only
when every item has a numeric value; any unknown item produces `null`.

## Compatibility and migration

Existing public five-nutrient fields remain unchanged. V2 API fields are
additive and nullable; `/api/v2` was not introduced. The R1A migration is
additive, has no backfill, and defines a downgrade. V2 CSV ingestion
intentionally requires the expanded format; the pre-R1 format is not accepted.
The importer stays dry-run capable, atomic, insert-only, and conflict-safe.

## Deferred work and R2 readiness

`DEC-TARGET-001` remains open: V2 target values need defined
goal/minimum/maximum/range semantics before targets or comparisons expand.
Progress/diagnostics need that decision plus scheduling, weight history, and
goal-history designs. Automatic source priority requires later FoodReference or
Recipe modeling. No recipe, ingredient, AI numeric fallback, USDA network API,
mobile, Pi, device, or cloud implementation is included in R1.

R2 may be authorized only with its own focused profile/onboarding, privacy, and
consent decisions; it must not silently absorb these R1 deferrals.
