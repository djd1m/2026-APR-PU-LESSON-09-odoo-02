# Specification: СтройУправ

**Version:** 1.0
**Date:** 2026-05-27
**Status:** Draft
**Based on:** [PRD.md](./PRD.md), Phase 0 Discovery Documents

---

## 1. Functional Requirements

### 1.1 AI-Estimator (AI-сметчик) — F01

| ID | Requirement | Priority | Description |
|----|-------------|:--------:|-------------|
| FR-EST-01 | Генерация сметы из текста | P0 | Пользователь вводит текстовое описание работ (вид работ, площадь, материалы). Система генерирует структурированную смету с расценками по ГЭСН/ФЕР. Время генерации < 60 сек для объекта до 200 м². |
| FR-EST-02 | Генерация сметы из чертежа | P0 | Загрузка PDF/JPEG/PNG чертежа. AI распознает помещения, площади (точность >= 85%), определяет виды работ, подбирает расценки ГЭСН/ФЕР. |
| FR-EST-03 | Применение индексов Минстроя | P0 | Автоматическое применение актуальных квартальных индексов пересчёта сметной стоимости (по данным Минстроя РФ) к базовым расценкам. |
| FR-EST-04 | AI-подсказки по оптимизации | P0 | Система выделяет позиции, где цена > 10% выше среднерыночной, и предлагает альтернативные расценки/материалы. |
| FR-EST-05 | Ручная корректировка сметы | P0 | Редактирование любой позиции сметы: изменение объёмов, расценок, добавление/удаление позиций. Пересчёт итогов в реальном времени. |
| FR-EST-06 | Экспорт сметы | P0 | Экспорт в PDF и Excel (.xlsx). PDF содержит шапку с реквизитами компании, таблицу расценок, итоги с НДС. |
| FR-EST-07 | Справочник ГЭСН/ФЕР | P0 | Встроенная база расценок ГЭСН (государственные элементные сметные нормы) и ФЕР (федеральные единичные расценки) с полнотекстовым поиском. Квартальное обновление индексов. |
| FR-EST-08 | История смет | P0 | Сохранение всех сгенерированных смет с версионированием. Возможность клонирования сметы для нового объекта. |
| FR-EST-09 | Usage-based billing для AI-смет | P0 | Учёт количества AI-генераций по тарифному плану. Сверх лимита — оплата ₽490/смета. |

### 1.2 Dashboard объектов — F02

| ID | Requirement | Priority | Description |
|----|-------------|:--------:|-------------|
| FR-DSH-01 | Список объектов | P0 | Карточки объектов с отображением: название, адрес, прогресс (%), бюджет факт/план, дедлайн, статус. |
| FR-DSH-02 | Цветовая индикация | P0 | Объекты с отклонениями выделены: зелёный (в норме), жёлтый (отклонение 5-15%), красный (отклонение > 15% или срыв сроков). |
| FR-DSH-03 | Drill-down по объекту | P0 | Переход в карточку объекта: детализация по этапам, задачам, бригадам, бюджету, фотоотчётам. |
| FR-DSH-04 | Фильтрация и сортировка | P0 | Фильтры: статус (активный/приостановлен/завершён), тип работ, назначенная бригада, дата создания. Сортировка по дедлайну, прогрессу, бюджетному отклонению. |
| FR-DSH-05 | Сводная аналитика | P0 | Виджеты: общий бюджет (факт/план), количество активных объектов, количество задач в работе, средний прогресс. |

### 1.3 Task Management (Управление задачами) — F03

| ID | Requirement | Priority | Description |
|----|-------------|:--------:|-------------|
| FR-TSK-01 | Создание задачи | P0 | Поля: название, описание, объект, этап, бригада, исполнитель, приоритет (низкий/средний/высокий/критический), дедлайн, плановая стоимость. |
| FR-TSK-02 | Жизненный цикл задачи | P0 | Статусы: `новая` -> `в работе` -> `на проверке` -> `выполнена`. Обратные переходы: `на проверке` -> `в работе` (при отклонении). |
| FR-TSK-03 | Подзадачи | P0 | Создание подзадач внутри задачи. Прогресс родительской задачи вычисляется автоматически из завершённых подзадач. |
| FR-TSK-04 | Зависимости | P0 | Связи: «finish-to-start» (задача B не начнётся, пока не завершена задача A). Визуальное отображение блокировок. |
| FR-TSK-05 | Назначение на бригаду | P0 | Привязка задачи к бригаде. Push-уведомление бригадиру при назначении. |
| FR-TSK-06 | Комментарии к задаче | P0 | Текстовые комментарии с @-mention участников. Уведомления упомянутым. |
| FR-TSK-07 | Массовые операции | P0 | Массовое изменение статуса, назначение бригады, перенос сроков для выбранных задач. |

### 1.4 Photo Reports (Фотофиксация) — F04

| ID | Requirement | Priority | Description |
|----|-------------|:--------:|-------------|
| FR-PHT-01 | Загрузка фото | P0 | Фотографирование или загрузка из галереи. Поддержка JPEG, PNG, HEIC. Максимум 10 фото за одну загрузку. Максимальный размер файла: 20 МБ. |
| FR-PHT-02 | Автоматический геотег | P0 | GPS-координаты и timestamp записываются автоматически при съёмке. Отображение на карте объекта. |
| FR-PHT-03 | Привязка к задаче/этапу | P0 | Каждое фото привязано к задаче и/или этапу работ. Обязательное поле при загрузке. |
| FR-PHT-04 | Обновление прогресса | P0 | При загрузке фото с подтверждением выполнения — автоматическое обновление прогресса задачи/этапа. |
| FR-PHT-05 | Offline-режим | P0 | Фото сохраняются локально при отсутствии сети. Автоматическая синхронизация при восстановлении соединения. Индикатор «ожидает загрузки». |
| FR-PHT-06 | Галерея объекта | P0 | Хронологическая лента всех фото объекта с фильтрами по дате, этапу, задаче. |

### 1.5 Budget Control (Бюджет real-time) — F05

| ID | Requirement | Priority | Description |
|----|-------------|:--------:|-------------|
| FR-BDG-01 | План vs Факт | P0 | Отображение плановых и фактических затрат по каждому объекту, этапу, категории (работы, материалы, оборудование). |
| FR-BDG-02 | Регистрация расходов | P0 | Ввод фактических расходов: сумма, категория, описание, дата, привязка к задаче/этапу. Загрузка чека/накладной (фото). |
| FR-BDG-03 | AI-алерты | P0 | Автоматические уведомления при отклонении факта от плана > 10%. Прогноз итоговой стоимости на основе текущих трендов. |
| FR-BDG-04 | Бюджетные отчёты | P0 | Сводные отчёты по объекту: таблица и графики (план/факт по этапам, динамика расходов). Экспорт в PDF/Excel. |
| FR-BDG-05 | Мультивалютность | P1 | Поддержка расчётов в рублях (primary). Отображение курсовых разниц для импортных материалов. |

### 1.6 Mobile App (PWA) — F06

| ID | Requirement | Priority | Description |
|----|-------------|:--------:|-------------|
| FR-MOB-01 | Progressive Web App | P0 | Установка на домашний экран (iOS/Android). Service Worker для кэширования. Manifest.json с иконками и splash screen. |
| FR-MOB-02 | Offline-first | P0 | Локальный кэш: задачи (read/write), фото (write), данные объекта (read). Sync queue при восстановлении сети. Conflict resolution: server wins для данных, append для фото. |
| FR-MOB-03 | Mobile-optimized UI | P0 | Адаптивная вёрстка для экранов 320-428px. Touch-friendly элементы управления (минимальная область нажатия 44x44px). Bottom navigation bar. |
| FR-MOB-04 | Push-уведомления | P0 | Web Push API. Уведомления: назначение задачи, изменение статуса, AI-алерт по бюджету, комментарий с @-mention. |
| FR-MOB-05 | Камера | P0 | Доступ к камере устройства через MediaDevices API для фотофиксации. |

### 1.7 Onboarding Quiz — F07

| ID | Requirement | Priority | Description |
|----|-------------|:--------:|-------------|
| FR-ONB-01 | Quiz из 4 вопросов | P0 | 1) Роль (руководитель/прораб/заказчик/мастер). 2) Размер команды. 3) Тип работ (ремонт квартир/коммерческие/ИЖС/капстроительство). 4) Текущие инструменты. |
| FR-ONB-02 | Персонализация | P0 | На основе ответов — настройка dashboard layout, предзаполнение шаблонов задач, рекомендация тарифного плана. |
| FR-ONB-03 | Skip | P0 | Возможность пропустить quiz и настроить интерфейс позже. |

### 1.8 Auth & Billing — F08

| ID | Requirement | Priority | Description |
|----|-------------|:--------:|-------------|
| FR-AUTH-01 | Регистрация | P0 | Email + пароль или телефон + SMS-код (Twilio/SMS.ru). Подтверждение email. |
| FR-AUTH-02 | Вход | P0 | Email/телефон + пароль. JWT access token (15 мин TTL) + refresh token (30 дней TTL) в httpOnly cookie. |
| FR-AUTH-03 | Роли и права | P0 | Роли: `owner` (полный доступ), `manager` (управление объектами/задачами), `foreman` (задачи/фото своих объектов), `viewer` (только просмотр). RBAC на уровне API. |
| FR-AUTH-04 | Организация (tenant) | P0 | Multi-tenant архитектура. Каждая компания — отдельный tenant. Данные изолированы на уровне PostgreSQL row-level security. |
| FR-AUTH-05 | Тарифные планы | P0 | 4 плана: Бесплатный (1 объект, 3 AI-сметы/мес), Стартер (₽2 990/мес, 5 объектов, 20 AI-смет), Бизнес (₽9 900/мес, 20 объектов, 100 AI-смет, КС-2/КС-3), Корпоративный (₽49 900/мес, unlimited). |
| FR-AUTH-06 | Trial | P0 | 14-дневный trial плана «Бизнес» при регистрации. Автопереход на Бесплатный по окончании. |
| FR-AUTH-07 | Оплата через ЮKassa | P0 | Интеграция с ЮKassa: банковские карты, СБП, ЮMoney. Рекуррентные платежи. Webhook для подтверждения оплаты. |
| FR-AUTH-08 | Управление подпиской | P0 | Просмотр текущего плана, история платежей, смена тарифа (upgrade/downgrade с prorated billing), отмена подписки. |

---

## 2. Non-Functional Requirements

### 2.1 Performance

| ID | Requirement | Metric | Notes |
|----|-------------|--------|-------|
| NFR-PERF-01 | Dashboard load time | < 2 сек (P95) | Включая рендер всех виджетов. Измерение: Time to Interactive (TTI). |
| NFR-PERF-02 | AI-смета генерация (текст) | < 30 сек (P95) для объекта до 100 м²; < 60 сек для 100-200 м² | Streaming response для отображения прогресса. |
| NFR-PERF-03 | AI-смета генерация (чертёж) | < 90 сек (P95) | Включает OCR/vision processing + расчёт расценок. |
| NFR-PERF-04 | API response time | < 300 мс (P95) для CRUD endpoints | Исключая AI-endpoints. |
| NFR-PERF-05 | Photo upload | < 5 сек для фото 10 МБ на 4G | Сжатие на клиенте до 2 МБ перед отправкой (quality 80%). |
| NFR-PERF-06 | Search | < 500 мс для полнотекстового поиска по сметной базе (>100K записей) | PostgreSQL full-text search + GIN index. |
| NFR-PERF-07 | Database queries | < 100 мс (P95) для одиночных запросов | Мониторинг slow queries > 500 мс. |

### 2.2 Security

| ID | Requirement | Description |
|----|-------------|-------------|
| NFR-SEC-01 | Аутентификация | JWT access tokens (RS256, 15 мин TTL). Refresh tokens (30 дней) в httpOnly, Secure, SameSite=Strict cookies. НИКОГДА не хранить токены в localStorage. |
| NFR-SEC-02 | Авторизация | RBAC с проверкой на каждом API endpoint. Row-level security в PostgreSQL для tenant isolation. |
| NFR-SEC-03 | Шифрование данных at rest | AES-256 для чувствительных полей (персональные данные, финансовые данные). PostgreSQL TDE или application-level encryption. |
| NFR-SEC-04 | Шифрование данных in transit | TLS 1.3 для всех соединений. HSTS header. Certificate pinning в мобильном приложении. |
| NFR-SEC-05 | Input validation | Server-side валидация всех входных данных. Parameterized queries (ORM). XSS protection (Content-Security-Policy, output encoding). CSRF tokens для форм. |
| NFR-SEC-06 | Rate limiting | API: 100 req/мин для аутентифицированных, 20 req/мин для anonymous. AI endpoints: 10 req/мин. Login: 5 попыток за 15 мин, далее блокировка на 30 мин. |
| NFR-SEC-07 | Audit log | Логирование всех операций с чувствительными данными: авторизация, изменение прав, доступ к финансовым данным, экспорт данных. Retention: 1 год. |
| NFR-SEC-08 | Secrets management | Все секреты (API keys, DB credentials) — через переменные окружения. НИКОГДА не хранить в коде или конфигурационных файлах. Fallback-значения запрещены. |
| NFR-SEC-09 | Webhook security | HMAC-SHA256 верификация для всех входящих webhooks (ЮKassa, Cloud.ru). Replay protection через timestamp validation (окно 5 мин). |
| NFR-SEC-10 | File upload security | Валидация MIME-type + magic bytes. Максимальный размер: 20 МБ. Хранение в S3-совместимом хранилище с private ACL. Генерация pre-signed URLs для доступа (TTL 1 час). |

### 2.3 Scalability

| ID | Requirement | Description |
|----|-------------|-------------|
| NFR-SCL-01 | Concurrent users | Year 1: 1 000 одновременных, Year 2: 10 000. |
| NFR-SCL-02 | Data growth | Поддержка до 100 000 объектов и 10 млн фото без деградации. Партиционирование таблиц photos и estimates по дате. |
| NFR-SCL-03 | Horizontal scaling | Stateless API servers за nginx reverse proxy. Session data в Redis. Горизонтальное масштабирование через docker-compose scale. |
| NFR-SCL-04 | Database scaling | Read replicas для отчётов и dashboard. Connection pooling через PgBouncer. |
| NFR-SCL-05 | File storage | S3-совместимое object storage (Cloud.ru Object Storage или MinIO). CDN для статических assets. |

### 2.4 Availability

| ID | Requirement | Description |
|----|-------------|-------------|
| NFR-AVL-01 | Uptime SLA | Year 1: 99.5% (max 43.8 час downtime/год). Year 2+: 99.9%. |
| NFR-AVL-02 | Backup | PostgreSQL: automated daily backups, WAL archiving, point-in-time recovery. Retention: 30 дней. S3: versioning enabled. |
| NFR-AVL-03 | Disaster recovery | RPO: 1 час (WAL shipping). RTO: 4 часа. Documented runbook. |
| NFR-AVL-04 | Health checks | `/health` endpoint (readiness + liveness). Docker HEALTHCHECK. Alerting при downtime > 1 мин. |

### 2.5 Compliance (Российские строительные нормы)

| ID | Requirement | Description |
|----|-------------|-------------|
| NFR-CMP-01 | ГЭСН (Государственные элементные сметные нормы) | Встроенная база расценок ГЭСН. Поддержка всех 47 сборников. Обновление при публикации Минстроем новых редакций. |
| NFR-CMP-02 | ФЕР (Федеральные единичные расценки) | База расценок ФЕР. Корреляция с ГЭСН через единую систему кодов. |
| NFR-CMP-03 | Индексы Минстроя | Квартальное обновление индексов пересчёта сметной стоимости строительства. Региональная дифференциация (по субъектам РФ). |
| NFR-CMP-04 | КС-2 (Акт выполненных работ) | Генерация формы КС-2 по ГОСТ Р 7.0.97-2016. Заполнение из данных задач и смет. Экспорт в PDF. |
| NFR-CMP-05 | КС-3 (Справка о стоимости) | Генерация формы КС-3 на основе данных КС-2. Автоматический расчёт НДС, накладных расходов, сметной прибыли. |
| NFR-CMP-06 | 152-ФЗ (Персональные данные) | Хранение персональных данных на территории РФ (Cloud.ru / VPS в РФ). Согласие на обработку ПД при регистрации. Право на удаление данных. Уведомление РКН. |
| NFR-CMP-07 | ТЕР (Территориальные единичные расценки) | Поддержка региональных расценок для ключевых регионов: Москва, Санкт-Петербург, Краснодарский край (расширение по мере роста). |

### 2.6 Observability

| ID | Requirement | Description |
|----|-------------|-------------|
| NFR-OBS-01 | Structured logging | JSON-формат логов. Correlation ID для трейсинга запросов. Levels: DEBUG, INFO, WARN, ERROR. |
| NFR-OBS-02 | Metrics | Prometheus-совместимые метрики: request latency, error rate, AI generation time, active users. |
| NFR-OBS-03 | Alerting | Alerts: error rate > 1%, response time P95 > 2 сек, disk usage > 80%, AI provider unavailable. |

---

## 3. User Stories with Acceptance Criteria

### Epic: AI-сметчик (F01)

**US-01: Генерация сметы из текстового описания**
```
Как руководитель ремонтной компании,
я хочу получить смету по ГЭСН/ФЕР из текстового описания работ,
чтобы быстро оценить стоимость нового объекта и подготовить КП для заказчика.

Acceptance Criteria:
  1. GIVEN пользователь ввёл описание работ (>= 20 символов) и указал площадь
     WHEN нажимает «Создать смету»
     THEN система генерирует таблицу расценок по ГЭСН/ФЕР в течение 60 сек
  2. GIVEN смета сгенерирована
     THEN каждая позиция содержит: код расценки, наименование, единица измерения, объём, цена за единицу, итого
  3. GIVEN смета сгенерирована
     THEN применены актуальные квартальные индексы Минстроя для выбранного региона
  4. GIVEN смета сгенерирована
     THEN позиции с ценой >10% выше среднерыночной выделены жёлтым
  5. GIVEN смета сгенерирована
     WHEN пользователь нажимает «Экспорт»
     THEN доступны форматы PDF и Excel (.xlsx)
```

**US-02: Генерация сметы из чертежа**
```
Как прораб,
я хочу загрузить чертёж и получить предварительную смету,
чтобы не считать вручную объёмы работ.

Acceptance Criteria:
  1. GIVEN пользователь загрузил PDF/JPEG/PNG чертежа
     WHEN система обработала файл
     THEN распознаны помещения и их площади с точностью >= 85%
  2. GIVEN помещения распознаны
     THEN AI определил виды работ и подобрал расценки ГЭСН/ФЕР
  3. GIVEN смета сгенерирована из чертежа
     WHEN пользователь видит результат
     THEN может скорректировать любую позицию вручную
  4. GIVEN смета содержит ошибку распознавания
     WHEN пользователь исправляет площадь или вид работ
     THEN итоговая сумма пересчитывается автоматически
```

**US-03: Клонирование и версионирование смет**
```
Как руководитель,
я хочу скопировать существующую смету для похожего объекта,
чтобы не создавать расчёт с нуля.

Acceptance Criteria:
  1. GIVEN существует сохранённая смета
     WHEN пользователь нажимает «Клонировать»
     THEN создаётся копия с пометкой «Копия — [оригинальное название]»
  2. GIVEN смета была изменена
     THEN предыдущая версия доступна в истории версий
  3. GIVEN открыта история версий
     THEN можно сравнить две версии (diff по позициям и суммам)
```

### Epic: Dashboard объектов (F02)

**US-04: Обзор всех объектов**
```
Как руководитель,
я хочу видеть все мои объекты на одном экране,
чтобы понимать общую картину бизнеса.

Acceptance Criteria:
  1. GIVEN пользователь открыл Dashboard
     THEN отображаются карточки всех объектов с: названием, прогрессом (%), бюджетом факт/план, дедлайном
  2. GIVEN есть объекты с отклонениями
     THEN карточки окрашены: зелёный (норма), жёлтый (5-15% отклонение), красный (>15% или срыв срока)
  3. GIVEN пользователь применяет фильтр «статус: активный»
     THEN отображаются только активные объекты
  4. GIVEN Dashboard содержит 20+ объектов
     THEN страница загружается за < 2 секунды (P95)
```

**US-05: Детальная карточка объекта**
```
Как руководитель,
я хочу перейти в детали объекта по нажатию на карточку,
чтобы увидеть полную картину: задачи, бригады, бюджет, фото.

Acceptance Criteria:
  1. GIVEN пользователь нажимает на карточку объекта
     THEN открывается детальная страница с табами: Обзор, Задачи, Бюджет, Фото, Сметы
  2. GIVEN открыт таб «Обзор»
     THEN видны: прогресс по этапам (progress bar), назначенные бригады, ближайшие дедлайны, последние фото
  3. GIVEN открыт таб «Бюджет»
     THEN отображается таблица план/факт по категориям с графиком динамики
```

### Epic: Управление задачами (F03)

**US-06: Создание и назначение задачи с мобильного**
```
Как прораб,
я хочу создать задачу и назначить на бригаду с телефона,
чтобы управлять работами прямо на объекте.

Acceptance Criteria:
  1. GIVEN прораб открыл форму создания задачи на мобильном
     THEN форма содержит: название, описание, бригада, приоритет, дедлайн
  2. GIVEN задача создана и назначена на бригаду
     THEN бригадир получает push-уведомление в течение 30 сек
  3. GIVEN задача создана
     THEN она появляется в списке задач объекта со статусом «новая»
  4. GIVEN прораб создаёт задачу offline
     THEN задача сохраняется локально и синхронизируется при появлении сети
```

**US-07: Отслеживание статуса задачи**
```
Как руководитель,
я хочу видеть статус всех задач по объекту,
чтобы понимать, где есть проблемы.

Acceptance Criteria:
  1. GIVEN открыт список задач объекта
     THEN задачи отображаются в колонках: Новые, В работе, На проверке, Выполнены
  2. GIVEN бригадир перевёл задачу в «на проверке»
     THEN прораб получает уведомление о необходимости проверки
  3. GIVEN задача имеет зависимость от незавершённой задачи
     THEN она помечена как «заблокирована» и не может быть переведена в «в работе»
```

### Epic: Фотофиксация (F04)

**US-08: Фотофиксация выполненных работ**
```
Как прораб,
я хочу сфотографировать выполненную работу и привязать к задаче,
чтобы заказчик видел прогресс без звонков.

Acceptance Criteria:
  1. GIVEN прораб открыл задачу на мобильном
     WHEN нажимает «Добавить фото»
     THEN открывается камера устройства
  2. GIVEN фото сделано
     THEN автоматически записаны GPS-координаты и timestamp (без возможности подмены)
  3. GIVEN фото загружено
     THEN оно привязано к текущей задаче и отображается в галерее объекта
  4. GIVEN нет интернет-соединения
     WHEN прораб делает фото
     THEN фото сохраняется локально с индикатором «ожидает загрузки»
  5. GIVEN соединение восстановлено
     THEN все фото из очереди загружаются автоматически в фоновом режиме
```

**US-09: Просмотр галереи объекта**
```
Как руководитель,
я хочу просмотреть все фото по объекту в хронологическом порядке,
чтобы оценить прогресс работ визуально.

Acceptance Criteria:
  1. GIVEN открыта галерея объекта
     THEN фото отображаются в хронологическом порядке с датой и привязкой к задаче
  2. GIVEN пользователь применяет фильтр по этапу «Электрика»
     THEN отображаются только фото привязанные к задачам этапа «Электрика»
  3. GIVEN пользователь нажимает на фото
     THEN открывается полноразмерный просмотр с метаданными: дата, GPS, задача, автор
```

### Epic: Бюджет real-time (F05)

**US-10: Отслеживание бюджета объекта**
```
Как руководитель,
я хочу видеть бюджет объекта в реальном времени (план vs факт),
чтобы вовремя реагировать на перерасход.

Acceptance Criteria:
  1. GIVEN открыт таб «Бюджет» объекта
     THEN отображена таблица: этап | план | факт | отклонение (%) | прогноз итого
  2. GIVEN фактические расходы превысили план на > 10%
     THEN строка выделена красным и руководитель получил AI-алерт
  3. GIVEN пользователь нажимает «Добавить расход»
     THEN форма: сумма, категория, описание, дата, привязка к задаче, фото чека
```

**US-11: AI-прогноз бюджета**
```
Как руководитель,
я хочу получать AI-прогноз итоговой стоимости объекта,
чтобы планировать финансовые потоки.

Acceptance Criteria:
  1. GIVEN объект выполнен на >= 20%
     THEN система отображает прогнозируемую итоговую стоимость с доверительным интервалом
  2. GIVEN прогноз превышает план на > 15%
     THEN руководитель получает push-уведомление с рекомендациями по оптимизации
```

### Epic: Mobile App (F06)

**US-12: Работа офлайн на объекте**
```
Как прораб,
я хочу работать с приложением без интернета на объекте,
чтобы не зависеть от качества связи.

Acceptance Criteria:
  1. GIVEN устройство offline
     THEN доступны: просмотр задач, создание задач, фотофиксация
  2. GIVEN устройство вернулось online
     THEN все изменения синхронизируются автоматически в течение 60 сек
  3. GIVEN конфликт данных (offline edit + server edit)
     THEN серверная версия побеждает для данных; фото добавляются (append)
  4. GIVEN синхронизация завершена
     THEN пользователь видит уведомление «Данные синхронизированы»
```

### Epic: Onboarding (F07)

**US-13: Быстрый onboarding за 3 минуты**
```
Как новый пользователь,
я хочу настроить приложение за 3 минуты,
чтобы сразу начать работу, а не разбираться с интерфейсом.

Acceptance Criteria:
  1. GIVEN пользователь зарегистрировался
     THEN появляется quiz из 4 вопросов (роль, размер команды, тип работ, текущие инструменты)
  2. GIVEN quiz завершён
     THEN dashboard настроен под роль: прораб видит задачи и фото, руководитель — объекты и бюджет
  3. GIVEN пользователь нажимает «Пропустить»
     THEN загружается дефолтный dashboard с подсказками по настройке
```

### Epic: Auth & Billing (F08)

**US-14: Регистрация и trial**
```
Как потенциальный клиент,
я хочу зарегистрироваться и получить 14-дневный trial,
чтобы оценить продукт перед покупкой.

Acceptance Criteria:
  1. GIVEN пользователь заполнил форму (email, пароль, имя компании)
     WHEN нажимает «Зарегистрироваться»
     THEN создан аккаунт с тарифом «Бизнес (trial)» на 14 дней
  2. GIVEN trial активен
     THEN в header отображается «Trial: осталось X дней»
  3. GIVEN trial истёк и пользователь не оплатил
     THEN аккаунт переведён на тариф «Бесплатный» (1 объект, 3 AI-сметы/мес)
  4. GIVEN пользователь потерял пароль
     WHEN нажимает «Забыл пароль»
     THEN получает email со ссылкой для сброса (TTL 1 час)
```

**US-15: Оплата подписки**
```
Как руководитель компании,
я хочу оплатить подписку банковской картой или через СБП,
чтобы получить доступ к расширенному функционалу.

Acceptance Criteria:
  1. GIVEN пользователь выбрал тариф «Бизнес»
     WHEN нажимает «Оплатить»
     THEN открывается страница оплаты ЮKassa с выбором: карта, СБП, ЮMoney
  2. GIVEN оплата успешна
     THEN тариф активирован мгновенно, пользователь получает email-чек
  3. GIVEN подписка активна
     THEN ежемесячное автоматическое списание (рекуррентный платёж)
  4. GIVEN пользователь отменил подписку
     THEN доступ сохраняется до конца оплаченного периода, далее — тариф «Бесплатный»
```

**US-16: Управление командой**
```
Как руководитель,
я хочу добавить сотрудников в систему и назначить роли,
чтобы прорабы и бригадиры могли работать в приложении.

Acceptance Criteria:
  1. GIVEN руководитель открыл раздел «Команда»
     WHEN нажимает «Пригласить»
     THEN вводит email/телефон и выбирает роль (manager/foreman/viewer)
  2. GIVEN приглашение отправлено
     THEN приглашённый получает email/SMS со ссылкой на регистрацию
  3. GIVEN сотрудник принял приглашение
     THEN он видит только объекты и задачи, назначенные на него (согласно роли)
  4. GIVEN руководитель изменил роль сотрудника
     THEN права доступа обновляются мгновенно
```

**US-17: Freemium — бесплатная AI-смета как lead magnet**
```
Как частный мастер,
я хочу бесплатно создать AI-смету без регистрации,
чтобы оценить качество сервиса перед покупкой.

Acceptance Criteria:
  1. GIVEN неаутентифицированный пользователь на landing page
     WHEN вводит описание работ и нажимает «Создать смету бесплатно»
     THEN получает предварительную смету (без экспорта)
  2. GIVEN предварительная смета показана
     THEN отображается CTA «Зарегистрируйтесь для экспорта в PDF и полного доступа»
  3. GIVEN лимит 3 бесплатных смет/мес исчерпан
     THEN отображается сообщение с предложением регистрации
```

---

## 4. API Contracts

### 4.1 Base URL and Conventions

```
Base URL: https://api.stroyuprav.ru/v1
Content-Type: application/json
Authentication: Bearer JWT (Authorization header)
Pagination: ?page=1&page_size=20 (default 20, max 100)
Error format: { "error": { "code": "string", "message": "string", "details": {} } }
```

### 4.2 Estimates API (AI-сметчик)

#### POST /estimates/generate

Генерация AI-сметы из текстового описания.

```
Request:
  POST /v1/estimates/generate
  Authorization: Bearer <jwt>
  Content-Type: application/json

  {
    "project_id": "uuid",                    // optional — привязка к объекту
    "description": "string",                 // >= 20 символов, описание работ
    "area_m2": 85.5,                         // площадь в м²
    "region_code": "77",                     // код региона для индексов Минстроя
    "work_types": ["отделка", "электрика"],  // optional — фильтр по видам работ
    "pricing_base": "gesn" | "fer"           // база расценок (default: "gesn")
  }

Response 202 (Accepted):
  {
    "estimate_id": "uuid",
    "status": "processing",
    "poll_url": "/v1/estimates/{estimate_id}/status"
  }

Response 429 (Rate Limit):
  {
    "error": {
      "code": "ESTIMATE_LIMIT_EXCEEDED",
      "message": "Лимит AI-смет по тарифу исчерпан",
      "details": { "limit": 20, "used": 20, "upgrade_url": "/billing/plans" }
    }
  }
```

#### GET /estimates/{id}/status

Polling статуса генерации.

```
Response 200:
  {
    "estimate_id": "uuid",
    "status": "processing" | "completed" | "failed",
    "progress_pct": 75,
    "result": null | EstimateObject   // populated when status = "completed"
  }
```

#### GET /estimates/{id}

Получение сметы.

```
Response 200:
  {
    "id": "uuid",
    "project_id": "uuid | null",
    "title": "string",
    "region_code": "77",
    "pricing_base": "gesn",
    "version": 3,
    "items": [
      {
        "id": "uuid",
        "code": "ГЭСНр 61-01-001-01",
        "name": "Разборка покрытий полов из линолеума",
        "unit": "100 м²",
        "quantity": 0.855,
        "unit_price_base": 1245.00,
        "index": 8.21,
        "unit_price_current": 10221.45,
        "total": 8739.34,
        "is_above_market": false,
        "optimization_hint": null
      }
    ],
    "totals": {
      "direct_costs": 425000.00,
      "overhead": 55250.00,
      "profit": 34000.00,
      "subtotal": 514250.00,
      "vat": 102850.00,
      "total": 617100.00
    },
    "created_at": "2026-05-27T10:00:00Z",
    "updated_at": "2026-05-27T10:05:00Z"
  }
```

#### PUT /estimates/{id}/items/{item_id}

Ручная корректировка позиции сметы.

```
Request:
  {
    "quantity": 1.0,
    "unit_price_base": 1300.00
  }

Response 200:
  { ...updated item with recalculated totals... }
```

#### GET /estimates/{id}/export?format=pdf|xlsx

Экспорт сметы.

```
Response 200:
  Content-Type: application/pdf | application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
  Content-Disposition: attachment; filename="smeta_2026-05-27.pdf"
  <binary>
```

### 4.3 Projects API (Объекты)

#### GET /projects

```
Request:
  GET /v1/projects?status=active&page=1&page_size=20
  Authorization: Bearer <jwt>

Response 200:
  {
    "items": [
      {
        "id": "uuid",
        "name": "Ремонт 3-комн кв ул. Ленина 15",
        "address": "г. Москва, ул. Ленина, д.15, кв.42",
        "status": "active" | "paused" | "completed",
        "progress_pct": 65,
        "budget_planned": 2500000.00,
        "budget_actual": 1800000.00,
        "budget_deviation_pct": -28.0,
        "deadline": "2026-08-15",
        "brigade_ids": ["uuid"],
        "created_at": "2026-03-01T00:00:00Z"
      }
    ],
    "total": 12,
    "page": 1,
    "page_size": 20
  }
```

#### POST /projects

```
Request:
  {
    "name": "string",
    "address": "string",
    "description": "string",
    "budget_planned": 2500000.00,
    "deadline": "2026-08-15",
    "work_type": "apartment_renovation" | "commercial" | "izhs" | "capital_construction",
    "area_m2": 85.5
  }

Response 201:
  { ...created project... }
```

#### GET /projects/{id}/summary

Сводка по объекту для drill-down.

```
Response 200:
  {
    "project": { ...project details... },
    "stages": [
      { "name": "Демонтаж", "progress_pct": 100, "budget_planned": 150000, "budget_actual": 145000 },
      { "name": "Электрика", "progress_pct": 80, "budget_planned": 300000, "budget_actual": 290000 }
    ],
    "tasks_summary": { "total": 45, "completed": 30, "in_progress": 10, "blocked": 2, "new": 3 },
    "recent_photos": [ { "id": "uuid", "thumbnail_url": "string", "created_at": "string" } ],
    "budget_forecast": { "predicted_total": 2650000, "confidence": 0.85 }
  }
```

### 4.4 Tasks API (Задачи)

#### GET /projects/{project_id}/tasks

```
Request:
  GET /v1/projects/{project_id}/tasks?status=in_progress&brigade_id=uuid
  Authorization: Bearer <jwt>

Response 200:
  {
    "items": [
      {
        "id": "uuid",
        "project_id": "uuid",
        "title": "Штукатурка стен — спальня",
        "description": "string",
        "status": "new" | "in_progress" | "review" | "completed",
        "priority": "low" | "medium" | "high" | "critical",
        "brigade_id": "uuid",
        "assignee_id": "uuid",
        "stage": "Отделка",
        "deadline": "2026-06-10",
        "planned_cost": 45000.00,
        "actual_cost": 0.00,
        "parent_task_id": "uuid | null",
        "depends_on": ["uuid"],
        "photo_count": 3,
        "subtask_count": 4,
        "subtask_completed": 2,
        "created_at": "2026-05-20T00:00:00Z"
      }
    ],
    "total": 45,
    "page": 1,
    "page_size": 20
  }
```

#### POST /projects/{project_id}/tasks

```
Request:
  {
    "title": "string",
    "description": "string",
    "brigade_id": "uuid",
    "assignee_id": "uuid",
    "stage": "string",
    "priority": "medium",
    "deadline": "2026-06-10",
    "planned_cost": 45000.00,
    "parent_task_id": "uuid | null",
    "depends_on": ["uuid"]
  }

Response 201:
  { ...created task... }
```

#### PATCH /projects/{project_id}/tasks/{task_id}/status

```
Request:
  {
    "status": "in_progress" | "review" | "completed",
    "comment": "Работы завершены, фото прикреплены"
  }

Response 200:
  { ...updated task... }

Response 409 (Conflict):
  {
    "error": {
      "code": "TASK_BLOCKED",
      "message": "Задача заблокирована: зависимость 'Демонтаж пола' не завершена",
      "details": { "blocked_by": ["uuid"] }
    }
  }
```

### 4.5 Photos API (Фотофиксация)

#### POST /projects/{project_id}/photos

```
Request:
  POST /v1/projects/{project_id}/photos
  Authorization: Bearer <jwt>
  Content-Type: multipart/form-data

  Fields:
    file: <binary>                // JPEG/PNG/HEIC, max 20MB
    task_id: "uuid"               // required
    stage: "string"               // optional
    latitude: 55.7558             // auto from device
    longitude: 37.6173            // auto from device
    captured_at: "ISO8601"        // timestamp from device
    comment: "string"             // optional

Response 201:
  {
    "id": "uuid",
    "project_id": "uuid",
    "task_id": "uuid",
    "url": "https://storage.stroyuprav.ru/photos/uuid.jpg",
    "thumbnail_url": "https://storage.stroyuprav.ru/photos/uuid_thumb.jpg",
    "latitude": 55.7558,
    "longitude": 37.6173,
    "captured_at": "2026-05-27T14:30:00Z",
    "uploaded_by": "uuid",
    "created_at": "2026-05-27T14:30:05Z"
  }
```

#### GET /projects/{project_id}/photos

```
Request:
  GET /v1/projects/{project_id}/photos?stage=Электрика&from=2026-05-01&to=2026-05-31&page=1
  Authorization: Bearer <jwt>

Response 200:
  {
    "items": [ ...PhotoObject... ],
    "total": 156,
    "page": 1,
    "page_size": 20
  }
```

### 4.6 Billing API (Подписки)

#### GET /billing/subscription

```
Response 200:
  {
    "plan": "business",
    "status": "active" | "trial" | "expired" | "cancelled",
    "trial_ends_at": "2026-06-10T00:00:00Z | null",
    "current_period_end": "2026-06-27T00:00:00Z",
    "ai_estimates_used": 15,
    "ai_estimates_limit": 100,
    "projects_used": 8,
    "projects_limit": 20
  }
```

#### POST /billing/checkout

```
Request:
  {
    "plan": "starter" | "business" | "enterprise",
    "payment_method": "card" | "sbp" | "yoomoney"
  }

Response 200:
  {
    "checkout_url": "https://yookassa.ru/checkout/...",
    "payment_id": "uuid"
  }
```

#### POST /billing/webhook (internal — ЮKassa callback)

```
Request (from ЮKassa):
  X-YooKassa-Signature: <hmac-sha256>
  {
    "event": "payment.succeeded",
    "object": {
      "id": "uuid",
      "status": "succeeded",
      "amount": { "value": "9900.00", "currency": "RUB" },
      "metadata": { "tenant_id": "uuid", "plan": "business" }
    }
  }

Verification:
  1. Validate HMAC-SHA256 signature
  2. Check timestamp within 5-minute window (replay protection)
  3. Idempotency check by payment_id

Response 200:
  { "status": "ok" }
```

### 4.7 Auth API

#### POST /auth/register

```
Request:
  {
    "email": "string",
    "password": "string",           // min 8 chars, 1 uppercase, 1 digit
    "company_name": "string",
    "phone": "string"               // optional, format: +7XXXXXXXXXX
  }

Response 201:
  {
    "user_id": "uuid",
    "tenant_id": "uuid",
    "email": "string",
    "plan": "business_trial",
    "trial_ends_at": "2026-06-10T00:00:00Z"
  }

Set-Cookie: refresh_token=<token>; HttpOnly; Secure; SameSite=Strict; Path=/v1/auth; Max-Age=2592000
```

#### POST /auth/login

```
Request:
  {
    "email": "string",
    "password": "string"
  }

Response 200:
  {
    "access_token": "<jwt>",          // RS256, 15 min TTL
    "expires_in": 900,
    "user": {
      "id": "uuid",
      "email": "string",
      "role": "owner" | "manager" | "foreman" | "viewer",
      "tenant_id": "uuid"
    }
  }

Set-Cookie: refresh_token=<token>; HttpOnly; Secure; SameSite=Strict; Path=/v1/auth; Max-Age=2592000
```

#### POST /auth/refresh

```
Request:
  Cookie: refresh_token=<token>

Response 200:
  {
    "access_token": "<new-jwt>",
    "expires_in": 900
  }
```

#### POST /auth/invite

```
Request:
  Authorization: Bearer <jwt>   // must be owner or manager
  {
    "email": "string",
    "role": "manager" | "foreman" | "viewer"
  }

Response 201:
  {
    "invitation_id": "uuid",
    "email": "string",
    "role": "foreman",
    "expires_at": "2026-06-03T00:00:00Z"
  }

Error 403:
  { "error": { "code": "INSUFFICIENT_ROLE", "message": "Only owner/manager can invite" } }
```

---

## 5. Data Model

### 5.1 Entity Relationship Diagram (текстовое описание)

```
Tenant 1──* User
Tenant 1──* Project
Tenant 1──* Brigade

Project 1──* Estimate
Project 1──* Task
Project 1──* Photo
Project 1──* Expense
Project *──* Brigade (через ProjectBrigade)

Task 1──* Task (parent-child: подзадачи)
Task *──* Task (depends_on: зависимости)
Task 1──* Photo
Task 1──* TaskComment

Estimate 1──* EstimateItem
Estimate 1──* EstimateVersion

User 1──* Photo (uploaded_by)
User 1──* TaskComment (author)
User *──1 Brigade (member)

Brigade 1──1 User (brigadier — leader)

Tenant 1──1 Subscription
Subscription 1──* Payment
```

### 5.2 Key Entities

#### Tenant (Организация)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | |
| name | VARCHAR(255) | NOT NULL | Название компании |
| inn | VARCHAR(12) | UNIQUE, nullable | ИНН организации |
| phone | VARCHAR(20) | | Контактный телефон |
| email | VARCHAR(255) | | Контактный email |
| address | TEXT | | Юридический адрес |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

#### User (Пользователь)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK -> Tenant, NOT NULL | |
| email | VARCHAR(255) | UNIQUE, NOT NULL | |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt hash |
| phone | VARCHAR(20) | UNIQUE, nullable | +7XXXXXXXXXX |
| first_name | VARCHAR(100) | NOT NULL | |
| last_name | VARCHAR(100) | NOT NULL | |
| role | ENUM | NOT NULL | owner, manager, foreman, viewer |
| brigade_id | UUID | FK -> Brigade, nullable | Для прорабов/рабочих |
| is_active | BOOLEAN | DEFAULT TRUE | |
| last_login_at | TIMESTAMPTZ | nullable | |
| created_at | TIMESTAMPTZ | NOT NULL | |

**RLS Policy:** `WHERE tenant_id = current_setting('app.tenant_id')::uuid`

#### Project (Объект/Проект)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK -> Tenant, NOT NULL | |
| name | VARCHAR(255) | NOT NULL | Название объекта |
| address | TEXT | | Адрес объекта |
| description | TEXT | | |
| work_type | ENUM | NOT NULL | apartment_renovation, commercial, izhs, capital_construction |
| area_m2 | DECIMAL(10,2) | | Площадь в м² |
| status | ENUM | NOT NULL, DEFAULT 'active' | active, paused, completed |
| progress_pct | DECIMAL(5,2) | DEFAULT 0 | Вычисляется из задач |
| budget_planned | DECIMAL(15,2) | | Плановый бюджет (руб.) |
| budget_actual | DECIMAL(15,2) | DEFAULT 0 | Фактический бюджет (руб.) |
| deadline | DATE | | |
| started_at | DATE | | |
| completed_at | DATE | nullable | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `(tenant_id, status)`, `(tenant_id, deadline)`

#### Estimate (Смета)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK -> Tenant, NOT NULL | |
| project_id | UUID | FK -> Project, nullable | |
| title | VARCHAR(255) | NOT NULL | |
| description | TEXT | | Исходное описание для AI |
| region_code | VARCHAR(3) | NOT NULL | Код региона (ОКАТО) |
| pricing_base | ENUM | NOT NULL | gesn, fer |
| version | INTEGER | DEFAULT 1 | Версия сметы |
| status | ENUM | NOT NULL | draft, approved, archived |
| total_amount | DECIMAL(15,2) | | Итого с НДС |
| ai_generated | BOOLEAN | DEFAULT FALSE | Создана AI или вручную |
| source_file_url | TEXT | nullable | URL загруженного чертежа |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Partitioning:** by `created_at` (monthly)

#### EstimateItem (Позиция сметы)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | |
| estimate_id | UUID | FK -> Estimate, NOT NULL | |
| sort_order | INTEGER | NOT NULL | Порядок в смете |
| code | VARCHAR(50) | NOT NULL | Код расценки ГЭСН/ФЕР |
| name | TEXT | NOT NULL | Наименование работы |
| unit | VARCHAR(50) | NOT NULL | Единица измерения |
| quantity | DECIMAL(12,4) | NOT NULL | Объём работ |
| unit_price_base | DECIMAL(12,2) | NOT NULL | Базовая цена за единицу |
| index_value | DECIMAL(8,4) | NOT NULL, DEFAULT 1.0 | Индекс пересчёта Минстроя |
| unit_price_current | DECIMAL(12,2) | NOT NULL | Текущая цена (base * index) |
| total | DECIMAL(15,2) | NOT NULL | Итого = quantity * unit_price_current |
| is_above_market | BOOLEAN | DEFAULT FALSE | Цена выше среднерыночной >10% |
| optimization_hint | TEXT | nullable | AI-подсказка по оптимизации |

#### Task (Задача)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK -> Tenant, NOT NULL | |
| project_id | UUID | FK -> Project, NOT NULL | |
| parent_task_id | UUID | FK -> Task, nullable | Для подзадач |
| title | VARCHAR(255) | NOT NULL | |
| description | TEXT | | |
| status | ENUM | NOT NULL, DEFAULT 'new' | new, in_progress, review, completed |
| priority | ENUM | NOT NULL, DEFAULT 'medium' | low, medium, high, critical |
| stage | VARCHAR(100) | | Этап работ (Демонтаж, Электрика и т.д.) |
| brigade_id | UUID | FK -> Brigade, nullable | |
| assignee_id | UUID | FK -> User, nullable | |
| planned_cost | DECIMAL(12,2) | | Плановая стоимость |
| actual_cost | DECIMAL(12,2) | DEFAULT 0 | Фактическая стоимость |
| deadline | DATE | | |
| started_at | TIMESTAMPTZ | nullable | |
| completed_at | TIMESTAMPTZ | nullable | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `(project_id, status)`, `(brigade_id, status)`, `(parent_task_id)`

#### TaskDependency (Зависимости задач)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| task_id | UUID | FK -> Task, PK | Зависимая задача |
| depends_on_task_id | UUID | FK -> Task, PK | Блокирующая задача |
| dependency_type | ENUM | DEFAULT 'finish_to_start' | finish_to_start |

#### Photo (Фото)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK -> Tenant, NOT NULL | |
| project_id | UUID | FK -> Project, NOT NULL | |
| task_id | UUID | FK -> Task, NOT NULL | |
| stage | VARCHAR(100) | nullable | Этап работ |
| file_url | TEXT | NOT NULL | URL в S3-хранилище |
| thumbnail_url | TEXT | NOT NULL | URL миниатюры |
| file_size_bytes | INTEGER | NOT NULL | |
| mime_type | VARCHAR(50) | NOT NULL | |
| latitude | DECIMAL(10,7) | nullable | GPS широта |
| longitude | DECIMAL(10,7) | nullable | GPS долгота |
| captured_at | TIMESTAMPTZ | NOT NULL | Время съёмки (от устройства) |
| uploaded_by | UUID | FK -> User, NOT NULL | |
| comment | TEXT | nullable | |
| created_at | TIMESTAMPTZ | NOT NULL | |

**Partitioning:** by `created_at` (monthly)
**Indexes:** `(project_id, created_at)`, `(task_id)`

#### Brigade (Бригада)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK -> Tenant, NOT NULL | |
| name | VARCHAR(255) | NOT NULL | Название бригады |
| brigadier_id | UUID | FK -> User, NOT NULL | Бригадир (руководитель) |
| specialization | VARCHAR(255) | | Специализация (электрика, сантехника и т.д.) |
| is_active | BOOLEAN | DEFAULT TRUE | |
| created_at | TIMESTAMPTZ | NOT NULL | |

#### Expense (Расход)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK -> Tenant, NOT NULL | |
| project_id | UUID | FK -> Project, NOT NULL | |
| task_id | UUID | FK -> Task, nullable | |
| category | ENUM | NOT NULL | labor, materials, equipment, transport, other |
| amount | DECIMAL(12,2) | NOT NULL | Сумма в рублях |
| description | TEXT | | |
| receipt_url | TEXT | nullable | Фото чека/накладной |
| date | DATE | NOT NULL | Дата расхода |
| created_by | UUID | FK -> User, NOT NULL | |
| created_at | TIMESTAMPTZ | NOT NULL | |

#### Subscription (Подписка)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK -> Tenant, UNIQUE, NOT NULL | |
| plan | ENUM | NOT NULL | free, starter, business, enterprise |
| status | ENUM | NOT NULL | active, trial, expired, cancelled |
| trial_ends_at | TIMESTAMPTZ | nullable | |
| current_period_start | TIMESTAMPTZ | | |
| current_period_end | TIMESTAMPTZ | | |
| ai_estimates_used | INTEGER | DEFAULT 0 | Счётчик за текущий период |
| ai_estimates_limit | INTEGER | NOT NULL | По тарифу |
| projects_limit | INTEGER | NOT NULL | По тарифу |
| yookassa_customer_id | VARCHAR(100) | nullable | ID клиента в ЮKassa |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

#### Payment (Платёж)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK -> Tenant, NOT NULL | |
| subscription_id | UUID | FK -> Subscription, NOT NULL | |
| yookassa_payment_id | VARCHAR(100) | UNIQUE, NOT NULL | ID платежа в ЮKassa |
| amount | DECIMAL(10,2) | NOT NULL | Сумма в рублях |
| status | ENUM | NOT NULL | pending, succeeded, cancelled, refunded |
| payment_method | VARCHAR(50) | | card, sbp, yoomoney |
| paid_at | TIMESTAMPTZ | nullable | |
| created_at | TIMESTAMPTZ | NOT NULL | |

### 5.3 Справочные таблицы (сметная база)

#### GesnRate (Расценка ГЭСН/ФЕР)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | |
| code | VARCHAR(50) | UNIQUE, NOT NULL | Код расценки |
| collection | VARCHAR(10) | NOT NULL | Номер сборника |
| name | TEXT | NOT NULL | Наименование |
| unit | VARCHAR(50) | NOT NULL | Единица измерения |
| base_price | DECIMAL(12,2) | NOT NULL | Базовая цена (2001 год) |
| pricing_base | ENUM | NOT NULL | gesn, fer |
| category | VARCHAR(100) | | Категория работ |
| search_vector | TSVECTOR | | Для полнотекстового поиска |

**Indexes:** GIN index on `search_vector`, `(pricing_base, category)`

#### MinstroyIndex (Индекс Минстроя)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | |
| region_code | VARCHAR(3) | NOT NULL | Код региона |
| quarter | VARCHAR(7) | NOT NULL | "2026-Q2" |
| work_category | VARCHAR(100) | NOT NULL | Категория работ |
| index_value | DECIMAL(8,4) | NOT NULL | Коэффициент пересчёта |
| published_at | DATE | NOT NULL | Дата публикации письма Минстроя |

**Indexes:** `(region_code, quarter, work_category)`

---

## 6. Integration Requirements

### 6.1 Cloud.ru Foundation Models (Primary AI)

| Parameter | Value |
|-----------|-------|
| **Purpose** | Генерация AI-смет, распознавание чертежей, AI-подсказки по оптимизации, прогноз бюджета |
| **API** | Cloud.ru Foundation Models API (OpenAI-compatible) |
| **Access** | Через OpenAI-compatible client для unified interface |
| **Models** | Qwen3 (text generation), Vision model (чертежи) |
| **Data sovereignty** | Все данные обрабатываются на территории РФ (Cloud.ru дата-центры) |
| **Rate limits** | По договору с Cloud.ru (minimum 100 RPM) |
| **Latency budget** | < 30 сек для текстовой сметы, < 60 сек для чертежа |
| **Retry policy** | 3 попытки с exponential backoff (1s, 3s, 9s). При исчерпании — fallback на OpenAI |
| **Error handling** | Timeout 90 сек. При ошибке — показать пользователю «AI временно недоступен» с предложением создать смету вручную |

**Prompt architecture:**
- System prompt: роль сметчика, контекст ГЭСН/ФЕР, формат вывода (structured JSON)
- User prompt: описание работ + площадь + регион
- RAG: поиск релевантных расценок из GesnRate по описанию (top-K similarity search)

### 6.2 OpenAI API (Fallback AI)

| Parameter | Value |
|-----------|-------|
| **Purpose** | Fallback при недоступности Cloud.ru |
| **API** | OpenAI API через OpenAI-compatible client |
| **Models** | GPT-4o (text), GPT-4o (vision) |
| **Activation** | Автоматически при 3 последовательных ошибках Cloud.ru |
| **Data considerations** | Не передавать персональные данные (только описания работ и расценки). Логировать использование fallback для compliance reporting. |
| **Cost** | Usage-based, мониторинг через OpenAI-compatible client dashboard |

### 6.3 OpenAI-compatible client (AI Gateway)

| Parameter | Value |
|-----------|-------|
| **Purpose** | Единый интерфейс к множественным AI-провайдерам, routing, fallback, usage tracking |
| **Deployment** | Self-hosted Docker container в compose stack |
| **Configuration** | Provider routing: Cloud.ru (primary, weight 100%) -> OpenAI (fallback). Rate limiting per tenant. Cost tracking per request. |
| **Monitoring** | Dashboard с метриками: latency, cost, error rate per provider |

### 6.4 ЮKassa (Платежи)

| Parameter | Value |
|-----------|-------|
| **Purpose** | Приём платежей за подписки (рекуррентные) и AI-сметы (разовые) |
| **Integration type** | Server-side API v3 |
| **Payment methods** | Банковские карты (Visa, MasterCard, МИР), СБП, ЮMoney |
| **Webhooks** | `payment.succeeded`, `payment.cancelled`, `refund.succeeded` |
| **Security** | HMAC-SHA256 signature verification, IP whitelist (ЮKassa IP ranges), idempotency keys |
| **Testing** | Sandbox environment для разработки и тестирования |
| **PCI DSS** | ЮKassa обеспечивает PCI DSS compliance — карточные данные не проходят через наши серверы (redirect flow) |

### 6.5 SMS/Уведомления

| Parameter | Value |
|-----------|-------|
| **Purpose** | SMS-верификация телефона, OTP при регистрации |
| **Provider** | SMS.ru (primary) или SMSC.ru (fallback) |
| **Integration** | HTTP API |
| **Rate limiting** | Max 3 SMS/номер/час, max 10 SMS/номер/день |
| **Cost** | ~₽2-4 за SMS, бюджет до ₽50K/мес |

### 6.6 S3-совместимое Object Storage

| Parameter | Value |
|-----------|-------|
| **Purpose** | Хранение фото, чертежей, экспортированных PDF/Excel |
| **Provider** | Cloud.ru Object Storage (primary) или MinIO (self-hosted fallback) |
| **API** | S3-compatible (AWS SDK) |
| **Access** | Private ACL + pre-signed URLs (TTL 1 час для просмотра, 15 мин для загрузки) |
| **Lifecycle** | Фото > 2 лет — перемещение в cold storage (Glacier-compatible) |

### 6.7 1С:Бухгалтерия (Future — P2)

| Parameter | Value |
|-----------|-------|
| **Purpose** | Двусторонняя синхронизация: экспорт расходов/актов в 1С, импорт контрагентов из 1С |
| **Integration type** | REST API (1С:Предприятие 8.3 HTTP-сервисы) или CommerceML |
| **Data mapping** | Expense -> Документ «Расход», КС-2 -> Акт выполненных работ, Контрагент -> Brigade/User |
| **Timeline** | P2 (Day 180-360), после валидации спроса |

---

## 7. Security Requirements

### 7.1 Regulatory Compliance

| Requirement | Description |
|-------------|-------------|
| **152-ФЗ «О персональных данных»** | Все персональные данные (ФИО, телефон, email, адрес) хранятся и обрабатываются на территории РФ. Серверы размещены в Cloud.ru (дата-центры в РФ) и/или российские VPS-провайдеры (AdminVPS, HOSTKEY). |
| **Согласие на обработку ПД** | При регистрации пользователь даёт согласие на обработку ПД. Текст согласия доступен по ссылке. Согласие хранится с timestamp и IP-адресом. |
| **Право на удаление** | Пользователь может запросить полное удаление своих данных. Срок исполнения: 30 дней. Каскадное удаление: фото, комментарии, профиль. Аудит-лог сохраняется в обезличенном виде. |
| **Уведомление РКН** | До начала обработки ПД — подача уведомления в Роскомнадзор. Назначение ответственного за обработку ПД. |
| **Данные в AI-моделях** | Через Cloud.ru: данные не покидают РФ. Через OpenAI (fallback): передаются только описания работ и расценки (без ПД). Логирование каждого запроса к fallback-провайдеру. |

### 7.2 Data Sovereignty

| Layer | Implementation |
|-------|---------------|
| **Application servers** | VPS в РФ (AdminVPS/HOSTKEY), Docker Compose |
| **Database** | PostgreSQL на VPS в РФ. Бэкапы — Cloud.ru Object Storage (РФ) |
| **File storage** | Cloud.ru Object Storage (дата-центры РФ) |
| **AI processing** | Cloud.ru Foundation Models (primary). OpenAI используется только как fallback и только для non-PII данных |
| **DNS/CDN** | Российские DNS-провайдеры. CDN — по необходимости (CloudFlare с настройкой Geo-restriction на РФ) |

### 7.3 Authentication & Authorization

| Aspect | Implementation |
|--------|---------------|
| **Password policy** | Минимум 8 символов, 1 заглавная буква, 1 цифра. Проверка по базе утечённых паролей (HaveIBeenPwned API, k-anonymity). |
| **JWT signing** | RS256 (асимметричные ключи). Private key — только на auth server. Public key — на всех API servers. Ротация ключей каждые 90 дней. |
| **Token storage** | Access token: в памяти JS (не в localStorage, не в sessionStorage). Refresh token: httpOnly, Secure, SameSite=Strict cookie. |
| **Session invalidation** | При смене пароля — отзыв всех refresh tokens. При блокировке пользователя — немедленная инвалидация. |
| **RBAC enforcement** | Middleware на каждом API endpoint. Декоратор `@require_role(roles)`. Проверка tenant_id на каждом запросе. НИКОГДА не доверять role из JWT без server-side верификации для критических операций. |
| **Registration endpoint** | Роль `owner` назначается только первому пользователю tenant. Последующие пользователи — только через invite с явным указанием роли owner/manager. Эндпоинт регистрации НЕ принимает поле `role` в request body. |

### 7.4 API Security

| Aspect | Implementation |
|--------|---------------|
| **CORS** | Allow-origin: только `https://app.stroyuprav.ru` и `https://stroyuprav.ru`. Credentials: true. |
| **Rate limiting** | nginx rate limiting + application-level per-tenant limits. Отдельные лимиты для AI endpoints (10 RPM). |
| **Input sanitization** | Server-side validation через Pydantic/Odoo ORM. Parameterized queries (ORM-only, raw SQL запрещён без review). XSS: Content-Security-Policy header. |
| **CSRF** | SameSite cookie + CSRF token для non-GET requests (double-submit cookie pattern). |
| **File upload** | Валидация: MIME type + magic bytes. Запрещённые расширения: .exe, .sh, .bat, .js, .php. Хранение вне webroot (S3). Антивирус-сканирование (ClamAV). |
| **Webhook verification** | ЮKassa: HMAC-SHA256 + timestamp window (5 мин) + IP whitelist. Cloud.ru: по документации провайдера. |

### 7.5 Infrastructure Security

| Aspect | Implementation |
|--------|---------------|
| **Network** | Docker internal network для inter-service communication. Только nginx exposed (ports 80, 443). PostgreSQL, Redis, OpenAI-compatible client — internal only. |
| **TLS** | Let's Encrypt certificates, auto-renewal. TLS 1.3 only (disable TLS 1.0/1.1/1.2 for API). HSTS: max-age=31536000; includeSubDomains. |
| **SSH** | Key-only authentication. Disable root login. Fail2ban. Port non-standard. |
| **Docker** | Non-root containers. Read-only filesystem where possible. Resource limits (CPU, memory). No `--privileged`. |
| **Secrets** | Environment variables via `.env` (not committed). Docker secrets for production. НИКОГДА: hardcoded secrets, fallback values for API keys, secrets in logs. |
| **Dependency scanning** | Dependabot / Safety (Python) для vulnerability scanning. Weekly automated scan. |

---

## Appendix A: Glossary

| Term | Definition |
|------|-----------|
| ГЭСН | Государственные элементные сметные нормы — федеральная база нормативов затрат на строительные работы |
| ФЕР | Федеральные единичные расценки — расценки на строительные работы, привязанные к ГЭСН |
| ТЕР | Территориальные единичные расценки — региональные расценки, учитывающие местные условия |
| КС-2 | Акт о приёмке выполненных работ (форма КС-2) — обязательный документ при сдаче строительных работ |
| КС-3 | Справка о стоимости выполненных работ и затрат (форма КС-3) — финансовый документ, сопровождающий КС-2 |
| 152-ФЗ | Федеральный закон «О персональных данных» — регулирует сбор, хранение и обработку персональных данных на территории РФ |
| РКН | Роскомнадзор — Федеральная служба по надзору в сфере связи, информационных технологий и массовых коммуникаций |
| Индексы Минстроя | Квартальные коэффициенты пересчёта сметной стоимости, публикуемые Министерством строительства РФ |
| Tenant | Организация-арендатор в multi-tenant архитектуре (каждая компания-клиент) |
| RBAC | Role-Based Access Control — управление доступом на основе ролей |
| OpenAI-compatible client | Open-source proxy для унификации API различных AI-провайдеров |
| СБП | Система быстрых платежей — российская система мгновенных переводов через QR-код |

## Appendix B: Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-05-27 | AI-generated | Initial specification based on PRD v1.0 |
