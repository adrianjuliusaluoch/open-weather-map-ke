# Upload and download files in the Backblaze bucket (it speaks the S3 language)
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from . import config

def client():
    return boto3.client(
        "s3",
        endpoint_url=config.B2_ENDPOINT,
        aws_access_key_id=config.B2_KEY_ID,
        aws_secret_access_key=config.B2_APP_KEY,
        # newer boto3 adds checksums that Backblaze can reject, so only use them when required
        config=Config(request_checksum_calculation="when_required",
                      response_checksum_validation="when_required"),
    )

def upload(local_path, key):
    client().upload_file(str(local_path), config.B2_BUCKET, key)

def download_if_exists(key, local_path):
    # Returns False when the file is not in the bucket yet (first run)
    try:
        client().download_file(config.B2_BUCKET, key, str(local_path))
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
            return False
        raise