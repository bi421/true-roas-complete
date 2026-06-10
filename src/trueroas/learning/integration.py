import logging
from typing import Any, Optional
from celery.signals import task_success
from trueroas.learning.config import learning_settings

logger = logging.getLogger("trueroas.learning.integration")


@task_success.connect  # type: ignore[untyped-decorator]
def on_reconcile_complete(
    tenant_id: Optional[str] = None, *args: Any, **kwargs: Any
) -> None:
    """
    Celery signal hook that triggers a learning cycle after reconciliation.
    Ensures Zero-Touch integration without modifying core worker tasks.
    """
    if not learning_settings.learning_enabled:
        return

    # We verify it's the reconciliation task.
    # Safely access sender.name, handling potential None
    sender_obj = kwargs.get("sender")
    if sender_obj is None:
        logger.warning("Learning hook triggered without a sender object.")
        return

    # Mypy untyped-decorator workaround: cast sender_obj to Any
    # to allow accessing .name without further type checking issues.
    sender_name = getattr(sender_obj, "name", "")
    if not sender_name or "reconcile_decisions" not in sender_name:
        return

    # Extract tenant_id from Celery result or kwargs
    if tenant_id is None:
        result = kwargs.get("result")
        if result:
            tenant_id = getattr(
                result,
                "tenant_id",
                result.get("tenant_id") if isinstance(result, dict) else None,
            )

    if not tenant_id:
        logger.warning("Learning hook triggered but no tenant_id found in context.")
        return

    try:
        # Local import to prevent circular dependencies at module load time
        from trueroas.learning.auto_tuner import process_reconciled_batch

        process_reconciled_batch(tenant_id)
    except Exception as e:
        logger.error(f"Learning cycle failed for tenant {tenant_id}: {e}")
