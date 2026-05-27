# Refinement: Auth & Billing (F08)

**Feature:** F08 — Auth & Billing
**Version:** 1.0
**Date:** 2026-05-27
**Status:** SPARC Phase 1

---

## 1. Edge Cases & Error Handling

### 1.1 Registration

| Edge Case | Handling |
|-----------|----------|
| Email already exists | Return 409 with generic message (no enumeration leak) |
| Phone already exists | Same 409 generic message |
| Payload contains `role` field | **Silently ignore.** NEVER assign from request. Hardcode `client`. |
| Payload contains `company_id` field | Silently ignore. Always create new company or use invite flow. |
| Very long email (>254 chars) | Reject with 422 validation error |
| Unicode in password | Allow — bcrypt handles arbitrary bytes. Max 72 bytes after UTF-8 encoding (bcrypt limit). |
| Concurrent registration with same email | Database unique constraint prevents race condition. Second request gets 409. |
| SMS delivery failure | Return 503, suggest email registration. Do not create partial account. |

### 1.2 Authentication

| Edge Case | Handling |
|-----------|----------|
| Account locked (5 failed attempts) | Return 429 with `retry_after` seconds. Do NOT reveal that account exists. |
| User deactivated by admin | Return 403 `ACCOUNT_DEACTIVATED` (only after successful password check). |
| Token issued before role change | Old access token retains old role until expiry (15 min max). Next refresh gets updated role. |
| Clock skew between servers | Allow 30-second leeway in JWT `exp` validation. |
| Multiple concurrent refresh calls | First succeeds, subsequent ones trigger family revocation (theft detection). |
| Browser clears cookies mid-session | User must re-login. No silent re-auth. |

### 1.3 Billing & Payments

| Edge Case | Handling |
|-----------|----------|
| Downgrade with over-limit objects | Existing objects become read-only. No data deletion. User notified. |
| Upgrade during trial | Trial ends immediately, paid period starts. No double-charging. |
| Payment succeeds but webhook delayed | Polling endpoint `GET /billing/subscription` returns `pending` until webhook arrives. |
| ЮKassa timeout on payment creation | Return 503 to user. Do NOT create subscription record until payment confirmed. |
| Currency mismatch in webhook | Log error, do NOT process. Alert operations team. |
| Webhook received for unknown subscription | Log error, return 200 (prevent ЮKassa retries for unknown entities). |
| User cancels then re-subscribes same day | New subscription created. Old one remains `canceled`. |
| Decimal precision loss | Use `Decimal` with 2 decimal places. **NEVER cast to float.** |
| Plan price change for existing subscribers | Existing subscribers keep old price until renewal. Price change applies on next cycle. |

### 1.4 Multi-Tenancy

| Edge Case | Handling |
|-----------|----------|
| User tries to access another company's data | `ir.rule` blocks at ORM level. Even if API has a bug, DB returns empty set. |
| Admin removes themselves | Prevent: at least 1 admin must exist per company. Return 422. |
| Last admin leaves company | Block operation. Require transferring admin role first. |
| Company with expired subscription but active users | Users can still log in but see "subscription expired" banner. Read-only mode. |

---

## 2. Testing Strategy

### 2.1 Unit Tests

| Module | Test Area | Cases |
|--------|-----------|:-----:|
| `su_auth` | Password hashing | bcrypt cost factor, max length, unicode |
| `su_auth` | JWT generation | RS256 signing, claims, expiry |
| `su_auth` | Token rotation | Family tracking, reuse detection |
| `su_auth` | Rate limiting | Counter increment, window reset, lockout |
| `su_billing` | Plan limits | Object count, AI estimate count, user count |
| `su_billing` | Trial logic | Start, expiry, reminder scheduling |
| `su_billing` | Prorated billing | Upgrade mid-cycle, downgrade at end |
| `su_payment` | HMAC verification | Valid sig, invalid sig, missing sig, tampered body |
| `su_payment` | Idempotency | Duplicate webhook, expired key |
| `su_payment` | Amount handling | Decimal precision, no float conversion |

### 2.2 Integration Tests

| Test | Description |
|------|-------------|
| Full registration flow | Register -> confirm email -> login -> get profile |
| Token lifecycle | Login -> access API -> expire -> refresh -> access API -> logout |
| Payment flow | Create subscription -> ЮKassa payment -> webhook -> verify status |
| Trial expiration | Create trial -> advance time 14 days -> verify downgrade |
| Plan upgrade | Start Starter -> pay for Business -> verify limits updated |
| Plan downgrade | Start Business (15 objects) -> downgrade Starter -> verify objects frozen |

### 2.3 Security Tests (CRITICAL)

| Test ID | Attack Vector | Test Description | Expected Result |
|---------|--------------|-------------------|-----------------|
| SEC-01 | **Role escalation via register** | `POST /auth/register` with `{"role": "admin"}` in body | Role field ignored, user created as `client` |
| SEC-02 | **Role escalation via profile update** | `PUT /users/me` with `{"role": "admin"}` | Role field ignored or 403 |
| SEC-03 | **Cross-tenant access** | Authenticated user A requests `/users` of company B | Empty list (ir.rule) or 403 |
| SEC-04 | **IDOR on user management** | Manager tries `PUT /users/{admin_id}/role` | 403 (only admin can change roles) |
| SEC-05 | **JWT in localStorage check** | Verify no endpoint returns tokens in response body | Tokens only in Set-Cookie headers |
| SEC-06 | **Hardcoded secret detection** | Grep codebase for fallback patterns like `os.getenv("JWT_SECRET_KEY", "default")` | Zero matches |
| SEC-07 | **Webhook without HMAC** | `POST /webhooks/yukassa` without signature header | 403 |
| SEC-08 | **Webhook with invalid HMAC** | `POST /webhooks/yukassa` with wrong signature | 403 |
| SEC-09 | **Webhook replay** | Send valid webhook with timestamp > 5 min old | 403 |
| SEC-10 | **Timing attack on HMAC** | Measure response time variance for different incorrect signatures | Constant time (hmac.compare_digest) |
| SEC-11 | **Refresh token reuse** | Use the same refresh token twice | 401, entire family revoked |
| SEC-12 | **Brute force login** | Send 6 login attempts in 15 min | 5th succeeds/fails normally, 6th gets 429 |
| SEC-13 | **SQL injection** | Malicious input in email/password fields | Parameterized queries, no injection |
| SEC-14 | **Startup without secrets** | Remove JWT_SECRET_KEY from env | Application crashes, does NOT start |
| SEC-15 | **Float for money** | Verify all payment amounts use Decimal | No float anywhere in payment pipeline |
| SEC-16 | **Email enumeration** | Register existing email, note error message | Generic error, same response time |

### 2.4 Load Tests

| Scenario | Target | Tool |
|----------|--------|------|
| Login endpoint | 100 req/sec, P95 < 300ms | k6 / Locust |
| Token refresh | 200 req/sec, P95 < 100ms | k6 / Locust |
| Webhook processing | 50 req/sec, P95 < 500ms | k6 / Locust |
| Registration (with bcrypt) | 20 req/sec, P95 < 1s | k6 / Locust |

### 2.5 Test Data Strategy

| Entity | Test Data |
|--------|-----------|
| Users | 5 users per role per tenant, 3 tenants |
| Subscriptions | One per plan type, plus trial and expired states |
| Payments | Succeeded, failed, refunded, pending |
| Refresh tokens | Active, used, revoked, expired |

---

## 3. Performance Considerations

### 3.1 Database Indexes

```sql
-- High-frequency lookups
CREATE UNIQUE INDEX idx_users_email ON res_users(email) WHERE email IS NOT NULL;
CREATE UNIQUE INDEX idx_users_phone ON res_users(phone) WHERE phone IS NOT NULL;
CREATE INDEX idx_refresh_token_hash ON su_refresh_token(token_hash);
CREATE INDEX idx_refresh_token_family ON su_refresh_token(family_id);
CREATE INDEX idx_subscription_company ON su_subscription(company_id);
CREATE INDEX idx_subscription_status ON su_subscription(status);
CREATE INDEX idx_subscription_trial_ends ON su_subscription(trial_ends_at)
    WHERE status = 'trialing';
CREATE INDEX idx_payment_yukassa_id ON su_payment(yukassa_payment_id);
CREATE INDEX idx_payment_idempotency ON su_payment(idempotency_key);
CREATE INDEX idx_audit_log_created ON su_audit_log(created_at);
CREATE INDEX idx_audit_log_user ON su_audit_log(user_id, created_at);
```

### 3.2 Caching

| Data | Cache Location | TTL | Invalidation |
|------|:-------------:|:---:|:------------:|
| Plan limits | Redis | 1 hour | On plan change |
| User role | JWT claims | 15 min | On token refresh |
| Rate limit counters | Redis | Sliding window | Auto-expire |
| Token blacklist | Redis | Token remaining TTL | Auto-expire |

### 3.3 bcrypt Performance

bcrypt with cost factor 12 takes ~250ms per hash. Mitigations:
- Rate limit registration (3/hour/IP) — prevents DoS via hash computation
- Run hash verification in thread pool (Odoo's threaded worker model handles this)
- Do NOT reduce cost factor below 12 for "performance" — it weakens security

---

## 4. Observability

### 4.1 Metrics (Prometheus)

| Metric | Type | Labels |
|--------|------|--------|
| `su_auth_login_total` | Counter | status={success,failed,locked} |
| `su_auth_registration_total` | Counter | status={success,conflict,error} |
| `su_auth_token_refresh_total` | Counter | status={success,expired,revoked,reuse_detected} |
| `su_billing_trial_expired_total` | Counter | - |
| `su_billing_plan_change_total` | Counter | from_plan, to_plan |
| `su_payment_webhook_total` | Counter | event_type, status={processed,invalid_sig,replay,duplicate} |
| `su_payment_amount_total` | Counter | plan, currency |
| `su_auth_bcrypt_duration_seconds` | Histogram | - |

### 4.2 Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| High login failure rate | > 50 failures/min | Warning |
| HMAC verification failure | Any occurrence | Critical |
| Cross-tenant attempt | Any occurrence | Critical |
| Refresh token reuse | Any occurrence | Critical |
| Payment webhook failure | > 5 failures/hour | Warning |
| bcrypt latency | P95 > 500ms | Warning |

---

## 5. Migration & Rollback Plan

### 5.1 Database Migrations

| Order | Migration | Reversible |
|:-----:|-----------|:----------:|
| 1 | Extend `res.users` with `su_*` fields | Yes (drop columns) |
| 2 | Create `su.refresh.token` table | Yes (drop table) |
| 3 | Create `su.subscription` table | Yes (drop table) |
| 4 | Create `su.payment` table | Yes (drop table) |
| 5 | Create `su.audit.log` table | Yes (drop table) |
| 6 | Seed plan data (4 plans) | Yes (delete records) |
| 7 | Create `ir.rule` records for tenant isolation | Yes (delete rules) |
| 8 | Create indexes | Yes (drop indexes) |

### 5.2 Rollback Triggers

- Any security test (SEC-01 through SEC-16) fails
- HMAC verification not working in staging
- Token rotation causes session drops > 1% of requests
- Payment webhook processing time > 2 seconds P95
