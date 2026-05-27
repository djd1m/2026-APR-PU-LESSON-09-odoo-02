# Completion: AI-Estimator (F01)

Deployment, ГЭСН data import, monitoring, and operational readiness.

---

## 1. Deployment Plan

### 1.1 Services to Deploy

| Service | Image | Resources (Y1) | Health Check |
|---------|-------|-----------------|--------------|
| ai-service | `ai_service:latest` | 2 CPU, 4GB RAM | `GET /health` |
| celery-worker | `ai_service:latest` | 2 CPU, 4GB RAM | celery inspect ping |
| elasticsearch | `elasticsearch:8.14.0` | 4 CPU, 8GB RAM | `GET /_cluster/health` |
| redis | `redis:7-alpine` | 1 CPU, 1GB RAM | `redis-cli ping` |
| postgres | `postgres:16-alpine` | 2 CPU, 4GB RAM | `pg_isready` |
| nginx | `nginx:alpine` | 0.5 CPU, 256MB | TCP check :443 |

### 1.2 Environment Variables (Required)

All required. Service crashes on startup if any is missing.

| Variable | Service | Example |
|----------|---------|---------|
| `AI_BASE_URL` | ai-service | `https://api.cloud.ru/v1` |
| `AI_API_KEY` | ai-service | (secret) |
| `AI_MODEL` | ai-service | `qwen3-coder-480b` |
| `AI_VISION_MODEL` | ai-service | `qwen3-vl` |
| `EMBEDDING_MODEL` | ai-service | `bge-m3` |
| `ELASTICSEARCH_URL` | ai-service | `http://elasticsearch:9200` |
| `DATABASE_URL` | ai-service | `postgresql://user:pass@postgres/stroyuprav` |
| `REDIS_URL` | ai-service, celery | `redis://redis:6379/0` |
| `S3_ENDPOINT` | ai-service | `https://s3.cloud.ru` |
| `S3_ACCESS_KEY` | ai-service | (secret) |
| `S3_SECRET_KEY` | ai-service | (secret) |
| `S3_BUCKET_ESTIMATES` | ai-service | `stroyuprav-estimates` |
| `S3_BUCKET_DRAWINGS` | ai-service | `stroyuprav-drawings` |

### 1.3 Deployment Sequence

```
1. Deploy infrastructure (postgres, redis, elasticsearch)
2. Run DB migrations (alembic upgrade head)
3. Import ГЭСН/ФЕР data into Elasticsearch (see section 2)
4. Import Минстрой indices into PostgreSQL (see section 2)
5. Deploy ai-service + celery-worker
6. Deploy nginx with updated config
7. Smoke test: POST /api/v1/estimate/generate with test data
8. Enable traffic routing
```

### 1.4 Rollback Plan

- Blue-green deployment: keep previous version running
- Rollback trigger: error rate > 10% in first 15 minutes
- Rollback: switch nginx upstream back to previous version
- Elasticsearch index is immutable (versioned: `gesn_fer_v1`, `gesn_fer_v2`)
- DB migrations: include `downgrade` for every `upgrade`

---

## 2. ГЭСН/ФЕР Data Import

### 2.1 Data Sources

| Source | Format | Records | Update Frequency |
|--------|--------|---------|-----------------|
| ГЭСН (47 сборников) | XML/CSV from Минстрой ФСНБ | ~80,000 | Annual (new editions) |
| ФЕР | XML/CSV from Минстрой ФСНБ | ~30,000 | Annual |
| ТЕР (Moscow, SPb, Krasnodar) | CSV | ~15,000 | Annual |
| Минстрой indices | PDF/CSV from minstroyrf.gov.ru | ~500 per quarter | Quarterly |
| Market benchmarks | Scraped/manual from industry sources | ~5,000 | Monthly |

### 2.2 Import Pipeline

```
1. Download raw data (ГЭСН XML from ФСНБ-2024)
2. Parse XML → normalize to unified JSON schema
3. Generate embeddings (bge-m3) for each record description
4. Bulk index into Elasticsearch (gesn_fer_v{N} alias)
5. Validate: count docs, spot-check 20 random codes
6. Switch alias gesn_fer → gesn_fer_v{N}
7. Delete old index after 7 days
```

**Import script:** `scripts/import_gesn.py`

```python
# Idempotent: re-running creates a new versioned index
python scripts/import_gesn.py \
    --source data/gesn_2024.xml \
    --es-url $ELASTICSEARCH_URL \
    --embedding-model bge-m3 \
    --batch-size 500
```

### 2.3 Минстрой Index Import

```python
# Quarterly manual import (PDF parsing or CSV)
python scripts/import_minstroy_indices.py \
    --source data/minstroy_indices_2026_q2.csv \
    --db-url $DATABASE_URL
```

CSV format:
```csv
region,work_category,quarter,coefficient,published_date
moscow,finishing,2026-Q2,8.34,2026-04-15
moscow,electrical,2026-Q2,7.92,2026-04-15
spb,finishing,2026-Q2,7.89,2026-04-15
```

### 2.4 Data Validation

| Check | Threshold |
|-------|-----------|
| Total ГЭСН records | >= 75,000 (alert if significantly fewer) |
| Records with embeddings | 100% (fail import if any missing) |
| Минстрой index coverage | All regions × categories × current quarter |
| Duplicate codes | 0 (fail on duplicates) |
| base_rate > 0 | 100% |
| Valid units (from whitelist) | 100% |

---

## 3. Monitoring & Observability

### 3.1 Dashboards (Grafana)

**AI Estimator Dashboard:**
- Estimates generated (count/day, by type: text/drawing)
- Generation time P50/P95/P99
- ГЭСН match rate (% lines with score >= 0.7)
- AI provider latency and error rate
- Usage quota: estimates per tenant (histogram)
- Export count by format (PDF/Excel)

### 3.2 Structured Logging

```json
{
  "timestamp": "2026-05-27T10:00:00Z",
  "level": "INFO",
  "service": "ai-service",
  "correlation_id": "uuid",
  "event": "estimate_generated",
  "tenant_id": 42,
  "input_type": "text",
  "lines_count": 15,
  "duration_sec": 28.5,
  "gesn_match_avg_score": 0.85,
  "grand_total": "1500000.00"
}
```

PII masking: never log user descriptions, file content, or personal data.

### 3.3 Alerts

| Alert | Condition | Channel |
|-------|-----------|---------|
| AI Service Down | Health check fails 3x consecutive | Telegram + email |
| High Error Rate | > 5% errors in 15 min | Telegram |
| Slow Generation | P95 > 90s for 10 min | Telegram |
| ES Cluster Red | Cluster health = red | Telegram + email |
| Quota Bypass | Any tenant usage > limit + 1 | Email (non-urgent) |
| ГЭСН Index Stale | Index not updated in > 400 days | Email |
| Минстрой Index Missing | Current quarter not imported | Email |

---

## 4. Operational Runbooks

### 4.1 ГЭСН Index Update (Annual)

1. Download new ФСНБ edition from Минстрой
2. Run `import_gesn.py` to create new versioned index
3. Validate record count and spot-check
4. Switch alias, monitor error rate for 1 hour
5. Delete old index after 7 days

### 4.2 Минстрой Index Update (Quarterly)

1. Download quarterly indices from minstroyrf.gov.ru
2. Parse into CSV format
3. Run `import_minstroy_indices.py`
4. Verify coverage for all supported regions
5. Clear Redis cache (`minstroy_index:*`)

### 4.3 AI Provider Outage

1. Alert fires: AI provider unavailable
2. Check Cloud.ru status page
3. If extended outage (>30 min): show maintenance banner to users
4. Queued tasks will retry automatically (max 3x)
5. After recovery: check for stuck tasks, requeue if needed

---

## 5. Launch Checklist

- [ ] All env vars configured in production
- [ ] ГЭСН/ФЕР data imported (>= 75K records)
- [ ] Минстрой indices imported for current quarter
- [ ] Market benchmarks loaded (>= 1K entries)
- [ ] S3 buckets created with correct ACLs
- [ ] Nginx rate limiting configured (10 req/min AI endpoints)
- [ ] Health checks responding on all services
- [ ] Smoke test: generate estimate from text (< 60s)
- [ ] Smoke test: generate estimate from drawing (< 90s)
- [ ] Smoke test: export PDF and Excel
- [ ] Usage tracking: verify counter increment
- [ ] Grafana dashboards deployed
- [ ] Alert channels configured (Telegram, email)
- [ ] Rollback plan documented and tested
- [ ] DB backup verified
