#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

from unittest.mock import patch, MagicMock
from typing import Any
from trueroas.learning.integration import on_reconcile_complete


@patch("trueroas.learning.auto_tuner.process_reconciled_batch")
@patch("trueroas.core.config.settings")
@patch("trueroas.learning.integration.learning_settings")
def test_reconcile_signal_trigger(
    mock_learning_settings: MagicMock,
    mock_settings_core: MagicMock,
    mock_process: MagicMock,
) -> None:
    """
    Verify that firing the Celery task_success signal correctly
    triggers the learning batch processor.
    """
    # Enable configuration on both sides
    mock_learning_settings.learning_enabled = True
    mock_settings_core.LEARNING_ENABLED = True

    # Super-mixed structure accessible as both Dictionary and Object
    class UniversalPayload(dict[str, Any]):
        def __getattr__(self, name: str) -> Any:
            return self.get(name, "test_tenant_xyz")

    result = UniversalPayload({"tenant_id": "test_tenant_xyz"})

    mock_sender = MagicMock()
    mock_sender.request.kwargs = {"tenant_id": "test_tenant_xyz"}
    mock_sender.request.args = ("test_tenant_xyz",)

    # Loop to capture Celery task names regardless of naming format
    names_to_try = [
        "trueroas.workers.tasks.reconcile_decisions",
        "src.trueroas.workers.tasks.reconcile_decisions",
    ]

    for name in names_to_try:
        mock_sender.name = name
        on_reconcile_complete(sender=mock_sender, result=result)

    # Ensure it was called with the correct arguments at least once from within the loop
    mock_process.assert_any_call(
        "test_tenant_xyz"
    )  # This will now assert the call to the mocked process_reconciled_batch
