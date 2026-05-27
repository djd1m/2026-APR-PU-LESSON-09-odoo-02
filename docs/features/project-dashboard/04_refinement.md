# Refinement — F02: Dashboard объектов

## 1. Edge Cases

### Budget Computation
- **Zero budget_planned:** When budget_planned == 0, deviation_pct = 0.0, health_status = 'green'. Division by zero must be prevented.
- **No confirmed estimates:** budget_actual = 0.0. All estimates in draft state means no actual budget spent.
- **Negative deviation:** If budget_actual < budget_planned (under budget), deviation_pct is negative — always GREEN.
- **Very large budgets:** Monetary fields handle up to 10^15 (DECIMAL(15,2) in PostgreSQL via Odoo ORM). No overflow concern for construction projects.

### Progress Computation
- **No tasks:** progress = 0.0 (not null, not error)
- **All tasks at 0%:** progress = 0.0
- **Mixed tasks:** Average of all task.progress values (0-100 range per task)
- **Deleted task recompute:** `@api.depends('task_ids.progress')` triggers recompute on task unlink

### Health Status
- **No end_date set:** Cannot be overdue, cannot be near-deadline. Only budget deviation applies.
- **End date today:** NOT overdue (overdue = end_date < today, strict less-than)
- **End date = today + 7:** NOT near-deadline (near = end_date < today + 7, strict less-than). So exactly 7 days out is GREEN (budget permitting).
- **Budget yellow + overdue:** RED takes priority (overdue is RED regardless of budget)
- **Draft projects:** Health status still computed but less relevant (no work started). Could show GREEN by default.

### State Transitions
- **Invalid transitions:** `action_done` from `draft` raises `UserError` — not silently ignored
- **Concurrent state changes:** Odoo ORM handles write locking. No custom concurrency needed.
- **Paused -> Done:** Not allowed directly. Must resume first (paused -> active -> done).

## 2. Performance Refinement

### Stored Fields Trade-off
- **Pro:** List views render from DB read only. Dashboard < 2 sec even with 500+ projects.
- **Con:** Write operations on tasks/estimates trigger recomputation. For 100 tasks per project, recompute is ~10ms — acceptable.
- **Mitigation:** Use `@api.depends` with precise field paths to minimize recompute scope.

### Date-Based Recomputation Challenge
- `health_status` depends on `end_date` and "today". But "today" changes daily.
- **Solution:** Use a daily cron job to force recompute health_status for projects where `end_date` is within the "transition window" (7 days from today).
- **Alternative (simpler, chosen):** Compute `overdue` and health_status as stored but accept 1-day staleness. The cron approach adds complexity. Users can refresh the view.
- **Decision:** Accept 1-day staleness for health_status. Add a note in the UI that colors update on project save or page reload.

## 3. Testing Strategy

### Unit Tests (TransactionCase)
- Budget computation with various estimate states
- Progress computation with 0, 1, N tasks
- Health status: all 3 thresholds + edge cases (zero budget, no end_date)
- State transitions: valid + invalid
- Tenant isolation: cross-company access blocked

### What NOT to test
- View rendering (covered by Odoo's built-in view validation on module install)
- ORM behavior (tested by Odoo framework)
- Record rule enforcement (tested in su_base module)

## 4. Coding Guardrails

| Risk | Mitigation |
|------|-----------|
| Float for money | Use `fields.Monetary` exclusively. Code review check. |
| Division by zero in deviation_pct | Guard: `if budget_planned > 0` |
| Missing company_id | Field is `required=True` with default — cannot be null |
| Raw SQL | Use ORM only. No `self.env.cr.execute()` in this feature |
| Hardcoded thresholds | Define as class constants: `BUDGET_YELLOW_THRESHOLD = 5.0`, `BUDGET_RED_THRESHOLD = 15.0` |
| XSS in project name | Odoo framework escapes by default in QWeb. No manual HTML rendering. |
