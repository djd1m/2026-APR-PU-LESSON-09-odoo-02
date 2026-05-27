# Auth & Billing (F08) -- Architecture

**Feature ID:** F08
**Version:** 1.0
**Date:** 2026-05-27

---

## 1. Component Overview

Auth & Billing is implemented as an Odoo custom module (`su_billing`) within
the Odoo backend container. It extends the standard `res.users` model and
adds subscription/payment models. No separate microservice is needed.

```
┌─────────────────────── Odoo Backend Container ───────────────────────┐
│                                                                       │
│  ┌──────────────────── su_billing module ─────────────────────────┐  │
│  │                                                                 │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐  │  │
│  │  │ Auth        │  │ Subscription│  │ YooKassa Integration │  │  │
│  │  │ Controller  │  │ Manager     │  │ Service              │  │  │
│  │  │             │  │             │  │                      │  │  │
│  │  │ - register  │  │ - plans     │  │ - create_payment     │  │  │
│  │  │ - login     │  │ - trial     │  │ - verify_webhook     │  │  │
│  │  │ - refresh   │  │ - upgrade   │  │ - process_event      │  │  │
│  │  │ - logout    │  │ - downgrade │  │ - recurring_charge   │  │  │
│  │  │ - reset_pwd │  │ - usage     │  │ - refund             │  │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────────┬───────────┘  │  │
│  │         │                │                     │              │  │
│  │  ┌──────▼────────────────▼─────────────────────▼───────────┐  │  │
│  │  │                  JWT Middleware                          │  │  │
│  │  │  - Extract token from httpOnly cookie                   │  │  │
│  │  │  - RS256 verification                                   │  │  │
│  │  │  - Attach user + company_id to request context          │  │  │
│  │  │  - RBAC decorator for endpoint authorization            │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌──────────────────── Existing Odoo Models ──────────────────────┐  │
│  │  res.users (extended)  │  res.company (tenant)                 │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────┬──────────────────────┬──────────────────────┬─────────────┘
           │                      │                      │
     ┌─────▼──────┐     ┌────────▼────────┐     ┌───────▼───────┐
     │ PostgreSQL │     │ Redis           │     │ YooKassa API  │
     │            │     │                 │     │ (external)    │
     │ - users    │     │ - refresh tokens│     │               │
     │ - subscr.  │     │ - rate limits   │     │ - payments    │
     │ - payments │     │ - sessions      │     │ - webhooks    │
     │ - webhooks │     │ - lockouts      │     │ - refunds     │
     └────────────┘     └─────────────────┘     └───────────────┘
```

---

## 2. Data Model

### 2.1 res.users Extension

Extends Odoo's built-in `res.users` model with auth-specific fields.

```
res.users (EXTENDED)
├── id                     : Integer (PK, Odoo standard)
├── login                  : Char (email, Odoo standard, UNIQUE)
├── password               : Char (bcrypt hash, Odoo standard, cost >= 12)
├── phone                  : Char (UNIQUE, nullable)
├── full_name              : Char (required)
├── role                   : Selection ['admin', 'manager', 'foreman', 'client']
├── company_id             : Many2one → res.company (tenant, Odoo standard)
├── is_email_confirmed     : Boolean (default: false)
├── is_active              : Boolean (default: true)
├── pd_consent_at          : Datetime (152-FZ consent timestamp)
├── pd_consent_version     : Char (consent document version)
├── password_history       : Text (JSON array of last 3 bcrypt hashes)
├── last_login_at          : Datetime
├── failed_login_attempts  : Integer (default: 0)
├── locked_until           : Datetime (nullable)
├── created_at             : Datetime (default: now)
└── updated_at             : Datetime (auto-update)

CONSTRAINTS:
  - UNIQUE(login)
  - UNIQUE(phone) WHERE phone IS NOT NULL
  - CHECK(role IN ('admin', 'manager', 'foreman', 'client'))
```

### 2.2 su.subscription

```
su.subscription
├── id                       : Integer (PK)
├── company_id               : Many2one → res.company (REQUIRED, indexed)
├── plan                     : Selection ['free', 'starter', 'business', 'enterprise']
├── status                   : Selection ['trial', 'active', 'past_due', 'canceled']
├── trial_start              : Date (nullable)
├── trial_end                : Date (nullable)
├── current_period_start     : Date
├── current_period_end       : Date
├── objects_limit            : Integer
├── ai_estimates_limit       : Integer
├── ai_estimates_used        : Integer (default: 0, reset each period)
├── yukassa_customer_id      : Char (nullable, for saved payment methods)
├── yukassa_subscription_id  : Char (nullable, for recurring)
├── billing_cycle            : Selection ['monthly', 'annual'] (default: monthly)
├── amount                   : Monetary (Decimal, current plan price in RUB)
├── currency                 : Char (default: 'RUB')
├── created_at               : Datetime
└── updated_at               : Datetime

CONSTRAINTS:
  - ONE active subscription per company_id (unique where status != 'canceled')
  - amount uses fields.Monetary (Decimal, NEVER Float)

INDEXES:
  - idx_subscription_company ON (company_id)
  - idx_subscription_status ON (status)
  - idx_subscription_trial_end ON (trial_end) WHERE status = 'trial'
```

### 2.3 su.payment

```
su.payment
├── id                    : Integer (PK)
├── subscription_id       : Many2one → su.subscription (REQUIRED)
├── company_id            : Many2one → res.company (denormalized for queries)
├── amount                : Monetary (Decimal, NEVER Float)
├── currency              : Char (default: 'RUB')
├── status                : Selection ['pending', 'success', 'failed', 'refunded']
├── yukassa_payment_id    : Char (UNIQUE, indexed)
├── payment_method        : Selection ['bank_card', 'sbp', 'yoo_money']
├── description           : Char
├── paid_at               : Datetime (nullable)
├── failed_at             : Datetime (nullable)
├── failure_reason        : Char (nullable)
├── refund_amount         : Monetary (Decimal, nullable)
├── refund_reason         : Char (nullable)
├── retry_count           : Integer (default: 0)
├── next_retry_at         : Datetime (nullable)
├── created_at            : Datetime
└── updated_at            : Datetime

CONSTRAINTS:
  - amount > 0
  - UNIQUE(yukassa_payment_id)
  - amount and refund_amount are Decimal (NEVER Float)

INDEXES:
  - idx_payment_subscription ON (subscription_id)
  - idx_payment_status ON (status)
  - idx_payment_yukassa_id ON (yukassa_payment_id)
```

### 2.4 su.webhook_log

```
su.webhook_log
├── id                : Integer (PK)
├── idempotency_key   : Char (UNIQUE, indexed)
├── event_type        : Char
├── payload           : Text (JSON)
├── source_ip         : Char
├── signature_valid   : Boolean
├── processed_at      : Datetime
├── created_at        : Datetime

CONSTRAINTS:
  - UNIQUE(idempotency_key)

INDEXES:
  - idx_webhook_idempotency ON (idempotency_key)
  - idx_webhook_created ON (created_at)

PARTITIONING:
  - By month on created_at (retain 12 months online, archive older)
```

---

## 3. API Endpoints

### 3.1 Authentication

| Method | Endpoint | Auth | Role | Description |
|--------|----------|:----:|------|-------------|
| POST | `/api/v1/auth/register` | None | - | Register new user + company |
| POST | `/api/v1/auth/login` | None | - | Login, returns JWT in cookies |
| POST | `/api/v1/auth/refresh` | Cookie | Any | Rotate refresh token |
| POST | `/api/v1/auth/logout` | Cookie | Any | Invalidate tokens, clear cookies |
| POST | `/api/v1/auth/password/reset-request` | None | - | Request password reset |
| POST | `/api/v1/auth/password/reset-confirm` | None | - | Confirm password reset |
| GET | `/api/v1/auth/confirm-email/{token}` | None | - | Confirm email address |
| GET | `/api/v1/auth/me` | Cookie | Any | Current user profile |

### 3.2 User Management

| Method | Endpoint | Auth | Role | Description |
|--------|----------|:----:|------|-------------|
| GET | `/api/v1/users` | Cookie | admin | List company users |
| POST | `/api/v1/users/invite` | Cookie | admin, manager | Invite user by email with role |
| PATCH | `/api/v1/users/{id}/role` | Cookie | admin | Change user role |
| DELETE | `/api/v1/users/{id}` | Cookie | admin | Deactivate user |
| POST | `/api/v1/users/{id}/logout-all` | Cookie | admin, self | Revoke all sessions |

### 3.3 Subscription & Billing

| Method | Endpoint | Auth | Role | Description |
|--------|----------|:----:|------|-------------|
| GET | `/api/v1/billing/plans` | None | - | List available plans with pricing |
| GET | `/api/v1/billing/subscription` | Cookie | admin | Current subscription details |
| POST | `/api/v1/billing/subscribe` | Cookie | admin | Create/change subscription |
| POST | `/api/v1/billing/cancel` | Cookie | admin | Cancel subscription |
| GET | `/api/v1/billing/payments` | Cookie | admin | Payment history |
| GET | `/api/v1/billing/usage` | Cookie | admin, manager | Current period usage stats |

### 3.4 Webhooks

| Method | Endpoint | Auth | Description |
|--------|----------|:----:|-------------|
| POST | `/api/v1/webhooks/yukassa` | HMAC | YooKassa payment events |

**Security notes:**
- `/auth/register` MUST NOT accept `role` field in request body
- All `/billing/*` endpoints enforce `company_id` scoping
- Webhook endpoint validates HMAC before any processing
- Rate limits applied per endpoint group (see Specification)

---

## 4. Security Architecture

### 4.1 Token Flow

```
┌──────┐     ┌──────────┐     ┌──────────┐     ┌─────────┐
│Client│     │ Nginx    │     │  Odoo    │     │  Redis  │
│(PWA) │     │ (proxy)  │     │ Backend  │     │         │
└──┬───┘     └────┬─────┘     └────┬─────┘     └────┬────┘
   │              │                │                 │
   │ POST /login  │                │                 │
   │─────────────>│                │                 │
   │              │ Forward        │                 │
   │              │───────────────>│                 │
   │              │                │ Verify password │
   │              │                │ (bcrypt)        │
   │              │                │                 │
   │              │                │ Generate JWT    │
   │              │                │ (RS256)         │
   │              │                │                 │
   │              │                │ Store refresh   │
   │              │                │────────────────>│
   │              │                │                 │
   │              │ Set-Cookie:    │                 │
   │              │ access_token   │                 │
   │              │ (httpOnly)     │                 │
   │<─────────────│<───────────────│                 │
   │              │                │                 │
   │ GET /api/... │                │                 │
   │ Cookie: ...  │                │                 │
   │─────────────>│───────────────>│                 │
   │              │                │ JWT middleware:  │
   │              │                │ extract cookie   │
   │              │                │ verify RS256     │
   │              │                │ attach user ctx  │
   │              │                │ check RBAC       │
   │              │                │ enforce tenant   │
```

### 4.2 Tenant Isolation

```
EVERY database query includes:
  WHERE company_id = request.company_id

Implementation:
  - Odoo record rules (ir.rule) on all su_billing models
  - Additional manual check in controllers for edge cases
  - PostgreSQL row-level security as defense-in-depth layer

Cross-tenant access:
  - IMPOSSIBLE by design
  - No API endpoint allows specifying another company_id
  - Admin role is scoped to own tenant only
```

### 4.3 Webhook Security

```
YooKassa ──HTTPS──> Nginx ──> /api/v1/webhooks/yukassa

Verification steps:
  1. Read X-Yukassa-Signature header
  2. Compute HMAC-SHA256(webhook_secret, raw_body)
  3. Constant-time comparison (hmac.compare_digest)
  4. Check timestamp within 5-minute window (replay protection)
  5. Check idempotency_key in su.webhook_log (dedup)
  6. Process event inside transaction
```

---

## 5. Module Structure

```
addons/
└── su_billing/
    ├── __init__.py
    ├── __manifest__.py
    ├── controllers/
    │   ├── __init__.py
    │   ├── auth.py              # register, login, refresh, logout
    │   ├── billing.py           # plans, subscribe, cancel, payments
    │   ├── users.py             # invite, role change, deactivate
    │   └── webhooks.py          # YooKassa webhook handler
    ├── models/
    │   ├── __init__.py
    │   ├── res_users.py         # res.users extension
    │   ├── subscription.py      # su.subscription model
    │   ├── payment.py           # su.payment model
    │   └── webhook_log.py       # su.webhook_log model
    ├── services/
    │   ├── __init__.py
    │   ├── jwt_service.py       # Token generation, verification
    │   ├── yukassa_service.py   # YooKassa API client
    │   └── subscription_service.py  # Trial, upgrade, downgrade logic
    ├── middleware/
    │   ├── __init__.py
    │   └── jwt_middleware.py    # Cookie extraction, verification, RBAC
    ├── cron/
    │   ├── __init__.py
    │   ├── trial_expiration.py  # Daily trial check
    │   └── payment_retry.py     # Failed payment retry
    ├── security/
    │   ├── ir.model.access.csv  # Odoo ACL
    │   └── security.xml         # Record rules (tenant isolation)
    ├── data/
    │   ├── subscription_plans.xml   # Plan definitions
    │   └── cron_jobs.xml            # Scheduled actions
    └── views/
        └── (Odoo backend views if needed)
```

---

## 6. External Dependencies

| Dependency | Purpose | Env Vars |
|------------|---------|----------|
| PostgreSQL | Primary database | `DATABASE_URL` |
| Redis | Refresh tokens, rate limiting, sessions | `REDIS_URL` |
| YooKassa API | Payment processing | `YUKASSA_SHOP_ID`, `YUKASSA_SECRET_KEY`, `YUKASSA_WEBHOOK_SECRET` |
| SMS.ru / Twilio | Phone verification | `SMS_PROVIDER`, `SMS_API_KEY` |
| SMTP | Email (confirmation, reminders, receipts) | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` |

All are required at startup. Application crashes if any is missing (see
startup validation in Pseudocode, Section 8).

---

## 7. Sequence: Subscription Upgrade

```
User              Frontend           Odoo API         YooKassa         DB
 │                    │                  │                │              │
 │ Click "Upgrade"    │                  │                │              │
 │───────────────────>│                  │                │              │
 │                    │ POST /subscribe  │                │              │
 │                    │ {plan: "business"}│                │              │
 │                    │─────────────────>│                │              │
 │                    │                  │ Calculate      │              │
 │                    │                  │ prorated amount│              │
 │                    │                  │ (Decimal math) │              │
 │                    │                  │                │              │
 │                    │                  │ Create payment │              │
 │                    │                  │───────────────>│              │
 │                    │                  │                │              │
 │                    │ Redirect to      │ confirmation   │              │
 │                    │ YooKassa checkout │<──────────────│              │
 │<───────────────────│                  │                │              │
 │                    │                  │                │              │
 │ (user pays)        │                  │                │              │
 │                    │                  │   Webhook      │              │
 │                    │                  │<───────────────│              │
 │                    │                  │ Verify HMAC    │              │
 │                    │                  │ Update plan    │              │
 │                    │                  │───────────────────────────────>│
 │                    │                  │                │              │
 │                    │ Plan updated     │                │              │
 │<───────────────────│<─────────────────│                │              │
```
