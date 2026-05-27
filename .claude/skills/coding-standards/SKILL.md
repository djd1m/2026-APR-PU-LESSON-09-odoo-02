---
name: coding-standards
description: >
  Tech-specific coding patterns for СтройУправ: Odoo ORM (models, views, actions),
  FastAPI async patterns, React component patterns, PostgreSQL query patterns.
version: "1.0"
maturity: production
---

# Coding Standards: СтройУправ

## Odoo ORM Patterns

### Model Definition
```python
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SuEstimate(models.Model):
    _name = 'su.estimate'
    _description = 'Строительная смета'
    _order = 'create_date desc'

    name = fields.Char(string='Название', required=True)
    project_id = fields.Many2one('su.project', string='Объект', required=True, ondelete='cascade')
    total_amount = fields.Monetary(string='Итого', compute='_compute_total', store=True, currency_field='currency_id')
    state = fields.Selection([
        ('draft', 'Черновик'),
        ('confirmed', 'Утверждена'),
        ('archived', 'Архив'),
    ], default='draft')

    @api.depends('item_ids.amount')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.item_ids.mapped('amount'))

    @api.constrains('total_amount')
    def _check_positive_total(self):
        for rec in self:
            if rec.total_amount < 0:
                raise ValidationError('Сумма сметы не может быть отрицательной')
```

### Access Control (ir.model.access.csv)
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
su_estimate_manager,su.estimate.manager,model_su_estimate,su_base.group_su_manager,1,1,1,1
su_estimate_foreman,su.estimate.foreman,model_su_estimate,su_base.group_su_foreman,1,0,0,0
```

## FastAPI Patterns

### AI Client (no proxy, env-based switch)
```python
from openai import AsyncOpenAI
from app.config import settings

ai_client = AsyncOpenAI(
    base_url=settings.AI_BASE_URL,  # Cloud.ru or OpenAI
    api_key=settings.AI_API_KEY,
)

async def generate_estimate(description: str) -> EstimateResult:
    response = await ai_client.chat.completions.create(
        model=settings.AI_ESTIMATE_MODEL,  # e.g., "Qwen3-Coder-480B"
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    return parse_estimate(response.choices[0].message.content)
```

### Router Pattern
```python
from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user

router = APIRouter(prefix="/api/v1/estimate", tags=["estimates"])

@router.post("/", response_model=EstimateResponse)
async def create_estimate(
    req: EstimateRequest,
    user = Depends(get_current_user),
):
    # Validate tenant access
    # Generate via AI
    # Store in DB
    # Return result
```

## React Portal Patterns

### Component
```tsx
export function ProjectProgress({ projectId }: { projectId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => api.getProject(projectId),
  });
  if (isLoading) return <Skeleton />;
  return <ProgressBar value={data.progress} />;
}
```

## PostgreSQL Patterns

- Use `DECIMAL(15,2)` for money — NEVER `FLOAT`
- Index: `CREATE INDEX idx_su_task_project_status ON su_task(project_id, state);`
- Tenant isolation: every query MUST include `company_id` filter
- Use Odoo ORM — raw SQL only for reports/analytics with parameterized queries
