# F03 Task Management — Validation Report

**Date:** 2026-05-27
**Validator:** requirements-validator
**Verdict:** READY

## Scoring

| Dimension | Score | Notes |
|-----------|-------|-------|
| Completeness | 85 | All FR covered, NFR addressed, edge cases documented |
| Consistency | 90 | State machine, RBAC, data model internally consistent |
| Testability | 90 | Each FR has corresponding test case with clear AC |
| Feasibility | 95 | Pure Odoo ORM, no external deps, standard patterns |
| Security | 80 | RBAC gap identified and fix planned, no privilege escalation vectors |
| Performance | 85 | Stored computed fields, bounded algorithms |

**Average: 87.5** (threshold: 70)

## Blockers

None.

## Caveats

### C-01: Client Record Rule (Low)
The client record rule domain is a placeholder. Requires `su.project` sharing
mechanism (project ↔ client link) which does not exist yet. Recommend
implementing as `[(1, '=', 0)]` (deny all) until sharing is built.

**Impact:** Clients won't see tasks until F11 (Client Portal). Acceptable for MVP.

### C-02: Notification Volume (Medium)
Brigade assignment notification goes to ALL members. For large brigades (15+
workers), this may generate noise. Consider adding a user preference for
notification opt-out in future iteration.

**Impact:** Cosmetic — notifications work, may be excessive. No blocker.

### C-03: Subtask Progress Hybrid (Low)
Progress field is both manually editable AND computed from children. If user
manually sets progress on a parent that has children, the computed value
overwrites on next recompute. Document this behavior for users.

**Impact:** UX surprise, not a bug. Computed always wins when children exist.

## Requirements Traceability

| PRD Requirement | Spec Reference | Test Case |
|-----------------|---------------|-----------|
| US-04: Create task, assign brigade | FR-01, FR-06 | test_state_new_to_in_progress, test_notification |
| US-04: Push notification | FR-06 | test_notification_on_assignment |
| US-04: Statuses new→in_progress→review→done | FR-01 | test_state_* |
| US-04: Subtasks and dependencies | FR-02, FR-03 | test_circular_*, test_subtask_* |
| F03: RBAC foreman/manager | FR-07 | test_foreman_rbac, test_manager_rbac |

## Verdict

**READY** — proceed to Phase 3 (IMPLEMENT).
