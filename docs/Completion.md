# Completion: СтройУправ

## 1. Deployment Strategy

### 1.1 Environment Setup

| Environment | Purpose | URL | Infrastructure |
|-------------|---------|-----|---------------|
| `dev` | Local development | `http://localhost:8069` | Docker Compose on dev machine |
| `staging` | QA, demo, pre-prod | `https://staging.stroiuprav.ru` | VPS 4 vCPU / 8GB RAM (AdminVPS) |
| `prod` | Production | `https://app.stroiuprav.ru` | VPS 8 vCPU / 16GB RAM (HOSTKEY) |

**Environment variable management:**
```
.env.example     — committed, template with placeholders
.env.dev         — local only, gitignored
.env.staging     — stored in GitHub Secrets
.env.prod        — stored in GitHub Secrets + VPS /etc/stroiuprav/.env
```

**Required env vars:**
```bash
# Core
DATABASE_URL=postgresql://stroiuprav:${DB_PASSWORD}@db:5432/stroiuprav
REDIS_URL=redis://redis:6379/0
SECRET_KEY=<random-64-char>

# AI Providers (OpenAI-compatible client)
CLOUDRU_API_KEY=<cloud.ru-key>
CLOUDRU_MODEL=qwen3-72b
OPENAI_API_KEY=<fallback-only>
LITELLM_MASTER_KEY=<openai-proxy-key>

# Storage (S3-compatible)
S3_ENDPOINT=https://s3.cloud.ru
S3_BUCKET=stroiuprav-photos
S3_ACCESS_KEY=<key>
S3_SECRET_KEY=<secret>

# Payments
YUKASSA_SHOP_ID=<shop-id>
YUKASSA_SECRET_KEY=<secret>
YUKASSA_WEBHOOK_SECRET=<hmac-secret>

# Monitoring
SENTRY_DSN=https://<key>@sentry.stroiuprav.ru/1
GRAFANA_ADMIN_PASSWORD=<password>
```

### 1.2 Docker Compose Configuration

```yaml
# docker-compose.yml (production)
version: "3.8"

services:
  odoo:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "127.0.0.1:8069:8069"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    volumes:
      - odoo-data:/var/lib/odoo
      - ./custom-addons:/mnt/extra-addons
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: "4"

  celery-worker:
    build:
      context: .
      dockerfile: Dockerfile
    command: celery -A stroiuprav.celery worker -l info -c 4 -Q estimates,photos,billing
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - CLOUDRU_API_KEY=${CLOUDRU_API_KEY}
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G

  celery-beat:
    build:
      context: .
      dockerfile: Dockerfile
    command: celery -A stroiuprav.celery beat -l info --schedule=/var/run/celerybeat-schedule
    depends_on:
      - redis
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: stroiuprav
      POSTGRES_USER: stroiuprav
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./backups:/backups
    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U stroiuprav"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis-data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - certbot-data:/var/www/certbot:ro
    depends_on:
      - odoo
    restart: unless-stopped

  certbot:
    image: certbot/certbot
    volumes:
      - ./nginx/ssl:/etc/letsencrypt
      - certbot-data:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"

  openai:
    image: ghcr.io/berriai/openai:main-latest
    ports:
      - "127.0.0.1:4000:4000"
    environment:
      - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}
    volumes:
      - ./openai-config.yaml:/app/config.yaml
    command: --config /app/config.yaml
    restart: unless-stopped

volumes:
  postgres-data:
  redis-data:
  odoo-data:
  certbot-data:
```

### 1.3 VPS Provisioning (AdminVPS / HOSTKEY)

**Production server (HOSTKEY):**
```bash
# 1. Provision VPS
# Plan: Dedicated 8 vCPU / 16GB RAM / 200GB NVMe SSD
# OS: Ubuntu 22.04 LTS
# Location: Moscow (Tier III DC)

# 2. Initial setup
apt update && apt upgrade -y
apt install -y docker.io docker-compose-v2 ufw fail2ban

# 3. Security hardening
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH (change port later)
ufw allow 80/tcp    # HTTP -> redirect to HTTPS
ufw allow 443/tcp   # HTTPS
ufw enable

# 4. Create deploy user
useradd -m -s /bin/bash deploy
usermod -aG docker deploy
mkdir -p /home/deploy/.ssh
# Copy SSH public key

# 5. SSH hardening
sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd

# 6. Swap (safety net)
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

**Staging server (AdminVPS):**
- Plan: 4 vCPU / 8GB RAM / 100GB SSD
- Same setup, lighter resource limits in Docker Compose

### 1.4 Domain and SSL (Let's Encrypt)

```bash
# DNS records (configured at registrar):
# A     app.stroiuprav.ru        -> <prod-ip>
# A     staging.stroiuprav.ru    -> <staging-ip>
# A     api.stroiuprav.ru        -> <prod-ip>       (optional, same server)
# CNAME www.stroiuprav.ru        -> app.stroiuprav.ru

# Initial certificate
docker compose run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d app.stroiuprav.ru \
  -d api.stroiuprav.ru \
  --email devops@stroiuprav.ru \
  --agree-tos \
  --no-eff-email

# Auto-renewal: handled by certbot container (every 12h check)
# Nginx reload after renewal:
# Add to certbot command: --deploy-hook "docker compose exec nginx nginx -s reload"
```

**Nginx config:**
```nginx
# nginx/conf.d/stroiuprav.conf
server {
    listen 80;
    server_name app.stroiuprav.ru;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name app.stroiuprav.ru;

    ssl_certificate /etc/nginx/ssl/live/app.stroiuprav.ru/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/live/app.stroiuprav.ru/privkey.pem;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; img-src 'self' https://s3.cloud.ru; style-src 'self' 'unsafe-inline'";

    # Photo uploads
    client_max_body_size 50M;

    location / {
        proxy_pass http://odoo:8069;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket for real-time updates
    location /websocket {
        proxy_pass http://odoo:8072;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Static files caching
    location /web/static/ {
        proxy_pass http://odoo:8069;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
}
```

---

## 2. CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install ruff mypy
      - run: ruff check .
      - run: ruff format --check .
      - run: mypy stroiuprav/ --ignore-missing-imports

  test-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/unit/ --cov=stroiuprav --cov-report=xml --cov-fail-under=80 --timeout=30
      - uses: codecov/codecov-action@v4
        with:
          file: coverage.xml

  test-integration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: stroiuprav_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/integration/ --timeout=60
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/stroiuprav_test
          REDIS_URL: redis://localhost:6379/0

  test-e2e:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - run: docker compose -f docker-compose.test.yml up -d --build
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npx playwright install --with-deps chromium
      - run: npx playwright test --project=chromium
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/

  build-and-push:
    needs: [lint, test-unit, test-integration]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}

  deploy-staging:
    needs: [build-and-push]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: staging
    steps:
      - name: Deploy to staging
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: deploy
          key: ${{ secrets.STAGING_SSH_KEY }}
          script: |
            cd /home/deploy/stroiuprav
            docker compose pull
            docker compose up -d --remove-orphans
            docker compose exec -T odoo python -m stroiuprav.migrate
            echo "Staging deployed: $(date)"

  deploy-prod:
    needs: [deploy-staging, test-e2e]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://app.stroiuprav.ru
    steps:
      - name: Deploy to production
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.PROD_HOST }}
          username: deploy
          key: ${{ secrets.PROD_SSH_KEY }}
          script: |
            cd /home/deploy/stroiuprav
            # Blue-green: pull new, keep old running
            docker compose pull
            docker compose up -d --remove-orphans
            # Health check
            sleep 10
            curl -f http://localhost:8069/web/health || (docker compose logs --tail=50 && exit 1)
            docker compose exec -T odoo python -m stroiuprav.migrate
            echo "Production deployed: $(date)"

  ai-accuracy-nightly:
    runs-on: ubuntu-latest
    if: github.event.schedule == '0 3 * * *'  # 3 AM UTC daily
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/ai_accuracy/ --timeout=600 -v
        env:
          CLOUDRU_API_KEY: ${{ secrets.CLOUDRU_API_KEY }}
      - uses: actions/upload-artifact@v4
        with:
          name: ai-accuracy-results
          path: tests/ai_accuracy/results/
```

---

## 3. Database Migration Strategy

### Odoo Module Migrations

```python
# custom-addons/stroiuprav_core/migrations/16.0.1.1/pre-migrate.py
"""
Migration naming: <odoo_version>.<module_version>/pre-migrate.py | post-migrate.py

pre-migrate:  runs BEFORE module update (schema changes, data prep)
post-migrate: runs AFTER module update (data migration, cleanup)
"""

def migrate(cr, version):
    """Add index for project dashboard performance."""
    cr.execute("""
        CREATE INDEX IF NOT EXISTS idx_project_company_status
        ON stroiuprav_project(company_id, status)
        WHERE status != 'archived';
    """)
```

### Alembic Migrations (for non-Odoo tables)

```bash
# Directory structure
migrations/
  alembic.ini
  env.py
  versions/
    001_initial_schema.py
    002_add_estimate_versioning.py
    003_add_photo_geotag_index.py
```

**Migration rules:**
1. Every migration MUST be reversible (`downgrade()` implemented)
2. No data-destructive migrations without explicit backup step
3. Large table migrations: use `CREATE INDEX CONCURRENTLY` (no table lock)
4. Test migrations on staging with production-volume data copy first
5. Migration timeout: 5 min max. Longer migrations -> split into batches.

**Migration workflow:**
```bash
# Create migration
alembic revision --autogenerate -m "add_estimate_versioning"

# Review generated migration (ALWAYS review autogenerate output)
# Apply to staging
alembic upgrade head

# Apply to production (via CI/CD deploy step)
docker compose exec -T odoo python -m stroiuprav.migrate

# Rollback (if needed)
alembic downgrade -1
```

**ГЭСН/ФЕР reference data updates:**
```python
# Quarterly update job (manual trigger + CI)
# 1. Download new ГЭСН/ФЕР indexes from Минстрой
# 2. Parse XML/CSV -> staging table
# 3. Diff against current data
# 4. Apply changes in transaction
# 5. Recalculate active estimates with new indexes (background job)
# 6. Notify affected users
```

---

## 4. Monitoring & Alerting

### 4.1 Application Monitoring (Sentry)

```python
# sentry_sdk initialization
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration

sentry_sdk.init(
    dsn=os.environ["SENTRY_DSN"],
    environment=os.environ.get("ENVIRONMENT", "dev"),
    traces_sample_rate=0.1,  # 10% of transactions for performance
    profiles_sample_rate=0.05,
    integrations=[CeleryIntegration(), RedisIntegration()],
    before_send=filter_pii,  # Strip personal data (152-ФЗ)
)
```

**Alert rules:**
| Condition | Severity | Channel |
|-----------|----------|---------|
| Error rate > 5% in 5 min | Critical | Telegram bot + email |
| P95 response time > 5 sec | Warning | Telegram bot |
| Unhandled exception | Error | Sentry default (email) |
| AI provider timeout rate > 20% | Critical | Telegram bot |
| Celery queue depth > 100 | Warning | Telegram bot |

### 4.2 Infrastructure Monitoring (Prometheus + Grafana)

```yaml
# docker-compose.monitoring.yml (separate from app)
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "127.0.0.1:9090:9090"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD}
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "127.0.0.1:3000:3000"
    restart: unless-stopped

  node-exporter:
    image: prom/node-exporter:latest
    pid: host
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
    command: --path.procfs=/host/proc --path.sysfs=/host/sys
    restart: unless-stopped

  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    environment:
      DATA_SOURCE_NAME: "postgresql://stroiuprav:${DB_PASSWORD}@db:5432/stroiuprav?sslmode=disable"
    restart: unless-stopped

  redis-exporter:
    image: oliver006/redis_exporter:latest
    environment:
      REDIS_ADDR: redis://redis:6379
    restart: unless-stopped
```

**Key metrics tracked:**
| Category | Metric | Alert Threshold |
|----------|--------|----------------|
| CPU | node_cpu_usage | > 80% sustained 5 min |
| Memory | node_memory_usage | > 85% |
| Disk | node_disk_usage | > 80% |
| PostgreSQL | pg_connections_active | > 80% of pool |
| PostgreSQL | pg_replication_lag | > 30 sec |
| Redis | redis_memory_used | > 400MB (of 512MB limit) |
| Docker | container_restart_count | > 3 in 10 min |

### 4.3 Business Metrics Dashboards

**Grafana dashboards (custom):**

**Dashboard 1: Revenue & Growth**
- MRR (Monthly Recurring Revenue) — target vs actual
- New subscriptions this week/month
- Churn rate (weekly rolling)
- ARPU (Average Revenue Per User)
- Trial-to-paid conversion funnel

**Dashboard 2: Product Usage**
- DAU / WAU / MAU
- AI-estimates generated per day (with P50/P95 generation time)
- Photos uploaded per day
- Projects created per week
- Feature adoption rates (% users using each P0 feature)

**Dashboard 3: Operational Health**
- API response time (P50, P95, P99)
- Error rate by endpoint
- Celery queue depth and processing time
- AI provider availability and failover events
- Database query performance (slow queries > 1 sec)

**Data source:** Application logs -> structured JSON -> Loki or direct PostgreSQL queries via Grafana.

### 4.4 AI Monitoring

| Metric | How | Alert |
|--------|-----|-------|
| Estimate accuracy | Nightly benchmark vs manual estimates | Accuracy < 80% |
| ГЭСН code hit rate | `found / total` per estimate | Hit rate < 85% |
| AI latency P95 | OpenAI-compatible client metrics | > 120 sec |
| Token usage | OpenAI-compatible client usage tracking | > budget threshold |
| Provider failover frequency | Count of fallback events | > 10/hour |
| Prompt injection attempts | Count of `PROMPT_INJECTION_DETECTED` | > 5/day |

---

## 5. Rollback Strategy

### Application Rollback

```bash
# 1. Identify last known good image
docker images ghcr.io/stroiuprav/stroiuprav --format "{{.Tag}} {{.CreatedAt}}" | head -5

# 2. Rollback to previous version
cd /home/deploy/stroiuprav
export ROLLBACK_TAG=<previous-commit-sha>

# Update docker-compose to use specific tag
sed -i "s|image:.*stroiuprav:.*|image: ghcr.io/stroiuprav/stroiuprav:${ROLLBACK_TAG}|" docker-compose.yml
docker compose up -d --remove-orphans

# 3. Verify health
curl -f https://app.stroiuprav.ru/web/health

# 4. If database migration needs rollback
docker compose exec -T odoo alembic downgrade -1
```

**Rollback decision matrix:**
| Situation | Action | Max Time |
|-----------|--------|----------|
| App crashes on startup | Rollback image immediately | 2 min |
| Performance degradation > 3x | Rollback image | 5 min |
| Data corruption detected | Stop writes, assess, rollback image + DB | 15 min |
| Non-critical bug found | Hotfix forward, no rollback | N/A |

**Rules:**
- Keep last 5 Docker images tagged and available
- Database rollback: only if migration was applied < 1 hour ago
- After rollback: create incident report within 24 hours
- Never rollback ГЭСН reference data (append-only, versioned)

---

## 6. Data Backup

### PostgreSQL Backup

```bash
# 1. Daily full backup (pg_dump)
# Cron: 02:00 MSK daily
0 23 * * * /home/deploy/scripts/backup-db.sh

# backup-db.sh
#!/bin/bash
set -euo pipefail
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/backups/postgres
RETENTION_DAYS=30

docker compose exec -T db pg_dump \
  -U stroiuprav \
  -Fc \
  --compress=9 \
  stroiuprav > "${BACKUP_DIR}/stroiuprav_${TIMESTAMP}.dump"

# Upload to S3 (off-site)
aws s3 cp "${BACKUP_DIR}/stroiuprav_${TIMESTAMP}.dump" \
  s3://stroiuprav-backups/postgres/ \
  --storage-class STANDARD_IA

# Cleanup old local backups
find "${BACKUP_DIR}" -name "*.dump" -mtime +${RETENTION_DAYS} -delete

echo "[$(date)] Backup completed: stroiuprav_${TIMESTAMP}.dump"
```

**WAL archiving (Point-in-Time Recovery):**
```ini
# postgresql.conf additions
wal_level = replica
archive_mode = on
archive_command = 'test ! -f /backups/wal/%f && cp %p /backups/wal/%f'
archive_timeout = 300  # Force archive every 5 min even if not full
```

```bash
# WAL backup to S3 (every hour)
0 * * * * aws s3 sync /backups/wal/ s3://stroiuprav-backups/wal/ --delete
```

**Recovery procedure:**
```bash
# Point-in-time recovery
pg_restore -U stroiuprav -d stroiuprav_recovery <latest_full_backup.dump>
# Apply WAL up to target time
recovery_target_time = '2026-05-27 14:30:00 MSK'
```

### Photo Backup

```bash
# Photos stored in S3/MinIO with versioning enabled
# Replication: Cloud.ru S3 -> separate bucket in different region

# S3 lifecycle policy:
# - Original photos: keep indefinitely
# - Thumbnails: regeneratable, no backup needed
# - Deleted photos: soft delete, hard delete after 90 days

# Backup verification (weekly)
# Compare S3 object count vs database photo count
# Alert if delta > 1%
```

### Backup Verification

```bash
# Monthly backup restore test
# 1. Restore latest backup to test DB
# 2. Run sanity queries (project count, estimate count, user count)
# 3. Compare with production counts
# 4. Log result to monitoring

# Automated test (GitHub Actions, monthly schedule)
# .github/workflows/backup-verify.yml
```

---

## 7. Compliance Checklist

### 152-ФЗ (Персональные данные)

| Requirement | Implementation | Status |
|-------------|---------------|--------|
| Согласие на обработку ПД | Checkbox при регистрации + ссылка на политику конфиденциальности | TODO |
| Хранение ПД на территории РФ | VPS: HOSTKEY (Moscow DC), S3: Cloud.ru (Moscow) | DONE (by infra choice) |
| Шифрование at rest | PostgreSQL: TDE или disk-level encryption. S3: server-side encryption (AES-256) | TODO |
| Шифрование in transit | TLS 1.3 everywhere (nginx, DB connections, S3) | TODO |
| Право на удаление | API endpoint: DELETE /api/v1/users/me + cascade delete всех данных пользователя в течение 30 дней | TODO |
| Право на выгрузку | API endpoint: GET /api/v1/users/me/export -> ZIP с данными пользователя | TODO |
| Уведомление Роскомнадзора | Подача уведомления об обработке ПД до запуска | TODO |
| Назначение ответственного за ПД | Документ о назначении DPO (даже если совмещение) | TODO |
| Политика конфиденциальности | Публикация на сайте: stroiuprav.ru/privacy | TODO |
| Логирование доступа к ПД | Audit log: кто, когда, какие данные запрашивал | TODO |
| Sentry: фильтрация ПД | `before_send` hook: strip email, phone, ФИО из error reports | TODO |

### ГОСТ для КС-2 / КС-3

| Requirement | Standard | Implementation |
|-------------|----------|---------------|
| Формат КС-2 (акт выполненных работ) | Унифицированная форма №КС-2 (Постановление Госкомстата №100) | PDF-генератор с точным соответствием формы. Поля: номер, дата, заказчик, подрядчик, объект, позиции работ. |
| Формат КС-3 (справка о стоимости) | Унифицированная форма №КС-3 | PDF-генератор. Нарастающий итог с начала строительства. |
| Расценки по ГЭСН/ФЕР | МДС 81-35.2004, приказы Минстроя | База ГЭСН/ФЕР в PostgreSQL. Квартальное обновление индексов. |
| Индексы пересчёта | Письма Минстроя (ежеквартально) | Таблица `price_index`: регион, квартал, вид работ, значение индекса. |
| Электронная подпись (опционально) | 63-ФЗ "Об электронной подписи" | P2: интеграция с КриптоПро CSP для усиленной квалифицированной ЭП. MVP: без ЭП. |

---

## 8. Launch Checklist

### Pre-Launch (Day -14 to Day -1)

**Infrastructure:**
- [ ] Production VPS provisioned and hardened (firewall, SSH keys, fail2ban)
- [ ] Docker Compose stack running stable on production (72h soak test)
- [ ] SSL certificates issued and auto-renewal verified
- [ ] DNS records configured and propagated
- [ ] PostgreSQL WAL archiving enabled and tested
- [ ] Daily backup cron job active and first backup verified
- [ ] S3 bucket created with versioning enabled
- [ ] Redis memory limits configured

**Application:**
- [ ] All P0 features (F01-F08) implemented and tested
- [ ] AI-сметчик accuracy >= 80% on benchmark dataset
- [ ] ЮKassa payment integration tested with test credentials
- [ ] ЮKassa webhook HMAC verification implemented
- [ ] JWT auth with httpOnly cookies (NOT localStorage)
- [ ] Rate limiting configured (API + AI endpoints)
- [ ] CORS configured (allowed origins: app.stroiuprav.ru only)
- [ ] Health check endpoint `/web/health` returns 200

**Security:**
- [ ] Penetration test (basic: OWASP Top 10 scan)
- [ ] No hardcoded secrets in codebase (grep for API keys, passwords)
- [ ] `.env` files gitignored
- [ ] Input validation on all user-facing endpoints
- [ ] IDOR checks on photo, project, task access
- [ ] CSP headers configured
- [ ] SQL injection: parameterized queries only (audit complete)

**Monitoring:**
- [ ] Sentry configured with PII filtering
- [ ] Prometheus + Grafana dashboards deployed
- [ ] Alert channels configured (Telegram bot for critical alerts)
- [ ] Error rate baseline established (from staging traffic)
- [ ] AI accuracy tracking dashboard live

**Legal & Compliance:**
- [ ] Политика конфиденциальности опубликована
- [ ] Пользовательское соглашение опубликовано
- [ ] Уведомление в Роскомнадзор подано
- [ ] Оферта для SaaS-подписки готова
- [ ] Реквизиты юрлица на сайте

**Content:**
- [ ] Landing page live (stroiuprav.ru)
- [ ] Onboarding quiz flow tested (4 questions -> dashboard < 3 min)
- [ ] Demo project/estimate seeded for new users
- [ ] Help/FAQ section (минимум 10 вопросов)

### Launch Day (Day 0)

**Morning (09:00 MSK):**
- [ ] Final backup of staging database
- [ ] Deploy latest build to production
- [ ] Run database migrations
- [ ] Smoke test: registration -> onboarding -> create project -> AI estimate -> PDF export
- [ ] Verify ЮKassa production credentials active
- [ ] Enable production AI providers (Cloud.ru)

**Go-Live (12:00 MSK):**
- [ ] Switch DNS / remove "coming soon" page
- [ ] Monitor error rate (Sentry) — first 30 min watch
- [ ] Monitor AI estimate generation — first 10 estimates success
- [ ] Test payment flow with real card (refund immediately)
- [ ] Post launch announcement (Telegram channel, social media)

**Evening (18:00 MSK):**
- [ ] Review Sentry for new errors
- [ ] Check Grafana dashboards: response times, error rates
- [ ] Verify nightly backup cron will run at 02:00
- [ ] Document any launch issues in incident log

### Post-Launch (Day 1-14)

**Daily:**
- [ ] Review Sentry errors (target: < 5 unique errors/day)
- [ ] Check AI accuracy metrics
- [ ] Monitor MRR and signup funnel
- [ ] Respond to user feedback within 4 hours

**Week 1:**
- [ ] Analyze first 50 AI estimates — manual quality check
- [ ] Review server resource usage (CPU, memory, disk) — resize if needed
- [ ] First backup restore test on separate server
- [ ] Collect NPS from first 10 active users
- [ ] Fix any P0 bugs found in production

**Week 2:**
- [ ] Performance baseline established (P50, P95, P99 response times)
- [ ] AI prompt tuning based on real-world usage patterns
- [ ] First monthly ГЭСН index update (if applicable)
- [ ] Plan P1 features (F09-F14) based on user feedback
- [ ] Publish first changelog / release notes
