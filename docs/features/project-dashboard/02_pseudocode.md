# Pseudocode — F02: Dashboard объектов

## 1. Model Enhancement: su.project

```python
class SuProject(models.Model):
    # ... existing fields ...

    # NEW: Health status computed field
    health_status = Selection([green, yellow, red], compute, store)
    budget_deviation = Monetary(compute, store)  # absolute deviation
    budget_deviation_pct = Float(compute, store)  # percentage deviation
    task_count = Integer(compute, store)
    overdue = Boolean(compute, store)

    @api.depends(budget_actual, budget_planned)
    def _compute_budget_deviation():
        for project:
            if budget_planned > 0:
                deviation = budget_actual - budget_planned
                deviation_pct = (deviation / budget_planned) * 100
            else:
                deviation = 0
                deviation_pct = 0
            project.budget_deviation = deviation
            project.budget_deviation_pct = deviation_pct

    @api.depends(budget_deviation_pct, end_date)
    def _compute_health_status():
        for project:
            today = fields.Date.today()
            is_overdue = end_date AND end_date < today
            is_near_deadline = end_date AND end_date < today + 7 days
            pct = budget_deviation_pct

            if is_overdue OR pct > 15:
                health_status = 'red'
            elif is_near_deadline OR (pct > 5 AND pct <= 15):
                health_status = 'yellow'
            else:
                health_status = 'green'

    @api.depends(task_ids)
    def _compute_task_count():
        for project:
            task_count = len(task_ids)

    @api.depends(end_date)
    def _compute_overdue():
        for project:
            overdue = end_date AND end_date < today

    # State transition actions
    def action_start():
        assert state == 'draft'
        write(state='active', start_date=today if not start_date)

    def action_pause():
        assert state == 'active'
        write(state='paused')

    def action_resume():
        assert state == 'paused'
        write(state='active')

    def action_done():
        assert state == 'active'
        write(state='done')
```

## 2. View Updates

### Tree View Enhancement
```xml
tree:
    add health_status field with badge widget + color decorations
    add budget_deviation_pct display
    row decoration based on health_status:
        decoration-danger = health_status == 'red'
        decoration-warning = health_status == 'yellow'
        decoration-success = health_status == 'green'
```

### Form View Enhancement
```xml
form:
    header:
        button action_start (visible if state == draft)
        button action_pause (visible if state == active)
        button action_resume (visible if state == paused)
        button action_done (visible if state == active)
        statusbar

    sheet:
        title + health_status badge
        group columns (existing + health fields)
        notebook:
            page Задачи (existing)
            page Сметы (existing)
            page Фото (existing)
            page Бюджет:
                budget_planned, budget_actual, budget_deviation
                budget_deviation_pct with color
```

### Kanban View Enhancement
```xml
kanban grouped by state:
    card:
        name (title)
        health_status badge (colored)
        progress bar
        budget_planned / budget_actual
        manager avatar
        end_date with overdue indicator
```

### Search View
```xml
search:
    field name
    field address
    field manager_id
    filter "В работе" domain=[state=active]
    filter "Проблемные" domain=[health_status in (yellow, red)]
    filter "Просроченные" domain=[overdue=True]
    group_by state
    group_by project_type
    group_by manager_id
    group_by health_status
```

## 3. Dashboard Action
```xml
act_window "Dashboard объектов":
    res_model = su.project
    view_mode = tree,kanban,form
    context = {search_default_filter_active: 1}
    domain = []  # company_id filtering via record rules
```

## 4. Test Scenarios

```python
class TestSuProject(TransactionCase):
    def setUp():
        create project with budget_planned = 1_000_000

    test_health_green():
        set budget_actual = 1_000_000  (0% over)
        assert health_status == 'green'

    test_health_yellow_budget():
        set budget_actual = 1_100_000  (10% over)
        assert health_status == 'yellow'

    test_health_red_budget():
        set budget_actual = 1_200_000  (20% over)
        assert health_status == 'red'

    test_health_red_overdue():
        set end_date = yesterday
        assert health_status == 'red'

    test_health_yellow_near_deadline():
        set end_date = today + 3 days, budget within 5%
        assert health_status == 'yellow'

    test_progress_computation():
        create 2 tasks with progress 50 and 100
        assert project.progress == 75

    test_budget_actual_computation():
        create confirmed estimate total_amount = 500_000
        create draft estimate total_amount = 200_000
        assert budget_actual == 500_000  (only confirmed)

    test_tenant_isolation():
        create project in company A
        switch to company B
        assert project not in search results

    test_state_transitions():
        assert draft -> active via action_start
        assert active -> paused via action_pause
        assert paused -> active via action_resume
        assert active -> done via action_done
        assert draft -> done raises error
```
