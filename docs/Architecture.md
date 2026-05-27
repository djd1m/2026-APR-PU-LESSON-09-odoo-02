# Architecture: СтройУправ

## 1. System Overview

СтройУправ — mobile-first ERP для строительства и ремонта, построенный
на базе Odoo Community Edition с AI-сметчиком, порталом заказчика и
интеграцией Cloud.ru Foundation Models.

```
                            ┌──────────────────────────────────┐
                            │         CDN / Reverse Proxy      │
                            │           (Nginx / Caddy)        │
                            └──────────┬───────────┬───────────┘
                                       │           │
                         ┌─────────────▼──┐   ┌────▼──────────────┐
                         │  OWL Frontend  │   │  React Portal     │
                         │  (ERP modules) │   │  (Заказчик view)  │
                         │  + PWA Shell   │   │                   │
                         └──────┬─────────┘   └────┬──────────────┘
                                │                  │
                    ┌───────────▼──────────────────▼───────────────┐
                    │              API Gateway (Nginx)             │
                    └───┬──────────────────────────────┬───────────┘
                        │                              │
              ┌─────────▼──────────┐      ┌────────────▼──────────┐
              │    Odoo Backend    │      │   FastAPI AI Service  │
              │   (Python/ORM)    │      │   (AI endpoints)      │
              │                   │      │                       │
              │  - Объекты/Projects│      │  - AI-сметчик         │
              │  - Задачи/Tasks   │      │  - Чертёж parser      │
              │  - Бюджеты        │      │  - AI-аналитика       │
              │  - Фотофиксация   │      │  - Генерация КС-2/3  │
              │  - Auth/Billing   │      │                       │
              └──┬──────┬─────────┘      └──┬──────┬─────────────┘
                 │      │                   │      │
     ┌───────────▼──┐   │      ┌────────────▼──┐   │
     │  PostgreSQL  │◄──┘                    │      │
     │  (primary)   │                       │      │
     └──────────────┘           ┌───────────▼──┐   │
                                │ OpenAI-      │   │
              ┌─────────────┐   │ compatible   │   │
              │Redis + Celery│   │ client       │   │
              │(queue/cache) │   │ (env switch) │   │
              └─────────────┘   └──┬──────┬────┘   │
                                   │      │        │
                                ┌──▼──┐ ┌─▼───────┐│
                                │Cloud│ │OpenAI/  ││
                                │.ru  │ │Anthropic││
                                │FM   │ │(fallback)│
                                └─────┘ └─────────┘│
              ┌─────────────┐  ┌──────────────────┐ │
              │    MinIO     │  │  Elasticsearch   │ │
              │  (S3 photos) │  │  (ГЭСН/ФЕР)     │◄┘
              └─────────────┘  └──────────────────┘
```

---

## 2. Architecture Pattern

### Distributed Monolith in Monorepo

**Pattern:** Odoo monolith + вспомогательные сервисы в единой кодовой базе,
оркестрированные через Docker Compose.

**Rationale:**

| Factor                 | Decision                                          |
|------------------------|---------------------------------------------------|
| Команда (8 чел.)       | Monolith проще для малой команды, меньше infra overhead |
| Odoo ecosystem         | Odoo модули — plugins внутри одного процесса, не микросервисы |
| AI workloads           | FastAPI отдельно — разные runtime (GPU, long polling) |
| Deploy target          | VPS + Docker Compose, не Kubernetes               |
| Масштабирование        | Горизонтальное через Docker replicas, вертикальное через VPS |
| Future migration path  | Чёткие границы модулей -> легко выделить в микросервисы |

**Boundary rules:**

- Odoo backend = единый Python-процесс со всеми бизнес-модулями
- FastAPI AI Service = отдельный контейнер, общается с Odoo через Internal API
- Frontend apps = отдельные контейнеры за Nginx
- Shared state = только через PostgreSQL и Redis (никакого shared memory)

---

## 3. Component Diagram

```
┌─────────────────────────────── Monorepo ───────────────────────────────┐
│                                                                        │
│  ┌─────────────────── Odoo Backend ───────────────────────────┐       │
│  │                                                             │       │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐│       │
│  │  │stroyuprav_ │ │stroyuprav_ │ │stroyuprav_ │ │stroyuprav││       │
│  │  │estimate    │ │project     │ │task        │ │_photo    ││       │
│  │  │            │ │            │ │            │ │          ││       │
│  │  │- AI-сметы  │ │- Объекты   │ │- Задачи   │ │- Фото    ││       │
│  │  │- ГЭСН/ФЕР │ │- Dashboard │ │- Бригады  │ │- Геотег  ││       │
│  │  │- Экспорт   │ │- Бюджеты   │ │- Статусы  │ │- S3 sync ││       │
│  │  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └────┬─────┘│       │
│  │        │              │              │              │       │       │
│  │  ┌─────┴──────┐ ┌─────┴──────┐ ┌─────┴──────┐            │       │
│  │  │stroyuprav_ │ │stroyuprav_ │ │stroyuprav_ │            │       │
│  │  │billing     │ │onboarding  │ │portal      │            │       │
│  │  │            │ │            │ │            │            │       │
│  │  │- ЮKassa    │ │- Quiz 4Q   │ │- Заказчик  │            │       │
│  │  │- Подписки  │ │- Persona   │ │- Read-only │            │       │
│  │  │- Trial 14d │ │- UI config │ │- API       │            │       │
│  │  └────────────┘ └────────────┘ └────────────┘            │       │
│  │                                                           │       │
│  └───────────────────────────────────────────────────────────┘       │
│                                                                      │
│  ┌─────────────────── FastAPI AI Service ────────────────────┐       │
│  │                                                           │       │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐           │       │
│  │  │estimate_   │ │drawing_    │ │analytics_  │           │       │
│  │  │engine      │ │parser      │ │engine      │           │       │
│  │  │            │ │            │ │            │           │       │
│  │  │- LLM calls │ │- OCR/CV    │ │- Прогнозы  │           │       │
│  │  │- RAG query │ │- Area calc │ │- Алерты    │           │       │
│  │  │- КС-2/КС-3│ │- Room det. │ │- Отчёты    │           │       │
│  │  └────────────┘ └────────────┘ └────────────┘           │       │
│  │                                                           │       │
│  └───────────────────────────────────────────────────────────┘       │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐          │
│  │ OWL Frontend │  │ React Portal │  │ Shared Libraries  │          │
│  │ (ERP UI)     │  │ (Заказчик)   │  │ (types, utils)    │          │
│  └──────────────┘  └──────────────┘  └───────────────────┘          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Module Interaction Map

```
stroyuprav_estimate ──▶ FastAPI AI Service (LLM calls)
                    ──▶ stroyuprav_project (link estimate to object)

stroyuprav_project  ──▶ stroyuprav_task (tasks per project)
                    ──▶ stroyuprav_estimate (budget from estimates)
                    ──▶ stroyuprav_billing (subscription check)

stroyuprav_task     ──▶ stroyuprav_photo (photo per task)
                    ──▶ stroyuprav_project (parent reference)

stroyuprav_photo    ──▶ MinIO S3 (file storage)
                    ──▶ stroyuprav_task (link back)

stroyuprav_billing  ──▶ ЮKassa API (payments)
                    ──▶ Odoo res.partner (customer records)

stroyuprav_portal   ──▶ stroyuprav_project (read-only views)
                    ──▶ stroyuprav_photo (gallery)

stroyuprav_onboarding ──▶ res.users (profile setup)
```

---

## 4. Tech Stack Decision Matrix

| Layer           | Technology                        | Rationale                                                  |
|-----------------|-----------------------------------|------------------------------------------------------------|
| **Backend (ERP)** | Python 3.12 + Odoo 17 ORM       | Российский рынок ERP, модульность, ORM, встроенный workflow |
| **Backend (AI)** | Python 3.12 + FastAPI            | Async, отдельный runtime для GPU/long-running AI tasks      |
| **Frontend (ERP)** | OWL Framework (Odoo)           | Нативная интеграция с Odoo, rich components                 |
| **Frontend (Portal)** | React 18 + TypeScript       | SPA для заказчика, отдельный UX от ERP                      |
| **Mobile**      | PWA (Phase 1) → React Native (Phase 2) | PWA: быстрый старт; RN: push, камера, offline              |
| **Database**    | PostgreSQL 16                    | Odoo-совместим, JSONB для flexible fields, отлично масштабируется |
| **AI/ML**       | Cloud.ru Foundation Models (primary) | Данные в РФ (152-ФЗ), OpenAI-compatible API               |
| **AI Fallback** | OpenAI / Anthropic               | Resilience, A/B testing моделей. Тот же OpenAI-compatible API |
| **RAG**         | Cloud.ru Managed RAG             | ГЭСН/ФЕР normative base, managed infrastructure            |
| **Fine-tuning** | Cloud.ru ML Finetuning           | Custom estimate model на исторических сметах                 |
| **Search**      | Elasticsearch / Meilisearch      | Full-text search по ГЭСН/ФЕР (200K+ расценок)             |
| **Queue**       | Redis 7 + Celery                 | Async tasks: AI generation, PDF export, notifications       |
| **Cache**       | Redis 7                          | Session cache, rate limiting, AI response cache              |
| **Object Storage** | MinIO (S3-compatible)         | Фото, чертежи, PDF-сметы. Self-hosted, S3 API              |
| **Payments**    | ЮKassa                           | Единственный крупный платёжный шлюз РФ с хорошим API        |
| **CI/CD**       | GitHub Actions                   | Встроен в GitHub, Docker build + deploy                      |
| **Containers**  | Docker + Docker Compose          | Стандарт для VPS deploy, без overhead Kubernetes             |
| **Hosting**     | VPS (AdminVPS / HOSTKEY)         | Российские ЦОД, 152-ФЗ compliance, стоимость ниже облаков  |
| **Reverse Proxy** | Nginx                          | SSL termination, rate limiting, static files                 |
| **Monitoring**  | Prometheus + Grafana             | Метрики, алерты, dashboards                                  |
| **Logging**     | Loki + Promtail                  | Centralized logs, Grafana integration                        |

### AI Model Selection

| Model                | Provider  | Use Case                        | Why                                |
|----------------------|-----------|----------------------------------|------------------------------------|
| Qwen3-Coder-480B    | Cloud.ru  | AI-сметы generation             | Best code/structured output, large context |
| DeepSeek-V3         | Cloud.ru  | Аналитика, отчёты               | Strong reasoning, cost-effective    |
| T-pro-it-2.0        | Cloud.ru  | Russian NLP (описания, чат)     | Best Russian language understanding |
| bge-reranker        | Cloud.ru  | Embeddings (RAG search)         | Высокое качество reranking для RAG  |
| GPT-4o / Claude 3.5 | Fallback  | Backup при недоступности Cloud.ru | Proven quality, higher latency     |

---

## 5. Data Architecture

### PostgreSQL Schema Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        PostgreSQL 16                            │
│                                                                 │
│  ┌─── Odoo Core ──────────┐  ┌─── СтройУправ Domain ────────┐ │
│  │                         │  │                               │ │
│  │  res_partner            │  │  su_project (Объекты)         │ │
│  │  res_users              │  │  ├── su_project_stage         │ │
│  │  res_company            │  │  ├── su_budget_line           │ │
│  │  ir_attachment          │  │  └── su_project_member        │ │
│  │  ir_config_parameter    │  │                               │ │
│  │                         │  │  su_task (Задачи)             │ │
│  └─────────────────────────┘  │  ├── su_task_dependency       │ │
│                                │  └── su_task_log              │ │
│  ┌─── Billing ────────────┐  │                               │ │
│  │                         │  │  su_estimate (Сметы)          │ │
│  │  su_subscription        │  │  ├── su_estimate_line         │ │
│  │  su_subscription_plan   │  │  ├── su_estimate_version      │ │
│  │  su_payment             │  │  └── su_estimate_ai_log       │ │
│  │  su_invoice             │  │                               │ │
│  └─────────────────────────┘  │  su_photo (Фотофиксация)     │ │
│                                │  ├── geotag (JSONB)           │ │
│  ┌─── ГЭСН/ФЕР Нормативы ┐  │  └── s3_key                  │ │
│  │                         │  │                               │ │
│  │  su_gesn_section        │  │  su_portal_access             │ │
│  │  su_gesn_item           │  │  su_notification              │ │
│  │  su_fer_rate            │  │  su_onboarding_profile        │ │
│  │  su_price_index         │  │                               │ │
│  │  (квартальный update)   │  └───────────────────────────────┘ │
│  └─────────────────────────┘                                    │
└─────────────────────────────────────────────────────────────────┘
```

### Key Tables

| Table               | Description                              | Key Fields                                              |
|---------------------|------------------------------------------|---------------------------------------------------------|
| `su_project`        | Строительный объект                      | name, address, status, budget_plan, budget_fact, progress_pct, start_date, end_date |
| `su_task`           | Задача на объекте                        | project_id, assignee_ids, status, priority, parent_id, deadline |
| `su_estimate`       | Смета (AI-generated or manual)           | project_id, total_amount, currency, ai_model, confidence_score, version |
| `su_estimate_line`  | Позиция сметы                            | estimate_id, gesn_code, description, unit, quantity, unit_price, total |
| `su_photo`          | Фотофиксация                            | task_id, s3_key, geotag (JSONB: lat, lng, accuracy), taken_at |
| `su_gesn_item`      | Расценка ГЭСН/ФЕР                       | code, section_id, description, unit, base_price, region_coefficients |
| `su_price_index`    | Индексы Минстроя                         | region, period_quarter, category, index_value             |
| `su_subscription`   | Подписка клиента                         | partner_id, plan_id, status, start_date, end_date, yukassa_subscription_id |
| `su_payment`        | Платёж через ЮKassa                      | subscription_id, amount, status, yukassa_payment_id, paid_at |

### Data Partitioning Strategy

- `su_photo`: partitioned by `created_at` (monthly) -- highest volume table
- `su_estimate_ai_log`: partitioned by `created_at` (monthly) -- AI audit trail
- `su_gesn_item`: no partitioning, ~200K rows, fully cached in Elasticsearch
- Индексы: composite indexes on `(project_id, status)`, `(task_id, created_at)`

---

## 6. AI Architecture

### AI Provider (OpenAI-compatible client)

Оба провайдера (Cloud.ru и OpenAI) предоставляют OpenAI-совместимый API.
Переключение — через env vars `AI_BASE_URL` + `AI_API_KEY`. Никакого proxy.

```
┌────────────────────────────────────────────────────────────────┐
│                     FastAPI AI Service                         │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │ /api/v1/     │  │ /api/v1/     │  │ /api/v1/             │ │
│  │ estimate     │  │ drawing/     │  │ analytics            │ │
│  │              │  │ parse        │  │                      │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────────────┘ │
│         │                 │                  │                 │
│         ▼                 ▼                  ▼                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              AIClient (OpenAI SDK wrapper)              │   │
│  │                                                        │   │
│  │  client = OpenAI(                                      │   │
│  │    base_url=env("AI_BASE_URL"),  # Cloud.ru or OpenAI  │   │
│  │    api_key=env("AI_API_KEY"),                          │   │
│  │  )                                                     │   │
│  │                                                        │   │
│  │  Features:                                             │   │
│  │  - Switch provider via env var (zero code change)      │   │
│  │  - Auto-retry with exponential backoff                 │   │
│  │  - Cost tracking per request (logged to DB)            │   │
│  │  - Model aliasing via config dict                      │   │
│  │  - Response caching (Redis, TTL 1h for estimates)      │   │
│  └────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
         ┌───────────┐ ┌──────────┐ ┌────────────┐
         │ Cloud.ru  │ │ OpenAI   │ │ Anthropic  │
         │ FM API    │ │ API      │ │ API        │
         │           │ │          │ │            │
         │ Qwen3-480B│ │ GPT-4o   │ │ Claude 3.5 │
         │ DeepSeek  │ │          │ │            │
         │ T-pro-it  │ │          │ │            │
         │ bge-rerank│ │          │ │            │
         └───────────┘ └──────────┘ └────────────┘
```

### RAG Pipeline for ГЭСН/ФЕР

```
┌──────────────────── Ingestion Pipeline (Celery) ────────────────┐
│                                                                  │
│  ГЭСН/ФЕР XML/CSV ──▶ Parser ──▶ Chunker ──▶ bge-reranker     │
│  (Минстрой source)      │           │          (embeddings)      │
│                          ▼           ▼              │             │
│                   su_gesn_item   Elasticsearch      │             │
│                   (PostgreSQL)   (full-text)         │             │
│                                                      ▼             │
│                                              Cloud.ru Managed RAG │
│                                              (vector store)       │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────── Query Pipeline (real-time) ─────────────────┐
│                                                                  │
│  User prompt ──▶ Intent classifier ──▶ Query builder             │
│  "Штукатурка         (T-pro-it)         │                        │
│   стен 50 м²"                           ▼                        │
│                                   ┌─────────────┐               │
│                                   │ Hybrid Search│               │
│                                   │              │               │
│                                   │ 1. ES full-  │               │
│                                   │    text match│               │
│                                   │ 2. RAG vector│               │
│                                   │    similarity│               │
│                                   │ 3. Reranker  │               │
│                                   └──────┬──────┘               │
│                                          ▼                       │
│                                   Top-K ГЭСН items              │
│                                          │                       │
│                                          ▼                       │
│                              ┌────────────────────┐             │
│                              │ Qwen3-Coder-480B   │             │
│                              │                    │             │
│                              │ Prompt:            │             │
│                              │ - User description │             │
│                              │ - ГЭСН matches    │             │
│                              │ - Price indices    │             │
│                              │ - Region coeff.    │             │
│                              │                    │             │
│                              │ Output:            │             │
│                              │ - Structured JSON  │             │
│                              │ - estimate_lines[] │             │
│                              │ - confidence_score │             │
│                              └────────┬───────────┘             │
│                                       ▼                          │
│                              su_estimate + su_estimate_line      │
│                              (saved to PostgreSQL)               │
└──────────────────────────────────────────────────────────────────┘
```

### Cloud.ru ML Finetuning Pipeline

```
Historical estimates (su_estimate + su_estimate_line)
         │
         ▼
  Data preparation (Celery periodic task)
  - Filter: confidence_score >= 0.85 AND user_approved = true
  - Format: instruction/input/output pairs
         │
         ▼
  Cloud.ru ML Finetuning API
  - Base model: Qwen3-Coder-480B
  - Training: supervised fine-tuning
  - Evaluation: held-out test set (20%)
         │
         ▼
  Finetuned model deployed to Cloud.ru FM
  - A/B test: 10% traffic → finetuned model
  - Compare: confidence_score, user acceptance rate
  - Promote if metrics improve
```

---

## 7. Security Architecture

### Authentication Flow

```
┌─────────┐     ┌───────────┐     ┌──────────────┐     ┌──────────┐
│  Client  │────▶│  Nginx    │────▶│  Odoo Auth   │────▶│PostgreSQL│
│  (PWA/   │     │  (TLS 1.3)│     │  Controller  │     │          │
│   React) │◀────│           │◀────│              │◀────│          │
└─────────┘     └───────────┘     └──────────────┘     └──────────┘
     │                                    │
     │  1. POST /auth/login               │
     │     {email, password}              │
     │                                    │
     │  2. Validate credentials           │
     │     bcrypt hash comparison         │
     │                                    │
     │  3. Response:                      │
     │     Set-Cookie: access_token       │
     │     (httpOnly, Secure, SameSite)   │
     │     Set-Cookie: refresh_token      │
     │     (httpOnly, Secure, SameSite,   │
     │      Path=/auth/refresh)           │
     │                                    │
     │  4. Subsequent requests:           │
     │     Cookie sent automatically      │
     │     Odoo middleware validates JWT   │
     ▼                                    ▼
```

### Token Architecture

| Token          | Lifetime | Storage          | Purpose                    |
|----------------|----------|------------------|----------------------------|
| Access Token   | 15 min   | httpOnly cookie  | API authorization           |
| Refresh Token  | 7 days   | httpOnly cookie  | Access token renewal        |
| CSRF Token     | per session | meta tag      | CSRF protection             |

**CRITICAL:** No tokens in localStorage. Proven XSS vector.

### Data Encryption

| Layer         | Method                     | Details                         |
|---------------|----------------------------|---------------------------------|
| In Transit    | TLS 1.3                    | Nginx terminates SSL            |
| At Rest (DB)  | AES-256 (PostgreSQL TDE)   | Персональные данные, платежи    |
| At Rest (S3)  | AES-256 (MinIO encryption) | Фото, чертежи                   |
| Secrets       | Docker Secrets + .env      | API keys, DB passwords          |
| Backups       | GPG encrypted              | Offsite backup encryption        |

### 152-ФЗ Compliance

| Requirement                      | Implementation                                   |
|----------------------------------|--------------------------------------------------|
| Данные граждан РФ — хранение в РФ | VPS: AdminVPS/HOSTKEY (ЦОД в РФ)                |
| AI-обработка — данные в РФ       | Cloud.ru Foundation Models (ЦОД в РФ)            |
| Согласие на обработку ПД         | Checkbox при регистрации + политика конфиденциальности |
| Право на удаление                | API endpoint DELETE /api/v1/me + Celery job для cascade delete |
| Журналирование доступа           | Odoo audit log + su_audit_log table               |
| Уведомление Роскомнадзора        | Уведомление подаётся при запуске (оператор ПД)    |
| Минимизация данных               | Collect only what's needed, TTL on logs (90 days) |

### API Security

- Rate limiting: Nginx (100 req/min global), per-tenant (Redis token bucket)
- Input validation: Pydantic models (FastAPI), Odoo ORM constraints
- SQL injection: Odoo ORM (parameterized queries), no raw SQL
- CORS: whitelist frontend domains only
- Webhook HMAC: ЮKassa webhooks verified via SHA-256 HMAC signature
- File upload: type validation, size limits (20MB photo, 50MB drawing), ClamAV scan

---

## 8. Deployment Architecture

### Docker Compose Services

```yaml
# Production Docker Compose topology
#
# ┌──────────────────────────────────────────────────────────┐
# │                    Docker Network: stroyuprav            │
# │                                                          │
# │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───────────┐ │
# │  │  nginx   │  │  odoo   │  │ fastapi │  │  celery   │ │
# │  │  :443    │──│  :8069  │  │  :8000  │  │  worker   │ │
# │  │  :80     │  │         │──│         │  │           │ │
# │  └─────────┘  └────┬────┘  └────┬────┘  └─────┬─────┘ │
# │                    │           │              │         │
# │  ┌─────────┐  ┌────▼────┐  ┌───▼──────┐  ┌───▼─────┐  │
# │  │ celery  │  │postgres │  │  redis   │  │ minio   │  │
# │  │ beat    │  │  :5432  │  │  :6379   │  │  :9000  │  │
# │  └─────────┘  └─────────┘  └──────────┘  └─────────┘  │
# │                                                          │
# │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐ │
# │  │elasticsearch│  │  prometheus  │  │    grafana     │ │
# │  │   :9200     │  │    :9090     │  │    :3000       │ │
# │  └─────────────┘  └──────────────┘  └────────────────┘ │
# │                                                          │
# │  ┌─────────┐                                            │
# │  │  loki   │                                            │
# │  │  :3100  │                                            │
# │  └─────────┘                                            │
# └──────────────────────────────────────────────────────────┘
```

### Service Specifications

| Service        | Image                | CPU  | RAM   | Volumes                        |
|----------------|----------------------|------|-------|---------------------------------|
| nginx          | nginx:1.27-alpine    | 0.5  | 256M  | certs, nginx.conf               |
| odoo           | custom (Odoo 17)     | 2    | 2G    | odoo-data, addons               |
| fastapi        | custom (Python 3.12) | 2    | 2G    | -                               |
| celery-worker  | same as fastapi      | 1    | 1G    | -                               |
| celery-beat    | same as fastapi      | 0.25 | 256M  | -                               |
| postgres       | postgres:16-alpine   | 2    | 4G    | pgdata (persistent)             |
| redis          | redis:7-alpine       | 0.5  | 512M  | redis-data                      |
| minio          | minio/minio          | 0.5  | 512M  | minio-data (persistent)         |
| elasticsearch  | elasticsearch:8.x    | 1    | 2G    | es-data (persistent)            |
| prometheus     | prom/prometheus       | 0.25 | 256M  | prom-data                       |
| grafana        | grafana/grafana       | 0.25 | 256M  | grafana-data                    |
| loki           | grafana/loki          | 0.25 | 256M  | loki-data                       |

**Total minimum VPS:** 8 vCPU, 16 GB RAM, 200 GB SSD (AdminVPS ~ ₽5K/мес)

### Networking

- External: only Nginx exposed (ports 80, 443)
- Internal: Docker bridge network `stroyuprav`
- Service discovery: Docker DNS (service names as hostnames)
- No port exposure for internal services (postgres, redis, etc.)
- Firewall: UFW — allow 80, 443, 22 (SSH) only

### CI/CD Pipeline

```
GitHub Push ──▶ GitHub Actions
                    │
                    ├── Lint (ruff, mypy)
                    ├── Unit Tests (pytest)
                    ├── Integration Tests (docker-compose test profile)
                    │
                    ▼
              Docker Build
                    │
                    ├── Build odoo image
                    ├── Build fastapi image
                    │
                    ▼
              Push to Registry
              (GitHub Container Registry)
                    │
                    ▼
              Deploy to VPS
              (SSH + docker compose pull + up -d)
                    │
                    ├── Health check
                    ├── Rollback on failure
                    └── Notify (Telegram)
```

---

## 9. Scalability Strategy

### Phase 1: Single VPS (0 - 1,000 users)

```
Single VPS (8 vCPU, 16 GB RAM)
- All services on one machine
- PostgreSQL single instance
- Vertical scaling: upgrade VPS
```

### Phase 2: Horizontal Split (1,000 - 5,000 users)

```
VPS 1 (App Server)          VPS 2 (Data Server)
┌──────────────────┐        ┌──────────────────┐
│  nginx           │        │  postgres        │
│  odoo (x2)       │───────▶│  (primary)       │
│  fastapi (x2)    │        │                  │
│  celery (x4)     │        │  postgres        │
│  redis           │        │  (read replica)  │
└──────────────────┘        │                  │
                            │  elasticsearch   │
                            │  minio           │
                            └──────────────────┘
```

- Odoo behind Nginx upstream (round-robin)
- FastAPI replicas with shared Redis for sessions
- PostgreSQL read replica for dashboard queries
- Celery worker scaling based on AI queue depth

### Phase 3: Kubernetes Migration (5,000+ users)

```
Kubernetes Cluster (Managed K8s)
┌──────────────────────────────────────────┐
│  Ingress Controller (Nginx)              │
│                                          │
│  ┌─────────┐ ┌─────────┐ ┌───────────┐ │
│  │ odoo    │ │ fastapi │ │ celery    │ │
│  │ HPA 2-8│ │ HPA 2-6│ │ HPA 2-16 │ │
│  └─────────┘ └─────────┘ └───────────┘ │
│                                          │
│  Managed PostgreSQL (Cloud.ru / Yandex)  │
│  Managed Redis                           │
│  Managed S3 (instead of MinIO)           │
└──────────────────────────────────────────┘
```

### Scaling Triggers

| Metric                          | Threshold      | Action                              |
|---------------------------------|----------------|-------------------------------------|
| API response time P95           | > 500ms        | Add app server replica              |
| Celery queue depth              | > 100 tasks    | Scale celery workers                |
| PostgreSQL connections          | > 80% max      | Add read replica or PgBouncer       |
| CPU utilization (sustained)     | > 70%          | Vertical scale or add node          |
| Disk usage                      | > 80%          | Expand volume / archive old photos  |
| AI request queue wait time      | > 30s          | Scale FastAPI workers + Celery concurrency |

---

## 10. Monitoring & Observability

### Stack

```
┌──────────────────────────────────────────────────────────┐
│                      Grafana                             │
│                   (dashboards + alerts)                   │
│                                                          │
│  ┌─────────────┐  ┌──────────┐  ┌────────────────────┐ │
│  │ Prometheus  │  │  Loki    │  │  Custom Metrics    │ │
│  │ (metrics)   │  │  (logs)  │  │  (business KPIs)   │ │
│  └──────┬──────┘  └────┬─────┘  └─────────┬──────────┘ │
│         │              │                   │            │
│  ┌──────▼──────┐  ┌────▼─────┐  ┌─────────▼──────────┐ │
│  │ Exporters:  │  │ Promtail │  │ Odoo custom module │ │
│  │ - node      │  │ (agent)  │  │ stroyuprav_metrics │ │
│  │ - postgres  │  │          │  │                    │ │
│  │ - redis     │  │          │  │ - DAU/MAU          │ │
│  │ - nginx     │  │          │  │ - AI-смет/день     │ │
│  │ - celery    │  │          │  │ - MRR              │ │
│  └─────────────┘  └──────────┘  │ - Conversion rate  │ │
│                                  └────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### Key Dashboards

| Dashboard             | Metrics                                                      |
|-----------------------|--------------------------------------------------------------|
| **System Health**     | CPU, RAM, disk, network per container                        |
| **API Performance**   | Request rate, latency P50/P95/P99, error rate (5xx, 4xx)     |
| **Database**          | Connections, query time, replication lag, table sizes         |
| **AI Pipeline**       | Request count, latency, token usage, cost, model distribution |
| **Business KPIs**     | DAU/MAU, AI-смет/день, MRR, trial-to-paid conversion         |
| **Celery Queues**     | Queue depth, processing time, failure rate per task type      |
| **Security**          | Failed auth attempts, rate limit hits, suspicious patterns    |

### Alerting Rules

| Alert                              | Condition               | Channel        |
|------------------------------------|-------------------------|----------------|
| Service down                       | Health check fails x3   | Telegram + PagerDuty |
| API error rate > 5%                | 5min window             | Telegram       |
| AI response time > 120s            | P95 over 5min           | Telegram       |
| Database connections > 80%         | Sustained 10min         | Telegram       |
| Disk usage > 85%                   | Any volume              | Telegram       |
| Payment webhook failures           | Any failure             | Telegram (urgent) |
| SSL certificate expiry             | < 14 days               | Email          |

### Structured Logging

All services log in JSON format for Loki ingestion:

```json
{
  "timestamp": "2026-05-27T10:00:00Z",
  "level": "INFO",
  "service": "fastapi-ai",
  "trace_id": "abc123",
  "user_id": 42,
  "action": "estimate_generated",
  "model": "qwen3-coder-480b",
  "tokens_used": 4200,
  "latency_ms": 8500,
  "confidence": 0.87
}
```

### Health Checks

| Service       | Endpoint            | Interval | Timeout |
|---------------|---------------------|----------|---------|
| Odoo          | /web/health         | 30s      | 5s      |
| FastAPI       | /health             | 15s      | 5s      |
| PostgreSQL    | pg_isready          | 15s      | 3s      |
| Redis         | redis-cli ping      | 15s      | 3s      |
| MinIO         | /minio/health/live  | 30s      | 5s      |
| Elasticsearch | /_cluster/health    | 30s      | 5s      |
