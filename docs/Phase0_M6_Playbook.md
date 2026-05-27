# 🎯 PLAYBOOK SYNTHESIS: СтройУправ — 90-Day Launch Plan
**Режим:** DEEP | **Дата:** 2026-05-27

---

## A. EXECUTIVE SUMMARY

**Что:** Mobile-first ERP для строительства и ремонта (РФ) с AI-сметчиком по ГЭСН/ФЕР

**Для кого:** Ремонтные компании (5-50 чел.) и генподрядчики (50-500 чел.)

**Почему сейчас:**
- BIM/ТИМ обязателен с 2024 → принудительная цифровизация
- Рынок ПО для стройки ×4 к 2028 (₽6.4 → ₽25 млрд)
- Импортозамещение: 70% → 90% российского ПО, Odoo/SAP ушли
- AI-зрелость: 37% стройкомпаний уже используют ИИ

**Дифференциация:** AI-сметы по ГЭСН/ФЕР (ни один конкурент не предлагает) + mobile-first (vs desktop-only 1С) + маркетплейс подрядчиков

**Unit Economics:** LTV:CAC = 5.7:1, payback 3.2 мес, GM 78%

---

## B. 90-DAY PLAN

### Phase 1: Foundation (Дни 1-30)

| # | Задача | Результат | Owner | Статус |
|---|--------|-----------|-------|--------|
| 1 | Техническая архитектура (Odoo fork vs custom) | Architecture Decision Record | CTO | — |
| 2 | AI-сметчик MVP: ГЭСН/ФЕР парсинг + калькулятор | Web-форма: загрузи описание → получи смету | AI Lead | — |
| 3 | Landing page + SEO-основа | Лендинг с AI-демо + 5 SEO-статей | Marketing | — |
| 4 | Базовый dashboard (1-3 объекта) | Web + PWA: объекты, задачи, бюджет | Frontend | — |
| 5 | Database schema + API | PostgreSQL + REST API | Backend | — |
| 6 | CI/CD + Docker | Docker Compose + GitHub Actions | DevOps | — |

**Checkpoint Day 30:** Работающий прототип: AI-смета (web) + dashboard (web+PWA) + лендинг

### Phase 2: Traction (Дни 31-60)

| # | Задача | Результат | Owner | Статус |
|---|--------|-----------|-------|--------|
| 7 | Первые 10 beta-клиентов (ручной outreach) | 10 компаний на бесплатном плане | Founder | — |
| 8 | Мобильное приложение (PWA → native) | iOS + Android базовый функционал | Mobile | — |
| 9 | Фотофиксация + авто-прогресс | Фото с геотегом → авто-обновление прогресса | Backend | — |
| 10 | КС-2/КС-3 генератор | Авто-формирование актов по ГОСТ | Backend | — |
| 11 | Яндекс.Директ запуск | Кампании по SEO-ядру | Marketing | — |
| 12 | Branded сметы (product-led viral) | PDF/link с «Создано в СтройУправ» | Frontend | — |

**Checkpoint Day 60:** 10 beta-клиентов, мобильное приложение, КС-2/КС-3, первые paid leads

### Phase 3: PMF Signal (Дни 61-90)

| # | Задача | Результат | Owner | Статус |
|---|--------|-----------|-------|--------|
| 13 | Платёжная система (ЮKassa) | Подписки + авто-списание | Backend | — |
| 14 | Портал заказчика (view-only) | Заказчик видит прогресс ремонта | Frontend | — |
| 15 | Referral system | Приглашение субподрядчиков + скидки | Backend | — |
| 16 | AI-оптимизация смет | «Электромонтаж на 12% дороже рынка» | AI Lead | — |
| 17 | Первые платящие клиенты (25+) | Trial → paid конверсия | Sales | — |
| 18 | Ретроспектива + unit economics | Реальные CAC, LTV, churn, NPS | Founder | — |

**Checkpoint Day 90:** 25+ платящих клиентов, PMF signal (NPS>30, daily usage, willingness to pay)

---

## C. TECH STACK RECOMMENDATION

| Компонент | Решение | Обоснование |
|-----------|---------|-------------|
| **Backend** | Python (Odoo ORM) / FastAPI | Odoo-совместимость + быстрые AI-эндпоинты |
| **Frontend** | OWL (Odoo) + React (портал) | OWL для ERP-модулей, React для customer-facing |
| **Mobile** | PWA → React Native | PWA для MVP, native для scale |
| **Database** | PostgreSQL | Odoo-стандарт, проверенный на 13M+ users |
| **AI/ML** | Python + LangChain + dual-provider (см. ниже) | AI-сметчик, NLP для чертежей |

### AI Provider Strategy: Dual-Provider (Cloud.ru + Western)

**Основной провайдер (production):** [Cloud.ru Evolution Foundation Models](https://cloud.ru/products/evolution-foundation-models)

| Возможность | Детали | Источник |
|-------------|--------|----------|
| **API** | OpenAI-совместимый API (drop-in замена) | [Cloud.ru Docs](https://cloud.ru/docs/foundation-models/ug/index) |
| **Модели LLM** | 20+ моделей: DeepSeek, Qwen3-480B, Qwen3-Coder-480B, OpenAI gpt-oss-120B, GLM-4.6, T-pro-it-2.0 | [Cloud.ru Catalog](https://cloud.ru/products/evolution-ai-factory/catalog-foundation-models) |
| **Embedding** | 2+ модели (bge-reranker-v2-m3, Qwen3-VL-Reranker-8B) | [Cloud.ru Docs](https://cloud.ru/docs/foundation-models/ug/topics/overview__available__models) |
| **Function Calling** | Поддерживается в ряде моделей | [Cloud.ru Docs](https://cloud.ru/docs/foundation-models/ug/topics/overview__available__models) |
| **RAG** | Evolution Managed RAG — готовый сервис | [Cloud.ru Products](https://cloud.ru/products/evolution-ai-factory) |
| **Fine-tuning** | Evolution ML Finetuning — адаптация под сметные данные ГЭСН/ФЕР | [Cloud.ru Blog](https://cloud.ru/blog/stali-dostupny-instrumenty-cloud-ru-evolution-ai-factory) |
| **AI Agents** | Evolution AI Agents — визуальный редактор агентов на LLM | [Cloud.ru Blog](https://cloud.ru/blog/stali-dostupny-instrumenty-cloud-ru-evolution-ai-factory) |
| **Pricing** | От ₽35/1M input tokens, ₽70/1M output tokens (120B+ моделей) | [Cloud.ru Blog](https://cloud.ru/blog/cloud-ru-delayet-otkrytyye-llm-dostupnee) |
| **Бесплатный доступ** | 16 моделей бесплатно до 31.10.2025 | [Cloud.ru Promo](https://cloud.ru/blog/besplatniy-dostup-k-open-source-llm-modelyam) |
| **Rate Limit** | 15 RPS на API key (можно увеличить через ML Inference) | [Cloud.ru Docs](https://cloud.ru/docs/foundation-models/ug/topics/overview__available__models) |
| **Суверенность** | Данные в РФ, без VPN, без иностранных карт | [Cloud.ru](https://cloud.ru/products/evolution-foundation-models) |

**Fallback-провайдер:** OpenAI / Anthropic (для R&D, бенчмарков, edge-case моделей)

#### Архитектура dual-provider (через LiteLLM gateway)

```
┌──────────────────────────────────────────────┐
│  СтройУправ Backend                          │
│                                              │
│  ┌──────────────┐    ┌─────────────────────┐ │
│  │  AI-сметчик  │───▶│  LiteLLM Gateway    │ │
│  │  (LangChain) │    │  (OpenAI-compatible) │ │
│  └──────────────┘    └───────┬─────────────┘ │
│                              │               │
│              ┌───────────────┼───────────┐   │
│              ▼               ▼           │   │
│  ┌───────────────┐  ┌──────────────┐     │   │
│  │  Cloud.ru     │  │  OpenAI /    │     │   │
│  │  Foundation   │  │  Anthropic   │     │   │
│  │  Models       │  │  (fallback)  │     │   │
│  │  PRIMARY ⭐   │  │  SECONDARY   │     │   │
│  └───────────────┘  └──────────────┘     │   │
│                                          │   │
│  ┌───────────────┐  ┌──────────────┐     │   │
│  │  Cloud.ru     │  │  Cloud.ru    │     │   │
│  │  Managed RAG  │  │  Finetuning  │     │   │
│  │  (ГЭСН/ФЕР)  │  │  (сметы)     │     │   │
│  └───────────────┘  └──────────────┘     │   │
└──────────────────────────────────────────────┘
```

#### Рекомендуемые модели для задач СтройУправ

| Задача | Cloud.ru модель | Fallback | Обоснование |
|--------|----------------|----------|-------------|
| **AI-сметчик** (парсинг чертежей → расчёт) | Qwen3-Coder-480B + fine-tuned на ГЭСН | GPT-4o | Code + math reasoning для сметных расчётов |
| **AI-прогноз задержек** | DeepSeek-V3 | Claude Sonnet | Аналитика временных рядов |
| **AI-подсказки прорабу** | T-pro-it-2.0 (русскоязычная) | GPT-4o-mini | Нужен качественный русский, low-latency |
| **Embedding (поиск по ГЭСН/ФЕР)** | bge-reranker-v2-m3 | text-embedding-3-small | Семантический поиск по нормативной базе |
| **RAG (нормативные документы)** | Cloud.ru Managed RAG | Self-hosted RAG | ГЭСН, ФЕР, ТЕР, индексы Минстроя |
| **OCR/Vision (чертежи)** | Qwen3-VL (vision) | GPT-4o (vision) | Распознавание планов, чертежей |

#### Преимущества Cloud.ru для СтройУправ

1. **Суверенность данных** — строительные сметы и проектная документация остаются в РФ (compliance)
2. **Цена** — ₽35-70/1M tokens vs $2.50-10/1M tokens у OpenAI (в 10-50× дешевле)
3. **Fine-tuning** — можно дообучить модель на реальных сметах ГЭСН/ФЕР без экспорта данных
4. **Managed RAG** — готовый сервис для нормативной базы без своей инфраструктуры
5. **OpenAI-совместимый API** — переключение между Cloud.ru и OpenAI через LiteLLM = 1 строка конфига
| **Search** | Elasticsearch / Meilisearch | Поиск по базе ГЭСН/ФЕР |
| **Storage** | S3-compatible (MinIO) | Фото, чертежи, документы |
| **Queue** | Redis + Celery | Фоновые задачи (AI-генерация смет) |
| **CI/CD** | GitHub Actions + Docker | Стандарт для Odoo-проектов |
| **Hosting** | VPS (AdminVPS/HOSTKEY) | Docker Compose deploy |
| **Payments** | ЮKassa | Российский рынок, рекуррентные платежи |

### Архитектурное решение: Fork Odoo vs Custom

| Критерий | Fork Odoo Community | Custom (Odoo-inspired) |
|----------|:-------------------:|:----------------------:|
| Time-to-market | ⭐⭐⭐⭐⭐ (быстро) | ⭐⭐ (долго) |
| Гибкость UI/UX | ⭐⭐ (OWL ограничен) | ⭐⭐⭐⭐⭐ |
| AI-интеграция | ⭐⭐⭐ (возможно) | ⭐⭐⭐⭐⭐ |
| Модульность | ⭐⭐⭐⭐⭐ (из коробки) | ⭐⭐⭐ (нужно строить) |
| Сообщество | ⭐⭐⭐⭐⭐ | ⭐ |
| **Рекомендация** | **✅ Для MVP** | Для Scale (M12+) |

**Стратегия:** Fork Odoo Community для MVP → постепенная замена frontend на React + добавление AI-модулей.

---

## D. MVP SCOPE (из {CHOSEN_CJM} — 6 экранов)

### Must Have (Day 90)

| Экран CJM | Модули | Приоритет |
|-----------|--------|:---------:|
| Landing | Landing page + AI-demo | P0 |
| Onboarding | Quiz + первый объект за 5 мин | P0 |
| Aha: AI-смета | AI-сметчик по ГЭСН/ФЕР (веб-форма → PDF) | P0 |
| Aha: Dashboard | Dashboard объектов (до 5) + бюджет + прогресс | P0 |
| Core Loop | Задачи бригадам + фотоотчёты + push-уведомления | P1 |
| Paywall | Trial 14 дней → 3 плана + ЮKassa | P1 |

### Nice to Have (Day 90-180)

| Фича | Приоритет |
|------|:---------:|
| Портал заказчика (view-only) | P2 |
| Маркетплейс подрядчиков | P2 |
| Gantt-график | P2 |
| Авто-КС-2/КС-3 | P2 |
| 1С:Бухгалтерия интеграция | P3 |
| BIM-интеграция | P3 |
| Дроны / AI-инспекция | P4 |

---

## E. BS-CHECK (самокритика)

| Claim | BS Level | Reality Check |
|-------|:--------:|---------------|
| «AI-смета за 5 минут с точностью 94%» | 🟡 | 94% — optimistic. Нужна обучающая выборка 10K+ реальных смет. MVP: 70-80% точность, ручная доработка |
| «LTV:CAC 5.7:1» | 🟡 | Прогноз. Реальный CAC может быть 2-3× выше из-за конкуренции за «сметы программа» в Директе |
| «K-factor 0.6-0.9» | 🟡 | Агрессивный. Строительный B2B вирально НЕ распространяется как B2C. Реалистично: 0.3-0.5 |
| «Break-even M20-24» | 🟢 | Достижимо при conservative growth, т.к. SaaS + low COGS |
| «Замена 1С:УСО» | 🔴 | НЕ замена, а дополнение. 1С:Бухгалтерия останется. СтройУправ = операционный слой поверх 1С |
| «200K целевых компаний» | 🟢 | Реалистично для total, но адресуемых (готовых платить за SaaS) — скорее 20-50K |

### Главные риски

| Риск | Вероятность | Impact | Митигация |
|------|:----------:|:------:|-----------|
| AI-сметы <80% точности | Средняя | Высокий | Hybrid: AI-черновик + ручная доработка сметчиком |
| 1С блокирует интеграцию | Низкая | Средний | Open API + CSV-экспорт как fallback |
| CAC > ₽50K | Средняя | Высокий | PLG (бесплатные AI-сметы) как zero-CAC канал |
| Churn > 8% | Средняя | Высокий | Sticky data + портал заказчика + авто-отчёты |
| Фокус расплывётся (ремонт + капстрой + ИЖС) | Высокая | Высокий | **START: только ремонт квартир/офисов** → expand |

---

## F. РЕКОМЕНДОВАННАЯ СТАРТОВАЯ СТРАТЕГИЯ

### Wedge: «Ремонт квартир + AI-сметы»

1. **Не пытаться покрыть весь строительный рынок** — начать с ремонтных компаний (5-50 чел.)
2. **AI-смета = lead magnet** — бесплатно, без регистрации → сбор контактов
3. **Dashboard + фотоотчёты = daily habit** — прораб открывает каждое утро
4. **Портал заказчика = viral** — заказчик видит прогресс → рекомендует друзьям
5. **Expand:** ремонт → ИЖС → коммерческая отделка → капстроительство

### Команда для старта (8 чел.)

| Роль | Кол-во | Приоритет |
|------|:------:|:---------:|
| Founder/CEO + Sales | 1 | P0 |
| CTO / Backend Lead (Python/Odoo) | 1 | P0 |
| Frontend (React + OWL) | 1 | P0 |
| Mobile (React Native) | 1 | P1 |
| AI/ML Engineer | 1 | P0 |
| Designer (UI/UX) | 1 | P1 |
| Content Marketing + SEO | 1 | P1 |
| Customer Success | 1 | P2 |

---

## G. NEXT STEPS (после Phase 0)

```
Phase 0 COMPLETE ✅ → Phase 1: SPARC Documentation (sparc-prd-mini)
                      ↓
                      11 SPARC documents → docs/
                      ↓
                      Phase 2: Validation (requirements-validator)
                      ↓
                      Phase 3: Toolkit Generation (cc-toolkit-generator)
                      ↓
                      Phase 4: Finalize → /start → /feature
```

---

## 📈 Overall Phase 0 Confidence Summary

| Module | Avg Confidence | Artifacts |
|--------|:--------------:|-----------|
| M1: Intelligence | 0.89 | Fact Sheet (34 facts, 30 verified) |
| M2: Product & Customers | 0.85 | JTBD, 3 segments, 12 quotes, 8 micro-trends |
| M2.5: CJM | 0.85 | HTML prototype, 3 variants, chosen A+C (39/50) |
| M3: Market | 0.78 | TAM/SAM/SOM, 7 competitors, Blue Ocean, Game Theory |
| M4: Finance | 0.63 | Unit Economics, P&L, Sensitivity, Fundraising |
| M5: Growth | 0.70 | PLG loop, channels, moats, 90-day plan |
| M6: Playbook | 0.75 | 90-day plan, tech stack, MVP scope, BS-check |
| **OVERALL** | **0.78** | **6 документов + HTML-прототип** |
