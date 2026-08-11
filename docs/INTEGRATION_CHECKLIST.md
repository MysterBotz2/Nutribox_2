# Integration Checklist

- [ ] Client base URL is configured, not hard-coded.
- [ ] `GET /api/health` returns `healthy` and `connected`.
- [ ] Registration succeeds.
- [ ] Login succeeds using form field `username` for email.
- [ ] Bearer token is stored in platform-secure storage.
- [ ] `GET /api/users/me` accepts the bearer token.
- [ ] JPEG, PNG, and WEBP upload behavior is handled.
- [ ] Nutrition search and food detail work.
- [ ] A meal can be created from `food_id` and `weight_grams`.
- [ ] Meal history pagination is handled.
- [ ] Progress timezone is sent as an IANA identifier.
- [ ] Weekly chart consumes all seven daily points.
- [ ] Targets and target status work.
- [ ] AI Coach endpoint works with authentication.
- [ ] Expired/invalid token produces a handled `401`.
- [ ] `404`, `409`, `422`, `429`, `502`, `503`, and `504` are handled safely where relevant.
