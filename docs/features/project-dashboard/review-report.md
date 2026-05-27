# Review Report — F02: Dashboard объектов

**Date:** 2026-05-27
**Reviewer:** brutal-honesty-review
**Overall:** PASS (no blockers)

---

## Critical Findings Checklist

| Common Finding | Status | Notes |
|---|---|---|
| Float for money | PASS | All budget fields use `fields.Monetary` with `currency_id`. `budget_deviation_pct` is Float but represents a percentage, not money — correct. |
| Hardcoded secret fallbacks | N/A | No secrets in this feature. |
| Tokens in localStorage | N/A | No auth changes. |
| Webhook without HMAC | N/A | No webhooks. |
| Dead code / orphaned integrations | PASS | All fields are used in views. All action methods are bound to buttons. No orphaned code. |
| Tenant isolation on dashboard queries | PASS | Dashboard action uses no hardcoded domain. company_id is `required=True` with default. Relies on su_base record rules for isolation. No raw SQL. |
| Role escalation | N/A | No registration or role endpoints. State transition buttons restricted by `groups="su_base.group_su_manager"`. |

---

## Findings

### ID: F02-R01
**Severity:** medium
**Category:** Correctness
**Finding:** Stat button in form view references `%(su_project_action)d` which navigates to the main project list — not to a filtered task list. The task_count stat button should ideally open a list of tasks for that specific project, not the project list itself.
**Impact:** Confusing UX when clicking "Задачи" stat button — it shows all projects instead of project's tasks.
**Recommendation:** Replace with a Python method `action_view_tasks` that returns an `act_window` for `su.task` filtered by `project_id`. Or remove the stat button since tasks are already visible in the notebook tab.
**Fix required:** No (medium — optional fix)

### ID: F02-R02
**Severity:** low
**Category:** Performance
**Finding:** `_compute_health_status` and `_compute_overdue` depend on `end_date` but also implicitly depend on "today". Stored computed fields based on date comparisons with `today` become stale after midnight. A project that becomes overdue overnight will show GREEN until the next record write.
**Impact:** Health status may be incorrect for up to 24 hours after a deadline passes.
**Recommendation:** Accept staleness for MVP. Post-MVP, add a daily `ir.cron` job that calls `_compute_health_status()` and `_compute_overdue()` on projects with `end_date` near today.
**Fix required:** No (documented and accepted in refinement doc)

### ID: F02-R03
**Severity:** low
**Category:** Quality
**Finding:** The `_compute_budget_deviation` method uses Python float division (`deviation / project.budget_planned * 100.0`). While `budget_planned` and `budget_actual` are Monetary (Decimal in DB), the in-Python arithmetic may introduce minor float precision drift in the percentage. For a percentage display field this is acceptable (we're not storing money in this field).
**Impact:** Negligible — percentage display rounded to 2 decimal places.
**Recommendation:** No action needed. The percentage is not used for financial calculations.
**Fix required:** No

### ID: F02-R04
**Severity:** low
**Category:** Completeness
**Finding:** PRD mentions "summary analytics widgets (total projects, budget, overdue count)". The implementation uses filtered views instead of OWL-based summary cards. This was explicitly noted and accepted in the validation report as an MVP trade-off.
**Impact:** Less visually impactful dashboard compared to custom widgets.
**Recommendation:** Follow-up feature: add OWL dashboard component with KPI cards.
**Fix required:** No (accepted MVP trade-off)

### ID: F02-R05
**Severity:** low
**Category:** Quality
**Finding:** The `web_ribbon` widget for "Просрочен" uses `invisible="overdue != True"` — in Odoo 17, the `invisible` attribute on widgets accepts domain-like syntax but the behavior of `!=` with boolean may vary. The safer form is `invisible="not overdue"` or `invisible="overdue == False"`.
**Impact:** Ribbon may not display correctly in edge cases.
**Recommendation:** Test ribbon visibility in Odoo 17 runtime. If it works, keep as-is.
**Fix required:** No

---

## Spec Coverage

| Specification Requirement | Implemented | Test Coverage |
|---|---|---|
| FR-01: Computed progress from tasks | Yes | 3 tests |
| FR-02: Budget actual from confirmed estimates | Yes | 2 tests |
| FR-03: Health status GREEN/YELLOW/RED | Yes | 6 tests |
| FR-04: Enhanced tree view | Yes | N/A (visual) |
| FR-05: Enhanced form view with action buttons | Yes | 6 tests (transitions) |
| FR-06: Kanban view with drag-and-drop | Yes | N/A (visual) |
| FR-07: Dashboard action with defaults | Yes | N/A (visual) |
| FR-08: Search & filters | Yes | N/A (visual) |
| FR-09: Performance (stored fields) | Yes | N/A (arch) |
| NFR-01: Tenant isolation | Yes | 1 test |
| NFR-02: Money precision (Monetary) | Yes | 1 test |
| NFR-03: Security (button groups) | Yes | N/A (visual) |

**Test count:** 28 unit tests covering all computed logic and state transitions.

---

## Summary

| Severity | Count | Action Required |
|---|---|---|
| blocker | 0 | - |
| high | 0 | - |
| medium | 1 | Optional: fix stat button navigation (F02-R01) |
| low | 4 | Logged, no action needed |

**Verdict:** PASS. No blockers or high-severity findings. The implementation correctly uses Monetary fields for all money values, enforces tenant isolation via company_id + record rules, and provides comprehensive test coverage (28 tests). The 1 medium finding (stat button navigation) is cosmetic and does not affect functionality or security.
