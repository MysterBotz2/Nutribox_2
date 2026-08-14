# V2 Profile Consent Model

## Status

This is a product and engineering design model, not legal policy or a claim of
compliance. Privacy notice text, terms, lawful basis, retention periods,
jurisdictional requirements, consent evidence, and account-deletion handling
are **LEGAL_REVIEW_REQUIRED** before release.

## Separate product-level purposes

| Consent / state | Purpose | Applies to | Default / withdrawal | Implementation implication |
| --- | --- | --- | --- | --- |
| Account/service processing | Operate authenticated account and requested profile synchronization | Account identity and essential service records | Required to use an account; account closure policy is later | Do not put credentials in a profile table or AI context. |
| Optional profile personalization | Store/use ordinary profile and dietary preference data for approved non-clinical product features | P1/P2 fields | Explicit state; withdrawal stops optional use and permits clearing where supported | Storage and UI presentation are separate from recommendations. |
| Sensitive health/lifestyle declarations | Store voluntary health/lifestyle declarations | P3/P4 fields | Separate explicit opt-in; withdrawal stops use and supports an explicit clear | Do not make ordinary account use depend on optional declarations. |
| AI personalization context | Send the minimum needed approved profile context to an external/provider-neutral Coach task | Only field-level AI-eligible data | Separate explicit opt-in; withdrawal removes profile context from later AI requests | Never forward a whole profile object; a provider receives no DB access or identity. |

## Consent state requirements for a future R2 implementation

- Consent is explicit, purpose-specific, versioned, and never inferred from a
  populated field, registration, or a prior AI request.
- `UNKNOWN`, not yet asked, declined, withdrawn, and granted are distinguishable
  states. Missing data is not a refusal or a negative health/lifestyle answer.
- A consent change affects future use immediately: disable the affected
  personalization/AI assembly path and expose applicable clear/reset actions.
  It does not silently rewrite immutable meal snapshots or past aggregate data.
- Storage withdrawal/erasure behavior, audit evidence, legal wording, retention,
  support access, and provider disclosures require legal/product review.
- Existing `NutritionProfile` fields currently have no profile-consent metadata;
  this document does not retroactively assert consent for them.

## R2B-0 purpose-specific state model

Future sensitive-context implementation must model these independently for
each applicable purpose: sensitive storage, personalization/recommendation use,
and AI-context use.

| State | Meaning | Required behavior |
| --- | --- | --- |
| `NOT_ASKED` | The product has not requested a decision. | Do not collect or use the related optional sensitive declaration. |
| `GRANTED` | The user has explicitly allowed the named purpose. | Permit only the scoped future behavior; it never authorizes medical logic. |
| `DECLINED` | The user chose not to grant the named purpose. | Do not infer a negative health/lifestyle declaration or a deletion choice. |
| `WITHDRAWN` | A previously granted purpose was revoked. | Stop future use immediately; stored-data retention/clear behavior remains unresolved. |

Timestamps and consent-version evidence are product/audit design candidates,
but their retention, wording, and legal significance are `LEGAL_REVIEW_REQUIRED`.
No single `consent = true` flag is sufficient.

## AI-context minimization boundary

Future context assembly must start with the current task and include only
field-level `AI_ALLOWED` or `AI_ALLOWED_WITH_USER_OPT_IN` values. Identity,
credentials, contact details, raw health/lifestyle declarations, measurements,
and methodology-restricted fields are blocked unless a later approved field
classification changes them. Generic LLM reasoning is not a substitute for a
validated nutrition or medical method.

## Withdrawal and edit design questions

`DEC-SYNC-003` remains open for offline writes/conflicts. `DEC-PROF-002` must
settle mandatory onboarding fields. A future R2 API must define whether a clear
is represented by `null`, a dedicated reset operation, or a controlled empty
collection—without treating omitted fields as a clear.
