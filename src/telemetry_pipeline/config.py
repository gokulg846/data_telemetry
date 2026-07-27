from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "telemetry")
    postgres_user: str = os.getenv("POSTGRES_USER", "telemetry")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "telemetry_dev")
    s3_endpoint_url: str = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
    s3_access_key: str = os.getenv("S3_ACCESS_KEY", "minio")
    s3_secret_key: str = os.getenv("S3_SECRET_KEY", "minio123")
    s3_bucket: str = os.getenv("S3_BUCKET", "telemetry-raw")
    s3_region: str = os.getenv("S3_REGION", "us-east-1")
    alert_webhook_url: str = os.getenv("ALERT_WEBHOOK_URL", "")

    @property
    def postgres_dsn(self) -> str:
        return (
            f"host={self.postgres_host} port={self.postgres_port} "
            f"dbname={self.postgres_db} user={self.postgres_user} "
            f"password={self.postgres_password}"
        )
