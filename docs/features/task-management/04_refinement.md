# F03 Task Management — Refinement

## Edge Cases & Error Handling

### EC-01: Circular Dependency Detection
- **Scenario:** Task A depends on B, B depends on C, user adds C depends on A.
- **Handling:** `_check_circular_dependency` traverses the dependency graph
  using iterative DFS. Raises `ValidationError` with message in Russian.
- **Bound:** Max traversal depth = number of tasks in project. For 1K tasks
  worst case is O(1K) — acceptable.

### EC-02: Cancel with Active Dependents
- **Scenario:** Task A (in_progress) depends on Task B. User cancels B.
- **Handling:** `action_cancel` posts a `message_post` warning listing
  affected dependent tasks. Does NOT block the cancel — business decision
  is to allow cancellation but inform.
- **Recomputation:** `is_blocked` on dependents auto-recomputes because
  `cancelled` is in the "done" set for blocking purposes.

### EC-03: Subtask Progress with Cancelled Children
- **Scenario:** Parent has 3 children: 100%, 50%, cancelled.
- **Handling:** Cancelled children are excluded from average calculation.
  Result: (100 + 50) / 2 = 75%.

### EC-04: Reopen Done Task
- **Scenario:** Manager reopens a completed task.
- **Handling:** `action_reopen` moves to `in_progress`, sets progress to 99%
  (not 100% since it's no longer complete). Dependent tasks that were
  unblocked may become blocked again — `_compute_is_blocked` handles this.

### EC-05: Drag-Drop Blocked Task in Kanban
- **Scenario:** User drags blocked task from "new" to "in_progress".
- **Handling:** Server-side `write` override checks: if `state` changes to
  `in_progress` and `is_blocked`, raise `ValidationError`. Client-side
  kanban uses `readonly` attribute for visual indication.

### EC-06: Empty Brigade Assignment
- **Scenario:** Task assigned to brigade with no members.
- **Handling:** No notification sent (empty partner list). No error — valid
  for pre-planning stage.

### EC-07: Concurrent State Transition
- **Scenario:** Two users try to complete the same task simultaneously.
- **Handling:** Odoo's ORM pessimistic locking (`FOR UPDATE` on write)
  ensures one succeeds. Second gets a concurrency error dialog.

## Testing Strategy

### Unit Tests (test_su_task.py)

| Test | Description |
|------|-------------|
| `test_state_new_to_in_progress` | Happy path transition |
| `test_state_blocked_cannot_start` | Blocked task raises error |
| `test_circular_dependency_detection` | A→B→A raises error |
| `test_deep_circular_dependency` | A→B→C→A raises error |
| `test_subtask_progress_aggregation` | Parent = avg of children |
| `test_subtask_progress_excludes_cancelled` | Cancelled children skipped |
| `test_cancel_warns_dependents` | Message posted on cancel |
| `test_action_done_sets_progress_100` | Progress forced to 100 |
| `test_reopen_resets_progress` | Progress set to 99 |
| `test_brigade_member_count` | Computed field accuracy |
| `test_brigade_active_task_count` | Counts only active states |
| `test_foreman_rbac` | Foreman sees only own brigade |
| `test_manager_rbac` | Manager sees all tasks |
| `test_notification_on_assignment` | message_post called on brigade change |

### Integration Considerations
- Tests use `TransactionCase` (Odoo standard) — each test in its own
  transaction, rolled back after.
- RBAC tests use `with_user()` to switch security context.
- No external dependencies — pure ORM tests.

## Performance Optimizations

1. **Batch `_compute_is_blocked`**: Single query with `read_group` for
   dependency states instead of per-record iteration for large recordsets.
   For MVP, per-record loop is acceptable (<1K tasks per project).

2. **Stored `is_blocked`**: Avoids recomputation on every tree/kanban load.
   Trade-off: slight delay on dependency state change propagation (ORM
   handles via `modified` signals).

3. **`active_task_count` NOT stored**: Changes on every task state change.
   Storing would cause excessive recomputation. Computed on demand is
   acceptable for brigade list (typically <50 brigades).
