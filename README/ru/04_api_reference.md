# Справочник API

Базовый URL: `https://yourdomain.ru`

Все API-запросы, кроме `/health` и `/api/auth/register`, требуют JWT-токен в httpOnly cookie.

## Аутентификация

### POST /api/auth/register

Регистрация нового пользователя.

**Запрос:**
```json
{
  "email": "user@example.com",
  "password": "StrongP@ss123",
  "name": "Иван Иванов",
  "company_name": "ООО СтройМастер",
  "phone": "+79001234567"
}
```

**Ответ (201):**
```json
{
  "id": 42,
  "email": "user@example.com",
  "name": "Иван Иванов",
  "role": "manager"
}
```

Роль назначается автоматически (по умолчанию `manager`). Назначить роль через этот endpoint нельзя.

### POST /api/auth/login

Аутентификация. Возвращает JWT в httpOnly cookie.

**Запрос:**
```json
{
  "email": "user@example.com",
  "password": "StrongP@ss123"
}
```

**Ответ (200):**
```json
{
  "user_id": 42,
  "name": "Иван Иванов",
  "role": "manager"
}
```

Cookies (устанавливаются автоматически):
- `access_token` -- JWT, RS256, срок действия 15 минут
- `refresh_token` -- срок действия 7 дней

### POST /api/auth/refresh

Обновление access-токена. Refresh-токен берётся из cookie.

**Ответ (200):**
```json
{
  "message": "Token refreshed"
}
```

### POST /api/auth/logout

Выход из системы. Удаляет cookies.

**Ответ (200):**
```json
{
  "message": "Logged out"
}
```

## AI-сметы

### POST /api/v1/estimate/generate

Генерация AI-сметы из текстового описания.

**Запрос:**
```json
{
  "project_id": 1,
  "description": "Капитальный ремонт квартиры 65 м2: демонтаж, штукатурка стен, стяжка пола, электрика, сантехника, укладка плитки в санузле",
  "region_code": "77",
  "price_level": "2026-Q1"
}
```

**Ответ (202):**
```json
{
  "estimate_id": 123,
  "status": "processing",
  "message": "Смета генерируется. Ожидаемое время: 30-60 сек."
}
```

### GET /api/v1/estimate/{estimate_id}

Получение готовой сметы.

**Ответ (200):**
```json
{
  "estimate_id": 123,
  "status": "completed",
  "total_cost": 1250000.00,
  "items": [
    {
      "gesn_code": "46-01-001-01",
      "description": "Демонтаж штукатурки стен",
      "unit": "м2",
      "quantity": 180.0,
      "unit_price": 285.50,
      "total": 51390.00,
      "ai_flag": null
    },
    {
      "gesn_code": "15-02-016-01",
      "description": "Штукатурка стен цементным раствором",
      "unit": "м2",
      "quantity": 180.0,
      "unit_price": 650.00,
      "total": 117000.00,
      "ai_flag": "above_market_12%"
    }
  ],
  "ai_suggestions": [
    "Позиция 'Штукатурка стен' на 12% выше среднерыночной. Альтернатива: 15-02-016-03 (гипсовая) -- 570 руб/м2."
  ],
  "created_at": "2026-01-15T10:30:00Z"
}
```

### POST /api/v1/estimate/{estimate_id}/export

Экспорт сметы в PDF или Excel.

**Запрос:**
```json
{
  "format": "pdf"
}
```

**Ответ (200):** Файл (binary).

### POST /api/v1/estimate/from-drawing

Генерация сметы из чертежа (PDF или изображение).

**Запрос:** `multipart/form-data`
- `file` -- PDF или изображение чертежа (до 20 МБ)
- `project_id` -- ID объекта
- `region_code` -- код региона

**Ответ (202):**
```json
{
  "estimate_id": 124,
  "status": "processing",
  "message": "Чертёж распознаётся. Ожидаемое время: 60-120 сек."
}
```

## Проверка здоровья

### GET /health

Проверка состояния системы. Не требует аутентификации.

**Ответ (200):**
```json
{
  "status": "healthy",
  "services": {
    "postgres": "ok",
    "redis": "ok",
    "elasticsearch": "ok",
    "minio": "ok",
    "ai_provider": "ok"
  },
  "version": "0.1.0"
}
```

## Rate Limiting

| Тип пользователя | Лимит |
|-------------------|-------|
| Аутентифицированный | 100 запросов/мин |
| Анонимный | 20 запросов/мин |
| AI-эндпоинты | 10 запросов/мин |

При превышении лимита возвращается `429 Too Many Requests`.

## Коды ошибок

| Код | Описание |
|-----|----------|
| 400 | Некорректный запрос (ошибка валидации) |
| 401 | Не авторизован (токен отсутствует или истёк) |
| 403 | Нет прав доступа |
| 404 | Ресурс не найден |
| 422 | Ошибка обработки (невалидные данные) |
| 429 | Превышен лимит запросов |
| 500 | Внутренняя ошибка сервера |
