# Refinement: СтройУправ

## 1. Edge Cases by Module

### 1.1 AI-сметчик (F01)

| Edge Case | Scenario | Expected Behavior | Priority |
|-----------|----------|-------------------|----------|
| Invalid input | Пустая строка, бессмысленный текст, не-строительная тематика | Валидация на уровне API: return 422 с human-readable ошибкой на русском. AI-fallback: "Не удалось распознать виды работ. Уточните описание." | P0 |
| Unsupported work types | Работы, отсутствующие в базе ГЭСН/ФЕР (спец. промышленные, военные) | Пометить позицию как `unresolved`, предложить ручной ввод расценки. Не блокировать генерацию остальной сметы. | P0 |
| ГЭСН code not found | Код существует в справочнике, но удалён/заменён в новой редакции | Fallback-цепочка: ГЭСН -> ФЕР -> ТЕР -> manual. Логировать miss-rate для мониторинга актуальности базы. | P0 |
| Very large estimate (1000+ items) | Крупный объект: многоквартирный дом, торговый центр | Streaming generation: отдавать результат блоками по 50 позиций. Progress bar на фронте. Timeout увеличить до 300 сек. Memory guard: если prompt > 128K tokens, разбить на sub-estimates по разделам. | P1 |
| Duplicate positions | AI генерирует одну и ту же расценку дважды с разными формулировками | Post-processing deduplication по коду ГЭСН + единице измерения. Объединить объёмы, показать warning пользователю. | P1 |
| Чертёж низкого качества | Фото чертежа с плохим освещением, низким разрешением, рукописные пометки | Confidence score < 0.6 -> предупредить пользователя, предложить повторную загрузку. Никогда не генерировать смету "молча" с низкой confidence. | P0 |
| Concurrent estimate generation | 50+ пользователей одновременно запрашивают AI-сметы | Queue (Redis + Celery) с приоритетами по тарифу. Free tier: max 1 concurrent, очередь до 5 мин. Paid: до 3 concurrent. | P0 |
| Устаревшие индексы Минстроя | Квартальные индексы не обновлены вовремя | Показывать дату актуальности индексов в шапке сметы. Warning если индексы старше 4 месяцев. Админ-панель для ручного обновления. | P1 |

### 1.2 Dashboard объектов (F02)

| Edge Case | Scenario | Expected Behavior | Priority |
|-----------|----------|-------------------|----------|
| 50+ concurrent projects | Руководитель крупной компании с 50-100 активными объектами | Pagination: 20 объектов/страница. Virtual scrolling. API: `?page=1&per_page=20&sort=updated_at`. Summary-агрегация через materialized view, обновляемый каждые 5 мин. | P0 |
| Stale data | Прораб обновил прогресс, руководитель видит старые данные | WebSocket для real-time updates критичных полей (прогресс, бюджет). Fallback: polling каждые 30 сек. Last-updated timestamp на каждой карточке. | P1 |
| Timezone issues | Бригады в разных часовых поясах (Москва, Новосибирск, Владивосток) | Хранить всё в UTC. Отображать в timezone пользователя (из профиля, default: Europe/Moscow). Дедлайны задач — в timezone объекта, не пользователя. | P0 |
| Zero projects | Новый пользователь, ещё не создал ни одного объекта | Empty state с CTA: "Создайте первый объект" + демо-объект для ознакомления (read-only). | P1 |
| Deleted project with active tasks | Попытка удалить объект, по которому есть незакрытые задачи | Soft delete. Предупреждение: "На объекте N незакрытых задач". Требовать подтверждение. Архивированные объекты доступны 90 дней. | P0 |

### 1.3 Управление задачами (F03)

| Edge Case | Scenario | Expected Behavior | Priority |
|-----------|----------|-------------------|----------|
| Circular dependencies | Задача A зависит от B, B зависит от C, C зависит от A | Валидация при создании/обновлении зависимости: topological sort (Kahn's algorithm). Если цикл обнаружен — reject с визуализацией цепочки. | P0 |
| Concurrent updates | Два прораба одновременно меняют статус одной задачи | Optimistic locking: `version` field на каждой задаче. При конфликте: показать diff, предложить merge или force-update. HTTP 409 Conflict. | P0 |
| Offline conflict resolution | Прораб обновил задачу offline, другой — online. Sync при reconnect. | Last-write-wins для простых полей (статус, прогресс). Append-only для комментариев и фото. Конфликтующие обновления — показать обе версии пользователю. Offline queue в IndexedDB. | P1 |
| Задача без исполнителя | Бригада уволена/удалена, задачи остались привязаны | Не каскадно удалять задачи. Пометить как `unassigned`. Уведомить руководителя. | P0 |
| Массовое обновление | Перенос 100+ задач из-за изменения сроков проекта | Bulk update API endpoint. Транзакция: все-или-ничего. Progress indicator. Timeout: 30 сек. | P1 |
| Глубокая вложенность подзадач | 10+ уровней вложенности подзадач | Ограничить до 5 уровней. При попытке создать 6-й уровень — предложить реструктуризацию. | P1 |

### 1.4 Фотофиксация (F04)

| Edge Case | Scenario | Expected Behavior | Priority |
|-----------|----------|-------------------|----------|
| Large files (>20MB) | DSLR-фотографии, видео с дрона | Client-side resize: max 4096x4096, quality 85%, JPEG. Оригинал сохранять опционально (paid plans). Max upload: 50MB. > 50MB — reject. | P0 |
| No GPS signal | Подвал, подземная парковка, бункер | Fallback: координаты объекта (из карточки проекта). Warning: "Геотег определён по адресу объекта, не по GPS". Разрешить ручной выбор на карте. | P0 |
| Batch uploads | 50+ фото за раз (фотофиксация за весь день) | Chunked parallel upload: 5 concurrent. Progress bar per-file + overall. Resume на обрыве. Pre-signed URLs для direct S3/MinIO upload. | P1 |
| Fake geotag | Подмена GPS-координат (фрод) | Cross-check: расстояние до объекта > 1 км -> warning (не блокировать). Логировать для аудита. EXIF-timestamp vs server-timestamp delta > 24h -> flag. | P1 |
| Corrupted file | Битый JPEG, обрезанный upload | Server-side validation: проверка magic bytes, попытка decode. Если не удаётся — reject с "Файл повреждён, загрузите повторно". | P0 |
| Storage quota | Бесплатный план, 1GB лимит исчерпан | Показать usage bar. При 80% — warning. При 100% — предложить upgrade. Не удалять существующие фото. | P0 |

### 1.5 Бюджет real-time (F05)

| Edge Case | Scenario | Expected Behavior | Priority |
|-----------|----------|-------------------|----------|
| Currency rounding | Копейки при расчёте смет (0.01 руб разница на 1000 позиций = 10 руб) | `Decimal(12, 2)` everywhere (НЕ float). Rounding: HALF_UP (банковское округление). Итого: сумма позиций, а не пересчёт. Unit tests на копейки. | P0 |
| Retroactive changes | Изменение расценки задним числом в уже принятом КС-2 | Версионирование смет. Изменение после "принятия" — создаёт новую версию. Diff-view: было/стало. Audit log. | P0 |
| Index recalculation | Обновление индексов Минстроя на квартал — пересчёт всех активных смет | Background job (Celery). Batch recalculation. Уведомить пользователя: "Индексы обновлены, N смет пересчитано. Проверьте изменения." Показать delta. | P1 |
| Negative budget | Факт > плана, бюджет "в минусе" | Допустимо. Отображать красным. AI-alert: "Перерасход N% по объекту X. Рекомендуем: ...". Не блокировать работу. | P0 |
| Multi-currency | Закупка импортных материалов (EUR, CNY) | MVP: только RUB. Конвертация на стороне пользователя. P1: курс ЦБ РФ auto-fetch. | P2 |
| НДС toggle | Объект с НДС 20%, часть работ без НДС | Per-position НДС flag. Итого с НДС и без НДС. Гибкая ставка: 0%, 10%, 20%. | P0 |

---

## 2. Error Handling Strategy

### 2.1 API Layer (Odoo/FastAPI Controllers)

```
Layer: HTTP Controllers
Pattern: Structured error responses + global exception handler

Response format:
{
  "error": {
    "code": "ESTIMATE_GENERATION_FAILED",
    "message": "Не удалось сгенерировать смету. Попробуйте позже.",
    "details": { "retry_after": 30 },   // optional, dev-mode only
    "request_id": "uuid-v4"
  }
}
```

| HTTP Code | When | User Message |
|-----------|------|-------------|
| 400 | Validation failed (пустое описание, неверный формат) | Конкретная ошибка: "Описание работ не может быть пустым" |
| 401 | JWT expired / missing | "Сессия истекла. Войдите заново" + auto-redirect to login |
| 403 | Нет доступа к объекту другой компании | "Нет доступа к данному объекту" (не раскрывать существование) |
| 404 | Ресурс не найден | "Объект не найден" (generic, без ID в сообщении) |
| 409 | Optimistic lock conflict | "Данные были изменены другим пользователем. Обновите страницу" |
| 422 | Business rule violation | Конкретное описание нарушения |
| 429 | Rate limit exceeded | "Превышен лимит запросов. Подождите N секунд" |
| 500 | Unhandled exception | "Внутренняя ошибка. Мы уже разбираемся. ID: {request_id}" |
| 503 | AI provider unavailable | "AI-сервис временно недоступен. Попробуйте через 5 минут" |

**Rules:**
- Все сообщения на русском языке
- Никогда не раскрывать stack trace пользователю (только в dev mode)
- `request_id` в каждом ответе для корреляции с логами
- Structured logging (JSON) для всех 4xx/5xx

### 2.2 Service Layer (Business Logic)

```python
# Custom exception hierarchy
class СтройУправError(Exception):
    """Base exception for all business errors."""
    code: str
    http_status: int = 500

class EstimateError(СтройУправError):
    http_status = 422

class EstimateGenerationTimeout(EstimateError):
    code = "ESTIMATE_TIMEOUT"

class GESNCodeNotFound(EstimateError):
    code = "GESN_NOT_FOUND"

class BudgetOverflowError(СтройУправError):
    code = "BUDGET_OVERFLOW"
    http_status = 422

class ConcurrentUpdateError(СтройУправError):
    code = "CONCURRENT_UPDATE"
    http_status = 409
```

**Retry policy for service-to-service calls:**
- Database transient errors: 3 retries, exponential backoff (100ms, 500ms, 2s)
- External API (ЮKassa, AI): 3 retries, exponential backoff (1s, 5s, 15s)
- Never retry on 4xx (client errors)

### 2.3 AI Provider Layer

```
Provider chain (LiteLLM):
  1. Cloud.ru Foundation Models (primary)
  2. Qwen3 via Cloud.ru (fallback #1)
  3. OpenAI GPT-4o (fallback #2, for non-PII requests only)

Failure handling:
  - Timeout: 120 sec per request, 300 sec for large estimates
  - Rate limit: queue with priority (paid > free)
  - Malformed response: retry once with stricter prompt
  - All providers down: return 503, queue request for async processing
  - Content filter triggered: log, return generic "try rephrasing" message
```

**AI response validation pipeline:**
```
AI raw response
  -> JSON schema validation (ГЭСН structure)
  -> ГЭСН code existence check (local DB)
  -> Price sanity check (< 10x median for category)
  -> Volume sanity check (area > 0, quantity > 0)
  -> Return validated estimate OR list of issues
```

### 2.4 Database Layer

| Error Type | Handling |
|-----------|----------|
| Unique constraint violation | Map to 409 or 422 with human message: "Объект с таким названием уже существует" |
| Foreign key violation | Map to 422: "Связанная запись не найдена" (вероятно, удалена параллельно) |
| Deadlock | Auto-retry (max 3), log warning. If persistent — alert. |
| Connection pool exhausted | 503 + circuit breaker. Alert в Sentry. Log queue depth. |
| Migration failure | Halt deployment. Rollback to previous migration. Alert. |

**Circuit breaker pattern** (для AI provider и внешних сервисов):
- Open after 5 consecutive failures in 60 sec
- Half-open: try 1 request every 30 sec
- Close after 3 consecutive successes

---

## 3. Testing Strategy

### 3.1 Unit Tests (pytest)

**Coverage target:** 80% for business logic, 90% for estimator calculations.

**Estimator calculations (critical):**
```python
# tests/unit/test_estimate_calculator.py

class TestEstimateCalculator:
    """Test ГЭСН/ФЕР расчёт с точностью до копейки."""

    def test_basic_calculation_with_index(self):
        """Расценка * объём * индекс Минстроя = итого."""
        # ГЭСН 11-01-001-01: Кладка стен из кирпича
        # Единица: 1 м3, базовая цена: 1 234.56 руб
        # Индекс: 8.42 (Q1 2026)
        # Объём: 15.5 м3
        # Ожидаемый итого: 1234.56 * 8.42 * 15.5 = 161_057.60 руб

    def test_rounding_consistency(self):
        """Сумма позиций == итого (не пересчитывать)."""

    def test_nds_calculation(self):
        """НДС 20% применяется к итогу, не к каждой позиции."""

    def test_empty_estimate(self):
        """Пустой список работ -> пустая смета, не ошибка."""

    def test_negative_volume_rejected(self):
        """Отрицательный объём -> ValidationError."""

    def test_gesn_code_format_validation(self):
        """Формат XX-XX-XXX-XX, иначе ValueError."""

    def test_index_expiration_warning(self):
        """Индекс старше 4 месяцев -> warning в результате."""

    def test_1000_items_performance(self):
        """1000 позиций рассчитываются < 2 сек."""
```

**Business logic:**
```python
# tests/unit/test_task_dependencies.py
class TestTaskDependencies:
    def test_circular_dependency_detection(self): ...
    def test_deep_dependency_chain(self): ...
    def test_bulk_status_update_cascade(self): ...

# tests/unit/test_budget_tracking.py
class TestBudgetTracking:
    def test_overbudget_alert_threshold(self): ...
    def test_retroactive_price_change_creates_version(self): ...
    def test_decimal_precision_no_float(self): ...
```

**Run configuration:**
```bash
# Fast feedback loop (< 30 sec)
pytest tests/unit/ -x --timeout=10 -q

# With coverage
pytest tests/unit/ --cov=stroiuprav --cov-report=html --cov-fail-under=80
```

### 3.2 Integration Tests

**Database integration:**
```python
# tests/integration/test_db_integration.py
# Use: testcontainers-python с PostgreSQL
# Каждый тест — в транзакции, rollback после теста

class TestEstimateDBIntegration:
    def test_estimate_create_and_retrieve(self): ...
    def test_concurrent_budget_update(self): ...
    def test_soft_delete_cascade(self): ...
    def test_materialized_view_refresh(self): ...
```

**AI provider integration:**
```python
# tests/integration/test_ai_provider.py
# Mock: vcrpy для записи/воспроизведения AI-ответов
# Real calls: только в CI nightly, не на каждый PR

class TestAIProviderIntegration:
    @vcr.use_cassette('fixtures/ai_estimate_basic.yaml')
    def test_basic_estimate_generation(self): ...

    @vcr.use_cassette('fixtures/ai_estimate_malformed.yaml')
    def test_malformed_ai_response_handling(self): ...

    def test_provider_failover_chain(self): ...
    def test_rate_limit_queueing(self): ...
```

**ЮKassa webhook integration:**
```python
# tests/integration/test_yukassa_webhook.py
class TestYuKassaWebhook:
    def test_payment_success_activates_subscription(self): ...
    def test_payment_failed_keeps_trial(self): ...
    def test_duplicate_webhook_idempotency(self): ...
    def test_invalid_signature_rejected(self): ...
    def test_refund_webhook_downgrades_plan(self): ...
```

**Run configuration:**
```bash
# Requires Docker (testcontainers)
pytest tests/integration/ --timeout=60 -v
```

### 3.3 E2E Tests (Playwright)

**Critical user flows:**

```python
# tests/e2e/test_critical_flows.py

class TestOnboardingFlow:
    """Quiz -> первый объект за < 3 минуты."""
    def test_onboarding_4_questions_to_dashboard(self): ...
    def test_skip_onboarding_direct_to_dashboard(self): ...

class TestEstimateFlow:
    """Описание -> смета -> PDF export."""
    def test_text_to_estimate_full_flow(self): ...
    def test_estimate_edit_and_recalculate(self): ...
    def test_estimate_pdf_export_download(self): ...

class TestProjectManagementFlow:
    """Создание объекта -> задачи -> фото -> прогресс."""
    def test_create_project_add_tasks_upload_photo(self): ...
    def test_task_status_updates_project_progress(self): ...

class TestBillingFlow:
    """Trial -> выбор плана -> оплата."""
    def test_trial_to_paid_upgrade(self): ...
    def test_plan_downgrade_with_confirmation(self): ...

class TestMobileFlow:
    """PWA на мобильном разрешении."""
    def test_mobile_photo_upload_flow(self): ...
    def test_mobile_task_update_flow(self): ...
```

**Run configuration:**
```bash
# Headed mode для отладки
npx playwright test --headed --project=chromium

# CI: headless, 3 workers, all browsers
npx playwright test --workers=3

# Mobile viewports
npx playwright test --project=mobile-chrome --project=mobile-safari
```

### 3.4 AI Accuracy Tests

**Benchmark suite:**
```python
# tests/ai_accuracy/test_estimate_precision.py

# Датасет: 50 ручных смет от профессиональных сметчиков
# Формат: input_description -> expected_items[] с расценками

BENCHMARK_DATASET = load_json("fixtures/manual_estimates_50.json")

class TestEstimatePrecision:
    @pytest.mark.parametrize("case", BENCHMARK_DATASET)
    def test_estimate_vs_manual(self, case):
        """AI-смета vs ручная: отклонение < 15% по итогу."""
        ai_result = generate_estimate(case["input"])
        manual_total = case["expected_total"]
        deviation = abs(ai_result.total - manual_total) / manual_total
        assert deviation < 0.15, f"Deviation {deviation:.1%} exceeds 15%"

    def test_gesn_code_accuracy(self):
        """≥ 85% позиций имеют корректный код ГЭСН."""

    def test_volume_estimation_from_drawing(self):
        """Площади из чертежа: отклонение < 15%."""

    def test_missing_items_rate(self):
        """Пропущено < 10% позиций vs ручная смета."""
```

**Accuracy tracking over time:**
- Nightly CI job: run benchmark on current AI prompt + model
- Store results in `tests/ai_accuracy/results/YYYY-MM-DD.json`
- Grafana dashboard: accuracy trend, P50/P95 deviation
- Alert: accuracy drops below 80% -> Slack notification

---

## 4. Performance Optimization

### 4.1 Database

**Indexes (PostgreSQL):**
```sql
-- High-frequency queries
CREATE INDEX idx_project_company_status ON project(company_id, status)
    WHERE status != 'archived';
CREATE INDEX idx_task_project_status ON task(project_id, status);
CREATE INDEX idx_task_assignee ON task(assignee_id)
    WHERE status IN ('new', 'in_progress');
CREATE INDEX idx_estimate_project ON estimate(project_id, created_at DESC);
CREATE INDEX idx_photo_task ON photo(task_id, created_at DESC);
CREATE INDEX idx_budget_entry_project ON budget_entry(project_id, category);

-- Full-text search (работы в сметах)
CREATE INDEX idx_estimate_item_description ON estimate_item
    USING gin(to_tsvector('russian', description));

-- ГЭСН lookup
CREATE INDEX idx_gesn_code ON gesn_reference(code);
CREATE INDEX idx_gesn_search ON gesn_reference
    USING gin(to_tsvector('russian', name || ' ' || description));
```

**Query optimization:**
- Dashboard: materialized view `mv_project_summary` (project_id, progress, budget_fact, budget_plan, task_count, overdue_count). Refresh every 5 min via pg_cron.
- Budget aggregations: pre-computed в `budget_snapshot` table, обновляемая триггером при INSERT/UPDATE в `budget_entry`.
- Pagination: keyset pagination (cursor-based), не OFFSET.

**Connection pooling:**
- PgBouncer in transaction mode
- Pool size: 20 connections (for 4-core VPS)
- Max client connections: 200
- Statement timeout: 30 sec (queries), 300 sec (migrations)

### 4.2 AI Layer

**Response caching (Redis):**
```python
# Cache key: hash(normalized_description + gesn_version + index_quarter)
# TTL: 24 hours (индексы не меняются чаще)
# Hit rate target: 30-40% (similar projects -> similar estimates)

CACHE_KEY = f"estimate:{hashlib.sha256(normalized_input).hexdigest()}"
cached = redis.get(CACHE_KEY)
if cached:
    return decompress(cached)  # Skip AI call entirely
```

**Batch processing:**
- Large estimates: split into sections (фундамент, стены, кровля, отделка)
- Process sections in parallel (asyncio.gather)
- Merge results, resolve cross-section dependencies
- Net effect: 1000-item estimate 120 sec -> 45 sec

**Async generation:**
```
User request -> immediate 202 Accepted + job_id
  -> Celery worker picks up
  -> WebSocket notification on completion
  -> Client fetches result via GET /estimates/{job_id}
```

**Token optimization:**
- System prompt: cache per-model (Cloud.ru, Qwen3 have different optimal prompts)
- ГЭСН reference: send only relevant category (not full 50K-item database)
- Response format: structured JSON schema -> fewer tokens than free-form

### 4.3 Frontend

**Lazy loading:**
```javascript
// Route-level code splitting
const EstimateModule = lazy(() => import('./modules/Estimate'));
const GanttModule = lazy(() => import('./modules/Gantt'));  // P1, heavy lib

// Image lazy loading
<img loading="lazy" src={thumbnail_url} />

// Infinite scroll for photo gallery (not pagination)
const { data, fetchNextPage } = useInfiniteQuery('photos', fetchPhotos);
```

**Image optimization:**
- Upload: client-side resize to max 2048px (preview), store original in cold storage
- Serve: WebP format via CDN/nginx, responsive srcset (320w, 640w, 1024w, 2048w)
- Thumbnail: 200x200, generated on upload (Celery task)
- Lazy load: Intersection Observer API

**PWA caching strategy:**
```javascript
// Service Worker caching
const CACHE_STRATEGIES = {
  // App shell: cache-first (обновление в фоне)
  '/static/**': 'CacheFirst',
  '/api/projects': 'StaleWhileRevalidate',  // dashboard data
  '/api/tasks/**': 'NetworkFirst',          // fresh data preferred
  '/photos/thumb/**': 'CacheFirst',         // thumbnails immutable
  '/photos/original/**': 'NetworkOnly',     // too large to cache
};

// Offline queue for mutations
const offlineQueue = new IndexedDBQueue('mutations');
// При reconnect: replay queue в порядке timestamp
```

---

## 5. Security Edge Cases

### 5.1 Injection in Estimate Descriptions

**Threat:** Пользователь вводит в описание работ SQL/NoSQL injection или prompt injection для AI.

**Mitigations:**
```python
# 1. SQL injection: parameterized queries only (Odoo ORM / SQLAlchemy)
# NEVER: f"SELECT * FROM gesn WHERE name LIKE '%{user_input}%'"
# ALWAYS: session.query(GESN).filter(GESN.name.ilike(f"%{sanitized}%"))

# 2. AI prompt injection
def sanitize_for_ai(user_input: str) -> str:
    """Remove prompt injection attempts."""
    # Strip control characters
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', user_input)
    # Detect instruction override patterns
    injection_patterns = [
        r'ignore\s+(previous|above)\s+instructions',
        r'system\s*:',
        r'<\|.*?\|>',
        r'```system',
    ]
    for pattern in injection_patterns:
        if re.search(pattern, cleaned, re.IGNORECASE):
            raise SecurityError("PROMPT_INJECTION_DETECTED")
    # Length limit
    if len(cleaned) > 10_000:
        raise ValidationError("Description too long (max 10,000 chars)")
    return cleaned

# 3. AI response validation: never execute AI output as code
# Parse as data only (JSON schema validation)
```

### 5.2 XSS in Project Names

**Threat:** Пользователь создаёт объект с именем `<script>alert('xss')</script>` или `" onload="alert(1)`.

**Mitigations:**
- Server-side: HTML-escape all user-generated content before storage (belt)
- Template layer: auto-escaping enabled by default (Odoo QWeb / Jinja2) (suspenders)
- CSP header: `Content-Security-Policy: default-src 'self'; script-src 'self'` — blocks inline scripts
- Input validation: project name regex `^[\w\s\-\.\,\(\)№«»]{1,200}$` — reject HTML tags at API level
- PDF export: sanitize before rendering (wkhtmltopdf XSS is a known vector)

### 5.3 IDOR in Photo Access

**Threat:** Прораб компании A подставляет photo_id компании B в URL и скачивает чужие фотографии.

**Mitigations:**
```python
# 1. Authorization check on EVERY photo access
def get_photo(photo_id: int, current_user: User):
    photo = Photo.get(photo_id)
    if not photo:
        raise NotFound()  # Same error for "doesn't exist" and "no access"

    # Check: user belongs to the same company as the project
    if photo.task.project.company_id != current_user.company_id:
        raise NotFound()  # NOT 403 — don't reveal existence

    return photo

# 2. Signed URLs for photo downloads (expire in 15 min)
def get_photo_url(photo_id: int) -> str:
    return s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET, 'Key': photo.storage_key},
        ExpiresIn=900
    )

# 3. Never use sequential IDs in URLs
# Use UUIDv4 for photo identifiers in API
# Internal DB can still use integer PK for performance
```

### 5.4 Additional Security Edge Cases

| Threat | Vector | Mitigation |
|--------|--------|-----------|
| Mass estimate generation (abuse) | Free tier: script generating 1000 estimates | Rate limit: 3/hour free, 20/hour paid. CAPTCHA after 5th in 1 hour. IP-based throttling. |
| JWT token theft | XSS, man-in-the-middle | httpOnly + Secure + SameSite=Strict cookies. Short-lived access (15 min). Refresh token rotation. |
| File upload RCE | Disguised PHP/shell script as .jpg | Magic bytes validation. Strip EXIF metadata. Re-encode image (prevents polyglot files). Serve from separate domain (no cookie scope). |
| SSRF via drawing URL | User provides URL to "drawing" -> server fetches internal resource | Whitelist: only accept file uploads, never fetch URLs. If URL fetch needed: block RFC1918, link-local, metadata endpoints. |
| Privilege escalation | User modifies role claim in JWT or registration payload | Role assignment: server-side only, from company admin. JWT claims: signed, not user-modifiable. Registration: default role `member`, admin promotes. |
| Webhook forgery (ЮKassa) | Attacker sends fake payment webhook | HMAC signature verification on every webhook. IP whitelist (ЮKassa ranges). Idempotency key to prevent replay. |
