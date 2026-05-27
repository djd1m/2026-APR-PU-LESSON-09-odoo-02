# Устранение неполадок

## Docker Compose не поднимается

**Симптом:** `docker compose up -d` завершается с ошибкой или контейнеры перезапускаются.

**Диагностика:**
```bash
docker compose ps
docker compose logs
```

**Частые причины:**

| Проблема | Решение |
|----------|---------|
| Порт 80/443 занят | Остановите другой веб-сервер: `sudo systemctl stop nginx` или `sudo systemctl stop apache2` |
| Не хватает RAM | Минимум 8 ГБ. Elasticsearch один требует 2 ГБ. Проверьте: `free -h` |
| `.env` не заполнен | Убедитесь, что `cp .env.example .env` выполнен и все значения заменены |
| Docker не запущен | `sudo systemctl start docker` |
| Старая версия Docker Compose | Нужен Docker Compose v2. Проверьте: `docker compose version` |

## PostgreSQL не запускается

**Симптом:** контейнер `postgres` в статусе `unhealthy` или `restarting`.

```bash
docker compose logs postgres
```

**Частые причины:**
- `DB_PASSWORD` в `.env` содержит спецсимволы без экранирования
- Повреждены данные volume: `docker compose down -v` и пересоздайте (данные будут потеряны)
- Недостаточно места на диске: `df -h`

## Odoo не видит модули

**Симптом:** модули СтройУправ не отображаются в списке приложений Odoo.

**Проверьте:**
1. Директория `custom-addons/` примонтирована: `docker compose exec odoo ls /mnt/extra-addons`
2. В каждом модуле есть файл `__manifest__.py`
3. Обновите список модулей: в Odoo перейдите в "Приложения" и нажмите "Обновить список приложений"
4. Перезапустите Odoo: `docker compose restart odoo`

## AI-сметы не генерируются

**Симптом:** запрос на генерацию сметы зависает или возвращает ошибку.

**Проверьте:**

1. **API-ключ:** убедитесь, что `CLOUDRU_API_KEY` в `.env` корректен
   ```bash
   docker compose exec fastapi-ai env | grep CLOUDRU
   ```

2. **Доступность AI-провайдера:**
   ```bash
   docker compose exec fastapi-ai curl -s https://api.cloud.ru/v1/models
   ```

3. **Логи FastAPI:**
   ```bash
   docker compose logs fastapi-ai | tail -50
   ```

4. **Celery-worker запущен:** AI-генерация выполняется асинхронно через Celery
   ```bash
   docker compose ps celery-worker
   docker compose logs celery-worker | tail -20
   ```

5. **Redis доступен:**
   ```bash
   docker compose exec redis redis-cli ping
   # Должно вернуть: PONG
   ```

6. **Elasticsearch доступен (для поиска ГЭСН/ФЕР):**
   ```bash
   docker compose exec elasticsearch curl -s http://localhost:9200/_cluster/health
   ```

## Фото не загружаются

**Симптом:** при загрузке фото ошибка или фото не отображается.

**Проверьте:**

1. **MinIO запущен:**
   ```bash
   docker compose ps minio
   ```

2. **Bucket создан:**
   ```bash
   docker compose exec minio mc ls local/stroiuprav
   ```
   Если bucket не существует, создайте:
   ```bash
   docker compose exec minio mc mb local/stroiuprav
   ```

3. **Ключи доступа:** сверьте `S3_ACCESS_KEY` и `S3_SECRET_KEY` в `.env` с `MINIO_ROOT_USER` и `MINIO_ROOT_PASSWORD`

4. **Размер файла:** максимум 20 МБ. Проверьте формат: только JPEG и PNG.

5. **Логи Odoo:**
   ```bash
   docker compose logs odoo | grep -i "minio\|s3\|upload"
   ```

## Вебхуки ЮKassa не работают

**Симптом:** платежи проходят в ЮKassa, но статус в системе не обновляется.

**Проверьте:**
1. Вебхук в настройках ЮKassa указывает на `https://yourdomain.ru/api/billing/webhook`
2. SSL-сертификат валидный (ЮKassa не отправляет на HTTP)
3. `YUKASSA_WEBHOOK_SECRET` совпадает с секретом в настройках магазина
4. Nginx проксирует `/api/billing/webhook` на Odoo

```bash
docker compose logs odoo | grep -i "webhook\|yukassa"
```

## Высокое потребление памяти

Рекомендуемые лимиты и что отключить при нехватке RAM:

| Сервис | RAM | Можно ли отключить |
|--------|-----|--------------------|
| elasticsearch | 2 ГБ | Нет (нужен для ГЭСН/ФЕР) |
| odoo | 4 ГБ | Нет |
| fastapi-ai | 2 ГБ | Нет |
| postgres | 2 ГБ | Нет |
| celery-worker | 2 ГБ | Временно (сметы не будут генерироваться) |

Для серверов с 8 ГБ RAM уменьшите лимиты ES:
```yaml
# docker-compose.yml -> elasticsearch -> environment
- "ES_JAVA_OPTS=-Xms512m -Xmx512m"
```
