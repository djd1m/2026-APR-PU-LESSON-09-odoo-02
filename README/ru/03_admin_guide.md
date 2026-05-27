# Руководство администратора

## Деплой на VPS

### Требования к серверу

- Ubuntu 22.04 / Debian 12
- 4+ vCPU, 16 ГБ RAM, 100 ГБ SSD
- Домен с A-записью, указывающей на IP сервера
- Рекомендуемые хостинги: AdminVPS, HOSTKEY (российские ЦОД, 152-ФЗ)

### Установка Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

### Развёртывание

```bash
git clone https://github.com/your-org/stroyuprav.git /opt/stroyuprav
cd /opt/stroyuprav
cp .env.example .env
# Заполните .env реальными значениями (см. Быстрый старт)
docker compose up -d
```

## SSL-сертификат (Let's Encrypt)

### Первоначальная выдача

```bash
# Убедитесь, что домен указывает на IP сервера
docker compose exec nginx certbot certonly \
  --webroot -w /var/www/certbot \
  -d yourdomain.ru \
  --agree-tos \
  -m admin@yourdomain.ru
```

### Автопродление

Добавьте в crontab:

```bash
0 3 * * * cd /opt/stroyuprav && docker compose exec nginx certbot renew --quiet && docker compose exec nginx nginx -s reload
```

## Резервное копирование PostgreSQL

### Ручной бекап

```bash
docker compose exec postgres pg_dump -U stroiuprav stroiuprav | gzip > /opt/stroyuprav/backups/backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Автоматические бекапы (ежедневно в 2:00)

Добавьте в crontab:

```bash
0 2 * * * docker compose -f /opt/stroyuprav/docker-compose.yml exec -T postgres pg_dump -U stroiuprav stroiuprav | gzip > /opt/stroyuprav/backups/backup_$(date +\%Y\%m\%d).sql.gz
```

### Восстановление из бекапа

```bash
gunzip < /opt/stroyuprav/backups/backup_20260101.sql.gz | docker compose exec -T postgres psql -U stroiuprav stroiuprav
```

### Хранение бекапов

Рекомендуется хранить минимум 7 ежедневных + 4 еженедельных бекапа. Удаление старых:

```bash
find /opt/stroyuprav/backups -name "*.sql.gz" -mtime +30 -delete
```

## Мониторинг

Стек мониторинга: Prometheus + Grafana + Loki.

- **Prometheus** -- сбор метрик (CPU, RAM, диск, HTTP-ответы)
- **Grafana** -- дашборды и алерты
- **Loki + Promtail** -- централизованные логи

Просмотр логов:

```bash
# Все сервисы
docker compose logs -f

# Конкретный сервис
docker compose logs -f odoo
docker compose logs -f fastapi-ai
docker compose logs -f postgres
```

## Обновление

```bash
cd /opt/stroyuprav
git pull origin main
docker compose build
docker compose up -d
```

При обновлении базы данных Odoo автоматически выполнит миграции.

## Управление пользователями

Управление пользователями осуществляется через веб-интерфейс Odoo:

1. Войдите как администратор.
2. Перейдите в **Настройки -> Пользователи**.
3. Создайте нового пользователя, назначьте роль:
   - **admin** -- полный доступ
   - **manager** -- управление объектами, задачами, бюджетами
   - **worker** -- просмотр задач, фотофиксация
   - **client** -- портал заказчика (только просмотр)

Роли контролируются RBAC. Роль нельзя назначить через API регистрации (защита от повышения привилегий).

## Настройка Cloud.ru API

1. Зарегистрируйтесь на [cloud.ru](https://cloud.ru) и создайте проект.
2. Получите API-ключ в разделе Foundation Models.
3. Укажите в `.env`:

```dotenv
CLOUDRU_API_KEY=ваш-ключ
CLOUDRU_API_BASE=https://api.cloud.ru/v1
CLOUDRU_MODEL=qwen3-72b
```

Доступные модели: Qwen3-Coder-480B, DeepSeek-V3, T-pro-it-2.0. При смене модели перезапустите fastapi-ai:

```bash
docker compose restart fastapi-ai celery-worker
```

## Настройка ЮKassa

1. Зарегистрируйте магазин на [yookassa.ru](https://yookassa.ru).
2. Получите Shop ID и секретный ключ в настройках магазина.
3. Настройте вебхук: URL -- `https://yourdomain.ru/api/billing/webhook`, события -- `payment.succeeded`, `payment.canceled`, `refund.succeeded`.
4. Сгенерируйте секрет для HMAC-верификации вебхуков.
5. Укажите в `.env`:

```dotenv
YUKASSA_SHOP_ID=ваш-shop-id
YUKASSA_SECRET_KEY=ваш-секретный-ключ
YUKASSA_WEBHOOK_SECRET=ваш-webhook-секрет
```

6. Перезапустите Odoo:

```bash
docker compose restart odoo
```

Система принимает: банковские карты, СБП, ЮMoney. Поддерживаются рекуррентные платежи.
