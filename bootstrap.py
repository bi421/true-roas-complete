#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

import sqlite3
from src.trueroas.core.database import get_db_path


class PolicyBootstrapper:
    """
    Auto-generates initial thresholds based on local merchant data.
    """

    @staticmethod
    def derive_break_even_roas(tenant_id: str) -> float:
        """
        Read last 90d orders from tenant SQLite (local, ZK compliant).
        """
        db_path = get_db_path(tenant_id)
        try:
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                query = "SELECT SUM(revenue), SUM(cogs), SUM(shipping) FROM orders WHERE created_at > date('now', '-90 days')"
                cursor.execute(query)
                row = cursor.fetchone()
                if not row or not row[0]:
                    return 1.54

                margin = (row[0] - (row[1] or 0) - (row[2] or 0)) / row[0]
                return round(1.0 / margin, 2) if margin > 0 else 1.54
        except Exception:
            return 1.54
