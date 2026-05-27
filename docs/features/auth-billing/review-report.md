# Review Report: auth-billing

## Verdict: NEEDS FIX

## Summary

The auth-billing implementation gets the headline security items right (role
hardcoding, httpOnly cookies, no JWT secret fallback, HMAC webhook verification
with constant-time comparison, Monetary fields for money). However, there are
**two blockers** and multiple high-severity gaps. The spec calls for RS256 but
HS256 is used, the YooKassa webhook secret silently defaults to empty string
instead of crashing, and roughly 40% of the P0 specification requirements are
completely unimplemented (rate limiting, phone registration, email confirmation,
password reset, 152-FZ consent, refresh token invalidation, prorated billing).

---

## Findings

### Blocker

1. **YUKASSA_WEBHOOK_SECRET defaults to empty string instead of crashing**
   - **File:** `controllers/webhook.py:25`
   - **Code:** `YUKASSA_WEBHOOK_SECRET = os.environ.get('YUKASSA_WEBHOOK_SECRET', '')`
   - The JWT secret correctly crashes on missing env var (auth.py:31-38). The
     webhook secret uses a silent empty-string fallback. Yes, line 69-71 checks
     at runtime and returns 500 -- but the app STARTS without it. A developer
     could deploy to production, never notice the missing secret, and every
     single webhook would silently fail with a 500. This is inconsistent with
     the security rules which state: "Crash on startup if required secrets are
     missing" and "NEVER add convenience fallback values for missing secrets."
   - **Fix:** Mirror the JWT pattern -- `raise RuntimeError` if missing at
     module load time.

2. **Spec requires RS256, implementation uses HS256**
   - **File:** `controllers/auth.py:43` -- `JWT_ALGORITHM = 'HS256'`
   - **Spec:** FR-AB-12 explicitly says "RS256 algorithm. Key rotation every
     90 days." Security rules say the same.
   - HS256 uses a shared symmetric secret. RS256 uses an asymmetric keypair
     where the verification key can be public. This is not a cosmetic
     difference -- it changes the entire key management model. With HS256, every
     service that needs to verify tokens must have the secret, expanding the
     attack surface.
   - The code comment on line 97 acknowledges this ("For production RS256, swap
     to python-jose...") but ships HS256 anyway with no tracking issue or TODO.
   - **Fix:** Implement RS256 with `python-jose` or `PyJWT[cryptography]`, or
     formally amend the spec to accept HS256 with documented risk acceptance.

### High

3. **No rate limiting on auth endpoints**
   - **Spec:** FR-AB-15 (P0) -- "Max 5 failed login attempts per 15 min per
     IP/account. After threshold: 30 min lockout + email/SMS notification."
   - Security rules: "Rate limit auth endpoints (5 attempts / 15 min per IP)."
   - **Implementation:** Zero rate limiting. No failed attempt counter, no
     lockout, no notification. The login endpoint is wide open to brute-force.
   - **Severity:** HIGH because it is P0 in spec and explicitly called out in
     security rules.

4. **Refresh token rotation is not actually single-use**
   - **Spec:** FR-AB-13 (P0) -- "Refresh tokens are single-use. On refresh,
     old token is invalidated."
   - **Spec:** FR-AB-14 (P0) -- "Invalidate refresh token server-side (Redis
     blacklist or DB deletion)."
   - **Implementation:** `auth.py:413-463` -- The refresh endpoint issues new
     tokens but NEVER invalidates the old refresh token. There is no token
     blacklist, no DB tracking of issued tokens, no Redis. The old refresh
     token remains valid until its natural expiry (7 days). This means a stolen
     refresh token can be reused indefinitely within its TTL window.
   - **Fix:** Implement a `su.refresh.token` model or Redis-based blacklist.
     On each refresh, record the old token's `jti` as revoked.

5. **Phone registration completely missing (P0)**
   - **Spec:** FR-AB-02 (P0) -- "User registers with phone number + SMS code."
   - **Implementation:** Not implemented. No phone field, no SMS integration,
     no code verification.
   - This is a P0 requirement marked as mandatory in the spec.

6. **Email confirmation not implemented (P0)**
   - **Spec:** FR-AB-01 (P0) -- "Email confirmation link sent (TTL 24h)."
   - **Implementation:** Registration creates the user immediately with no
     email verification. No confirmation token, no verification endpoint.

7. **Password reset flow missing (P0)**
   - **Spec:** FR-AB-16 (P0) -- "Forgot password flow: email/SMS with reset
     link/code (TTL 1h, single-use). New password must differ from previous 3."
   - **Implementation:** Not implemented at all.

8. **152-FZ consent not captured (P0)**
   - **Spec:** FR-AB-06 (P0) -- "User must accept personal data processing
     agreement during registration. Timestamp and version stored in DB."
   - **Implementation:** No consent field in registration, no DB storage of
     consent timestamp/version. This is a legal compliance requirement under
     Russian federal law.

9. **Prorated billing not implemented (P0)**
   - **Spec:** FR-AB-44 (P0) -- "Plan change with prorated billing. Upgrade:
     charge difference immediately."
   - **Implementation:** `action_upgrade()` in su_subscription.py just updates
     the plan fields with no proration calculation, no payment trigger, no
     credit tracking.

10. **Failed payment retry logic incomplete (P0)**
    - **Spec:** FR-AB-46 (P0) -- "Retry after 1, 3, 7 days. After 3 failures:
      downgrade to Free."
    - **Implementation:** The `retry_count` and `next_retry_date` fields exist
      on `su.subscription`, but there is no cron job to execute retries, no
      logic to schedule the 1/3/7-day intervals, and no auto-downgrade after 3
      failures. The webhook handler sets `past_due` on cancel but never
      triggers retry scheduling.

### Medium

11. **Registration assigns role `foreman` instead of spec's `admin`**
    - **Spec:** FR-AB-04 -- "Default role on registration: `admin` (company
      owner)."
    - **Implementation:** auth.py:295 assigns `group_su_foreman`.
    - The person registering is the company owner. They should be admin, not
      foreman. A foreman cannot manage billing, users, or company settings.
      This is a functional correctness issue -- the company owner is locked
      out of admin features from day one.
    - The auth.py docstring (line 6) and tests both assert foreman is correct,
      which means this was an intentional but wrong decision that contradicts
      the spec.

12. **`datetime.utcnow()` is deprecated in Python 3.12+**
    - **File:** `controllers/auth.py:105,166`
    - `datetime.utcnow()` is deprecated since Python 3.12. Use
      `datetime.now(datetime.UTC)` instead. Not a security issue today but
      will emit deprecation warnings and eventually break.

13. **Login credential verification may not work correctly**
    - **File:** `controllers/auth.py:368`
    - `_check_credentials` is called on the `res.users` model class (via
      `sudo()`), not on the specific user. Depending on Odoo version, this may
      verify credentials for the current session user, not the looked-up user.
      The standard Odoo pattern is `request.session.authenticate(db, email,
      password)`. This needs verification against the target Odoo version.

14. **Trial-once enforcement missing**
    - **Spec:** FR-AB-33 (P0) -- "One trial per email/phone/company. Prevent
      abuse via duplicate registrations."
    - **Implementation:** Duplicate email is blocked (good), but there is no
      check for the same company name, phone, or other re-registration abuse
      vectors.

15. **No `su.webhook.log` cleanup/retention policy**
    - Webhook logs grow indefinitely. No cron job to archive or purge old
      entries. In a system processing recurring payments, this table will grow
      without bound.

### Low

16. **Duplicated `_json_response` / `_json_error` helpers**
    - Both `auth.py` and `webhook.py` define identical `_json_response` and
      `_json_error` functions. Extract to a shared utility module.

17. **Trial reminder cron only logs, does not send emails**
    - `_cron_send_trial_reminders` in su_subscription.py just calls
      `_logger.info`. The comment says "Email sending would be handled by Odoo
      mail module" but no mail template is defined or referenced.

18. **Hand-rolled JWT implementation**
    - The JWT generation/verification is implemented manually with
      `hmac`/`base64` instead of using a battle-tested library (`PyJWT`,
      `python-jose`). While the implementation looks correct, hand-rolled
      crypto is inherently higher risk. Edge cases in base64 padding, JSON
      serialization order, or future algorithm changes become the team's
      responsibility.

19. **Missing `__all__` exports and type hints**
    - No type annotations on any function. No `__all__` in modules. Minor
      code quality issue.

20. **Bcrypt password stored but Odoo's `_check_credentials` used for login**
    - Registration hashes password with bcrypt (line 278) but also passes
      plaintext to `res.users.create({'password': password})` (line 292),
      which means Odoo stores its own hash. The bcrypt hash from line 278 is
      computed but never stored or used -- it's dead code. Login then uses
      Odoo's `_check_credentials`, not the custom bcrypt verify. The
      `_hash_password` and `_verify_password` functions are orphaned.

---

## Security Checklist

| # | Check | Status | Details |
|---|-------|--------|---------|
| 1 | Register ignores role from body | PASS | Role hardcoded to `foreman` (line 294-296). Body `role` field explicitly not read. Tests verify. |
| 2 | JWT in httpOnly cookies (not localStorage) | PASS | `_set_auth_cookies` sets `httponly=True`, `secure=True`, `samesite=Strict`. Never returned in response body. |
| 3 | No hardcoded JWT secret fallback | PASS | `auth.py:31-38` raises `RuntimeError` if `JWT_SECRET_KEY` is missing. |
| 4 | YooKassa webhook HMAC with constant-time comparison | PASS | `webhook.py:81` uses `hmac.compare_digest()`. |
| 5 | YooKassa webhook secret crash on missing | **FAIL** | `webhook.py:25` defaults to `''`. Runtime check at line 69 returns 500 but app starts. |
| 6 | Monetary fields use Decimal, not Float | PASS | `su_subscription.py` and `su_payment.py` use `fields.Monetary` with `currency_id`. `PLAN_CONFIG` uses `Decimal`. |
| 7 | Webhook idempotency | PASS | Deduplication by `idempotency_key` with DB unique constraint. |
| 8 | Rate limiting on auth endpoints | **FAIL** | Not implemented. Spec requires 5 attempts / 15 min. |
| 9 | Refresh token single-use (rotation) | **FAIL** | New tokens issued but old tokens never invalidated. |
| 10 | RS256 signing per spec | **FAIL** | HS256 used instead. |
| 11 | Password hashing bcrypt cost >= 12 | PASS | `PASSWORD_BCRYPT_ROUNDS = 12`. |
| 12 | No PII in logs | PASS | Logs contain IPs and payment IDs, not emails/names. |
| 13 | Input validation on registration | PASS | Email format, password complexity, required fields all validated. |
| 14 | Dead code / orphaned functions | **WARN** | `_hash_password` and `_verify_password` are never used (Odoo handles passwords). |

---

## Implementation Coverage

| Spec Item | ID | Priority | Implemented? | Notes |
|-----------|----|:--------:|:------------:|-------|
| Email registration | FR-AB-01 | P0 | Partial | Registration works but no email confirmation link |
| Phone registration | FR-AB-02 | P0 | NO | Not implemented at all |
| Registration fields | FR-AB-03 | P0 | Partial | Email/password/name/company yes. Phone, INN, position missing |
| Role assignment | FR-AB-04 | P0 | WRONG | Assigns `foreman` instead of spec's `admin` |
| Tenant creation | FR-AB-05 | P0 | YES | Company created on registration |
| 152-FZ consent | FR-AB-06 | P0 | NO | No consent capture |
| Duplicate prevention | FR-AB-07 | P0 | Partial | Email uniqueness yes, phone N/A |
| Login | FR-AB-10 | P0 | YES | Works (credential verification needs Odoo version check) |
| Token storage | FR-AB-11 | P0 | YES | httpOnly cookies |
| Token signing | FR-AB-12 | P0 | WRONG | HS256 instead of RS256, no key rotation |
| Refresh token rotation | FR-AB-13 | P0 | NO | Old tokens not invalidated |
| Logout | FR-AB-14 | P0 | Partial | Cookies cleared but no server-side invalidation |
| Brute-force protection | FR-AB-15 | P0 | NO | Not implemented |
| Password reset | FR-AB-16 | P0 | NO | Not implemented |
| Multi-device support | FR-AB-17 | P0 | NO | No per-device token tracking |
| Trial activation | FR-AB-30 | P0 | YES | 14-day Business trial on registration |
| Trial countdown | FR-AB-31 | P0 | Partial | Cron sends reminders (logging only, no actual email) |
| Trial expiration | FR-AB-32 | P0 | YES | Cron downgrades to free plan |
| Trial once | FR-AB-33 | P0 | Partial | Email uniqueness only |
| Payment methods | FR-AB-40 | P0 | Partial | Model supports card/SBP/YooMoney; no payment initiation API |
| Recurring payments | FR-AB-41 | P0 | NO | No auto-charge, no saved payment method management |
| Webhook processing | FR-AB-42 | P0 | YES | HMAC verified, events processed |
| Idempotency | FR-AB-43 | P0 | YES | Deduplicated by key + DB unique constraint |
| Upgrade/Downgrade | FR-AB-44 | P0 | Partial | Plan change works; no prorated billing |
| Payment history | FR-AB-45 | P0 | YES | su.payment model with full status tracking |
| Failed payment retry | FR-AB-46 | P0 | NO | Fields exist, no retry logic |
| Refunds | FR-AB-47 | P1 | Partial | Webhook handles refund.succeeded; no admin-initiated refund API |

**Overall implementation coverage: ~40% of P0 requirements fully implemented.**

---

## Recommendations

1. **Fix blocker: Make `YUKASSA_WEBHOOK_SECRET` crash on missing** -- same
   pattern as JWT secret. Two lines of code, zero excuses.

2. **Fix blocker: Either implement RS256 or formally amend the spec** -- do
   not ship with a spec/code mismatch on cryptographic algorithm choice. If
   HS256 is the deliberate decision, document why and update FR-AB-12.

3. **Implement rate limiting immediately** -- this is the single most
   exploitable gap. Use Odoo's `ir.config_parameter` + a simple counter
   model, or an nginx-level rate limiter as a quick win.

4. **Implement refresh token invalidation** -- add a `su.refresh.token`
   model storing `jti` + `expires_at` + `revoked` flag. On refresh, mark old
   `jti` as revoked. On decode, check revocation list.

5. **Delete dead code** -- `_hash_password()` and `_verify_password()` are
   never called. They give a false sense of security ("we use bcrypt!") while
   Odoo's own password mechanism is what actually runs.

6. **Fix default registration role to match spec** -- the company owner who
   registers should be `admin`, not `foreman`. Update auth.py, update the
   tests, and update the docstring.

7. **Create tracking issues for missing P0 items** -- phone registration,
   email confirmation, password reset, 152-FZ consent, and payment retry
   logic are all P0. Either implement them or explicitly defer with a
   documented decision.

8. **Replace hand-rolled JWT with PyJWT** -- the current implementation
   works, but any future algorithm change (RS256 migration) will be
   significantly easier with a standard library.

9. **Add webhook log retention cron** -- purge or archive entries older than
   90 days.

10. **Extract shared helpers** -- `_json_response` / `_json_error` are
    duplicated across controllers. Move to a `su_billing.utils` module.

---

*Reviewed: 2026-05-27*
*Reviewer: brutal-honesty-review (Phase 4)*
*Files reviewed: 7 implementation files, 2 rule files, 1 spec file*
