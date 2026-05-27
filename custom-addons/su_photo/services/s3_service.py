# -*- coding: utf-8 -*-
"""S3 (MinIO) client wrapper for photo storage."""
import logging
import os
import uuid
from datetime import datetime

_logger = logging.getLogger(__name__)


class S3Service:
    """Lazy-initialized S3 client for MinIO photo uploads.

    Configuration via environment variables:
    - S3_ENDPOINT: MinIO endpoint URL (e.g. http://minio:9000)
    - S3_ACCESS_KEY: MinIO access key
    - S3_SECRET_KEY: MinIO secret key
    - S3_BUCKET: bucket name (default: stroiuprav)
    """

    _client = None

    @classmethod
    def _get_client(cls):
        if cls._client is None:
            import boto3
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
                region_name='us-east-1',
            )
        return cls._client

    @classmethod
    def reset_client(cls):
        """Reset cached client (for testing)."""
        cls._client = None

    @classmethod
    def get_bucket(cls):
        return os.environ.get('S3_BUCKET', 'stroiuprav')

    @classmethod
    def upload(cls, binary_data, company_id, project_id, extension):
        """Upload binary data to S3.

        Args:
            binary_data: raw bytes of the image
            company_id: int, company ID for key namespacing
            project_id: int, project ID for key namespacing
            extension: str, file extension without dot (e.g. 'jpeg')

        Returns:
            str: S3 object key

        Raises:
            Exception: on S3 upload failure
        """
        client = cls._get_client()
        bucket = cls.get_bucket()
        date_prefix = datetime.utcnow().strftime('%Y-%m')
        file_uuid = uuid.uuid4().hex
        s3_key = (
            f"photos/{company_id}/{project_id}/"
            f"{date_prefix}/{file_uuid}.{extension}"
        )

        content_type_map = {
            'jpeg': 'image/jpeg',
            'jpg': 'image/jpeg',
            'png': 'image/png',
            'heic': 'image/heic',
            'heif': 'image/heif',
        }
        content_type = content_type_map.get(extension, 'application/octet-stream')

        client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=binary_data,
            ContentType=content_type,
        )
        _logger.info('Uploaded photo to S3: %s (%d bytes)', s3_key, len(binary_data))
        return s3_key

    @classmethod
    def get_presigned_url(cls, s3_key, expires_in=3600):
        """Generate a presigned GET URL for the given S3 key.

        Args:
            s3_key: str, the S3 object key
            expires_in: int, URL validity in seconds (default: 1 hour)

        Returns:
            str: presigned URL
        """
        client = cls._get_client()
        bucket = cls.get_bucket()
        return client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': s3_key},
            ExpiresIn=expires_in,
        )

    @classmethod
    def delete(cls, s3_key):
        """Delete an object from S3.

        Args:
            s3_key: str, the S3 object key
        """
        client = cls._get_client()
        bucket = cls.get_bucket()
        client.delete_object(Bucket=bucket, Key=s3_key)
        _logger.info('Deleted photo from S3: %s', s3_key)
