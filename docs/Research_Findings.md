# Research Findings: СтройУправ

## Executive Summary

Рынок ПО для строительства в РФ (₽6.4 млрд, 2024) растёт на 14% YoY с прогнозом ×4 к 2028. Обязательный BIM с 2024, импортозамещение (70% российского ПО) и AI-зрелость (37% компаний используют ИИ) создают окно возможностей для mobile-first ERP с AI-сметчиком. Ниша «российский Odoo для стройки» пуста — 1С:УСО доминирует, но имеет архаичный UI и тяжёлое внедрение.

## Research Objective

Определить жизнеспособность mobile-first ERP для строительства/ремонта в РФ с AI-сметчиком как core feature.

## Methodology

GOAP A* + OODA (DEEP mode). 10 поисковых итераций, 23+ источника, confidence threshold 0.85.

## Market Analysis

### Объёмы рынка
- Строительная отрасль РФ: ₽16.8 трлн (2024) — [Strategy Partners](https://strategy.ru/research/research/obem-rynka-cifrovizacii-stroitelnoj-otrasli-mozhet-vyrasti-v-chetyre-raza-k-2028-godu/)
- Рынок ПО для строительства: ₽6.4 млрд (2024, +14% YoY) — [Strategy Partners](https://strategy.ru/research/research/obem-rynka-cifrovizacii-stroitelnoj-otrasli-mozhet-vyrasti-v-chetyre-raza-k-2028-godu/)
- Глобальный рынок construction management software: $7.67B (2025) → $16.37B (2033), CAGR 10.2% — [Grand View Research](https://www.grandviewresearch.com/industry-analysis/construction-management-software-market-report)
- Рынок ремонта (B2C): ~₽500 млрд к 2027 — [РБК](https://marketing.rbc.ru/articles/14851/)

### Драйверы роста
1. **BIM обязателен** с 2024 (жильё с госфинансированием), с 2025 (ИЖС) — [Cifrastroy](https://cifrastroy.ru/news/chem-zapomnitsja-2024-god-i-chto-zhdet-stroitelnuju-otrasl-v-2025-m)
2. **Импортозамещение**: доля российского ПО ~70% (2024) — [CNews](https://www.cnews.ru/projects/2025/tsifrovizatsiya_stroitelnoj_otrasli)
3. **AI adoption**: 37% стройкомпаний используют ИИ (2025) — [TAdviser](https://www.tadviser.ru/)
4. **Прозрачность = валюта**: 40% заказчиков жалуются на срывы и скрытые доплаты — [Forbes.ru](https://blogs.forbes.ru/2025/12/30/rynok-remonta-i-stroitelstva-cifrovaja-zrelost-doverie-i-novaja-struktura-sprosa/)

## Competitive Landscape

| Competitor | Strengths | Weaknesses | Differentiation от СтройУправ |
|------------|-----------|------------|-------------------------------|
| **1С:ERP УСО 2** | Доминирование в РФ, глубокая бухгалтерия, привычка | Архаичный UI, внедрение 3-12 мес, нет mobile, нет AI | Mobile-first + AI-сметы + внедрение <1 дня |
| **АЛТИУС** | Глубокая отраслевая экспертиза, сметы | Устаревший интерфейс, нет SaaS | SaaS + AI + modern UX |
| **Аспро.Cloud** | Современный UI, облако | Нет ERP-глубины, нет смет | AI-сметы + полный ERP |
| **РемонтCRM** | Специализация на ремонте, мобильность | Узкий функционал, нет AI | AI + ERP-глубина + масштаб |
| **Odoo** | Модульность, $650M ARR, open source | Нет стройки из коробки, плохая поддержка | Отраслевая специализация |
| **Procore** | Лидер ($2B+ ARR), 2M+ users | Нет РФ-специфики, $500/user/мес | Российский рынок + ГЭСН + цена |

## Technology Assessment

### AI для строительства
- **AI в строительстве**: рынок $4.86B (2025) → $22.68B (2032) — [Autodesk](https://www.autodesk.com/blogs/construction/2026-ai-trends-25-experts-share-insights/)
- **ML quantity extraction**: автоматический takeoff из PDF/DWG/IFC — [Autodesk](https://www.autodesk.com/blogs/construction/top-2025-ai-construction-trends-according-to-the-experts/)
- **AI-агенты**: DroneDeploy Safety AI, Progress AI, Inspection AI — [Autodesk](https://www.autodesk.com/blogs/construction/2026-ai-trends-25-experts-share-insights/)
- **Digital twins**: рынок $64.87B (2025) → $155.01B (2030) — [RIB Software](https://www.rib-software.com/en/blogs/construction-technology-trends)

### Cloud.ru Foundation Models
- 20+ моделей (DeepSeek, Qwen3-480B, T-pro-it-2.0) — [Cloud.ru](https://cloud.ru/products/evolution-foundation-models)
- OpenAI-совместимый API — [Cloud.ru Docs](https://cloud.ru/docs/foundation-models/ug/index)
- Pricing: от ₽35/1M input tokens — [Cloud.ru Blog](https://cloud.ru/blog/cloud-ru-delayet-otkrytyye-llm-dostupnee)
- Managed RAG, Fine-tuning, AI Agents — [Cloud.ru](https://cloud.ru/products/evolution-ai-factory)
- Суверенность данных в РФ — [Cloud.ru](https://cloud.ru/products/evolution-foundation-models)

### Odoo как техническая база
- Three-tier architecture: Python + PostgreSQL + OWL/QWeb — [Odoo Docs](https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/01_architecture.html)
- 82+ модулей, модульная архитектура — [odoo.com](https://www.odoo.com)
- Community Edition: LGPL-v3 (open source, можно форкнуть) — [odoo.com/pricing](https://www.odoo.com/pricing)
- Текущая версия: Odoo 19 — [Odoo Docs](https://www.odoo.com/documentation/19.0/)

## User Insights

### Что строители любят в ERP
- «Project Management module is user-friendly, used across all construction sites» — [Capterra](https://www.capterra.com/p/135618/Odoo/reviews/)
- «Integration of accounting with project management gives us real-time budget visibility» — [First Line Software](https://firstlinesoftware.com/blog/odoo-for-construction-project-management/)

### Что ненавидят
- «Все туториалы 5+ лет устарели. Поддержка = менеджер, с которым надо платить чтобы поговорить» — [Trustpilot](https://www.trustpilot.com/review/odoo.com)
- «Каждый вечер свожу Excel, приходит документ за прошлый месяц — и всё пересчитываешь» — [Planfact](https://planfact.io/blog/posts/upravlencheskij-uchet-v-stroitelnoj-kompanii)
- «40% заказчиков жалуются на срывы сроков и скрытые доплаты» — [Forbes.ru](https://blogs.forbes.ru/2025/12/30/rynok-remonta-i-stroitelstva-cifrovaja-zrelost-doverie-i-novaja-struktura-sprosa/)

## Confidence Assessment

- **High confidence:** Размер рынка (₽6.4 млрд), обязательный BIM, Odoo tech stack, Cloud.ru API capabilities
- **Medium confidence:** Unit economics (LTV:CAC, churn), AI accuracy для ГЭСН/ФЕР, конверсия freemium
- **Low confidence:** Реальная готовность ремонтных компаний платить за SaaS, K-factor viral loop

## Sources

1. [Strategy Partners — Рынок цифровизации строительства](https://strategy.ru/research/research/obem-rynka-cifrovizacii-stroitelnoj-otrasli-mozhet-vyrasti-v-chetyre-raza-k-2028-godu/)
2. [Forbes.ru — Рынок ремонта: цифровая зрелость](https://blogs.forbes.ru/2025/12/30/rynok-remonta-i-stroitelstva-cifrovaja-zrelost-doverie-i-novaja-struktura-sprosa/)
3. [CNews — Цифровизация строительной отрасли 2025](https://www.cnews.ru/projects/2025/tsifrovizatsiya_stroitelnoj_otrasli)
4. [Grand View Research — Construction Management Software Market](https://www.grandviewresearch.com/industry-analysis/construction-management-software-market-report)
5. [Autodesk — AI Construction Trends 2026](https://www.autodesk.com/blogs/construction/2026-ai-trends-25-experts-share-insights/)
6. [TechCrunch — Odoo $5.26B valuation](https://techcrunch.com/2024/11/20/riding-high-on-open-source-erp-odoo-raises-527m-via-secondaries-lifting-its-valuation-to-5-26b/)
7. [Cloud.ru — Evolution Foundation Models](https://cloud.ru/products/evolution-foundation-models)
8. [Cloud.ru — Pricing for open LLM models](https://cloud.ru/blog/cloud-ru-delayet-otkrytyye-llm-dostupnee)
9. [Odoo Docs — Architecture Overview](https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/01_architecture.html)
10. [РБК — Рынок ремонта ₽500 млрд](https://marketing.rbc.ru/articles/14851/)
11. [Capterra — Odoo Reviews](https://www.capterra.com/p/135618/Odoo/reviews/)
12. [Cifrastroy — Итоги 2024](https://cifrastroy.ru/news/chem-zapomnitsja-2024-god-i-chto-zhdet-stroitelnuju-otrasl-v-2025-m)
