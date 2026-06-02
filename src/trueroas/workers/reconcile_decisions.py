import duckdb
import json

def reconcile_past_decisions(db_path: str):
    """
    Analyses decisions made 7 days ago by comparing the profit 
    in the 7 days following the decision against the 7 days prior.
    """
    with duckdb.connect(db_path) as con:
        pending = con.execute("""
            SELECT decision_id, account_id, timestamp, predicted_ev, assumptions_json 
            FROM decision_audit_trail 
            WHERE reconciled_at IS NULL 
            AND timestamp <= CURRENT_TIMESTAMP - INTERVAL '7 days'
        """).fetchall()

        for d_id, acct_id, decision_ts, predicted_ev, assumptions_raw in pending:
            # Use captured financial logic for true audit
            assumptions = json.loads(assumptions_raw)
            v_rate = assumptions.get('v_rate', 0.4)
            t_rate = assumptions.get('t_rate', 0.0)
            margin = 1.0 - v_rate - t_rate

            # 1. Calculate Profit in the 7 days BEFORE the decision
            prior_profit = con.execute("""
                SELECT SUM(true_revenue * ? - normalized_spend) 
                FROM historical_metrics 
                WHERE clean_date < ? AND clean_date >= ?::DATE - INTERVAL '7 days'
            """, [margin, decision_ts, decision_ts]).fetchone()[0] or 0.0

            # 2. Calculate Profit in the 7 days AFTER the decision
            post_profit = con.execute("""
                SELECT SUM(true_revenue * ? - normalized_spend) 
                FROM historical_metrics 
                WHERE clean_date >= ? AND clean_date < ?::DATE + INTERVAL '7 days'
            """, [margin, decision_ts, decision_ts]).fetchone()[0] or 0.0

            actual_delta = post_profit - prior_profit
            
            # Recommendation was successful if:
            # 1. Action was scaling and profit increased
            # 2. Action was hold/reduce and profit didn't collapse (> -20% drawdown)
            success_threshold = predicted_ev if predicted_ev > 0 else (prior_profit * -0.2)
            
            # 3. Success Criteria: Did the realized delta match the predicted direction?
            if predicted_ev > 0:
                is_success = actual_delta > 0
            else:
                # For defensive moves, success is preventing a significant loss
                is_success = actual_delta >= success_threshold 
            
            con.execute("""
                UPDATE decision_audit_trail 
                SET actual_outcome = ?, is_successful = ?, reconciled_at = CURRENT_TIMESTAMP,
                    outcome_7d = ?, outcome_30d = NULL
                WHERE decision_id = ?
            """, [actual_delta, is_success, post_profit, d_id])
            
        return len(pending)