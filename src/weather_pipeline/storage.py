# Upload files to the Backblaze bucket (it speaks the S3 language)
import boto3
from botocore.config import Config

from . import config


def upload(local_path, key):
    s3 = boto3.client(
        "s3",
        endpoint_url=config.B2_ENDPOINT,
        aws_access_key_id=config.B2_KEY_ID,
        aws_secret_access_key=config.B2_APP_KEY,
        # newer boto3 adds checksums that Backblaze can reject, so only use them when required
        config=Config(request_checksum_calculation="when_required",
                      response_checksum_validation="when_required"),
    )
    s3.upload_file(str(local_path), config.B2_BUCKET, key)