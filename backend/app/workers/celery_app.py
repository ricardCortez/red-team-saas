from celery import Celery
import os
from dotenv import load_dotenv

# Load .env so REDIS_URL is available even when not set in the OS environment
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "redteam",
    broker=redis_url,
    backend=redis_url,
    include=[],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
