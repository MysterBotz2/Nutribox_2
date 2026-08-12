# Nutri-Box V2 Reuse Inventory

| Component | Classification | Reason |
| --- | --- | --- |
| FastAPI application structure (routers/services/schemas/repos) | KEEP | Clear shared-backend boundaries; extend without a giant application module. |
| SQLAlchemy 2.x, PostgreSQL, Alembic | KEEP | Sound migration foundation for approved V2 domain changes. |
| JWT auth and current-user ownership | EXTEND | Reuse for protected V2 data; add account capabilities only after DEC-AUTH-001. |
| `NutritionProfile` | EXTEND | Conservative current profile is reusable, but sensitive context must not be bolted on casually. |
| `NutritionTarget` | KEEP | Explicit provenance-aware targets avoid unapproved prescriptions; add history only after decisions. |
| `Food` and `FoodAlias` | EXTEND | Reuse canonical resolution/provenance; broaden reference scope in R1. |
| Food CSV ingestion CLI | EXTEND | Strong atomic curated import foundation; add datasets/recipes only with governance. |
| `NutrientCalculator` | KEEP | Deterministic measured-portion calculation is reusable under database-first authority. |
| `Meal` and `MealItem` snapshots | KEEP | Historical stability is required; extend with deliberate V2 snapshot policy. |
| `MealAnalysisService` | EXTEND | Reuse validation/food-resolution flow; improve confirmed multi-food/device captures later. |
| Progress and target-comparison services | EXTEND | Reuse bounded, timezone-aware aggregation; diagnostics need new non-clinical foundations. |
| `FoodRecognitionProvider` and Gemini adapter | KEEP | Provider-neutral recognition preserves vendor independence. |
| `NutritionCoachProvider` and mock providers | EXTEND | Reuse safety/provider boundary; V2 chatbot persistence is a separate domain. |
| `DeviceService` abstraction | REFACTOR | Keep the boundary but evolve from a two-value mock read into tested device capability/state interfaces. |
| OpenAPI generation and integration documentation | KEEP | Essential shared-contract mechanism for mobile/device clients. |
| Native PowerShell setup/start/migrate scripts | KEEP | Portable native deployment support; no Docker dependency required. |
| LAN portability / relative web API design | KEEP | Supports local device/mobile development without embedded addresses. |
| React/Vite Web Companion | DEPRECATE | Freeze as a reference/integration client after 16E; it is not the official companion product and receives selective regression updates only. |
