# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestSuOnboarding(TransactionCase):
    """Unit tests for su.onboarding model (F07 Onboarding Quiz)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner Onboarding',
        })
        cls.company = cls.env.company
        cls.Onboarding = cls.env['su.onboarding']

    def _create_record(self):
        """Helper: create a blank onboarding record."""
        return self.Onboarding.create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
        })

    # ── Plan recommendation matrix ─────────────────────────────

    def test_plan_recommendation_client_always_free(self):
        """Client always gets free plan regardless of object count."""
        for oc in ('1_3', '4_10', '11_50', '50_plus'):
            plan = self.Onboarding._compute_recommended_plan('client', oc)
            self.assertEqual(plan, 'free',
                             "client + %s should be free" % oc)

    def test_plan_recommendation_private_master(self):
        """Private master scales free -> starter -> business."""
        cases = {
            '1_3': 'free',
            '4_10': 'starter',
            '11_50': 'business',
            '50_plus': 'business',
        }
        for oc, expected in cases.items():
            plan = self.Onboarding._compute_recommended_plan(
                'private_master', oc,
            )
            self.assertEqual(plan, expected,
                             "private_master + %s should be %s" % (oc, expected))

    def test_plan_recommendation_repair(self):
        """Repair company scales starter -> business -> enterprise."""
        cases = {
            '1_3': 'starter',
            '4_10': 'business',
            '11_50': 'enterprise',
            '50_plus': 'enterprise',
        }
        for oc, expected in cases.items():
            plan = self.Onboarding._compute_recommended_plan('repair', oc)
            self.assertEqual(plan, expected,
                             "repair + %s should be %s" % (oc, expected))

    def test_plan_recommendation_contractor(self):
        """Contractor starts at business, scales to enterprise."""
        cases = {
            '1_3': 'business',
            '4_10': 'enterprise',
            '11_50': 'enterprise',
            '50_plus': 'enterprise',
        }
        for oc, expected in cases.items():
            plan = self.Onboarding._compute_recommended_plan(
                'contractor', oc,
            )
            self.assertEqual(plan, expected,
                             "contractor + %s should be %s" % (oc, expected))

    def test_plan_recommendation_missing_values(self):
        """Missing company_type or object_count returns default (starter)."""
        self.assertEqual(
            self.Onboarding._compute_recommended_plan(None, '4_10'),
            'starter',
        )
        self.assertEqual(
            self.Onboarding._compute_recommended_plan('repair', None),
            'starter',
        )

    # ── Submit flow ────────────────────────────────────────────

    def test_submit_creates_fields(self):
        """action_submit writes all answers and computes plan."""
        record = self._create_record()
        result = record.action_submit({
            'company_type': 'repair',
            'object_count': '4_10',
            'current_tools': 'excel, 1c',
            'biggest_pain': 'budget',
        })
        self.assertEqual(result['recommended_plan'], 'business')
        self.assertEqual(record.company_type, 'repair')
        self.assertEqual(record.object_count, '4_10')
        self.assertEqual(record.current_tools, 'excel, 1c')
        self.assertEqual(record.biggest_pain, 'budget')
        self.assertTrue(record.completed)
        self.assertFalse(record.skipped)
        self.assertIsNotNone(record.completed_at)

    def test_submit_idempotent(self):
        """Second submit overwrites first, no duplicate records."""
        record = self._create_record()
        record.action_submit({
            'company_type': 'repair',
            'object_count': '1_3',
            'current_tools': '',
            'biggest_pain': 'deadlines',
        })
        self.assertEqual(record.recommended_plan, 'starter')

        # Re-submit with different answers
        record.action_submit({
            'company_type': 'contractor',
            'object_count': '50_plus',
            'current_tools': 'whatsapp',
            'biggest_pain': 'communication',
        })
        self.assertEqual(record.recommended_plan, 'enterprise')
        self.assertEqual(record.company_type, 'contractor')

        # Still only one record for this partner+company
        count = self.Onboarding.search_count([
            ('partner_id', '=', self.partner.id),
            ('company_id', '=', self.company.id),
        ])
        self.assertEqual(count, 1)

    # ── Skip flow ──────────────────────────────────────────────

    def test_skip_sets_defaults(self):
        """action_skip sets completed=True, skipped=True, plan=starter."""
        record = self._create_record()
        record.action_skip()
        self.assertTrue(record.completed)
        self.assertTrue(record.skipped)
        self.assertEqual(record.recommended_plan, 'starter')
        self.assertIsNotNone(record.completed_at)

    def test_submit_after_skip_clears_skipped(self):
        """Re-submitting after skip sets skipped=False."""
        record = self._create_record()
        record.action_skip()
        self.assertTrue(record.skipped)

        record.action_submit({
            'company_type': 'client',
            'object_count': '1_3',
            'current_tools': '',
            'biggest_pain': 'documents',
        })
        self.assertFalse(record.skipped)
        self.assertTrue(record.completed)
        self.assertEqual(record.recommended_plan, 'free')

    # ── Validation ─────────────────────────────────────────────

    def test_invalid_company_type_rejected(self):
        """Invalid company_type raises ValidationError."""
        record = self._create_record()
        with self.assertRaises(ValidationError):
            record.action_submit({
                'company_type': 'hacker',
                'object_count': '1_3',
                'current_tools': '',
                'biggest_pain': 'budget',
            })

    def test_invalid_object_count_rejected(self):
        """Invalid object_count raises ValidationError."""
        record = self._create_record()
        with self.assertRaises(ValidationError):
            record.action_submit({
                'company_type': 'repair',
                'object_count': '999',
                'current_tools': '',
                'biggest_pain': 'budget',
            })

    def test_invalid_biggest_pain_rejected(self):
        """Invalid biggest_pain raises ValidationError."""
        record = self._create_record()
        with self.assertRaises(ValidationError):
            record.action_submit({
                'company_type': 'repair',
                'object_count': '1_3',
                'current_tools': '',
                'biggest_pain': 'nonexistent',
            })

    def test_current_tools_max_length(self):
        """current_tools exceeding 500 chars raises ValidationError."""
        record = self._create_record()
        with self.assertRaises(ValidationError):
            record.action_submit({
                'company_type': 'repair',
                'object_count': '1_3',
                'current_tools': 'x' * 501,
                'biggest_pain': 'budget',
            })

    # ── Company isolation ──────────────────────────────────────

    def test_company_isolation(self):
        """Records are filtered by company_id."""
        other_company = self.env['res.company'].create({
            'name': 'Other Company',
        })
        rec1 = self.Onboarding.create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
        })
        rec2 = self.Onboarding.create({
            'partner_id': self.partner.id,
            'company_id': other_company.id,
        })
        # Different records for same partner, different companies
        self.assertNotEqual(rec1.id, rec2.id)
        self.assertEqual(rec1.company_id, self.company)
        self.assertEqual(rec2.company_id, other_company)
