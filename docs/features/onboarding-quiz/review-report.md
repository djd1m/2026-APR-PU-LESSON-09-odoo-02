# Review Report: Onboarding Quiz (F07)

**Reviewer:** brutal-honesty-review
**Date:** 2026-05-27
**Scope:** `custom-addons/su_onboard/` + `docs/features/onboarding-quiz/`

---

## Summary

Solid, minimal Odoo module. Clean separation of model/controller/view.
Good test coverage (13 unit tests covering all matrix combinations, validation,
idempotency, skip flow, company isolation). No blockers found.

---

## Findings

### HIGH Severity

#### H1: Controller uses `.sudo()` without ownership check

**File:** `controllers/onboarding_controller.py`, lines 28, 72, 111
**Description:** All three endpoints use `.sudo()` to search/create `su.onboarding`
records. While the search filters by `partner_id = current_user.partner_id`,
the `.sudo()` bypasses Odoo's record rules entirely. If a future developer
adds more operations on the record (e.g., reading related sensitive data),
the sudo context will carry through silently.
**Risk:** Privilege escalation in future modifications.
**Recommendation:** Remove `.sudo()`. The controller already runs as
`auth='user'`. Grant `create` permission to `group_su_foreman` in
`ir.model.access.csv` so the ORM can create records without sudo.

**Status:** Fixed below.

#### H2: `action_skip()` callable as button without returning action

**File:** `views/su_onboarding_views.xml`, line 12-15; `models/su_onboarding.py`, line 157
**Description:** The form view has `<button name="action_skip" type="object">`.
In Odoo 17, button methods of type `object` must return a dict (action) or
`False`/`None` to close the dialog. Currently `action_skip()` returns `None`
implicitly, which works but is fragile. More importantly, the button is
visible in the backend admin view — an admin could accidentally skip another
user's quiz.
**Risk:** Accidental data modification by admin.
**Recommendation:** Add explicit `return {'type': 'ir.actions.act_window_close'}`
and consider restricting the button to the quiz wizard context only.

**Status:** Fixed below.

### MEDIUM Severity

#### M1: Missing `ir.rule` for record-level security

**File:** `security/ir.model.access.csv`
**Description:** ACL grants foreman read access to ALL `su.onboarding` records,
not just their own. The specification says "foreman: read own records" but
no `ir.rule` enforces this. A foreman could see other users' quiz answers.
**Risk:** Data leakage across users within the same company.
**Recommendation:** Add `security/su_onboarding_rule.xml` with a domain
filter `[('partner_id', '=', user.partner_id.id)]` for foreman/client groups.

**Status:** Fixed below.

#### M2: Unused `PLAN_KEYS` constant

**File:** `models/su_onboarding.py`, line 13
**Description:** `PLAN_KEYS` set is defined but never referenced. Dead code.
**Risk:** Minor clutter.
**Recommendation:** Remove or use in validation.

**Status:** Fixed below.

#### M3: No test for SQL uniqueness constraint

**File:** `tests/test_su_onboarding.py`
**Description:** The SQL constraint `partner_company_uniq` is defined but
never tested. If a future migration breaks it, tests won't catch it.
**Recommendation:** Add a test that attempts to create two records with
the same `(partner_id, company_id)` and asserts `IntegrityError`.

**Status:** Deferred — low risk for MVP.

### LOW Severity

#### L1: Form view shows all 4 steps simultaneously

**File:** `views/su_onboarding_views.xml`
**Description:** The form displays all 4 question groups at once rather than
as a true wizard with step-by-step progression. The specification says
"wizard-style form" but the implementation is a single-page form.
**Risk:** UX — not a true wizard experience. Functional correctness unaffected.
**Recommendation:** For MVP this is acceptable. A true wizard would require
a `TransientModel` (wizard) with state tracking, which adds complexity.
Can be enhanced post-MVP.

#### L2: `current_tools` stored as comma-separated Char

**File:** `models/su_onboarding.py`, line 85
**Description:** Multi-select stored as CSV string. This is documented as a
deliberate trade-off in the validation report. Limits filtering/reporting
capabilities but is adequate for the current read-only analytics use case.
**Risk:** Technical debt if filtering by tool becomes needed.
**Recommendation:** Acceptable for MVP. Document in ADR if refactored later.

---

## Fixes Applied During Review

### Fix H1: Remove `.sudo()`, grant foreman create permission

Updated `ir.model.access.csv` to grant `perm_create=1` to foreman group,
allowing record creation without sudo escalation.

### Fix H2: Explicit return from `action_skip()`

Added `return {'type': 'ir.actions.act_window_close'}` to `action_skip()`.

### Fix M1: Added record rules

Created `security/su_onboarding_rule.xml` with own-record rules for
foreman and client groups.

### Fix M2: Removed unused `PLAN_KEYS`

Removed the dead constant from `su_onboarding.py`.

---

## Checklist

| Item | Status |
|------|:------:|
| No hardcoded secrets | PASS |
| No Float for money | PASS (no money fields) |
| No raw SQL | PASS (ORM only) |
| No localStorage for tokens | N/A (backend module) |
| HMAC webhook verification | N/A (no webhooks) |
| Input validation (server-side) | PASS |
| Company isolation | PASS (after M1 fix) |
| Test coverage | PASS (13 tests) |
| Unused imports | PASS (removed `api` import) |
| Dead code | PASS (removed `PLAN_KEYS`) |

---

## Verdict

**No blockers.** Two HIGH findings fixed in-place. One MEDIUM (M3: constraint test)
deferred to follow-up. Module is ready for merge after fixes applied.
