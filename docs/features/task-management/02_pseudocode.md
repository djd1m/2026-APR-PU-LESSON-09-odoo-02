# F03 Task Management — Pseudocode

## State Transition Methods

```python
class SuTask:

    def action_start(self):
        for task in self:
            if task.is_blocked:
                raise ValidationError("Задача заблокирована незавершёнными зависимостями.")
            if task.state != 'new':
                raise ValidationError("Начать можно только новую задачу.")
            task.state = 'in_progress'

    def action_review(self):
        for task in self:
            if task.state != 'in_progress':
                raise ValidationError("Отправить на проверку можно только задачу в работе.")
            task.state = 'review'

    def action_done(self):
        """Alias: action_complete"""
        for task in self:
            if task.state != 'review':
                raise ValidationError("Завершить можно только задачу на проверке.")
            task.state = 'done'
            task.progress = 100.0

    def action_cancel(self):
        for task in self:
            if task.state in ('done', 'cancelled'):
                raise ValidationError("Нельзя отменить завершённую или уже отменённую задачу.")
            # Warn about downstream dependents
            dependents = self.search([('dependency_ids', 'in', task.id)])
            active_dependents = dependents.filtered(
                lambda t: t.state not in ('done', 'cancelled')
            )
            if active_dependents:
                # Log warning but allow cancel
                task.message_post(
                    body=f"Внимание: {len(active_dependents)} зависимых задач будут заблокированы."
                )
            task.state = 'cancelled'

    def action_reopen(self):
        for task in self:
            if task.state not in ('review', 'done'):
                raise ValidationError("Вернуть в работу можно только задачу на проверке или завершённую.")
            task.state = 'in_progress'
            if task.progress == 100.0:
                task.progress = 99.0  # Reset from 100% to indicate reopened
```

## Dependency Engine

```python
    @api.depends('dependency_ids.state')
    def _compute_is_blocked(self):
        for task in self:
            task.is_blocked = any(
                dep.state not in ('done', 'cancelled')
                for dep in task.dependency_ids
            )

    @api.constrains('dependency_ids')
    def _check_circular_dependency(self):
        for task in self:
            visited = set()
            stack = list(task.dependency_ids.ids)
            while stack:
                dep_id = stack.pop()
                if dep_id == task.id:
                    raise ValidationError(
                        "Обнаружена циклическая зависимость задач."
                    )
                if dep_id not in visited:
                    visited.add(dep_id)
                    dep_task = self.browse(dep_id)
                    stack.extend(dep_task.dependency_ids.ids)
```

## Subtask Progress Aggregation

```python
    @api.depends('child_ids.progress', 'child_ids.state')
    def _compute_progress(self):
        for task in self:
            children = task.child_ids.filtered(
                lambda c: c.state != 'cancelled'
            )
            if children:
                task.progress = sum(children.mapped('progress')) / len(children)
            # If no children, keep manual progress (no write)

    subtask_count = fields.Integer(compute='_compute_subtask_count')

    def _compute_subtask_count(self):
        for task in self:
            task.subtask_count = len(task.child_ids)
```

## Brigade Computed Fields

```python
class SuBrigade:

    member_count = fields.Integer(compute='_compute_member_count', store=True)
    active_task_count = fields.Integer(compute='_compute_active_task_count')

    @api.depends('member_ids')
    def _compute_member_count(self):
        for brigade in self:
            brigade.member_count = len(brigade.member_ids)

    def _compute_active_task_count(self):
        for brigade in self:
            brigade.active_task_count = self.env['su.task'].search_count([
                ('brigade_id', '=', brigade.id),
                ('state', 'in', ('new', 'in_progress', 'review')),
            ])
```

## Notification on Assignment

```python
    def write(self, vals):
        old_brigades = {task.id: task.brigade_id for task in self}
        result = super().write(vals)
        if 'brigade_id' in vals:
            for task in self:
                if task.brigade_id and task.brigade_id != old_brigades.get(task.id):
                    partners = task.brigade_id.member_ids.mapped('partner_id')
                    if task.brigade_id.foreman_id:
                        partners |= task.brigade_id.foreman_id.partner_id
                    task.message_post(
                        body=f"Задача назначена на бригаду: {task.brigade_id.name}",
                        partner_ids=partners.ids,
                        message_type='notification',
                        subtype_xmlid='mail.mt_comment',
                    )
        return result
```

## RBAC Record Rules (XML)

```xml
<!-- Foreman: own brigade tasks only -->
<record id="su_task_rule_foreman" model="ir.rule">
    <field name="name">Прораб: задачи своей бригады</field>
    <field name="model_id" ref="model_su_task"/>
    <field name="groups" eval="[(4, ref('su_base.group_su_foreman'))]"/>
    <field name="domain_force">
        ['|',
         ('brigade_id.foreman_id', '=', user.id),
         ('brigade_id.member_ids', 'in', user.id)]
    </field>
</record>

<!-- Manager: all tasks -->
<record id="su_task_rule_manager" model="ir.rule">
    <field name="name">Руководитель: все задачи</field>
    <field name="model_id" ref="model_su_task"/>
    <field name="groups" eval="[(4, ref('su_base.group_su_manager'))]"/>
    <field name="domain_force">[(1, '=', 1)]</field>
</record>
```
