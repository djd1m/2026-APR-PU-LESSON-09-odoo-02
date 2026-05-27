# Auth & Billing (F08) -- Pseudocode

**Feature ID:** F08
**Version:** 1.0
**Date:** 2026-05-27

---

## 1. Registration Flow

```
FUNCTION register(request):
    # SECURITY: NEVER read "role" from request body
    INPUT: email, password, full_name, company_name, phone (optional),
           pd_consent (boolean)

    # Step 1: Validate inputs
    VALIDATE email IS valid email format
    VALIDATE password length >= 8
    VALIDATE password contains at least 1 uppercase letter
    VALIDATE password contains at least 1 digit
    VALIDATE pd_consent IS true  # 152-FZ requirement
    VALIDATE full_name IS NOT empty
    VALIDATE company_name IS NOT empty

    # Step 2: Check duplicates
    IF User.exists(email=email):
        RETURN Error(409, "Email already registered")
    IF phone AND User.exists(phone=phone):
        RETURN Error(409, "Phone already registered")

    # Step 3: Hash password
    password_hash = bcrypt.hash(password, cost=12)

    # Step 4: Create tenant (Odoo company)
    BEGIN TRANSACTION
        company = Company.create(
            name=company_name,
            # Odoo company_id used for multi-tenant isolation
        )

        # Step 5: Create user with DEFAULT role — never from request
        user = User.create(
            email=email,
            phone=phone,
            password_hash=password_hash,
            full_name=full_name,
            company_id=company.id,
            role="admin",               # HARDCODED default, not from request
            is_email_confirmed=false,
            pd_consent_at=now(),
            pd_consent_version="1.0",
        )

        # Step 6: Create trial subscription
        subscription = Subscription.create(
            company_id=company.id,
            plan="business",            # Trial starts with Business
            status="trial",
            trial_start=now(),
            trial_end=now() + 14 days,
            ai_estimates_used=0,
            ai_estimates_limit=100,     # Business plan limit
            objects_limit=20,           # Business plan limit
        )
    COMMIT TRANSACTION

    # Step 7: Send confirmation email
    token = generate_confirmation_token(user.id, ttl=24h)
    send_email(user.email, "confirm_registration", token=token)

    # Step 8: Generate JWT pair
    access_token, refresh_token = generate_jwt_pair(user)

    # Step 9: Set httpOnly cookies
    response = Response(status=201, body={user_id, company_id, plan: "business_trial"})
    response.set_cookie("access_token", access_token,
        httpOnly=true, secure=true, sameSite="Strict", maxAge=15*60)
    response.set_cookie("refresh_token", refresh_token,
        httpOnly=true, secure=true, sameSite="Strict", maxAge=7*24*60*60)

    RETURN response
```

---

## 2. JWT Pair Generation

```
FUNCTION generate_jwt_pair(user):
    # SECURITY: Application MUST crash on startup if JWT_SECRET_KEY is missing
    # This is enforced in app initialization, not here

    jti_access = uuid4()
    jti_refresh = uuid4()

    access_payload = {
        sub: user.id,
        company_id: user.company_id,
        role: user.role,
        jti: jti_access,
        iat: now(),
        exp: now() + 15 minutes,
        type: "access",
    }

    refresh_payload = {
        sub: user.id,
        jti: jti_refresh,
        iat: now(),
        exp: now() + 7 days,
        type: "refresh",
        device_id: request.device_fingerprint OR uuid4(),
    }

    private_key = load_rsa_private_key()  # From env / mounted secret
    access_token = jwt.encode(access_payload, private_key, algorithm="RS256")
    refresh_token = jwt.encode(refresh_payload, private_key, algorithm="RS256")

    # Store refresh token metadata for rotation/revocation
    Redis.set(
        key=f"refresh:{jti_refresh}",
        value={user_id: user.id, device_id: refresh_payload.device_id, used: false},
        ttl=7 days
    )

    RETURN (access_token, refresh_token)
```

---

## 3. JWT Authentication Middleware

```
FUNCTION jwt_auth_middleware(request):
    # Step 1: Extract token from httpOnly cookie (NEVER from header/localStorage)
    access_token = request.cookies.get("access_token")

    IF access_token IS null:
        RETURN Error(401, "Authentication required")

    # Step 2: Verify and decode
    TRY:
        public_key = load_rsa_public_key()
        payload = jwt.decode(access_token, public_key, algorithms=["RS256"])
    CATCH ExpiredTokenError:
        RETURN Error(401, "Token expired", code="TOKEN_EXPIRED")
    CATCH InvalidTokenError:
        RETURN Error(401, "Invalid token")

    # Step 3: Validate token type
    IF payload.type != "access":
        RETURN Error(401, "Invalid token type")

    # Step 4: Load user and attach to request
    user = User.get(id=payload.sub)
    IF user IS null OR user.is_active IS false:
        RETURN Error(401, "User not found or deactivated")

    # Step 5: Attach user context (used by RBAC and tenant isolation)
    request.user = user
    request.company_id = payload.company_id
    request.role = user.role  # Always from DB, NEVER trust token claim alone

    RETURN proceed_to_handler(request)
```

---

## 4. Refresh Token Rotation

```
FUNCTION refresh_token_handler(request):
    refresh_token = request.cookies.get("refresh_token")

    IF refresh_token IS null:
        RETURN Error(401, "No refresh token")

    # Step 1: Decode (allow expired access, but refresh must be valid)
    TRY:
        payload = jwt.decode(refresh_token, public_key, algorithms=["RS256"])
    CATCH InvalidTokenError:
        RETURN Error(401, "Invalid refresh token")

    IF payload.type != "refresh":
        RETURN Error(401, "Invalid token type")

    # Step 2: Check if token was already used (rotation)
    token_data = Redis.get(f"refresh:{payload.jti}")

    IF token_data IS null:
        # Token not found — possibly expired or revoked
        RETURN Error(401, "Refresh token revoked or expired")

    IF token_data.used IS true:
        # SECURITY: Token reuse detected — possible theft
        # Revoke ALL tokens for this user's device
        revoke_all_device_tokens(payload.sub, token_data.device_id)
        LOG.warning("Refresh token reuse detected", user_id=payload.sub)
        RETURN Error(401, "Token reuse detected — all sessions revoked")

    # Step 3: Mark old token as used
    Redis.update(f"refresh:{payload.jti}", {used: true})

    # Step 4: Issue new pair
    user = User.get(id=payload.sub)
    new_access, new_refresh = generate_jwt_pair(user)

    # Step 5: Set new cookies
    response = Response(status=200)
    response.set_cookie("access_token", new_access, httpOnly=true, ...)
    response.set_cookie("refresh_token", new_refresh, httpOnly=true, ...)

    RETURN response
```

---

## 5. RBAC Authorization Decorator

```
FUNCTION require_role(*allowed_roles):
    RETURN DECORATOR(handler):
        FUNCTION wrapper(request, *args):
            # jwt_auth_middleware already ran; request.user is set
            IF request.user.role NOT IN allowed_roles:
                RETURN Error(403, "Insufficient permissions")

            # Tenant isolation: inject company_id filter
            request.tenant_filter = {company_id: request.company_id}

            RETURN handler(request, *args)
        RETURN wrapper

# Usage examples:
@require_role("admin")
FUNCTION manage_users(request): ...

@require_role("admin", "manager")
FUNCTION manage_projects(request): ...

@require_role("admin", "manager", "foreman")
FUNCTION manage_tasks(request): ...

@require_role("admin", "manager", "foreman", "client")
FUNCTION view_project(request): ...
```

---

## 6. YooKassa Webhook Handler

```
FUNCTION yukassa_webhook(request):
    # Step 1: Verify HMAC signature
    signature = request.headers.get("X-Yukassa-Signature")
    IF signature IS null:
        RETURN Error(400, "Missing signature")

    expected_signature = hmac_sha256(
        key=YUKASSA_SECRET_KEY,     # From env var
        message=request.raw_body
    )

    # SECURITY: Constant-time comparison to prevent timing attacks
    IF NOT constant_time_compare(signature, expected_signature):
        LOG.warning("Invalid webhook signature", ip=request.remote_addr)
        RETURN Error(403, "Invalid signature")

    # Step 2: Parse event
    event = parse_json(request.body)

    # Step 3: Idempotency check
    idempotency_key = event.idempotency_key OR event.object.id
    IF WebhookLog.exists(idempotency_key=idempotency_key):
        LOG.info("Duplicate webhook, skipping", key=idempotency_key)
        RETURN Response(200, "Already processed")

    # Step 4: Timestamp validation (replay protection)
    event_time = parse_datetime(event.created_at)
    IF abs(now() - event_time) > 5 minutes:
        LOG.warning("Webhook timestamp outside window", delta=now()-event_time)
        RETURN Error(400, "Event too old")

    # Step 5: Process by event type
    BEGIN TRANSACTION
        WebhookLog.create(
            idempotency_key=idempotency_key,
            event_type=event.event,
            payload=event,
            processed_at=now(),
        )

        SWITCH event.event:
            CASE "payment.succeeded":
                process_payment_success(event.object)
            CASE "payment.canceled":
                process_payment_canceled(event.object)
            CASE "refund.succeeded":
                process_refund(event.object)
            DEFAULT:
                LOG.info("Unhandled event type", type=event.event)
    COMMIT TRANSACTION

    RETURN Response(200, "OK")


FUNCTION process_payment_success(payment):
    subscription = Subscription.get(yukassa_payment_id=payment.id)
    IF subscription IS null:
        subscription = Subscription.get_by_metadata(payment.metadata)

    # CRITICAL: Use Decimal for money, never float
    amount = Decimal(payment.amount.value)
    currency = payment.amount.currency  # "RUB"

    Payment.create(
        subscription_id=subscription.id,
        amount=amount,              # Decimal, NOT float
        currency=currency,
        status="success",
        yukassa_payment_id=payment.id,
        payment_method=payment.payment_method.type,
        paid_at=now(),
    )

    # Activate or extend subscription
    IF subscription.status IN ("trial", "free", "past_due"):
        subscription.status = "active"
        subscription.current_period_start = now()
        subscription.current_period_end = now() + 30 days
        subscription.save()

    # Reset usage counters for new period
    subscription.ai_estimates_used = 0
    subscription.save()
```

---

## 7. Trial Expiration Cron Job

```
FUNCTION check_trial_expirations():
    # Runs daily via Celery Beat (or Odoo ir.cron)
    # Scheduled: every day at 03:00 UTC

    expired_trials = Subscription.search(
        status="trial",
        trial_end <= now(),
    )

    FOR subscription IN expired_trials:
        BEGIN TRANSACTION
            # Downgrade to Free plan
            subscription.plan = "free"
            subscription.status = "active"
            subscription.ai_estimates_limit = 3
            subscription.objects_limit = 1
            subscription.save()

            # Make excess objects read-only (do NOT delete)
            company_objects = Project.search(
                company_id=subscription.company_id,
                is_active=true,
                order_by="created_at ASC",
            )
            IF len(company_objects) > 1:
                # Keep the first (oldest) object active, rest read-only
                FOR obj IN company_objects[1:]:
                    obj.is_read_only = true
                    obj.save()

            # Notify user
            admin_user = User.search(
                company_id=subscription.company_id,
                role="admin",
            ).first()
            send_email(admin_user.email, "trial_expired", {
                company_name: subscription.company.name,
                upgrade_url: f"{BASE_URL}/billing/plans",
            })
        COMMIT TRANSACTION

    LOG.info("Trial expiration check complete",
             processed=len(expired_trials))


# Reminder emails (separate cron, runs daily at 10:00 UTC)
FUNCTION send_trial_reminders():
    FOR days_remaining IN [7, 3, 1]:
        target_date = now() + days_remaining days
        trials = Subscription.search(
            status="trial",
            trial_end BETWEEN target_date.start_of_day AND target_date.end_of_day,
        )
        FOR subscription IN trials:
            admin_user = get_admin_for_company(subscription.company_id)
            send_email(admin_user.email, "trial_reminder", {
                days_remaining: days_remaining,
                upgrade_url: f"{BASE_URL}/billing/plans",
            })
```

---

## 8. Application Startup -- Secret Validation

```
FUNCTION validate_required_secrets():
    # Called during application initialization, BEFORE accepting requests
    # CRITICAL: Must crash if any required secret is missing

    REQUIRED_SECRETS = [
        "JWT_SECRET_KEY",           # RSA private key or path
        "JWT_PUBLIC_KEY",           # RSA public key or path
        "YUKASSA_SHOP_ID",         # YooKassa shop identifier
        "YUKASSA_SECRET_KEY",      # YooKassa API secret
        "YUKASSA_WEBHOOK_SECRET",  # HMAC key for webhook verification
        "DATABASE_URL",            # PostgreSQL connection
        "REDIS_URL",               # Redis for sessions/cache
    ]

    missing = []
    FOR secret_name IN REQUIRED_SECRETS:
        IF os.environ.get(secret_name) IS null OR empty:
            missing.append(secret_name)

    IF len(missing) > 0:
        LOG.critical("Missing required secrets", missing=missing)
        CRASH("Application cannot start: missing secrets: " + join(missing, ", "))
        # sys.exit(1) — NO fallback values, NO defaults, NO "dev mode"
```

---

## 9. Password Reset Flow

```
FUNCTION request_password_reset(email):
    user = User.get(email=email)

    # Always return success to prevent email enumeration
    IF user IS null:
        LOG.info("Password reset requested for unknown email")
        RETURN Response(200, "If this email exists, a reset link was sent")

    # Generate single-use token
    reset_token = generate_secure_token(32)
    Redis.set(
        key=f"password_reset:{reset_token}",
        value={user_id: user.id, used: false},
        ttl=1 hour,
    )

    send_email(user.email, "password_reset", {
        reset_url: f"{BASE_URL}/auth/reset-password?token={reset_token}",
    })

    RETURN Response(200, "If this email exists, a reset link was sent")


FUNCTION confirm_password_reset(token, new_password):
    token_data = Redis.get(f"password_reset:{token}")

    IF token_data IS null:
        RETURN Error(400, "Invalid or expired reset token")

    IF token_data.used IS true:
        RETURN Error(400, "Token already used")

    user = User.get(id=token_data.user_id)

    # Check new password differs from last 3
    FOR old_hash IN user.password_history[-3:]:
        IF bcrypt.verify(new_password, old_hash):
            RETURN Error(400, "New password must differ from previous 3 passwords")

    VALIDATE new_password meets complexity requirements

    user.password_hash = bcrypt.hash(new_password, cost=12)
    user.password_history.append(user.password_hash)
    user.save()

    # Invalidate the reset token
    Redis.update(f"password_reset:{token}", {used: true})

    # Revoke all existing refresh tokens (force re-login)
    revoke_all_user_tokens(user.id)

    RETURN Response(200, "Password updated successfully")
```

---

## 10. Login Rate Limiting

```
FUNCTION check_login_rate_limit(identifier):
    # identifier = email or IP address
    key = f"login_attempts:{identifier}"
    attempts = Redis.get(key)

    IF attempts IS null:
        Redis.set(key, 1, ttl=15 minutes)
        RETURN {allowed: true, remaining: 4}

    IF attempts >= 5:
        lockout_key = f"login_lockout:{identifier}"
        IF NOT Redis.exists(lockout_key):
            Redis.set(lockout_key, true, ttl=30 minutes)
            # Notify user of lockout
            notify_lockout(identifier)
        RETURN {allowed: false, locked_until: Redis.ttl(lockout_key)}

    Redis.incr(key)
    RETURN {allowed: true, remaining: 5 - attempts - 1}
```
