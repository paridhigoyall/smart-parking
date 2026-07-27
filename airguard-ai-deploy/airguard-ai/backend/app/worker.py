"""
Celery application for background work — currently just alert notification
delivery, structured so future async jobs (analytics rollups, predictive
maintenance scans) register here too.

Run the worker with:
    celery -A app.worker worker --loglevel=info
"""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "airguard_ai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_track_started=True,
)

celery_app.autodiscover_tasks(["app.tasks"])
