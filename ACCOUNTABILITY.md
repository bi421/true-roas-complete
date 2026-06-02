# TrueROAS Decision Accountability

Unlike standard reporting tools, TrueROAS tracks its own accuracy to build a verifiable track record of strategic success.

---

## 1. The Learning Loop
Every time a simulation is run or a recommendation is generated, the system creates an immutable record in the `decision_audit_trail`:

1. **Commitment:** The engine records its Predicted EV and Confidence.
2. **Observation:** Background workers monitor real Shopify profit deltas over the next 7–14 days.
3. **Reconciliation:** The `reconcile_decisions.py` worker compares the prediction against the actual outcome.
4. **Scoring:** The "Decision Accuracy Score" is updated.

---

## 2. Audit Trail Schema
The `decision_audit_trail` table stores:
- `predicted_ev`: Weighted financial expectation.
- `predicted_confidence`: Statistical certainty at time of decision.
- `assumptions_json`: The CTR/CR floors used for the decision.
- `actual_outcome`: Realized profit delta.
- `is_successful`: Binary accuracy indicator.

---

## 3. Research Engine Metrics
For the **Risk Manager** role, we calculate advanced Decision Science metrics:

| Metric | Purpose |
| :--- | :--- |
| **Accuracy Score** | % of successful vs. predicted outcomes. |
| **Brier Score** | Measures the calibration of probability forecasts. |
| **Systematic Bias** | Detects if the model is consistently over-optimistic or conservative. |
| **Error Drift** | Tracks how accuracy decays from 7 to 90 days. |

---
**Precision over vanity. Evidence over assumptions. Decisions over dashboards.**
