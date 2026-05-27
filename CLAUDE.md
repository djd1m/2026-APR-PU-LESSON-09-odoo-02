# Project: СтройУправ

## Overview

Mobile-first ERP для строительства и ремонта (РФ) с AI-сметчиком по ГЭСН/ФЕР.
Строительные и ремонтные компании РФ управляют проектами через Excel + WhatsApp + 1С + бумажные сметы, что приводит к непрозрачности бюджетов, срывам сроков (40% заказчиков) и потере данных при уходе сотрудников.
СтройУправ заменяет 5-7 инструментов одним приложением: смета за 5 минут по ГЭСН/ФЕР + все объекты в одном экране + AI-прогнозы.

## Problem & Solution

**Проблема:** Excel + WhatsApp + 1С:Бухгалтерия — разрозненные инструменты без единой картины бизнеса. Прораб уволился — информация пропала. Бюджеты непрозрачны, объекты убыточны из-за ручного учёта. Заказчик звонит каждый час, потому что нет портала прогресса.

**Решение:** Единая платформа на базе Odoo Community Edition:
- AI-сметчик автоматически генерирует сметы по ГЭСН/ФЕР за минуты вместо дней
- Dashboard объектов показывает прогресс, бюджет и сроки в реальном времени
- Mobile-first PWA позволяет прорабам фиксировать прогресс прямо с объекта
- Портал заказчика убирает необходимость звонков и WhatsApp-чатов
- AI-алерты предупреждают о перерасходах до того, как объект станет убыточным

## Architecture

- **Pattern:** Distributed Monolith (Monorepo)
- **Backend (ERP):** Python 3.12 + Odoo 17 ORM — бизнес-модули, workflow, auth
- **Backend (AI):** Python 3.12 + FastAPI — AI endpoints, RAG, чертёж-парсер
- **Frontend (ERP):** OWL Framework (Odoo) + PWA Shell
- **Frontend (Portal):** React 18 + TypeScript (SPA для заказчика)
- **Mobile:** PWA (Phase 1) -> React Native (Phase 2)
- **Database:** PostgreSQL 16 (Odoo-compatible, JSONB, row-level security)
- **AI:** Cloud.ru Foundation Models (primary) + OpenAI (fallback), OpenAI-compatible API, switch via env var `AI_BASE_URL`
- **Queue:** Redis 7 + Celery (async tasks: AI generation, PDF export, notifications)
- **Storage:** MinIO (S3-compatible) — фото, чертежи, PDF-сметы
- **Search:** Elasticsearch (ГЭСН/ФЕР full-text, 200K+ расценок)
- **Payments:** ЮKassa (банковские карты, СБП, ЮMoney, рекуррентные платежи)
- **Monitoring:** Prometheus + Grafana + Loki
- **Deploy:** Docker Compose on VPS (AdminVPS/HOSTKEY), Nginx reverse proxy

## Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend (ERP) | Python 3.12 + Odoo 17 ORM | Модульность, ORM, встроенный workflow |
| Backend (AI) | Python 3.12 + FastAPI | Async, отдельный runtime для GPU/long-running AI |
| Frontend (ERP) | OWL Framework (Odoo) | Нативная интеграция с Odoo |
| Frontend (Portal) | React 18 + TypeScript | SPA для заказчика, отдельный UX от ERP |
| Mobile | PWA -> React Native | PWA: быстрый старт; RN: push, камера, offline |
| Database | PostgreSQL 16 | Odoo-совместим, JSONB, row-level security |
| AI Primary | Cloud.ru FM (Qwen3-Coder-480B, DeepSeek-V3, T-pro-it-2.0) | Данные в РФ (152-ФЗ) |
| AI Fallback | OpenAI GPT-4o / Claude 3.5 | Resilience, A/B testing |
| RAG | Cloud.ru Managed RAG + bge-reranker | ГЭСН/ФЕР normative base |
| Search | Elasticsearch | Full-text search по ГЭСН/ФЕР |
| Queue | Redis 7 + Celery | Async tasks |
| Cache | Redis 7 | Sessions, rate limiting, AI cache |
| Object Storage | MinIO (S3-compatible) | Фото, чертежи, PDF |
| Payments | ЮKassa | Российский платёжный шлюз |
| CI/CD | GitHub Actions | Docker build + deploy |
| Containers | Docker + Docker Compose | VPS deploy |
| Hosting | VPS (AdminVPS / HOSTKEY) | Российские ЦОД, 152-ФЗ |
| Reverse Proxy | Nginx | SSL, rate limiting, static |
| Monitoring | Prometheus + Grafana | Metrics + alerts |
| Logging | Loki + Promtail | Centralized logs |

## Key Algorithms

### AI Estimator Pipeline
1. **Input parsing** — текст или чертёж (OCR via Qwen3-VL / GPT-4o fallback)
2. **Work classification** — AI классифицирует описание в стандартные виды работ (Qwen3-Coder-480B)
3. **ГЭСН/ФЕР lookup** — семантический поиск через Cloud.ru Managed RAG + bge-reranker + Elasticsearch fallback
4. **Cost calculation** — base_rate * quantity * minstroy_index + overhead + profit
5. **AI optimization** — выявление позиций > 10% дороже рынка, предложение альтернативных расценок
6. **Data flywheel** — сохранение одобренных смет для fine-tuning модели

### Budget Control
- Materialized views + Redis cache (TTL 300s) для агрегации
- Взвешенный прогресс по плановой трудоёмкости задач
- Health score: GREEN/YELLOW/RED на основе budget deviation, overdue tasks, progress lag
- AI-алерты при отклонении факт/план > 10%

### Task State Machine
```
новая -> в_работе -> на_проверке -> выполнена
любое -> отменена (кроме выполнена)
отменена -> новая (реактивация)
```
Переходы контролируются RBAC: `done` только для manager/admin, `cancelled` только для manager/admin.

## Security Rules

- JWT in httpOnly cookies (NOT localStorage) — RS256, access 15 min, refresh 7 days
- No hardcoded secrets — crash on startup if env vars missing (no fallback values)
- Role NOT assignable via register endpoint (prevent privilege escalation)
- HMAC-SHA256 verification on ЮKassa webhooks + replay protection (5 min window)
- 152-ФЗ: personal data stays in Russia (Cloud.ru + VPS в РФ)
- Input validation on ALL user-facing endpoints (Pydantic + ORM constraints)
- Row-level security in PostgreSQL for tenant isolation
- Rate limiting: 100 req/min authenticated, 20 req/min anonymous, 10 req/min AI
- File uploads: MIME + magic bytes validation, 20MB limit, ClamAV scan
- TLS 1.3 everywhere, HSTS, CORS whitelist, CSP headers
- Audit log for all sensitive operations (1 year retention)

## Monorepo Structure

```
stroyuprav/
├── addons/                          # Odoo custom modules
│   ├── stroyuprav_estimate/         # AI-сметчик (F01)
│   ├── stroyuprav_project/          # Dashboard + объекты (F02, F05)
│   ├── stroyuprav_task/             # Управление задачами (F03)
│   ├── stroyuprav_photo/            # Фотофиксация (F04)
│   ├── stroyuprav_billing/          # Auth & Billing (F08)
│   ├── stroyuprav_onboarding/       # Onboarding quiz (F07)
│   └── stroyuprav_portal/           # Портал заказчика (F11)
├── ai_service/                      # FastAPI AI Service
│   ├── estimate_engine/             # LLM calls, RAG, cost calculation
│   ├── drawing_parser/              # OCR/CV, area calculation
│   └── analytics_engine/           # Прогнозы, алерты, отчёты
├── portal/                          # React Portal (заказчик)
│   └── src/
├── shared/                          # Shared libraries (types, utils)
├── docker/                          # Docker configurations
│   ├── Dockerfile.odoo
│   ├── Dockerfile.fastapi
│   └── nginx/
├── data/                            # ГЭСН/ФЕР normative data
├── docs/                            # SPARC documentation
├── .claude/                         # Claude Code toolkit
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
└── CLAUDE.md
```

## Development Commands

- `/start` — bootstrap from SPARC docs (fresh scaffolds only)
- `/feature <name>` — full lifecycle (PLAN -> VALIDATE -> IMPLEMENT -> REVIEW)
- `/plan <name>` — lightweight plan for small changes (< 4 files)
- `/go <name>` — auto-route to /plan or /feature based on scope
- `/run mvp` — autonomous build loop
- `/myinsights "..."` — capture development insights (rakes/workarounds)
- `/docs` — generate documentation
- `/deploy` — deploy to VPS

## Available Agents

- **planner.md** — feature planning with algorithm templates from Pseudocode.md
- **code-reviewer.md** — quality review with edge cases from Refinement.md
- **architect.md** — system design decisions from Architecture.md

## Parallel Execution Strategy

- Use `Task` tool for independent subtasks (e.g., separate Odoo modules)
- Run tests, linting, type-checking in parallel
- For complex features: spawn specialized agents per work unit
- Each agent reads SPARC sections + implements + tests + commits
- Coordinator merges/integrates after all agents complete

## Key Environment Variables

| Variable | Purpose |
|----------|---------|
| `AI_BASE_URL` | AI provider endpoint (Cloud.ru or OpenAI) |
| `AI_API_KEY` | AI provider API key |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `MINIO_ENDPOINT` | MinIO S3 endpoint |
| `MINIO_ACCESS_KEY` | MinIO access key |
| `MINIO_SECRET_KEY` | MinIO secret key |
| `YUKASSA_SHOP_ID` | ЮKassa shop identifier |
| `YUKASSA_SECRET_KEY` | ЮKassa API secret |
| `YUKASSA_WEBHOOK_SECRET` | ЮKassa HMAC verification secret |

**All env vars are REQUIRED. Application MUST crash on startup if any are missing.**
