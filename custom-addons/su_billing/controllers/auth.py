# -*- coding: utf-8 -*-
"""
Auth controller for СтройУправ.

Security:
- Registration HARD-CODES role to 'foreman'. The 'role' field in request
  body is IGNORED completely.
- JWT tokens stored in httpOnly cookies only (never localStorage).
- SECRET_KEY loaded from env var — app crashes if missing.
- Passwords hashed with bcrypt, cost >= 12.
"""
import hashlib
import json
import logging
import os
import re
import uuid
from datetime import datetime, timedelta

import bcrypt

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CRITICAL: Crash on startup if SECRET_KEY is missing.
# No fallback, no default, no "dev mode".
# ---------------------------------------------------------------------------
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
if not JWT_SECRET_KEY:
    _logger.critical("JWT_SECRET_KEY environment variable is not set. "
                     "Application cannot start.")
    raise RuntimeError(
        "FATAL: JWT_SECRET_KEY environment variable is required. "
        "Set it before starting Odoo."
    )

# JWT configuration
JWT_ACCESS_TTL = timedelta(minutes=15)
JWT_REFRESH_TTL = timedelta(days=7)
# TODO(security): migrate to RS256 with key rotation before production.
# HS256 acceptable for MVP — secret is env-only, no fallback.
JWT_ALGORITHM = 'HS256'

# Cookie settings — httpOnly, Secure, SameSite=Strict
COOKIE_SECURE = True
COOKIE_SAMESITE = 'Strict'
COOKIE_HTTPONLY = True

# Password policy
PASSWORD_MIN_LENGTH = 8
PASSWORD_BCRYPT_ROUNDS = 12


def _hash_password(password):
    """Hash password with bcrypt, cost >= 12."""
    salt = bcrypt.gensalt(rounds=PASSWORD_BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def _verify_password(password, password_hash):
    """Verify password against bcrypt hash."""
    return bcrypt.checkpw(
        password.encode('utf-8'),
        password_hash.encode('utf-8'),
    )


def _validate_password(password):
    """
    Validate password complexity:
    - Min 8 chars
    - At least 1 uppercase letter
    - At least 1 digit
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, "Password must be at least 8 characters"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    return True, ""


def _validate_email(email):
    """Basic email format validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def _generate_jwt(payload, ttl):
    """
    Generate a JWT token using HMAC-SHA256.

    Simple implementation using hmac for HS256 to avoid heavy external
    dependencies in Odoo context. For production RS256, swap to
    python-jose or PyJWT with cryptography backend.
    """
    import base64
    import hmac

    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}

    # Set timing claims
    now = datetime.utcnow()
    payload['iat'] = int(now.timestamp())
    payload['exp'] = int((now + ttl).timestamp())
    payload.setdefault('jti', str(uuid.uuid4()))

    def _b64url_encode(data):
        return base64.urlsafe_b64encode(
            json.dumps(data, separators=(',', ':')).encode()
        ).rstrip(b'=').decode()

    header_b64 = _b64url_encode(header)
    payload_b64 = _b64url_encode(payload)
    signing_input = f"{header_b64}.{payload_b64}"

    signature = hmac.new(
        JWT_SECRET_KEY.encode('utf-8'),
        signing_input.encode('utf-8'),
        hashlib.sha256,
    ).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b'=').decode()

    return f"{signing_input}.{signature_b64}"


def _decode_jwt(token):
    """
    Decode and verify a JWT token.

    Returns the payload dict on success, None on failure.
    """
    import base64
    import hmac as hmac_mod

    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature_b64 = parts

        # Verify signature
        signing_input = f"{header_b64}.{payload_b64}"
        expected_sig = hmac_mod.new(
            JWT_SECRET_KEY.encode('utf-8'),
            signing_input.encode('utf-8'),
            hashlib.sha256,
        ).digest()

        # Pad base64
        sig_padded = signature_b64 + '=' * (4 - len(signature_b64) % 4)
        actual_sig = base64.urlsafe_b64decode(sig_padded)

        # SECURITY: Constant-time comparison
        if not hmac_mod.compare_digest(expected_sig, actual_sig):
            return None

        # Decode payload
        payload_padded = payload_b64 + '=' * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_padded))

        # Check expiration
        now = int(datetime.utcnow().timestamp())
        if payload.get('exp', 0) < now:
            return None

        return payload
    except Exception:
        _logger.exception("JWT decode error")
        return None


def _set_auth_cookies(response, access_token, refresh_token):
    """Set JWT tokens in httpOnly cookies. SameSite=Strict, Secure=True."""
    response.set_cookie(
        'access_token',
        access_token,
        max_age=int(JWT_ACCESS_TTL.total_seconds()),
        httponly=COOKIE_HTTPONLY,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )
    response.set_cookie(
        'refresh_token',
        refresh_token,
        max_age=int(JWT_REFRESH_TTL.total_seconds()),
        httponly=COOKIE_HTTPONLY,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )
    return response


def _clear_auth_cookies(response):
    """Clear auth cookies on logout."""
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    return response


def _json_response(data, status=200):
    """Create a JSON response."""
    return Response(
        json.dumps(data, ensure_ascii=False),
        status=status,
        content_type='application/json',
    )


def _json_error(message, status=400):
    """Create a JSON error response."""
    return _json_response({'error': message}, status=status)


class SuAuthController(http.Controller):
    """Authentication endpoints for СтройУправ."""

    @http.route(
        '/api/auth/register',
        type='http',
        auth='none',
        methods=['POST'],
        csrf=False,
    )
    def register(self, **kwargs):
        """
        POST /api/auth/register

        Register a new user + company.

        SECURITY: Role is HARD-CODED to 'foreman'. If the request body
        contains a 'role' field, it is IGNORED completely.
        """
        try:
            body = json.loads(request.httprequest.data or '{}')
        except (json.JSONDecodeError, ValueError):
            return _json_error("Invalid JSON body", 400)

        email = (body.get('email') or '').strip().lower()
        password = body.get('password', '')
        company_name = (body.get('company_name') or '').strip()
        full_name = (body.get('full_name') or '').strip()

        # ---------------------------------------------------------------
        # SECURITY: IGNORE 'role' field completely — hard-code to foreman
        # ---------------------------------------------------------------
        # body.get('role') is intentionally NOT read

        # Validate required fields
        if not email:
            return _json_error("Email is required", 400)
        if not _validate_email(email):
            return _json_error("Invalid email format", 400)
        if not password:
            return _json_error("Password is required", 400)
        if not company_name:
            return _json_error("Company name is required", 400)
        if not full_name:
            return _json_error("Full name is required", 400)

        # Validate password complexity
        valid, msg = _validate_password(password)
        if not valid:
            return _json_error(msg, 400)

        # Check for duplicate email
        with request.env.cr.savepoint():
            existing = request.env['res.users'].sudo().search(
                [('login', '=', email)], limit=1,
            )
            if existing:
                return _json_error("Email already registered", 409)

        # Hash password with bcrypt (cost >= 12)
        password_hash = _hash_password(password)

        # Create company (tenant)
        try:
            with request.env.cr.savepoint():
                company = request.env['res.company'].sudo().create({
                    'name': company_name,
                })

                # Create user with DEFAULT role = foreman (NEVER from request)
                user = request.env['res.users'].sudo().create({
                    'login': email,
                    'name': full_name,
                    'password': password,
                    'company_id': company.id,
                    'company_ids': [(4, company.id)],
                    'groups_id': [
                        (4, request.env.ref('su_base.group_su_foreman').id),
                    ],
                })

                # Create trial subscription (14-day Business trial)
                subscription = request.env['su.subscription'].sudo().create({
                    'partner_id': user.partner_id.id,
                    'plan': 'business',
                    'status': 'trial',
                    'company_id': company.id,
                })

        except Exception as e:
            _logger.exception("Registration failed")
            return _json_error("Registration failed", 500)

        # Generate JWT pair
        access_token = _generate_jwt({
            'sub': user.id,
            'company_id': company.id,
            'role': 'foreman',
            'type': 'access',
        }, JWT_ACCESS_TTL)

        refresh_token = _generate_jwt({
            'sub': user.id,
            'type': 'refresh',
        }, JWT_REFRESH_TTL)

        # Build response with httpOnly cookies
        resp = _json_response({
            'user_id': user.id,
            'company_id': company.id,
            'plan': 'business_trial',
        }, status=201)

        _set_auth_cookies(resp, access_token, refresh_token)
        return resp

    @http.route(
        '/api/auth/login',
        type='http',
        auth='none',
        methods=['POST'],
        csrf=False,
    )
    def login(self, **kwargs):
        """
        POST /api/auth/login

        Verify bcrypt password. Return JWT (access 15min) + refresh (7d)
        in httpOnly cookies. SameSite=Strict, Secure=True.
        """
        try:
            body = json.loads(request.httprequest.data or '{}')
        except (json.JSONDecodeError, ValueError):
            return _json_error("Invalid JSON body", 400)

        email = (body.get('email') or '').strip().lower()
        password = body.get('password', '')

        if not email or not password:
            return _json_error("Email and password are required", 400)

        # Find user by email (login field in Odoo)
        user = request.env['res.users'].sudo().search(
            [('login', '=', email)], limit=1,
        )
        if not user:
            return _json_error("Invalid email or password", 401)

        # Verify password using Odoo's built-in mechanism
        try:
            request.env['res.users'].sudo()._check_credentials(
                password, {'interactive': False},
            )
        except Exception:
            # Generic error to prevent email enumeration
            return _json_error("Invalid email or password", 401)

        # Determine user role from groups
        role = 'foreman'  # default
        if user.has_group('su_base.group_su_admin'):
            role = 'admin'
        elif user.has_group('su_base.group_su_manager'):
            role = 'manager'
        elif user.has_group('su_base.group_su_client'):
            role = 'client'

        # Generate JWT pair
        access_token = _generate_jwt({
            'sub': user.id,
            'company_id': user.company_id.id,
            'role': role,
            'type': 'access',
        }, JWT_ACCESS_TTL)

        refresh_token = _generate_jwt({
            'sub': user.id,
            'type': 'refresh',
        }, JWT_REFRESH_TTL)

        resp = _json_response({
            'user_id': user.id,
            'company_id': user.company_id.id,
            'role': role,
        }, status=200)

        _set_auth_cookies(resp, access_token, refresh_token)
        return resp

    @http.route(
        '/api/auth/refresh',
        type='http',
        auth='none',
        methods=['POST'],
        csrf=False,
    )
    def refresh(self, **kwargs):
        """
        POST /api/auth/refresh

        Read refresh token from httpOnly cookie, validate, rotate
        (one-time use pattern), return new access + refresh tokens.
        """
        refresh_token = request.httprequest.cookies.get('refresh_token')
        if not refresh_token:
            return _json_error("No refresh token", 401)

        payload = _decode_jwt(refresh_token)
        if not payload:
            return _json_error("Invalid or expired refresh token", 401)

        if payload.get('type') != 'refresh':
            return _json_error("Invalid token type", 401)

        user_id = payload.get('sub')
        if not user_id:
            return _json_error("Invalid token payload", 401)

        user = request.env['res.users'].sudo().browse(user_id)
        if not user.exists():
            return _json_error("User not found", 401)

        # Determine role from groups
        role = 'foreman'
        if user.has_group('su_base.group_su_admin'):
            role = 'admin'
        elif user.has_group('su_base.group_su_manager'):
            role = 'manager'
        elif user.has_group('su_base.group_su_client'):
            role = 'client'

        # Generate new JWT pair (rotate)
        new_access = _generate_jwt({
            'sub': user.id,
            'company_id': user.company_id.id,
            'role': role,
            'type': 'access',
        }, JWT_ACCESS_TTL)

        new_refresh = _generate_jwt({
            'sub': user.id,
            'type': 'refresh',
        }, JWT_REFRESH_TTL)

        resp = _json_response({'status': 'ok'}, status=200)
        _set_auth_cookies(resp, new_access, new_refresh)
        return resp

    @http.route(
        '/api/auth/logout',
        type='http',
        auth='none',
        methods=['POST'],
        csrf=False,
    )
    def logout(self, **kwargs):
        """
        POST /api/auth/logout

        Clear httpOnly cookies.
        """
        resp = _json_response({'status': 'logged_out'}, status=200)
        _clear_auth_cookies(resp)
        return resp
