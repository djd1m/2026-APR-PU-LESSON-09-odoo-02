# F03 Task Management — Specification

## Overview

Enhance the existing `su_task` Odoo module to deliver production-ready task
management for construction projects: state machine with dependency-aware
transitions, subtask aggregation, brigade workload tracking, kanban board,
push notifications on assignment, and RBAC enforcement (foreman sees own
brigade only, manager sees all).

## Functional Requirements

### FR-01: State Machine with Guard Conditions

| From | To | Guard | Button |
|------|----|-------|--------|
| `new` | `in_progress` | `is_blocked == False` | `action_start` |
| `in_progress` | `review` | — | `action_review` |
| `review` | `done` | — | `action_done` |
| `review` | `in_progress` | — | `action_reopen` |
| `new/in_progress/review` | `cancelled` | — | `action_cancel` |
| `done` | `in_progress` | — | `action_reopen` (future) |

- `action_start` MUST raise `ValidationError` when `is_blocked is True`.
- `action_complete` (alias for `action_done`) MUST set `progress = 100.0`.
- `action_cancel` MUST cascade-check: warn if dependent tasks exist that are
  not cancelled themselves.

### FR-02: Dependency Engine (Finish-to-Start)

- `dependency_ids` (existing M2M) represents finish-to-start links.
- `is_blocked` computed field: `True` when any dependency is NOT in
  `done` or `cancelled` state.
- Stored, recomputed on `dependency_ids.state` change.
- Circular dependency prevention via `@api.constrains`.

### FR-03: Subtask Progress Aggregation

- Parent task `progress` auto-computed as weighted average of children's
  progress when children exist.
- Weight = 1 per child (equal weighting for MVP).
- Parent with no children: manual progress as today.
- `subtask_count` computed field for stat button.

### FR-04: Brigade Computed Fields

- `member_count`: computed count of `member_ids`.
- `active_task_count`: computed count of tasks in states `new`,
  `in_progress`, `review`.

### FR-05: Kanban View with Drag-Drop

- Kanban grouped by `state` with drag-drop between columns.
- Card shows: name, priority (stars), brigade, assignee avatar, deadline,
  progress bar, blocked ribbon.
- Drag restricted: cannot move to `in_progress` if `is_blocked`.

### FR-06: Push Notifications on Assignment

- When `brigade_id` changes on a task, send Odoo `mail.message` notification
  to the brigade foreman and all brigade members.
- Uses `mail.thread` mixin on `su.task`.

### FR-07: RBAC — Record Rules

- **Foreman:** read/write only tasks where `brigade_id.foreman_id == user`
  OR `brigade_id.member_ids contains user`.
- **Manager:** read/write ALL tasks.
- **Client:** read-only tasks of projects shared with them.
- Implemented via `ir.rule` domain filters.

## Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| Performance | Task list < 1s for 10K tasks (indexed queries) |
| Money | `planned_cost` MUST be `fields.Monetary` — never Float |
| Security | No privilege escalation via direct ORM calls |
| Offline | Kanban view state cached via PWA service worker (future) |
| i18n | All user-facing strings in Russian, technical in English |

## Acceptance Criteria

1. State transitions enforce dependency guards — blocked task cannot start.
2. Circular dependency raises `ValidationError`.
3. Subtask progress propagates to parent.
4. Kanban drag-drop respects blocked status.
5. Foreman cannot see other brigades' tasks.
6. Manager sees all tasks.
7. Brigade form shows member count and active task count.
8. Assignment triggers notification to brigade.
