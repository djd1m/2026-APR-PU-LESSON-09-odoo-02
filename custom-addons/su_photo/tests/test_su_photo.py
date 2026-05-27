# -*- coding: utf-8 -*-
import base64
from unittest.mock import patch, MagicMock

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


# Minimal valid 1x1 white JPEG (binary)
TINY_JPEG = (
    b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
    b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
    b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
    b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
    b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00'
    b'\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00'
    b'\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b'
    b'\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04'
    b'\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07'
    b'\x22q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16'
    b'\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz'
    b'\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99'
    b'\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7'
    b'\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5'
    b'\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1'
    b'\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa'
    b'\xff\xda\x00\x08\x01\x01\x00\x00?\x00T\xdb\xa8\xa3 \x02\x80\x0f\xff\xd9'
)
TINY_JPEG_B64 = base64.b64encode(TINY_JPEG).decode()


class TestSuPhotoValidation(TransactionCase):
    """Test file upload validation: MIME type, size, executables."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['su.project'].create({
            'name': 'Тестовый объект для фото',
        })
        cls.task = cls.env['su.task'].create({
            'name': 'Тестовая задача',
            'project_id': cls.project.id,
            'state': 'in_progress',
        })

    def _create_photo(self, **kwargs):
        vals = {
            'project_id': self.project.id,
            'image': TINY_JPEG_B64,
            'image_filename': 'test.jpg',
        }
        vals.update(kwargs)
        return vals

    @patch('odoo.addons.su_photo.services.s3_service.S3Service.upload',
           return_value='photos/1/1/2026-05/abc123.jpeg')
    @patch('odoo.addons.su_photo.services.file_validator.magic')
    def test_upload_jpeg_stores_s3_key(self, mock_magic, mock_upload):
        """Valid JPEG upload should store s3_key and clear binary."""
        mock_magic.from_buffer.return_value = 'image/jpeg'
        photo = self.env['su.photo'].create(self._create_photo())
        self.assertTrue(photo.s3_key)
        self.assertEqual(photo.mime_type, 'image/jpeg')
        self.assertFalse(photo.image, 'Binary should be cleared after S3 upload')
        mock_upload.assert_called_once()

    @patch('odoo.addons.su_photo.services.file_validator.magic')
    def test_reject_executable(self, mock_magic):
        """Executable file extension should be rejected."""
        mock_magic.from_buffer.return_value = 'application/x-executable'
        with self.assertRaises(ValidationError) as cm:
            self.env['su.photo'].create(self._create_photo(
                image_filename='malware.exe',
            ))
        self.assertIn('Недопустимый тип файла', str(cm.exception))

    @patch('odoo.addons.su_photo.services.file_validator.magic')
    def test_reject_oversize(self, mock_magic):
        """File > 20MB should be rejected."""
        mock_magic.from_buffer.return_value = 'image/jpeg'
        # Create a fake 21MB base64 payload
        big_data = b'\xff\xd8\xff\xe0' + b'\x00' * (21 * 1024 * 1024)
        big_b64 = base64.b64encode(big_data).decode()
        with self.assertRaises(ValidationError) as cm:
            self.env['su.photo'].create(self._create_photo(image=big_b64))
        self.assertIn('слишком большой', str(cm.exception))

    @patch('odoo.addons.su_photo.services.s3_service.S3Service.upload',
           return_value='photos/1/1/2026-05/abc123.png')
    @patch('odoo.addons.su_photo.services.file_validator.magic')
    def test_upload_png(self, mock_magic, mock_upload):
        """PNG upload should be accepted."""
        mock_magic.from_buffer.return_value = 'image/png'
        photo = self.env['su.photo'].create(self._create_photo(
            image_filename='screenshot.png',
        ))
        self.assertEqual(photo.mime_type, 'image/png')
        self.assertTrue(photo.s3_key)


class TestSuPhotoAutoProgress(TransactionCase):
    """Test auto-progress update on photo upload."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['su.project'].create({
            'name': 'Объект для прогресса',
        })
        cls.task = cls.env['su.task'].create({
            'name': 'Задача в работе',
            'project_id': cls.project.id,
            'state': 'in_progress',
            'progress_manual': 50.0,
        })

    @patch('odoo.addons.su_photo.services.s3_service.S3Service.upload',
           return_value='photos/1/1/2026-05/abc123.jpeg')
    @patch('odoo.addons.su_photo.services.file_validator.magic')
    def test_auto_progress_increments(self, mock_magic, mock_upload):
        """Photo with confirms_progress=True should increment task progress."""
        mock_magic.from_buffer.return_value = 'image/jpeg'
        self.env['su.photo'].create({
            'project_id': self.project.id,
            'task_id': self.task.id,
            'image': TINY_JPEG_B64,
            'image_filename': 'progress.jpg',
            'confirms_progress': True,
            'progress_delta': 10.0,
        })
        self.assertEqual(self.task.progress_manual, 60.0)

    @patch('odoo.addons.su_photo.services.s3_service.S3Service.upload',
           return_value='photos/1/1/2026-05/abc123.jpeg')
    @patch('odoo.addons.su_photo.services.file_validator.magic')
    def test_auto_progress_caps_at_100(self, mock_magic, mock_upload):
        """Progress should not exceed 100%."""
        mock_magic.from_buffer.return_value = 'image/jpeg'
        self.task.write({'progress_manual': 95.0})
        self.env['su.photo'].create({
            'project_id': self.project.id,
            'task_id': self.task.id,
            'image': TINY_JPEG_B64,
            'image_filename': 'final.jpg',
            'confirms_progress': True,
            'progress_delta': 10.0,
        })
        self.assertEqual(self.task.progress_manual, 100.0)

    @patch('odoo.addons.su_photo.services.s3_service.S3Service.upload',
           return_value='photos/1/1/2026-05/abc123.jpeg')
    @patch('odoo.addons.su_photo.services.file_validator.magic')
    def test_auto_progress_skipped_when_task_done(self, mock_magic, mock_upload):
        """No progress update when task is in 'done' state."""
        mock_magic.from_buffer.return_value = 'image/jpeg'
        self.task.write({'state': 'done', 'progress_manual': 100.0})
        self.env['su.photo'].create({
            'project_id': self.project.id,
            'task_id': self.task.id,
            'image': TINY_JPEG_B64,
            'image_filename': 'extra.jpg',
            'confirms_progress': True,
            'progress_delta': 10.0,
        })
        # Progress should remain 100, not 110
        self.assertEqual(self.task.progress_manual, 100.0)

    @patch('odoo.addons.su_photo.services.s3_service.S3Service.upload',
           return_value='photos/1/1/2026-05/abc123.jpeg')
    @patch('odoo.addons.su_photo.services.file_validator.magic')
    def test_no_progress_when_flag_false(self, mock_magic, mock_upload):
        """Photo without confirms_progress should not change task progress."""
        mock_magic.from_buffer.return_value = 'image/jpeg'
        original = self.task.progress_manual
        self.env['su.photo'].create({
            'project_id': self.project.id,
            'task_id': self.task.id,
            'image': TINY_JPEG_B64,
            'image_filename': 'just_photo.jpg',
            'confirms_progress': False,
        })
        self.assertEqual(self.task.progress_manual, original)


class TestSuPhotoS3Lifecycle(TransactionCase):
    """Test S3 upload/delete lifecycle."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['su.project'].create({
            'name': 'Объект S3',
        })

    @patch('odoo.addons.su_photo.services.s3_service.S3Service.delete')
    @patch('odoo.addons.su_photo.services.s3_service.S3Service.upload',
           return_value='photos/1/1/2026-05/abc123.jpeg')
    @patch('odoo.addons.su_photo.services.file_validator.magic')
    def test_s3_delete_on_unlink(self, mock_magic, mock_upload, mock_delete):
        """Deleting a photo should call S3 delete."""
        mock_magic.from_buffer.return_value = 'image/jpeg'
        photo = self.env['su.photo'].create({
            'project_id': self.project.id,
            'image': TINY_JPEG_B64,
            'image_filename': 'delete_me.jpg',
        })
        s3_key = photo.s3_key
        photo.unlink()
        mock_delete.assert_called_once_with(s3_key)

    @patch('odoo.addons.su_photo.services.s3_service.S3Service.upload',
           side_effect=Exception('MinIO down'))
    @patch('odoo.addons.su_photo.services.file_validator.magic')
    def test_s3_failure_fallback(self, mock_magic, mock_upload):
        """S3 failure should fallback to DB storage."""
        mock_magic.from_buffer.return_value = 'image/jpeg'
        photo = self.env['su.photo'].create({
            'project_id': self.project.id,
            'image': TINY_JPEG_B64,
            'image_filename': 'fallback.jpg',
        })
        self.assertFalse(photo.s3_key)
        self.assertTrue(photo.image, 'Image should remain in DB on S3 failure')


class TestSuPhotoExif(TransactionCase):
    """Test EXIF extraction service."""

    def test_exif_missing_returns_defaults(self):
        """Image without EXIF should return None defaults."""
        from odoo.addons.su_photo.services.exif_parser import extract_exif
        # TINY_JPEG has no EXIF data
        result = extract_exif(TINY_JPEG)
        self.assertIsNone(result['latitude'])
        self.assertIsNone(result['longitude'])
        self.assertIsNone(result['taken_at'])
        self.assertIsNone(result['camera_model'])

    def test_gps_to_decimal_north_east(self):
        """Test DMS to decimal conversion for N/E."""
        from odoo.addons.su_photo.services.exif_parser import _gps_to_decimal
        # 55 degrees 45 minutes 30 seconds N = 55.7583333
        result = _gps_to_decimal((55.0, 45.0, 30.0), 'N')
        self.assertAlmostEqual(result, 55.7583333, places=5)

    def test_gps_to_decimal_south(self):
        """Test DMS to decimal conversion for S (negative)."""
        from odoo.addons.su_photo.services.exif_parser import _gps_to_decimal
        result = _gps_to_decimal((33.0, 51.0, 54.0), 'S')
        self.assertAlmostEqual(result, -33.865, places=3)

    def test_gps_to_decimal_none_input(self):
        """None GPS input should return None."""
        from odoo.addons.su_photo.services.exif_parser import _gps_to_decimal
        self.assertIsNone(_gps_to_decimal(None, 'N'))
        self.assertIsNone(_gps_to_decimal((55.0, 45.0, 30.0), None))


class TestSuPhotoProgressDelta(TransactionCase):
    """Test progress_delta constraint."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['su.project'].create({
            'name': 'Объект для delta',
        })

    @patch('odoo.addons.su_photo.services.s3_service.S3Service.upload',
           return_value='photos/1/1/2026-05/abc123.jpeg')
    @patch('odoo.addons.su_photo.services.file_validator.magic')
    def test_negative_progress_delta_rejected(self, mock_magic, mock_upload):
        """Progress delta < 0 should raise ValidationError."""
        mock_magic.from_buffer.return_value = 'image/jpeg'
        with self.assertRaises(ValidationError):
            self.env['su.photo'].create({
                'project_id': self.project.id,
                'image': TINY_JPEG_B64,
                'image_filename': 'test.jpg',
                'progress_delta': -5.0,
            })

    @patch('odoo.addons.su_photo.services.s3_service.S3Service.upload',
           return_value='photos/1/1/2026-05/abc123.jpeg')
    @patch('odoo.addons.su_photo.services.file_validator.magic')
    def test_over_100_progress_delta_rejected(self, mock_magic, mock_upload):
        """Progress delta > 100 should raise ValidationError."""
        mock_magic.from_buffer.return_value = 'image/jpeg'
        with self.assertRaises(ValidationError):
            self.env['su.photo'].create({
                'project_id': self.project.id,
                'image': TINY_JPEG_B64,
                'image_filename': 'test.jpg',
                'progress_delta': 150.0,
            })
