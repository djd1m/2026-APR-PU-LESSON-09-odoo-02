# -*- coding: utf-8 -*-
"""EXIF metadata extraction for photo geotag and timestamp."""
import io
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


def extract_exif(binary_data):
    """Extract geotag, timestamp, and camera model from EXIF data.

    Args:
        binary_data: raw bytes of the image file

    Returns:
        dict with keys:
            latitude (float or None)
            longitude (float or None)
            taken_at (datetime or None)
            camera_model (str or None)
    """
    result = {
        'latitude': None,
        'longitude': None,
        'taken_at': None,
        'camera_model': None,
    }
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(binary_data))
        exif_data = img._getexif()
        if not exif_data:
            return result

        # Camera model (EXIF tag 272 = Model)
        model = exif_data.get(272)
        if model:
            result['camera_model'] = str(model)[:128]

        # DateTime — prefer DateTimeOriginal (36867), fallback to DateTime (306)
        dt_str = exif_data.get(36867) or exif_data.get(306)
        if dt_str and isinstance(dt_str, str):
            try:
                result['taken_at'] = datetime.strptime(
                    dt_str, '%Y:%m:%d %H:%M:%S'
                )
            except ValueError:
                _logger.debug('Could not parse EXIF datetime: %s', dt_str)

        # GPS info (EXIF tag 34853 = GPSInfo)
        gps_info = exif_data.get(34853)
        if gps_info:
            lat = _gps_to_decimal(
                gps_info.get(2),  # GPSLatitude
                gps_info.get(1),  # GPSLatitudeRef
            )
            lon = _gps_to_decimal(
                gps_info.get(4),  # GPSLongitude
                gps_info.get(3),  # GPSLongitudeRef
            )
            if lat is not None:
                result['latitude'] = lat
            if lon is not None:
                result['longitude'] = lon

    except Exception as e:
        _logger.debug('EXIF extraction failed: %s', e)

    return result


def _gps_to_decimal(dms_tuple, ref):
    """Convert EXIF GPS DMS (degrees-minutes-seconds) to decimal degrees.

    Args:
        dms_tuple: tuple of 3 values (degrees, minutes, seconds)
                   Each value may be a float, int, or IFDRational
        ref: str, one of 'N', 'S', 'E', 'W'

    Returns:
        float rounded to 7 decimal places, or None if input is invalid
    """
    if not dms_tuple or not ref:
        return None
    try:
        degrees = float(dms_tuple[0])
        minutes = float(dms_tuple[1])
        seconds = float(dms_tuple[2])
        decimal = degrees + minutes / 60.0 + seconds / 3600.0
        if ref in ('S', 'W'):
            decimal = -decimal
        return round(decimal, 7)
    except (TypeError, ValueError, IndexError) as e:
        _logger.debug('GPS DMS conversion failed: %s', e)
        return None
