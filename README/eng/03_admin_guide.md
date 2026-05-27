# Admin Guide

Deployment, configuration, monitoring, and maintenance for StroyUprav.

---

## Table of Contents

1. [System Requirements](#1-system-requirements)
2. [VPS Deployment](#2-vps-deployment)
3. [Docker Configuration](#3-docker-configuration)
4. [SSL / TLS Setup](#4-ssl--tls-setup)
5. [Monitoring and Alerting](#5-monitoring-and-alerting)
6. [Backups](#6-backups)
7. [Cloud.ru API Setup](#7-cloudru-api-setup)
8. [YuKassa Payment Setup](#8-yukassa-payment-setup)
9. [Elasticsearch and GESN/FER Data](#9-elasticsearch-and-gesnfer-data)
10. [Security Checklist](#10-security-checklist)
11. [Scaling](#11-scaling)

---

## 1. System Requirements

### Minimum (MVP, up to 100 users)

| Resource | Value |
|----------|-------|
| CPU | 4 cores |
| RAM | 16 GB |
| Disk | 100 GB SSD |
| OS | Ubuntu 22.04 LTS / Debian 12 |
| Network | Public IP, ports 80/443 open |

### Recommended (up to 1,000 users)

| Resource | Value |
|----------|-------|
| CPU | 8 cores |
| RAM | 32 GB |
| Disk | 500 GB NVMe SSD |
| Separate DB disk | 200 GB for PostgreSQL |

### VPS Providers (Russia-based, 152-FZ compliant)

- **AdminVPS** -- budget option, good for MVP
- **HOSTKEY** -- dedicated servers, better for production

---

## 2. VPS Deployment

### Initial server setup

```bash
# Update the system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker

# Install Docker Compose plugin
apt install docker-compose-plugin -y

# Create application user
useradd -m -s /bin/bash stroyuprav
usermod -aG docker stroyuprav

# Switch to app user
su - stroyuprav
```

### Deploy the application

```bash
# Clone the repository
git clone https://github.com/your-org/stroyuprav.git
cd stroyuprav

# Configure environment
cp .env.example .env
nano .env    # Fill in all required values

# Build and start
docker compose up -d --build

# Verify all services
docker compose ps
```

### Firewall configuration

```bash
# Allow only HTTP, HTTPS, and SSH
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

> **Do not expose** ports 5432 (PostgreSQL), 6379 (Redis), 9200 (Elasticsearch), 9000/9001 (MinIO) to the public internet. They are internal-only via Docker networking.

---

## 3. Docker Configuration

### Services Overview (9 containers)

| Service | Image | Ports | Memory Limit | Purpose |
|---------|-------|-------|:------------:|---------|
| `nginx` | nginx:alpine | 80, 443 | -- | Reverse proxy, SSL termination, static files |
| `odoo` | Custom build | 8069 (internal) | 4 GB | ERP backend (business logic, ORM, auth) |
| `fastapi-ai` | Custom build | 8000 (internal) | 2 GB | AI endpoints (estimator, drawing parser) |
| `postgres` | postgres:16-alpine | 5432 (internal) | 2 GB | Primary database |
| `redis` | redis:7-alpine | 6379 (internal) | 512 MB | Cache, sessions, Celery broker |
| `celery-worker` | Custom build | -- | 2 GB | Async tasks: AI generation, PDF export, billing |
| `celery-beat` | Custom build | -- | -- | Periodic task scheduler |
| `minio` | minio/minio:latest | 9000, 9001 (internal) | -- | S3-compatible object storage (photos, PDFs) |
| `elasticsearch` | elasticsearch:8.13.0 | 9200 (internal) | 2 GB | Full-text search for GESN/FER (200K+ rates) |

### Volumes

| Volume | Purpose |
|--------|---------|
| `postgres-data` | PostgreSQL data files |
| `redis-data` | Redis persistence |
| `odoo-data` | Odoo filestore |
| `certbot-data` | SSL certificate data |
| `minio-data` | Uploaded files (photos, drawings, PDFs) |
| `es-data` | Elasticsearch indices |

### Resource Tuning

Edit `docker-compose.yml` to adjust resource limits:

```yaml
deploy:
  resources:
    limits:
      memory: 4G    # Increase for more concurrent users
      cpus: "4"
```

---

## 4. SSL / TLS Setup

### Option A: Let's Encrypt with Certbot

```bash
# Install certbot
apt install certbot python3-certbot-nginx -y

# Obtain certificate
certbot certonly --webroot -w /var/www/certbot \
  -d stroyuprav.example.com \
  --agree-tos --email admin@example.com

# Certificate files will be at:
# /etc/letsencrypt/live/stroyuprav.example.com/fullchain.pem
# /etc/letsencrypt/live/stroyuprav.example.com/privkey.pem
```

### Nginx SSL configuration

Create `nginx/conf.d/stroyuprav.conf`:

```nginx
server {
    listen 80;
    server_name stroyuprav.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name stroyuprav.example.com;

    ssl_certificate     /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols       TLSv1.3;
    ssl_prefer_server_ciphers on;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # CSP and security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    # Odoo backend
    location / {
        proxy_pass http://odoo:8069;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # FastAPI AI service
    location /api/ {
        proxy_pass http://fastapi-ai:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Auto-renewal

```bash
# Add cron job for certificate renewal
echo "0 3 * * * certbot renew --quiet && docker compose restart nginx" | crontab -
```

---

## 5. Monitoring and Alerting

### Stack: Prometheus + Grafana + Loki

The monitoring stack is defined in `docker-compose.monitoring.yml` (or added to the main compose file).

#### Prometheus

Collects metrics from all services:
- Odoo: custom `/metrics` endpoint
- FastAPI: automatic `/metrics` via `prometheus-fastapi-instrumentator`
- PostgreSQL: `postgres_exporter`
- Redis: `redis_exporter`
- Elasticsearch: `elasticsearch_exporter`

#### Grafana Dashboards

Access Grafana at `http://your-server:3000` (default credentials: `admin/admin`).

Recommended dashboards:
- **System Overview** -- CPU, RAM, disk, network per container
- **Odoo Performance** -- request latency, active sessions, ORM queries
- **AI Service** -- estimate generation time, model API latency, error rates
- **Database** -- connections, query duration, table sizes
- **Business Metrics** -- estimates/day, active users, revenue

#### Loki (Centralized Logging)

Collects logs from all containers via Promtail. Query logs in Grafana:

```logql
{container="odoo"} |= "ERROR"
{container="fastapi-ai"} | json | status >= 500
```

### Key Alerts to Configure

| Alert | Condition | Severity |
|-------|-----------|----------|
| Service down | Any container not running for > 2 min | Critical |
| High memory | Container > 90% memory limit | Warning |
| Disk space | < 10% free | Critical |
| DB connections | > 80% of `max_connections` | Warning |
| AI latency | Estimate generation > 120s (P95) | Warning |
| Error rate | > 5% of requests returning 5xx | Critical |

---

## 6. Backups

### PostgreSQL

The `backups` directory is mounted into the postgres container.

```bash
# Manual backup
docker compose exec postgres pg_dump -U stroiuprav stroiuprav | gzip > backups/stroiuprav_$(date +%Y%m%d_%H%M%S).sql.gz

# Restore from backup
gunzip < backups/stroiuprav_20260527_120000.sql.gz | docker compose exec -T postgres psql -U stroiuprav stroiuprav
```

#### Automated daily backup (cron)

```bash
# Add to crontab
0 2 * * * cd /home/stroyuprav/stroyuprav && docker compose exec -T postgres pg_dump -U stroiuprav stroiuprav | gzip > backups/stroiuprav_$(date +\%Y\%m\%d).sql.gz
```

### MinIO (Object Storage)

```bash
# Install MinIO client
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc && mv mc /usr/local/bin/

# Configure
mc alias set local http://localhost:9000 minioadmin YOUR_PASSWORD

# Mirror to backup location
mc mirror local/stroiuprav /backups/minio/
```

### Retention Policy

| Data | Retention | Frequency |
|------|-----------|-----------|
| PostgreSQL | 30 daily + 12 monthly | Daily at 02:00 |
| MinIO files | Mirrored weekly | Weekly on Sunday |
| Elasticsearch | Rebuild from source data | On demand |
| Redis | Not backed up (cache only) | -- |

---

## 7. Cloud.ru API Setup

Cloud.ru Foundation Models is the primary AI provider for the estimator.

### 1. Create an account

Register at [cloud.ru](https://cloud.ru) and activate Foundation Models service.

### 2. Get API credentials

1. Go to Cloud.ru console > Foundation Models > API Keys
2. Create a new API key
3. Copy the key and base URL

### 3. Configure environment variables

```bash
CLOUDRU_API_KEY=your-cloud-ru-api-key
CLOUDRU_API_BASE=https://api.cloud.ru/v1
CLOUDRU_MODEL=qwen3-72b
```

### Available Models

| Model | Use Case | Notes |
|-------|----------|-------|
| `qwen3-72b` | Default for cost estimation | Good balance of speed and accuracy |
| `qwen3-coder-480b` | Work classification | Highest accuracy, slower |
| `deepseek-v3` | Alternative estimator | Fast, good for high-volume |
| `t-pro-it-2.0` | Russian text processing | Optimized for Russian language |

### Fallback to OpenAI

If Cloud.ru is unavailable, the system falls back to OpenAI:

```bash
OPENAI_API_KEY=your-openai-api-key
```

The fallback is automatic -- no manual switching required. The AI client uses the OpenAI-compatible API format, switchable via `AI_BASE_URL`.

---

## 8. YuKassa Payment Setup

### 1. Register a merchant account

1. Go to [yukassa.ru](https://yukassa.ru)
2. Register as a legal entity (ИП or ООО)
3. Complete verification (1-3 business days)

### 2. Get credentials

From the YuKassa dashboard:
- **Shop ID** -- numeric merchant identifier
- **Secret Key** -- API authentication key
- **Webhook Secret** -- HMAC-SHA256 key for webhook verification

### 3. Configure webhooks

In YuKassa dashboard, set the webhook URL:
```
https://stroyuprav.example.com/api/webhooks/yukassa
```

Events to subscribe to:
- `payment.succeeded`
- `payment.canceled`
- `refund.succeeded`

### 4. Environment variables

```bash
YUKASSA_SHOP_ID=your-shop-id
YUKASSA_SECRET_KEY=your-secret-key
YUKASSA_WEBHOOK_SECRET=your-webhook-secret
```

> **Security:** All webhooks are verified with HMAC-SHA256 + replay protection (5-minute window). Never disable webhook verification.

---

## 9. Elasticsearch and GESN/FER Data

### Initial data load

The GESN/FER normative database (200,000+ unit rates) must be loaded into Elasticsearch:

```bash
# Load GESN/FER data (from the data/ directory)
docker compose exec fastapi-ai python -m scripts.load_gesn_fer
```

### Index structure

| Index | Documents | Purpose |
|-------|-----------|---------|
| `gesn_rates` | ~120K | State Elemental Estimate Norms |
| `fer_rates` | ~80K | Federal Unit Rates |
| `minstroy_indices` | ~1K | Quarterly price indices by region |

### Updating indices (quarterly)

When Minstroy publishes new quarterly indices:

1. Download the updated index file
2. Place it in `data/indices/`
3. Run: `docker compose exec fastapi-ai python -m scripts.update_indices`

---

## 10. Security Checklist

Before going to production, verify:

- [ ] All `.env` secrets are unique, strong, and not defaults
- [ ] `SECRET_KEY` is a random 64-character string
- [ ] SSL/TLS 1.3 is active (no HTTP access)
- [ ] HSTS header is set
- [ ] Internal ports (5432, 6379, 9200, 9000) are not exposed to the internet
- [ ] Firewall allows only 22, 80, 443
- [ ] JWT tokens are stored in httpOnly cookies (not localStorage)
- [ ] Roles cannot be assigned via the registration endpoint
- [ ] YuKassa webhook HMAC verification is enabled
- [ ] File uploads are validated (MIME + magic bytes, 20 MB limit)
- [ ] Rate limiting is configured: 100 req/min auth, 20 req/min anon, 10 req/min AI
- [ ] ClamAV is scanning uploaded files
- [ ] Audit logging is enabled (1-year retention)
- [ ] Row-level security is active in PostgreSQL
- [ ] No secrets in git history

---

## 11. Scaling

### Horizontal Scaling (Docker replicas)

```bash
# Scale Odoo to 3 instances (Nginx load balances)
docker compose up -d --scale odoo=3

# Scale Celery workers
docker compose up -d --scale celery-worker=4
```

### Vertical Scaling

Upgrade VPS resources. Key bottlenecks in order:
1. **PostgreSQL** -- RAM for shared_buffers, CPU for complex queries
2. **Elasticsearch** -- RAM for JVM heap (set ES_JAVA_OPTS)
3. **Odoo** -- RAM for concurrent sessions
4. **FastAPI** -- CPU for AI request processing

### Year 1 to Year 2 Migration Path

| Metric | Year 1 | Year 2 |
|--------|--------|--------|
| Concurrent users | 1,000 | 10,000 |
| Uptime SLA | 99.5% | 99.9% |
| Architecture | Single VPS | Multi-VPS + load balancer |
| Database | Single PostgreSQL | Primary + read replicas |
| Cache | Single Redis | Redis Sentinel |
