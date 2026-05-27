# F04 Photo Reports — Refinement

## Edge Cases & Error Handling

### EC-01: S3 Unavailable During Upload
- **Scenario:** MinIO container is down or network partition when user uploads photo.
- **Handling:** `create()` catches `boto3` exceptions, logs warning, keeps binary
  in Odoo's standard `ir.attachment` storage. Sets `s3_key = False`.
- **Recovery:** A scheduled action (`ir.cron`) can retry failed S3 uploads by
  finding photos where `image IS NOT NULL AND s3_key IS NULL`.
- **Bound:** Fallback uses PostgreSQL BLOB — acceptable for short outages but
  not for sustained use (DB bloat risk).

### EC-02: Corrupt/No EXIF Data
- **Scenario:** User uploads screenshot (no GPS), or EXIF is stripped by messaging app.
- **Handling:** `extract_exif()` returns `None` for all fields. `latitude` and
  `longitude` default to 0.0. `taken_at` defaults to `fields.Datetime.now()`.
- **Impact:** Map display shows marker at (0,0) — UI should hide map widget
  when both lat/lon are 0.0. Not a blocker for MVP.

### EC-03: HEIC Format
- **Scenario:** iPhone user uploads HEIC photos (default iOS format).
- **Handling:** `python-magic` correctly identifies HEIC MIME type. Pillow
  requires `pillow-heif` plugin for EXIF extraction. If plugin missing,
  EXIF extraction fails silently (returns None), photo still uploads.
- **Dependency:** Add `pillow-heif` to requirements.txt.

### EC-04: File Size at Boundary (exactly 20MB)
- **Scenario:** File is exactly 20,971,520 bytes.
- **Handling:** `<=` comparison, not `<`. Files at exactly 20MB are accepted.

### EC-05: Concurrent Upload (10 photos batch)
- **Scenario:** Foreman uploads 10 photos at once from mobile.
- **Handling:** `create()` with `vals_list` processes each photo sequentially.
  S3 uploads are synchronous (acceptable latency: 10 x ~1s = ~10s for 2MB avg).
- **Future optimization:** Background job via Celery for batch uploads.
  Not needed for MVP given mobile upload speeds.

### EC-06: Auto-Progress Beyond 100%
- **Scenario:** Task at 95%, foreman uploads photo with `progress_delta=10`.
- **Handling:** `min(task.progress_manual + delta, 100.0)` caps at 100%.

### EC-07: Auto-Progress on Wrong Task State
- **Scenario:** Photo uploaded with `confirms_progress=True` but task is in
  `new` or `done` state.
- **Handling:** `_update_task_progress()` checks `task.state == 'in_progress'`
  before applying delta. No error raised — photo is still created, progress
  just not updated. Post a `message_post` note explaining why progress was
  not updated.

### EC-08: IDOR — User A Accessing User B's Photos
- **Scenario:** Foreman in Brigade A crafts a request to read/modify photos
  belonging to Brigade B's project.
- **Handling:** Odoo record rules enforce project-level isolation. The foreman
  rule domain restricts visibility to projects where user is foreman or
  brigade member. Direct ID access is blocked by `ir.rule` check.
- **Verification:** Test case explicitly creates two users in different brigades
  and verifies `AccessError` on cross-access.

### EC-09: S3 Key Collision
- **Scenario:** Two uploads generate the same UUID (astronomically unlikely).
- **Handling:** UUID4 collision probability is ~2^-122. No mitigation needed.
  If it somehow occurs, the newer upload overwrites the older S3 object —
  the older photo's presigned URL would serve the newer image. Acceptable risk.

### EC-10: Delete Photo with Missing S3 Object
- **Scenario:** S3 object already deleted (manual cleanup, bucket policy), user
  deletes photo record.
- **Handling:** `unlink()` catches `ClientError` from boto3 on `delete_object`.
  Logs warning, proceeds with DB record deletion. No orphaned DB records.

### EC-11: Filename with Path Traversal
- **Scenario:** Malicious upload with filename `../../../etc/passwd`.
- **Handling:** `validate_file()` strips `..`, `/`, `\` from filename before
  any processing. S3 key uses UUID, not original filename — path traversal
  has no effect on storage location.

## Performance Considerations

| Operation | Target | Strategy |
|-----------|--------|----------|
| S3 upload (single 20MB) | < 3s | Direct MinIO on same VPS (localhost network) |
| EXIF extraction | < 200ms | Pillow reads only EXIF header, not full image |
| MIME detection | < 50ms | python-magic reads first 2KB only |
| Gallery load (100 photos) | < 2s | Presigned URLs computed on read, paginated |
| Presigned URL generation | < 10ms per URL | boto3 local computation (no S3 roundtrip) |

## Test Strategy

| Test | Type | What it verifies |
|------|------|------------------|
| test_upload_jpeg | Unit | JPEG upload stores s3_key, clears binary |
| test_upload_png | Unit | PNG upload accepted |
| test_reject_executable | Unit | .exe upload raises ValidationError |
| test_reject_oversize | Unit | 21MB file raises ValidationError |
| test_exif_extraction | Unit | GPS and DateTime extracted from test JPEG |
| test_exif_missing | Unit | No EXIF → defaults used |
| test_auto_progress | Unit | confirms_progress=True increments task progress |
| test_auto_progress_caps_100 | Unit | Progress does not exceed 100% |
| test_auto_progress_wrong_state | Unit | No progress update when task is done |
| test_s3_delete_on_unlink | Unit | S3 delete called when photo record deleted |
| test_idor_cross_brigade | Integration | Foreman cannot access other brigade's photos |
| test_presigned_url | Unit | image_url computed when s3_key present |
| test_gallery_filters | Integration | Search view filters by project, task, date |
