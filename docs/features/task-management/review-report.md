# F03 Task Management — Review Report

**Date:** 2026-05-27
**Reviewer:** brutal-honesty-review
**Phase:** 4 (REVIEW)

---

## Findings

### BLOCKER-01: Kanban drag-drop bypasses `action_start` guard (FIXED)

**Severity:** blocker
**Category:** Security / State Machine Integrity

**Problem:** When a user drags a task card from "new" to "in_progress" in kanban
view, Odoo calls `write({'state': 'in_progress'})` directly — NOT
`action_start()`. The blocked check in `action_start` was therefore
completely bypassed, allowing blocked tasks to be started via drag-drop.

**Fix applied:** Added guard in `write()` override: if `state` changes to
`in_progress` from `new` and `is_blocked is True`, raise `ValidationError`.

**Status:** FIXED in this phase.

---

### HIGH-01: RBAC record rules use `noupdate="1"` — cannot fix via module upgrade

**Severity:** high
**Category:** Security

**Problem:** `su_task_rules.xml` has `noupdate="1"`. If record rule domains
need correction after initial install, `odoo -u su_task` will NOT update
them. An admin must manually edit via UI or use `--init`.

**Recommendation:** For development phase, keep `noupdate="0"`. Switch to
`noupdate="1"` only for production freeze. Current setting is acceptable
for security-sensitive data (prevents accidental overwrites), but team must
be aware of the trade-off.

**Status:** Acknowledged — no change needed for MVP.

---

### HIGH-02: Foreman record rule does not cover unassigned tasks

**Severity:** high
**Category:** RBAC Gap

**Problem:** The foreman record rule domain is:
```python
['|', ('brigade_id.foreman_id', '=', user.id), ('brigade_id.member_ids', 'in', user.id)]
```
Tasks with `brigade_id = False` (unassigned) are invisible to foremen.
This is correct behavior IF managers always assign brigades first. However,
if a foreman creates a task (they have create permission), they immediately
lose visibility of their own task until a brigade is assigned.

**Recommendation:** Extend domain to include:
```python
['|', '|', ('brigade_id', '=', False), ...]
```
OR restrict foreman's create permission (remove perm_create in CSV).

**Status:** Deferred — requires product decision. Logged as follow-up.

---

### MEDIUM-01: `action_complete` alias is a class-level reference, not a true method

**Severity:** medium
**Category:** Code Quality

**Problem:** `action_complete = action_done` creates a class-level alias.
This works in Python but will NOT work as an Odoo button `name` in XML
because Odoo resolves button methods via `getattr` on the model instance,
and class-level aliases don't participate in Odoo's method resolution for
`type="object"` buttons in all cases.

**Impact:** Low — `action_complete` is not referenced in any XML. It's only
a code-level alias for potential programmatic use. No dead code, but
borderline unnecessary.

**Status:** Acknowledged — keep for API convenience.

---

### MEDIUM-02: No index on `su_task_dependency_rel` join table

**Severity:** medium
**Category:** Performance

**Problem:** The M2M relation table `su_task_dependency_rel` relies on Odoo's
auto-generated indexes. For large projects (1K+ tasks), the circular
dependency check does `self.browse(dep_id).dependency_ids.ids` in a loop,
which hits this table repeatedly.

**Recommendation:** Add explicit SQL index via `init()` method or accept
Odoo's default B-tree indexes on FK columns (which Odoo does create).

**Status:** Acceptable for MVP (<1K tasks per project).

---

### MEDIUM-03: `_compute_subtask_count` not stored — N+1 on list views

**Severity:** medium
**Category:** Performance

**Problem:** `subtask_count` is computed but not stored. In tree view with
`optional="show"`, loading 100 tasks triggers 100 separate `len(child_ids)`
computations. Odoo batches these via prefetch, but storing would be faster.

**Recommendation:** Add `store=True` and `@api.depends('child_ids')`.

**Status:** Deferred — acceptable for MVP volume.

---

### LOW-01: `progress` field is `Float` (correct per coding-style.md)

**Severity:** low
**Category:** Money / Types

**Problem:** Reviewed `progress` field — it is `fields.Float` for percentage,
NOT for money. This is correct. `planned_cost` correctly uses
`fields.Monetary`. No Float-money violation found.

**Status:** Clean — no issue.

---

### LOW-02: No dead code detected

**Severity:** low
**Category:** Code Quality

**Problem:** Checked for orphaned methods, unused imports, unreachable code.
All methods are wired to XML buttons or called programmatically.
`action_view_subtasks` and `action_view_tasks` are referenced in form views.

**Status:** Clean — no dead code.

---

### LOW-03: `su_photo` dependency in manifest

**Severity:** low
**Category:** Architecture

**Problem:** `__manifest__.py` declares dependency on `su_photo` module.
The `photo_ids` field and photo stat button reference
`%(su_photo.su_photo_action)d`. If `su_photo` is not installed, module
install will fail with a clear error (Odoo dependency resolution). This is
correct behavior.

**Status:** Clean — dependency is intentional.

---

## Summary

| Severity | Count | Fixed | Deferred |
|----------|-------|-------|----------|
| Blocker | 1 | 1 | 0 |
| High | 2 | 0 | 2 |
| Medium | 3 | 0 | 3 |
| Low | 3 | 0 | 0 (clean) |

**Verdict:** All blockers fixed. No remaining blockers. Feature is
**READY FOR MERGE** with HIGH-02 tracked as follow-up issue.

## Follow-Up Issues

1. **HIGH-02:** Decide on foreman visibility for unassigned tasks — product
   decision needed.
2. **MEDIUM-03:** Store `subtask_count` when task volume exceeds 500/project.
