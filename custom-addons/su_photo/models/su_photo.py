# -*- coding: utf-8 -*-
import base64
import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError

from ..services.s3_service import S3Service
from ..services.exif_parser import extract_exif
from ..services.file_validator import validate_file

_logger = logging.getLogger(__name__)


class SuPhoto(models.Model):
    _name = 'su.photo'
    _description = 'Фотофиксация'
    _order = 'taken_at desc, id desc'

    # ── Core fields ──────────────────────────────────────────
    name = fields.Char(
        string='Название',
        compute='_compute_name',
        store=True,
    )
    project_id = fields.Many2one(
        'su.project',
        string='Объект',
        ondelete='cascade',
        required=True,
    )
    task_id = fields.Many2one(
        'su.task',
        string='Задача',
        domain="[('project_id', '=', project_id)]",
    )
    image = fields.Binary(
        string='Фото',
        attachment=True,
    )
    image_filename = fields.Char(string='Имя файла')
    description = fields.Text(string='Описание')
    author_id = fields.Many2one(
        'res.users',
        string='Автор',
        default=lambda self: self.env.user,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Компания',
        related='project_id.company_id',
        store=True,
    )

    # ── Geolocation ──────────────────────────────────────────
    latitude = fields.Float(string='Широта', digits=(10, 7))
    longitude = fields.Float(string='Долгота', digits=(10, 7))
    taken_at = fields.Datetime(
        string='Дата съёмки',
        default=fields.Datetime.now,
    )

    # ── S3 Storage ───────────────────────────────────────────
    s3_key = fields.Char(
        string='S3 ключ',
        size=512,
        copy=False,
        index=True,
    )
    image_url = fields.Char(
        string='URL фото',
        compute='_compute_image_url',
    )

    # ── File metadata ────────────────────────────────────────
    file_size = fields.Integer(string='Размер файла (байт)')
    mime_type = fields.Char(string='MIME тип', size=64)
    camera_model = fields.Char(string='Камера', size=128)

    # ── Auto-progress ────────────────────────────────────────
    confirms_progress = fields.Boolean(
        string='Подтверждает прогресс',
        default=False,
        help='Если включено, загрузка фото автоматически увеличит прогресс задачи.',
    )
    progress_delta = fields.Float(
        string='Прирост прогресса %',
        default=10.0,
        help='На сколько процентов увеличить прогресс задачи (0-100).',
    )

    # ── Computed methods ─────────────────────────────────────

    @api.depends('project_id.name', 'task_id.name', 'taken_at')
    def _compute_name(self):
        for photo in self:
            parts = []
            if photo.project_id:
                parts.append(photo.project_id.name or '')
            if photo.task_id:
                parts.append(photo.task_id.name or '')
            if photo.taken_at:
                parts.append(fields.Datetime.to_string(photo.taken_at)[:10])
            photo.name = ' / '.join(parts) if parts else 'Фото'

    def _compute_image_url(self):
        """Generate presigned S3 URL for photo access."""
        for photo in self:
            if photo.s3_key:
                try:
                    photo.image_url = S3Service.get_presigned_url(photo.s3_key)
                except Exception as e:
                    _logger.warning(
                        'Failed to generate presigned URL for %s: %s',
                        photo.s3_key, e,
                    )
                    photo.image_url = False
            else:
                photo.image_url = False

    # ── CRUD overrides ───────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            raw_image = vals.get('image')
            if raw_image:
                binary_data = base64.b64decode(raw_image)

                # 1. Validate file (MIME + size + filename)
                mime = validate_file(binary_data, vals.get('image_filename'))
                vals['mime_type'] = mime
                vals['file_size'] = len(binary_data)

                # 2. Extract EXIF metadata (geotag, datetime, camera)
                exif = extract_exif(binary_data)
                if exif['latitude'] is not None and not vals.get('latitude'):
                    vals['latitude'] = exif['latitude']
                if exif['longitude'] is not None and not vals.get('longitude'):
                    vals['longitude'] = exif['longitude']
                if exif['taken_at'] is not None and not vals.get('taken_at'):
                    vals['taken_at'] = exif['taken_at']
                if exif['camera_model']:
                    vals['camera_model'] = exif['camera_model']

                # 3. Upload to S3 (MinIO)
                ext = mime.split('/')[-1]
                if ext == 'heif':
                    ext = 'heic'
                try:
                    project_id = vals.get('project_id')
                    company_id = (
                        vals.get('company_id')
                        or self.env.company.id
                    )
                    s3_key = S3Service.upload(
                        binary_data, company_id, project_id, ext,
                    )
                    vals['s3_key'] = s3_key
                    # Clear binary — S3 is the source of truth
                    vals['image'] = False
                except Exception as e:
                    _logger.warning(
                        'S3 upload failed, keeping image in DB: %s', e,
                    )
                    # Fallback: image stays in Odoo ir.attachment

        records = super().create(vals_list)

        # 4. Auto-progress update
        for record in records:
            if record.confirms_progress and record.task_id:
                record._update_task_progress()

        return records

    def unlink(self):
        """Delete S3 objects before removing DB records."""
        for photo in self:
            if photo.s3_key:
                try:
                    S3Service.delete(photo.s3_key)
                except Exception as e:
                    _logger.warning(
                        'S3 delete failed for %s: %s', photo.s3_key, e,
                    )
        return super().unlink()

    # ── Auto-progress logic ──────────────────────────────────

    def _update_task_progress(self):
        """Increment task progress when photo confirms work completion."""
        self.ensure_one()
        task = self.task_id
        if not task:
            return
        if task.state != 'in_progress':
            _logger.info(
                'Photo %d: task %d is in state "%s", '
                'skipping auto-progress update.',
                self.id, task.id, task.state,
            )
            return
        new_progress = min(
            task.progress_manual + self.progress_delta, 100.0,
        )
        task.write({'progress_manual': new_progress})
        task.message_post(
            body=(
                'Фотофиксация: прогресс задачи обновлён до %.0f%% '
                '(фото: %s)'
            ) % (new_progress, self.name or 'Фото'),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

    # ── Constraints ──────────────────────────────────────────

    @api.constrains('progress_delta')
    def _check_progress_delta(self):
        for photo in self:
            if photo.progress_delta < 0 or photo.progress_delta > 100:
                raise ValidationError(
                    'Прирост прогресса должен быть от 0 до 100%%.'
                )
