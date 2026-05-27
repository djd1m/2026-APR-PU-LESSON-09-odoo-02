# Requirements Validation Report: Auth & Billing (F08)

**Feature:** F08 — Auth & Billing
**Validator:** requirements-validator (INVEST + SMART + Security)
**Date:** 2026-05-27
**SPARC Docs Analyzed:** 01_specification, 02_pseudocode, 03_architecture, 04_refinement, 05_completion

---

## Summary

- **Stories analyzed:** 5
- **Average score:** 88/100
- **Blocked:** 0 (score < 50)
- **Verdict:** READY (average >= 70, no blockers)

---

## Results

| Story | Title | INVEST | SMART | Security | Score | Status |
|-------|-------|:------:|:-----:|:--------:|:-----:|:------:|
| US-F08-01 | Registration | 6/6 | 5/5 | +5 | 92/100 | READY |
| US-F08-02 | Login | 6/6 | 5/5 | +5 | 93/100 | READY |
| US-F08-03 | Subscription Management | 5/6 | 4/5 | +5 | 83/100 | READY |
| US-F08-04 | Trial Expiration | 6/6 | 5/5 | +0 | 87/100 | READY |
| US-F08-05 | Role Management | 5/6 | 4/5 | +5 | 85/100 | READY |

---

## Detailed Analysis

### US-F08-01: Registration (92/100) — READY

**INVEST Analysis**

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Independent | Y | No dependency on other stories for implementation |
| Negotiable | Y | Implementation details flexible (email-first vs phone-first) |
| Valuable | Y | Clear user benefit: "start managing my projects" |
| Estimable | Y | Well-defined scope: form, validation, tenant creation, trial |
| Small | Y | One sprint deliverable |
| Testable | Y | 5 concrete acceptance criteria with GIVEN/WHEN/THEN |

**SMART Analysis**

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Specific | Y | Exact fields, password rules (>=8 chars, 1 uppercase, 1 digit) |
| Measurable | Y | Password complexity quantified, TTL values (24h confirmation) |
| Achievable | Y | Standard registration flow on Odoo stack |
| Relevant | Y | Core user onboarding path |
| Time-bound | Y | Confirmation email TTL 24h, trial 14 days |

**Security Check**

| Criterion | Status | Evidence |
|-----------|:------:|----------|
| Role escalation protection | PASS | AC#4 explicitly: server IGNORES role field. FR-AB-04 says "Role is NEVER accepted from the registration request body." Pseudocode line 49: `role="admin"` hardcoded. |
| Input validation | PASS | FR-AB-03 defines exact constraints. Pseudocode Section 1 validates all inputs. |
| 152-FZ consent | PASS | FR-AB-06 requires consent. AC#5 verifies. Pseudocode stores timestamp + version. |
| Duplicate prevention | PASS | FR-AB-07 + unique DB constraints + 409 response. |

**Minor finding (medium):** Refinement doc (Section 1.1) says default role is `client`, but Specification FR-AB-04 says `admin` (company owner). Pseudocode also uses `admin`. The Refinement doc is inconsistent. This is not a blocker since the Specification and Pseudocode agree, but the Refinement doc should be corrected.

---

### US-F08-02: Login (93/100) — READY

**INVEST Analysis**

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Independent | Y | Can be developed after registration exists |
| Negotiable | Y | Cookie handling approach flexible |
| Valuable | Y | "access my projects securely" |
| Estimable | Y | Clear JWT flow with specific TTLs |
| Small | Y | Single sprint |
| Testable | Y | 4 acceptance criteria, specific thresholds |

**SMART Analysis**

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Specific | Y | "JWT access token (15 min) and refresh token (7 days) in httpOnly cookies" |
| Measurable | Y | 5 attempts / 15 min threshold, 30 min lockout |
| Achievable | Y | Standard JWT + Redis pattern |
| Relevant | Y | Core authentication |
| Time-bound | Y | All TTLs specified: 15 min access, 7 day refresh, 30 min lockout |

**Security Check**

| Criterion | Status | Evidence |
|-----------|:------:|----------|
| JWT httpOnly (not localStorage) | PASS | FR-AB-11: "NEVER in localStorage/sessionStorage." AC#1: "in httpOnly cookies." Pseudocode sets cookies with `httpOnly=true, secure=true, sameSite="Strict"`. Architecture Section 4.1 confirms cookie flow. SEC-05 test verifies. |
| No hardcoded secret fallbacks | PASS | FR-AB-12: "application MUST crash on startup if missing. No hardcoded fallbacks." Pseudocode Section 8: explicit crash with `sys.exit(1)`. Completion Section 2.1: `CRASH IF MISSING` table. SEC-06 + SEC-14 test. |
| RS256 signing | PASS | FR-AB-12 specifies RS256. Pseudocode `jwt.encode(..., algorithm="RS256")`. |
| Brute-force protection | PASS | FR-AB-15: 5 attempts/15 min, 30 min lockout. Pseudocode Section 10. SEC-12 test. |
| Refresh token rotation | PASS | FR-AB-13: single-use. Pseudocode Section 4: reuse triggers family revocation. SEC-11 test. |

---

### US-F08-03: Subscription Management (83/100) — READY

**INVEST Analysis**

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Independent | Y | Depends on auth (expected) |
| Negotiable | Y | Payment flow details flexible |
| Valuable | Y | "unlock features for my team" |
| Estimable | Y | Well-scoped: 4 plan tiers, prorated billing |
| Small | N | YooKassa integration + prorated billing + webhooks is large for one sprint. Consider splitting payment processing from plan management. |
| Testable | Y | 4 acceptance criteria with specific flows |

**SMART Analysis**

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Specific | Y | Exact plan names, pricing, upgrade/downgrade behavior |
| Measurable | Y | Retry intervals (1, 3, 7 days), prorated amounts |
| Achievable | Y | YooKassa has good API/SDK support |
| Relevant | Y | Revenue-critical |
| Time-bound | N | AC#3 says "change takes effect at end of billing cycle" but no exact timing for proration calculation. FR-AB-44 clarifies. Minor. |

**Security Check**

| Criterion | Status | Evidence |
|-----------|:------:|----------|
| HMAC on YooKassa webhooks | PASS | FR-AB-42: "HMAC-SHA256 signature verification required. Constant-time comparison." Pseudocode Section 6: full HMAC flow with `hmac_sha256()` + `constant_time_compare()` + replay protection (5 min window). Architecture Section 4.3 reconfirms. SEC-07/08/09/10 tests. |
| Decimal for money | PASS | FR-AB-42/Section 2.4: "All monetary values stored as Decimal... NEVER float." Pseudocode `Decimal(payment.amount.value)`. Architecture: `fields.Monetary` (Decimal). SEC-15 test. Completion pre-deploy check: grep for `float(`. |
| Idempotency | PASS | FR-AB-43: dedup by `idempotency_key`. Pseudocode + webhook_log table. |
| Webhook secret from env | PASS | Pseudocode Section 8: `YUKASSA_WEBHOOK_SECRET` in required secrets list. |

---

### US-F08-04: Trial Expiration (87/100) — READY

**INVEST Analysis**

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Independent | Y | Self-contained cron logic |
| Negotiable | Y | Reminder timing negotiable |
| Valuable | Y | "decide whether to subscribe" |
| Estimable | Y | Cron job + email templates |
| Small | Y | Focused scope |
| Testable | Y | 3 clear acceptance criteria with specific day counts |

**SMART Analysis**

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Specific | Y | 14 days, reminders at 7/3/1 days, downgrade to Free |
| Measurable | Y | Exact day counts, banner with "remaining days" |
| Achievable | Y | Standard cron + email |
| Relevant | Y | Conversion funnel, retention |
| Time-bound | Y | All timings explicit |

**Security Check:** Not security-relevant. Score +0 (neutral).

---

### US-F08-05: Role Management (85/100) — READY

**INVEST Analysis**

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Independent | Y | Builds on auth, independent of billing |
| Negotiable | Y | Invitation mechanism flexible |
| Valuable | Y | "appropriate access levels" |
| Estimable | Y | RBAC matrix clearly defined |
| Small | N | Invitation flow + role assignment + RBAC enforcement is borderline for one sprint |
| Testable | Y | 3 acceptance criteria, specific 403 response |

**SMART Analysis**

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Specific | Y | 4 roles defined with permission matrix (Section 2.3) |
| Measurable | Y | 403 response code specified |
| Achievable | Y | Odoo ir.rule + decorator pattern |
| Relevant | Y | Multi-tenant access control |
| Time-bound | N | No invitation expiry specified. Should define: invitation link TTL (suggest 7 days). |

**Security Check**

| Criterion | Status | Evidence |
|-----------|:------:|----------|
| Authorization enforcement | PASS | RBAC checked on every endpoint via decorator. Specification: "Client-side role claims are NEVER trusted." Pseudocode Section 3 line 163: role from DB, not token. |
| Tenant isolation | PASS | `company_id` in every query. Odoo `ir.rule`. PostgreSQL RLS as defense-in-depth. SEC-03 test. |
| IDOR prevention | PASS | Specification: "Object ownership verified before update/delete." SEC-04 test. |

---

## Cross-Document Coherence

| Check | Status | Details |
|-------|:------:|---------|
| Spec <-> Pseudocode alignment | WARN | Default role: Spec says `admin` (FR-AB-04), Pseudocode says `admin` (line 49), Refinement says `client` (Section 1.1 row 3), Completion says `client` (Section 6). **Inconsistency between docs.** See finding below. |
| Pseudocode <-> Architecture alignment | PASS | All models, endpoints, and flows match. Data types consistent. |
| Architecture <-> Refinement alignment | PASS | Test strategy covers all architectural components. Edge cases address all integration points. |
| Refinement <-> Completion alignment | PASS | SEC tests referenced in both. Deployment checklist covers all refinement concerns. |
| NFR coverage | PASS | All NFRs from Specification Section 4 are addressed in implementation docs. |
| Missing endpoint coverage | PASS | All Architecture endpoints have pseudocode. |
| Env var consistency | PASS | Completion env vars match Architecture dependencies and Pseudocode secret validation. |

### Finding: Default Role Inconsistency (severity: medium)

**Problem:** Two different default roles appear across SPARC docs:
- `admin` in 01_specification.md (FR-AB-04) and 02_pseudocode.md (line 49)
- `client` in 04_refinement.md (Section 1.1, edge case for role field in payload) and 05_completion.md (Definition of Done, line 238)

**Impact:** Implementer could use the wrong default role. The Specification is the authoritative source and says `admin` (company owner on self-registration). The Refinement/Completion docs likely confused the registration default with the invitation default (invited users should get `client` or the assigned role).

**Recommendation:** Update 04_refinement.md and 05_completion.md to say `admin` for self-registration default, and clarify that invited users get the role specified by the inviting admin.

---

## Security Findings Summary

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| 1 | Role escalation via register endpoint | Addressed | FR-AB-04 + AC#4 + Pseudocode + SEC-01 test |
| 2 | JWT httpOnly (not localStorage) | Addressed | FR-AB-11 + Pseudocode + SEC-05 test |
| 3 | No hardcoded secret fallbacks | Addressed | FR-AB-12 + Pseudocode Section 8 + SEC-06/14 tests |
| 4 | HMAC on YooKassa webhooks | Addressed | FR-AB-42 + Pseudocode Section 6 + SEC-07/08/09/10 tests |
| 5 | Decimal for money | Addressed | Section 2.4 + Pseudocode + Architecture + SEC-15 test |
| 6 | Default role inconsistency across docs | medium | Fix in refinement + completion docs |
| 7 | Missing invitation link TTL | low | Add to US-F08-05 acceptance criteria |

All 5 critical security checks from the task brief **PASS**. No blockers found.

---

## BDD Scenarios

### Feature: User Registration

```gherkin
Scenario: Successful email registration
  Given I am an unregistered user
  When I submit the registration form with:
    | email    | ivan@example.com     |
    | password | StrongPass1          |
    | full_name| Ivan Petrov          |
    | company  | OOO StroyMir         |
    | pd_consent | true              |
  Then my account is created with role "admin"
  And a new company "OOO StroyMir" is created
  And I am enrolled in a 14-day Business trial
  And I receive a confirmation email
  And my response contains httpOnly cookies with JWT tokens

Scenario: Registration with role field in payload (role escalation attempt)
  Given I am an unregistered user
  When I submit the registration form with:
    | email    | attacker@example.com |
    | password | StrongPass1          |
    | full_name| Attacker             |
    | company  | Evil Corp            |
    | role     | superadmin           |
    | pd_consent | true              |
  Then my account is created with role "admin"
  And the "role" field from the request is ignored

Scenario: Registration with duplicate email
  Given a user with email "existing@example.com" already exists
  When I submit the registration form with email "existing@example.com"
  Then I receive a 409 response with message "Email already registered"

Scenario: Registration without 152-FZ consent
  Given I am an unregistered user
  When I submit the registration form with pd_consent=false
  Then I receive a 422 validation error

Scenario: Registration with weak password
  Given I am an unregistered user
  When I submit the registration form with password "weak"
  Then I receive a 422 validation error mentioning password requirements
```

### Feature: User Login

```gherkin
Scenario: Successful login
  Given I am a registered user with email "user@example.com"
  When I submit valid credentials
  Then I receive httpOnly cookies containing access_token (15 min TTL) and refresh_token (7 day TTL)
  And no tokens appear in the response body

Scenario: Brute force protection
  Given I am a registered user
  When I submit 5 incorrect passwords within 15 minutes
  Then my account is locked for 30 minutes
  And I receive a notification email
  And the 6th attempt returns 429 with retry_after header

Scenario: Token refresh
  Given my access_token has expired
  And my refresh_token is still valid
  When my browser sends a request with the refresh cookie
  Then a new access_token and refresh_token are issued in httpOnly cookies
  And the old refresh_token is invalidated

Scenario: Refresh token reuse detection (theft)
  Given I have a valid refresh_token
  And the refresh_token has already been used once
  When I attempt to use the same refresh_token again
  Then I receive a 401 response
  And all sessions for my device are revoked

Scenario: Logout
  Given I am logged in
  When I click "Logout"
  Then both cookies are cleared
  And the refresh_token is invalidated server-side

Scenario: JWT in localStorage check
  Given I am using the application
  When I inspect localStorage and sessionStorage
  Then no JWT tokens are stored there
```

### Feature: Subscription Management

```gherkin
Scenario: Upgrade from Free to Starter
  Given I am on the Free plan
  When I select the Starter plan and enter my card details
  Then YooKassa processes a payment of 2990 RUB (Decimal, not float)
  And my plan upgrades to Starter immediately
  And my object limit increases to 5

Scenario: Mid-cycle upgrade with proration
  Given I am on Starter plan, 15 days into a 30-day cycle
  When I upgrade to Business plan
  Then I am charged the prorated difference: (9900-2990) * 15/30 = 3455 RUB
  And all amounts are calculated using Decimal arithmetic

Scenario: Downgrade at end of cycle
  Given I am on Business plan
  When I downgrade to Starter
  Then the change takes effect at the end of my current billing cycle
  And I retain Business features until then

Scenario: Failed recurring payment retry
  Given my recurring payment has failed
  Then the system retries after 1 day
  And retries again after 3 days if still failing
  And retries again after 7 days if still failing
  And downgrades to Free after the 3rd failure
  And I receive an email notification of the downgrade
```

### Feature: YooKassa Webhook Security

```gherkin
Scenario: Webhook with valid HMAC signature
  Given YooKassa sends a payment.succeeded webhook
  And the X-Yukassa-Signature header contains a valid HMAC-SHA256 signature
  And the event timestamp is within the 5-minute window
  When the webhook endpoint processes the request
  Then the payment is recorded with Decimal amount
  And the subscription status is updated
  And a webhook_log entry is created with the idempotency_key

Scenario: Webhook without HMAC signature
  Given a request is sent to /api/v1/webhooks/yukassa
  And no X-Yukassa-Signature header is present
  When the webhook endpoint receives the request
  Then it returns 400 "Missing signature"

Scenario: Webhook with invalid HMAC signature
  Given a request is sent with a tampered X-Yukassa-Signature header
  When the webhook endpoint processes the request
  Then it returns 403 "Invalid signature"
  And response time is constant regardless of which byte differs (timing-safe)

Scenario: Webhook replay attack
  Given a valid webhook is re-sent with a timestamp older than 5 minutes
  When the webhook endpoint processes the request
  Then it returns 400 "Event too old"

Scenario: Duplicate webhook (idempotency)
  Given a webhook with idempotency_key "abc-123" was already processed
  When the same webhook is sent again
  Then the endpoint returns 200 "Already processed"
  And no duplicate records are created
```

### Feature: Trial Expiration

```gherkin
Scenario: Trial countdown display
  Given I am on a 14-day Business trial with 5 days remaining
  When I view the dashboard
  Then I see a banner showing "5 days remaining in trial"

Scenario: Trial reminder emails
  Given I am on a trial ending in 7 days
  When the reminder cron job runs
  Then I receive an email reminder about my trial expiration

Scenario: Trial expiration with over-limit objects
  Given I am on a trial with 15 active projects
  And my trial expires
  When the trial expiration cron runs
  Then my plan downgrades to Free (1 object limit)
  And 14 projects become read-only
  And the oldest project remains active
  And no projects are deleted

Scenario: Trial abuse prevention
  Given I already used a trial with email "user@example.com"
  When I try to register again with the same email
  Then registration is rejected (duplicate email constraint)
```

### Feature: Role Management

```gherkin
Scenario: Admin invites a foreman
  Given I am logged in as an admin
  When I invite "worker@example.com" with role "foreman"
  Then the user receives an invitation email
  And upon accepting, they join my company as "foreman"

Scenario: Foreman attempts billing access
  Given I am logged in as a foreman
  When I access GET /api/v1/billing/subscription
  Then I receive a 403 Forbidden response

Scenario: Cross-tenant access attempt
  Given I am logged in as admin of Company A
  When I attempt to access users from Company B via API
  Then I receive an empty list (ir.rule tenant isolation)
  And no Company B data is exposed

Scenario: IDOR on user role change
  Given I am logged in as a manager
  When I attempt PATCH /api/v1/users/{admin_id}/role
  Then I receive a 403 Forbidden response
```

---

## Verdict

```
=================================================================
  VERDICT: READY
  Average Score: 88/100
  Blockers: 0
  Security: All 5 critical checks PASS
  Action: Proceed to Phase 3 (IMPLEMENT)
=================================================================
```

**Conditions:**
- Fix default role inconsistency in 04_refinement.md and 05_completion.md before implementation (medium)
- Add invitation link TTL to US-F08-05 acceptance criteria (low)
