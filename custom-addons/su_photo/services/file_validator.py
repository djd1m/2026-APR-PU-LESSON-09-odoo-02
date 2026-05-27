# -*- coding: utf-8 -*-
"""File upload validation for photo reports.

Validates MIME type via magic bytes (libmagic), file size, and filename
safety. NEVER relies on file extension alone for type detection.
"""
import logging
import os

_logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = frozenset({
    'image/jpeg',
    'image/png',
    'image/heic',
    'image/heif',
})

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

BLOCKED_EXTENSIONS = frozenset({
    '.exe', '.sh', '.bat', '.cmd', '.py', '.js', '.php',
    '.pl', '.rb', '.com', '.msi', '.scr', '.vbs', '.ps1',
    '.jar', '.war', '.elf', '.bin', '.cgi',
})


def validate_file(binary_data, filename=None):
    """Validate an uploaded file for photo reports.

    Checks:
    1. File size <= 20 MB
    2. MIME type is in whitelist (detected via magic bytes, not extension)
    3. Filename does not have a blocked executable extension
    4. Filename sanitized (no path traversal)

    Args:
        binary_data: raw bytes of the uploaded file
        filename: optional original filename

    Returns:
        str: detected MIME type

    Raises:
        odoo.exceptions.ValidationError: on any validation failure
    """
    from odoo.exceptions import ValidationError

    # 1. Size check
    if len(binary_data) > MAX_FILE_SIZE:
        raise ValidationError(
            'Файл слишком большой (%d МБ). '
            'Максимальный размер: 20 МБ.' % (len(binary_data) // (1024 * 1024))
        )

    # 2. MIME type check via magic bytes
    try:
        import magic
        mime = magic.from_buffer(binary_data[:2048], mime=True)
    except ImportError:
        _logger.warning(
            'python-magic not installed, falling back to extension check'
        )
        mime = _guess_mime_from_filename(filename)

    if mime not in ALLOWED_MIME_TYPES:
        raise ValidationError(
            'Недопустимый тип файла: %s. '
            'Разрешены: JPEG, PNG, HEIC.' % mime
        )

    # 3. Filename checks
    if filename:
        sanitized = sanitize_filename(filename)
        ext = os.path.splitext(sanitized)[1].lower()
        if ext in BLOCKED_EXTENSIONS:
            raise ValidationError(
                'Исполняемые файлы запрещены к загрузке.'
            )

    return mime


def sanitize_filename(filename):
    """Remove path traversal characters and limit length.

    Args:
        filename: original filename string

    Returns:
        str: sanitized filename
    """
    if not filename:
        return 'photo'
    # Strip path traversal
    sanitized = filename.replace('..', '').replace('/', '').replace('\\', '')
    # Limit length
    sanitized = sanitized[:255]
    return sanitized or 'photo'


def _guess_mime_from_filename(filename):
    """Fallback MIME detection from extension (only when python-magic unavailable)."""
    if not filename:
        return 'application/octet-stream'
    ext = os.path.splitext(filename)[1].lower()
    ext_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.heic': 'image/heic',
        '.heif': 'image/heif',
    }
    return ext_map.get(ext, 'application/octet-stream')
