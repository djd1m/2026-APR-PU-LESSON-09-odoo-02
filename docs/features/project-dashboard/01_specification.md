# Specification — F02: Dashboard объектов

## 1. Overview

Feature F02 provides a comprehensive project dashboard for the СтройУправ Odoo module (`su_project`). It enables construction company managers to monitor all active projects from a single screen with real-time progress tracking, budget deviation indicators, and health status color coding.

## 2. Functional Requirements

### FR-01: Computed Progress Field
- Progress (%) is computed from linked tasks (`su.task`) as average of task progress values
- Stored computed field with `@api.depends('task_ids.progress')` trigger
- Displays as progressbar widget in tree and kanban views
- Range: 0.0 to 100.0

### FR-02: Computed Budget Actual Field
- Aggregates `total_amount` from confirmed estimates (`su.estimate` where `state == 'confirmed'`)
- Uses `fields.Monetary` with `currency_id` (never Float for money)
- Stored computed field with `@api.depends('estimate_ids.total_amount', 'estimate_ids.state')` trigger

### FR-03: Health Status Indicator
- Computed selection field `health_status` with values: `green`, `yellow`, `red`
- Logic:
  - **GREEN:** `budget_actual <= budget_planned * 1.05` AND `end_date >= today` (or no end_date)
  - **YELLOW:** `budget_actual > budget_planned * 1.05 AND budget_actual <= budget_planned * 1.15` OR `end_date < today + 7 days`
  - **RED:** `budget_actual > budget_planned * 1.15` OR `end_date < today` (overdue)
  - If `budget_planned == 0`: GREEN (no budget to compare against)
- Displayed as colored badge in tree, kanban, and form views

### FR-04: Enhanced Tree View
- Columns: name, address, project_type, state (badge), area_sqm, budget_planned, budget_actual, progress (progressbar), health_status (colored badge), manager_id, start_date, end_date
- Row decoration based on health_status

### FR-05: Enhanced Form View
- Status bar with state transitions
- Header buttons: action_start (draft->active), action_pause (active->paused), action_resume (paused->active), action_done (active->done)
- Notebook tabs: Задачи, Сметы, Фото, Бюджет
- Budget tab: planned vs actual with deviation percentage
- Health status badge in header area

### FR-06: Kanban View
- Grouped by `state` with drag-and-drop state changes
- Card shows: name, progress bar, budget plan/fact, health badge, manager avatar
- Color-coded border by health_status

### FR-07: Dashboard View (act_window with search defaults)
- Summary widgets via `<searchpanel>` or custom QWeb template not required for Odoo 17
- Instead: use search view with default filters and group-by options
- Server action for dashboard entry point with predefined domain

### FR-08: Search & Filters
- Filters: by state (active, paused, done, draft), by project_type, by health_status (problematic = yellow+red)
- Group by: state, project_type, manager_id, health_status
- Search fields: name, address, manager_id

### FR-09: Performance
- Dashboard (tree view with all projects) loads < 2 seconds
- Stored computed fields ensure no on-the-fly computation for list rendering
- Indexes on `(company_id, state)` for common queries

## 3. Non-Functional Requirements

### NFR-01: Tenant Isolation
- All queries filtered by `company_id` (Odoo multi-company record rules)
- `company_id` field is required, defaults to `self.env.company`
- Existing record rule in `su_base` module enforces this

### NFR-02: Money Precision
- All monetary values use `fields.Monetary` with `currency_field='currency_id'`
- Never use `fields.Float` for budget/cost fields
- Budget deviation computed as Monetary, not percentage stored as Float

### NFR-03: Security
- Access rights by role (foreman: read-only, manager: CRUD, admin: full, client: read-only)
- State transition buttons visible only to manager/admin roles

## 4. Acceptance Criteria

| ID | Criteria | Method |
|----|----------|--------|
| AC-01 | Dashboard shows all projects with progress %, budget fact/plan, deadlines | Manual |
| AC-02 | Health status shows GREEN/YELLOW/RED based on deviation thresholds | Unit test |
| AC-03 | Drill-down from list to project form works | Manual |
| AC-04 | Kanban grouped by state with drag-and-drop | Manual |
| AC-05 | Filters by status, type, manager, health work correctly | Manual |
| AC-06 | Dashboard loads < 2 seconds for 100 projects | Performance test |
| AC-07 | No Float for money fields | Code review |
| AC-08 | Company-based tenant isolation enforced | Unit test |
