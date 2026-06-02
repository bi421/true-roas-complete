# 🛡️ TrueROAS: Bayesian Marketing Audit & Intelligence Engine

### "Decisions over Dashboards."
**TrueROAS** is a high-precision **Audit Service System** designed to reconcile "overstated" ROAS reported by platforms (Meta, Google) with real-world financial outcomes (Shopify/Bank Data). It uses Bayesian statistics to diagnose the true return on marketing spend and identify capital efficiency bottlenecks.

> Platform metrics tell you what was reported.
> TrueROAS provides an independent reconciliation layer between marketing platforms and your bank account.
> **"Platforms can lie, but bank accounts never do."**

---

**Built for:** E-commerce founders, performance marketers, and CFOs who need verified ROI before scaling.

## 🚀 Business Outcomes
TrueROAS answers three business-critical questions:

1.  **Am I actually making money after advertising costs?**
    *   Independently reconcile Meta Ads performance against verified Shopify outcomes.
2.  **How much is the platform overstating my ROAS?**
    *   Identify the "Attribution Variance" to avoid scaling based on double-counted or inflated metrics.
3.  **What should I do next?**
    *   Get context-aware advice based on business constraints like Creative fatigue or Offer friction.

## 🔬 Deterministic Science over "AI Magic"
TrueROAS prioritizes deterministic statistical inference over black-box generative AI. Every recommendation is traceable to evidence, assumptions, and mathematical proofs using:
- **Bayesian Inference:** Normal-Normal conjugate priors to reconcile platform bias with financial reality.
- **SciPy Statistical Core:** Exact PDF/CDF probability modeling using the Normal Survival Function.
- **Pessimistic Bound (P10):** Risk management based on worst-case scenarios rather than just averages.

---

## 🚀 Key Value Propositions
*   **Bayesian Reconciliation:** Merges Meta ROAS with verified revenue to produce a "True Posterior ROAS."
*   **Waste Audit:** Quantifies monthly "inefficient spend" caused by inflated platform reporting.
*   **Safety Margin (P10):** Diagnoses the "Safety Zone" to ensure capital is protected even in high-volatility scenarios.
*   **Decision Accountability:** Tracks historical advice against actual outcomes to maintain a system "Accuracy Score."
*   **Audit PDF Export:** Generates professional strategic audit reports for CEOs and CFOs.

---

## 🏗️ System Architecture

*   **Core Logic:** Bayesian Reconciliation (SciPy) and Decision Intelligence Engines.
*   **Backend:** FastAPI (Python 3.10+).
*   **Data Warehouse:** DuckDB (Multi-tenant). Dedicated local files per tenant for extreme speed and isolation.
*   **Reporting Engine:** WeasyPrint (PDF Export) and Matplotlib (Visual Analytics).
*   **Accountability Layer:** Background workers that reconcile past decisions against future financial reality.

---

## 📊 Audit Workflow

1.  **Sync:** Connect Meta and Shopify via `/api/v1/sync`.
2.  **Analyze:** Diagnose performance health via `/api/v1/status`.
3.  **Audit:** Download the **Audit Report PDF** for strategic planning.
4.  **Correct:** Export the "Truth File" (CAPI CSV) to correct platform attribution.

---

## 🧠 11-Step Strategic Reasoning Logic
TrueROAS replaces "black box" advice with a traceable reasoning chain:
1. **Observation:** Detect divergence between platform and verified revenue.
2. **Evidence:** Quantify reconciliation variance and statistical confidence.
3. **Hypothesis:** Identify likely causes (e.g., Attribution Overlap).
4. **Decision Cost:** Quantify potential capital loss (Drawdown) of a wrong move.
5. **Delay Cost:** Quantify profit lost per 14 days of inaction.
6. **Evidence Quality:** Score data integrity based on Match Rate and Volatility.
7. **Readiness:** Measure business scaling capacity via CTR, CR, and Frequency.
8. **Conditions for Success:** "What Must Be True" (minimum metrics required).
9. **Expected Value (EV):** Probability-weighted financial return.
10. **Recommendation:** Actionable advice (e.g., STRONG_SCALE or REDUCE_OR_HOLD).
11. **Validation:** Post-decision monitoring plan.

---

## 🛠️ Installation & Setup

### 1. Prerequisites
*   Python 3.12+
*   Docker & Docker Compose
*   **Windows Users:** Install GTK+ Runtime for WeasyPrint PDF generation.

### 2. Production Deployment (Docker)
```bash
# 1. Configure .env with your secrets
# 2. Run in production mode
docker-compose -f docker-compose.prod.yml up -d --build
```

### 3. Configuration
Copy `.env.example` to `.env` and configure your credentials.
**Crucial:** Ensure `APP_SECRET_SALT` is a unique, long string to secure your PII hashing.

### 4. Initialize Database
```bash
# Migrations run automatically on first API start. Manual:
python src/trueroas/core/migrations.py
```

---

## 🔒 Security & Privacy

*   **Data Isolation:** Multi-tenant architecture using individual DuckDB files prevents cross-tenant data leakage.
*   **PII Protection:** Identifiers (Email/Phone) are salted and hashed locally; raw PII is never sent to marketing platforms.
*   **Auditability:** Every strategic suggestion includes a full trace of the underlying math and data points used.
*   **Circuit Breaker:** Operational guardrails prevent automated scaling if data variance exceeds safe thresholds.

---

## 📄 License
© 2024 TrueROAS Team. All rights reserved.

**"Precision over vanity. Evidence over assumptions. Decisions over dashboards."**
