# Architecture

System architecture for StroyUprav: 9 Docker services, Odoo + FastAPI + Cloud.ru AI.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Pattern](#2-architecture-pattern)
3. [Service Map (9 Containers)](#3-service-map-9-containers)
4. [Component Diagram](#4-component-diagram)
5. [Data Flow](#5-data-flow)
6. [Odoo Modules](#6-odoo-modules)
7. [FastAPI AI Service](#7-fastapi-ai-service)
8. [Database Schema](#8-database-schema)
9. [AI Pipeline](#9-ai-pipeline)
10. [Security Architecture](#10-security-architecture)

---

## 1. System Overview

StroyUprav is a mobile-first ERP for construction and renovation, built on Odoo Community Edition with an AI cost estimator, a client portal, and Cloud.ru Foundation Models integration.

```
                            +----------------------------------+
                            |         CDN / Reverse Proxy      |
                            |           (Nginx)                |
                            +----------+-----------+-----------+
                                       |           |
                         +-------------v--+   +----v--------------+
                         |  OWL Frontend  |   |  React Portal     |
                         |  (ERP modules) |   |  (Client view)    |
                         |  + PWA Shell   |   |                   |
                         +------+---------+   +----+--------------+
                                |                  |
                    +-----------v------------------v---------------+
                    |              API Gateway (Nginx)              |
                    +---+------------------------------+----------+
                        |                              |
              +---------v----------+      +------------v----------+
              |    Odoo Backend    |      |   FastAPI AI Service  |
              |   (Python/ORM)    |      |   (AI endpoints)      |
              |                   |      |                       |
              |  - Projects       |      |  - AI Estimator       |
              |  - Tasks          |      |  - Drawing parser     |
              |  - Budgets        |      |  - AI Analytics       |
              |  - Photo reports  |      |  - KS-2/KS-3 gen     |
              |  - Auth/Billing   |      |                       |
              +--+------+---------+      +--+------+-------------+
                 |      |                   |      |
     +-----------v--+   |      +------------v--+   |
     |  PostgreSQL  |<--+      |  Cloud.ru FM  |   |
     |  (primary)   |         |  + OpenAI     |   |
     +--------------+         |  (fallback)   |   |
                              +--------------+   |
              +-------------+  +-----------------v+
              |Redis + Celery|  |  Elasticsearch   |
              |(queue/cache) |  |  (GESN/FER)      |
              +-------------+  +------------------+
              +-------------+
              |    MinIO     |
              |  (S3 photos) |
              +-------------+
```

---

## 2. Architecture Pattern

### Distributed Monolith in Monorepo

Odoo monolith + auxiliary services in a single codebase, orchestrated via Docker Compose.

| Factor | Decision |
|--------|----------|
| Team size (8 people) | Monolith is simpler for small teams, less infra overhead |
| Odoo ecosystem | Odoo modules are plugins within one process, not microservices |
| AI workloads | FastAPI runs separately -- different runtime (GPU, long polling) |
| Deploy target | VPS + Docker Compose, not Kubernetes |
| Scaling | Horizontal via Docker replicas, vertical via VPS upgrade |
| Future migration | Clear module boundaries make it easy to extract microservices later |

### Boundary Rules

- **Odoo backend** = single Python process with all business modules
- **FastAPI AI Service** = separate container, communicates with Odoo via Internal API
- **Frontend apps** = separate containers behind Nginx
- **Shared state** = only via PostgreSQL and Redis (no shared memory)

---

## 3. Service Map (9 Containers)

| # | Service | Image | Internal Port | Memory Limit | Role |
|---|---------|-------|:-------------:|:------------:|------|
| 1 | `nginx` | nginx:alpine | 80, 443 | -- | Reverse proxy, SSL termination, static files, rate limiting |
| 2 | `odoo` | Custom (Dockerfile) | 8069 | 4 GB | ERP backend: projects, tasks, budgets, photos, auth, billing |
| 3 | `fastapi-ai` | Custom (Dockerfile) | 8000 | 2 GB | AI endpoints: estimator, drawing parser, analytics |
| 4 | `postgres` | postgres:16-alpine | 5432 | 2 GB | Primary relational database (Odoo-compatible) |
| 5 | `redis` | redis:7-alpine | 6379 | 512 MB | Cache (sessions, rate limits, AI cache), Celery broker |
| 6 | `celery-worker` | Custom (Dockerfile) | -- | 2 GB | Async task execution: AI generation, PDF export, billing |
| 7 | `celery-beat` | Custom (Dockerfile) | -- | -- | Periodic task scheduler (cron-like) |
| 8 | `minio` | minio/minio:latest | 9000, 9001 | -- | S3-compatible object storage for photos, drawings, PDFs |
| 9 | `elasticsearch` | elasticsearch:8.13.0 | 9200 | 2 GB | Full-text search for GESN/FER normative database (200K+ rates) |

### Total Resource Requirements

- Minimum: ~12.5 GB RAM, 4 CPU cores
- Recommended: 16+ GB RAM, 8 CPU cores

---

## 4. Component Diagram

### Odoo Backend Modules

```
+------------------------- Odoo Backend -------------------------+
|                                                                  |
|  +---------------+ +---------------+ +---------------+          |
|  | stroyuprav_   | | stroyuprav_   | | stroyuprav_   |          |
|  | estimate      | | project       | | task          |          |
|  |               | |               | |               |          |
|  | - AI estimates| | - Projects    | | - Tasks       |          |
|  | - GESN/FER    | | - Dashboard   | | - Crews       |          |
|  | - PDF export  | | - Budgets     | | - Statuses    |          |
|  +-------+-------+ +-------+-------+ +-------+-------+          |
|          |                  |                 |                   |
|  +-------+-------+ +-------+-------+ +-------+-------+          |
|  | stroyuprav_   | | stroyuprav_   | | stroyuprav_   |          |
|  | photo         | | billing       | | onboarding    |          |
|  |               | |               | |               |          |
|  | - Photos      | | - Auth (JWT)  | | - Quiz        |          |
|  | - Geotags     | | - Subscriptions| | - Personalization|     |
|  | - S3 sync     | | - YuKassa     | |               |          |
|  +---------------+ +---------------+ +---------------+          |
|                                                                  |
|  +---------------+                                               |
|  | stroyuprav_   |                                               |
|  | portal        |                                               |
|  |               |                                               |
|  | - Client view |                                               |
|  | - Read-only   |                                               |
|  +---------------+                                               |
+------------------------------------------------------------------+
```

### FastAPI AI Service

```
+---------------------- FastAPI AI Service ----------------------+
|                                                                 |
|  +------------------+  +------------------+  +----------------+ |
|  | estimate_engine  |  | drawing_parser   |  | analytics_     | |
|  |                  |  |                  |  | engine         | |
|  | - LLM calls      |  | - OCR (Qwen3-VL)|  | - Predictions  | |
|  | - RAG lookup     |  | - Area calc      |  | - Alerts       | |
|  | - Cost calc      |  | - Work detection |  | - Reports      | |
|  | - Optimization   |  |                  |  |                | |
|  +------------------+  +------------------+  +----------------+ |
+------------------------------------------------------------------+
```

---

## 5. Data Flow

### AI Estimate Generation (from text)

```
User Input (text)
    |
    v
[Odoo Backend] -- POST /api/ai/estimates/from-text -->
    |
    v
[Celery Worker] picks up task from Redis queue
    |
    v
[FastAPI AI Service]
    |
    +-- 1. Input Parsing (Qwen3-Coder-480B)
    |      Classify text into standard work categories
    |
    +-- 2. GESN/FER Lookup
    |      Cloud.ru Managed RAG + bge-reranker
    |      Elasticsearch fallback (200K+ rates)
    |
    +-- 3. Cost Calculation
    |      base_rate * quantity * minstroy_index + overhead + profit
    |
    +-- 4. AI Optimization
    |      Flag items > 10% above market average
    |      Suggest alternative codes
    |
    v
[Result stored in PostgreSQL]
    |
    v
[User polls or receives webhook]
```

### Photo Upload Flow

```
Mobile Device (PWA)
    |
    v
Photo + GPS + Timestamp
    |
    v
[Nginx] --> [Odoo Backend]
    |
    +-- Validate (MIME + magic bytes + ClamAV)
    +-- Upload to MinIO (S3)
    +-- Store metadata in PostgreSQL
    +-- Update task progress
    +-- Recalculate project progress
```

---

## 6. Odoo Modules

| Module | Feature ID | Description |
|--------|-----------|-------------|
| `stroyuprav_estimate` | F01 | AI cost estimator: LLM integration, GESN/FER lookup, PDF/Excel export |
| `stroyuprav_project` | F02, F05 | Project dashboard, real-time budget tracking, health scores |
| `stroyuprav_task` | F03 | Task management: statuses, crews, dependencies, state machine |
| `stroyuprav_photo` | F04 | Photo reports: geotagging, S3 upload, progress tracking |
| `stroyuprav_billing` | F08 | Authentication (JWT), subscriptions (YuKassa), trial management |
| `stroyuprav_onboarding` | F07 | Onboarding quiz: 4 questions, interface personalization |
| `stroyuprav_portal` | F11 | Client portal: read-only project view (P1 release) |

All modules are installed as Odoo addons in the `custom-addons/` directory.

---

## 7. FastAPI AI Service

Located in `services/fastapi-ai/`. Runs as a separate container.

### Submodules

| Submodule | Purpose |
|-----------|---------|
| `estimate_engine` | LLM calls to Cloud.ru/OpenAI, RAG queries, cost calculation |
| `drawing_parser` | OCR via Qwen3-VL (Cloud.ru) or GPT-4o (fallback), area calculation |
| `analytics_engine` | Budget predictions, delay forecasting, AI alerts |

### AI Provider Switching

The service uses an OpenAI-compatible client. The provider is selected via environment variables:

```
CLOUDRU_API_BASE=https://api.cloud.ru/v1    # Primary
OPENAI_API_KEY=sk-...                        # Fallback
```

Automatic failover: if Cloud.ru returns an error or times out, the request is retried with OpenAI.

---

## 8. Database Schema

### Core Tables (PostgreSQL 16)

| Table | Module | Key Fields |
|-------|--------|------------|
| `stroyuprav_project` | project | name, address, status, budget_planned, budget_actual, health |
| `stroyuprav_task` | task | project_id, name, status, assignee_id, priority, due_date, depends_on |
| `stroyuprav_estimate` | estimate | project_id, description, total_cost, status, model_used |
| `stroyuprav_estimate_line` | estimate | estimate_id, gesn_code, description, quantity, unit_rate, total |
| `stroyuprav_photo` | photo | task_id, s3_key, latitude, longitude, taken_at |
| `stroyuprav_subscription` | billing | user_id, plan, status, period_start, period_end |
| `stroyuprav_payment` | billing | subscription_id, amount, yukassa_payment_id, status |
| `stroyuprav_audit_log` | billing | user_id, action, entity_type, entity_id, timestamp |

### Key Design Decisions

- **JSONB columns** for flexible metadata (estimate AI responses, quiz answers)
- **Row-level security** for tenant isolation (each company sees only its own data)
- **Materialized views** for budget aggregations (refreshed every 5 minutes)
- **Audit log** for all sensitive operations (1-year retention)

---

## 9. AI Pipeline

### GESN/FER RAG (Retrieval-Augmented Generation)

```
User text description
    |
    v
[Embedding model] -- vectorize query
    |
    v
[Cloud.ru Managed RAG]
    |-- bge-reranker for relevance scoring
    |-- Top-K matching GESN/FER codes
    |
    v
[Elasticsearch fallback]
    |-- Full-text BM25 search
    |-- 200K+ indexed rates
    |
    v
[LLM (Qwen3-Coder-480B)]
    |-- Select best-matching codes
    |-- Calculate quantities from description
    |
    v
[Cost Calculation]
    base_rate * quantity * minstroy_index + overhead_pct + profit_pct
```

### Data Flywheel

Approved estimates are saved and used to improve the model:
1. User generates AI estimate
2. User reviews and corrects inaccuracies
3. Corrected estimates are stored
4. Periodically used for fine-tuning the classification model

---

## 10. Security Architecture

### Authentication Flow

```
Registration --> Default role assigned (no role in request body)
    |
    v
Login --> JWT access token (15 min, RS256) + Refresh token (7 days)
    |        Both set as httpOnly cookies
    v
API Request --> Validate JWT --> Check RBAC --> Execute
    |
    v
Token Expired --> Use refresh token --> New access token
```

### Key Security Measures

| Layer | Measure |
|-------|---------|
| Transport | TLS 1.3 everywhere, HSTS, CORS whitelist |
| Authentication | JWT RS256 in httpOnly cookies, no localStorage |
| Authorization | RBAC + row-level security in PostgreSQL |
| Secrets | No hardcoded defaults -- crash on startup if env vars missing |
| Payments | HMAC-SHA256 webhook verification + 5-min replay protection |
| Uploads | MIME + magic bytes validation, 20 MB limit, ClamAV scan |
| Rate limiting | 100/min auth, 20/min anon, 10/min AI |
| Data residency | All data in Russia (Cloud.ru + Russian VPS) per 152-FZ |
| Audit | All sensitive operations logged, 1-year retention |
| Headers | CSP, X-Frame-Options, X-Content-Type-Options |
