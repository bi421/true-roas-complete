#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

import sys
from unittest.mock import patch, MagicMock


@patch("trueroas.learning.auto_tuner.httpx.Client")
def test_learning_proof_zero_knowledge_compliance(mock_httpx: MagicMock) -> None:
    """
    Zero-Knowledge test: Mock the Proof Ingestion endpoint and assert
    the payload contains no PII or raw transaction outcomes.
    """
    # Setup mock data for PolicyStore
    mock_policy_store_instance = MagicMock()
    mock_policy_store_instance.is_enabled.return_value = True
    mock_policy_store_instance.get_audit_trail_for_learning.return_value = [
        {"ev": 2.0, "conf": 0.9, "outcome": "FAILURE"}
    ] * 5  # Must provide at least 5 samples to satisfy the AutoTuner safety guard
    mock_policy_store_instance.get_latest_policy.return_value = {"pause_threshold": 1.0}

    # Setup mock for learning_settings
    mock_learning_settings = MagicMock()
    mock_learning_settings.learning_enabled = True
    mock_learning_settings.learning_min_samples = 1

    # Setup mock for PolicySigner
    mock_policy_signer = MagicMock()
    mock_policy_signer.sign_policy.return_value = "mock_signature"

    # Setup mock for core config settings
    mock_core_settings = MagicMock()
    mock_core_settings.APP_PORT = 8001
    mock_core_settings.APP_SECRET_SALT = "test_salt_32_chars_long_exactly_!!"

    # Patch modules within the test scope
    with patch.dict(
        sys.modules,
        {
            "trueroas.learning.policy_store": MagicMock(
                PolicyStore=MagicMock(return_value=mock_policy_store_instance)
            ),
            "trueroas.learning.config": MagicMock(
                learning_settings=mock_learning_settings
            ),
            "trueroas.learning.worm_proof": MagicMock(
                PolicySigner=mock_policy_signer
            ),
            "trueroas.core.config": MagicMock(settings=mock_core_settings),
            "trueroas.core.database": MagicMock(
                SessionLocal=MagicMock(
                    return_value=MagicMock(
                        __enter__=MagicMock(return_value=MagicMock()),
                        __exit__=MagicMock(),
                    )
                )
            ),
        },
    ):
        # Import the function after patching is set up
        from trueroas.learning.auto_tuner import process_reconciled_batch

        # Mock httpx client context manager
        mock_client = MagicMock()
        mock_httpx.return_value.__enter__.return_value = mock_client

        # Execute the function
        process_reconciled_batch("tenant_abc")

        # Verify the HTTP POST request was made
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        payload = kwargs["json"]

        # ZK Compliance check
        assert payload["true_roas"] is None
        assert payload["meta_roas"] is None
        assert "predicted_ev" not in payload
        assert "actual_outcome" not in payload
