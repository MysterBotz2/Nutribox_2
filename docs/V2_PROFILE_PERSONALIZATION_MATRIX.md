# V2 Profile Personalization Matrix

This matrix applies the field register to current product behavior. It does not
authorize medical recommendations, calculator targets, or new API fields.

R2A hardens only the existing `age`, `height_cm`, `weight_kg`,
`activity_level`, `nutrition_goal`, `dietary_restrictions`, and `allergies`
fields. R2B1 adds storage-only sensitive declarations; it does not expand any
personalization or AI-context status below.

| Profile field/group | Stored? | UI personalization? | Deterministic nutrition logic? | AI Coach context? | Validated method/source | Current status | Future requirement |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Account identity/contact/credentials | Existing account only | Account display only | No | No | E | ACTIVE / KEEP | Decide username/phone/profile-image ownership separately. |
| Age/DOB, sex/gender, ethnicity, location | Age exists; others not stored | Unresolved | No | No | F/PROF-001, PROF-005; no methodology | UNRESOLVED | Confirm exact fields, terminology, purpose, requiredness, and method. |
| Height and current weight | Existing | Display only | No | No | E; no calculator method | STORAGE_ONLY | DEC-HISTORY-001; calculator methodology before any derived use. |
| Activity level | Existing | Possible non-clinical display | No | Only explicit AI opt-in | E, Q14--15 | OPTIONAL_AI_CONTEXT | Approved task-specific AI purpose and consent state. |
| General nutrition goal | Existing | Display / user-selected context | No auto-targeting | Only explicit AI opt-in | E, Q13 | OPTIONAL_AI_CONTEXT | Separate from target and history; see DEC-GOAL-001/DEC-TARGET-001. |
| Dietary pattern, preferences, restrictions | Restrictions exist; other fields not stored | Display only | No | Only explicit AI opt-in | F/PROF-002 | STORAGE_ONLY / OPTIONAL_AI_CONTEXT | Controlled vocabulary/matching methodology if a future feature needs it. |
| Allergies | Existing declarations | Display only | No automatic detection/filtering | Only explicit AI opt-in | F/PROF-002 | STORAGE_ONLY | Approved allergen-reference, exclusion, warning, and safety policy. |
| Medical conditions | Not stored | No | No | No | Q14--15; methodology absent | BLOCKED_BY_RESEARCH_METHOD | Sensitive consent plus validated, approved rule/reference. |
| Pregnancy/postpartum | Not stored | No | No | No | Q14--15; methodology absent | BLOCKED_BY_RESEARCH_METHOD | Sensitive consent plus validated, approved rule/reference. |
| Smoking/drinking declarations | Not stored | No | No | No | Q14--15; methodology absent | BLOCKED_BY_RESEARCH_METHOD | Sensitive consent plus validated, approved rule/reference. |
| Blood type/body type | Not stored | No | No | No | Q14--15; methodology absent | BLOCKED_BY_RESEARCH_METHOD | Validated research method and express product approval. |
| Budget allotment | Not stored | No | No | No | F/PROF-004; no method | UNRESOLVED | Define currency/period/purpose and food-cost methodology. |
| Derived BMI/BMR/TDEE/EER | Not primary profile data | Future calculator output only | No | No | Q13; DEC-CALC-001 open | BLOCKED_BY_RESEARCH_METHOD | Formula, population, validation, and target-application policy. |

## R2B-0 confirmation

The sensitive rows remain `BLOCKED_BY_RESEARCH_METHOD`; no row is promoted to
storage, AI, or recommendation authorization by R2B-0. See
`V2_R2B_SENSITIVE_FIELD_REGISTER.md` for the field-level AI permission matrix.

All fields are subject to the consent model in
`V2_PROFILE_CONSENT_MODEL.md`. “AI Coach context” means task-minimized data
passed through the existing provider-neutral context object; it does not permit
full-profile forwarding or vendor-specific profile endpoints.
