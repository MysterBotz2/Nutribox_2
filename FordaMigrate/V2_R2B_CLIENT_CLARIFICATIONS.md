# V2 R2B Client Clarifications

These questions are required before sensitive-profile runtime implementation.
They ask for product/research decisions, not software design.

1. Which of these fields should Nutri-Box actually collect and store: medical
   conditions, pregnancy/postpartum, smoking, drinking, blood type, body type,
   and ethnicity? Please mark each as **collect** or **do not collect**.
2. For every field marked collect, what should a user enter or select? Please
   provide the allowed choices, a reference to the approved questionnaire, or
   confirm that it is free-text.
3. Are any of these fields required for onboarding, or are all optional? If a
   user declines or leaves one unanswered, should the app record that as a
   separate choice from “none”?
4. May a user edit and clear each stored declaration? When they withdraw
   permission, should Nutri-Box retain the value, remove it, or ask the user?
5. Which fields, if any, may the future mobile app cache locally? Are there
   fields that must only be retrieved from the backend when needed?
6. Which fields, if any, may be sent to the AI Coach for a specific task, with
   a separate user opt-in? Please identify the task and the minimum field data.
7. For each field intended to affect a recommendation, provide the approved
   research reference, deterministic rule, population/conditions it applies to,
   and the intended non-clinical output. Without this, Nutri-Box will store no
   sensitive field and will not use it for recommendations.

Privacy notice wording, retention periods, consent evidence, and user-rights
handling require separate `LEGAL_REVIEW_REQUIRED` review.
