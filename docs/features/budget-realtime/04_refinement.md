# Refinement: Budget Real-Time (F05)

## 1. Edge Cases

| # | Scenario | Expected Behavior |
|---|----------|-------------------|
| 1 | budget_planned = 0, expenses exist | deviation_pct = 0.0, no alert, no division by zero |
| 2 | All expenses cancelled | budget_actual = 0.0 |
| 3 | Negative amount (refund) | Allowed — reduces budget_actual |
| 4 | Expense confirmed then cancelled | budget_actual recalculates excluding cancelled |
| 5 | Very large expense (>10M) | Monetary handles up to 15 digits — OK |
| 6 | Concurrent expense confirmations | Odoo ORM serialization — no race condition |
| 7 | Project with no expenses | budget_actual = 0.0, deviation = -100% if planned > 0 |
| 8 | Expense without project | Prevented by required=True on project_id |
| 9 | Alert threshold exactly 10% | Alert triggers (> threshold, not >=) |
| 10 | Multiple rapid confirmations | _check_budget_alert called per confirm, may post multiple messages — acceptable for MVP |

## 2. Security Considerations

| Risk | Mitigation |
|------|------------|
| Foreman creating fake expenses | Foreman has read-only access to su.expense |
| Client viewing sensitive expense data | Client gets read-only, review if expense amounts should be hidden |
| Receipt file upload abuse | Odoo attachment limits apply, no custom upload endpoint |
| Budget alert spam | One message per confirm — acceptable; future: deduplicate by time window |

## 3. Test Strategy

### Unit Tests (test_su_budget.py)

| Test | What it verifies |
|------|-----------------|
| test_expense_create | Basic creation with all required fields |
| test_expense_confirm | State transition draft → confirmed |
| test_expense_cancel | State transition confirmed → cancelled |
| test_expense_reset_draft | State transition cancelled → draft |
| test_expense_invalid_transitions | Errors on invalid state changes |
| test_budget_actual_from_expenses | budget_actual sums confirmed expenses only |
| test_budget_actual_excludes_cancelled | Cancelled expenses not in sum |
| test_budget_deviation_pct_computed | Correct percentage calculation |
| test_budget_deviation_zero_planned | No crash when planned = 0 |
| test_budget_alert_triggered | Alert posted when >10% |
| test_budget_alert_not_triggered | No alert at 10% or below |
| test_expense_count | expense_count reflects linked expenses |
| test_monetary_type | amount field is Monetary, not Float |
| test_company_required | company_id defaults to env.company |
| test_negative_amount_allowed | Refund scenario works |

### Integration Tests (future)

- Export PDF report renders without errors
- Pivot view aggregates correctly by category
- Multi-company: company A cannot see company B expenses

## 4. Migration Notes

- Existing `_compute_budget_actual` computes from `estimate_ids` — we modify it to compute from `expense_ids`
- Old data: if projects have estimates but no expenses, budget_actual will become 0
- Recommendation: keep estimate-based budget_actual as a separate field or migrate confirmed estimate totals to expenses
- For MVP: accept the behavioral change — expenses are the new source of truth

## 5. Future Enhancements

- Budget categories with sub-budgets (planned per category)
- Approval workflow for expenses >threshold amount
- Receipt OCR (AI reads amount from photo)
- Weekly/monthly budget digest email
- Budget forecast based on burn rate
