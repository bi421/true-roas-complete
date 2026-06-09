# TrueROAS Zero-Touch Self-Learning System

## Overview
The Learning System automatically tunes campaign thresholds (pause/scale) based on historical decision accuracy (Brier Scores) recorded in the `decision_audit_trail`. 

## Architectural Integration
This system is implemented as a **Zero-Modification Plugin**. It hooks into the existing Celery worker pool using Celery signals.

### Celery Signal Hook
In `src/trueroas/learning/integration.py`, the system connects to the `task_success` signal of the `reconcile_decisions` task. When a reconciliation batch completes, the learning engine automatically evaluates the calibration of the forecasts against the actual outcomes.

## WORM Proof Format
All policy updates are immutable and signed using HMAC-SHA256. 
The signature is generated from a canonical JSON string:
- Keys sorted alphabetically.
- No unnecessary whitespace (`separators=(',', ':')`).
- Signed with the existing `APP_SECRET_SALT`.

Format:
`HMAC-SHA256(APP_SECRET_SALT, {"break_even_roas": 3.3, "min_confidence_prob": 0.8, "tenant_id": "..."})`

## Configuration
The learning system can be toggled globally via the `.env` file:

```bash
LEARNING_ENABLED=True  # Set to False to disable auto-tuning
```

## Migrations
To enable the system, run the additive migration script:
`python -m trueroas.learning.migrate`