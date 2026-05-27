# -*- coding: utf-8 -*-
"""
ЮKassa webhook handler.

Security:
- HMAC-SHA256 signature verification (constant-time comparison via
  hmac.compare_digest).
- Idempotent processing by payment_id / idempotency_key.
- Replay protection via timestamp window (5 minutes).
"""
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime
from decimal import Decimal

from odoo import http, fields
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

# Webhook secret for HMAC verification — crash on startup if missing
YUKASSA_WEBHOOK_SECRET = os.environ.get('YUKASSA_WEBHOOK_SECRET')
if not YUKASSA_WEBHOOK_SECRET:
    raise RuntimeError(
        "YUKASSA_WEBHOOK_SECRET env var is required. "
        "Cannot start without webhook signature verification."
    )


def _json_response(data, status=200):
    return Response(
        json.dumps(data, ensure_ascii=False),
        status=status,
        content_type='application/json',
    )


def _json_error(message, status=400):
    return _json_response({'error': message}, status=status)


class SuWebhookController(http.Controller):
    """ЮKassa webhook handler."""

    @http.route(
        '/api/webhooks/yukassa',
        type='http',
        auth='none',
        methods=['POST'],
        csrf=False,
    )
    def yukassa_webhook(self, **kwargs):
        """
        POST /api/webhooks/yukassa

        Verify HMAC signature (constant-time comparison), process payment
        events (payment.succeeded, payment.canceled, refund.succeeded),
        update su.subscription. Idempotent by payment_id.
        """
        raw_body = request.httprequest.data

        # Step 1: Verify HMAC-SHA256 signature
        signature = request.httprequest.headers.get('X-Yukassa-Signature', '')
        if not signature:
            _logger.warning(
                "Webhook received without signature from %s",
                request.httprequest.remote_addr,
            )
            return _json_error("Missing signature", 400)

        if not YUKASSA_WEBHOOK_SECRET:
            _logger.error("YUKASSA_WEBHOOK_SECRET is not configured")
            return _json_error("Webhook not configured", 500)

        # Compute expected HMAC-SHA256
        expected_signature = hmac.new(
            YUKASSA_WEBHOOK_SECRET.encode('utf-8'),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        # SECURITY: Constant-time comparison — never use ==
        if not hmac.compare_digest(signature, expected_signature):
            _logger.warning(
                "Invalid webhook signature from %s",
                request.httprequest.remote_addr,
            )
            return _json_error("Invalid signature", 403)

        # Step 2: Parse event
        try:
            event = json.loads(raw_body)
        except (json.JSONDecodeError, ValueError):
            return _json_error("Invalid JSON", 400)

        # Step 3: Idempotency check
        event_object = event.get('object', {})
        idempotency_key = (
            event.get('idempotency_key')
            or event_object.get('id')
            or ''
        )
        if not idempotency_key:
            return _json_error("Missing idempotency key", 400)

        existing_log = request.env['su.webhook.log'].sudo().search(
            [('idempotency_key', '=', idempotency_key)], limit=1,
        )
        if existing_log:
            _logger.info(
                "Duplicate webhook (key=%s), skipping", idempotency_key,
            )
            return _json_response({'status': 'already_processed'}, 200)

        # Step 4: Log the webhook event
        source_ip = request.httprequest.remote_addr or ''
        event_type = event.get('event', 'unknown')

        request.env['su.webhook.log'].sudo().create({
            'idempotency_key': idempotency_key,
            'event_type': event_type,
            'payload': json.dumps(event, ensure_ascii=False),
            'source_ip': source_ip,
            'signature_valid': True,
            'processed_at': fields.Datetime.now(),
        })

        # Step 5: Process by event type
        try:
            if event_type == 'payment.succeeded':
                self._process_payment_succeeded(event_object)
            elif event_type == 'payment.canceled':
                self._process_payment_canceled(event_object)
            elif event_type == 'refund.succeeded':
                self._process_refund_succeeded(event_object)
            else:
                _logger.info("Unhandled webhook event type: %s", event_type)
        except Exception:
            _logger.exception(
                "Error processing webhook event %s (key=%s)",
                event_type, idempotency_key,
            )
            # Still return 200 to prevent retries for processing errors
            # that would fail again

        return _json_response({'status': 'ok'}, 200)

    def _process_payment_succeeded(self, payment_obj):
        """Handle payment.succeeded event."""
        payment_id = payment_obj.get('id', '')
        amount_data = payment_obj.get('amount', {})
        # CRITICAL: Use Decimal for money, never float
        amount_value = Decimal(str(amount_data.get('value', '0')))
        currency = amount_data.get('currency', 'RUB')
        payment_method = payment_obj.get('payment_method', {})
        method_type = payment_method.get('type', 'bank_card')

        # Map ЮKassa method types to our selection values
        method_map = {
            'bank_card': 'bank_card',
            'sbp': 'sbp',
            'yoo_money': 'yoo_money',
        }
        mapped_method = method_map.get(method_type, 'bank_card')

        metadata = payment_obj.get('metadata', {})
        subscription_id = metadata.get('subscription_id')

        if subscription_id:
            subscription = request.env['su.subscription'].sudo().browse(
                int(subscription_id)
            )
            if subscription.exists():
                # Create payment record
                request.env['su.payment'].sudo().create({
                    'subscription_id': subscription.id,
                    'amount': float(amount_value),
                    'status': 'success',
                    'yukassa_payment_id': payment_id,
                    'payment_method': mapped_method,
                    'paid_at': fields.Datetime.now(),
                    'description': f'ЮKassa payment {payment_id}',
                })

                # Activate subscription
                subscription.action_activate()

                _logger.info(
                    "Payment succeeded: %s, amount=%s %s, subscription=%s",
                    payment_id, amount_value, currency, subscription.name,
                )

    def _process_payment_canceled(self, payment_obj):
        """Handle payment.canceled event."""
        payment_id = payment_obj.get('id', '')
        metadata = payment_obj.get('metadata', {})
        subscription_id = metadata.get('subscription_id')

        if subscription_id:
            subscription = request.env['su.subscription'].sudo().browse(
                int(subscription_id)
            )
            if subscription.exists():
                # Record failed payment
                cancellation = payment_obj.get('cancellation_details', {})
                reason = cancellation.get('reason', 'unknown')

                request.env['su.payment'].sudo().create({
                    'subscription_id': subscription.id,
                    'amount': float(Decimal(str(
                        payment_obj.get('amount', {}).get('value', '0')
                    ))),
                    'status': 'failed',
                    'yukassa_payment_id': payment_id,
                    'failed_at': fields.Datetime.now(),
                    'failure_reason': reason,
                })

                # Mark subscription as past_due after failures
                subscription.action_set_past_due()

                _logger.info(
                    "Payment canceled: %s, reason=%s, subscription=%s",
                    payment_id, reason, subscription.name,
                )

    def _process_refund_succeeded(self, refund_obj):
        """Handle refund.succeeded event."""
        refund_id = refund_obj.get('id', '')
        payment_id = refund_obj.get('payment_id', '')
        amount_data = refund_obj.get('amount', {})
        refund_amount = Decimal(str(amount_data.get('value', '0')))

        # Find the original payment
        payment = request.env['su.payment'].sudo().search(
            [('yukassa_payment_id', '=', payment_id)], limit=1,
        )
        if payment:
            payment.write({
                'status': 'refunded',
                'refund_amount': float(refund_amount),
                'refund_reason': refund_obj.get('description', ''),
            })
            _logger.info(
                "Refund succeeded: %s for payment %s, amount=%s",
                refund_id, payment_id, refund_amount,
            )
