# Refinement: Onboarding Quiz (F07)

**Feature:** F07 — Onboarding Quiz
**Date:** 2026-05-27

---

## 1. Edge Cases

### 1.1 Partial Completion

**Scenario:** User answers Q1-Q2, then closes browser.
**Handling:** Answers are NOT saved until final submit. Partial state lives
only in the frontend. On next visit, quiz restarts from Q1. This is
intentional — avoids storing incomplete data.

### 1.2 Re-taking the Quiz

**Scenario:** User completed quiz, wants to change answers later.
**Handling:** `action_submit()` uses upsert (search existing record, overwrite).
The `completed_at` timestamp updates. `recommended_plan` recalculates.
No new record created.

### 1.3 Multiple Companies (Multi-tenant)

**Scenario:** User belongs to two companies.
**Handling:** SQL constraint `UNIQUE(partner_id, company_id)`. Each company
gets its own onboarding record. Quiz appears per-company on first switch.

### 1.4 Skipped Quiz + Later Completion

**Scenario:** User skips, later re-takes quiz from settings.
**Handling:** `action_submit()` sets `skipped = False`, `completed = True`,
overwrites default recommendation with computed one.

### 1.5 Invalid Selection Values

**Scenario:** Malicious client sends `company_type = "hacker"`.
**Handling:** Server-side validation against allowed selection keys.
Odoo ORM rejects values not in the Selection field definition.
Controller additionally validates before write.

---

## 2. Test Strategy

### 2.1 Unit Tests

| Test | Description |
|------|-------------|
| `test_plan_recommendation_matrix` | All 10+ company_type x object_count combinations return correct plan |
| `test_submit_creates_record` | Submit creates `su.onboarding` with all fields |
| `test_submit_idempotent` | Second submit overwrites first, no duplicate |
| `test_skip_sets_defaults` | Skip sets `completed=True`, `skipped=True`, `recommended_plan=starter` |
| `test_company_isolation` | Records filtered by `company_id` |
| `test_invalid_selection_rejected` | Invalid values raise `ValidationError` |

### 2.2 Integration Tests

| Test | Description |
|------|-------------|
| `test_status_endpoint_unauthenticated` | Returns 401 without session/JWT |
| `test_submit_endpoint_flow` | Full submit via HTTP, verify DB state |
| `test_skip_endpoint_flow` | Full skip via HTTP, verify DB state |

---

## 3. Error Handling

| Error | HTTP Code | User Message |
|-------|:---------:|--------------|
| Missing required field in submit | 400 | "Заполните все обязательные поля" |
| Invalid selection value | 400 | "Некорректное значение: {field}" |
| Not authenticated | 401 | "Требуется авторизация" |
| Server error | 500 | "Ошибка сервера, попробуйте позже" |

---

## 4. Performance Considerations

- Plan recommendation is O(1) — dictionary lookup, no DB queries.
- Quiz submit does one `search` + one `write` (or `create`) — 2 DB ops max.
- No N+1 queries possible — single record per partner.
- Index on `(partner_id, company_id)` via SQL constraint.

---

## 5. Migration Path

- Module install creates the `su_onboarding` table automatically (Odoo ORM).
- No data migration needed — new table, no existing data.
- If `su_billing` is not installed, quiz still works but cannot display
  plan pricing details (graceful degradation).
