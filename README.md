# 🛡️ TrueROAS | Decision Accountability Platform

TrueROAS is a production-grade reconciliation engine designed for scaling e-commerce brands. Unlike traditional analytics tools that simply report history, TrueROAS enforces strategic accountability by verifying marketing decisions against verified financial outcomes from Shopify and Meta Ads.

## 🛡️ Core Philosophy: Decisions over Dashboards
Analytics tell you what happened. **TrueROAS proves if your strategy worked.** We track **Decision Accuracy**—the only metric that matters for long-term capital growth—by reconciling platform claims with bank-truth data.

## 🚀 Key Features
- **Bayesian Reconciliation:** Merges Platform Priors (Meta) with Business Truth (Shopify) using a Normal-Normal conjugate prior model to calculate risk-adjusted ROAS.
- **Decision Audit Trail:** Automatically logs and reconciles strategic moves (e.g., scaling a campaign) after 7, 30, and 90 days to determine actual ROI.
- **Strategy Feedback Loop:** A "Strategic Memory" engine that identifies systematic biases in past decisions to recalibrate future scaling advice.
- **Circuit Breaker:** Real-time safety caps to prevent runaway ad spend when variance exceeds historical thresholds.
- **Multi-Tenant Architecture:** Isolation using per-tenant SQLite databases (WAL mode) with PII protection via Keyed BLAKE2b hashing.
- **Automated Lead Nurture:** High-conversion 5-email drip sequence via Resend integration.
- **Production Webhooks:** Secure, signature-verified handlers for Stripe (subscriptions) and Shopify (real-time order/refund sync).
- **Merchant Verdicts:** Translates complex statistical variance into plain-English strategic advice and financial risk assessments ($).

## 🛡️ Reliability Disclaimer
No system is 100% secure. While TrueROAS uses industry-standard hashing and database isolation, we recommend regular manual audits of high-value scaling decisions.

## 🛠️ Tech Stack
- **Backend:** FastAPI (Python 3.10+)
- **Database:** SQLite (Tenant Warehouse), PostgreSQL (Central Metadata)
- **Analytics:** DuckDB, SciPy (Statistical Inference)
- **Worker Engine:** Celery + Redis
- **Infrastructure:** Docker & Docker Compose
- **Integrations:** Stripe Checkout, Resend Email API

## ⚙️ Setup Instructions

### 1. Environment Configuration
Copy `.env.example` to `.env` and configure your production secrets:

```bash
# Security
APP_SECRET_SALT=your-unique-32-character-minimum-salt

# Payment & Email
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
RESEND_API_KEY=re_...

# Integrations
SHOPIFY_API_SECRET=...
SHOPIFY_TOKEN=...
META_AD_ACCOUNT_ID=...
META_ACCESS_TOKEN=...
```

### 2. Initialization
Ensure you have Docker installed and run the full stack:

```bash
docker-compose up --build
```

The system will automatically apply migrations for the central database and initialize the default tenant during the lifespan startup event.

## 📈 Primary API Endpoints
| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/sync` | `POST` | Trigger data reconciliation for a tenant. |
| `/api/v1/metrics` | `GET` | Fetch risk-adjusted ROAS and Decision Accuracy. |
| `/api/v1/webhooks/stripe` | `POST` | Manage subscription lifecycle (Active/Canceled). |
| `/api/v1/leads/` | `POST` | Capture and initiate nurture sequence. |
| `/api/v1/export/detailed-audit-csv` | `GET` | Download full proof metrics for external auditing. |

---
*© 2024-2026 TrueROAS Team. All rights reserved. Proprietary and confidential.*
*Precision over vanity.*