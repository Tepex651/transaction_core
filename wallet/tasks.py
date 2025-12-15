import logging
import random
import time

from celery import shared_task
from celery.app.task import Task as CeleryTask
from celery.exceptions import MaxRetriesExceededError

logger = logging.getLogger(__name__)


class NotificationTask(CeleryTask):
    autoretry_for = (Exception,)
    retry_kwargs = {
        "max_retries": 3,
        "countdown": 3,
    }
    retry_backoff = False
    retry_jitter = False


@shared_task(bind=True, base=NotificationTask)
def send_fake_notification(
    self: NotificationTask, wallet_id: str, message: str
) -> None:
    try:
        time.sleep(5)

        if random.choice([True, False]):
            raise Exception(f"Send to wallet {wallet_id} failed")

    except MaxRetriesExceededError:
        logger.error(
            "Notification failed permanently. wallet_id=%s",
            wallet_id,
        )
        raise

    except Exception as exc:
        print(f"Failed to send notification: {exc}, retrying...")
        raise self.retry(exc=exc, countdown=3)
