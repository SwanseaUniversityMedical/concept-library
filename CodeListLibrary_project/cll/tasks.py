from celery import shared_task
from celery import Celery
from celery.utils.log import get_task_logger

import os

logger = get_task_logger(__name__)
