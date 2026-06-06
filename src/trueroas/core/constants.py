#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

SOFT_VARIANCE_THRESHOLD = 0.30
HARD_VARIANCE_THRESHOLD = 0.50
MIN_ROAS_FLOOR = 0.01

# Meta Compliance: Retention window for Platform Data
META_DATA_RETENTION_DAYS = 120

# EU AI Act Article 13: Transparency. Penalty for data outside standard attribution windows.
ATTRIBUTION_LAG_PENALTY = 0.1

MIN_SAMPLE_SIZE = 10
EPSILON = 1e-9
ROAS_LOG_OFFSET = 0.01
ATTRIBUTION_LAG_HALF_LIFE = 7.0

# USA defaults
DEFAULT_TIMEZONE = "America/New_York"
DEFAULT_CURRENCY = "USD"
DEFAULT_DATE_FORMAT = "%m/%d/%Y"

# Rate limits
META_RATE_LIMIT_PER_HOUR = 180  # 90% of 200
META_PAUSE_COOLDOWN_SEC = 5
