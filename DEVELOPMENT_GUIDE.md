# Development Guide: СтройУправ

Step-by-step guide for developing, testing, and deploying the СтройУправ platform.

## 1. Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker | 24+ | Container runtime |
| Docker Compose | v2+ | Service orchestration |
| Python | 3.12 | Odoo backend, FastAPI AI service |
| Node.js | 20 LTS | OWL frontend tooling, rtlcss |
| Git | 2.40+ | Version control |

Optional:
- **PostgreSQL client** (`psql`) for direct DB access during debugging
- **Redis CLI** (`redis-cli`) for cache inspection

## 2. Getting Started

```bash
# Clone the repository
git clone git@github.com:<org>/2026-APR-PU-LESSON-09-odoo-02.git
cd 2026-APR-PU-LESSON-09-odoo-02

# Create environment file from template
cp .env.example .env
# Edit .env — fill in DB_PASSWORD, SECRET_KEY, API keys

# Start all services
docker compose up -d

# Verify services are running
docker compose ps

# Access Odoo
open http://localhost:8069
```

First-time Odoo setup: the database manager will appear at `/web/database/manager`. Create a database named `stroiuprav` and install base modules.

## 3. Project Structure

```
2026-APR-PU-LESSON-09-odoo-02/
|-- custom-addons/                 # Odoo custom modules
|   |-- stroyuprav_estimate/       # AI-сметчик module
|   |-- stroyuprav_project/        # Объекты/Dashboard module
|   |-- stroyuprav_task/           # Задачи module
|   |-- stroyuprav_photo/          # Фотофиксация module
|   |-- stroyuprav_billing/        # ЮKassa billing module
|   |-- stroyuprav_onboarding/     # Onboarding quiz module
|   |-- stroyuprav_portal/         # Заказчик portal module
|-- services/
|   |-- fastapi-ai/                # FastAPI AI service
|   |   |-- estimate_engine/       # LLM calls, RAG queries
|   |   |-- drawing_parser/        # OCR/CV for blueprints
|   |   |-- analytics_engine/      # Forecasts, alerts
|-- nginx/
|   |-- conf.d/                    # Nginx virtual host configs
|   |-- ssl/                       # TLS certificates (gitignored)
|-- docs/                          # SPARC documentation
|   |-- PRD.md                     # Product Requirements
|   |-- Architecture.md            # System architecture
|   |-- Specification.md           # Technical specification
|   |-- features/                  # Per-feature docs
|-- .claude/                       # Claude Code toolkit
|-- docker-compose.yml             # Service orchestration
|-- Dockerfile                     # Odoo + custom addons image
|-- odoo.conf                      # Odoo server configuration
|-- requirements.txt               # Python dependencies
```

## 4. Development Workflow

### Branch strategy

- `main` -- production-ready, protected
- `feature/<id>-<slug>` -- per-feature development
- `hotfix/<slug>` -- emergency fixes

### Feature development

1. Create a feature branch: `git checkout -b feature/f01-ai-estimate`
2. Use `/feature` command for structured development (PLAN -> VALIDATE -> IMPLEMENT -> REVIEW)
3. Commit after each logical change using conventional commits
4. Push and create a pull request

### Odoo module development

Custom modules live in `custom-addons/`. Each module follows Odoo conventions:

```
stroyuprav_<name>/
|-- __init__.py
|-- __manifest__.py
|-- models/
|-- views/
|-- security/
|-- data/
|-- static/
|-- tests/
```

Restart Odoo after model changes:
```bash
docker compose restart odoo
```

Update module in Odoo:
```bash
docker compose exec odoo odoo -u stroyuprav_<name> --stop-after-init
```

### FastAPI AI service development

The AI service runs independently in `services/fastapi-ai/`:

```bash
cd services/fastapi-ai
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## 5. Testing

### Odoo module tests

```bash
# Run tests for a specific module
docker compose exec odoo odoo --test-enable -u stroyuprav_estimate --stop-after-init

# Run all custom module tests
docker compose exec odoo odoo --test-enable -u all --stop-after-init
```

### FastAPI AI service tests

```bash
cd services/fastapi-ai
pytest tests/ -v --cov=.
```

### End-to-end tests (Playwright)

```bash
npx playwright install
npx playwright test
```

### Test categories

| Type | Tool | Scope |
|------|------|-------|
| Unit | pytest | Individual functions, model methods |
| Integration | pytest + testcontainers | Cross-module, DB interactions |
| API | pytest + httpx | FastAPI endpoints |
| E2E | Playwright | Full user flows through browser |

## 6. AI Development

### Cloud.ru Foundation Models setup

1. Register at [Cloud.ru](https://cloud.ru) and obtain API credentials
2. Set environment variables in `.env`:

```bash
CLOUDRU_API_KEY=your-api-key
CLOUDRU_API_BASE=https://api.cloud.ru/v1
CLOUDRU_MODEL=qwen3-72b
```

3. The FastAPI AI service uses an OpenAI-compatible client, so the same codebase works with any provider:

```bash
# Switch to OpenAI fallback
OPENAI_API_KEY=sk-...
```

### AI models used

| Model | Provider | Use Case |
|-------|----------|----------|
| Qwen3-Coder-480B | Cloud.ru | AI-estimate generation |
| DeepSeek-V3 | Cloud.ru | Analytics, reports |
| T-pro-it-2.0 | Cloud.ru | Russian NLP |
| GPT-4o / Claude 3.5 | Fallback | Backup when Cloud.ru is unavailable |

### GESN/FER normative base

The Elasticsearch service indexes 200K+ construction price entries (GESN/FER). To populate:

```bash
# Import normative base
docker compose exec fastapi-ai python scripts/import_gesn_fer.py
```

## 7. Deployment

### VPS deployment (AdminVPS / HOSTKEY)

```bash
# SSH into production server
ssh deploy@app.stroiuprav.ru

# Pull latest changes
cd /home/deploy/stroiuprav
git pull origin main

# Rebuild and restart
docker compose build
docker compose up -d

# Run database migrations
docker compose exec odoo odoo -u all --stop-after-init

# Verify
docker compose ps
curl -sf https://app.stroiuprav.ru/web/login
```

### SSL certificates (Let's Encrypt)

Certificates are managed by the certbot container with automatic renewal every 12 hours.

Initial certificate setup:
```bash
docker compose run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d app.stroiuprav.ru -d staging.stroiuprav.ru
```

### Database backups

```bash
# Manual backup
docker compose exec postgres pg_dump -U stroiuprav stroiuprav | gzip > backups/$(date +%Y%m%d_%H%M%S).sql.gz

# Restore from backup
gunzip -c backups/<file>.sql.gz | docker compose exec -T postgres psql -U stroiuprav stroiuprav
```

## 8. Troubleshooting

### Odoo won't start

```bash
# Check logs
docker compose logs odoo --tail=50

# Common issues:
# - Database not ready: wait for postgres healthcheck to pass
# - Missing Python deps: rebuild with `docker compose build odoo`
# - Port conflict: check `docker compose ps` for port bindings
```

### Elasticsearch out of memory

Increase JVM heap in `docker-compose.yml`:
```yaml
environment:
  - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
```

Ensure the host has enough virtual memory:
```bash
sudo sysctl -w vm.max_map_count=262144
```

### Redis connection refused

```bash
docker compose logs redis --tail=20
# Verify Redis is running
docker compose exec redis redis-cli ping
```

### AI service returning errors

```bash
# Check FastAPI logs
docker compose logs fastapi-ai --tail=50

# Verify API key is set
docker compose exec fastapi-ai env | grep CLOUDRU

# Test direct API call
curl http://localhost:8000/health
```

### Module update fails

```bash
# Check for Python syntax errors
docker compose exec odoo python -c "import stroyuprav_estimate"

# Force reinstall module
docker compose exec odoo odoo -i stroyuprav_<name> --stop-after-init
```
