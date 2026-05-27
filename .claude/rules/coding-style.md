# Coding Style — СтройУправ

## Python (Odoo Modules)

### Naming
- Module directory: `su_<module>` (e.g., `su_estimate`, `su_project`)
- Model class: `SuEstimate`, `SuProject` (CamelCase with `Su` prefix)
- Model `_name`: `su.estimate`, `su.project` (dotted lowercase)
- Fields: `snake_case` — `total_amount`, `created_at`
- Methods: `action_<verb>` for buttons, `_compute_<field>` for computed, `_check_<rule>` for constraints

### Module Structure
```
su_estimate/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── su_estimate.py
├── views/
│   └── su_estimate_views.xml
├── security/
│   └── ir.model.access.csv
├── data/
│   └── gesn_rates.csv
└── tests/
    └── test_su_estimate.py
```

### Patterns
- Use Odoo ORM for all DB operations — never raw SQL
- Use `@api.depends` for computed fields, `@api.constrains` for validation
- Use `self.env['model.name']` for cross-model access
- Multi-tenant: always filter by `company_id` (Odoo built-in)

## Python (FastAPI AI Service)

### Structure
```
ai_service/
├── main.py              # FastAPI app
├── routers/
│   ├── estimate.py      # /api/v1/estimate
│   └── drawing.py       # /api/v1/drawing
├── services/
│   ├── ai_client.py     # OpenAI-compatible client wrapper
│   ├── gesn_search.py   # Elasticsearch ГЭСН/ФЕР
│   └── estimator.py     # Business logic
├── models/
│   └── schemas.py       # Pydantic models
└── tests/
```

### Patterns
- Async handlers (`async def`) for all AI endpoints
- Pydantic models for request/response validation
- AI client: `OpenAI(base_url=env("AI_BASE_URL"))` — no proxy
- Use `httpx.AsyncClient` for external calls
- Celery for long-running tasks (>30s)

## TypeScript (React Portal)

### Naming
- Components: `PascalCase` — `ProjectDashboard.tsx`
- Hooks: `camelCase` with `use` prefix — `useProjects.ts`
- Types: `PascalCase` with `I` prefix for interfaces — `IProject`
- Files: match component name — `ProjectDashboard.tsx`

### Patterns
- Functional components only (no classes)
- React Query for server state
- Zustand for client state (not Redux)
- Tailwind CSS for styling

## SQL (PostgreSQL)

### Naming
- Tables: `su_<entity>` (matching Odoo model `_table`)
- Columns: `snake_case`
- Indexes: `idx_<table>_<columns>`
- Foreign keys: `fk_<table>_<ref_table>`

### Patterns
- Always use Odoo ORM or parameterized queries
- Indexes on: `(tenant_id, status)`, `(project_id, created_at)`
- Use `JSONB` for flexible fields (estimate metadata)
- Use `DECIMAL(15,2)` for money — never `FLOAT`

## Money & Numeric Types

### CRITICAL: Float vs Decimal
- **Money fields:** ALWAYS use `Monetary` (Odoo) or `Decimal` (Python/FastAPI) — **NEVER Float**
- **Odoo:** `fields.Monetary(currency_field='currency_id')` — uses Decimal internally
- **FastAPI/Pydantic:** `Decimal` from `decimal` module — `amount: Decimal = Field(..., decimal_places=2)`
- **PostgreSQL:** `DECIMAL(15,2)` or `NUMERIC(15,2)` — never `REAL` or `DOUBLE PRECISION`
- **Calculations:** Convert via `Decimal(str(value))` — never `Decimal(float_value)` (loses precision)
- **Quantity fields:** `fields.Float(digits=(16,4))` is acceptable for non-money quantities (площадь, количество)
- **WHY:** Float(0.1 + 0.2) = 0.30000000000000004. В сметах на ₽3М это даёт ошибку в тысячи рублей.

## General

### Commits
Follow Conventional Commits: `feat(estimate): add GESN lookup`

### Comments
- Only where logic isn't self-evident
- Russian for domain concepts: `# Расчёт по ГЭСН с применением индекса Минстроя`
- English for technical: `# Cache invalidation on estimate update`
