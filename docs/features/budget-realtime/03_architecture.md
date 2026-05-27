# Architecture: Budget Real-Time (F05)

## 1. Component Overview

```
┌──────────────────────────────────────────────────────┐
│                   su_project module                    │
│                                                        │
│  ┌─────────────┐    ┌──────────────┐                  │
│  │  su.project  │◄───│  su.expense   │ (NEW)           │
│  │  (modified)  │    │              │                  │
│  └─────────────┘    └──────────────┘                  │
│        │                    │                          │
│        │    One2many        │  Many2one                │
│        ├────────────────────┘                          │
│        │                                              │
│  ┌─────────────┐                                      │
│  │  mail.thread │ ← _check_budget_alert               │
│  │  (chatter)   │   posts notification                │
│  └─────────────┘                                      │
└──────────────────────────────────────────────────────┘
```

## 2. Data Flow

```
1. User creates su.expense (draft)
2. User confirms expense → action_confirm()
3. _compute_budget_actual triggers (depends on expense_ids.state)
4. _compute_budget_deviation triggers (depends on budget_actual)
5. _compute_health_status triggers (depends on budget_deviation_pct)
6. _check_budget_alert posts chatter message if pct > 10%
```

## 3. File Structure (changes)

```
custom-addons/su_project/
├── models/
│   ├── __init__.py          # ADD: from . import su_budget
│   ├── su_project.py        # MODIFY: add expense_ids, update _compute_budget_actual
│   └── su_budget.py         # NEW: SuExpense model
├── views/
│   ├── su_project_views.xml # (no changes — budget tab already exists)
│   └── su_budget_views.xml  # NEW: expense views + project form inherit
├── security/
│   └── ir.model.access.csv  # ADD: su.expense access rules
├── tests/
│   ├── __init__.py          # ADD: from . import test_su_budget
│   └── test_su_budget.py    # NEW: expense + budget tests
└── __manifest__.py          # ADD: views/su_budget_views.xml, security
```

## 4. Dependencies

- `su_base` — groups (foreman, manager, admin, client)
- `mail` — mail.thread mixin for chatter alerts (su.project already inherits)
- No new external dependencies

## 5. Tenant Isolation

- `su.expense.company_id` is required, defaults to `self.env.company`
- Odoo record rules on `res.company` enforce multi-company isolation
- All queries go through ORM — no raw SQL

## 6. Performance Considerations

- `_compute_budget_actual` is stored (materialized) — no runtime re-computation
- Depends on `expense_ids.amount` and `expense_ids.state` — recomputes only when expenses change
- For large expense sets (>1000), Odoo ORM handles batching via `mapped()`

## 7. Money Type Discipline

| Field | Type | Why |
|-------|------|-----|
| su.expense.amount | Monetary | Money field — MUST be Monetary, NEVER Float |
| su.project.budget_planned | Monetary | Already correct |
| su.project.budget_actual | Monetary | Already correct |
| su.project.budget_deviation | Monetary | Already correct |
| su.project.budget_deviation_pct | Float(5,2) | Percentage — Float is acceptable for non-money |
