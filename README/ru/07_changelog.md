# Журнал изменений

## v0.1.0-scaffold (2026-05-27)

Начальный скаффолд проекта. Docker-инфраструктура и документация.

### Добавлено

- Docker Compose конфигурация: 9 сервисов (nginx, odoo, fastapi-ai, postgres, redis, celery-worker, celery-beat, minio, elasticsearch)
- Файл `.env.example` с описанием всех переменных окружения
- SPARC-документация: PRD, Specification, Architecture, Pseudocode, Refinement, Completion
- Claude Code toolkit (.claude/): команды, агенты, правила, навыки, хуки

### MVP-фичи (запланированы)

| ID | Фича | Статус |
|----|-------|--------|
| F01 | AI-сметчик по ГЭСН/ФЕР | Запланирована |
| F02 | Dashboard объектов | Запланирована |
| F03 | Управление задачами | Запланирована |
| F04 | Фотофиксация | Запланирована |
| F05 | Бюджет real-time | Запланирована |
| F06 | Mobile App (PWA) | Запланирована |
| F07 | Onboarding quiz | Запланирована |
| F08 | Auth & Billing | Запланирована |
