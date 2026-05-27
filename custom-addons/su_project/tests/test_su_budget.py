# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestSuBudgetRealTime(TransactionCase):
    """Tests for F05: Budget real-time — expenses, deviation, alerts."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref('base.main_company')
        cls.currency = cls.company.currency_id

        cls.project = cls.env['su.project'].create({
            'name': 'Объект Тест-Бюджет',
            'address': 'ул. Бюджетная, 5',
            'project_type': 'renovation',
            'budget_planned': 1000000.00,
            'start_date': date.today() - timedelta(days=30),
            'end_date': date.today() + timedelta(days=60),
            'company_id': cls.company.id,
        })

    # ── Expense creation ─────────────────────────────────────

    def _create_expense(self, amount, category='materials', state='draft'):
        """Helper to create an expense."""
        return self.env['su.expense'].create({
            'name': 'Тестовый расход',
            'project_id': self.project.id,
            'amount': amount,
            'category': category,
            'expense_date': date.today(),
            'company_id': self.company.id,
        })

    def test_expense_create(self):
        """Expense is created with correct defaults."""
        expense = self._create_expense(50000.00)
        self.assertEqual(expense.state, 'draft')
        self.assertEqual(expense.category, 'materials')
        self.assertEqual(expense.company_id, self.company)
        self.assertEqual(expense.currency_id, self.currency)

    # ── State transitions ────────────────────────────────────

    def test_expense_confirm(self):
        """Draft expense can be confirmed."""
        expense = self._create_expense(50000.00)
        expense.action_confirm()
        self.assertEqual(expense.state, 'confirmed')

    def test_expense_cancel(self):
        """Confirmed expense can be cancelled."""
        expense = self._create_expense(50000.00)
        expense.action_confirm()
        expense.action_cancel()
        self.assertEqual(expense.state, 'cancelled')

    def test_expense_reset_draft(self):
        """Cancelled expense can be reset to draft."""
        expense = self._create_expense(50000.00)
        expense.action_confirm()
        expense.action_cancel()
        expense.action_reset_draft()
        self.assertEqual(expense.state, 'draft')

    def test_expense_confirm_not_draft_raises(self):
        """Cannot confirm a non-draft expense."""
        expense = self._create_expense(50000.00)
        expense.action_confirm()
        with self.assertRaises(UserError):
            expense.action_confirm()

    def test_expense_cancel_not_confirmed_raises(self):
        """Cannot cancel a draft expense."""
        expense = self._create_expense(50000.00)
        with self.assertRaises(UserError):
            expense.action_cancel()

    def test_expense_reset_not_cancelled_raises(self):
        """Cannot reset a confirmed expense to draft."""
        expense = self._create_expense(50000.00)
        expense.action_confirm()
        with self.assertRaises(UserError):
            expense.action_reset_draft()

    # ── Budget actual from expenses ──────────────────────────

    def test_budget_actual_from_expenses(self):
        """budget_actual sums only confirmed expenses."""
        e1 = self._create_expense(300000.00)
        e2 = self._create_expense(200000.00)
        e3 = self._create_expense(100000.00)  # stays draft
        e1.action_confirm()
        e2.action_confirm()
        self.project.invalidate_recordset()
        self.assertAlmostEqual(
            self.project.budget_actual, 500000.00, places=2
        )

    def test_budget_actual_excludes_cancelled(self):
        """Cancelled expenses are excluded from budget_actual."""
        e1 = self._create_expense(300000.00)
        e2 = self._create_expense(200000.00)
        e1.action_confirm()
        e2.action_confirm()
        e2.action_cancel()
        self.project.invalidate_recordset()
        self.assertAlmostEqual(
            self.project.budget_actual, 300000.00, places=2
        )

    def test_budget_actual_no_expenses(self):
        """budget_actual is 0 when no expenses exist."""
        # Create a fresh project with no expenses
        project = self.env['su.project'].create({
            'name': 'Пустой проект',
            'budget_planned': 500000.00,
            'company_id': self.company.id,
        })
        self.assertAlmostEqual(project.budget_actual, 0.0, places=2)

    # ── Budget deviation ─────────────────────────────────────

    def test_budget_deviation_pct_computed(self):
        """Deviation percentage computed correctly."""
        e1 = self._create_expense(1100000.00)  # 10% over 1M plan
        e1.action_confirm()
        self.project.invalidate_recordset()
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
        expense = self.env['su.expense'].create({
            'name': 'Расход',
            'project_id': project.id,
            'amount': 50000.00,
            'expense_date': date.today(),
            'company_id': self.company.id,
        })
        expense.action_confirm()
        project.invalidate_recordset()
        self.assertEqual(project.budget_deviation_pct, 0.0)

    # ── Budget alert ─────────────────────────────────────────

    def test_budget_alert_triggered(self):
        """Alert posted when deviation exceeds 10% threshold."""
        e1 = self._create_expense(1150000.00)  # 15% over
        messages_before = len(self.project.message_ids)
        e1.action_confirm()
        self.project.invalidate_recordset()
        messages_after = len(self.project.message_ids)
        self.assertGreater(
            messages_after, messages_before,
            'Budget alert message should be posted to chatter'
        )

    def test_budget_alert_not_triggered_below_threshold(self):
        """No alert when deviation is at or below 10%."""
        # Use a fresh project to avoid interference
        project = self.env['su.project'].create({
            'name': 'Проект без алерта',
            'budget_planned': 1000000.00,
            'company_id': self.company.id,
        })
        expense = self.env['su.expense'].create({
            'name': 'Расход в пределах',
            'project_id': project.id,
            'amount': 1050000.00,  # 5% over — below 10% threshold
            'expense_date': date.today(),
            'company_id': self.company.id,
        })
        messages_before = len(project.message_ids)
        expense.action_confirm()
        project.invalidate_recordset()
        messages_after = len(project.message_ids)
        self.assertEqual(
            messages_after, messages_before,
            'No alert should be posted below threshold'
        )

    # ── Expense count ────────────────────────────────────────

    def test_expense_count(self):
        """expense_count reflects number of linked expenses."""
        self._create_expense(10000.00)
        self._create_expense(20000.00)
        self.project.invalidate_recordset()
        self.assertEqual(self.project.expense_count, 2)

    # ── Monetary type verification ───────────────────────────

    def test_monetary_type(self):
        """Expense amount field is Monetary, not Float."""
        field_amount = self.env['su.expense']._fields['amount']
        self.assertEqual(
            field_amount.type, 'monetary',
            'amount MUST be Monetary — never Float for money'
        )

    # ── Company / tenant isolation ───────────────────────────

    def test_company_required(self):
        """company_id defaults to current company."""
        expense = self._create_expense(10000.00)
        self.assertEqual(expense.company_id, self.env.company)

    # ── Negative amount (refund) ─────────────────────────────

    def test_negative_amount_allowed(self):
        """Negative amounts (refunds) are allowed and reduce actual."""
        e1 = self._create_expense(500000.00)
        e2 = self._create_expense(-50000.00)  # refund
        e1.action_confirm()
        e2.action_confirm()
        self.project.invalidate_recordset()
        self.assertAlmostEqual(
            self.project.budget_actual, 450000.00, places=2
        )
