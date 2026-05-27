# F03 Task Management — Architecture

## Component Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                   Odoo 17 Web Client                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐  │
│  │ Tree View  │  │ Form View  │  │ Kanban View (new)     │  │
│  │ (existing) │  │ (enhanced) │  │ drag-drop by state    │  │
│  └────────────┘  └────────────┘  └────────────────────────┘  │
└──────────────────────┬───────────────────────────────────────┘
                       │  JSON-RPC
┌──────────────────────▼───────────────────────────────────────┐
│                 su_task Odoo Module                           │
│  ┌──────────────────┐  ┌──────────────────────────────────┐  │
│  │ su.task model     │  │ su.brigade model                │  │
│  │ - state machine   │  │ - member_count (computed)       │  │
│  │ - dependency eng  │  │ - active_task_count (computed)  │  │
│  │ - subtask agg     │  │                                │  │
│  │ - mail.thread     │  │                                │  │
│  │ - notifications   │  │                                │  │
│  └──────────────────┘  └──────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Security Layer                                          │ │
│  │ - ir.model.access.csv (CRUD per group)                  │ │
│  │ - ir.rule (record-level: foreman→own brigade)           │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────┐
│                PostgreSQL (Odoo ORM)                         │
│  su_task, su_brigade, su_task_dependency_rel                 │
│  Indexes: state, brigade_id, project_id, deadline            │
└──────────────────────────────────────────────────────────────┘
```

## Files Modified / Created

| File | Action | Purpose |
|------|--------|---------|
| `models/su_task.py` | MODIFY | Add mail.thread, guard methods, subtask agg, circular dep check, notifications |
| `models/su_brigade.py` | MODIFY | Add member_count, active_task_count computed fields |
| `views/su_task_views.xml` | MODIFY | Enhance form (subtask stat button, dependency warnings), add kanban view |
| `views/su_brigade_views.xml` | MODIFY | Show member_count, active_task_count in tree/form |
| `security/ir.model.access.csv` | NO CHANGE | Existing CRUD rules are correct |
| `security/su_task_rules.xml` | CREATE | Record rules for RBAC (foreman/manager/client) |
| `tests/test_su_task.py` | CREATE | State transitions, blocked detection, RBAC, circular deps |
| `tests/__init__.py` | CREATE | Test package init |
| `__manifest__.py` | MODIFY | Add security/su_task_rules.xml to data, mail dependency |

## Data Model Changes

### su.task additions
- `_inherit = ['mail.thread', 'mail.activity.mixin']` — notifications
- `subtask_count` — `fields.Integer(compute='_compute_subtask_count')`
- `progress` — becomes computed when `child_ids` exist (hybrid)
- `_check_circular_dependency` — new constraint

### su.brigade additions
- `member_count` — `fields.Integer(compute='_compute_member_count', store=True)`
- `active_task_count` — `fields.Integer(compute='_compute_active_task_count')`

## Security Architecture

### Layer 1: Model Access (ir.model.access.csv) — EXISTING
- Foreman: CRUD (no unlink) on su.task
- Manager: CRUD (no unlink) on su.task, CRUD on su.brigade
- Admin: full CRUD on both
- Client: read-only on both

### Layer 2: Record Rules (ir.rule) — NEW
- `su_task_rule_foreman`: foreman sees only own brigade's tasks
- `su_task_rule_manager`: manager sees all tasks (global)
- `su_task_rule_client`: client sees only tasks on shared projects

### RBAC gap found (existing code)
Foreman has write access to su.task but no record rule limits which
tasks. Without record rules, a foreman can edit ANY task. This is the
primary security gap being fixed.

## Performance Considerations

- `is_blocked` is stored + indexed — avoids recomputation on every list load
- `member_count` is stored — one computation per brigade write
- `active_task_count` is NOT stored (changes frequently) — computed on read
- Kanban view: `read_group` by state uses database GROUP BY
- Dependency cycle check: bounded by max task count per project (~1000)
