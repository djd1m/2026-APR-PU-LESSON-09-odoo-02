# F04 Photo Reports — Completion Checklist

## Implementation Checklist

### Models — su.photo
- [x] New fields: `s3_key`, `image_url`, `confirms_progress`, `progress_delta`, `file_size`, `mime_type`, `camera_model`
- [x] `@api.model_create_multi` override: validate → EXIF → S3 upload → auto-progress
- [x] `unlink()` override: S3 delete before DB removal
- [x] `_compute_image_url()`: presigned URL generation from s3_key
- [x] `_update_task_progress()`: increment task.progress_manual, post message
- [x] `@api.constrains('image')`: MIME type validation via magic bytes
- [x] `@api.constrains('image')`: file size <= 20MB check
- [x] `_compute_name()`: existing, depends on `@api.depends('project_id.name', 'task_id.name', 'taken_at')`

### Services
- [x] `services/s3_service.py`: S3Service class with upload/get_presigned_url/delete
- [x] `services/exif_parser.py`: extract_exif() with GPS DMS→decimal, DateTime, camera model
- [x] `services/file_validator.py`: validate_file() with magic bytes, size, extension blocking
- [x] `services/__init__.py`: package init

### Views
- [x] Search view with predefined filters: "Мои фото", "Сегодня", "Эта неделя"
- [x] Search view with group-by: project, task, month
- [x] Form view: add new fields (s3_key hidden, confirms_progress, progress_delta)
- [x] Form view: image_url widget for S3-backed photos
- [x] Kanban view: enhanced with search view reference
- [x] Tree view: add file_size, mime_type columns (optional hide)
- [x] Action: add search_view_id reference

### Security
- [x] `su_photo_rules.xml`: foreman record rule (own brigade projects + own photos)
- [x] `su_photo_rules.xml`: manager record rule (own company)
- [x] `su_photo_rules.xml`: client record rule (assigned projects, read-only)
- [x] `ir.model.access.csv`: unchanged (already correct)

### Cross-Module Changes
- [x] `su.task`: add `photo_count` computed field
- [x] `su.task` form view: add photo stat button
- [x] `su.project` form view: add photo stat button (uses existing `photo_ids`)

### Manifest & Dependencies
- [x] `__manifest__.py`: add `security/su_photo_rules.xml` to data
- [x] `requirements.txt`: add `boto3`, `Pillow`, `python-magic`, `pillow-heif`

### Tests
- [x] `tests/__init__.py`: import test module
- [x] `tests/test_su_photo.py`: upload validation tests
- [x] `tests/test_su_photo.py`: EXIF extraction tests
- [x] `tests/test_su_photo.py`: auto-progress tests
- [x] `tests/test_su_photo.py`: IDOR / RBAC tests
- [x] `tests/test_su_photo.py`: S3 delete on unlink tests

## Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| `boto3` | >= 1.28 | S3/MinIO client |
| `Pillow` | >= 10.0 | EXIF parsing |
| `python-magic` | >= 0.4.27 | MIME type detection via libmagic |
| `pillow-heif` | >= 0.13 | HEIC/HEIF format support for Pillow |

## Deployment Notes

- MinIO container already exists in `docker-compose.yml`
- S3 env vars already defined in `.env.example`
- `libmagic` must be installed in Docker image (`apt-get install libmagic1`)
- Create bucket `stroiuprav` on first deploy (MinIO auto-creates on first PUT)
