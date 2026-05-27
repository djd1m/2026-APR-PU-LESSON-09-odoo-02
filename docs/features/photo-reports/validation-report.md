# F04 Photo Reports — Validation Report

**Date:** 2026-05-27
**Validator:** requirements-validator
**Verdict:** READY

## Scoring

| Dimension | Score | Notes |
|-----------|-------|-------|
| Completeness | 85 | All 6 FR-PHT requirements from Specification.md covered (FR-PHT-01 through FR-PHT-06). FR-PHT-05 (offline mode) deferred to PWA module (F06) — acceptable |
| Consistency | 90 | Data model, S3 flow, EXIF parsing, auto-progress logic internally consistent. Field types match coding-style rules (Float for lat/lon OK, Monetary not needed) |
| Testability | 85 | Each FR has matching test cases with clear assertions. S3 interactions mockable via boto3 stubber. EXIF testable with crafted JPEG fixtures |
| Feasibility | 90 | Pure Odoo ORM + boto3 + Pillow — all mature libraries. MinIO already in docker-compose.yml. S3 env vars already in .env.example |
| Security | 85 | MIME magic-byte validation (not extension-only), 20MB limit, executable blocking, IDOR prevention via record rules, S3 keys not exposed, presigned URLs with TTL |
| Performance | 80 | Synchronous S3 upload acceptable for single photos. Batch (10 photos) may take ~10s — acceptable for mobile. Presigned URL computation is local (no S3 roundtrip) |

**Average: 85.8** (threshold: 70)

## Blockers

None.

## Caveats

### C-01: Offline Photo Upload (FR-PHT-05) Deferred (Low)

FR-PHT-05 (offline mode with local storage and auto-sync) is explicitly deferred
to the PWA module (F06). The `su_photo` Odoo module handles server-side only.
Offline queueing will be implemented in the Service Worker layer.

**Impact:** Foremen without connectivity cannot upload photos until back online.
Acceptable for MVP — most construction sites have mobile coverage.

### C-02: Synchronous S3 Upload (Medium)

S3 uploads happen synchronously inside `create()`. For a single 20MB photo
this is ~1-3s. For batch uploads (10 photos), total time may reach ~10-30s
depending on photo sizes.

**Impact:** User waits during upload. Acceptable for MVP. Future optimization:
Celery background task for batch uploads.

### C-03: HEIC EXIF Dependency (Low)

HEIC EXIF extraction requires `pillow-heif` package. If not installed, HEIC
photos still upload but without geotag extraction. The system logs a warning
but does not block the upload.

**Impact:** iPhone users may not get automatic geotags. Mitigated by adding
`pillow-heif` to requirements.txt.

### C-04: Client Record Rule Placeholder (Low)

Client record rule for photo access requires a project-to-client sharing
mechanism that does not exist yet (same caveat as F03 task-management).
Rule uses `[(1, '=', 0)]` (deny all) until F11 (Client Portal) is built.

**Impact:** Clients cannot view photos until F11. Acceptable for MVP scope.

## Requirements Traceability

| PRD Requirement | Spec Reference | Test Case |
|-----------------|---------------|-----------|
| US-05: Photo with auto geotag and timestamp | FR-03 (EXIF extraction) | test_exif_extraction, test_exif_missing |
| US-05: Link to task/stage | FR-03 (task_id field) | test_upload_with_task |
| US-05: Auto-update progress | FR-04 (auto-progress) | test_auto_progress, test_auto_progress_caps_100 |
| FR-PHT-01: Upload validation | FR-01 (file validation) | test_reject_executable, test_reject_oversize |
| FR-PHT-02: Auto geotag | FR-03 | test_exif_extraction |
| FR-PHT-03: Link to task/stage | FR-01 (task_id required) | test_upload_with_task |
| FR-PHT-04: Progress update | FR-04 | test_auto_progress |
| FR-PHT-05: Offline mode | Deferred to F06 | N/A |
| FR-PHT-06: Gallery with filters | FR-05 (search view) | test_gallery_filters |
| Security: IDOR prevention | FR-07 (record rules) | test_idor_cross_brigade |
| Security: File validation | FR-01 | test_reject_executable, test_reject_oversize |
| Security: No S3 key exposure | FR-02 (presigned URLs) | test_presigned_url |

## Verdict

**READY** — proceed to Phase 3 (IMPLEMENT).
