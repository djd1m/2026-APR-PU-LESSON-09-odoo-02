# Validation Report: AI-Estimator (F01)

**Date:** 2026-05-27
**Validator:** requirements-validator
**Input:** 5 SPARC documents (01-05)

---

## 1. INVEST Scoring

| Criterion | Score (0-100) | Notes |
|-----------|:------------:|-------|
| **I**ndependent | 85 | Self-contained feature with clear API boundaries. Dependency on Auth/Billing (F08) for usage tracking, but can operate standalone with hardcoded limits for dev. |
| **N**egotiable | 80 | Core pipeline is fixed (ГЭСН lookup + AI), but optimization suggestions, export formats, and accuracy thresholds are negotiable. Drawing support could be deferred to P0.5. |
| **V**aluable | 95 | Primary value proposition ("Смета за 5 минут"). Lead magnet for freemium. Directly generates revenue via usage-based billing. |
| **E**stimable | 75 | AI accuracy is inherently uncertain. Pipeline steps are well-defined with clear SLAs. ГЭСН data import effort depends on source format quality. Estimated: 3-4 weeks for MVP (text only), +2 weeks for drawing support. |
| **S**mall | 65 | Feature is large (text + drawing + optimization + export + billing). Recommendation: split into sub-features for incremental delivery (see section 4). |
| **T**estable | 80 | Clear acceptance criteria with numeric thresholds. AI accuracy benchmarking defined (50 reference estimates). Edge cases documented. Decimal arithmetic fully testable. |

**INVEST Average: 80**

---

## 2. SMART Scoring

| Criterion | Score (0-100) | Notes |
|-----------|:------------:|-------|
| **S**pecific | 90 | API contracts defined with request/response schemas. Data model specified (PostgreSQL + ES). All money fields explicitly Decimal. |
| **M**easurable | 85 | SLAs: <60s text, <90s drawing, >=85% area accuracy, <500ms search. Usage quota metrics defined. AI accuracy benchmarks with test dataset. |
| **A**chievable | 70 | Cloud.ru AI capabilities assumed but not validated. ГЭСН data availability from ФСНБ assumed. 85% area recognition is ambitious for V1. Elasticsearch KNN search for 100K docs is proven technology. |
| **R**elevant | 95 | Directly serves primary persona (Алексей). Core monetization feature. Aligned with product vision "Смета за 5 минут по ГЭСН/ФЕР". |
| **T**ime-bound | 75 | Timeline: Day 1-30 for AI-сметчик MVP. 3-4 weeks realistic for text pipeline. Drawing parser adds 2 weeks. No explicit milestones within the 30-day window. |

**SMART Average: 83**

---

## 3. Dimension Scores

| Dimension | Score | Details |
|-----------|:-----:|---------|
| Completeness | 85 | All user stories have AC. API contracts defined. Data model complete. Missing: error response schemas, pagination for estimate history. |
| Consistency | 90 | Money = Decimal throughout (specification, pseudocode, architecture). Security rules aligned with project-level security.md. Coding style follows su_ prefix convention. |
| Clarity | 85 | Pseudocode is readable with clear step numbering. Architecture diagram shows all components. Edge cases enumerated with specific handling. |
| Testability | 80 | Unit/integration/performance test strategy defined. AI accuracy benchmarks with 50-estimate dataset. Missing: specific test data fixtures in docs. |
| Security | 90 | Prompt injection mitigation documented. File upload validation (MIME + magic bytes). Tenant isolation. HMAC webhook verification. No hardcoded secrets. 152-ФЗ compliance (Cloud.ru only). |
| Feasibility | 70 | Cloud.ru AI API assumed OpenAI-compatible (needs validation). ГЭСН data format assumed XML (needs confirmation). 85% drawing accuracy is stretch goal. Elasticsearch KNN is proven. |

---

## 4. Findings

### Blockers

None.

### High Severity

| # | Finding | Recommendation |
|---|---------|----------------|
| H1 | **ГЭСН data source not validated.** Spec assumes XML from ФСНБ but actual format and access method unconfirmed. If data is only available in proprietary format, import pipeline needs rework. | Validate ФСНБ data access before sprint start. Confirm XML schema or identify alternative source. |
| H2 | **Cloud.ru API compatibility untested.** Spec assumes OpenAI-compatible SDK works with Cloud.ru. Function calling, JSON mode, vision API may differ. | Create spike task: test Cloud.ru API with OpenAI SDK for text completion, JSON mode, and vision endpoint. 1-2 days. |
| H3 | **Drawing accuracy target (85%) may be unrealistic for V1.** Vision AI area recognition depends heavily on drawing quality and style. No baseline data. | Collect 20 sample drawings from target users. Run manual accuracy test before committing to 85% target. Consider launching text-only first. |

### Medium Severity

| # | Finding | Recommendation |
|---|---------|----------------|
| M1 | **No error response schemas defined.** API contracts show success responses but not structured error formats. | Add standard error schema: `{"error": {"code": "QUOTA_EXCEEDED", "message": "...", "details": {}}}` |
| M2 | **Market benchmark data source unclear.** Optimization algorithm requires market benchmarks but source is listed as "scraped/manual". No import pipeline defined. | Define initial benchmark dataset. Even a small curated set (500 entries) enables optimization feature launch. |
| M3 | **No pagination for estimate history (FR-EST-08).** User story mentions "all generated estimates" but no API endpoint for listing with pagination. | Add `GET /api/v1/estimates?page=1&per_page=20&status=completed` |
| M4 | **Celery task result expiry not specified.** If user polls status after result expires, they get a "task not found" error. | Set Celery result backend TTL to 24h. After completion, estimate is in DB regardless. |
| M5 | **Feature size is large.** INVEST "Small" scored 65. Risk of scope creep and delayed delivery. | Split into 3 increments: (1) Text estimate + export (2 weeks), (2) Drawing support (2 weeks), (3) Optimization + usage billing (1 week). |

### Low Severity

| # | Finding | Recommendation |
|---|---------|----------------|
| L1 | Embedding model (bge-m3) dimension size not specified in ES mapping. | Specify 1024 dimensions for bge-m3 in index mapping. |
| L2 | No rate limiting specified for export endpoint. | Add rate limit: 30 exports/min per user (lower priority than generation endpoint). |
| L3 | No mention of estimate deletion or archival policy. | Add soft-delete with 90-day retention, then archive to cold storage. |
| L4 | Optimization suggestions are fire-and-forget (async). No notification when ready. | Add WebSocket or polling mechanism for suggestion readiness. Low priority -- suggestions typically complete in <5s. |

---

## 5. Verdict

| Metric | Value |
|--------|-------|
| INVEST Average | 80 |
| SMART Average | 83 |
| Overall Average | **81.5** |
| Blockers | 0 |
| High findings | 3 |
| Medium findings | 5 |
| Low findings | 4 |

### Verdict: READY

Average score 81.5 >= 70, no blockers. High findings (H1-H3) are validation tasks that should be executed as spike tasks in sprint 0, but do not block implementation planning.

**Recommendation:** Proceed to Phase 3 (IMPLEMENT). Address H1-H3 as parallel spike tasks in the first 2-3 days. Consider M5's incremental delivery approach: ship text-only estimate first, add drawing support in second increment.
