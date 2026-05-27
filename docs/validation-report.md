# Requirements Validation Report

**Project:** СтройУправ
**Date:** 2026-05-27
**Validator:** requirements-validator (INVEST 50% + SMART 30% + Security 10%)
**Sources:** PRD.md (5 user stories US-01..05), Specification.md (17 user stories US-01..17)

---

## Summary

- **Stories analyzed:** 17
- **Average score:** 74/100
- **Ready (>=70):** 12
- **Caveats (50-69):** 5
- **Blocked (<50):** 0
- **Verdict:** 🟡 CAVEATS

> Average 74 with no blockers, but 5 stories have scores between 50-69 requiring attention before full implementation confidence.

---

## Results Table

| Story | Title | INVEST (X/6) | SMART (X/5) | Security | Score | Status |
|-------|-------|:------------:|:-----------:|:--------:|:-----:|:------:|
| US-01 | Генерация сметы из текстового описания | 6/6 | 5/5 | +5 | **92** | READY |
| US-02 | Генерация сметы из чертежа | 5/6 | 4/5 | +5 | **80** | READY |
| US-03 | Клонирование и версионирование смет | 5/6 | 4/5 | +0 | **75** | READY |
| US-04 | Обзор всех объектов | 6/6 | 5/5 | +0 | **85** | READY |
| US-05 | Детальная карточка объекта | 5/6 | 4/5 | +0 | **73** | READY |
| US-06 | Создание и назначение задачи с мобильного | 5/6 | 4/5 | +0 | **75** | READY |
| US-07 | Отслеживание статуса задачи | 5/6 | 3/5 | +0 | **65** | CAVEATS |
| US-08 | Фотофиксация выполненных работ | 6/6 | 5/5 | +5 | **90** | READY |
| US-09 | Просмотр галереи объекта | 5/6 | 4/5 | +0 | **73** | READY |
| US-10 | Отслеживание бюджета объекта | 5/6 | 4/5 | +0 | **73** | READY |
| US-11 | AI-прогноз бюджета | 4/6 | 3/5 | +0 | **58** | CAVEATS |
| US-12 | Работа офлайн на объекте | 5/6 | 4/5 | +0 | **73** | READY |
| US-13 | Быстрый onboarding за 3 минуты | 4/6 | 3/5 | +0 | **55** | CAVEATS |
| US-14 | Регистрация и trial | 6/6 | 5/5 | +5 | **90** | READY |
| US-15 | Оплата подписки | 5/6 | 4/5 | +5 | **82** | READY |
| US-16 | Управление командой | 5/6 | 4/5 | +5 | **80** | READY |
| US-17 | Freemium — бесплатная AI-смета | 4/6 | 3/5 | -10 | **50** | CAVEATS |

---

## Detailed Analysis

---

### US-01: Генерация сметы из текстового описания

**Score: 92/100 — READY**

#### INVEST Analysis (6/6)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Independent | Pass | Self-contained feature, no blocking dependencies |
| Negotiable | Pass | Implementation details (AI model, UI layout) open to discussion |
| Valuable | Pass | Clear user benefit: "быстро оценить стоимость нового объекта" |
| Estimable | Pass | Well-scoped: text input -> structured table output |
| Small | Pass | Fits in 1-2 sprints with defined scope |
| Testable | Pass | 5 concrete acceptance criteria with measurable thresholds |

#### SMART Analysis (5/5)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Specific | Pass | Clear input (text >= 20 chars + area) and output (table with GESN/FER codes) |
| Measurable | Pass | "< 60 сек", ">10% выше среднерыночной", export in PDF/Excel |
| Achievable | Pass | AI generation with structured prompt is feasible |
| Relevant | Pass | Core value proposition for persona Алексей |
| Time-bound | Pass | 60 sec generation time explicitly stated |

**Security: +5** — Rate limiting defined (FR-EST-09), usage-based billing prevents abuse, JWT auth required.

**Issues:** None.

---

### US-02: Генерация сметы из чертежа

**Score: 80/100 — READY**

#### INVEST Analysis (5/6)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Independent | Pass | Can be developed after US-01 (shares estimate infrastructure) but is self-contained |
| Negotiable | Pass | OCR/vision approach negotiable |
| Valuable | Pass | "не считать вручную объёмы работ" |
| Estimable | Fail | Vision model accuracy (>= 85%) hard to estimate without prototype; what counts as "точность распознавания площадей"? Is it absolute error, percentage error? |
| Small | Pass | Scoped to upload + parse + generate |
| Testable | Pass | 4 ACs with measurable thresholds |

#### SMART Analysis (4/5)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Specific | Pass | Clear flow: upload PDF/JPEG/PNG -> recognize rooms -> generate estimate |
| Measurable | Pass | ">= 85% accuracy" |
| Achievable | Fail | 85% area recognition accuracy from arbitrary floor plans is ambitious; no fallback if accuracy is lower |
| Relevant | Pass | Directly addresses prораб persona pain |
| Time-bound | Pass | NFR-PERF-03 specifies < 90 sec |

**Security: +5** — File upload security (NFR-SEC-10) covers MIME validation, magic bytes, size limits, S3 private ACL.

**Issues found:**
1. "Точность распознавания площадей >= 85%" — accuracy metric is undefined. Is this mean absolute percentage error (MAPE)? Per-room or aggregate? Needs clarification.
2. No AC for unsupported file formats (e.g., corrupt PDF, non-floorplan image).
3. No AC for maximum file size (defined in FR-PHT-01 as 20MB but not in this story's AC).

**Suggested additions:**
- AC5: `GIVEN пользователь загрузил файл > 20 МБ THEN отображается ошибка с указанием лимита`
- AC6: `GIVEN загружен файл не содержащий чертёж THEN система сообщает "Чертёж не распознан" и предлагает ввести данные вручную`

---

### US-03: Клонирование и версионирование смет

**Score: 75/100 — READY**

#### INVEST Analysis (5/6)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Independent | Pass | Can be developed independently |
| Negotiable | Pass | Diff UI approach negotiable |
| Valuable | Pass | "не создавать расчёт с нуля" |
| Estimable | Pass | Standard CRUD + versioning |
| Small | Pass | 3 focused ACs |
| Testable | Fail | AC3 "можно сравнить две версии (diff по позициям и суммам)" — no definition of how diff is displayed, no measurable criteria for what "compare" means |

#### SMART Analysis (4/5)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Specific | Pass | Clone creates copy with naming convention |
| Measurable | Fail | "diff по позициям и суммам" — what exactly is shown? Added/removed/changed items? Percentage change? |
| Achievable | Pass | Standard versioning pattern |
| Relevant | Pass | Time-saver for repeated work types |
| Time-bound | Pass | Implicit — instant clone operation expected |

**Security: +0** — Not security-relevant.

**Issues found:**
1. No AC for maximum number of versions stored (storage implications).
2. No AC for who can clone — any user in tenant? Only owner of estimate?
3. Diff display criteria are vague.

---

### US-04: Обзор всех объектов

**Score: 85/100 — READY**

#### INVEST Analysis (6/6)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Independent | Pass | Core dashboard, no dependencies |
| Negotiable | Pass | Card layout, color scheme negotiable |
| Valuable | Pass | "понимать общую картину бизнеса" |
| Estimable | Pass | Standard dashboard with cards + filters |
| Small | Pass | Well-scoped |
| Testable | Pass | 4 ACs with specific thresholds (< 2 sec, color codes for deviation %) |

#### SMART Analysis (5/5)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Specific | Pass | Exact fields listed, exact color rules (5-15%, >15%) |
| Measurable | Pass | "< 2 секунд", percentage thresholds for colors |
| Achievable | Pass | Standard dashboard pattern |
| Relevant | Pass | Primary screen for руководитель persona |
| Time-bound | Pass | 2 sec load time |

**Security: +0** — Tenant isolation covered at data model level (RLS).

**Issues:** None significant.

---

### US-05: Детальная карточка объекта

**Score: 73/100 — READY**

#### INVEST Analysis (5/6)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Independent | Fail | Depends on US-04 (dashboard) and US-08 (photos) and US-10 (budget) existing |
| Negotiable | Pass | Tab layout negotiable |
| Valuable | Pass | "увидеть полную картину" |
| Estimable | Pass | Tab container with sub-views |
| Small | Pass | 3 ACs, each tab is a sub-component |
| Testable | Pass | Specific tabs and data points listed |

#### SMART Analysis (4/5)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Specific | Pass | Tabs named: Обзор, Задачи, Бюджет, Фото, Сметы |
| Measurable | Fail | No load time for detail page; no metric for "ближайшие дедлайны" (how many? next 7 days?) |
| Achievable | Pass | Standard detail view |
| Relevant | Pass | Drill-down from dashboard |
| Time-bound | Fail | No response time specified (unlike dashboard's < 2 sec) |

**Security: +0** — Not directly security-relevant (covered by tenant RLS).

**Issues found:**
1. No load time metric for detail page.
2. "Ближайшие дедлайны" — how many? What time horizon?
3. "Последние фото" — how many? Last 5? Last 10?

**Suggested additions:**
- AC: `GIVEN detail page opened THEN loads within 3 seconds (P95)`
- Clarify: "отображаются 5 ближайших дедлайнов в следующие 14 дней"

---

### US-06: Создание и назначение задачи с мобильного

**Score: 75/100 — READY**

#### INVEST Analysis (5/6)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Independent | Pass | Core task creation feature |
| Negotiable | Pass | Form layout negotiable |
| Valuable | Pass | "управлять работами прямо на объекте" |
| Estimable | Pass | CRUD form + push notification |
| Small | Pass | Form creation + notification |
| Testable | Fail | AC4 mentions offline but no conflict resolution spec in this story |

#### SMART Analysis (4/5)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Specific | Pass | Fields listed: название, описание, бригада, приоритет, дедлайн |
| Measurable | Pass | "push-уведомление в течение 30 сек" |
| Achievable | Pass | Standard mobile form |
| Relevant | Pass | Primary action for прораб persona |
| Time-bound | Fail | No time metric for task creation itself (form submission -> confirmation) |

**Security: +0** — RBAC covered at API level (foreman can create tasks only for assigned projects).

**Issues found:**
1. AC4 (offline task creation) should cross-reference US-12 conflict resolution rules.
2. No validation rules in AC (e.g., title required, max length).
3. Missing AC for required fields validation error.

---

### US-07: Отслеживание статуса задачи

**Score: 65/100 — CAVEATS**

#### INVEST Analysis (5/6)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Independent | Fail | Depends on US-06 (tasks exist) and notification system |
| Negotiable | Pass | Kanban vs list view negotiable |
| Valuable | Pass | "понимать, где есть проблемы" |
| Estimable | Pass | Kanban board + notification logic |
| Small | Pass | 3 ACs |
| Testable | Pass | Status transitions and blocking rules are testable |

#### SMART Analysis (3/5)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Specific | Pass | Kanban columns named |
| Measurable | Fail | No metric for notification delivery time |
| Achievable | Pass | Standard kanban |
| Relevant | Pass | Oversight for руководитель |
| Time-bound | Fail | No response time; no notification timing (US-06 says 30 sec for push, but US-07 doesn't reference it) |

**Security: +0** — Not directly security-relevant.

**Issues found:**
1. No load time for task board view.
2. No notification timing specified (borrowed from US-06 implicitly).
3. AC3 "помечена как заблокирована" — what visual indicator? How does user unblock?
4. Missing AC for: what happens when a blocking task is deleted?
5. No AC for filtering tasks by priority, assignee, or deadline.

**Suggested rewrites:**
- AC2 should specify: "THEN прораб получает push-уведомление в течение 30 сек"
- Add AC4: `GIVEN task board contains 100+ tasks THEN board renders in < 3 seconds`
- Add AC5: `GIVEN blocking task is deleted THEN dependent task is automatically unblocked`

---

### US-08: Фотофиксация выполненных работ

**Score: 90/100 — READY**

#### INVEST Analysis (6/6)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Independent | Pass | Self-contained photo upload feature |
| Negotiable | Pass | UI for photo upload negotiable |
| Valuable | Pass | "заказчик видел прогресс без звонков" |
| Estimable | Pass | Camera API + upload + offline queue |
| Small | Pass | Well-scoped |
| Testable | Pass | 5 concrete ACs including offline scenario |

#### SMART Analysis (5/5)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Specific | Pass | GPS auto-record, task binding, offline queue |
| Measurable | Pass | "без возможности подмены" (tamper-proof), clear offline/online behavior |
| Achievable | Pass | MediaDevices API + Service Worker |
| Relevant | Pass | Core прораб workflow |
| Time-bound | Pass | Implicit real-time (camera -> attach) |

**Security: +5** — GPS tamper protection mentioned ("без возможности подмены"), file upload security in NFR-SEC-10.

**Issues found:**
1. "Без возможности подмены" GPS — technically hard to enforce on client side. Should clarify server-side validation strategy (e.g., cross-check with known project address).

---

### US-09: Просмотр галереи объекта

**Score: 73/100 — READY**

#### INVEST Analysis (5/6)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Independent | Fail | Depends on US-08 (photos exist) |
| Negotiable | Pass | Gallery layout negotiable |
| Valuable | Pass | "оценить прогресс работ визуально" |
| Estimable | Pass | Gallery view + filters |
| Small | Pass | 3 ACs |
| Testable | Pass | Filterable gallery with metadata |

#### SMART Analysis (4/5)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Specific | Pass | Chronological order, filter by stage, full-size view with metadata |
| Measurable | Fail | No load time for gallery; no pagination spec for galleries with 1000+ photos |
| Achievable | Pass | Standard gallery pattern |
| Relevant | Pass | Visual oversight for руководитель |
| Time-bound | Fail | No performance metric |

**Security: +0** — Pre-signed URLs cover access control.

**Issues found:**
1. No load time specified for gallery (potentially heavy with many photos).
2. No pagination mentioned (FR-PHT-06 says "хронологическая лента" but doesn't specify lazy loading or pagination).
3. No AC for empty state (no photos yet).

---

### US-10: Отслеживание бюджета объекта

**Score: 73/100 — READY**

#### INVEST Analysis (5/6)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Independent | Fail | Depends on projects (US-04) and expense data existing |
| Negotiable | Pass | Table/chart layout negotiable |
| Valuable | Pass | "вовремя реагировать на перерасход" |
| Estimable | Pass | Table + alert logic |
| Small | Pass | 3 ACs |
| Testable | Pass | 10% threshold is testable |

#### SMART Analysis (4/5)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Specific | Pass | Table columns defined, alert threshold defined |
| Measurable | Pass | ">10% deviation" triggers alert |
| Achievable | Pass | Standard budget tracking |
| Relevant | Pass | Core for руководитель persona |
| Time-bound | Fail | "real-time" in feature name but no refresh rate specified. Does "real-time" mean WebSocket updates, polling every 30 sec, or page refresh? |

**Security: +0** — Financial data covered by NFR-SEC-03 (AES-256 encryption at rest).

**Issues found:**
1. "Real-time" is vague — no refresh rate or update mechanism specified.
2. "Прогноз итого" mentioned in AC1 but not detailed (that's US-11).
3. No AC for currency format (always RUB? see FR-BDG-05 multicurrency P1).
4. AC3 "фото чека" — what happens if photo is corrupted or too large?

**Suggested addition:**
- Clarify: "Budget data refreshes within 5 seconds of new expense entry" or "real-time via WebSocket"

---

### US-11: AI-прогноз бюджета

**Score: 58/100 — CAVEATS**

#### INVEST Analysis (4/6)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Independent | Fail | Depends on US-10 (budget data) and sufficient historical data |
| Negotiable | Pass | ML model approach negotiable |
| Valuable | Pass | "планировать финансовые потоки" |
| Estimable | Fail | "AI-прогноз" and "доверительный интервал" — what model? How trained? No basis for effort estimation without prototype |
| Small | Pass | 2 ACs |
| Testable | Pass | ">= 20% completion" and ">15% deviation" are testable thresholds |

#### SMART Analysis (3/5)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Specific | Fail | "доверительный интервал" — what confidence level? 80%? 95%? Not specified |
| Measurable | Pass | ">= 20%" and ">15%" thresholds |
| Achievable | Fail | AI budget forecasting requires historical data that won't exist for MVP (new product, no training data). How does the model work with 0 historical projects? |
| Relevant | Pass | Valuable for financial planning |
| Time-bound | Fail | No response time for prediction generation |

**Security: +0** — Not directly security-relevant.

**Issues found:**
1. **No training data strategy** — MVP will have zero historical data. How does the AI model predict? Heuristic? Rule-based? This needs clarification.
2. "Доверительный интервал" without confidence level is meaningless.
3. No AC for what happens when project is < 20% complete (what UI is shown?).
4. "Рекомендации по оптимизации" in AC2 — what kind? Generic or project-specific?
5. No error handling for when AI prediction fails.

**Suggested rewrites:**
```
AC1: GIVEN объект выполнен на >= 20% AND имеет >= 5 записей расходов
     THEN система отображает прогнозируемую итоговую стоимость
     с 80%-доверительным интервалом
     AND время расчёта < 10 секунд
AC3: GIVEN объект выполнен на < 20%
     THEN отображается сообщение "Недостаточно данных для прогноза"
```

---

### US-12: Работа офлайн на объекте

**Score: 73/100 — READY**

#### INVEST Analysis (5/6)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Independent | Fail | Cross-cutting concern affecting US-06, US-08 |
| Negotiable | Pass | Sync strategy negotiable |
| Valuable | Pass | "не зависеть от качества связи" |
| Estimable | Pass | Service Worker + IndexedDB + sync queue |
| Small | Pass | 4 ACs |
| Testable | Pass | Specific sync behavior and conflict resolution defined |

#### SMART Analysis (4/5)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Specific | Pass | Read/write capabilities defined per entity, conflict resolution rule stated |
| Measurable | Pass | "в течение 60 сек" for sync |
| Achievable | Pass | PWA offline patterns are well-established |
| Relevant | Pass | Critical for прораб on construction site |
| Time-bound | Pass | 60 sec sync time |

**Security: +0** — Offline data stored locally; no encryption-at-rest for IndexedDB mentioned (potential issue but not in AC scope).

**Issues found:**
1. No AC for storage quota (what if device runs out of space?).
2. "Server wins" for data conflicts — could lose user's offline edits without warning. Should notify user.
3. No AC for how long offline data is retained.

---

### US-13: Быстрый onboarding за 3 минуты

**Score: 55/100 — CAVEATS**

#### INVEST Analysis (4/6)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Independent | Pass | Can be built independently |
| Negotiable | Pass | Questions and UI negotiable |
| Valuable | Pass | "сразу начать работу" |
| Estimable | Fail | "персонализация dashboard" based on quiz — scope of personalization is undefined. How many dashboard variants? |
| Small | Pass | 3 ACs |
| Testable | Fail | "за 3 минуты" — what is measured? Time from registration to first meaningful action? Time to complete quiz? No metric for personalization correctness |

#### SMART Analysis (3/5)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Specific | Fail | "настроен под роль" — what exactly changes? Just widget order? Data shown? Navigation? "Подсказки по настройке" — what are they? |
| Measurable | Fail | "3 минуты" is in the title but not in any AC as a measurable criterion |
| Achievable | Pass | Quiz + conditional layout |
| Relevant | Pass | Reduces time-to-value |
| Time-bound | Fail | "3 минуты" is vague — from what starting point? |

**Security: +0** — Not security-relevant.

**Issues found:**
1. "3 минуты" is in the story title but NOT in any acceptance criterion as a measurable threshold.
2. Personalization rules are undefined — what does "настроен под роль" mean concretely?
3. No AC for: what if user changes role later? Can they retake the quiz?
4. No AC for analytics — tracking quiz completion rate.
5. "Предзаполнение шаблонов задач" (FR-ONB-02) not reflected in any AC.

**Suggested rewrites:**
```
AC1: GIVEN пользователь зарегистрировался
     THEN quiz из 4 вопросов отображается в течение 2 сек
     AND завершение quiz занимает < 90 секунд (измерено на тестировании)
AC2: GIVEN quiz завершён с ролью «прораб»
     THEN dashboard показывает виджеты: «Мои задачи», «Фотофиксация», «Уведомления»
     AND НЕ показывает: «Сводная аналитика», «Бюджеты»
AC4: GIVEN пользователь завершил quiz
     THEN может повторно пройти quiz через Настройки → Персонализация
```

---

### US-14: Регистрация и trial

**Score: 90/100 — READY**

#### INVEST Analysis (6/6)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Independent | Pass | Core auth feature |
| Negotiable | Pass | Registration flow details negotiable |
| Valuable | Pass | "оценить продукт перед покупкой" |
| Estimable | Pass | Standard auth + trial logic |
| Small | Pass | 4 focused ACs |
| Testable | Pass | Specific trial duration, auto-downgrade, password reset TTL |

#### SMART Analysis (5/5)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Specific | Pass | Exact trial plan ("Бизнес"), 14 days, auto-downgrade to "Бесплатный" |
| Measurable | Pass | "14 дней", "1 час" TTL for password reset |
| Achievable | Pass | Standard SaaS trial pattern |
| Relevant | Pass | Conversion funnel entry point |
| Time-bound | Pass | 14-day trial, 1-hour reset link TTL |

**Security: +5** — Registration endpoint explicitly does NOT accept `role` in request body (Section 7.3). Password policy defined. JWT + httpOnly cookies specified. Password reset with TTL.

**Issues found:**
1. No AC for email verification (FR-AUTH-01 mentions "подтверждение email" but US-14 ACs don't cover it).
2. No AC for duplicate email registration attempt.
3. No AC for password strength validation feedback.

---

### US-15: Оплата подписки

**Score: 82/100 — READY**

#### INVEST Analysis (5/6)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Independent | Fail | Depends on US-14 (user exists) and ЮKassa integration |
| Negotiable | Pass | Payment UX negotiable |
| Valuable | Pass | Revenue-generating |
| Estimable | Pass | ЮKassa integration is well-documented |
| Small | Pass | 4 ACs |
| Testable | Pass | Payment flow with specific outcomes |

#### SMART Analysis (4/5)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Specific | Pass | Payment methods listed, redirect flow described |
| Measurable | Pass | "мгновенно" activation — though this could be more precise |
| Achievable | Pass | ЮKassa SDK available |
| Relevant | Pass | Revenue stream |
| Time-bound | Fail | "Мгновенно" — define "within 30 seconds of webhook confirmation"? |

**Security: +5** — HMAC-SHA256 webhook verification (NFR-SEC-09), PCI DSS via ЮKassa redirect, idempotency keys.

**Issues found:**
1. "Мгновенно" for plan activation — should specify "within 30 seconds of payment confirmation webhook".
2. No AC for failed payment retry.
3. No AC for prorated billing on mid-cycle upgrade/downgrade (mentioned in FR-AUTH-08 but not in AC).
4. No AC for receipt/invoice generation for юр.лица (legal entities need акт + счёт-фактура).

---

### US-16: Управление командой

**Score: 80/100 — READY**

#### INVEST Analysis (5/6)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Independent | Pass | Can be built after auth (US-14) |
| Negotiable | Pass | Invitation flow negotiable |
| Valuable | Pass | Enables team collaboration |
| Estimable | Pass | Standard invitation system |
| Small | Pass | 4 ACs |
| Testable | Pass | Role assignment and access verification testable |

#### SMART Analysis (4/5)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Specific | Pass | Roles listed, invitation flow described |
| Measurable | Fail | "мгновенно" for role change — no metric |
| Achievable | Pass | Standard RBAC |
| Relevant | Pass | Multi-user collaboration |
| Time-bound | Fail | No expiry for invitation link |

**Security: +5** — RBAC defined (owner/manager can invite), role-based access control, invite endpoint restricted (FR-AUTH-04 error 403).

**Issues found:**
1. No AC for invitation expiry (API says 7 days in FR-AUTH-04 response but AC doesn't mention it).
2. "Мгновенно" for role change propagation — should specify timing.
3. No AC for revoking an invitation before it's accepted.
4. No AC for maximum team size per plan.

---

### US-17: Freemium — бесплатная AI-смета как lead magnet

**Score: 50/100 — CAVEATS**

#### INVEST Analysis (4/6)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Independent | Fail | Depends on US-01 (AI estimate generation) |
| Negotiable | Pass | CTA copy negotiable |
| Valuable | Pass | Lead generation |
| Estimable | Pass | Landing page + anonymous estimate |
| Small | Pass | 3 ACs |
| Testable | Fail | AC1 "предварительная смета (без экспорта)" — how different from full estimate? What's hidden? No spec for "preview" vs "full" estimate |

#### SMART Analysis (3/5)

| Criterion | Pass | Notes |
|-----------|:----:|-------|
| Specific | Fail | "Предварительная смета" — what exactly is shown/hidden? Are totals shown? Are individual rates hidden? |
| Measurable | Pass | "3 бесплатных смет/мес" |
| Achievable | Pass | Standard freemium gate |
| Relevant | Pass | PLG growth strategy |
| Time-bound | Fail | No response time for anonymous estimate generation |

**Security: -10** — CRITICAL MISSING: Anonymous (unauthenticated) endpoint for AI estimate generation has NO security specification:
- No rate limiting defined for anonymous users (NFR-SEC-06 says "20 req/min for anonymous" but no AI-specific limit for anonymous)
- No CAPTCHA or bot protection mentioned
- No IP-based rate limiting for anonymous estimates
- Potential for AI cost abuse (each estimate costs money via Cloud.ru API)
- "3 бесплатных смет/мес" — tracked by what? Cookie? IP? Fingerprint? Easily circumvented without auth

**Issues found:**
1. **SECURITY:** Anonymous AI endpoint is a significant cost-attack vector. Must define bot protection.
2. "Без регистрации" — how are 3/month limits tracked without authentication?
3. "Предварительная смета" content is undefined.
4. No AC for what data is collected (email capture? analytics tracking?).
5. No AC for response time of anonymous estimate.

**Suggested rewrites:**
```
AC1: GIVEN неаутентифицированный пользователь на landing page
     WHEN вводит описание работ (>= 20 символов) и площадь
     AND проходит CAPTCHA-проверку
     THEN получает предварительную смету: итоговая сумма + топ-5 позиций (без кодов расценок)
     AND время генерации < 60 сек
AC4: GIVEN пользователь без регистрации
     THEN лимит 3 смет/мес определяется по fingerprint + IP
     AND при исчерпании лимита — форма регистрации
```

---

## Cross-Document Coherence Check

### 1. PRD ↔ Specification Consistency

| Check | Status | Notes |
|-------|:------:|-------|
| PRD stories (US-01..05) reflected in Spec | PASS | PRD's 5 stories expanded to 17 in Specification |
| Feature IDs match | PASS | F01-F08 consistent across both documents |
| NFRs consistent | PASS | Specification expands PRD's NFR table with IDs and details |
| Personas referenced | PASS | All 3 personas (Алексей, Сергей, Ольга) represented |
| Timeline alignment | PASS | P0/P1/P2 priorities match |

### 2. PRD ↔ Specification Gaps

| Gap | Severity | Notes |
|-----|:--------:|-------|
| PRD US-03 (dashboard) became Spec US-04 | Low | Renumbering is fine but could confuse references |
| PRD US-04 (tasks) became Spec US-06/07 | Low | Good — split into creation and tracking |
| PRD US-05 (photo) became Spec US-08/09 | Low | Good — split into capture and gallery |
| PRD mentions F06 "полнофункциональное мобильное приложение" | Medium | Spec US-12 covers only offline; no story for PWA installation flow |
| PRD mentions "AI подсказывает позиции" in US-01 | Pass | Reflected in FR-EST-04 and US-01 AC4 |

### 3. Missing Stories for Listed Features

| Feature | Story Coverage | Gap |
|---------|:-------------:|-----|
| F01 AI-сметчик | US-01, US-02, US-03 | **Missing:** Story for GESN/FER reference search (FR-EST-07). Users need to browse/search the rate database independently of estimate generation |
| F02 Dashboard | US-04, US-05 | **Missing:** Story for dashboard widget "сводная аналитика" (FR-DSH-05). No story for the summary analytics widgets |
| F03 Tasks | US-06, US-07 | **Missing:** Stories for subtasks (FR-TSK-03), comments (FR-TSK-06), and mass operations (FR-TSK-07). These are P0 requirements without user stories |
| F04 Photo | US-08, US-09 | Adequate |
| F05 Budget | US-10, US-11 | **Missing:** Story for expense registration workflow (FR-BDG-02). US-10 AC3 mentions it briefly but no dedicated story |
| F06 Mobile | US-12 | **Missing:** Story for PWA installation (FR-MOB-01), push notification opt-in (FR-MOB-04), camera permission handling (FR-MOB-05) |
| F07 Onboarding | US-13 | Adequate |
| F08 Auth & Billing | US-14, US-15, US-16, US-17 | **Missing:** Story for subscription management — upgrade/downgrade/cancel (FR-AUTH-08) |

### 4. Orphaned Requirements (in Spec but no story)

| Requirement | Description | Risk |
|-------------|-------------|------|
| FR-TSK-03 | Subtasks | Medium — P0 feature without dedicated story and AC |
| FR-TSK-06 | Task comments with @-mention | Medium — P0 feature without dedicated story |
| FR-TSK-07 | Mass operations | Low — could be deferred |
| FR-BDG-02 | Expense registration | High — core budget workflow without story |
| FR-BDG-04 | Budget reports export | Medium — export functionality undefined |
| FR-MOB-01 | PWA installation | Low — standard PWA behavior |
| FR-MOB-04 | Push notification setup | Medium — opt-in flow undefined |
| FR-AUTH-08 | Subscription management (upgrade/downgrade) | High — billing lifecycle incomplete |
| FR-EST-07 | GESN/FER reference search | Medium — utility feature |
| FR-EST-09 | Usage-based billing counter | Low — infrastructure, not user-facing |

### 5. Architecture Alignment

| Check | Status | Notes |
|-------|:------:|-------|
| Odoo backend matches Spec data model | PASS | PostgreSQL + Odoo ORM aligns |
| FastAPI AI service matches AI requirements | PASS | Separate service for AI endpoints |
| Redis/Celery for async processing | PASS | Matches async estimate generation (202 response) |
| OpenAI-compatible client as AI gateway | PASS | Matches provider fallback strategy |
| PWA architecture | PASS | OWL Frontend + PWA Shell mentioned |
| React Portal for заказчик | INFO | P1 feature, not in MVP user stories |

---

## Verdict

### 🟡 CAVEATS

**Average score: 74/100. No blockers. 5 stories need improvement.**

**Top issues to address before development:**

1. **US-17 (Freemium):** Anonymous AI endpoint has no bot protection or cost-abuse mitigation. Must add CAPTCHA, IP-based rate limiting, and fingerprint-based limit tracking. **Security risk.**

2. **US-11 (AI-прогноз):** No training data strategy for MVP. "Доверительный интервал" undefined. Story needs fundamental rethinking for Day 1 when no historical data exists.

3. **US-13 (Onboarding):** "3 минуты" claim is not in any AC. Personalization rules undefined.

4. **9 orphaned P0 requirements** have no user stories (subtasks, comments, mass operations, expense registration, subscription management). These should either get dedicated stories or be explicitly deferred to P1.

5. **"Real-time"** and **"мгновенно"** used without quantitative definitions in US-10, US-15, US-16.

**Recommendation:** Fix US-17 security gap and US-11 data strategy, then proceed to implementation. Other caveats can be addressed during sprint planning.
