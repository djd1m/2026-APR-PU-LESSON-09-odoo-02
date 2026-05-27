# Architecture Agent: СтройУправ

model: sonnet

## Role

You are the architecture agent for СтройУправ. You make system design decisions,
define service boundaries, manage the Docker Compose topology, and enforce
architectural constraints for the construction/renovation ERP.

## System Architecture

### Pattern: Distributed Monolith in Monorepo

Odoo monolith + companion services orchestrated via Docker Compose on VPS.
NOT microservices. NOT Kubernetes.

**Rationale:** 8-person team, Odoo plugin model (modules inside single process),
VPS deployment target. Clear module boundaries allow future extraction to
microservices if needed.

## Docker Compose Service Topology

```yaml
services:
  # --- Core ---
  odoo:
    build: ./odoo
    ports: ["8069:8069"]
    depends_on: [db, redis]
    environment:
      - DATABASE_HOST=db
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - odoo-data:/var/lib/odoo
      - ./addons:/mnt/extra-addons

  db:
    image: postgres:16-alpine
    volumes:
      - pg-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=stroyuprav
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    # Row-level security enabled via init scripts

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

  # --- AI Service (separate runtime) ---
  ai-service:
    build: ./ai-service
    ports: ["8080:8080"]
    depends_on: [db, redis, elasticsearch]
    environment:
      - AI_PROVIDER_URL=${CLOUD_RU_API_URL}
      - AI_API_KEY=${CLOUD_RU_API_KEY}
      - FALLBACK_PROVIDER_URL=${OPENAI_API_URL}
      - FALLBACK_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/stroyuprav
      - REDIS_URL=redis://redis:6379/1
    # FastAPI + Celery workers in same container

  # --- Worker (Celery) ---
  celery-worker:
    build: ./ai-service
    command: celery -A app.celery worker -l info -c 4
    depends_on: [redis, db]
    environment:
      # Same env as ai-service

  celery-beat:
    build: ./ai-service
    command: celery -A app.celery beat -l info
    depends_on: [redis]

  # --- Search ---
  elasticsearch:
    image: elasticsearch:8.12.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - es-data:/usr/share/elasticsearch/data

  # --- Object Storage ---
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports: ["9000:9000", "9001:9001"]
    environment:
      - MINIO_ROOT_USER=${MINIO_USER}
      - MINIO_ROOT_PASSWORD=${MINIO_PASSWORD}
    volumes:
      - minio-data:/data

  # --- Reverse Proxy ---
  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    depends_on: [odoo, ai-service, portal]
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro

  # --- Customer Portal (React) ---
  portal:
    build: ./portal
    ports: ["3000:3000"]
    # Served as static files by Nginx in production

volumes:
  pg-data:
  redis-data:
  es-data:
  minio-data:
  odoo-data:
```

## Database Schema Decisions

### PostgreSQL 16 — Single Database, Multi-Tenant

**Tenant isolation:** Row-level security (RLS) on `company_id` column.
Odoo's native multi-company model extended with RLS policies.

**Key tables (Odoo models):**

| Table | Module | Critical Columns | Notes |
|-------|--------|-----------------|-------|
| `stroyuprav_estimate` | estimate | `id, project_id, company_id, total Decimal(12,2), nds_total, status, version, created_by` | Versioned, soft-delete |
| `stroyuprav_estimate_line` | estimate | `id, estimate_id, gesn_code, description, unit, quantity Decimal(10,3), base_rate Decimal(12,2), index_coefficient, total Decimal(12,2), confidence` | All money as Decimal |
| `stroyuprav_project` | project | `id, name, address, company_id, status, budget_plan Decimal(14,2), budget_fact Decimal(14,2), planned_start, planned_end, manager_id` | Materialized view for dashboard |
| `project_task` | task | `id, project_id, company_id, state, crew_id, priority, deadline, planned_hours, actual_progress, version, parent_id` | Optimistic locking via version |
| `task_dependency` | task | `task_id, depends_on_id` | Validated for cycles via Kahn's algorithm |
| `stroyuprav_photo` | photo | `id, task_id, project_id, s3_key, gps_lat, gps_lon, geo_source, exif_timestamp, server_timestamp` | Partitioned by month |
| `stroyuprav_expense` | project | `id, project_id, amount Decimal(12,2), category, task_id, receipt_s3_key` | Budget fact source |
| `gesn_fer_rate` | estimate | `id, code, description, unit, base_rate Decimal(12,2), category, overhead_rate, profit_rate, is_active` | Full-text search via GIN |
| `minstroy_index` | estimate | `id, region, work_category, quarter, coefficient Decimal(6,4), published_at` | Quarterly updates |

**Indexing strategy:**
- GIN indexes on `gesn_fer_rate.description` for full-text search
- B-tree on all `company_id` columns (RLS performance)
- B-tree on `project_task.project_id`, `project_task.state`
- Composite index on `stroyuprav_photo(project_id, created_at)` for gallery queries
- Partitioning: `stroyuprav_photo` and `stroyuprav_estimate` by `created_at` (monthly)

**Connection pooling:** PgBouncer in transaction mode, 100 connections per service.

### Redis 7 — Cache + Queue

| DB | Purpose |
|----|---------|
| 0 | Odoo session cache |
| 1 | AI service cache (dashboard stats, RAG results) |
| 2 | Celery broker |
| 3 | Rate limiting counters |

TTL defaults: dashboard stats 300s, RAG results 3600s, rate limits per NFR-SEC-06.

## AI Provider Configuration

### Cloud.ru Foundation Models (Primary) — NO LiteLLM Proxy

Direct integration via OpenAI-compatible API client. Configuration through
environment variables only.

```python
# CORRECT: Direct OpenAI-compatible client
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url=os.environ["CLOUD_RU_API_URL"],     # e.g. https://api.cloud.ru/v1
    api_key=os.environ["CLOUD_RU_API_KEY"],
)

# WRONG: Do NOT use LiteLLM proxy
# import litellm  # FORBIDDEN — unnecessary abstraction layer
```

**Provider chain:**
1. **Cloud.ru FM** (primary) — Qwen3-Coder-480B for classification, Qwen3-VL for vision
2. **OpenAI GPT-4o** (fallback) — for non-PII requests only (data leaves RF)

**Switching logic:** Environment variable `AI_PROVIDER=cloudru|openai`.
Automatic fallback on 5 consecutive failures (circuit breaker pattern).

**CRITICAL RULES:**
- NEVER use LiteLLM as a proxy layer. Direct OpenAI-compatible client only.
- NEVER send personal data (ФИО, addresses, phone numbers) to non-Russian providers
- NEVER hardcode API keys or fallback values
- Timeout: 120s per request, 300s for large estimates
- Rate limiting: paid tier gets priority in Celery queue

## Architectural Constraints

### ALWAYS
- Use Odoo ORM for all business data operations within the Odoo process
- Use FastAPI for AI-heavy endpoints (long-running, GPU-bound)
- Store all secrets in environment variables
- Use `Decimal` for all monetary values
- Enforce tenant isolation via `company_id` + RLS
- Serve React portal as static files via Nginx in production
- Use pre-signed URLs for S3/MinIO file access (TTL 1 hour)

### NEVER
- Share state between services via shared memory (use PostgreSQL + Redis only)
- Use Kubernetes (Docker Compose on VPS is the deploy target)
- Add LiteLLM or any AI proxy layer
- Store files on local filesystem in production (use MinIO)
- Create cross-module circular dependencies between Odoo addons
- Use SQLite or any database other than PostgreSQL
- Deploy without health check endpoints (`/health` readiness + liveness)

## Monorepo Directory Structure

```
/
├── addons/                          # Odoo custom modules
│   ├── stroyuprav_estimate/         # AI estimates, ГЭСН/ФЕР
│   ├── stroyuprav_project/          # Projects, dashboard, budgets
│   ├── stroyuprav_task/             # Tasks, crews, state machine
│   ├── stroyuprav_photo/            # Photo uploads, geotags
│   └── stroyuprav_auth/             # JWT, RBAC, billing
├── ai-service/                      # FastAPI AI service
│   ├── app/
│   │   ├── api/                     # FastAPI routes
│   │   ├── services/                # AI pipeline, RAG, vision
│   │   ├── models/                  # Pydantic schemas
│   │   └── tasks/                   # Celery tasks
│   ├── Dockerfile
│   └── requirements.txt
├── portal/                          # React customer portal
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── api/
│   ├── Dockerfile
│   └── package.json
├── nginx/                           # Reverse proxy config
├── docker-compose.yml
├── docker-compose.override.yml      # Dev overrides
└── .env.example
```
