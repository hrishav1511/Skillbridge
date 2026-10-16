import os
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
import uuid
from datetime import datetime
from typing import Optional
from loguru import logger
from skillbridge.config import settings

# Leave credentials empty here. In cloud, use environment variables or an
# attached instance role so secrets are not stored in source code.

AWS_REGION = "us-east-1"
AWS_S3_BUCKET_NAME = "skillbridgeacademy-tutor-media"
AWS_S3_PREFIX = "tutor-media"

class S3Client:
    def __init__(
        self,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        aws_profile: str | None = None,
        region_name: str | None = None,
    ):
        self.bucket_name = os.getenv(
            "AWS_S3_BUCKET_NAME", settings.AWS_S3_BUCKET_NAME or AWS_S3_BUCKET_NAME
        )
        self.prefix = os.getenv(
            "AWS_S3_PREFIX", settings.S3_TUTOR_MEDIA_PREFIX or AWS_S3_PREFIX
        )
        self.region_name = region_name or os.getenv(
            "AWS_REGION", settings.AWS_REGION or AWS_REGION
        )
        self.last_error: str | None = None

        session_kwargs: dict[str, str] = {}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key
            if aws_session_token:
                session_kwargs["aws_session_token"] = aws_session_token
        else:
            configured_access_key = os.getenv("AWS_ACCESS_KEY_ID") or settings.AWS_ACCESS_KEY_ID
            configured_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY") or settings.AWS_SECRET_ACCESS_KEY
            configured_session_token = os.getenv("AWS_SESSION_TOKEN") or settings.AWS_SESSION_TOKEN
            if configured_access_key and configured_secret_key:
                session_kwargs["aws_access_key_id"] = configured_access_key
                session_kwargs["aws_secret_access_key"] = configured_secret_key
                if configured_session_token:
                    session_kwargs["aws_session_token"] = configured_session_token

        if not session_kwargs and aws_profile:
            session_kwargs["profile_name"] = aws_profile

        if session_kwargs:
            session = boto3.Session(**session_kwargs)
            self.s3_client = session.client(
                "s3",
                config=Config(
                    region_name=self.region_name,
                    signature_version="s3v4",
                ),
            )
        else:
            self.s3_client = boto3.client(
                "s3",
                config=Config(
                    region_name=self.region_name,
                    signature_version="s3v4",
                ),
            )

        logger.info(
            "S3 client initialized: bucket={}, region={}, prefix={}, "
            "access_key_configured={}, session_token_configured={}",
            self.bucket_name,
            self.region_name,
            self.prefix,
            bool(session_kwargs.get("aws_access_key_id")),
            bool(session_kwargs.get("aws_session_token")),
        )

    def generate_s3_key(self, folder: str, filename: str, tutor_id: str) -> str:
        """Generate S3 key/path for the file"""
        file_extension = filename.split(".")[-1].lower()
        unique_filename = f"{tutor_id}_{uuid.uuid4().hex[:8]}.{file_extension}"
        return f"{self.prefix}/{folder}/{unique_filename}"

    def upload_file(
        self, file_content: bytes, s3_key: str, content_type: str
    ) -> Optional[str]:
        """Upload file to S3 and return the URL"""
        self.last_error = None
        logger.info(
            "S3 upload started: bucket={}, region={}, key={}, bytes={}, content_type={}",
            self.bucket_name,
            self.region_name,
            s3_key,
            len(file_content),
            content_type,
        )
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata={
                    "uploaded_by": "skillbridge_backend",
                    "uploaded_at": str(datetime.utcnow()),
                },
            )
            logger.info("S3 upload completed: key={}", s3_key)
            return f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"
        except NoCredentialsError as exc:
            self.last_error = "AWS credentials were not found"
            logger.error("S3 upload failed: {}", self.last_error)
            return None
        except ClientError as exc:
            error = exc.response.get("Error", {})
            code = error.get("Code", "UnknownClientError")
            message = error.get("Message", str(exc))
            self.last_error = f"AWS {code}: {message}"
            logger.error(
                "S3 upload failed: bucket={}, region={}, key={}, error_code={}, "
                "error_message={}, request_id={}",
                self.bucket_name,
                self.region_name,
                s3_key,
                code,
                message,
                exc.response.get("ResponseMetadata", {}).get("RequestId"),
            )
            return None
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            logger.exception("S3 upload failed unexpectedly: key={}", s3_key)
            return None

    def generate_presigned_download_url(
        self, s3_key: str, expires_in: int = 300
    ) -> Optional[str]:
        try:
            return self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": s3_key},
                ExpiresIn=expires_in,
            )
        except (ClientError, NoCredentialsError) as exc:
            print(f"Error generating download URL: {exc}")
            return None

    def delete_file(self, s3_url: str) -> bool:
        """Delete file from S3"""
        try:
            key = s3_url.replace(f"https://{self.bucket_name}.s3.amazonaws.com/", "")
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except NoCredentialsError:
            print("Error deleting from S3: unable to locate credentials")
            return False
        except ClientError as e:
            print(f"Error deleting from S3: {e}")
            return False

    def delete_key(self, s3_key: str) -> bool:
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except (ClientError, NoCredentialsError) as exc:
            print(f"Error deleting S3 object: {exc}")
            return False


# Singleton instance
s3_client = S3Client()
