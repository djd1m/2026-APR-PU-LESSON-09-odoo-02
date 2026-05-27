# Auth & Billing (F08) -- Specification

**Feature ID:** F08
**Version:** 1.0
**Date:** 2026-05-27
**Status:** Draft
**References:** PRD.md (F08), Specification.md (Section 1.8, NFR-SEC-*), security.md

---

## 1. Overview

Auth & Billing covers user registration, authentication, role-based access
control, multi-tenant isolation, subscription management, and payment
processing via YooKassa for the СтройУправ platform. The module runs inside
the Odoo backend as `su_billing` and extends `res.users`.

---

## 2. Functional Requirements

### 2.1 User Registration

| ID | Requirement | Priority | Description |
|----|-------------|:--------:|-------------|
| FR-AB-01 | Email registration | P0 | User registers with email + password. Email confirmation link sent (TTL 24h). Password hashed with bcrypt, cost >= 12. |
| FR-AB-02 | Phone registration | P0 | User registers with phone number + SMS code (SMS.ru / Twilio). Code TTL: 5 min, max 3 attempts. |
| FR-AB-03 | Registration fields | P0 | Required: email OR phone, password (min 8 chars, 1 uppercase, 1 digit), full name, company name. Optional: INN, position. |
| FR-AB-04 | Role assignment | P0 | Default role on registration: `admin` (company owner). Role is NEVER accepted from the registration request body. Server assigns it. |
| FR-AB-05 | Tenant creation | P0 | On registration, system creates an Odoo company (tenant) and associates the user as owner. All subsequent data is scoped to this tenant via `company_id`. |
| FR-AB-06 | 152-FZ consent | P0 | User must accept personal data processing agreement during registration. Timestamp and version stored in DB. |
| FR-AB-07 | Duplicate prevention | P0 | Unique constraint on email and phone. Clear error message if already registered. |

### 2.2 Authentication (Login / JWT)

| ID | Requirement | Priority | Description |
|----|-------------|:--------:|-------------|
| FR-AB-10 | Login | P0 | Email/phone + password. On success: issue JWT access token (15 min TTL) + refresh token (7 days TTL). |
| FR-AB-11 | Token storage | P0 | Both tokens stored in httpOnly, Secure, SameSite=Strict cookies. NEVER in localStorage/sessionStorage. |
| FR-AB-12 | Token signing | P0 | RS256 algorithm. Key rotation every 90 days. `JWT_SECRET_KEY` loaded from env var -- application MUST crash on startup if missing. No hardcoded fallbacks. |
| FR-AB-13 | Refresh token rotation | P0 | Refresh tokens are single-use. On refresh, old token is invalidated and new pair (access + refresh) is issued. |
| FR-AB-14 | Logout | P0 | Invalidate refresh token server-side (Redis blacklist or DB deletion). Clear cookies. |
| FR-AB-15 | Brute-force protection | P0 | Max 5 failed login attempts per 15 min per IP/account. After threshold: 30 min lockout + email/SMS notification. |
| FR-AB-16 | Password reset | P0 | "Forgot password" flow: email/SMS with reset link/code (TTL 1h, single-use). New password must differ from previous 3. |
| FR-AB-17 | Multi-device support | P0 | Each device gets its own refresh token. Logout from one device does not affect others. "Logout all devices" option available. |

### 2.3 RBAC (Role-Based Access Control)

| Role | Dashboard | Projects | Tasks | Photos | Estimates | Billing | User Mgmt |
|------|:---------:|:--------:|:-----:|:------:|:---------:|:-------:|:---------:|
| `admin` | Full | CRUD | CRUD | CRUD | CRUD | Full | Full |
| `manager` | Full | CRUD | CRUD | CRUD | CRUD | View | Invite |
| `foreman` | Own projects | View assigned | CRUD own | CRUD own | View assigned | - | - |
| `client` | Assigned projects | View assigned | View | View | View | - | - |

**Enforcement rules:**
- RBAC checked on every API endpoint (decorator/middleware)
- Row-level security via `company_id` (tenant isolation) in every query
- Object ownership verified before update/delete (prevent IDOR)
- Client-side role claims are NEVER trusted

### 2.4 Subscription Plans

| Plan | Price (monthly) | Objects | AI Estimates/mo | Features | Overage |
|------|:---------------:|:-------:|:---------------:|----------|:-------:|
| Free | 0 | 1 | 3 | Dashboard, tasks, photo | - |
| Starter | 2 990 RUB | 5 | 20 | + Budget reports, export | 490 RUB/estimate |
| Business | 9 900 RUB | 20 | 100 | + KS-2/KS-3, client portal | 490 RUB/estimate |
| Enterprise | 49 900 RUB | Unlimited | Unlimited | + API, priority support, SLA 99.9% | - |

**Rules:**
- All monetary values stored as `Decimal` (Python `decimal.Decimal`, Odoo `fields.Monetary`). NEVER `float`.
- Prices include VAT (20%).
- Annual billing: 2 months free (10-month price).

### 2.5 Trial

| ID | Requirement | Priority | Description |
|----|-------------|:--------:|-------------|
| FR-AB-30 | Trial activation | P0 | 14-day trial of Business plan on registration. No payment required. |
| FR-AB-31 | Trial countdown | P0 | Display remaining trial days in UI. Email reminders at 7, 3, and 1 day before expiration. |
| FR-AB-32 | Trial expiration | P0 | Automatic downgrade to Free plan. Cron job runs daily. Active projects beyond Free limit are read-only, not deleted. |
| FR-AB-33 | Trial once | P0 | One trial per email/phone/company. Prevent abuse via duplicate registrations. |

### 2.6 YooKassa Payment Integration

| ID | Requirement | Priority | Description |
|----|-------------|:--------:|-------------|
| FR-AB-40 | Payment methods | P0 | Bank cards (Visa, MasterCard, MIR), SBP (Sistema Bystrykh Platezhey), YooMoney. |
| FR-AB-41 | Recurring payments | P0 | Auto-charge on subscription renewal. Saved payment method. User can update/remove card. |
| FR-AB-42 | Webhook processing | P0 | YooKassa sends payment status updates via webhook. HMAC-SHA256 signature verification required. Constant-time comparison. |
| FR-AB-43 | Idempotency | P0 | Webhook processing is idempotent. Deduplicate by `idempotency_key`. |
| FR-AB-44 | Upgrade/Downgrade | P0 | Plan change with prorated billing. Upgrade: charge difference immediately. Downgrade: credit applied to next billing cycle. |
| FR-AB-45 | Payment history | P0 | Full payment history with status (success/failed/refunded), amount, date, payment method. |
| FR-AB-46 | Failed payment retry | P0 | On failed recurring payment: retry after 1, 3, 7 days. After 3 failures: downgrade to Free + email notification. |
| FR-AB-47 | Refunds | P1 | Admin-initiated refunds via YooKassa API. Partial refunds supported. |

---

## 3. User Stories

### US-F08-01: Registration

```
As a construction company owner,
I want to register with my email and company name,
so that I can start managing my projects in СтройУправ.

Acceptance Criteria:
  1. GIVEN I fill in email, password (>=8 chars, 1 uppercase, 1 digit),
     full name, and company name
     WHEN I submit the registration form
     THEN my account is created with role=admin, a tenant (company) is
     created, and I receive a confirmation email

  2. GIVEN I register successfully
     THEN I am automatically enrolled in a 14-day Business trial

  3. GIVEN I try to register with an email that already exists
     THEN I see an error "This email is already registered"

  4. GIVEN the registration request body contains a "role" field
     THEN the server IGNORES it and assigns the default role (admin/owner)

  5. GIVEN I register
     THEN I must accept the 152-FZ personal data processing agreement
```

### US-F08-02: Login

```
As a registered user,
I want to log in with my email and password,
so that I can access my projects securely.

Acceptance Criteria:
  1. GIVEN I enter valid email and password
     WHEN I submit the login form
     THEN I receive JWT access token (15 min) and refresh token (7 days)
     in httpOnly cookies

  2. GIVEN I enter wrong password 5 times within 15 minutes
     THEN my account is locked for 30 minutes and I receive a notification

  3. GIVEN my access token expired
     WHEN my browser sends a request
     THEN the middleware uses the refresh token to obtain a new access token
     transparently

  4. GIVEN I click "Logout"
     THEN both cookies are cleared and refresh token is invalidated server-side
```

### US-F08-03: Subscription Management

```
As a company admin,
I want to choose a subscription plan and pay via YooKassa,
so that I can unlock features for my team.

Acceptance Criteria:
  1. GIVEN I am on the Free plan
     WHEN I select "Starter" and enter my card details
     THEN YooKassa processes the payment and my plan upgrades immediately

  2. GIVEN I upgrade mid-cycle from Starter to Business
     THEN I am charged the prorated difference for the remaining days

  3. GIVEN I downgrade from Business to Starter
     THEN the change takes effect at the end of the current billing cycle

  4. GIVEN my recurring payment fails
     THEN the system retries after 1, 3, 7 days before downgrading to Free
```

### US-F08-04: Trial Expiration

```
As a trial user,
I want to be notified before my trial ends,
so that I can decide whether to subscribe.

Acceptance Criteria:
  1. GIVEN I am on a 14-day trial
     THEN I see a banner showing remaining trial days

  2. GIVEN my trial has 7, 3, or 1 day(s) remaining
     THEN I receive an email reminder

  3. GIVEN my trial expires and I have not subscribed
     THEN my plan downgrades to Free
     AND my projects beyond the Free limit become read-only (not deleted)
```

### US-F08-05: Role Management

```
As a company admin,
I want to invite team members with specific roles,
so that they have appropriate access levels.

Acceptance Criteria:
  1. GIVEN I am an admin
     WHEN I invite a user by email with role "foreman"
     THEN they receive an invitation email to join my company

  2. GIVEN an invited user accepts the invitation
     THEN they are added to my company with the assigned role

  3. GIVEN I am a foreman
     WHEN I try to access billing or user management endpoints
     THEN I receive a 403 Forbidden response
```

---

## 4. Non-Functional Requirements (Auth & Billing Specific)

| Category | Requirement |
|----------|-------------|
| Security | JWT in httpOnly cookies only. RS256 signing. Crash if JWT_SECRET_KEY missing. |
| Security | Passwords: bcrypt, cost >= 12. Never return hashes in API. |
| Security | Registration endpoint MUST NOT accept role field. |
| Security | YooKassa webhooks: HMAC-SHA256 verification with constant-time comparison. |
| Security | Rate limiting: 5 login attempts / 15 min, then 30 min lockout. |
| Data | All monetary values: Decimal (never Float). |
| Data | Tenant isolation via Odoo company_id on every query. |
| Compliance | 152-FZ: personal data stored in Russia, consent on registration, right to deletion. |
| Performance | Auth endpoints: < 300 ms P95. |
| Availability | Payment webhook processing: at-least-once delivery with idempotency. |

---

## 5. Out of Scope (MVP)

- OAuth2 / social login (Google, VK, Yandex)
- Two-factor authentication (2FA)
- SSO / SAML for enterprise customers
- Marketplace payment splitting
- Invoice-based billing (only card/SBP for MVP)
