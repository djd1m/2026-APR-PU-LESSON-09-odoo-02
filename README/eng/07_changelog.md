# Changelog

All notable changes to the StroyUprav project are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.1.0-scaffold] - 2026-05-27

### Added

- **Project scaffold** -- Docker Compose configuration with 9 services:
  - `nginx` (reverse proxy, SSL termination)
  - `odoo` (ERP backend, Python 3.12 + Odoo 17 ORM)
  - `fastapi-ai` (AI service, Python 3.12 + FastAPI)
  - `postgres` (PostgreSQL 16, primary database)
  - `redis` (Redis 7, cache + Celery broker)
  - `celery-worker` (async task processing)
  - `celery-beat` (periodic task scheduler)
  - `minio` (S3-compatible object storage)
  - `elasticsearch` (GESN/FER full-text search, 200K+ rates)

- **SPARC documentation** -- full set of architectural documents:
  - Product Requirements Document (PRD)
  - Specification
  - Pseudocode
  - Architecture
  - Refinement
  - Completion

- **Phase 0 product discovery** -- market research and business analysis:
  - Intelligence fact sheet (Module 1)
  - Product and customer analysis (Module 2)
  - Customer journey mapping (Module 2.5)
  - Market and competition analysis (Module 3)
  - Business and finance model (Module 4)
  - Growth engine strategy (Module 5)
  - Go-to-market playbook (Module 6)

- **Feature specifications** (SPARC docs for each MVP feature):
  - F01: AI Estimator (AI-driven cost estimation per GESN/FER)
  - F02: Project Dashboard (real-time progress and budget)
  - F03: Task Management (statuses, crews, dependencies)
  - F04: Photo Reports (geotagged photos, S3 storage)
  - F05: Real-time Budget (actual vs. planned, AI alerts)
  - F06: Mobile PWA (offline-first, camera, push)
  - F07: Onboarding Quiz (4-question personalization)
  - F08: Auth and Billing (JWT, YuKassa subscriptions)

- **Validation reports** -- requirements validation for all features

- **Review reports** -- Phase 4 security and quality reviews for all features

- **Claude Code toolkit** -- development automation:
  - Commands: replicate, feature, plan, go, run, deploy, docs
  - Agents: planner, code-reviewer, architect
  - Rules: git workflow, security, coding style, feature lifecycle
  - Hooks: auto-commit for roadmap, insights, and plans

- **Environment configuration** -- `.env.example` with all required variables

- **Documentation** -- English and Russian documentation sets

### Technical Decisions

- **Distributed Monolith** pattern chosen over microservices (team size: 8)
- **Odoo Community Edition** as ERP base (LGPL-v3, modular, built-in ORM)
- **Cloud.ru Foundation Models** as primary AI (data residency in Russia, 152-FZ)
- **OpenAI** as AI fallback (resilience, A/B testing)
- **YuKassa** for payments (Russian payment gateway, SBP support)
- **VPS deployment** on Russian hosting (AdminVPS/HOSTKEY)

---

## Planned Releases

| Version | Target | Key Features |
|---------|--------|-------------|
| 0.2.0 | Day 30 | AI Estimator MVP + Project Dashboard + Landing page |
| 0.3.0 | Day 60 | Mobile PWA + KS-2/KS-3 generation + first 10 clients |
| 0.4.0 | Day 90 | Billing + Client Portal + Referral system |
| 1.0.0 | Day 180 | Gantt chart + Marketplace + 1C integration |
