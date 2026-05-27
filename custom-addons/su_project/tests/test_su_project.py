# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestSuProjectDashboard(TransactionCase):
    """Tests for F02: Dashboard объектов — computed fields and actions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref('base.main_company')
        cls.currency = cls.company.currency_id

        cls.project = cls.env['su.project'].create({
            'name': 'Тестовый объект',
            'address': 'ул. Тестовая, 1',
            'project_type': 'renovation',
            'budget_planned': 1000000.00,
            'start_date': date.today() - timedelta(days=30),
            'end_date': date.today() + timedelta(days=30),
            'company_id': cls.company.id,
        })

    # ── Progress computation ───────────────────────────────────

    def test_progress_no_tasks(self):
        """Progress is 0 when project has no tasks."""
        self.assertEqual(self.project.progress, 0.0)

    def test_progress_with_tasks(self):
        """Progress is average of task progress values."""
        Task = self.env['su.task']
        Task.create({
            'name': 'Задача 1',
            'project_id': self.project.id,
            'progress': 50.0,
        })
        Task.create({
            'name': 'Задача 2',
            'project_id': self.project.id,
            'progress': 100.0,
        })
        self.project.invalidate_recordset()
        self.assertAlmostEqual(self.project.progress, 75.0, places=1)

    def test_progress_all_zero(self):
        """Progress is 0 when all tasks are at 0%."""
        Task = self.env['su.task']
        Task.create({
            'name': 'Задача 1',
            'project_id': self.project.id,
            'progress': 0.0,
        })
        self.project.invalidate_recordset()
        self.assertEqual(self.project.progress, 0.0)

    # ── Budget actual computation ──────────────────────────────

    def test_budget_actual_confirmed_only(self):
        """Budget actual sums only confirmed estimates."""
        Estimate = self.env['su.estimate']
        Estimate.create({
            'name': 'Смета 1',
            'project_id': self.project.id,
            'total_amount': 500000.00,
            'state': 'confirmed',
        })
        Estimate.create({
            'name': 'Смета 2',
            'project_id': self.project.id,
            'total_amount': 200000.00,
            'state': 'draft',
        })
        self.project.invalidate_recordset()
        self.assertAlmostEqual(
            self.project.budget_actual, 500000.00, places=2
        )

    def test_budget_actual_no_estimates(self):
        """Budget actual is 0 when no estimates exist."""
        self.assertAlmostEqual(self.project.budget_actual, 0.0, places=2)

    # ── Budget deviation ───────────────────────────────────────

    def test_budget_deviation_over(self):
        """Deviation computed correctly when over budget."""
        Estimate = self.env['su.estimate']
        Estimate.create({
            'name': 'Смета',
            'project_id': self.project.id,
            'total_amount': 1100000.00,
            'state': 'confirmed',
        })
        self.project.invalidate_recordset()
        self.assertAlmostEqual(
            self.project.budget_deviation, 100000.00, places=2
        )
        self.assertAlmostEqual(
            self.project.budget_deviation_pct, 10.0, places=1
        )

    def test_budget_deviation_zero_planned(self):
        """No division by zero when budget_planned is 0."""
        project = self.env['su.project'].create({
            'name': 'Без бюджета',
            'budget_planned': 0.0,
            'company_id': self.company.id,
        })
        self.assertEqual(project.budget_deviation_pct, 0.0)

    # ── Health status ──────────────────────────────────────────

    def test_health_green_within_budget(self):
        """GREEN when within 5% of budget and not overdue."""
        Estimate = self.env['su.estimate']
        Estimate.create({
            'name': 'Смета',
            'project_id': self.project.id,
            'total_amount': 1040000.00,  # 4% over
            'state': 'confirmed',
        })
        self.project.invalidate_recordset()
        self.assertEqual(self.project.health_status, 'green')

    def test_health_yellow_budget(self):
        """YELLOW when 5-15% over budget."""
        Estimate = self.env['su.estimate']
        Estimate.create({
            'name': 'Смета',
            'project_id': self.project.id,
            'total_amount': 1100000.00,  # 10% over
            'state': 'confirmed',
        })
        self.project.invalidate_recordset()
        self.assertEqual(self.project.health_status, 'yellow')

    def test_health_red_budget(self):
        """RED when >15% over budget."""
        Estimate = self.env['su.estimate']
        Estimate.create({
            'name': 'Смета',
            'project_id': self.project.id,
            'total_amount': 1200000.00,  # 20% over
            'state': 'confirmed',
        })
        self.project.invalidate_recordset()
        self.assertEqual(self.project.health_status, 'red')

    def test_health_red_overdue(self):
        """RED when project is overdue regardless of budget."""
        self.project.write({'end_date': date.today() - timedelta(days=1)})
        self.project.invalidate_recordset()
        self.assertEqual(self.project.health_status, 'red')

    def test_health_yellow_near_deadline(self):
        """YELLOW when deadline within 7 days and budget is OK."""
        self.project.write({
            'end_date': date.today() + timedelta(days=3),
        })
        self.project.invalidate_recordset()
        self.assertEqual(self.project.health_status, 'yellow')

    def test_health_green_no_end_date(self):
        """GREEN when no end_date set and budget within threshold."""
        self.project.write({'end_date': False})
        self.project.invalidate_recordset()
        self.assertEqual(self.project.health_status, 'green')

    # ── Overdue flag ───────────────────────────────────────────

    def test_overdue_true(self):
        """Overdue is True when end_date is in the past."""
        self.project.write({'end_date': date.today() - timedelta(days=1)})
        self.project.invalidate_recordset()
        self.assertTrue(self.project.overdue)

    def test_overdue_false_future(self):
        """Overdue is False when end_date is in the future."""
        self.assertFalse(self.project.overdue)

    def test_overdue_false_today(self):
        """Overdue is False when end_date is today (strict less-than)."""
        self.project.write({'end_date': date.today()})
        self.project.invalidate_recordset()
        self.assertFalse(self.project.overdue)

    # ── Task count ─────────────────────────────────────────────

    def test_task_count(self):
        """Task count reflects number of linked tasks."""
        Task = self.env['su.task']
        Task.create({
            'name': 'Задача 1',
            'project_id': self.project.id,
        })
        Task.create({
            'name': 'Задача 2',
            'project_id': self.project.id,
        })
        self.project.invalidate_recordset()
        self.assertEqual(self.project.task_count, 2)

    # ── State transitions ──────────────────────────────────────

    def test_action_start(self):
        """Draft project can be started."""
        self.project.action_start()
        self.assertEqual(self.project.state, 'active')

    def test_action_start_sets_date(self):
        """action_start sets start_date if not already set."""
        self.project.write({'start_date': False})
        self.project.action_start()
        self.assertEqual(self.project.start_date, date.today())

    def test_action_pause(self):
        """Active project can be paused."""
        self.project.action_start()
        self.project.action_pause()
        self.assertEqual(self.project.state, 'paused')

    def test_action_resume(self):
        """Paused project can be resumed."""
        self.project.action_start()
        self.project.action_pause()
        self.project.action_resume()
        self.assertEqual(self.project.state, 'active')

    def test_action_done(self):
        """Active project can be completed."""
        self.project.action_start()
        self.project.action_done()
        self.assertEqual(self.project.state, 'done')

    def test_action_done_from_draft_raises(self):
        """Cannot complete a draft project."""
        with self.assertRaises(UserError):
            self.project.action_done()

    def test_action_start_from_active_raises(self):
        """Cannot start an already active project."""
        self.project.action_start()
        with self.assertRaises(UserError):
            self.project.action_start()

    def test_action_pause_from_draft_raises(self):
        """Cannot pause a draft project."""
        with self.assertRaises(UserError):
            self.project.action_pause()

    def test_action_resume_from_active_raises(self):
        """Cannot resume an active project."""
        self.project.action_start()
        with self.assertRaises(UserError):
            self.project.action_resume()

    # ── Tenant isolation ───────────────────────────────────────

    def test_company_id_required(self):
        """company_id is required and defaults to current company."""
        project = self.env['su.project'].create({
            'name': 'Без компании',
        })
        self.assertEqual(project.company_id, self.env.company)

    def test_monetary_fields_have_currency(self):
        """Budget fields use Monetary type with currency_id."""
        field_budget_planned = self.project._fields['budget_planned']
        field_budget_actual = self.project._fields['budget_actual']
        field_budget_deviation = self.project._fields['budget_deviation']
        self.assertEqual(field_budget_planned.type, 'monetary')
        self.assertEqual(field_budget_actual.type, 'monetary')
        self.assertEqual(field_budget_deviation.type, 'monetary')
