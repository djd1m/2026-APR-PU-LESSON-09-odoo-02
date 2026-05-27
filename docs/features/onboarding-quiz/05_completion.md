# Completion Checklist: Onboarding Quiz (F07)

**Feature:** F07 — Onboarding Quiz
**Date:** 2026-05-27

---

## 1. Deliverables

| # | Artifact | Path | Status |
|---|----------|------|:------:|
| 1 | Model: SuOnboarding | `custom-addons/su_onboard/models/su_onboarding.py` | TODO |
| 2 | Controller | `custom-addons/su_onboard/controllers/onboarding_controller.py` | TODO |
| 3 | Views (wizard form) | `custom-addons/su_onboard/views/su_onboarding_views.xml` | TODO |
| 4 | Security (ACL) | `custom-addons/su_onboard/security/ir.model.access.csv` | TODO |
| 5 | Manifest | `custom-addons/su_onboard/__manifest__.py` | TODO |
| 6 | Tests | `custom-addons/su_onboard/tests/test_su_onboarding.py` | TODO |
| 7 | Init files | `__init__.py` (root, models/, controllers/, tests/) | TODO |

---

## 2. Acceptance Criteria

| AC | Criteria | Verification |
|----|----------|:------------:|
| AC-01 | Quiz displays 4 questions in wizard steps | Manual test |
| AC-02 | Submit stores all answers and computes recommended plan | Unit test |
| AC-03 | Plan recommendation matches specification matrix | Unit test (all combos) |
| AC-04 | Skip marks completed=True, skipped=True | Unit test |
| AC-05 | Re-submit overwrites (no duplicates) | Unit test |
| AC-06 | Invalid selection values rejected server-side | Unit test |
| AC-07 | company_id isolation enforced | Unit test |
| AC-08 | API endpoints return correct responses | Integration test |
| AC-09 | Security: foreman/manager/admin ACLs correct | ACL test |
| AC-10 | Quiz is skippable at every step | Manual test |

---

## 3. Definition of Done

- [ ] All unit tests pass (`odoo -d test --test-tags su_onboard`)
- [ ] Lint clean (`flake8 custom-addons/su_onboard/`)
- [ ] Module installs cleanly on fresh Odoo 17 database
- [ ] Security groups and ACLs verified
- [ ] No raw SQL — ORM only
- [ ] No hardcoded secrets or fallback values
- [ ] Money fields use Monetary/Decimal (N/A for this module — no money fields)
- [ ] Code review (Phase 4) completed

---

## 4. Out of Scope (for this feature)

- Dashboard widget rearrangement logic (F02 responsibility)
- Task template pre-filling logic (F03 responsibility)
- Subscription/billing changes (F08 responsibility)
- Frontend PWA implementation (F06 responsibility)
- The quiz only computes and stores the recommendation; acting on it is
  handled by other modules reading `su.onboarding` data.
