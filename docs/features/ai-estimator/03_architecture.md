# Architecture: AI-Estimator (F01)

---

## 1. System Overview

```
┌──────────────────────────────────────────────────────────┐
│                      Client (PWA)                        │
│  React + React Query + Zustand                           │
└────────────────────┬─────────────────────────────────────┘
                     │ HTTPS (TLS 1.3)
                     ▼
┌──────────────────────────────────────────────────────────┐
│                   Nginx Reverse Proxy                    │
│  Rate limiting, CORS, security headers                   │
└────────┬───────────────────────────────┬─────────────────┘
         │                               │
         ▼                               ▼
┌─────────────────────┐     ┌────────────────────────────┐
│   Odoo Backend       │     │   AI Service (FastAPI)     │
│   su_estimate model  │     │   /api/v1/estimate/*       │
│   su_project model   │     │   Async, Pydantic, Celery  │
│   RBAC, billing      │     │                            │
└─────────┬───────────┘     └─────┬──────────┬───────────┘
          │                       │          │
          ▼                       ▼          ▼
┌─────────────────┐   ┌──────────────┐  ┌──────────────┐
│   PostgreSQL     │   │ Elasticsearch│  │  Redis       │
│   su_estimate    │   │ gesn_fer idx │  │  Cache +     │
│   su_minstroy_*  │   │ KNN vectors  │  │  Celery      │
│   DECIMAL(15,2)  │   │ 100K+ docs   │  │  broker      │
└─────────────────┘   └──────────────┘  └──────────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │  Cloud.ru AI     │
                     │  (OpenAI SDK)    │
                     │  qwen3-coder     │
                     │  qwen3-vl        │
                     │  bge-m3 embed    │
                     └──────────────────┘
```

---

## 2. Component Breakdown

### 2.1 AI Service (FastAPI)

**Purpose:** Handles all AI-related processing independently from Odoo.

**Structure:**
```
ai_service/
├── main.py              # FastAPI app, middleware, health check
├── config.py            # Settings from env vars (crash if missing)
├── routers/
│   ├── estimate.py      # POST /generate, GET /status, POST /export
│   ├── optimize.py      # POST /optimize
│   └── usage.py         # GET /usage
├── services/
│   ├── ai_client.py     # OpenAI SDK wrapper (Cloud.ru base_url)
│   ├── gesn_search.py   # Elasticsearch queries (KNN + fulltext)
│   ├── estimator.py     # Core pipeline orchestration
│   ├── drawing_parser.py # Vision AI for drawings
│   ├── optimizer.py     # Market benchmark comparison
│   ├── exporter.py      # PDF/Excel generation
│   └── usage_tracker.py # Quota management
├── models/
│   ├── schemas.py       # Pydantic request/response models
│   └── domain.py        # WorkItem, EstimateLine, Suggestion
├── tasks/
│   └── celery_tasks.py  # Async task definitions
└── tests/
    ├── test_estimator.py
    ├── test_gesn_search.py
    └── test_optimizer.py
```

**Key decisions:**
- OpenAI SDK directly (no LiteLLM) -- `OpenAI(base_url=env("AI_BASE_URL"))`
- Provider switch via env var `AI_BASE_URL` + `AI_API_KEY`
- All async handlers (`async def`)
- Pydantic v2 for validation, Decimal for money fields
- Celery for tasks >30s (estimate generation, export)

### 2.2 Odoo Module: `su_estimate`

**Purpose:** Data persistence, RBAC, billing integration, UI.

```
su_estimate/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── su_estimate.py       # Estimate header (Monetary fields)
│   ├── su_estimate_line.py  # Estimate lines
│   └── su_usage_counter.py  # Monthly usage tracking
├── views/
│   ├── su_estimate_views.xml
│   └── su_estimate_line_views.xml
├── security/
│   └── ir.model.access.csv
├── data/
│   └── gesn_categories.csv  # Work categories for index lookup
├── controllers/
│   └── estimate_api.py      # Odoo JSON-RPC bridge to FastAPI
└── tests/
    └── test_su_estimate.py
```

**Model fields (Decimal only for money):**
- `subtotal`: `fields.Monetary(currency_field='currency_id')`
- `nds_amount`: `fields.Monetary(currency_field='currency_id')`
- `grand_total`: `fields.Monetary(currency_field='currency_id')`
- `quantity`: `fields.Float(digits=(16,4))` (non-money, Float acceptable)

### 2.3 Elasticsearch

**Index:** `gesn_fer`
- ~100K+ documents (all 47 ГЭСН collections + ФЕР + regional ТЕР)
- KNN field: `description_vector` (768-dim, bge-m3 embeddings)
- Text fields: `description`, `keywords` with Russian analyzer
- Mapping uses `dense_vector` type with HNSW index

**Index settings:**
```json
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "analysis": {
      "analyzer": {
        "russian_custom": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": ["lowercase", "russian_stemmer"]
        }
      }
    }
  }
}
```

### 2.4 Redis

- **Celery broker** for async task queue
- **Cache** for:
  - Минстрой indices (TTL 24h, refreshed on quarter update)
  - Market benchmarks (TTL 1h)
  - Usage counters (TTL until month end)
- **Session store** (not used for tokens -- tokens in httpOnly cookies)

### 2.5 Cloud.ru AI Integration

**Models used:**
| Model | Purpose | Timeout |
|-------|---------|---------|
| qwen3-coder-480b | Text parsing, work classification | 30s |
| qwen3-vl | Drawing/image recognition | 60s |
| bge-m3 | Embeddings for ГЭСН semantic search | 5s |

**Client configuration:**
```python
# ai_client.py — NO LiteLLM, direct OpenAI SDK
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url=os.environ["AI_BASE_URL"],    # mandatory, crash if missing
    api_key=os.environ["AI_API_KEY"],      # mandatory, crash if missing
)
```

**Failover:** If Cloud.ru returns 5xx or timeout, retry 2x with exponential backoff. No automatic switch to other providers (152-ФЗ compliance -- data must stay in Russia).

---

## 3. Data Flow

### 3.1 Text Estimate Generation

```
User clicks "Create estimate"
  → PWA sends POST /api/v1/estimate/generate (text, region)
  → FastAPI validates input (Pydantic)
  → Check usage quota (Redis counter + DB)
  → Create Celery task, return 202 + task_id
  → Celery worker:
      1. Send description to Cloud.ru LLM → get structured WorkItems
      2. For each WorkItem:
         a. Generate embedding via bge-m3
         b. KNN search Elasticsearch gesn_fer index
         c. Fallback: fulltext search if KNN score < 0.7
         d. Fetch Минстрой index from PostgreSQL (cached in Redis)
         e. Calculate: base_rate × quantity × index + overhead + profit (Decimal)
      3. Sum all lines → subtotal, NDS 20%, grand_total
      4. Save to PostgreSQL (su_estimate + su_estimate_line)
      5. Increment usage counter
      6. Trigger async optimization task
  → PWA polls GET /api/v1/estimate/status/{task_id}
  → Returns completed estimate with lines
```

### 3.2 Drawing Estimate Generation

```
Same as 3.1 except step 1:
  1. Download file from S3
  2. Validate MIME + magic bytes
  3. PDF → convert pages to images (300 DPI, max 10 pages)
  4. Send each image to Cloud.ru vision model (qwen3-vl)
  5. Parse rooms, areas, work types from response
  → Continue from step 2 of text flow
```

### 3.3 Export Flow

```
User clicks "Export PDF"
  → POST /api/v1/estimate/{id}/export
  → Celery task:
      1. Fetch estimate + lines from DB
      2. Generate PDF (reportlab) or XLSX (openpyxl)
      3. Upload to S3 (private ACL)
      4. Generate pre-signed URL (TTL 1h)
  → Return download URL
```

---

## 4. Infrastructure (Docker Compose)

```yaml
services:
  odoo:
    image: odoo:17.0
    depends_on: [postgres, redis]

  ai-service:
    build: ./ai_service
    environment:
      - AI_BASE_URL            # Cloud.ru endpoint (required)
      - AI_API_KEY             # Cloud.ru key (required)
      - AI_MODEL               # default: qwen3-coder-480b
      - AI_VISION_MODEL        # default: qwen3-vl
      - EMBEDDING_MODEL        # default: bge-m3
      - ELASTICSEARCH_URL      # required
      - DATABASE_URL           # required
      - REDIS_URL              # required
      - S3_ENDPOINT            # required
      - S3_ACCESS_KEY          # required
      - S3_SECRET_KEY          # required
    depends_on: [postgres, redis, elasticsearch]

  celery-worker:
    build: ./ai_service
    command: celery -A tasks worker -l info -c 4
    depends_on: [redis, postgres, elasticsearch]

  postgres:
    image: postgres:16-alpine
    volumes: [pgdata:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine

  elasticsearch:
    image: elasticsearch:8.14.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes: [esdata:/usr/share/elasticsearch/data]

  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
```

---

## 5. Scaling Considerations

| Component | Y1 (1K users) | Y2 (10K users) |
|-----------|---------------|-----------------|
| AI Service | 2 replicas | 4 replicas + autoscale |
| Celery workers | 2 workers, 4 concurrency | 8 workers |
| Elasticsearch | 1 node, 1 shard | 3 nodes, 3 shards |
| PostgreSQL | Single primary | Primary + read replica |
| Redis | Single instance | Sentinel (3 nodes) |

Estimate table partitioned by `created_at` (monthly) after 1M rows.
