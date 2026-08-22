# Nutri-Box V2 Refactoring Roadmap

The order below is a controlled hypothesis derived from R0. Each phase begins only after the listed decisions are accepted. The React/Vite client is frozen as a reference/integration client after Phase 16E; it is updated only where useful to preserve or test critical shared APIs.

| Phase | Goal and dependencies | Migrations / APIs | Work by surface | Exit criteria |
| --- | --- | --- | --- | --- |
| R1 — Nutrition/Data Model Foundation | Confirm DEC-NUTR-001 and DEC-DATA-001; define nutrient dictionary, sources, completeness, provenance, historical snapshot policy. | Expected nutrition/food migrations and versioned APIs as needed. | B: reference model/imports/calculation. M/P: none beyond contract review. W: regression only. | Approved data dictionary, provenance policy, migration/backfill strategy, deterministic tests. |
| R2 — Profile & Onboarding Domain | Resolve DEC-PROF-001, DEC-SYNC-001, and consent needs. | Expected profile/consent migrations and APIs. | B: profile/consent boundaries. M: official onboarding UX. P: only minimal synchronized display after decision. | Sensitive-data policy, required/optional fields, authorization and deletion behavior tested. |
| R3 — Planning, History & Diagnostics Foundation | Resolve DEC-CALC-001 and DEC-DIAG-001; establish schedule, weight and goal history. | Expected schedule/history migrations and analytics APIs. | B: non-clinical analytics. M: schedule/history UI. P: read-only contextual display if useful. | No diagnostic claim exceeds validated rules; schedule-aware metrics have definitions/tests. |
| R4 — Ingredients, Recommendations & Portion/Leftover Analysis | Resolve DEC-LOSS-001 and finalize recipe/menu governance. | Expected ingredient/recipe/leftover migrations and APIs. | B: matching/recommendation boundaries. M: manual confirmation. P: capture/leftover workflow simulation. | Mixed-food and leftovers use evidence-based, confirmed semantics; no invented allocation. |
| R5 — AI Chatbot V2 | Resolve medical safety, conversation retention, language and preference policy. | Expected conversation/preference APIs and migrations. | B: provider-neutral conversation service. M: official chat UX. P: optional read-only/accessibility use. | Explicit history/clear semantics, safe provider failures, privacy/retention tests. |
| R6 — Account, Settings, Notifications & Sync | Resolve DEC-AUTH-001, DEC-NOTIF-001, DEC-SET-001, DEC-SYNC-002. | Likely identity/settings/notification/device-pairing APIs and migrations. | B: secure shared contracts. M: notifications/settings/account UX. P: paired-device preferences/status. | Auth/pairing/consent threat review, reliable ownership boundaries, no secret exposure. |
| R7 — Raspberry Pi Device Controller + Simulated UI | Resolve DEC-DEVICE-001 and hardware protocol. | Device state/capability APIs may be needed. | P: controller, simulated adapters/UI, safety state machine. B: device boundary. M: pairing/status only. | Simulated safety/fault tests and documented hardware integration contract; no uncontrolled heater path. |
| R8 — React Native Mobile Application Integration | Depends on stable shared contracts from R1–R6. | No speculative backend redesign; only approved contract additions. | M: official Expo client, secure storage, offline/sync implementation. B: integration support. W: selected regression paths. | End-to-end mobile integration on agreed flows, API compatibility tests. |
| R9 — Real Hardware Integration / Calibration | Depends on R7 and validated hardware specification. | Device telemetry changes only if approved. | P: calibrated sensors, camera, heater interlocks. B/M: integration. | Measured calibration, fault, power-loss, and safety test evidence. |
| R10 — Research Evaluation / Final Hardening | Depends on validated domain behavior and research protocol. | Only evidence-driven changes. | B/M/P: evaluation, privacy/security, performance, deployment/handoff. | Research validation report, regression suite, operational documentation, client acceptance. |

## Explicit non-work before decisions

Do not implement clinical deficiency/condition diagnosis, BMR/TDEE target prescriptions, numeric nutrition AI fallback, leftover subtraction, heater control, device pairing, notification delivery, social login/2FA, chatbot persistence, or React Native/Pi source before their R0 decisions and dependencies are approved.

## R2 controlled subphases

| Subphase | Scope | Entry condition |
| --- | --- | --- |
| R2A — Profile Persistence + Core API | Approved ordinary/dietary fields, ownership, explicit null/clear behavior, and compatible authenticated contracts. | `V2_R2_SCOPE_GATE.md` accepted and field requirements authorized. |
| R2B — Consent / Sensitive Context + AI Context Boundary | Purpose-specific consent metadata and only approved storage-only sensitive declarations; AI assembly gate. | Product/legal review inputs and sensitive-field authorization. |
| R2C — Mobile Onboarding Contract | Stable shared contract for the official React Native client and secure-cache classification. | R2A/B API contract accepted; no offline mutation assumption. |
| R2D — R2 Hardening / Closure | Migration/API/ownership/privacy regression evidence and documentation. | R2A–C scope completed. |

This sequence keeps sensitive storage and AI-context release separate from the
ordinary-profile foundation. Weight/goal history remains R3; no subphase
authorizes medical or unvalidated personalization.

## R2B-0 checkpoint

## R2B1 completion checkpoint

R2B1 implements the authorized sensitive storage and product-consent foundation
after the client follow-up response. It is not R2C: no React Native onboarding,
mobile cache, offline synchronization, or completion-state workflow is added.
Any later R2B2 work must separately approve AI task minimization and validated
non-clinical methodology before these declarations affect output.

R2B-0 is a documentation/decision gate between completed R2A and runtime R2B.
It must resolve field-level storage, cache, AI, recommendation, withdrawal, and
methodology authorization without changing runtime behavior. R2B cannot start
until its targeted client clarifications are accepted.

## R1 completion checkpoint

R1 is complete through R1D. The controlled completion record is
[V2_R1_COMPLETION_REPORT.md](V2_R1_COMPLETION_REPORT.md). R2 remains the next
candidate phase, but requires explicit authorization and the privacy, consent,
and profile-field decisions stated in its roadmap dependency.

## R0.6 priority re-baseline

R1 remains Nutrition/Data Model Foundation and may implement the resolved nutrition foundation in [V2 R1 Scope Gate](V2_R1_SCOPE_GATE.md). R2–R8 retain their dependency ordering, but first-priority scheduling, non-clinical weekly diagnostics, leftovers, ingredient identification, chat/history, notifications, device sync, and heating must be scheduled ahead of second-priority calculators, alternative recommendations, and account-security expansion where dependencies permit. R1 must not absorb full recipe/ingredient functionality, calculators, diagnostics, leftover runtime, chat persistence, notifications, pairing, heating, or mobile/Pi work.
