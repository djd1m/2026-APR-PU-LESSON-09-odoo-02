# СтройУправ

Mobile-first ERP for construction and renovation with AI-powered cost estimation.

**Смета за 5 минут по ГЭСН/ФЕР + все объекты в одном экране + AI-прогнозы**

## Quick Start

```bash
git clone git@github.com:<org>/2026-APR-PU-LESSON-09-odoo-02.git
cd 2026-APR-PU-LESSON-09-odoo-02
cp .env.example .env    # fill in secrets
docker compose up -d
open http://localhost:8069
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend (ERP) | Python 3.12, Odoo 17 ORM |
| Backend (AI) | Python 3.12, FastAPI |
| Frontend (ERP) | OWL Framework (Odoo) |
| Frontend (Portal) | React 18, TypeScript |
| Mobile | PWA (Phase 1), React Native (Phase 2) |
| Database | PostgreSQL 16 |
| AI Models | Cloud.ru Foundation Models (primary), OpenAI/Anthropic (fallback) |
| Search | Elasticsearch (GESN/FER normative base, 200K+ entries) |
| Queue | Redis 7 + Celery |
| Storage | MinIO (S3-compatible) |
| Payments | YooKassa |
| Deploy | Docker Compose on VPS |

## Architecture

```
                         +---------------------------+
                         |     Nginx (reverse proxy)  |
                         |       :80 / :443           |
                         +------+------------+-------+
                                |            |
                    +-----------+--+    +----+-----------+
                    | OWL Frontend |    | React Portal   |
                    | (ERP UI)     |    | (customer view)|
                    +------+-------+    +----+-----------+
                           |                 |
                    +------+-----------------+-------+
                    |         API Gateway (Nginx)     |
                    +------+-------------------+-----+
                           |                   |
                +----------+------+   +--------+---------+
                |  Odoo Backend   |   | FastAPI AI Service|
                |  :8069          |   | :8000             |
                |                 |   |                   |
                | - Projects      |   | - AI estimates    |
                | - Tasks         |   | - Drawing parser  |
                | - Budgets       |   | - Analytics       |
                | - Photos        |   | - KS-2/KS-3 gen  |
                | - Auth/Billing  |   |                   |
                +--+---------+----+   +--+-------+--------+
                   |         |           |       |
            +------+--+  +--+-----+  +--+---+ +-+--------+
            |Postgres |  | Redis  |  |MinIO | |Elastic-  |
            |:5432    |  | :6379  |  |:9000 | |search    |
            +---------+  +---+----+  +------+ |:9200     |
                             |                +----------+
                        +----+-----+
                        |  Celery  |
                        | worker   |
                        | + beat   |
                        +----------+
```

## MVP Features (P0)

- **AI Cost Estimator** -- generate GESN/FER estimates from text or blueprints in under 5 minutes
- **Project Dashboard** -- all construction sites with progress, budget, deadlines on one screen
- **Task Management** -- assign tasks to crews, track statuses, dependencies
- **Photo Documentation** -- geotagged photos linked to tasks, automatic progress updates
- **Real-time Budget** -- actual vs planned costs per project, AI alerts on deviations
- **Mobile App (PWA)** -- full-featured mobile interface for on-site workers
- **Onboarding Quiz** -- 4 questions to personalize the UI in 3 minutes
- **Auth and Billing** -- JWT auth, YooKassa subscriptions, 14-day trial

## Documentation

| Document | Path |
|----------|------|
| Product Requirements | [docs/PRD.md](docs/PRD.md) |
| Architecture | [docs/Architecture.md](docs/Architecture.md) |
| Specification | [docs/Specification.md](docs/Specification.md) |
| Development Guide | [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) |

## License

Proprietary. Odoo Community Edition components are licensed under LGPL-v3.
