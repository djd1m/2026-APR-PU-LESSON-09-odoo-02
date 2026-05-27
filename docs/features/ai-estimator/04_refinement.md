# Refinement: AI-Estimator (F01)

Edge cases, failure modes, testing strategy, and AI accuracy benchmarks.

---

## 1. Edge Cases & Failure Modes

### 1.1 Input Validation

| Case | Handling |
|------|----------|
| Description < 20 characters | Reject with 422: "Описание слишком короткое (мин. 20 символов)" |
| Description > 10,000 characters | Truncate to 10K, warn user |
| Empty area_m2 for text input | Accept (AI infers from description), flag as "area_estimated" |
| area_m2 > 10,000 m² | Accept but warn: "Для крупных объектов точность снижается" |
| area_m2 = 0 or negative | Reject with 422 |
| Non-Russian text | Accept (AI handles), but accuracy may degrade -- add disclaimer |
| Drawing with no recognizable rooms | Return error: "Не удалось распознать помещения. Загрузите более чёткий чертёж" |
| Corrupted PDF | Validate MIME + magic bytes, reject with 422 |
| Multi-page drawing (>10 pages) | Process first 10 pages, warn user |
| Drawing > 50 MB | Reject with 413 |

### 1.2 ГЭСН/ФЕР Lookup Failures

| Case | Handling |
|------|----------|
| No semantic match (KNN score < 0.7) | Fallback to fulltext search |
| No fulltext match either | Mark line as "unresolved", use AI-estimated rate with disclaimer |
| Obsolete ГЭСН code (superseded) | Use `superseded_by` field to follow chain to current code |
| Missing Минстрой index for region/quarter | Use latest available index with warning: "Индекс за Q1 2026 ещё не опубликован, использован Q4 2025" |
| Multiple equally scored matches | Pick the one with more specific description (shorter Levenshtein distance to query) |

### 1.3 AI Provider Failures

| Case | Handling |
|------|----------|
| Cloud.ru 429 (rate limit) | Exponential backoff: 2s, 4s, 8s (max 3 retries) |
| Cloud.ru 500/503 | Retry 2x, then fail task with user notification |
| Cloud.ru timeout (>30s text / >60s drawing) | Retry once with increased timeout (+50%), then fail |
| AI returns invalid JSON | Parse error -> retry with stricter prompt, max 2 retries |
| AI hallucinates ГЭСН codes | Validate every code against ES index -- reject non-existent codes |
| AI returns negative quantities | Clamp to 0, flag for manual review |
| AI returns unreasonable quantities (>1000x area) | Flag as "needs_review", include in estimate with warning |

### 1.4 Huge Estimates

| Case | Handling |
|------|----------|
| > 200 lines | Accept, but warn: SLA does not guarantee < 60s |
| > 500 lines | Split into batches of 100 for ГЭСН lookup (parallel) |
| grand_total > ₽100M | Flag as "large_estimate", require manager confirmation |
| > 50 AI-generated items from single description | Cap at 50, warn: "Описание слишком сложное, разбейте на отдельные сметы" |

### 1.5 Concurrency & Billing

| Case | Handling |
|------|----------|
| Two estimates submitted simultaneously, only 1 quota remaining | First to complete takes the slot; second gets QuotaExceeded |
| Usage counter race condition | Redis INCR (atomic), reconcile with DB monthly |
| ЮKassa webhook arrives before estimate completes | Overage payment credited immediately, estimate unblocked |
| Duplicate ЮKassa webhook | Idempotent: check `idempotency_key` before processing |
| User downgrades plan mid-month | Keep current month's limit until reset |

### 1.6 Export Edge Cases

| Case | Handling |
|------|----------|
| Estimate with 0 lines | Reject export: "Смета пуста" |
| Very long line descriptions (>500 chars) | Truncate in PDF table, full text in appendix |
| Company header with non-ASCII chars | UTF-8 throughout, PDF supports Cyrillic |
| S3 upload failure | Retry 2x, then return 503 |
| Pre-signed URL expired | User re-requests export (generate new URL) |

---

## 2. AI Accuracy & Hallucination Mitigation

### 2.1 Validation Pipeline

Every AI output goes through post-processing validation:

```
AI Response
  → JSON schema validation (Pydantic)
  → ГЭСН code existence check (ES lookup)
  → Quantity sanity check (0 < qty < area_m2 * 100)
  → Unit consistency check (work_type → expected unit mapping)
  → Duplicate detection (same ГЭСН code in multiple lines)
```

### 2.2 Confidence Scoring

Each estimate line gets a composite confidence score:

| Factor | Weight | Source |
|--------|--------|--------|
| ГЭСН match score | 40% | Elasticsearch relevance |
| AI classification confidence | 30% | LLM self-reported |
| Quantity reasonableness | 20% | Heuristic (qty vs area) |
| Unit match | 10% | work_type → unit mapping |

Lines with confidence < 0.5 marked as "low_confidence" in UI (yellow highlight).

### 2.3 Known AI Failure Modes

| Failure | Frequency | Mitigation |
|---------|-----------|------------|
| Invents non-existent ГЭСН codes | Common | Validate against ES index |
| Confuses м² and м.п. (linear vs area) | Occasional | Unit mapping table per work_type |
| Doubles quantities for symmetric rooms | Rare | Warn if quantity > 2x area |
| Mixes ГЭСН and ФЕР codes in output | Common | Normalize: strip prefix, look up both bases |
| Ignores regional specifics | Occasional | Force region in prompt, use regional ТЕР when available |

---

## 3. Testing Strategy

### 3.1 Unit Tests

| Module | Test Cases | Notes |
|--------|-----------|-------|
| `estimator.py` | Decimal arithmetic, line calculation, total with НДС | Assert exact Decimal values, never approximate |
| `gesn_search.py` | KNN query construction, fulltext fallback, score filtering | Mock ES client |
| `optimizer.py` | Overpriced detection (exactly at 10%, above, below), alternative lookup | Decimal comparison edge cases |
| `usage_tracker.py` | Quota check, increment, reset, overage | Race condition with concurrent requests |
| `drawing_parser.py` | PDF to images, MIME validation, multi-page handling | Mock vision AI |
| `exporter.py` | PDF generation, Excel formulas, Cyrillic support | Verify money formatting |

### 3.2 Integration Tests

| Scenario | What's tested |
|----------|---------------|
| Full text pipeline | Input → AI mock → ES → DB → response (end-to-end with test DB) |
| Drawing pipeline | File upload → S3 mock → Vision AI mock → ES → DB |
| Export flow | DB → PDF/XLSX generation → S3 upload → pre-signed URL |
| Usage quota enforcement | Generate N estimates, verify N+1 is blocked |
| Celery task retry | Simulate AI provider failure, verify retry + eventual success/failure |

### 3.3 AI Accuracy Benchmarks

**Test dataset:** 50 manually prepared estimates by professional сметчик.

| Metric | Target | Measurement |
|--------|--------|-------------|
| ГЭСН code accuracy | >= 80% correct codes | Exact match against reference estimate |
| Quantity accuracy | >= 85% within 15% of reference | Relative error per line |
| Total cost accuracy | >= 80% within 20% of reference | Relative error on grand_total |
| Area recognition (drawings) | >= 85% within 10% of actual | Measured area vs reference |
| False positive rate (optimization) | < 15% | Items flagged as overpriced that aren't |

**Benchmark execution:** Run weekly in CI against frozen AI responses (recorded fixtures). Live AI accuracy measured monthly against new professional estimates.

### 3.4 Performance Tests

| Test | Target | Tool |
|------|--------|------|
| Text estimate (100 m²) | < 30s P95 | locust |
| Text estimate (200 m²) | < 60s P95 | locust |
| Drawing estimate (1 page) | < 90s P95 | locust |
| ГЭСН search (100K docs) | < 500ms P95 | pytest-benchmark |
| 10 concurrent estimates | All complete < 120s | locust |
| Export PDF (200 lines) | < 10s | pytest-benchmark |

### 3.5 Security Tests

| Test | Expected |
|------|----------|
| AI prompt injection in description | Sanitized, no code execution |
| File upload with executable disguised as PDF | Rejected (MIME + magic bytes) |
| Cross-tenant estimate access | 403 Forbidden |
| Rate limit (>10 AI requests/min) | 429 Too Many Requests |
| Missing AI_API_KEY env var | Service refuses to start |
| Webhook without HMAC signature | 401 Unauthorized |

---

## 4. Monitoring & Alerts

| Metric | Alert Threshold | Action |
|--------|----------------|--------|
| AI response time P95 | > 45s (text), > 75s (drawing) | Scale Celery workers |
| AI error rate | > 5% in 15min window | Check Cloud.ru status, consider maintenance page |
| ГЭСН match rate | < 70% (lines with no match) | Review search configuration, re-index |
| Estimate generation failures | > 3 consecutive | Page on-call |
| Usage quota bypass | Any tenant exceeds limit | Investigate, fix counter |
| Elasticsearch cluster health | Yellow or Red | Investigate shard allocation |
