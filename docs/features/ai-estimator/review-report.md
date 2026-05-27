# Review Report: AI-Estimator (F01)

**Date:** 2026-05-27
**Reviewer:** brutal-honesty-review (Phase 4)
**Verdict:** NEEDS FIX

---

## Executive Summary

The ai-estimator implementation has a solid foundation -- Decimal arithmetic for money, prompt injection sanitization, structured AI response parsing, and graceful Elasticsearch fallback. However, there are **3 blockers**, **5 high-severity** issues, and several medium/low findings. The implementation covers approximately 40-50% of the specification's API contracts and user stories.

---

## Findings

### BLOCKER (3) -- MUST fix before merge

#### B-01: CORS set to `allow_origins=["*"]` with `allow_credentials=True`

**File:** `services/fastapi-ai/app/main.py:79-83`
**Rule violated:** `security.md` -- "Set CORS to specific origins (not `*`)"

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # <-- wide open
    allow_credentials=True,    # <-- incompatible with "*" per HTTP spec
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Setting `allow_origins=["*"]` with `allow_credentials=True` is both a security vulnerability and technically invalid per the Fetch spec (browsers ignore credentials with wildcard origins). The comment says "configurable via ALLOWED_ORIGINS env var" but that env var is never read. This endpoint accepts financial data -- CORS must be locked to specific origins.

**Fix:** Read `ALLOWED_ORIGINS` from Settings, split by comma, use the resulting list. Remove `allow_origins=["*"]`.

---

#### B-02: No authentication or authorization on any endpoint

**Files:** `services/fastapi-ai/app/routers/estimate.py` (all endpoints)
**Rule violated:** `security.md` -- tenant isolation, RBAC
**Spec violated:** US-05 (usage-based billing requires identity)

All four endpoints (`/generate`, `/optimize`, `/export/pdf`, `/render-pdf`) accept unauthenticated requests. There is:
- No JWT verification
- No tenant_id scoping
- No rate limiting per user/API key
- No usage tracking

Anyone who can reach the service can generate unlimited AI estimates at the operator's expense. The spec requires tenant isolation (`WHERE tenant_id = current_tenant`) and usage-based billing (US-05). Neither exists.

**Fix:** Add authentication middleware (JWT or API key). Scope all operations to authenticated tenant. Implement rate limiting (spec says 10 req/min for AI endpoints, `security.md` says 15 RPS per API key).

---

#### B-03: No rate limiting on AI endpoints

**Files:** All of `services/fastapi-ai/app/`
**Spec violated:** NFR-F01-08 -- "10 req/min для AI endpoints"
**Rule violated:** `security.md` -- "Rate limit AI endpoint (15 RPS per API key)"

There is zero rate limiting. Redis is initialized in `main.py` but never used anywhere. The `celery[redis]` dependency is in `requirements.txt` but Celery is never imported or configured. An unauthenticated attacker can call `/generate` in a loop, racking up Cloud.ru API costs with no throttle.

**Fix:** Implement rate limiting using Redis (already connected). Consider `slowapi` or a custom middleware. The Redis connection is already there -- use it.

---

### HIGH (5) -- Fix in this feature

#### H-01: `/render-pdf` accepts untyped `body: dict` -- no validation

**File:** `services/fastapi-ai/app/routers/estimate.py:217`

```python
@router.post("/render-pdf")
async def render_pdf(body: dict) -> Response:
```

This bypasses Pydantic validation entirely. The body can contain arbitrary keys. There is no length limit on item names (potential memory bomb), no sanitization of company_name/company_inn (injected into PDF), and no limit on number of items. The `ExportRequest` schema exists but is not used here.

**Fix:** Create a proper Pydantic model (e.g., `RenderPdfRequest`) with validated fields. Use it as the parameter type.

---

#### H-02: Odoo model uses `fields.Float` for money-adjacent calculations

**File:** `custom-addons/su_estimate/models/su_estimate.py:38,81`

```python
nds_rate = fields.Float(string='Ставка НДС', default=0.20, digits=(4, 2))
```

And in `_compute_totals`:
```python
nds = subtotal * (estimate.nds_rate or 0.20)
```

The `nds_rate` is Float, and it is multiplied directly with the Monetary `subtotal`. While Odoo's Monetary uses Decimal internally, multiplying by a Python float introduces precision loss. The coding-style rule is explicit: "Money fields: ALWAYS use Monetary -- NEVER Float." The NDS rate participates directly in money calculation, making it money-adjacent.

Additionally, `estimate.nds_rate or 0.20` silently uses `0.20` when `nds_rate` is `0.0`, which means a legitimate 0% NDS rate is impossible to set.

**Fix:** Change `nds_rate` to `fields.Float` with explicit `Decimal` conversion in compute, or store as `fields.Integer` (percentage * 100). Fix the `or 0.20` fallback -- use `if estimate.nds_rate is not False` or a proper default.

---

#### H-03: GESN codes from AI are never validated against a known format

**File:** `services/fastapi-ai/app/services/ai_client.py:151`

```python
"gesn_code": str(it.get("gesn_code", "")),
```

AI models hallucinate GESN codes. The code accepts any string as a GESN code with zero format validation. Real GESN codes follow patterns like `ГЭСНр XX-XX-XXX-XX` or `ФЕР XX-XX-XXX-XX`. When Elasticsearch is unavailable (which is the fallback path), hallucinated codes go straight to the client and into Odoo records with no warning.

The `_generate_with_validation` function in `estimate.py` does validate against ES, but only when ES is available. The fallback path (lines 62-68) has zero validation.

**Fix:** Add regex validation for GESN/FER code format. When a code doesn't match the pattern, flag it with `match_score: 0.0` and add a warning to `ai_suggestions`.

---

#### H-04: `knn_search()` and `find_alternatives()` are dead code

**File:** `services/fastapi-ai/app/services/gesn_search.py:118-175`

Two methods (`knn_search` and `find_alternatives`) are defined in `GesnSearchService` but never called from any router, service, or test. They represent ~60 lines of untested dead code.

The `find_alternatives` method would be needed for US-03 (optimization with alternative GESN/FER codes), but the actual optimization endpoint uses AI hallucination instead of real ES lookups. This means optimization suggestions contain AI-invented alternative codes rather than verified ones from the database.

**Fix:** Either wire these methods into the optimization pipeline (preferred -- use `find_alternatives` for real alternative lookups) or remove them. Do not ship dead code.

---

#### H-05: Spec requires async Celery pipeline, implementation is synchronous

**Spec:** Section 2.1 -- "Асинхронный endpoint -- создаёт задачу Celery, возвращает task_id."
**Spec response:** `202 Accepted` with `task_id` and `poll_url`
**Actual:** Synchronous `200 OK` with inline result

The spec explicitly requires:
1. `input_type` field (text vs drawing) -- missing from `EstimateRequest`
2. Celery task creation with `task_id` return -- not implemented
3. `GET /api/v1/estimate/status/{task_id}` polling endpoint -- not implemented
4. `202 Accepted` response -- returns `200` instead

`celery[redis]` is in `requirements.txt` but never imported. This is a significant architectural deviation from the spec.

**Fix:** Either implement the async Celery pipeline per spec, or update the spec to reflect the synchronous design (if that's an intentional simplification for MVP). Document the decision.

---

### MEDIUM (4) -- Optional fix; create follow-up issue

#### M-01: US-02 (drawing/blueprint upload) not implemented

The spec defines US-02 with drawing upload, OCR, and area recognition. Zero implementation exists -- no file upload endpoint, no drawing processing, no `input_type: "drawing"` support. This is P0 MVP scope per the spec.

#### M-02: US-05 (usage-based billing) not implemented

No usage tracking, no billing integration, no ЮKassa webhooks, no `GET /api/v1/estimate/usage` endpoint. The spec defines this as a core user story.

#### M-03: PDF renders in Latin transliteration, not Cyrillic

**File:** `services/fastapi-ai/app/services/pdf_generator.py:156-168`

The PDF table headers are hardcoded in Latin transliteration: "Kod GESN", "Naimenovanie", "Tsena", "Summa", "VSEGO". The disclaimer is also transliterated. If DejaVuSans is available (which it will be in Docker), Cyrillic rendering works fine. These should be proper Russian text.

#### M-04: `ExportResponse` schema is defined but never used

**File:** `services/fastapi-ai/app/models/schemas.py:151-155`

The `ExportResponse` model exists but no endpoint returns it. The spec calls for a pre-signed S3 URL in the export response -- the actual implementation returns raw PDF bytes inline. The spec also calls for `include_suggestions` in the export request, which is not implemented.

---

### LOW (4) -- Logged, no action required

#### L-01: `area_sqm` is `float` in Pydantic schema

`schemas.py:21` uses `area_sqm: float`. This is acceptable per `coding-style.md` which says "Float is acceptable for non-money quantities (площадь, количество)."

#### L-02: `ai_suggestions` always returns empty list

`ai_client.py:170` returns `"ai_suggestions": []` hardcoded. The field exists in the response schema but is never populated with actual suggestions.

#### L-03: `_compute_amount` in Odoo does not apply `index_coefficient`

`su_estimate.py:367-369`: The compute method calculates `amount = quantity * unit_price` but ignores `index_coefficient`. The field exists on the model but is not used in the computation. This may be intentional (if unit_price already includes the coefficient), but it's inconsistent with the spec which shows separate base_rate and coefficient.

#### L-04: No test for AI timeout handling

The endpoint catches `TimeoutError` and returns 504, but no test verifies this behavior. The `timeout=30` in the OpenAI SDK call and the `_AI_TIMEOUT = 60` in Odoo are mismatched (30s FastAPI vs 60s Odoo-to-FastAPI).

---

## Spec Coverage Matrix

| Spec Requirement | Status | Notes |
|---|---|---|
| US-01: Text-to-estimate | PARTIAL | Works, but sync instead of async, no Celery |
| US-02: Drawing-to-estimate | NOT IMPLEMENTED | Zero code exists |
| US-03: AI optimization | PARTIAL | Works, but uses AI hallucination for alternatives instead of ES lookup |
| US-04: Manual correction | IMPLEMENTED | Odoo write() override with manual_override flag |
| US-05: Usage billing | NOT IMPLEMENTED | Zero code exists |
| API 2.1: Async generate | NOT IMPLEMENTED | Synchronous, no task_id/polling |
| API 2.2: Optimize | PARTIAL | Takes items list instead of estimate_id |
| API 2.3: Export | PARTIAL | Returns inline PDF, not pre-signed S3 URL |
| API 2.4: Usage endpoint | NOT IMPLEMENTED | |
| NFR-F01-07: Decimal money | IMPLEMENTED | Consistently Decimal(str(...)) throughout FastAPI |
| NFR-F01-08: Rate limiting | NOT IMPLEMENTED | |
| Data model: su_minstroy_index | NOT IMPLEMENTED | No Minstroy index table or lookup |

---

## What Works Well

1. **Decimal discipline in FastAPI** -- money is consistently `Decimal(str(...))`, never `Decimal(float)`. Quantization to 2 decimal places is applied correctly.
2. **Prompt injection sanitization** -- regex-based stripping of common injection patterns with good test coverage.
3. **Graceful ES fallback** -- the system works without Elasticsearch, falling back to AI-only estimates.
4. **AI response parsing** -- handles markdown fences, malformed items, empty responses, list-vs-dict ambiguity.
5. **Odoo integration** -- clean separation between Odoo model and FastAPI service with proper error handling for connection/timeout failures.
6. **Test coverage for core paths** -- unit tests cover AI parsing, sanitization, Decimal precision, GESN validation, PDF generation, and endpoint integration.

---

## Verdict: NEEDS FIX

**3 blockers must be resolved before merge.** The CORS wildcard + no auth + no rate limiting combination means any internet-facing deployment allows unlimited unauthenticated AI generation at the operator's cost. The implementation covers roughly 40-50% of the specified API surface (no drawing upload, no billing, no async pipeline, no Minstroy indices). The FastAPI Decimal handling is excellent, but the security posture is production-unacceptable.
