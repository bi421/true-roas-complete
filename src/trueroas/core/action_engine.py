#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import logging
import csv
import io
import duckdb
from typing import Dict, Any

logger = logging.getLogger("trueroas.action_engine")


async def execute_circuit_breaker(
    tenant_id: str,
    action_required: str,
    campaign_id: str,
    access_token: str = "redacted",
) -> Dict[str, Any]:
    """
    Executes automated remediation logic. Currently logs the exact HTTP payload for Meta Ads API.
    """
    if action_required == "PAUSE_CAMPAIGN":
        # Target Meta Graph API structure for execution
        pause_payload = {
            "method": "POST",
            "url": f"https://graph.facebook.com/v21.0/{campaign_id}",
            "json": {"status": "PAUSED"},
            "headers": {"Authorization": f"Bearer {access_token}"},
        }

        logger.warning(
            f"EXECUTION_PLAN: Circuit Breaker for {tenant_id}. Target: PAUSE {campaign_id}. "
            f"Action Payload: {pause_payload}"
        )
        return {"status": "DRY_RUN_LOGGED", "action": "PAUSE", "payload": pause_payload}

    return {"status": "NO_ACTION_REQUIRED", "action": action_required}


async def generate_capi_truth_file(tenant_id: str, db_path: str) -> str:
    """
    Generates a CAPI-ready payload using reconciled data to correct Meta's attribution.
    """
    with duckdb.connect(db_path, read_only=True) as con:
        query = """
            SELECT clean_date, true_revenue, order_count, order_id
            FROM historical_metrics 
            WHERE clean_date >= CURRENT_DATE - INTERVAL 7 DAY
            ORDER BY clean_date DESC
        """
        results = con.execute(query).fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        # Fix 2: Add event_id to header to prevent Meta Ads double-counting
        writer.writerow(
            [
                "event_name",
                "event_time",
                "event_id",
                "action_source",
                "value",
                "currency",
            ]
        )
        for row in results:
            # Fix 2: Map order_id to event_id with system prefix
            event_id = f"trueroas_{row[3]}"
            writer.writerow(["Purchase", row[0], event_id, "website", row[1], "USD"])

        return output.getvalue()
