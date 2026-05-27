# Architecture: Onboarding Quiz (F07)

**Feature:** F07 — Onboarding Quiz
**Date:** 2026-05-27

---

## 1. Module Placement

```
custom-addons/
├── su_base/         # security groups (pre-existing)
├── su_billing/      # subscription model (pre-existing, dependency)
├── su_onboard/      # ← NEW MODULE
│   ├── __init__.py
│   ├── __manifest__.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── su_onboarding.py
│   ├── controllers/
│   │   ├── __init__.py
│   │   └── onboarding_controller.py
│   ├── views/
│   │   └── su_onboarding_views.xml
│   ├── security/
│   │   └── ir.model.access.csv
│   └── tests/
│       ├── __init__.py
│       └── test_su_onboarding.py
```

---

## 2. Dependencies

```
su_onboard
├── depends: su_base (security groups)
└── optional: su_billing (plan recommendation display)
```

`su_onboard` does NOT modify subscriptions directly. It only computes a
`recommended_plan` field. Activating a trial/plan is handled by `su_billing`.

---

## 3. Data Flow

```
User Login
    │
    ▼
Frontend checks GET /api/v1/onboarding/status
    │
    ├─ completed=true → skip, go to dashboard
    │
    └─ completed=false → show quiz wizard
                │
                ▼
        User answers 4 questions (or clicks Skip)
                │
                ▼
        POST /api/v1/onboarding/submit (or /skip)
                │
                ▼
        SuOnboarding._compute_recommended_plan()
                │
                ▼
        Store answers + recommended_plan
                │
                ▼
        Return recommendation to frontend
                │
                ▼
        User sees recommended plan + CTA
                │
                ├─ "Activate Trial" → redirect to su_billing
                └─ "Continue" → dashboard
```

---

## 4. Integration Points

### 4.1 su_billing (read-only)

The quiz reads the `PLAN_CONFIG` dictionary from `su_billing` to display
plan features alongside the recommendation. No write operations on
`su.subscription`.

### 4.2 Dashboard Personalization (future)

The `company_type` and `object_count` answers will be used by the dashboard
module to configure default widget layout. This is a read-only relationship:
the dashboard reads `su.onboarding` at render time.

### 4.3 Task Templates (future)

Pre-filled task templates based on `company_type`. Template data stored as
`data/*.xml` within `su_onboard`. Applied via `action_submit()` after quiz
completion.

---

## 5. Security Architecture

| Layer | Mechanism |
|-------|-----------|
| Authentication | Odoo session auth (views) / JWT (API endpoints) |
| Authorization | `ir.model.access.csv` — RBAC per security group |
| Tenant isolation | `company_id` field + Odoo multi-company rules |
| Input validation | Server-side selection value whitelisting |
| SQL injection | Odoo ORM only — no raw SQL |

---

## 6. Scalability

- One `su.onboarding` record per partner per company (small table).
- No heavy computation — plan recommendation is a simple lookup table.
- No external service calls.
- No caching needed — data read once per login.
