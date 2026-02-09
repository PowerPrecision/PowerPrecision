"""Config package."""
from config.task_queue import (
    REDIS_URL,
    REDIS_MAX_CONNECTIONS,
    task_settings,
    get_redis_settings,
    TaskQueueSettings,
)
