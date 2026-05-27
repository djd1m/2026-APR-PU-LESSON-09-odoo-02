# Quick Start

Get StroyUprav running locally in 5 commands.

---

## Prerequisites

| Tool | Minimum Version |
|------|----------------|
| Docker | 24.0+ |
| Docker Compose | 2.20+ |
| Git | 2.40+ |

Hardware: 8 GB RAM minimum (Elasticsearch alone needs 2 GB), 4 CPU cores recommended.

---

## 5-Step Launch

### 1. Clone the repository

```bash
git clone https://github.com/your-org/stroyuprav.git
cd stroyuprav
```

### 2. Create the environment file

```bash
cp .env.example .env
```

Edit `.env` and fill in the required values:

| Variable | What to set |
|----------|-------------|
| `DB_PASSWORD` | Strong password for PostgreSQL |
| `SECRET_KEY` | Random 64-character string (`openssl rand -hex 32`) |
| `CLOUDRU_API_KEY` | Your Cloud.ru Foundation Models API key |
| `S3_SECRET_KEY` | MinIO secret (change from default) |
| `MINIO_ROOT_PASSWORD` | Same as `S3_SECRET_KEY` |
| `YUKASSA_SHOP_ID` | YuKassa merchant ID (get from yukassa.ru dashboard) |
| `YUKASSA_SECRET_KEY` | YuKassa API secret key |
| `YUKASSA_WEBHOOK_SECRET` | YuKassa webhook HMAC secret |

> **Important:** The application will crash on startup if any required variable is missing. There are no fallback defaults for secrets.

### 3. Build and start all services

```bash
docker compose up -d --build
```

This starts 9 services: nginx, odoo, fastapi-ai, postgres, redis, celery-worker, celery-beat, minio, elasticsearch.

### 4. Wait for health checks

```bash
docker compose ps
```

All services should show `healthy` or `running`. PostgreSQL and Elasticsearch have health checks -- they may take 30-60 seconds.

### 5. Open the application

```
http://localhost           -- Odoo ERP (main application)
http://localhost/api       -- FastAPI AI service (Swagger docs at /api/docs)
http://localhost:9001      -- MinIO console (object storage admin)
```

---

## Verify the Installation

```bash
# Check all 9 services are up
docker compose ps

# Check Odoo logs
docker compose logs odoo --tail 50

# Check AI service health
curl http://localhost/api/health

# Check Elasticsearch has GESN/FER index
curl http://localhost:9200/_cat/indices
```

---

## Stop / Restart

```bash
# Stop all services (data persisted in volumes)
docker compose down

# Stop and remove all data (destructive!)
docker compose down -v

# Restart a single service
docker compose restart odoo
```

---

## Next Steps

- [User Guide](02_user_guide.md) -- learn end-user workflows
- [Admin Guide](03_admin_guide.md) -- deploy to production VPS
- [Architecture](05_architecture.md) -- understand the system design
