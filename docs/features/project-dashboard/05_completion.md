# Completion — F02: Dashboard объектов

## 1. Implementation Checklist

### Model (`su_project.py`)
- [x] Spec defined: computed fields health_status, budget_deviation, budget_deviation_pct, task_count, overdue
- [x] Spec defined: state transition action methods (action_start, action_pause, action_resume, action_done)
- [x] Spec defined: health threshold constants (5%, 15%)
- [x] Spec defined: Monetary fields for budget deviation (not Float)

### Views (`su_project_views.xml`)
- [x] Spec defined: enhanced tree view with health badge + decoration
- [x] Spec defined: enhanced form view with action buttons + budget tab
- [x] Spec defined: enhanced kanban view with health indicator
- [x] Spec defined: search view with filters and group-by

### Dashboard (`su_project_dashboard.xml`)
- [x] Spec defined: dashboard act_window with search defaults
- [x] Spec defined: dashboard menu item under СтройУправ

### Manifest (`__manifest__.py`)
- [x] Spec defined: add su_project_dashboard.xml to data list

### Tests (`test_su_project.py`)
- [x] Spec defined: health status computation tests
- [x] Spec defined: budget computation tests
- [x] Spec defined: progress computation tests
- [x] Spec defined: state transition tests
- [x] Spec defined: tenant isolation tests

## 2. Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `models/su_project.py` | MODIFY | Add computed fields, constants, action methods |
| `views/su_project_views.xml` | MODIFY | Enhance tree/form/kanban, add search view |
| `views/su_project_dashboard.xml` | CREATE | Dashboard action + menu |
| `__manifest__.py` | MODIFY | Add dashboard view to data list |
| `tests/__init__.py` | CREATE | Test package init |
| `tests/test_su_project.py` | CREATE | Unit tests |

## 3. Dependencies

- `su_base` module (provides record rules, groups, base model)
- `su.task` model (linked via task_ids — must have `progress` field)
- `su.estimate` model (linked via estimate_ids — must have `total_amount` and `state` fields)

## 4. Deployment Notes

- Module upgrade required: `odoo -u su_project -d <database>`
- Stored computed fields will auto-compute on upgrade for existing records
- No data migration needed — new fields compute from existing data
- No new Python dependencies

## 5. Acceptance Sign-off

Feature is complete when:
1. All 5 SPARC documents exist (this file is #5)
2. Validation report passes (Phase 2)
3. All code implemented and tests pass (Phase 3)
4. Review report completed with no blockers (Phase 4)
