# V2 R2B Sensitive-Field Register

## Status

This is an internal R2B-0 authorization register, not a legal classification
or runtime contract. No sensitive field is authorized for persistence in R2B
until the targeted client clarifications are accepted.

| Field / concept | Source | Proposed API name | Data concept | Requiredness | Storage | Mobile cache | Edit / clear | AI context / opt-in | Recommendation / method | Retention/history | Current status / blocking question |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Medical conditions | Q14–15; PROF-003 | `medical_conditions` | Unspecified declaration collection; do not invent taxonomy | UNRESOLVED | UNRESOLVED | MOBILE_CACHE_BLOCKED | UNRESOLVED / UNRESOLVED | AI_BLOCKED / explicit opt-in would be required | BLOCKED_BY_RESEARCH_METHOD; no rule supplied | UNRESOLVED | Confirm permitted values/data shape, storage purpose, clear/retention choice, AI use, and method. |
| Pregnancy / postpartum | Q14–15; PROF-003 | `pregnancy_postpartum_status` | Unspecified status/context; do not infer `not_pregnant` | UNRESOLVED | UNRESOLVED | MOBILE_CACHE_BLOCKED | UNRESOLVED / UNRESOLVED | AI_BLOCKED / explicit opt-in would be required | BLOCKED_BY_RESEARCH_METHOD | UNRESOLVED | Confirm terminology, values, collection purpose, storage, clear/retention, AI use, and method. |
| Smoking status/history | Q14–15; PROF-003 | `smoking_status` / history | Unspecified declaration; no risk scoring | UNRESOLVED | UNRESOLVED | MOBILE_CACHE_BLOCKED | UNRESOLVED / UNRESOLVED | AI_BLOCKED / explicit opt-in would be required | BLOCKED_BY_RESEARCH_METHOD | UNRESOLVED | Confirm data shape, purpose, storage, clear/retention, AI use, and method. |
| Drinking status/history | Q14–15; PROF-003 | `drinking_status` / history | Unspecified declaration; no risk scoring | UNRESOLVED | UNRESOLVED | MOBILE_CACHE_BLOCKED | UNRESOLVED / UNRESOLVED | AI_BLOCKED / explicit opt-in would be required | BLOCKED_BY_RESEARCH_METHOD | UNRESOLVED | Confirm data shape, purpose, storage, clear/retention, AI use, and method. |
| Blood type | Q14–15; PROF-004 | `blood_type` | Unspecified controlled value; no diet logic | UNRESOLVED | UNRESOLVED | MOBILE_CACHE_BLOCKED | UNRESOLVED / UNRESOLVED | AI_BLOCKED_BY_RESEARCH_METHOD / opt-in insufficient | BLOCKED_BY_RESEARCH_METHOD | UNRESOLVED | Confirm whether storage is actually needed; provide a validated method before any use. |
| Body type | Q14–15; PROF-004 | `body_type` | Unspecified controlled value; no diet logic | UNRESOLVED | UNRESOLVED | MOBILE_CACHE_BLOCKED | UNRESOLVED / UNRESOLVED | AI_BLOCKED_BY_RESEARCH_METHOD / opt-in insufficient | BLOCKED_BY_RESEARCH_METHOD | UNRESOLVED | Confirm whether storage is actually needed; provide a validated method before any use. |
| Ethnicity | PROF-001; existing P3 register classification | `ethnicity` | Unspecified self-declared value | UNRESOLVED | UNRESOLVED | MOBILE_CACHE_BLOCKED | UNRESOLVED / UNRESOLVED | AI_BLOCKED | BLOCKED_BY_RESEARCH_METHOD | UNRESOLVED | Confirm collection purpose, terminology, storage, and whether any use is intended. |

## Permission matrix

| Field group | Storage | AI context | Deterministic recommendation |
| --- | --- | --- | --- |
| Medical, pregnancy/postpartum, smoking, drinking, ethnicity | UNRESOLVED | AI_BLOCKED | BLOCKED_BY_RESEARCH_METHOD |
| Blood type, body type | UNRESOLVED | AI_BLOCKED_BY_RESEARCH_METHOD | BLOCKED_BY_RESEARCH_METHOD |

`AI_ALLOWED_WITH_EXPLICIT_OPT_IN` is not currently assigned to a sensitive
field. An opt-in cannot replace the missing field-level purpose and validated
methodology.
