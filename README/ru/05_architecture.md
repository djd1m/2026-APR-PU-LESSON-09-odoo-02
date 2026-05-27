# Архитектура

## Обзор

СтройУправ -- mobile-first ERP для строительства и ремонта, построенный на базе Odoo Community Edition. Архитектурный паттерн -- Distributed Monolith в Monorepo, оркестрированный через Docker Compose.

## Docker-сервисы (9 контейнеров)

| Сервис | Технология | Назначение |
|--------|-----------|------------|
| **nginx** | Nginx Alpine | Reverse proxy, SSL-терминация, статика |
| **odoo** | Python 3.12 + Odoo 17 | ERP-backend: объекты, задачи, бюджеты, фото, биллинг |
| **fastapi-ai** | Python 3.12 + FastAPI | AI-сервис: сметы, парсер чертежей, аналитика |
| **postgres** | PostgreSQL 16 | Основная БД (Odoo-совместимая, JSONB, RLS) |
| **redis** | Redis 7 | Кэш, очередь задач, сессии, rate limiting |
| **celery-worker** | Celery | Фоновые задачи: AI-генерация, PDF-экспорт, уведомления |
| **celery-beat** | Celery Beat | Планировщик периодических задач |
| **minio** | MinIO (S3-compatible) | Хранилище файлов: фото, чертежи, PDF-сметы |
| **elasticsearch** | Elasticsearch 8.13 | Полнотекстовый поиск по ГЭСН/ФЕР (200K+ расценок) |

## Схема взаимодействия

```
Пользователь (браузер / PWA)
        |
    [ Nginx ] -- SSL, роутинг
     /     \
    v       v
 [ Odoo ]  [ FastAPI AI ]
    |    \      |
    v     v     v
 [PostgreSQL] [Redis]
                |
            [Celery Worker]
                |
       +---------+---------+
       |         |         |
    [MinIO]  [Cloud.ru]  [Elasticsearch]
             [OpenAI]
```

## Границы компонентов

- **Odoo Backend** -- единый Python-процесс со всеми бизнес-модулями (addons). Модули: `stroyuprav_estimate`, `stroyuprav_project`, `stroyuprav_task`, `stroyuprav_photo`, `stroyuprav_billing`, `stroyuprav_onboarding`, `stroyuprav_portal`.
- **FastAPI AI Service** -- отдельный контейнер. Общается с Odoo через Internal API. Отдельный runtime для длительных AI-операций.
- **Frontend** -- OWL Framework (нативный Odoo) + PWA Shell для мобильных. Портал заказчика -- React 18 + TypeScript (SPA).
- **Shared state** -- только через PostgreSQL и Redis. Никакого shared memory между контейнерами.

## AI-провайдеры

| Провайдер | Роль | Модели |
|-----------|------|--------|
| Cloud.ru Foundation Models | Основной | Qwen3-Coder-480B, DeepSeek-V3, T-pro-it-2.0 |
| OpenAI | Резервный | GPT-4o |
| Anthropic | Резервный | Claude 3.5 |

Переключение через переменную окружения `CLOUDRU_API_BASE`. Все провайдеры используют OpenAI-compatible API.

## AI-конвейер сметчика

1. **Парсинг ввода** -- текст или чертёж (OCR через Qwen3-VL / GPT-4o fallback)
2. **Классификация работ** -- AI определяет стандартные виды работ
3. **Поиск ГЭСН/ФЕР** -- семантический поиск через Cloud.ru Managed RAG + Elasticsearch
4. **Расчёт стоимости** -- base_rate * quantity * индекс_Минстроя + накладные + прибыль
5. **AI-оптимизация** -- поиск позиций дороже рынка на 10%+
6. **Data flywheel** -- одобренные сметы сохраняются для дообучения модели

## Лимиты ресурсов

| Сервис | RAM | CPU |
|--------|-----|-----|
| odoo | 4 ГБ | 4 |
| fastapi-ai | 2 ГБ | 2 |
| postgres | 2 ГБ | -- |
| celery-worker | 2 ГБ | -- |
| elasticsearch | 2 ГБ | -- |
| redis | 512 МБ | -- |

## Безопасность

- JWT в httpOnly cookies (RS256, access 15 мин, refresh 7 дней)
- HMAC-SHA256 верификация вебхуков ЮKassa + защита от replay (окно 5 мин)
- Row-level security в PostgreSQL для изоляции арендаторов
- Валидация файлов: MIME + magic bytes, лимит 20 МБ, ClamAV
- TLS 1.3, HSTS, CORS whitelist, CSP headers
- 152-ФЗ: персональные данные остаются в РФ (Cloud.ru + VPS в РФ)
