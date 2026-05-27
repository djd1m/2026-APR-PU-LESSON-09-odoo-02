# StroyUprav Documentation (English)

**StroyUprav** (Russian: СтройУправ) -- Mobile-first ERP for construction and renovation with an AI cost estimator based on Russian normative databases (GESN/FER).

---

## Table of Contents

| # | Document | Description |
|---|----------|-------------|
| 1 | [Quick Start](01_quickstart.md) | Get the project running in 5 commands |
| 2 | [User Guide](02_user_guide.md) | End-user workflows: projects, estimates, tasks, photos, budget, billing |
| 3 | [Admin Guide](03_admin_guide.md) | Deployment on VPS, Docker, SSL, monitoring, backups, Cloud.ru API setup |
| 4 | [API Reference](04_api_reference.md) | REST API endpoints with request/response examples |
| 5 | [Architecture](05_architecture.md) | 9 Docker services, Odoo + FastAPI + Cloud.ru AI |
| 6 | [Troubleshooting](06_troubleshooting.md) | Common issues and fixes |
| 7 | [Changelog](07_changelog.md) | Release history |

---

## About the Project

StroyUprav replaces 5-7 disconnected tools (Excel, WhatsApp, 1C, paper estimates) with a single platform:

- **AI Estimator** -- generate cost estimates per GESN/FER standards in 5 minutes instead of days
- **Project Dashboard** -- real-time progress, budget, and deadlines for all sites on one screen
- **Task Management** -- assign tasks to crews from your phone, track statuses
- **Photo Reports** -- geotagged photos linked to tasks, automatic progress updates
- **Real-time Budget** -- actual vs. planned costs with AI alerts on deviations
- **Client Portal** -- read-only view for clients to track renovation progress

### Key Russian Domain Terms

| Russian Term | Transliteration | English Explanation |
|---|---|---|
| ГЭСН (GESN) | Gosudarstvennye Elementnye Smetnye Normy | State Elemental Estimate Norms -- federal unit-rate database for construction cost estimation |
| ФЕР (FER) | Federalnye Edinichnye Rascenki | Federal Unit Rates -- pre-calculated prices derived from GESN norms |
| ТЕР (TER) | Territorialnye Edinichnye Rascenki | Territorial Unit Rates -- regional adjustments to FER |
| КС-2 (KS-2) | | Certificate of Completed Work -- official act confirming work volumes (GOST standard) |
| КС-3 (KS-3) | | Certificate of Construction Costs -- summarizes KS-2 acts into payment amounts |
| Минстрой | Minstroy | Ministry of Construction -- publishes quarterly price indices |
| 152-ФЗ | 152-FZ | Federal Law on Personal Data -- Russian data residency requirement |
| ЮKassa | YuKassa | Russian payment gateway (bank cards, SBP instant payments, YuMoney wallet) |
| Прораб | Prorab | Site foreman / construction supervisor |

---

## Tech Stack at a Glance

| Layer | Technology |
|-------|-----------|
| Backend (ERP) | Python 3.12 + Odoo 17 ORM |
| Backend (AI) | Python 3.12 + FastAPI |
| Frontend (ERP) | OWL Framework (Odoo) + PWA |
| Frontend (Portal) | React 18 + TypeScript |
| Database | PostgreSQL 16 |
| AI Primary | Cloud.ru Foundation Models (Qwen3, DeepSeek-V3) |
| AI Fallback | OpenAI GPT-4o / Claude 3.5 |
| Queue | Redis 7 + Celery |
| Object Storage | MinIO (S3-compatible) |
| Search | Elasticsearch 8 |
| Payments | YuKassa |
| Monitoring | Prometheus + Grafana + Loki |
| Deploy | Docker Compose on VPS |

---

## License

Odoo Community Edition -- LGPL-v3. Custom modules -- proprietary.
