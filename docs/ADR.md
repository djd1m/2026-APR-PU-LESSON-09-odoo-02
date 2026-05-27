# Architecture Decision Records (ADR)

## ADR-001: Odoo Community Fork как база backend

**Статус:** Accepted
**Дата:** 2026-05-27
**Контекст:** Нужна ERP-платформа с модульной архитектурой, ORM, workflow engine, RBAC, multi-tenancy.
**Решение:** Fork Odoo 17 Community Edition (LGPL-v3) вместо custom backend.
**Обоснование:**
- Time-to-market: 30 дней vs 90+ дней на custom
- ORM, views, security, workflow — из коробки
- 82+ модулей для расширения
- 13M+ users — проверенная масштабируемость
- LGPL-v3 — можно форкнуть без ограничений
**Риски:** OWL frontend ограничен; привязка к Odoo release cycle.
**Альтернативы:** Django + DRF (больше гибкости, дольше), FastAPI-only (нет ERP-функций).

---

## ADR-002: Cloud.ru Foundation Models как primary AI provider

**Статус:** Accepted
**Дата:** 2026-05-27
**Контекст:** AI-сметчик требует LLM для генерации смет. Данные (сметы, проекты) содержат коммерческую информацию.
**Решение:** Cloud.ru Foundation Models (primary) + OpenAI (fallback). OpenAI-compatible API, переключение через env var `AI_BASE_URL`.
**Обоснование:**
- Суверенность данных в РФ (152-ФЗ)
- Цена: ₽35-70/1M tokens vs $2.50-10/1M у OpenAI (10-50× дешевле)
- OpenAI-compatible API — zero code change при переключении
- Managed RAG и Fine-tuning для ГЭСН/ФЕР
- 20+ моделей (Qwen3, DeepSeek, T-pro)
**Риски:** Менее зрелый API, меньше моделей чем у OpenAI.
**Альтернативы:** Только OpenAI (данные уходят за рубеж), YandexGPT (менее гибкий API), self-hosted (дорого).

---

## ADR-003: Без LiteLLM proxy — прямой OpenAI SDK

**Статус:** Accepted
**Дата:** 2026-05-27
**Контекст:** Первоначально планировался LiteLLM proxy для маршрутизации между AI-провайдерами.
**Решение:** Убрать LiteLLM. Использовать OpenAI SDK напрямую с `base_url` из env var.
**Обоснование:**
- Cloud.ru и OpenAI оба предоставляют идентичный OpenAI-compatible API
- LiteLLM = лишний сервис в Docker Compose (latency, memory, failure point)
- Переключение провайдера = 1 env var (`AI_BASE_URL`)
- LiteLLM нужен при 10+ провайдерах, у нас два с одинаковым API
**Риски:** Нет автоматического failover (нужна ручная логика retry в ai_client.py).

---

## ADR-004: JWT в httpOnly cookies, не localStorage

**Статус:** Accepted
**Дата:** 2026-05-27
**Контекст:** Нужно безопасное хранение JWT токенов в браузере.
**Решение:** JWT access token (15 мин) + refresh token (7 дней) в httpOnly cookies с `Secure=True`, `SameSite=Strict`.
**Обоснование:**
- localStorage уязвим к XSS — любой JS-скрипт может украсть токен
- httpOnly cookies недоступны из JavaScript
- SameSite=Strict предотвращает CSRF
- Это #1 security finding в прошлых проектах (outschool-01)
**Риски:** Сложнее работа с API из mobile apps (нужен отдельный flow).
**Альтернативы:** localStorage (XSS-уязвимость — REJECTED), sessionStorage (теряется при закрытии вкладки).

---

## ADR-005: HS256 для JWT (MVP), миграция на RS256 для production

**Статус:** Accepted (MVP), Planned migration
**Дата:** 2026-05-27
**Контекст:** Спецификация требует RS256, но это усложняет MVP (key management, rotation).
**Решение:** HS256 для MVP с обязательным SECRET_KEY из env var (crash if missing). TODO: миграция на RS256 перед production.
**Обоснование:**
- HS256 проще (один shared secret vs key pair)
- Секрет только из env var, без fallbacks — достаточно безопасно для MVP
- python-jose поддерживает оба алгоритма — миграция = смена 1 строки
**Риски:** HS256 не позволяет проверять токены без знания секрета (нельзя дать публичный ключ сторонним сервисам).

---

## ADR-006: Decimal для денег, никогда Float

**Статус:** Accepted (mandatory)
**Дата:** 2026-05-27
**Контекст:** Сметы содержат суммы в миллионах рублей. Float(0.1 + 0.2) = 0.30000000000000004.
**Решение:** Odoo `fields.Monetary` (Decimal внутренне), Python `Decimal(str(value))`, PostgreSQL `DECIMAL(15,2)`.
**Обоснование:**
- На смете ₽3М ошибка Float = тысячи рублей
- Это finding из Phase 4 review прошлого проекта (outschool-01)
- Odoo Monetary использует Decimal автоматически
- FastAPI/Pydantic: `Decimal` в схемах
**Риски:** Decimal медленнее Float в вычислениях (~3×), но для смет это несущественно.

---

## ADR-007: HMAC-SHA256 для ЮKassa webhooks

**Статус:** Accepted (mandatory)
**Дата:** 2026-05-27
**Контекст:** ЮKassa отправляет webhook при платежах. Без проверки подписи любой может подделать платёж.
**Решение:** HMAC-SHA256 с `hmac.compare_digest()` (constant-time). Crash on startup если `YUKASSA_WEBHOOK_SECRET` не задан.
**Обоснование:**
- `==` для сравнения строк уязвим к timing attack
- `hmac.compare_digest()` — constant-time comparison
- Без HMAC = подделка платежей = критическая уязвимость
- Это finding из Phase 4 review прошлого проекта
**Риски:** Нет (standard practice).

---

## ADR-008: PostgreSQL 16 как единственная СУБД

**Статус:** Accepted
**Дата:** 2026-05-27
**Контекст:** Odoo поддерживает только PostgreSQL. Нужна ACID для финансовых транзакций.
**Решение:** PostgreSQL 16 с JSONB для гибких полей, materialized views для dashboard.
**Обоснование:**
- Odoo-совместимость (единственная поддерживаемая СУБД)
- ACID для платежей и подписок
- JSONB для metadata смет (гибкая структура)
- Full-text search для русского языка (pg_trgm)
- Mature, battle-tested
**Альтернативы:** MongoDB (нет Odoo-совместимости), MySQL (нет JSONB).

---

## ADR-009: Docker Compose deploy (не Kubernetes)

**Статус:** Accepted (Y1-Y2)
**Дата:** 2026-05-27
**Контекст:** Деплой на VPS (AdminVPS/HOSTKEY). Команда 8 чел., первые 10K users.
**Решение:** Docker Compose для MVP и Growth фаз. Kubernetes — только при >10K concurrent users.
**Обоснование:**
- Проще: 1 файл vs helm charts + manifests + operators
- Дешевле: 1 VPS vs Kubernetes cluster
- Достаточно для 10K users (vertical scaling)
- Команда 8 чел. — нет DevOps для K8s
**Trigger для миграции:** CPU >70% sustained на максимальном VPS ИЛИ >10K concurrent users.

---

## ADR-010: Роль при регистрации — hardcoded, не из запроса

**Статус:** Accepted (mandatory, security)
**Дата:** 2026-05-27
**Контекст:** При регистрации нового пользователя нужно назначить роль.
**Решение:** Роль `foreman` (или `admin` для владельца компании) HARDCODED в контроллере. Поле `role` в теле запроса **полностью игнорируется**.
**Обоснование:**
- Privilege escalation via `POST /auth/register` с `role: "admin"` — #1 security finding в прошлых проектах
- LLM-генерированный код копирует DTO-поля из спеки без ограничений
- Единственная защита — не принимать роль из запроса вообще
**Риски:** Нет (standard practice). Повышение роли — через admin panel.
