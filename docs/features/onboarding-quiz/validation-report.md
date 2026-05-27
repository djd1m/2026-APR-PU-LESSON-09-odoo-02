# Validation Report: Onboarding Quiz (F07)

**Feature:** F07 — Onboarding Quiz
**Validator:** requirements-validator
**Date:** 2026-05-27
**Verdict:** READY

---

## Scoring Summary

| Dimension | Score | Weight | Weighted |
|-----------|:-----:|:------:|:--------:|
| Completeness | 85 | 25% | 21.25 |
| Consistency | 90 | 20% | 18.00 |
| Testability | 90 | 20% | 18.00 |
| Feasibility | 95 | 15% | 14.25 |
| Security | 80 | 20% | 16.00 |
| **Total** | | | **87.50** |

**Verdict: READY** (average 87.5, no blockers)

---

## Dimension Analysis

### Completeness (85/100)

**Strengths:**
- All 4 questions clearly defined with selection values
- Plan recommendation matrix covers all combinations
- Skip flow fully specified
- Data model has all necessary fields with types and constraints

**Gaps (non-blocking):**
- Dashboard personalization logic deferred to F02 (acceptable — documented in 05_completion.md as out of scope)
- Task template pre-filling deferred to F03 (acceptable — same rationale)
- No UX mockups for wizard steps (acceptable for backend-first approach)

### Consistency (90/100)

**Strengths:**
- Naming follows coding-style.md: `su_onboard` module, `SuOnboarding` class, `su.onboarding` model name
- Field naming matches conventions: `snake_case`, `action_` prefix for methods
- Security groups reference existing `su_base` groups
- Plan selection values match `su_billing.PLAN_CONFIG` keys exactly

**Gaps (non-blocking):**
- Pseudocode uses `_compute_recommended_plan` but it is not a true Odoo computed field (no `@api.depends`) — it is a helper method called during submit. Naming is slightly misleading but functional.

### Testability (90/100)

**Strengths:**
- 6 unit tests explicitly defined covering all core logic
- 3 integration tests for API endpoints
- Plan recommendation matrix is deterministic — easy to test exhaustively
- Edge cases documented: partial completion, re-take, multi-tenant, invalid input

**Gaps (non-blocking):**
- No explicit test for concurrent quiz submissions (low risk — upsert pattern handles it)

### Feasibility (95/100)

**Strengths:**
- Simple CRUD model — no external dependencies
- Odoo ORM handles all DB operations
- No AI/ML, no external API calls
- Plan recommendation is a lookup table — O(1)
- Estimated implementation: 2-4 hours

**Gaps:** None identified.

### Security (80/100)

**Strengths:**
- JWT auth required on all endpoints
- Server-side validation of selection values
- Company_id isolation via Odoo multi-company rules
- SQL constraint prevents duplicates
- ORM only — no raw SQL

**Gaps (non-blocking):**
- Controller should validate `current_tools` string length (max 500 chars specified but not in pseudocode constraint) — low risk, adding in implementation
- Rate limiting not specified for quiz endpoints (inherited from global API rate limits — NFR-SEC-06: 100 req/min)

---

## Blockers

None.

---

## Caveats

1. **Dashboard personalization is deferred.** The quiz stores answers but does not rearrange dashboard widgets. This is F02's responsibility. Users will see the recommendation but no immediate visual change beyond the plan suggestion. This is acceptable for MVP.

2. **`current_tools` is stored as comma-separated Char**, not a Many2many. This simplifies the model (no junction table) but limits querying. Acceptable for analytics-only usage — if filtering by tools becomes needed, refactor to Many2many.

---

## Recommendation

Proceed to Phase 3 (IMPLEMENT). All requirements are clear, testable, and feasible. No blockers identified. Caveats are documented and acceptable for MVP scope.
