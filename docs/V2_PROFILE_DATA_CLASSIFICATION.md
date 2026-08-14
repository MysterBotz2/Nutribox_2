# V2 Profile Data Classification Register

## Status and reading rule

**Status:** R2A-0 architecture decision record; no persistence or API change is
authorized by this document. P0--P4 are internal engineering sensitivity levels,
not legal classifications. `UNKNOWN`/not supplied is distinct from `false`,
`none`, or an empty declaration.

Sources are abbreviated as: **Q** = completed client questionnaire; **F** =
client roadmap/flowchart requirement as traced in `V2_REQUIREMENTS_TRACEABILITY.md`;
**E** = existing implementation. The questionnaire takes precedence where it
resolves a source conflict. The roadmap/flowchart binaries are not present in
this checkout; their requirements are traceable through the R0 records.

| Field / concept | Source | Domain | Requiredness | Sens. | Backend storage | Mobile cache | AI context | Recommendation use | Validated method | Editable / removable | Historical | Notes / status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Account ID | E, F/AUTH-001 | Account identity | REQUIRED service invariant | P0 | Existing | Not client-owned | AI_BLOCKED | BLOCKED | N/A | No / no | Audit identity only | KEEP; never duplicate in profile. |
| Email | E, F/PROF-005 | Account identity | REQUIRED for current local auth | P0 | Existing `User` | Secure token-account display only; cache policy unresolved | AI_BLOCKED | BLOCKED | N/A | Existing account flow / unresolved removal | Account audit only | KEEP; do not copy to profile. |
| First and last name / display name | E, F/PROF-005 username | Account identity | UNRESOLVED | P1 | Existing names; username design unresolved | Cacheable if needed for UI | AI_BLOCKED | BLOCKED | N/A | Existing names editable only if account policy permits / unresolved | No profile history | EXTEND only after username terminology/ownership decision. |
| Password hash / credentials | E | Account security | REQUIRED system invariant | P0 | Existing auth only | MOBILE-NOT-CACHEABLE | AI_BLOCKED | BLOCKED | N/A | Credential flow only / no profile reset | Security audit only | KEEP outside profile; never expose. |
| Date of birth or age | Q14 context; F/PROF-001, PROF-005; E age | Basic personal | UNRESOLVED (age vs DOB unresolved) | P2 | STORAGE_ALLOWED_IF_CONFIRMED | Cacheable with secure-cache policy | UNRESOLVED | BLOCKED_BY_RESEARCH_METHOD | None supplied | Editable / clearable if optional | Current state; history not required | Do not store both without an approved derivation/retention design. |
| Sex / gender | F/PROF-001, PROF-005 | Basic personal | UNRESOLVED | P2 | STORAGE_ALLOWED_IF_CONFIRMED | Cacheable with secure-cache policy | UNRESOLVED | BLOCKED_BY_RESEARCH_METHOD | None supplied | Editable / clearable if optional | No history | Client terminology and allowed values need confirmation. |
| Ethnicity | F/PROF-001 | Basic personal | UNRESOLVED | P3 | STORAGE_ALLOWED_IF_CONFIRMED | MOBILE-NOT-CACHEABLE pending purpose | AI_BLOCKED_UNTIL_VALIDATED_METHOD | BLOCKED_BY_RESEARCH_METHOD | None supplied | Editable / clearable if optional | No history | Purpose/minimization and methodology are unresolved. |
| Location | F/PROF-001, PROF-005 | Basic personal | UNRESOLVED | P2 | STORAGE_ALLOWED_IF_CONFIRMED | Cacheable only if product purpose confirmed | AI_BLOCKED | BLOCKED | None supplied | Editable / clearable if optional | No history | Granularity and purpose are unresolved; do not infer locale or address. |
| Phone number | F/PROF-005 | Account/contact | UNRESOLVED | P1 | STORAGE_ALLOWED_IF_CONFIRMED | MOBILE-NOT-CACHEABLE pending purpose | AI_BLOCKED | BLOCKED | N/A | Editable / clearable if optional | No history | Contact/verification purpose is not specified. |
| Profile picture | F/PROF-005 | Profile presentation | UNRESOLVED | P2 | STORAGE_ALLOWED_IF_CONFIRMED | MOBILE-NOT-CACHEABLE pending media design | AI_BLOCKED | BLOCKED | N/A | Replaceable / removable | No history | Requires media storage, access, deletion, and image-safety design. |
| Units | F/PROF-005 | Preference | UNRESOLVED | P1 | STORAGE_ALLOWED_IF_CONFIRMED | Cacheable | AI_BLOCKED | UI only | N/A | Editable / resettable | No history | Account-synced vs local/device setting remains DEC-SET-001. |
| Height | Q profile personalization; F/PROF-001; E | Basic personal | UNRESOLVED | P2 | Existing | Cacheable with secure-cache policy | AI_BLOCKED_UNTIL_VALIDATED_METHOD | BLOCKED_BY_RESEARCH_METHOD | No formula approved | Editable / clearable if optional | Current state only | Do not derive/store BMI/BMR/TDEE/EER as authoritative profile fields. |
| Current weight | Q profile personalization; F/PROF-001; E | Basic personal | UNRESOLVED | P2 | Existing current state | Cacheable with secure-cache policy | AI_BLOCKED_UNTIL_VALIDATED_METHOD | BLOCKED_BY_RESEARCH_METHOD | No formula approved | Editable / clearable if optional | **UNRESOLVED**: R3 owns possible history | `NutritionProfile.weight_kg` is current/default only pending DEC-HISTORY-001. |
| Activity level | Q profile personalization; F/PROF-001; E | Activity/lifestyle | UNRESOLVED | P2 | Existing | Cacheable with secure-cache policy | AI_ALLOWED_WITH_USER_OPT_IN | BLOCKED_BY_RESEARCH_METHOD | No approved adjustment rule | Editable / clearable if optional | No history | Existing Coach receives it without profile-consent metadata; R2 must not expand use silently. |
| General nutrition/health goal | Q13; F/PROF-001; E | Nutrition profile | UNRESOLVED | P2 | Existing | Cacheable with secure-cache policy | AI_ALLOWED_WITH_USER_OPT_IN | STORAGE_ONLY | No target-setting method approved | Editable / clearable if optional | Goal history deferred | Separate from `NutritionTarget`; see DEC-GOAL-001 and DEC-TARGET-001. |
| Dietary pattern / lifestyle diet | F/PROF-002 | Nutrition/dietary | UNRESOLVED | P2 | STORAGE_ALLOWED_IF_CONFIRMED | Cacheable with secure-cache policy | AI_ALLOWED_WITH_USER_OPT_IN | STORAGE_ONLY | No controlled taxonomy/rule | Editable / clearable | No history | No invented taxonomy or nutrition rule. |
| Food preferences / disliked foods | F/PROF-002, flowchart | Nutrition/dietary | UNRESOLVED | P2 | STORAGE_ALLOWED_IF_CONFIRMED | Cacheable with secure-cache policy | AI_ALLOWED_WITH_USER_OPT_IN | STORAGE_ONLY | No matching/exclusion method | Editable / clearable | No history | Use only after a future recommendation method is approved. |
| Dietary restrictions | F/PROF-002; E | Nutrition/dietary | UNRESOLVED | P2 | Existing free-text array | Cacheable with secure-cache policy | AI_ALLOWED_WITH_USER_OPT_IN | STORAGE_ONLY | No controlled taxonomy/rule | Existing replace / clearable | No history | Empty list is an explicit clear; omitted future PATCH value must remain unknown/no-change. |
| Allergies | F/PROF-002; E | Safety-relevant dietary | UNRESOLVED | P2 | Existing free-text array | Cacheable only with explicit sensitive-cache choice | AI_ALLOWED_WITH_USER_OPT_IN | BLOCKED pending approved food-filter/exclusion behavior | No safety/allergen reference methodology | Existing replace / clearable | No history | Display/storage may be authorized; no automatic allergen detection or medical guarantee. |
| Medical conditions | Q14--15; F/PROF-003 | Health context | UNRESOLVED | P3 | STORAGE_ALLOWED_IF_CONFIRMED with sensitive consent | MOBILE-NOT-CACHEABLE pending explicit choice | AI_BLOCKED_UNTIL_VALIDATED_METHOD | BLOCKED_BY_RESEARCH_METHOD | Some rules claimed, none supplied/approved | Editable / explicitly clearable | No history unless future research design requires it | User declaration only: no diagnosis, treatment, or disease rule. |
| Pregnancy / postpartum status | Q14--15; F/PROF-003 | Health context | UNRESOLVED | P3 | STORAGE_ALLOWED_IF_CONFIRMED with sensitive consent | MOBILE-NOT-CACHEABLE pending explicit choice | AI_BLOCKED_UNTIL_VALIDATED_METHOD | BLOCKED_BY_RESEARCH_METHOD | None supplied | Editable / explicitly clearable | No history unless approved | Unknown is not “not pregnant”; no pregnancy target logic. |
| Smoking history / status / method | Q14--15; F/PROF-003 | Lifestyle context | UNRESOLVED | P3 | STORAGE_ALLOWED_IF_CONFIRMED with sensitive consent | MOBILE-NOT-CACHEABLE pending explicit choice | AI_BLOCKED_UNTIL_VALIDATED_METHOD | BLOCKED_BY_RESEARCH_METHOD | None supplied | Editable / explicitly clearable | No history | Unknown is not non-smoker; no risk inference. |
| Drinking history / frequency / status | Q14--15; F/PROF-003 | Lifestyle context | UNRESOLVED | P3 | STORAGE_ALLOWED_IF_CONFIRMED with sensitive consent | MOBILE-NOT-CACHEABLE pending explicit choice | AI_BLOCKED_UNTIL_VALIDATED_METHOD | BLOCKED_BY_RESEARCH_METHOD | None supplied | Editable / explicitly clearable | No history | Unknown is not non-drinker; no risk inference. |
| Blood type | Q14--15; F/PROF-004 | Methodology-restricted | UNRESOLVED | P4 | STORAGE_ALLOWED_IF_CONFIRMED with sensitive consent | MOBILE-NOT-CACHEABLE | AI_BLOCKED_UNTIL_VALIDATED_METHOD | BLOCKED_BY_RESEARCH_METHOD | None supplied | Editable / explicitly clearable | No history | Never implement blood-type diet logic. |
| Body type | Q14--15; F/PROF-004 | Methodology-restricted | UNRESOLVED | P4 | STORAGE_ALLOWED_IF_CONFIRMED with sensitive consent | MOBILE-NOT-CACHEABLE | AI_BLOCKED_UNTIL_VALIDATED_METHOD | BLOCKED_BY_RESEARCH_METHOD | None supplied | Editable / explicitly clearable | No history | Never implement body-type nutrition logic. |
| Budget allotment | F/PROF-004 | Personalization context | UNRESOLVED | P2 | STORAGE_ALLOWED_IF_CONFIRMED | MOBILE-NOT-CACHEABLE pending purpose | AI_BLOCKED | BLOCKED | No food-cost/recommendation method | Editable / clearable | No history | Currency, period, and recommendation use are not specified. |
| Consent / preference state and version evidence | F/PROF-006 | Consent/preference | CONDITIONAL on an approved product design | P3 when covering sensitive/AI use | AUTHORIZED_FOR_R2A design only | Cache only if secure and necessary | AI_BLOCKED until relevant opt-in is recorded | Not recommendation input | Product state, not methodology | User changeable / withdrawal required | Consent-event history required if implemented | Legal language/versioning and retention are `LEGAL_REVIEW_REQUIRED`. |
| Derived BMI, BMR, TDEE, EER, calculator outputs | Q13; F/CALC-001 | Derived calculation | OPTIONAL future feature | P2 | Not primary profile storage | Not profile-cache data | AI_BLOCKED | BLOCKED_BY_RESEARCH_METHOD | Formula/population source unresolved | N/A | Future calculator/history policy | Do not store as authoritative profile input or auto-apply to targets. |

## Cross-cutting decisions

## R2A human authorization

The approved R2A implementation set is exactly: `age`, `height_cm`,
`weight_kg`, `activity_level`, `nutrition_goal`, `dietary_restrictions`, and
`allergies`. These existing fields are **AUTHORIZED_FOR_R2A** for core
persistence/API hardening only. This approval does not authorize new fields,
recommendation rules, sensitive-context storage, consent runtime, or AI-context
expansion. Every other register entry retains its existing status.

1. **Storage is not recommendation permission.** `STORAGE_ALLOWED_IF_CONFIRMED`
   means only that an R2A design may consider persisted user declarations with
   the required consent and ownership controls. It does not approve a nutrition,
   medical, or AI rule.
2. **Null/unknown semantics.** Future create/patch contracts must distinguish
   absent/unanswered, explicit `null`/clear where allowed, empty collections,
   and declared values. A blank medical/lifestyle field cannot become a negative
   answer by default.
3. **Deletion/reset.** Sensitive declarations should support an explicit clear
   in a future data model unless a documented research requirement authorizes
   historical retention. Account deletion is out of scope; it must later cover
   profile, health context, meals, chats, and device associations.
4. **Authority.** FastAPI/PostgreSQL is authoritative. React Native/Expo is a
   secure cache/copy, never an independent source of truth.
