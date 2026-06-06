import os
import random
from typing import Dict

import duckdb

from trueroas.core.config import settings
from trueroas.core.inference import DecisionEngine


def sync_shopify(db_path: str) -> Dict[str, int]:
    """
    DEMO: Generates individual simulated orders to calculate
    statistical variance and confidence via Welford's Algorithm.
    """
    token = settings.SHOPIFY_TOKEN

    # Use context manager to prevent database locks and ensure clean closures.
    with duckdb.connect(db_path) as con:
        rows = con.execute(
            "SELECT clean_date, normalized_spend, meta_roas FROM historical_metrics WHERE order_id LIKE 'meta_%'"
        ).fetchall()

        for date, spend, meta_roas in rows:
            if not token:  # Demo.
                # 1. Determine target daily revenue (30-40% lower than Meta)
                target_daily_revenue = spend * (meta_roas * random.uniform(0.6, 0.7))

                # 2. Simulate individual orders to create variance
                num_orders = random.randint(5, 15)
                avg_order_val = target_daily_revenue / num_orders

                # Initialize running stats
                count: int = 0
                mean: float = 0.0
                var: float = 0.0
                conf: float = 0.0

                for _ in range(num_orders):
                    # Create an individual order value with noise
                    order_value = avg_order_val * random.uniform(0.5, 1.5)
                    # Update stats using Welford's algorithm
                    count, mean, var, conf = DecisionEngine.update_historical_stats(
                        count, mean, var, order_value
                    )

                total_revenue = mean * count
                true_roas = total_revenue / spend
                true_cac = spend / max(count, 1)
            else:
                total_revenue = 0
                true_roas = 0
                true_cac = 0
                count, var, conf = 0, 0, 0

            con.execute(
                """
                UPDATE historical_metrics 
                SET true_revenue=?, true_roas=?, true_cac=?, 
                    order_count=?, revenue_variance=?, confidence_score=?
                WHERE clean_date=? AND order_id LIKE 'meta_%'
            """,
                [total_revenue, true_roas, true_cac, count, var, conf, date],
            )

        return {"synced": len(rows)}


if __name__ == "__main__":
    from src.trueroas.core.migrations import apply_migrations

    # Calculate paths for standalone execution from project root
    current_file_path = os.path.abspath(__file__)
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))
    )
    tenant_db_path = os.path.join(
        project_root, "data", "tenants", "default", "warehouse.duckdb"
    )

    print(
        f"--- Shopify Sync Audit (Mode: {'LIVE' if settings.SHOPIFY_TOKEN else 'DEMO'}) ---"
    )

    try:
        # Ensure tables are initialized before sync
        apply_migrations(tenant_db_path)

        result = sync_shopify(tenant_db_path)
        print(f"Success: {result}")
    except Exception as e:
        print(f"Sync failed: {e}")
