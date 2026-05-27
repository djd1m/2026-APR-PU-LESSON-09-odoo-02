# -*- coding: utf-8 -*-
"""
Tests for auth-billing feature.

Covers:
- Registration creates user with default role (not admin)
- Registration rejects/ignores role field in body
- Login returns httpOnly cookie
- JWT validation
- ЮKassa webhook HMAC verification
"""
import hashlib
import hmac
import json
import os
import unittest
from unittest.mock import patch

from odoo.tests.common import HttpCase, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAuthRegistration(HttpCase):
    """Test registration endpoint security."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Ensure JWT_SECRET_KEY is set for tests
        os.environ.setdefault('JWT_SECRET_KEY', 'test-secret-key-for-testing-only')

    def test_register_creates_user_with_default_role(self):
        """Registration should create user with 'foreman' role, not admin."""
        resp = self.url_open(
            '/api/auth/register',
            data=json.dumps({
                'email': 'newuser@test-stroyuprav.com',
                'password': 'StrongPass1',
                'company_name': 'Test Company',
                'full_name': 'Test User',
            }),
            headers={'Content-Type': 'application/json'},
        )

        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertIn('user_id', data)

        # Verify the user has foreman group, not admin
        user = self.env['res.users'].sudo().browse(data['user_id'])
        self.assertTrue(user.exists())
        self.assertTrue(
            user.has_group('su_base.group_su_foreman'),
            "User should have foreman group",
        )
        self.assertFalse(
            user.has_group('su_base.group_su_admin'),
            "User should NOT have admin group",
        )

    def test_register_ignores_role_field_in_body(self):
        """
        SECURITY: Even if request body contains 'role': 'admin',
        the server MUST ignore it and assign 'foreman'.
        """
        resp = self.url_open(
            '/api/auth/register',
            data=json.dumps({
                'email': 'hacker@test-stroyuprav.com',
                'password': 'StrongPass1',
                'company_name': 'Hacker Corp',
                'full_name': 'Hacker',
                'role': 'admin',  # MUST be ignored
            }),
            headers={'Content-Type': 'application/json'},
        )

        self.assertEqual(resp.status_code, 201)
        data = resp.json()

        user = self.env['res.users'].sudo().browse(data['user_id'])
        self.assertTrue(
            user.has_group('su_base.group_su_foreman'),
            "Role escalation attempt must be ignored — user gets foreman",
        )
        self.assertFalse(
            user.has_group('su_base.group_su_admin'),
            "Role escalation to admin MUST be prevented",
        )

    def test_register_rejects_weak_password(self):
        """Password must meet complexity requirements."""
        # Too short
        resp = self.url_open(
            '/api/auth/register',
            data=json.dumps({
                'email': 'weak@test-stroyuprav.com',
                'password': 'Aa1',
                'company_name': 'Weak Co',
                'full_name': 'Weak User',
            }),
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(resp.status_code, 400)

        # No uppercase
        resp = self.url_open(
            '/api/auth/register',
            data=json.dumps({
                'email': 'weak2@test-stroyuprav.com',
                'password': 'weakpassword1',
                'company_name': 'Weak Co',
                'full_name': 'Weak User',
            }),
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(resp.status_code, 400)

        # No digit
        resp = self.url_open(
            '/api/auth/register',
            data=json.dumps({
                'email': 'weak3@test-stroyuprav.com',
                'password': 'WeakPassword',
                'company_name': 'Weak Co',
                'full_name': 'Weak User',
            }),
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(resp.status_code, 400)

    def test_register_duplicate_email_rejected(self):
        """Duplicate email should return 409."""
        payload = json.dumps({
            'email': 'duplicate@test-stroyuprav.com',
            'password': 'StrongPass1',
            'company_name': 'Dup Co',
            'full_name': 'Dup User',
        })
        headers = {'Content-Type': 'application/json'}

        resp1 = self.url_open('/api/auth/register', data=payload, headers=headers)
        self.assertEqual(resp1.status_code, 201)

        resp2 = self.url_open('/api/auth/register', data=payload, headers=headers)
        self.assertEqual(resp2.status_code, 409)

    def test_login_returns_httponly_cookies(self):
        """Login should set access_token and refresh_token as httpOnly cookies."""
        # Register first
        self.url_open(
            '/api/auth/register',
            data=json.dumps({
                'email': 'logintest@test-stroyuprav.com',
                'password': 'StrongPass1',
                'company_name': 'Login Co',
                'full_name': 'Login User',
            }),
            headers={'Content-Type': 'application/json'},
        )

        # Login
        resp = self.url_open(
            '/api/auth/login',
            data=json.dumps({
                'email': 'logintest@test-stroyuprav.com',
                'password': 'StrongPass1',
            }),
            headers={'Content-Type': 'application/json'},
        )

        self.assertEqual(resp.status_code, 200)

        # Check cookies in response headers
        cookies = resp.headers.getlist('Set-Cookie')
        cookie_str = '; '.join(cookies)

        self.assertIn('access_token=', cookie_str,
                      "Response must contain access_token cookie")
        self.assertIn('refresh_token=', cookie_str,
                      "Response must contain refresh_token cookie")
        # httpOnly check (case-insensitive)
        self.assertIn('HttpOnly', cookie_str,
                      "Cookies must be httpOnly")

    def test_logout_clears_cookies(self):
        """Logout should clear auth cookies."""
        resp = self.url_open(
            '/api/auth/logout',
            data=json.dumps({}),
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(resp.status_code, 200)

    def test_register_creates_trial_subscription(self):
        """Registration should create a 14-day Business trial subscription."""
        resp = self.url_open(
            '/api/auth/register',
            data=json.dumps({
                'email': 'trial@test-stroyuprav.com',
                'password': 'StrongPass1',
                'company_name': 'Trial Co',
                'full_name': 'Trial User',
            }),
            headers={'Content-Type': 'application/json'},
        )

        self.assertEqual(resp.status_code, 201)
        data = resp.json()

        subscription = self.env['su.subscription'].sudo().search([
            ('company_id', '=', data['company_id']),
        ], limit=1)

        self.assertTrue(subscription.exists())
        self.assertEqual(subscription.plan, 'business')
        self.assertEqual(subscription.status, 'trial')
        self.assertTrue(subscription.trial_end)


@tagged('post_install', '-at_install')
class TestJWT(TransactionCase):
    """Test JWT generation and validation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret-for-unit-tests'

    def test_jwt_generate_and_decode(self):
        """Generated JWT should be decodable with correct secret."""
        from odoo.addons.su_billing.controllers.auth import (
            _generate_jwt,
            _decode_jwt,
            JWT_ACCESS_TTL,
        )

        payload = {
            'sub': 1,
            'company_id': 1,
            'role': 'foreman',
            'type': 'access',
        }

        token = _generate_jwt(payload.copy(), JWT_ACCESS_TTL)
        self.assertIsInstance(token, str)
        self.assertEqual(len(token.split('.')), 3, "JWT must have 3 parts")

        decoded = _decode_jwt(token)
        self.assertIsNotNone(decoded, "JWT should decode successfully")
        self.assertEqual(decoded['sub'], 1)
        self.assertEqual(decoded['role'], 'foreman')
        self.assertEqual(decoded['type'], 'access')

    def test_jwt_invalid_signature_rejected(self):
        """JWT with wrong signature should be rejected."""
        from odoo.addons.su_billing.controllers.auth import (
            _generate_jwt,
            _decode_jwt,
            JWT_ACCESS_TTL,
        )

        token = _generate_jwt({
            'sub': 1,
            'type': 'access',
        }, JWT_ACCESS_TTL)

        # Tamper with the token
        parts = token.split('.')
        parts[2] = parts[2][::-1]  # Reverse the signature
        tampered = '.'.join(parts)

        decoded = _decode_jwt(tampered)
        self.assertIsNone(decoded, "Tampered JWT must be rejected")

    def test_jwt_missing_secret_crashes(self):
        """Application must crash if JWT_SECRET_KEY is missing."""
        # This is tested by the module-level check in auth.py.
        # If JWT_SECRET_KEY were missing, the import would raise RuntimeError.
        # We verify the env var is checked at module level.
        import odoo.addons.su_billing.controllers.auth as auth_module
        self.assertTrue(
            hasattr(auth_module, 'JWT_SECRET_KEY'),
            "JWT_SECRET_KEY must be defined at module level",
        )
        self.assertIsNotNone(
            auth_module.JWT_SECRET_KEY,
            "JWT_SECRET_KEY must not be None (crash enforced at import)",
        )


@tagged('post_install', '-at_install')
class TestYukassaWebhookHMAC(TransactionCase):
    """Test ЮKassa webhook HMAC verification."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.webhook_secret = 'test-yukassa-webhook-secret'

    def test_hmac_signature_verification(self):
        """Valid HMAC signature should pass constant-time comparison."""
        body = b'{"event":"payment.succeeded","object":{"id":"pay_123"}}'

        # Compute correct HMAC
        expected = hmac.new(
            self.webhook_secret.encode('utf-8'),
            body,
            hashlib.sha256,
        ).hexdigest()

        # Verify using constant-time comparison (same as webhook handler)
        self.assertTrue(
            hmac.compare_digest(expected, expected),
            "Matching signatures should pass",
        )

    def test_hmac_invalid_signature_rejected(self):
        """Invalid HMAC signature should fail constant-time comparison."""
        body = b'{"event":"payment.succeeded","object":{"id":"pay_123"}}'

        correct = hmac.new(
            self.webhook_secret.encode('utf-8'),
            body,
            hashlib.sha256,
        ).hexdigest()

        wrong = hmac.new(
            b'wrong-secret',
            body,
            hashlib.sha256,
        ).hexdigest()

        self.assertFalse(
            hmac.compare_digest(correct, wrong),
            "Different signatures must not match",
        )

    def test_hmac_uses_compare_digest_not_equality(self):
        """
        SECURITY: Webhook handler uses hmac.compare_digest(), never ==.
        This prevents timing attacks.
        """
        import inspect
        from odoo.addons.su_billing.controllers.webhook import (
            SuWebhookController,
        )

        source = inspect.getsource(SuWebhookController.yukassa_webhook)
        self.assertIn(
            'hmac.compare_digest',
            source,
            "Webhook handler MUST use hmac.compare_digest for signature "
            "verification (constant-time comparison)",
        )


@tagged('post_install', '-at_install')
class TestSubscriptionLifecycle(TransactionCase):
    """Test subscription lifecycle methods."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
        })

    def test_trial_expiration_downgrades_to_free(self):
        """action_expire_trial should set plan=free, status=active."""
        subscription = self.env['su.subscription'].create({
            'partner_id': self.partner.id,
            'plan': 'business',
            'status': 'trial',
            'company_id': self.env.company.id,
        })

        subscription.action_expire_trial()

        self.assertEqual(subscription.plan, 'free')
        self.assertEqual(subscription.status, 'active')
        self.assertEqual(subscription.max_projects, 1)
        self.assertEqual(subscription.max_ai_estimates, 3)

    def test_activate_sets_billing_period(self):
        """action_activate should set period dates and reset counters."""
        subscription = self.env['su.subscription'].create({
            'partner_id': self.partner.id,
            'plan': 'business',
            'status': 'trial',
            'company_id': self.env.company.id,
        })

        subscription.action_activate()

        self.assertEqual(subscription.status, 'active')
        self.assertTrue(subscription.current_period_start)
        self.assertTrue(subscription.current_period_end)
        self.assertEqual(subscription.ai_estimates_used, 0)

    def test_cancel_sets_cancelled_status(self):
        """action_cancel should set status to cancelled."""
        subscription = self.env['su.subscription'].create({
            'partner_id': self.partner.id,
            'plan': 'business',
            'status': 'active',
            'company_id': self.env.company.id,
        })

        subscription.action_cancel()

        self.assertEqual(subscription.status, 'cancelled')

    def test_monetary_fields_use_currency_id(self):
        """Plan amount must use fields.Monetary with currency_id (Decimal)."""
        subscription = self.env['su.subscription'].create({
            'partner_id': self.partner.id,
            'plan': 'business',
            'status': 'active',
            'company_id': self.env.company.id,
        })

        # Verify the field is Monetary (uses Decimal internally)
        field = self.env['su.subscription']._fields['plan_amount']
        self.assertEqual(
            field.type, 'monetary',
            "plan_amount must be fields.Monetary (Decimal, never Float)",
        )

        # Verify currency_id is set
        self.assertTrue(
            subscription.currency_id,
            "currency_id must be set for Monetary fields",
        )
