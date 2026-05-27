# Completion Checklist: Budget Real-Time (F05)

## Implementation Checklist

### Models
- [x] `su_budget.py` — SuExpense model with Monetary amount
- [x] `su_project.py` — expense_ids, expense_count, updated _compute_budget_actual
- [x] `su_project.py` — _check_budget_alert method
- [x] `models/__init__.py` — import su_budget

### Views
- [x] `su_budget_views.xml` — tree, form, search, pivot, graph views
- [x] `su_budget_views.xml` — project form inherit (expense tab + stat button)
- [x] `su_budget_views.xml` — menu item and action

### Security
- [x] `ir.model.access.csv` — access rules for all 4 groups

### Manifest
- [x] `__manifest__.py` — add `views/su_budget_views.xml` to data list
- [x] `__manifest__.py` — add `mail` to depends

### Tests
- [x] `test_su_budget.py` — 15 test cases covering all requirements
- [x] `tests/__init__.py` — import test_su_budget

### Documentation
- [x] 01_specification.md
- [x] 02_pseudocode.md
- [x] 03_architecture.md
- [x] 04_refinement.md
- [x] 05_completion.md
- [x] validation-report.md
- [x] review-report.md

## Definition of Done

| Criteria | Status |
|----------|--------|
| All FR-BUD-* requirements implemented | Done |
| All money fields use Monetary type | Done |
| Tenant isolation via company_id | Done |
| Budget alert at >10% deviation | Done |
| Tests cover edge cases | Done |
| No Float for money anywhere | Done |
| Views functional (tree, form, pivot, graph) | Done |
| Security: 4-tier access (foreman/manager/admin/client) | Done |

## Files Created/Modified

| File | Action |
|------|--------|
| `custom-addons/su_project/models/su_budget.py` | Created |
| `custom-addons/su_project/models/__init__.py` | Modified |
| `custom-addons/su_project/models/su_project.py` | Modified |
| `custom-addons/su_project/views/su_budget_views.xml` | Created |
| `custom-addons/su_project/security/ir.model.access.csv` | Modified |
| `custom-addons/su_project/__manifest__.py` | Modified |
| `custom-addons/su_project/tests/test_su_budget.py` | Created |
| `custom-addons/su_project/tests/__init__.py` | Modified |
