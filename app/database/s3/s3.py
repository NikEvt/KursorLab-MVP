import os
import logging
from botocore.session import Session
from botocore.config import Config
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Загрузка переменных окружения из .env
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

class S3Client:
    def __init__(
        self,
        access_key: str,
        secret_key: str,
        endpoint_url: str,
        bucket_name: str,
        region_name: str = None
    ):
        """
        :param access_key: AWS Access Key ID
        :param secret_key: AWS Secret Access Key
        :param endpoint_url: S3-compatible endpoint URL
        :param bucket_name: Name of the S3 bucket
        :param region_name: (optional) AWS region
        """
        self.bucket_name = bucket_name
        # Создаем конфиг для отключения payload signing (избежать SHA256Mismatch) и SigV2
        self.client_config = Config(
            signature_version="s3",  # SigV2, не рассчитывает SHA256 тела
            s3={"payload_signing_enabled": False}
        )
        session = Session()
        client_kwargs = {
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "endpoint_url": endpoint_url,
            "use_ssl": True,
        }
        if region_name:
            client_kwargs["region_name"] = region_name

        # Инициализируем клиент с нашим Config
        self.client = session.create_client(
            "s3",
            config=self.client_config,
            **client_kwargs
        )
        logger.info("S3 client created with SigV2 and payload signing disabled.")

    def put_object(self, object_key: str, body: bytes | str, content_type: str = None) -> dict:
        """Upload arbitrary content to S3"""
        try:
            kwargs = {
                "Bucket": self.bucket_name,
                "Key": object_key,
                "Body": body,
            }
            if content_type:
                kwargs["ContentType"] = content_type
            resp = self.client.put_object(**kwargs)
            status = resp["ResponseMetadata"]["HTTPStatusCode"]
            logger.info(f"Put object '{object_key}', HTTP {status}")
            return resp
        except ClientError as e:
            logger.error(f"Error putting object '{object_key}': {e}")
            raise

    def get_object(self, object_key: str) -> bytes:
        """Retrieve object content from S3 as bytes"""
        try:
            resp = self.client.get_object(Bucket=self.bucket_name, Key=object_key)
            data = resp["Body"].read()
            logger.info(f"Retrieved '{object_key}', {len(data)} bytes")
            return data
        except ClientError as e:
            logger.error(f"Error retrieving '{object_key}': {e}")
            raise

    def download_file(self, object_key: str, dest_path: str) -> None:
        """Download S3 object to a local file"""
        data = self.get_object(object_key)
        with open(dest_path, "wb") as f:
            f.write(data)
        logger.info(f"Downloaded '{object_key}' to '{dest_path}'")

# Инициализация глобального клиента из .env
S3_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
S3_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_ENDPOINT = os.getenv("S3_ENDPOINT_URL")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_REGION = os.getenv("S3_REGION")

if not all([S3_ACCESS_KEY, S3_SECRET_KEY, S3_ENDPOINT, S3_BUCKET]):
    logger.error("Incomplete S3 configuration in .env")
    raise RuntimeError("Missing S3 config variables")

s3_client = S3Client(
    access_key=S3_ACCESS_KEY,
    secret_key=S3_SECRET_KEY,
    endpoint_url=S3_ENDPOINT,
    bucket_name=S3_BUCKET,
    region_name=S3_REGION
)
