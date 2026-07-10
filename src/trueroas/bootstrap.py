#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

import duckdb
from typing import Dict, Any
from trueroas.core.database import get_db_path


class PolicyBootstrapper:
    """
    Auto-generates initial thresholds based on merchant business margins.
    """

    @staticmethod
    def generate_initial_config(target_margin: float) -> Dict[str, Any]:
        """
        Calculates break-even and scaling thresholds from target margin.
        Example: 0.3 margin (30%) -> 3.33x Break-even ROAS.
        """
        if not (0.01 <= target_margin <= 0.99):
            raise ValueError("Margin must be between 1% and 99%")

        # Break-even ROAS calculation: 1 / margin
        break_even = 1.0 / target_margin

        config: Dict[str, Any] = {
            "target_margin": round(target_margin, 4),
            "break_even_roas": round(break_even, 2),
            "scale_threshold": round(break_even * 1.25, 2),
            "strong_scale_threshold": round(break_even * 1.5, 2),
            "pause_threshold": round(break_even * 0.9, 2),
            "min_confidence_prob": 0.75,
        }
        return config

    @staticmethod
    def derive_break_even_roas(tenant_id: str) -> float:
        """
        Read last 90d orders from tenant SQLite (local, ZK compliant).
        margin = (revenue - cogs - shipping) / revenue
        return 1.0 / margin
        If no COGS data, return industry default 1.54.
        """
        db_path = str(get_db_path(tenant_id))
        try:
            with duckdb.connect(db_path) as conn:
                query = """
                    SELECT 
                        SUM(revenue), 
                        SUM(cogs), 
                        SUM(shipping)
                    FROM orders
                    WHERE created_at > (CURRENT_TIMESTAMP - INTERVAL '90 days')
                """
                row = conn.execute(query).fetchone()

                if not row or row[0] is None or row[0] <= 0:
                    return 1.54

                revenue = float(row[0])
                cogs = float(row[1]) if row[1] is not None else 0.0
                shipping = float(row[2]) if row[2] is not None else 0.0

                margin = (revenue - cogs - shipping) / revenue
                if margin <= 0:
                    return 1.54

                return round(1.0 / margin, 2)
        except (duckdb.Error, Exception):
            return 1.54


if __name__ == "__main__":
    import argparse
    from trueroas.core.database import SessionLocal
    from trueroas.learning.policy_store import PolicyStore
    from trueroas.learning.worm_proof import PolicySigner

    parser = argparse.ArgumentParser(
        description="Bootstrap TrueROAS Learning Policy for a tenant."
    )
    parser.add_argument("--tenant", required=True, help="Tenant slug/ID")
    args = parser.parse_args()

    be_roas = PolicyBootstrapper.derive_break_even_roas(args.tenant)
    initial_config = PolicyBootstrapper.generate_initial_config(
        1.0 / be_roas if be_roas > 0 else 0.65
    )

    with SessionLocal() as session:
        store = PolicyStore(session)
        sig = PolicySigner.sign_policy(initial_config)
        store.save_policy(args.tenant, initial_config, sig)
        print(f"✅ Success: Bootstrapped {args.tenant} with BE ROAS {be_roas}")