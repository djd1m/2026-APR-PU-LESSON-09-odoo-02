# F04 Photo Reports — Pseudocode

## S3 Helper Service

```python
import boto3
import uuid
import os
import logging

_logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/heic', 'image/heif'}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

class S3Service:
    """Singleton-style S3 client wrapper for MinIO."""

    _client = None

    @classmethod
    def _get_client(cls):
        if cls._client is None:
            endpoint = os.environ.get('S3_ENDPOINT')
            access_key = os.environ.get('S3_ACCESS_KEY')
            secret_key = os.environ.get('S3_SECRET_KEY')
            if not all([endpoint, access_key, secret_key]):
                raise RuntimeError(
                    "S3 configuration missing. Set S3_ENDPOINT, "
                    "S3_ACCESS_KEY, S3_SECRET_KEY environment variables."
                )
            cls._client = boto3.client(
                's3',
                endpoint_url=endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name='us-east-1',  # MinIO default
            )
        return cls._client

    @classmethod
    def upload(cls, binary_data, company_id, project_id, extension):
        """Upload binary to S3, return s3_key."""
        client = cls._get_client()
        bucket = os.environ.get('S3_BUCKET', 'stroiuprav')
        from datetime import datetime
        date_prefix = datetime.utcnow().strftime('%Y-%m')
        file_uuid = uuid.uuid4().hex
        s3_key = f"photos/{company_id}/{project_id}/{date_prefix}/{file_uuid}.{extension}"
        client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=binary_data,
            ContentType=f'image/{extension}',
        )
        return s3_key

    @classmethod
    def get_presigned_url(cls, s3_key, expires_in=3600):
        """Generate presigned GET URL."""
        client = cls._get_client()
        bucket = os.environ.get('S3_BUCKET', 'stroiuprav')
        return client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': s3_key},
            ExpiresIn=expires_in,
        )

    @classmethod
    def delete(cls, s3_key):
        """Delete object from S3."""
        client = cls._get_client()
        bucket = os.environ.get('S3_BUCKET', 'stroiuprav')
        client.delete_object(Bucket=bucket, Key=s3_key)
```

## EXIF Extraction

```python
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import io

def extract_exif(binary_data):
    """Extract geotag + timestamp from EXIF data.

    Returns dict: {latitude, longitude, taken_at, camera_model}
    All values may be None if EXIF data is absent.
    """
    result = {'latitude': None, 'longitude': None,
              'taken_at': None, 'camera_model': None}
    try:
        img = Image.open(io.BytesIO(binary_data))
        exif_data = img._getexif()
        if not exif_data:
            return result

        # Camera model
        if 272 in exif_data:  # Tag 272 = Model
            result['camera_model'] = str(exif_data[272])[:128]

        # DateTime
        if 36867 in exif_data:  # DateTimeOriginal
            dt_str = exif_data[36867]  # "2025:03:15 14:30:00"
            from datetime import datetime
            result['taken_at'] = datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S')
        elif 306 in exif_data:  # DateTime
            dt_str = exif_data[306]
            from datetime import datetime
            result['taken_at'] = datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S')

        # GPS
        gps_info = exif_data.get(34853)  # GPSInfo tag
        if gps_info:
            result['latitude'] = _gps_to_decimal(
                gps_info.get(2), gps_info.get(1)  # GPSLatitude, GPSLatitudeRef
            )
            result['longitude'] = _gps_to_decimal(
                gps_info.get(4), gps_info.get(3)  # GPSLongitude, GPSLongitudeRef
            )
    except Exception:
        pass  # Corrupt/no EXIF — return defaults
    return result


def _gps_to_decimal(dms_tuple, ref):
    """Convert EXIF GPS DMS to decimal degrees.

    dms_tuple: ((deg_num, deg_den), (min_num, min_den), (sec_num, sec_den))
    ref: 'N'/'S' or 'E'/'W'
    """
    if not dms_tuple or not ref:
        return None
    degrees = float(dms_tuple[0])
    minutes = float(dms_tuple[1])
    seconds = float(dms_tuple[2])
    decimal = degrees + minutes / 60.0 + seconds / 3600.0
    if ref in ('S', 'W'):
        decimal = -decimal
    return round(decimal, 7)
```

## MIME Validation

```python
import magic

def validate_file(binary_data, filename):
    """Validate uploaded file: MIME type and size.

    Raises ValidationError on failure.
    """
    # Size check
    if len(binary_data) > MAX_FILE_SIZE:
        raise ValidationError(
            'Файл слишком большой. Максимальный размер: 20 МБ.'
        )

    # MIME check via magic bytes (NOT extension)
    mime = magic.from_buffer(binary_data[:2048], mime=True)
    if mime not in ALLOWED_MIME_TYPES:
        raise ValidationError(
            'Недопустимый тип файла: %s. '
            'Разрешены: JPEG, PNG, HEIC.' % mime
        )

    # Filename sanitization
    if filename:
        import re
        # Strip path traversal
        sanitized = filename.replace('..', '').replace('/', '').replace('\\', '')
        # Limit length
        sanitized = sanitized[:255]
        # Check for executable extensions
        BLOCKED_EXTENSIONS = {'.exe', '.sh', '.bat', '.cmd', '.py', '.js',
                              '.php', '.pl', '.rb', '.com', '.msi', '.scr'}
        ext = os.path.splitext(sanitized)[1].lower()
        if ext in BLOCKED_EXTENSIONS:
            raise ValidationError(
                'Исполняемые файлы запрещены к загрузке.'
            )
    return mime
```

## SuPhoto Model — Enhanced create/unlink

```python
class SuPhoto(models.Model):

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('image'):
                binary_data = base64.b64decode(vals['image'])

                # 1. Validate file
                mime = validate_file(binary_data, vals.get('image_filename'))
                vals['mime_type'] = mime
                vals['file_size'] = len(binary_data)

                # 2. Extract EXIF
                exif = extract_exif(binary_data)
                if exif['latitude'] is not None:
                    vals.setdefault('latitude', exif['latitude'])
                if exif['longitude'] is not None:
                    vals.setdefault('longitude', exif['longitude'])
                if exif['taken_at'] is not None:
                    vals.setdefault('taken_at', exif['taken_at'])
                if exif['camera_model']:
                    vals['camera_model'] = exif['camera_model']

                # 3. Upload to S3
                ext = mime.split('/')[-1]
                if ext == 'heif':
                    ext = 'heic'
                try:
                    project_id = vals.get('project_id')
                    company_id = self.env.company.id
                    s3_key = S3Service.upload(
                        binary_data, company_id, project_id, ext
                    )
                    vals['s3_key'] = s3_key
                    # Clear binary from DB — S3 is source of truth
                    vals['image'] = False
                except Exception as e:
                    _logger.warning('S3 upload failed, keeping in DB: %s', e)
                    # Fallback: keep binary in Odoo attachment

        records = super().create(vals_list)

        # 4. Auto-progress update
        for record in records:
            if record.confirms_progress and record.task_id:
                record._update_task_progress()

        return records

    def unlink(self):
        # Delete from S3 before removing DB record
        for photo in self:
            if photo.s3_key:
                try:
                    S3Service.delete(photo.s3_key)
                except Exception as e:
                    _logger.warning('S3 delete failed for %s: %s',
                                    photo.s3_key, e)
        return super().unlink()

    def _update_task_progress(self):
        """Increment task progress when photo confirms work completion."""
        self.ensure_one()
        task = self.task_id
        if not task or task.state != 'in_progress':
            return
        new_progress = min(
            task.progress_manual + self.progress_delta, 100.0
        )
        task.write({'progress_manual': new_progress})
        task.message_post(
            body='Фотофиксация: прогресс задачи обновлён до %.0f%%' % new_progress,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

    def _compute_image_url(self):
        """Generate presigned S3 URL for photo access."""
        for photo in self:
            if photo.s3_key:
                try:
                    photo.image_url = S3Service.get_presigned_url(photo.s3_key)
                except Exception:
                    photo.image_url = False
            else:
                photo.image_url = False
```

## Photo Count on su.task

```python
# In su.task model — add computed field
photo_count = fields.Integer(
    string='Фото',
    compute='_compute_photo_count',
)

@api.depends('photo_ids')
def _compute_photo_count(self):
    for task in self:
        task.photo_count = len(task.photo_ids)
```
