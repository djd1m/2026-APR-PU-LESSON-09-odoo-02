# Быстрый старт

Запуск СтройУправ за 5 команд.

## Предварительные требования

- Docker 24+ и Docker Compose v2
- 8 ГБ оперативной памяти (рекомендуется 16 ГБ)
- 20 ГБ свободного места на диске
- API-ключ Cloud.ru (или OpenAI как fallback)
- Учетная запись ЮKassa (для приёма платежей)

## Установка

### 1. Клонируйте репозиторий

```bash
git clone https://github.com/your-org/stroyuprav.git
cd stroyuprav
```

### 2. Скопируйте файл окружения

```bash
cp .env.example .env
```

### 3. Заполните переменные окружения

Откройте `.env` и укажите реальные значения:

```dotenv
# Обязательно замените:
DB_PASSWORD=надёжный-пароль-базы-данных
SECRET_KEY=случайная-строка-64-символа

# AI-провайдер (основной -- Cloud.ru)
CLOUDRU_API_KEY=ваш-ключ-cloud-ru
CLOUDRU_API_BASE=https://api.cloud.ru/v1
CLOUDRU_MODEL=qwen3-72b

# AI-провайдер (резервный -- OpenAI)
OPENAI_API_KEY=ваш-ключ-openai

# Хранилище (MinIO)
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=надёжный-пароль-minio
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=надёжный-пароль-minio

# Платежи (ЮKassa)
YUKASSA_SHOP_ID=ваш-shop-id
YUKASSA_SECRET_KEY=ваш-секретный-ключ
YUKASSA_WEBHOOK_SECRET=ваш-webhook-секрет
```

### 4. Запустите все сервисы

```bash
docker compose up -d
```

Поднимутся 9 контейнеров: nginx, odoo, fastapi-ai, postgres, redis, celery-worker, celery-beat, minio, elasticsearch.

### 5. Откройте в браузере

| Сервис | URL |
|--------|-----|
| ERP (Odoo) | http://localhost (через nginx) |
| AI API | http://localhost/api/ |
| MinIO Console | http://localhost:9001 |

## Проверка работоспособности

```bash
# Статус контейнеров
docker compose ps

# Логи (все сервисы)
docker compose logs -f

# Логи конкретного сервиса
docker compose logs -f odoo
docker compose logs -f fastapi-ai
```

## Остановка

```bash
docker compose down
```

Для удаления данных (volumes):

```bash
docker compose down -v
```
