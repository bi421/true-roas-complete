
CREATE TABLE IF NOT EXISTS historical_metrics (
    account_id VARCHAR,
    order_id VARCHAR,
    clean_date DATE,
    normalized_spend DOUBLE,
    true_revenue DOUBLE,
    true_roas DOUBLE,
    true_cac DOUBLE,
    meta_roas DOUBLE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (account_id, order_id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID DEFAULT gen_random_uuid(),
    action_type VARCHAR,
    details JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
