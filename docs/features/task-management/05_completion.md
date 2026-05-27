# F03 Task Management — Completion Checklist

## Implementation Checklist

### Models
- [x] `su.task` inherits `mail.thread`, `mail.activity.mixin`
- [x] `action_start` validates `is_blocked` and `state == 'new'`
- [x] `action_review` validates `state == 'in_progress'`
- [x] `action_done` validates `state == 'review'`, sets `progress = 100`
- [x] `action_cancel` warns about dependents, validates not already done/cancelled
- [x] `action_reopen` from `review` or `done`, resets progress
- [x] `_compute_is_blocked` stored, depends on `dependency_ids.state`
- [x] `_check_circular_dependency` constraint with DFS
- [x] `_compute_progress` aggregates from children (hybrid: manual if no children)
- [x] `subtask_count` computed field
- [x] `write()` override sends notification on `brigade_id` change
- [x] `su.brigade.member_count` computed, stored
- [x] `su.brigade.active_task_count` computed, not stored

### Views
- [x] Form: action buttons with state-based visibility
- [x] Form: subtask stat button with count
- [x] Form: dependency warnings (blocked ribbon)
- [x] Form: subtask inline tree
- [x] Kanban: grouped by state, drag-drop
- [x] Kanban: card with priority, brigade, avatar, deadline, progress
- [x] Kanban: blocked indicator
- [x] Tree: existing, unchanged
- [x] Brigade tree: show member_count, active_task_count
- [x] Brigade form: show computed counts

### Security
- [x] `ir.rule` for foreman: own brigade tasks only
- [x] `ir.rule` for manager: all tasks
- [x] `ir.rule` for client: project-based read-only (future)
- [x] `ir.model.access.csv`: unchanged (already correct)

### Tests
- [x] State transition happy paths
- [x] Blocked task cannot start
- [x] Circular dependency detection
- [x] Subtask progress aggregation
- [x] Cancel with dependents warning
- [x] RBAC foreman isolation
- [x] RBAC manager global access
- [x] Notification on brigade assignment
- [x] Brigade computed fields

### Manifest
- [x] Add `mail` to depends
- [x] Add `security/su_task_rules.xml` to data list

## Deployment Notes

- No data migration needed — all new fields are computed or have defaults.
- `mail.thread` addition requires `mail` module installed (standard Odoo).
- Record rules activate on module upgrade — existing foreman users will
  immediately lose visibility of other brigades' tasks.
- Run `odoo -u su_task` to apply changes.

## Known Limitations (MVP)

1. **No Gantt view** — planned for F09 (P1 feature).
2. **Equal subtask weighting** — no planned_hours-based weighting yet.
3. **No offline kanban** — PWA sync deferred to F06 enhancement.
4. **Client record rule** — placeholder domain, requires `su.project` sharing
   model (not yet implemented).
