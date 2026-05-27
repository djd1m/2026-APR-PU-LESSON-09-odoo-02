# F04 Photo Reports — Specification

## Overview

Enhance the existing `su_photo` Odoo module to deliver production-ready photo
documentation for construction projects: S3 (MinIO) storage for photo files,
EXIF metadata extraction for automatic geotag and timestamp, auto-progress
update on photo upload, gallery view with filters by project/task/date/stage,
file validation (MIME type whitelist, 20MB limit, no executables), and RBAC
enforcement (foreman uploads for own brigade projects, manager sees all,
client read-only).

## Functional Requirements

### FR-01: File Upload with Validation

| Aspect | Detail |
|--------|--------|
| Accepted MIME types | `image/jpeg`, `image/png`, `image/heic`, `image/heif` |
| Max file size | 20 MB per file |
| Max batch | 10 photos per single upload request |
| Rejection | Executable files (`.exe`, `.sh`, `.bat`, `.cmd`, `.py`, `.js`), archives, non-image MIME types |
| Validation | Server-side MIME sniffing via `python-magic` (libmagic), NOT extension-only check |
| Filename sanitization | Strip path traversal chars (`../`, `..\\`), limit to 255 chars, replace non-ASCII |

- `@api.constrains('image')` MUST validate MIME type by reading magic bytes.
- `@api.constrains('image')` MUST reject files > 20 MB.
- Error messages in Russian for user-facing validation.

### FR-02: S3 (MinIO) Storage

| Aspect | Detail |
|--------|--------|
| Backend | MinIO (S3-compatible) via `boto3` |
| Bucket | `${S3_BUCKET}` from env (default: `stroiuprav`) |
| Key schema | `photos/{company_id}/{project_id}/{YYYY-MM}/{uuid}.{ext}` |
| Config | `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` from env — crash if missing |
| Presigned URLs | For read access; TTL = 3600s (1 hour) |

- Store S3 key in `s3_key` field (Char) on `su.photo`.
- Store presigned URL in `image_url` field (Char, computed, not stored).
- On `create()`: upload binary to S3, store key, clear binary from DB.
- On `unlink()`: delete object from S3 bucket.
- Fallback: if S3 unavailable, keep binary in Odoo attachment (log warning).

### FR-03: EXIF Metadata Extraction

| Aspect | Detail |
|--------|--------|
| Library | `Pillow` (PIL) for EXIF parsing |
| Extracted fields | GPS latitude, GPS longitude, DateTime, camera model |
| GPS conversion | EXIF GPS DMS (degrees-minutes-seconds) to decimal degrees |
| Fallback | If no EXIF GPS data, latitude/longitude remain 0.0 (user can set manually) |

- Extract EXIF on `create()` before S3 upload.
- Populate `latitude`, `longitude`, `taken_at` from EXIF data.
- `taken_at` defaults to `fields.Datetime.now()` only if EXIF has no DateTime.

### FR-04: Auto-Progress Update on Photo Upload

| Aspect | Detail |
|--------|--------|
| Trigger | When photo is created with `confirms_progress = True` |
| Field | New Boolean `confirms_progress` on `su.photo` (default: False) |
| Progress delta | New Float `progress_delta` on `su.photo` (default: 10.0, range 0-100) |
| Logic | `task.progress_manual = min(task.progress_manual + delta, 100.0)` |
| Constraint | Only applies when `task_id` is set and task is in `in_progress` state |

- Auto-progress is opt-in per photo (not every photo bumps progress).
- After progress update, post `message_post` on task with photo thumbnail link.

### FR-05: Gallery View with Filters

| Aspect | Detail |
|--------|--------|
| Default view | Kanban (gallery-style, already exists — enhance) |
| Filters | project_id, task_id, date range (taken_at), author_id |
| Group by | project_id, task_id, taken_at (month) |
| Search view | New `su.photo.search` with filter presets |
| Lightbox | Click photo card to open full-size image (Odoo image widget) |

- Add search view with predefined filters: "Мои фото", "Сегодня", "Эта неделя".
- Add group-by options in search view.

### FR-06: Photo Count on Project and Task

| Aspect | Detail |
|--------|--------|
| `su.project.photo_count` | Computed integer, already has `photo_ids` relation |
| `su.task.photo_count` | New computed integer field |
| Stat buttons | Add photo stat button on project form and task form |

### FR-07: RBAC and Record Rules

| Role | Create | Read | Write | Unlink |
|------|--------|------|-------|--------|
| Foreman | Own brigade's projects | Own brigade's projects | Own photos only | No |
| Manager | All projects | All | Own company | No |
| Admin | All | All | All | Yes |
| Client | No | Assigned projects (read-only) | No | No |

- Record rules enforce project-level isolation via `company_id`.
- Foreman record rule: `('project_id.task_ids.brigade_id.foreman_id', '=', user.id)` OR `('author_id', '=', user.id)`.
- IDOR prevention: `write()` override MUST verify `author_id == self.env.user` for foreman role.

## Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| Performance | S3 upload < 3s for 20MB file (P95) |
| Performance | Gallery load < 2s for 100 photos (P95, presigned URLs) |
| Security | MIME type validation via magic bytes, not extension |
| Security | No executable uploads (server-side enforcement) |
| Security | S3 keys never exposed to client — presigned URLs only |
| Storage | Photos NOT stored in PostgreSQL BLOB (S3 only, DB fallback for resilience) |
| Compliance | 152-FZ: photos stored in RU datacenter (MinIO on same VPS) |

## Data Model Changes

### su.photo (enhanced)

| Field | Type | New? | Description |
|-------|------|------|-------------|
| `s3_key` | Char(512) | YES | S3 object key |
| `image_url` | Char | YES | Computed presigned URL (not stored) |
| `confirms_progress` | Boolean | YES | Whether this photo confirms task progress |
| `progress_delta` | Float | YES | Progress increment (0-100), default 10.0 |
| `file_size` | Integer | YES | File size in bytes |
| `mime_type` | Char(64) | YES | Detected MIME type |
| `camera_model` | Char(128) | YES | EXIF camera model |
| `photo_count` (on su.task) | Integer | YES | Computed photo count |
