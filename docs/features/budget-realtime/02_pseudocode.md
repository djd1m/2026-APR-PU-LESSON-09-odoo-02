# Pseudocode: Budget Real-Time (F05)

## 1. Model: su.expense

```python
class SuExpense(models.Model):
    _name = 'su.expense'
    _description = 'Расход по объекту'
    _order = 'expense_date desc, id desc'

    FIELDS:
        name: Char, required
        project_id: Many2one('su.project'), required, ondelete='cascade'
        amount: Monetary(currency_field='currency_id'), required
        category: Selection[
            ('materials', 'Материалы'),
            ('labor', 'Работа'),
            ('equipment', 'Оборудование'),
            ('transport', 'Транспорт'),
            ('other', 'Прочее'),
        ], required, default='materials'
        expense_date: Date, required, default=today
        receipt_attachment: Binary, attachment=True
        receipt_filename: Char
        state: Selection[
            ('draft', 'Черновик'),
            ('confirmed', 'Подтверждён'),
            ('cancelled', 'Отменён'),
        ], default='draft', tracking=True
        company_id: Many2one('res.company'), required, default=env.company
        currency_id: Many2one('res.currency'), related=company_id.currency_id, store=True
        notes: Text, optional

    METHODS:
        action_confirm():
            for expense in self:
                if expense.state != 'draft': raise UserError
                expense.write({'state': 'confirmed'})
            # trigger budget alert check on project
            self.mapped('project_id')._check_budget_alert()

        action_cancel():
            for expense in self:
                if expense.state != 'confirmed': raise UserError
                expense.write({'state': 'cancelled'})

        action_reset_draft():
            for expense in self:
                if expense.state != 'cancelled': raise UserError
                expense.write({'state': 'draft'})
```

## 2. Model: su.project (modifications)

```python
# New fields
expense_ids: One2many('su.expense', 'project_id', string='Расходы')
expense_count: Integer, compute='_compute_expense_count', store=True

# Modified compute: budget_actual now sums confirmed expenses
@api.depends('expense_ids.amount', 'expense_ids.state')
def _compute_budget_actual(self):
    for project in self:
        confirmed = project.expense_ids.filtered(
            lambda e: e.state == 'confirmed'
        )
        project.budget_actual = sum(confirmed.mapped('amount'))

# New compute: expense count
@api.depends('expense_ids')
def _compute_expense_count(self):
    for project in self:
        project.expense_count = len(project.expense_ids)

# New alert method
BUDGET_ALERT_THRESHOLD = 10.0  # class constant

def _check_budget_alert(self):
    """Post chatter message when deviation exceeds threshold."""
    for project in self:
        if not project.budget_planned:
            continue
        pct = project.budget_deviation_pct
        if pct > self.BUDGET_ALERT_THRESHOLD:
            project.message_post(
                body=f"Внимание: бюджет объекта превышен на {pct:.1f}% "
                     f"(порог: {self.BUDGET_ALERT_THRESHOLD}%)",
                subject="Превышение бюджета",
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
```

## 3. Views

```
su_budget_views.xml:
    - su.expense tree view (list of expenses)
    - su.expense form view (expense details with attachment)
    - su.expense search view (filters by category, state, date)
    - su.expense pivot view (category x month, measure=amount)
    - su.expense graph view (bar chart by category)
    - Action: su_expense_action (tree,form,pivot,graph)
    - Menu item under СтройУправ → Расходы

su_project_views.xml modifications (via inherit):
    - Add "Расходы" tab in project form notebook
    - Add expense_count stat button
    - Embed expense list in project form
```

## 4. Security

```
ir.model.access.csv additions:
    - foreman: read only on su.expense
    - manager: read, write, create on su.expense
    - admin: full CRUD + delete on su.expense
    - client: read only on su.expense
```

## 5. Algorithm: Budget Alert Check

```
TRIGGER: expense.action_confirm()
FOR EACH project in affected projects:
    IF project.budget_planned == 0: SKIP
    COMPUTE pct = (budget_actual - budget_planned) / budget_planned * 100
    IF pct > BUDGET_ALERT_THRESHOLD:
        POST notification to project chatter
        (uses mail.message — standard Odoo mechanism)
```
