# F04 Photo Reports — Architecture

## Component Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                   Odoo 17 Web Client                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐  │
│  │ Tree View  │  │ Form View  │  │ Kanban View (gallery)  │  │
│  │ (enhanced) │  │ (enhanced) │  │ (enhanced: filters)    │  │
│  └────────────┘  └────────────┘  └────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Search View (NEW) — filters: project, task, date, me   │  │
│  └─────────────────────────────────────────────────────────┘  │
└──────────────────────┬───────────────────────────────────────┘
                       │  JSON-RPC
┌──────────────────────▼───────────────────────────────────────┐
│                 su_photo Odoo Module                          │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ su.photo model                                        │    │
│  │ - create() override: validate → EXIF → S3 upload      │    │
│  │ - unlink() override: S3 delete                        │    │
│  │ - _compute_image_url(): presigned URL generation      │    │
│  │ - _update_task_progress(): auto-progress increment    │    │
│  │ - @api.constrains: MIME check, size check             │    │
│  └──────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ S3 Service (services/s3_service.py)                   │    │
│  │ - upload(binary, company_id, project_id, ext)         │    │
│  │ - get_presigned_url(s3_key, expires_in)               │    │
│  │ - delete(s3_key)                                      │    │
│  │ - _get_client() → boto3 client (lazy init)            │    │
│  └──────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ EXIF Parser (services/exif_parser.py)                 │    │
│  │ - extract_exif(binary) → {lat, lon, datetime, camera} │    │
│  │ - _gps_to_decimal(dms, ref) → float                   │    │
│  └──────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Security Layer                                        │    │
│  │ - ir.model.access.csv (CRUD per group)                │    │
│  │ - ir.rule (record-level: foreman→own projects)        │    │
│  │ - File validation (magic bytes, size, extension)      │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────┬───────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│ PostgreSQL   │ │  MinIO   │ │ su_task      │
│ (Odoo ORM)   │ │  (S3)    │ │ (progress    │
│ su_photo     │ │  photos/ │ │  update)     │
│ metadata     │ │  bucket  │ │              │
└──────────────┘ └──────────┘ └──────────────┘
```

## Files Modified / Created

| File | Action | Purpose |
|------|--------|---------|
| `su_photo/models/su_photo.py` | MODIFY | Add new fields, create/unlink overrides, EXIF, S3, validation |
| `su_photo/services/__init__.py` | CREATE | Package init for services |
| `su_photo/services/s3_service.py` | CREATE | S3/MinIO client wrapper |
| `su_photo/services/exif_parser.py` | CREATE | EXIF GPS/datetime extraction |
| `su_photo/services/file_validator.py` | CREATE | MIME validation, size check |
| `su_photo/views/su_photo_views.xml` | MODIFY | Search view, enhanced kanban, stat buttons |
| `su_photo/security/ir.model.access.csv` | NO CHANGE | Already correct |
| `su_photo/security/su_photo_rules.xml` | CREATE | Record rules for RBAC |
| `su_photo/__manifest__.py` | MODIFY | Add security XML, new Python deps |
| `su_photo/__init__.py` | NO CHANGE | |
| `su_photo/models/__init__.py` | NO CHANGE | |
| `su_photo/tests/__init__.py` | CREATE | Test package |
| `su_photo/tests/test_su_photo.py` | CREATE | Unit tests |

## Data Flow: Photo Upload

```
1. User selects photo(s) in Odoo form/kanban
2. Odoo web client sends base64-encoded image via JSON-RPC
3. su.photo.create() intercepts:
   a. Decode base64 → raw bytes
   b. validate_file(): magic bytes check → MIME type, size ≤ 20MB
   c. extract_exif(): GPS DMS → decimal lat/lon, datetime, camera
   d. S3Service.upload(): PUT to MinIO → return s3_key
   e. Store s3_key in DB, clear binary from vals
   f. If confirms_progress: increment task.progress_manual
4. On read: _compute_image_url() generates presigned GET URL
5. On delete: unlink() calls S3Service.delete() before DB removal
```

## Dependency Graph

```
su_photo
├── depends: su_base (groups, company)
├── depends: su_project (project_id relation)
├── depends: su_task (task_id relation, progress update)
└── external:
    ├── boto3 (S3 client)
    ├── Pillow (EXIF parsing)
    └── python-magic (MIME detection)
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Input Validation                                   │
│ - Magic bytes MIME check (not extension-based)              │
│ - File size ≤ 20MB                                          │
│ - Blocked executable extensions                             │
│ - Filename sanitization (no path traversal)                 │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: RBAC (ir.model.access.csv)                         │
│ - Foreman: CRUD (no unlink)                                 │
│ - Manager: CRUD (no unlink)                                 │
│ - Admin: full CRUD                                          │
│ - Client: read-only                                         │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: Record Rules (ir.rule)                             │
│ - Foreman: own brigade's projects + own authored photos     │
│ - Manager: own company only                                 │
│ - Client: assigned projects only (read)                     │
├─────────────────────────────────────────────────────────────┤
│ Layer 4: S3 Access Control                                  │
│ - S3 keys never sent to client                              │
│ - Presigned URLs with 1h TTL                                │
│ - Server-side URL generation only                           │
└─────────────────────────────────────────────────────────────┘
```
