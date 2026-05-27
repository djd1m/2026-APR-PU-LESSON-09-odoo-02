# Architecture — F02: Dashboard объектов

## 1. Component Overview

This feature enhances the existing `su_project` Odoo module. No new modules are created. All changes are contained within:

```
custom-addons/su_project/
├── models/
│   └── su_project.py          # Enhanced with computed fields + actions
├── views/
│   ├── su_project_views.xml   # Enhanced tree/form/kanban + search view
│   └── su_project_dashboard.xml  # NEW: dashboard action + menu
├── tests/
│   └── test_su_project.py     # NEW: unit tests
├── security/
│   └── ir.model.access.csv    # Unchanged
├── __manifest__.py            # Updated: add new view file + test
└── __init__.py                # Unchanged
```

## 2. Data Model Changes

### New Fields on `su.project`

| Field | Type | Computed | Stored | Dependencies |
|-------|------|----------|--------|-------------|
| `health_status` | Selection(green/yellow/red) | Yes | Yes | budget_deviation_pct, end_date |
| `budget_deviation` | Monetary | Yes | Yes | budget_actual, budget_planned |
| `budget_deviation_pct` | Float | Yes | Yes | budget_actual, budget_planned |
| `task_count` | Integer | Yes | Yes | task_ids |
| `overdue` | Boolean | Yes | Yes | end_date |

### Computation DAG

```
task_ids.progress ──→ progress
estimate_ids.total_amount, estimate_ids.state ──→ budget_actual
budget_actual, budget_planned ──→ budget_deviation, budget_deviation_pct
budget_deviation_pct, end_date ──→ health_status
end_date ──→ overdue
task_ids ──→ task_count
```

All computed fields are **stored** to ensure tree/kanban views load without on-the-fly computation (performance requirement: < 2 sec).

## 3. View Architecture

### View Hierarchy

```
su_project_action (act_window: tree,kanban,form)
├── su_project_view_tree      — Enhanced with health badge + deviation
├── su_project_view_kanban    — Enhanced with health indicator + deadline
├── su_project_view_form      — Enhanced with action buttons + budget tab
└── su_project_view_search    — NEW: filters + group-by

su_project_dashboard_action (act_window: tree,kanban,form)
├── Reuses same views
├── context: search_default_filter_active = 1
└── Menu: СтройУправ → Dashboard
```

### Dashboard Entry Point

Implemented as a separate `ir.actions.act_window` with preset search context, not as a custom QWeb dashboard widget. This approach:
- Uses native Odoo views (no custom JS)
- Leverages stored computed fields for performance
- Supports built-in export, pagination, and search

## 4. Tenant Isolation

- `company_id` field already exists with `required=True` and `default=lambda self: self.env.company`
- Record rules in `su_base` module filter by company_id
- Dashboard action does NOT hardcode domain — relies on record rules
- No raw SQL — all queries via ORM

## 5. Performance Strategy

| Technique | Benefit |
|-----------|---------|
| Stored computed fields | Tree/kanban renders from DB, not Python |
| `@api.depends` with specific field triggers | Recompute only when relevant data changes |
| DB index on `(company_id, state)` | Fast filtered queries for dashboard |
| No `search_count` in loops | Avoid N+1 queries |

## 6. Security Considerations

- State transition buttons restricted by `groups` attribute to manager/admin
- No new endpoints, no API surface increase
- Monetary fields use `fields.Monetary` (Decimal internally), never Float
- No hardcoded values for budget thresholds — defined as class constants for easy configuration
- All views respect existing access rights from `ir.model.access.csv`

## 7. Independent Work Units

| Unit | Scope | Dependencies |
|------|-------|-------------|
| U1 | Model: add computed fields + action methods | None |
| U2 | Views: enhance tree + form + kanban | U1 (fields must exist) |
| U3 | Views: search view + dashboard action | U1 (fields must exist) |
| U4 | Tests: unit tests for computations | U1 |
| U5 | Manifest: update data files | U2, U3 |
