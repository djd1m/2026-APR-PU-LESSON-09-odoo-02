# Completion: Auth & Billing (F08)

**Feature:** F08 — Auth & Billing
**Version:** 1.0
**Date:** 2026-05-27
**Status:** SPARC Phase 1

---

## 1. Deployment Checklist

### 1.1 Pre-Deployment

- [ ] All security tests SEC-01 through SEC-16 pass (see 04_refinement.md)
- [ ] Unit test coverage >= 90% for `su_auth`, `su_billing`, `su_payment`
- [ ] Integration tests pass end-to-end (register -> pay -> use -> cancel)
- [ ] Load tests pass at target throughput (see 04_refinement.md)
- [ ] No hardcoded secrets in codebase (`grep -r "fallback\|default.*secret\|getenv.*," --include="*.py"` returns zero matches)
- [ ] No `float` used for monetary values (`grep -r "float(" --include="*.py"` in payment code returns zero matches)
- [ ] No `localStorage` token storage in frontend code
- [ ] ЮKassa sandbox testing complete (all payment methods: card, SBP, ЮMoney)
- [ ] ЮKassa webhook URL configured in merchant dashboard
- [ ] HMAC webhook secret configured in ЮKassa dashboard and env vars
- [ ] RSA key pair generated for JWT (RS256) and stored securely
- [ ] SMTP configured and tested (confirmation emails, password reset, trial reminders)
- [ ] SMS gateway configured and tested (if phone registration enabled)
- [ ] Redis deployed and accessible from Odoo containers
- [ ] Odoo ir.rule records validated (no cross-tenant data leaks in staging)

### 1.2 Deployment Steps

```
1. Apply database migrations (Odoo module install/upgrade)
   $ docker compose exec odoo odoo -d stroyuprav -i su_auth,su_billing,su_payment --stop-after-init

2. Verify startup with required env vars
   $ docker compose up -d
   $ docker compose logs odoo | grep "Missing required secrets"
   # Should show NOTHING — if secrets are set correctly

3. Verify startup failure without secrets
   $ UNSET JWT_SECRET_KEY && docker compose up odoo
   # MUST exit with code 1

4. Seed plan data
   # Handled by su_billing/data/plans.xml on module install

5. Run smoke tests
   $ python -m pytest tests/smoke/ -v

6. Verify webhook endpoint is reachable
   $ curl -X POST https://app.stroyuprav.ru/api/v1/webhooks/yukassa \
       -H "Content-Type: application/json" -d '{}'
   # Should return 403 (no HMAC header)
```

### 1.3 Post-Deployment Verification

- [ ] Registration creates user + company + trial subscription
- [ ] Login returns httpOnly cookies (verify via browser DevTools → Application → Cookies)
- [ ] Access token expires after 15 minutes (test with delayed request)
- [ ] Refresh token rotation works (old token invalidated)
- [ ] Role escalation test: `POST /auth/register {"role":"admin"}` → user.role == "client"
- [ ] Cross-tenant test: user A cannot see user B's data
- [ ] ЮKassa test payment succeeds in production mode
- [ ] Webhook updates subscription status correctly
- [ ] Trial cron job runs at scheduled time
- [ ] Metrics appear in Prometheus
- [ ] Audit logs are being written

---

## 2. Environment Variables

### 2.1 Required (CRASH IF MISSING)

| Variable | Example | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | `-----BEGIN RSA PRIVATE KEY-----...` | RSA private key (PEM), min 2048-bit |
| `JWT_PUBLIC_KEY` | `-----BEGIN PUBLIC KEY-----...` | RSA public key (PEM) |
| `YUKASSA_SHOP_ID` | `123456` | ЮKassa merchant shop ID |
| `YUKASSA_SECRET_KEY` | `test_...` / `live_...` | ЮKassa API secret key |
| `YUKASSA_WEBHOOK_SECRET` | `whsec_...` | HMAC key for webhook verification |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `DATABASE_URL` | `postgresql://odoo:pass@db:5432/stroyuprav` | PostgreSQL (Odoo uses db_host/db_port params) |

### 2.2 Required (Functional)

| Variable | Example | Description |
|----------|---------|-------------|
| `SMTP_HOST` | `smtp.yandex.ru` | SMTP server for emails |
| `SMTP_PORT` | `465` | SMTP port |
| `SMTP_USER` | `noreply@stroyuprav.ru` | SMTP username |
| `SMTP_PASSWORD` | `...` | SMTP password |
| `SMS_API_KEY` | `...` | SMS.ru API key |
| `BASE_URL` | `https://app.stroyuprav.ru` | Application base URL |

### 2.3 Optional (with safe defaults)

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_ACCESS_TTL` | `900` (15 min) | Access token TTL in seconds |
| `JWT_REFRESH_TTL` | `604800` (7 days) | Refresh token TTL in seconds |
| `BCRYPT_COST_FACTOR` | `12` | bcrypt hash cost (minimum 12) |
| `RATE_LIMIT_LOGIN` | `5/15m` | Login rate limit |
| `RATE_LIMIT_REGISTER` | `3/1h` | Registration rate limit |
| `TRIAL_DURATION_DAYS` | `14` | Trial period in days |
| `WEBHOOK_TIMESTAMP_WINDOW` | `300` (5 min) | Max age for webhook timestamps |

**Note:** Optional defaults are NOT secrets. They are operational parameters with safe values. The "no fallback" rule applies ONLY to secrets (keys, passwords, tokens).

---

## 3. Monitoring & Alerting

### 3.1 Health Checks

```python
# /api/v1/health — unauthenticated
{
    "status": "healthy",
    "checks": {
        "database": "ok",       # SELECT 1
        "redis": "ok",          # PING
        "yukassa": "ok",        # GET /v3/me (cached, 5 min)
        "smtp": "ok"            # EHLO check (cached, 15 min)
    },
    "version": "1.0.0",
    "uptime_seconds": 86400
}
```

### 3.2 Dashboards (Grafana)

| Dashboard | Panels |
|-----------|--------|
| **Auth Overview** | Login rate, failure rate, registration rate, active sessions |
| **Token Lifecycle** | Refresh rate, revocations, family revocations (theft detection) |
| **Billing** | Active subscriptions by plan, trial conversions, churn |
| **Payments** | Payment volume (RUB), success rate, retry rate, webhook latency |
| **Security** | Failed HMAC, cross-tenant attempts, brute force detections |

### 3.3 Alert Rules

| Alert | Condition | Channel | Severity |
|-------|-----------|---------|----------|
| Auth service down | Health check fails 3x consecutive | Telegram + Email | P0 |
| HMAC verification failure | Any occurrence | Telegram | P0 |
| Cross-tenant access attempt | Any occurrence | Telegram | P0 |
| Refresh token reuse (theft) | Any occurrence | Telegram | P1 |
| Login failure spike | > 100 failures in 5 min | Telegram | P1 |
| Payment webhook errors | > 5 failures/hour | Email | P1 |
| Trial expiration cron failed | Cron missed scheduled run | Email | P2 |
| Subscription without payment | Active sub, no payment in 35 days | Email | P2 |

---

## 4. Database Migration Plan

### 4.1 Migration Sequence

Odoo handles migrations through module install/upgrade. Modules must be installed in dependency order:

```
1. su_auth       (no dependencies beyond base)
2. su_billing    (depends: su_auth)
3. su_payment    (depends: su_billing)
```

### 4.2 Seed Data

Plan definitions seeded via `su_billing/data/plans.xml`:

```xml
<record id="plan_free" model="su.plan">
    <field name="name">free</field>
    <field name="display_name">Free</field>
    <field name="price">0</field>
    <field name="objects_limit">1</field>
    <field name="ai_estimates_limit">3</field>
    <field name="users_limit">2</field>
    <field name="ks_documents">False</field>
</record>
<!-- starter, business, enterprise similarly -->
```

### 4.3 Rollback Procedure

```
1. Stop Odoo
   $ docker compose stop odoo

2. Uninstall modules (reverse order)
   $ docker compose exec odoo odoo -d stroyuprav \
       --uninstall su_payment,su_billing,su_auth --stop-after-init

3. Verify tables dropped
   $ docker compose exec db psql -U odoo -d stroyuprav \
       -c "\dt su_*"
   # Should return: "Did not find any relations"

4. Restart Odoo
   $ docker compose up -d odoo
```

---

## 5. Operational Runbook

### 5.1 Common Operations

| Operation | Command |
|-----------|---------|
| Force-expire a trial | `UPDATE su_subscription SET trial_ends_at = NOW() WHERE company_id = X;` then run cron |
| Revoke all user sessions | Delete refresh tokens + blacklist current access token in Redis |
| Emergency disable ЮKassa webhooks | Set `YUKASSA_WEBHOOK_ENABLED=false` env var, restart |
| Reset user password (admin) | Via Odoo admin panel or `user.write({'password': new_hash})` |
| Check subscription status | `SELECT plan, status, trial_ends_at FROM su_subscription WHERE company_id = X;` |

### 5.2 Incident Response

| Scenario | Steps |
|----------|-------|
| Suspected token theft | 1. Identify user 2. Revoke all refresh token families 3. Blacklist current access tokens in Redis 4. Force password reset 5. Audit log review |
| ЮKassa webhook flood | 1. Check rate limiting at Nginx level 2. Verify HMAC on all requests 3. If legitimate, scale webhook workers 4. If attack, block source IP at Nginx |
| Database connection exhaustion | 1. Check PgBouncer pool status 2. Kill idle connections 3. Review slow queries 4. Scale connection pool if needed |

---

## 6. Definition of Done

- [ ] All 5 SPARC documents complete (01-05)
- [ ] Three Odoo modules created: `su_auth`, `su_billing`, `su_payment`
- [ ] Registration flow: email + password, phone + SMS
- [ ] JWT in httpOnly cookies, RS256, 15 min access / 7 day refresh
- [ ] Refresh token rotation with theft detection (family revocation)
- [ ] RBAC: admin/manager/foreman/client with ir.rule tenant isolation
- [ ] **Registration NEVER accepts role field** — hardcoded to `client`
- [ ] **Startup crashes if JWT_SECRET_KEY missing** — no fallbacks
- [ ] 4 subscription plans with limits enforced at API level
- [ ] 14-day Business trial with auto-downgrade
- [ ] ЮKassa integration: cards, SBP, recurring payments
- [ ] **HMAC-SHA256 webhook verification** with constant-time comparison
- [ ] **Decimal for all money** — no float anywhere in payment pipeline
- [ ] Failed payment retry (Day 1, 3, 7) with auto-downgrade
- [ ] Audit logging for all auth and payment events
- [ ] Security tests SEC-01 through SEC-16 pass
- [ ] Unit + integration test coverage >= 90%
- [ ] Load tests pass at target throughput
- [ ] Monitoring: metrics, dashboards, alerts configured
- [ ] Documentation: API docs, env var reference, runbook
