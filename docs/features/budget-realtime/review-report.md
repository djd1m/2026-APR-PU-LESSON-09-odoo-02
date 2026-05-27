# Review Report: Budget Real-Time (F05)

**Date:** 2026-05-27
**Reviewer:** brutal-honesty-review
**Phase:** 4 (REVIEW)

---

## Summary

Feature F05 implements expense registration, real-time budget tracking (fact vs plan), deviation alerts, and budget reporting views within the existing `su_project` Odoo module.

---

## Findings

### BLOCKER

None.

### HIGH

| # | Finding | Category | File | Recommendation |
|---|---------|----------|------|----------------|
| H1 | `_check_budget_alert` reads `budget_deviation_pct` which is a stored computed field. After `action_confirm()` writes to expense state, the computed field chain `expense_ids.state -> budget_actual -> budget_deviation -> budget_deviation_pct` must recompute BEFORE `_check_budget_alert` reads the value. In Odoo 17, stored computed fields are recomputed at flush time, which happens before `message_post` writes. However, an explicit `self.flush_recordset()` call before reading `pct` in `_check_budget_alert` would make the ordering guarantee explicit and prevent subtle bugs if Odoo changes flush behavior. | Correctness | `su_project.py:179-194` | Add `project.flush_recordset(['budget_deviation_pct'])` before the threshold check. |
| H2 | `_compute_budget_actual` was changed from summing `estimate_ids` to summing `expense_ids`. Existing projects that have confirmed estimates but no expenses will see `budget_actual` drop to 0 on module upgrade. No data migration script provided. | Migration | `su_project.py:115-121` | Add a `pre_init_hook` or post-upgrade script that creates draft expenses from confirmed estimate totals, or keep estimate-based actual as a separate read-only field. |

### MEDIUM

| # | Finding | Category | File | Recommendation |
|---|---------|----------|------|----------------|
| M1 | Client group (`su_base.group_su_client`) has read access to `su.expense` including `amount`. In the PRD, Ольга (client persona) should see progress and photos, but detailed cost breakdowns may be commercially sensitive. | Security | `ir.model.access.csv` | Review with product owner. Consider removing client access or adding record rules that hide amounts. |
| M2 | Menu item `su_expense_menu` has `parent="su_project_menu"` which makes it a sub-item of the "Объекты" menu action, not a sibling. This means expenses appear nested under the project list, which may confuse users. | UX | `su_budget_views.xml` | Change parent to `su_main_menu` so "Расходы" appears as a top-level menu alongside "Объекты". |
| M3 | No `@api.constrains` on `su.expense.amount` to prevent zero-value expenses. A zero-amount expense is likely data entry error. | Correctness | `su_budget.py` | Add `@api.constrains('amount')` that raises `ValidationError` if `amount == 0`. |
| M4 | `_check_budget_alert` posts a new chatter message on EVERY expense confirmation that keeps the project above threshold. For a project at 15% deviation, confirming 10 small expenses will post 10 identical alerts. | UX | `su_project.py:179-194` | Track last alert time and skip if alert was posted within last hour, or use a boolean `budget_alert_sent` flag that resets when deviation drops below threshold. |

### LOW

| # | Finding | Category | File | Recommendation |
|---|---------|----------|------|----------------|
| L1 | `su.expense` inherits `mail.thread` but the form view only shows `message_ids` (chatter). Consider whether expense-level chatter adds value or is noise. Most discussion should happen at project level. | UX | `su_budget.py`, `su_budget_views.xml` | Acceptable for MVP. May remove `mail.thread` from expense if chatter is unused. |
| L2 | `receipt_attachment` uses `attachment=True` which stores files in Odoo's `ir.attachment` system. No file size limit is enforced. A user could upload a 100MB file. | Security | `su_budget.py` | Odoo's default upload limit applies (configurable via `--limit-memory-hard`). Acceptable for MVP. |
| L3 | Pivot view default filter is `search_default_filter_confirmed` on the action, but pivot shows all states by default in the view definition. This is consistent but worth noting. | UX | `su_budget_views.xml` | No action needed. |
| L4 | `expense_date` defaults to `fields.Date.today` but there is no validation preventing future dates. A user could enter an expense dated next year. | Correctness | `su_budget.py` | Add `@api.constrains('expense_date')` to prevent dates more than 1 day in the future. |

---

## Float Money Check

| Field | Type | Verdict |
|-------|------|---------|
| `su.expense.amount` | `fields.Monetary` | PASS |
| `su.project.budget_planned` | `fields.Monetary` | PASS |
| `su.project.budget_actual` | `fields.Monetary` | PASS |
| `su.project.budget_deviation` | `fields.Monetary` | PASS |
| `su.project.budget_deviation_pct` | `fields.Float(5,2)` | PASS (percentage, not money) |
| `su.project.area_sqm` | `fields.Float` | PASS (area, not money) |
| `su.project.progress` | `fields.Float` | PASS (percentage, not money) |

**Result:** Zero Float fields used for money. All monetary values use `fields.Monetary`.

---

## Dead Code Check

| Item | Status |
|------|--------|
| `estimate_ids` on `su.project` | ALIVE — still used by other features (estimates list, views). Not broken by budget_actual change. |
| `action_view_expenses` | ALIVE — called by stat button in form view. |
| All state transition methods | ALIVE — called by form buttons. |
| `_check_budget_alert` | ALIVE — called from `SuExpense.action_confirm()`. |

**Result:** No dead code detected.

---

## Tenant Isolation Check

| Model | company_id | Required | Default | Record Rules |
|-------|:----------:|:--------:|:-------:|:------------:|
| su.project | Yes | Yes | env.company | Via su_base |
| su.expense | Yes | Yes | env.company | Via su_base (implied by group-based access) |

**Note:** Odoo's built-in multi-company record rules apply. No custom `ir.rule` needed for basic company isolation since access is controlled via `company_id` field + group-based ACLs.

---

## Test Coverage Assessment

| Area | Tests | Coverage |
|------|:-----:|---------|
| Expense CRUD | 1 | Basic create |
| State transitions (valid) | 3 | confirm, cancel, reset_draft |
| State transitions (invalid) | 3 | All invalid transitions raise UserError |
| budget_actual computation | 3 | confirmed-only, excludes cancelled, no expenses |
| budget_deviation | 2 | correct pct, zero-planned |
| Budget alert | 2 | triggered above threshold, not triggered below |
| expense_count | 1 | Count reflects linked expenses |
| Monetary type | 1 | amount is Monetary |
| Company isolation | 1 | Defaults to env.company |
| Negative amount | 1 | Refund scenario |
| **Total** | **18** | Good coverage for MVP |

---

## Verdict

**PASS** -- no blockers found. Two HIGH findings (H1: explicit flush, H2: migration) are recommended fixes before production deployment but do not block merge for development/staging. All money fields correctly use Monetary. Tenant isolation is in place. Test coverage is adequate.

### Recommended Actions Before Merge

1. **H1** (recommended): Add explicit `flush_recordset` in `_check_budget_alert` for robustness
2. **H2** (recommended): Document migration path for existing estimate data
3. **M2** (quick fix): Move expense menu to top-level under СтройУправ
