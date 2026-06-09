#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import logging
from typing import Any
from celery.signals import task_postrun
from src.trueroas.workers.tasks import reconcile_decisions

logger = logging.getLogger("trueroas.learning.integration")


@task_postrun.connect(sender=reconcile_decisions)
def learning_hook(task_id: str, **kwargs: Any) -> None:
    """
    Celery signal hook that triggers a learning cycle after reconciliation.
    Ensures Zero-Touch integration without modifying core worker tasks.
    """
    try:
        from .auto_tuner import run_learning_cycle

        run_learning_cycle()
    except Exception as e:
        logger.error(f"Learning cycle execution failed for task {task_id}: {e}")
