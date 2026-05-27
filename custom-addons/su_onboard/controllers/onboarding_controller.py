# -*- coding: utf-8 -*-
import json
import logging

from odoo import http
from odoo.http import request, Response
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class OnboardingController(http.Controller):
    """REST API for onboarding quiz (F07).

    All endpoints require authenticated session (Odoo auth).
    """

    @http.route(
        '/api/v1/onboarding/status',
        type='http',
        auth='user',
        methods=['GET'],
        csrf=False,
    )
    def get_status(self):
        """Check if onboarding quiz is completed for current user."""
        partner = request.env.user.partner_id
        record = request.env['su.onboarding'].search([
            ('partner_id', '=', partner.id),
            ('company_id', '=', request.env.company.id),
        ], limit=1)

        if not record:
            return self._json_response({
                'completed': False,
                'needs_quiz': True,
            })

        return self._json_response({
            'completed': record.completed,
            'skipped': record.skipped,
            'recommended_plan': record.recommended_plan or None,
            'needs_quiz': not record.completed,
        })

    @http.route(
        '/api/v1/onboarding/submit',
        type='http',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def submit(self):
        """Submit quiz answers (all 4 questions)."""
        try:
            data = json.loads(request.httprequest.data or '{}')
        except (json.JSONDecodeError, TypeError):
            return self._json_response(
                {'error': 'Некорректный JSON'}, status=400,
            )

        required_fields = ['company_type', 'object_count', 'biggest_pain']
        missing = [f for f in required_fields if not data.get(f)]
        if missing:
            return self._json_response(
                {'error': 'Заполните все обязательные поля',
                 'missing': missing},
                status=400,
            )

        partner = request.env.user.partner_id
        Onboarding = request.env['su.onboarding']
        record = Onboarding.search([
            ('partner_id', '=', partner.id),
            ('company_id', '=', request.env.company.id),
        ], limit=1)

        if not record:
            record = Onboarding.create({
                'partner_id': partner.id,
                'company_id': request.env.company.id,
            })

        try:
            result = record.action_submit({
                'company_type': data.get('company_type'),
                'object_count': data.get('object_count'),
                'current_tools': data.get('current_tools', ''),
                'biggest_pain': data.get('biggest_pain'),
            })
        except ValidationError as exc:
            return self._json_response(
                {'error': str(exc.args[0])}, status=400,
            )

        return self._json_response({
            'status': 'ok',
            'recommended_plan': result['recommended_plan'],
        })

    @http.route(
        '/api/v1/onboarding/skip',
        type='http',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def skip(self):
        """Skip the onboarding quiz, apply defaults."""
        partner = request.env.user.partner_id
        Onboarding = request.env['su.onboarding']
        record = Onboarding.search([
            ('partner_id', '=', partner.id),
            ('company_id', '=', request.env.company.id),
        ], limit=1)

        if not record:
            record = Onboarding.create({
                'partner_id': partner.id,
                'company_id': request.env.company.id,
            })

        record.action_skip()
        return self._json_response({
            'status': 'ok',
            'skipped': True,
        })

    # ── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _json_response(data, status=200):
        """Return a JSON HTTP response with correct content type."""
        return Response(
            json.dumps(data, ensure_ascii=False),
            status=status,
            content_type='application/json; charset=utf-8',
        )
