# Specification: Budget Real-Time (F05)

**Feature:** Бюджет real-time — факт vs план по каждому объекту
**Priority:** P0 (Must Have — Day 90)
**Persona:** Алексей (руководитель ремонтной компании)

---

## 1. Functional Requirements

| ID | Requirement | Priority | Description |
|----|-------------|:--------:|-------------|
| FR-BUD-01 | Регистрация расходов | P0 | Модель `su.expense` — строка расхода с полями: сумма (Monetary), категория, дата, описание, вложение чека. Привязка к проекту. |
| FR-BUD-02 | Категории расходов | P0 | Selection-поле с категориями: материалы, работа, оборудование, транспорт, прочее. |
| FR-BUD-03 | Факт бюджета из расходов | P0 | `budget_actual` на `su.project` пересчитывается из суммы подтверждённых расходов (`su.expense`). Заменяет текущий расчёт из `su.estimate`. |
| FR-BUD-04 | Процент отклонения | P0 | `budget_deviation_pct` = (budget_actual - budget_planned) / budget_planned * 100. Отрицательное = экономия. |
| FR-BUD-05 | AI-алерт при отклонении >10% | P0 | Метод `_check_budget_alert` создаёт `mail.message` при превышении порога 10%. Порог вынесен в class constant `BUDGET_ALERT_THRESHOLD = 10.0`. |
| FR-BUD-06 | Бюджетные отчёты | P0 | Pivot/Graph view расходов по категориям и периодам. |
| FR-BUD-07 | Экспорт PDF/Excel | P0 | Стандартные механизмы Odoo для экспорта списков. QWeb-шаблон для PDF-отчёта по бюджету. |
| FR-BUD-08 | Вложение чека | P0 | Бинарное поле `receipt_attachment` для фото/скана чека к каждой записи расхода. |

## 2. Non-Functional Requirements

| ID | Requirement | Metric |
|----|-------------|--------|
| NFR-BUD-01 | Все денежные поля — Monetary | 0 Float-полей для денег |
| NFR-BUD-02 | Tenant isolation | Все записи фильтруются по `company_id` |
| NFR-BUD-03 | Пересчёт бюджета | < 500 мс при 1000 записей расходов |
| NFR-BUD-04 | Безопасность вложений | Вложения доступны только авторизованным пользователям через Odoo attachment security |

## 3. Data Model

### su.expense (new)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| name | Char | Yes | Описание расхода |
| project_id | Many2one(su.project) | Yes | Привязка к объекту |
| amount | Monetary | Yes | Сумма расхода (currency_id) |
| category | Selection | Yes | Категория: materials/labor/equipment/transport/other |
| expense_date | Date | Yes | Дата расхода |
| receipt_attachment | Binary | No | Скан/фото чека |
| receipt_filename | Char | No | Имя файла вложения |
| state | Selection | Yes | Статус: draft/confirmed/cancelled |
| company_id | Many2one(res.company) | Yes | Компания (tenant isolation) |
| currency_id | Many2one(res.currency) | Yes | related=company_id.currency_id |

### su.project (modifications)

| Field | Change | Description |
|-------|--------|-------------|
| expense_ids | ADD One2many | Связь с su.expense |
| budget_actual | MODIFY compute | Пересчёт из expense_ids вместо estimate_ids |
| _check_budget_alert | ADD method | AI-алерт при отклонении >10% |

## 4. User Stories

```
US-BUD-01: Как руководитель,
           я хочу регистрировать фактические расходы по объекту,
           чтобы видеть реальную картину бюджета.

           AC:
           - Создаю расход с суммой, категорией, датой
           - Могу прикрепить фото чека
           - Сумма в Monetary (не Float)
           - Расход привязан к объекту

US-BUD-02: Как руководитель,
           я хочу получать алерт при отклонении бюджета >10%,
           чтобы вовремя принять меры.

           AC:
           - При подтверждении расхода проверяется deviation_pct
           - Если >10% — создаётся уведомление в chatter проекта
           - Порог настраивается (class constant)

US-BUD-03: Как руководитель,
           я хочу видеть сводку расходов по категориям,
           чтобы понимать структуру затрат.

           AC:
           - Pivot view по категориям × месяцам
           - Graph view (bar chart) по категориям
           - Фильтры по периоду и статусу
```

## 5. Out of Scope (F05 MVP)

- AI-прогноз бюджета (F18, P2)
- Интеграция с 1С для автоимпорта расходов (F16, P2)
- Мультивалютные расходы (одна валюта = валюта компании)
