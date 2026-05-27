# Specification: AI-Estimator (F01)

**Feature:** AI-сметчик по ГЭСН/ФЕР
**Priority:** P0 (MVP Day 90)
**Personas:** Алексей (руководитель), Сергей (прораб)

---

## 1. User Stories

### US-01: Генерация сметы из текстового описания

```
Как руководитель ремонтной компании,
я хочу получить смету по ГЭСН/ФЕР из текстового описания работ,
чтобы быстро оценить стоимость нового объекта.

Acceptance Criteria:
  1. GIVEN описание работ >= 20 символов и указан регион
     WHEN пользователь нажимает "Создать смету"
     THEN система возвращает таблицу расценок в течение 60 сек (объект до 200 м²)
  2. GIVEN смета сгенерирована
     THEN каждая позиция содержит: код ГЭСН/ФЕР, наименование, ед. измерения,
          объём, базовая цена, индекс Минстроя, итого (Decimal)
  3. GIVEN смета сгенерирована
     THEN применены актуальные квартальные индексы Минстроя для выбранного региона
  4. GIVEN смета сгенерирована
     THEN позиции с ценой >10% выше среднерыночной помечены флагом OVERPRICED
  5. GIVEN пользователь запрашивает экспорт
     THEN доступны PDF (с шапкой, таблицей, итогами с НДС) и Excel (.xlsx)
```

### US-02: Генерация сметы из чертежа

```
Как прораб,
я хочу загрузить чертёж и получить предварительную смету,
чтобы не считать вручную объёмы работ.

Acceptance Criteria:
  1. GIVEN пользователь загрузил PDF/JPEG/PNG (макс. 50 МБ)
     WHEN система обрабатывает чертёж
     THEN AI распознаёт помещения, площади (точность >= 85%), виды работ
  2. GIVEN чертёж распознан
     THEN система подбирает расценки ГЭСН/ФЕР и генерирует смету (< 90 сек)
  3. GIVEN смета сгенерирована из чертежа
     THEN пользователь может скорректировать любую позицию вручную
```

### US-03: AI-оптимизация сметы

```
Как руководитель,
я хочу получить рекомендации по оптимизации сметы,
чтобы снизить стоимость без потери качества.

Acceptance Criteria:
  1. GIVEN смета содержит позиции >10% выше рыночного бенчмарка
     THEN система выводит до 10 рекомендаций, отсортированных по потенциальной экономии
  2. GIVEN рекомендация типа ALTERNATIVE
     THEN указан альтернативный код ГЭСН/ФЕР и расчёт экономии (Decimal)
  3. GIVEN пользователь принимает рекомендацию
     THEN позиция заменяется, итоги пересчитываются
```

### US-04: Ручная корректировка

```
Как руководитель,
я хочу редактировать любую позицию сметы,
чтобы уточнить объёмы и расценки.

Acceptance Criteria:
  1. GIVEN смета открыта
     WHEN пользователь меняет объём, расценку или удаляет/добавляет позицию
     THEN итоги пересчитываются в реальном времени (< 200 мс)
  2. GIVEN позиция изменена вручную
     THEN она помечена флагом "manual_override"
```

### US-05: Usage-based billing

```
Как система,
я должна учитывать лимиты AI-генераций по тарифу,
чтобы корректно тарифицировать пользователей.

Acceptance Criteria:
  1. GIVEN тариф "Бесплатный" с лимитом 3 AI-сметы/мес
     WHEN пользователь исчерпал лимит
     THEN генерация блокируется с предложением upgrade или оплаты ₽490/смета
  2. GIVEN оплата ₽490 через ЮKassa
     WHEN webhook подтверждает платёж
     THEN разблокируется одна генерация
  3. GIVEN конец календарного месяца
     THEN счётчик использованных генераций сбрасывается
```

---

## 2. API Contracts

### 2.1 POST /api/v1/estimate/generate

Асинхронный endpoint — создаёт задачу Celery, возвращает task_id.

**Request:**
```json
{
  "input_type": "text",                   // "text" | "drawing"
  "description": "Капитальный ремонт квартиры 80 м², штукатурка, электрика...",
  "region": "moscow",                     // субъект РФ для индексов
  "area_m2": 80.0,                        // площадь (Float допустим для площади)
  "file_id": null,                        // UUID загруженного файла (для drawing)
  "project_id": "uuid"                    // привязка к проекту (опционально)
}
```

**Response (202 Accepted):**
```json
{
  "task_id": "uuid",
  "status": "processing",
  "poll_url": "/api/v1/estimate/status/{task_id}"
}
```

**Response (GET /api/v1/estimate/status/{task_id} — 200 OK, completed):**
```json
{
  "task_id": "uuid",
  "status": "completed",
  "estimate": {
    "id": "uuid",
    "project_name": "Квартира на Ленина 5",
    "region": "moscow",
    "lines": [
      {
        "gesn_code": "ГЭСНр 61-01-001-01",
        "description": "Улучшенное оштукатуривание...",
        "unit": "м²",
        "quantity": "80.00",
        "base_rate": "245.50",
        "index_coefficient": "8.34",
        "cost": "163 795.80",
        "match_score": 0.92,
        "is_overpriced": false,
        "manual_override": false
      }
    ],
    "subtotal": "1 250 000.00",
    "nds_rate": "0.20",
    "nds_amount": "250 000.00",
    "grand_total": "1 500 000.00",
    "suggestions_count": 3,
    "created_at": "2026-05-27T10:00:00Z"
  }
}
```

All money fields are strings representing Decimal values.

### 2.2 POST /api/v1/estimate/optimize

**Request:**
```json
{
  "estimate_id": "uuid"
}
```

**Response (200 OK):**
```json
{
  "suggestions": [
    {
      "type": "OVERPRICED",
      "line_gesn_code": "ГЭСНр 61-01-001-01",
      "message": "Оштукатуривание: на 15% дороже рынка",
      "deviation_pct": "15.2",
      "potential_savings": "24 569.37"
    },
    {
      "type": "ALTERNATIVE",
      "line_gesn_code": "ГЭСНр 61-01-001-01",
      "alternative_code": "ФЕР 15-02-016-01",
      "message": "Альтернатива ФЕР — экономия ₽18 400",
      "potential_savings": "18 400.00"
    }
  ]
}
```

### 2.3 POST /api/v1/estimate/{id}/export

**Request:**
```json
{
  "format": "pdf",           // "pdf" | "xlsx"
  "include_suggestions": true,
  "company_header": {
    "name": "ООО Ремонт Плюс",
    "inn": "7712345678"
  }
}
```

**Response (200 OK):**
```json
{
  "download_url": "https://storage.example.com/estimates/uuid.pdf?token=...",
  "expires_at": "2026-05-27T11:00:00Z"
}
```

Download URL is a pre-signed S3 URL (TTL 1 hour).

### 2.4 GET /api/v1/estimate/usage

**Response (200 OK):**
```json
{
  "plan": "starter",
  "limit_monthly": 20,
  "used_this_month": 14,
  "remaining": 6,
  "overage_price": "490.00",
  "reset_date": "2026-06-01"
}
```

---

## 3. Data Model: ГЭСН/ФЕР

### Elasticsearch Index: `gesn_fer`

```json
{
  "code": "ГЭСНр 61-01-001-01",
  "type": "gesn",                         // "gesn" | "fer" | "ter"
  "collection_number": 61,                // номер сборника
  "description": "Улучшенное оштукатуривание цементно-известковым раствором...",
  "description_vector": [0.123, ...],     // embedding для семантического поиска
  "unit": "м²",
  "base_rate": "245.50",                  // базовая расценка (Decimal as string)
  "labor_cost": "120.30",
  "material_cost": "98.20",
  "machine_cost": "27.00",
  "overhead_rate": "0.112",               // коэффициент накладных расходов
  "profit_rate": "0.065",                 // коэффициент сметной прибыли
  "category": "finishing",                // для подбора индексов
  "keywords": ["штукатурка", "раствор", "цементно-известковый"],
  "effective_date": "2024-01-01",
  "superseded_by": null
}
```

### PostgreSQL: `su_minstroy_index`

```sql
CREATE TABLE su_minstroy_index (
    id SERIAL PRIMARY KEY,
    region VARCHAR(100) NOT NULL,          -- субъект РФ
    work_category VARCHAR(50) NOT NULL,    -- категория работ
    quarter VARCHAR(7) NOT NULL,           -- "2026-Q2"
    coefficient DECIMAL(8,4) NOT NULL,     -- индекс пересчёта
    published_date DATE NOT NULL,
    source_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_minstroy_region_cat_quarter
    ON su_minstroy_index (region, work_category, quarter);
```

### PostgreSQL: `su_estimate`

```sql
CREATE TABLE su_estimate (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES su_company(id),
    project_id UUID REFERENCES su_project(id),
    input_type VARCHAR(10) NOT NULL CHECK (input_type IN ('text', 'drawing')),
    description TEXT,
    region VARCHAR(100) NOT NULL,
    area_m2 REAL,                          -- площадь (Float допустим)
    status VARCHAR(20) DEFAULT 'draft',    -- draft, processing, completed, error
    subtotal DECIMAL(15,2) NOT NULL DEFAULT 0,
    nds_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    grand_total DECIMAL(15,2) NOT NULL DEFAULT 0,
    version INTEGER DEFAULT 1,
    parent_id UUID REFERENCES su_estimate(id), -- клонирование
    created_by INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_estimate_tenant_status ON su_estimate (tenant_id, status);
CREATE INDEX idx_estimate_project ON su_estimate (project_id);
```

### PostgreSQL: `su_estimate_line`

```sql
CREATE TABLE su_estimate_line (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    estimate_id UUID NOT NULL REFERENCES su_estimate(id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL,
    gesn_code VARCHAR(30) NOT NULL,
    description TEXT NOT NULL,
    unit VARCHAR(20) NOT NULL,
    quantity DECIMAL(16,4) NOT NULL,
    base_rate DECIMAL(15,2) NOT NULL,
    index_coefficient DECIMAL(8,4) NOT NULL,
    overhead_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    profit_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    cost DECIMAL(15,2) NOT NULL,
    match_score REAL,                      -- AI confidence (Float ok for score)
    manual_override BOOLEAN DEFAULT FALSE,
    is_overpriced BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_estimate_line_estimate ON su_estimate_line (estimate_id);
```

---

## 4. Non-Functional Requirements (Feature-Specific)

| ID | Requirement | Metric |
|----|-------------|--------|
| NFR-F01-01 | Генерация из текста | < 30 сек P95 (до 100 м²), < 60 сек (100-200 м²) |
| NFR-F01-02 | Генерация из чертежа | < 90 сек P95 |
| NFR-F01-03 | ГЭСН/ФЕР поиск | < 500 мс P95, >100K записей |
| NFR-F01-04 | Распознавание площадей | >= 85% accuracy |
| NFR-F01-05 | AI provider uptime | Failover Cloud.ru -> fallback в < 5 сек |
| NFR-F01-06 | File upload | Max 50 МБ чертёж, MIME + magic bytes validation |
| NFR-F01-07 | Money precision | Decimal(15,2) for all money, never Float |
| NFR-F01-08 | Rate limiting | 10 req/min для AI endpoints |
| NFR-F01-09 | Data residency | AI processing только через Cloud.ru (152-ФЗ) |

---

## 5. Security Considerations

- AI prompt injection: sanitize user descriptions before sending to LLM
- File uploads: validate MIME + magic bytes, scan for malicious content, store in S3 with private ACL
- Usage billing: idempotent webhook processing with HMAC-SHA256 verification
- Pre-signed download URLs with 1-hour TTL for exports
- Tenant isolation: all estimate queries scoped by `tenant_id`
- No secrets in code: `AI_BASE_URL`, `AI_API_KEY`, `ELASTICSEARCH_URL` from env vars, crash if missing
