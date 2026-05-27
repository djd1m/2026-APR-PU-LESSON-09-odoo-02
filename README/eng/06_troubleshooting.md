# Troubleshooting

Common issues and their solutions for StroyUprav.

---

## Table of Contents

1. [Docker and Startup Issues](#1-docker-and-startup-issues)
2. [Database Issues](#2-database-issues)
3. [AI Estimator Issues](#3-ai-estimator-issues)
4. [Elasticsearch Issues](#4-elasticsearch-issues)
5. [MinIO / File Storage Issues](#5-minio--file-storage-issues)
6. [Redis / Celery Issues](#6-redis--celery-issues)
7. [SSL / Nginx Issues](#7-ssl--nginx-issues)
8. [Performance Issues](#8-performance-issues)
9. [Payment / YuKassa Issues](#9-payment--yukassa-issues)

---

## 1. Docker and Startup Issues

### Application crashes on startup with "missing environment variable"

**Cause:** One or more required environment variables are not set. The application intentionally crashes if any required variable is missing (no fallback defaults for secrets).

**Fix:**
```bash
# Check which variables are missing -- read the error message
docker compose logs odoo --tail 20

# Verify .env file has all required values
cat .env | grep -v '^#' | grep -v '^$'

# Compare with the template
diff <(grep -oP '^\w+' .env.example) <(grep -oP '^\w+' .env)
```

### `docker compose up` fails with port conflict

**Cause:** Port 80 or 443 is already in use.

**Fix:**
```bash
# Find what is using the port
sudo lsof -i :80
sudo lsof -i :443

# Stop the conflicting service (e.g., Apache)
sudo systemctl stop apache2
```

### Container keeps restarting (restart loop)

**Cause:** Usually a configuration error or dependency not ready.

**Fix:**
```bash
# Check the failing container's logs
docker compose logs <service-name> --tail 100

# Common causes:
# - postgres: wrong DB_PASSWORD
# - odoo: DATABASE_URL incorrect
# - fastapi-ai: CLOUDRU_API_KEY invalid
# - elasticsearch: not enough memory (needs 2 GB)
```

### Out of disk space

**Cause:** Docker images, volumes, or logs consuming too much space.

**Fix:**
```bash
# Check disk usage
df -h

# Clean unused Docker resources
docker system prune -a --volumes

# Check log sizes
du -sh /var/lib/docker/containers/*/

# Truncate large log files
truncate -s 0 /var/lib/docker/containers/<container-id>/<container-id>-json.log
```

---

## 2. Database Issues

### Cannot connect to PostgreSQL

**Cause:** Database container not healthy or wrong credentials.

**Fix:**
```bash
# Check postgres health
docker compose ps postgres

# Test connection from inside the container
docker compose exec postgres psql -U stroiuprav -d stroiuprav -c "SELECT 1;"

# Check if DATABASE_URL matches postgres environment
# DATABASE_URL should be: postgresql://stroiuprav:<DB_PASSWORD>@postgres:5432/stroiuprav
```

### Database migrations fail

**Cause:** Schema mismatch after an update.

**Fix:**
```bash
# Run Odoo module update
docker compose exec odoo odoo -u stroyuprav_project -d stroiuprav --stop-after-init

# Update all custom modules
docker compose exec odoo odoo -u all -d stroiuprav --stop-after-init
```

### Database is slow

**Cause:** Missing indices or untuned PostgreSQL configuration.

**Fix:**
```bash
# Check slow queries
docker compose exec postgres psql -U stroiuprav -d stroiuprav \
  -c "SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Refresh materialized views (budget aggregations)
docker compose exec postgres psql -U stroiuprav -d stroiuprav \
  -c "REFRESH MATERIALIZED VIEW CONCURRENTLY stroyuprav_budget_summary;"
```

---

## 3. AI Estimator Issues

### Estimate generation times out (> 60 seconds)

**Cause:** Cloud.ru API is slow or the model is overloaded.

**Fix:**
1. Check Cloud.ru service status
2. Try switching to a faster model:
   ```bash
   # In .env
   CLOUDRU_MODEL=deepseek-v3  # Faster than qwen3-72b
   ```
3. If Cloud.ru is down, the system should auto-fallback to OpenAI. Verify `OPENAI_API_KEY` is set.

### AI estimate accuracy is low (< 80%)

**Cause:** Incorrect Minstroy price indices or poor GESN/FER search results.

**Fix:**
1. Verify Elasticsearch has the latest GESN/FER data:
   ```bash
   curl http://localhost:9200/gesn_rates/_count
   curl http://localhost:9200/fer_rates/_count
   ```
2. Update Minstroy quarterly indices:
   ```bash
   docker compose exec fastapi-ai python -m scripts.update_indices
   ```
3. Check the region code is correct in the estimate request.

### "AI provider unavailable" error

**Cause:** Both Cloud.ru and OpenAI are unreachable.

**Fix:**
```bash
# Test Cloud.ru connectivity
docker compose exec fastapi-ai curl -s https://api.cloud.ru/v1/models \
  -H "Authorization: Bearer $CLOUDRU_API_KEY"

# Test OpenAI connectivity
docker compose exec fastapi-ai curl -s https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Check DNS resolution inside container
docker compose exec fastapi-ai nslookup api.cloud.ru
```

---

## 4. Elasticsearch Issues

### Elasticsearch fails to start

**Cause:** Insufficient memory. Elasticsearch 8 requires at least 2 GB RAM for the JVM heap.

**Fix:**
```bash
# Check available memory
free -h

# Reduce ES memory if needed (not recommended for production)
# In docker-compose.yml, change:
# ES_JAVA_OPTS=-Xms512m -Xmx512m

# Or increase VPS RAM
```

### Elasticsearch health is "red"

**Cause:** Unassigned shards, usually after a disk space issue or unclean shutdown.

**Fix:**
```bash
# Check cluster health
curl http://localhost:9200/_cluster/health?pretty

# Check unassigned shards
curl http://localhost:9200/_cat/shards?v&h=index,shard,prirep,state,unassigned.reason

# Re-index if needed
docker compose exec fastapi-ai python -m scripts.load_gesn_fer
```

### Search returns no results

**Cause:** GESN/FER data not loaded into Elasticsearch.

**Fix:**
```bash
# Check if indices exist
curl http://localhost:9200/_cat/indices?v

# Load data
docker compose exec fastapi-ai python -m scripts.load_gesn_fer
```

---

## 5. MinIO / File Storage Issues

### Photos fail to upload

**Cause:** MinIO not running or bucket not created.

**Fix:**
```bash
# Check MinIO health
docker compose ps minio

# Create the bucket manually if it does not exist
docker compose exec minio mc alias set local http://localhost:9000 minioadmin $MINIO_ROOT_PASSWORD
docker compose exec minio mc mb local/stroiuprav --ignore-existing
```

### Cannot access MinIO console

**Cause:** Port 9001 not exposed.

**Fix:** MinIO console is intentionally internal-only. Access it via SSH tunnel:
```bash
ssh -L 9001:localhost:9001 user@your-vps-ip
# Then open http://localhost:9001 in your browser
```

---

## 6. Redis / Celery Issues

### Celery tasks stuck in queue

**Cause:** Celery worker crashed or is not running.

**Fix:**
```bash
# Check worker status
docker compose ps celery-worker

# Restart the worker
docker compose restart celery-worker

# Check the queue length
docker compose exec redis redis-cli LLEN celery
```

### Redis out of memory

**Cause:** Cache exceeds the 512 MB limit.

**Fix:** Redis is configured with `allkeys-lru` eviction policy, so it should evict old keys automatically. If issues persist:
```bash
# Check memory usage
docker compose exec redis redis-cli INFO memory

# Flush non-essential cache
docker compose exec redis redis-cli FLUSHDB
```

---

## 7. SSL / Nginx Issues

### SSL certificate expired

**Fix:**
```bash
# Renew certificate
certbot renew

# Restart nginx
docker compose restart nginx
```

### "502 Bad Gateway" error

**Cause:** Backend service (Odoo or FastAPI) is down.

**Fix:**
```bash
# Check which backend is down
docker compose ps

# Restart the failing service
docker compose restart odoo    # or fastapi-ai
```

### Mixed content warnings

**Cause:** Some assets loaded over HTTP instead of HTTPS.

**Fix:** Ensure `X-Forwarded-Proto` header is set in Nginx config and the application reads it.

---

## 8. Performance Issues

### Dashboard loads slowly (> 2 seconds)

**Cause:** Materialized views stale or Redis cache expired.

**Fix:**
```bash
# Refresh materialized views
docker compose exec postgres psql -U stroiuprav -d stroiuprav \
  -c "REFRESH MATERIALIZED VIEW CONCURRENTLY stroyuprav_budget_summary;"

# Check Redis cache hit rate
docker compose exec redis redis-cli INFO stats | grep keyspace
```

### High memory usage

**Fix:**
```bash
# Check per-container memory
docker stats --no-stream

# Identify the largest consumer and adjust limits in docker-compose.yml
# Common culprits: Elasticsearch (increase ES_JAVA_OPTS), Odoo (reduce worker count)
```

---

## 9. Payment / YuKassa Issues

### Webhook delivery failures

**Cause:** HMAC verification failing or webhook URL unreachable.

**Fix:**
1. Verify `YUKASSA_WEBHOOK_SECRET` matches the value in YuKassa dashboard
2. Ensure the webhook URL is accessible from the internet:
   ```bash
   curl -X POST https://stroyuprav.example.com/api/webhooks/yukassa \
     -H "Content-Type: application/json" \
     -d '{}'
   # Should return 401 (unauthorized), not 404 or connection refused
   ```
3. Check for clock skew (replay protection uses a 5-minute window):
   ```bash
   date
   # Sync time if needed: timedatectl set-ntp on
   ```

### Subscriptions not activating after payment

**Cause:** Webhook not received or processed.

**Fix:**
```bash
# Check Celery worker logs for webhook processing
docker compose logs celery-worker --tail 50 | grep yukassa

# Check the payment status in the database
docker compose exec postgres psql -U stroiuprav -d stroiuprav \
  -c "SELECT * FROM stroyuprav_payment ORDER BY created_at DESC LIMIT 5;"
```

---

## Getting Help

If none of the above solutions work:

1. Collect diagnostic information:
   ```bash
   docker compose ps > diag.txt
   docker compose logs --tail 100 >> diag.txt
   docker stats --no-stream >> diag.txt
   ```
2. Check the project's issue tracker
3. Contact the development team with the diagnostic file
