# \# TrueROAS v1.0 Production 🛡️

# 

# TrueROAS is an enterprise-grade precision marketing analytics engine. 

# It reconciles Meta Ads telemetry with actual Shopify financial settlements, 

# identifying the gap between platform reporting and business reality.

# 

# > \*"Meta says 4.2x. Shopify says 2.69x. TrueROAS tells you why."\*

# 

# \## 🚀 Overview

# 

# TrueROAS transitions from `DEMO\_MODE` to `LIVE` by integrating directly 

# with Meta Graph API v21.0 and Shopify Admin API 2024-01. It employs a 

# 7-stage Polars pipeline and DuckDB OLAP warehouse for sub-second 

# reconciliation and audit scoring.

# Compatible with Meta Advantage+, Crush AI, Motion, and all 3rd-party media buyers.

# 

# \## 🛠 Features

# 

# \- \*\*Live Data Connectors\*\*: Async connectors for Meta + Shopify with rate-limiting and cursor-based pagination.

# \- \*\*7-Stage Refinement Pipeline\*\*: Bot removal, deduplication, attribution normalization, incrementality calculation.

# \- \*\*Truth Reconciliation\*\*: True ROAS using 7d\_click, 1d\_click, 1d\_view per Meta 2026.03 policy vs Shopify settled revenue.

# \- \*\*Andromeda ML Engine\*\*: Prophet-based organic baseline modeling.

# \- \*\*Financial Circuit Breaker\*\*: Auto-halt if variance > 10% for 2 weeks.

# \- \*\*Telegram Guardian Bot\*\*: Real-time alerts + approval gates.

# \- \*\*Privacy First\*\*: BLAKE2b salted PII hashing before any persistence.

# 

# \## 📦 Project Structure

# 

# ```mermaid

# graph LR

# &#x20;   Project\[true-roas-shopify]

# &#x20;   Project --> Src\[src/trueroas]

# &#x20;   Project --> Data\[data: DuckDB Storage]

# &#x20;   Project --> Files\[Root Scripts]

# 

# &#x20;   Src --> API\[api: FastAPI \& Routes]

# &#x20;   Src --> Core\[core: Reconciliation \& ML]

# &#x20;   Src --> Ingest\[ingestion: API Connectors]

# &#x20;   Src --> Pipe\[pipeline: Polars Pipeline]

# &#x20;   Src --> Wh\[warehouse: DuckDB Schema]

# &#x20;   Src --> Math\[math: Core Metrics]

# 

# &#x20;   Files --> Setup\[setup\_v1.py]

# &#x20;   Files --> Bot\[bot.py]

# &#x20;   Files --> Main\[main.py]

# ```

# 

# \## ⚡️ Quick Start

# 

# \### 1. Configure Environment

# 

# \*\*Windows:\*\*

# ```cmd

# copy .env.example .env

# ```

# Fill in your `META\_ACCESS\_TOKEN`, `META\_AD\_ACCOUNT\_ID`, `SHOPIFY\_STORE\_URL`, `SHOPIFY\_ACCESS\_TOKEN`, and Telegram credentials.

# 

# \### 2. Initialize Warehouse

# Run the setup script to initialize directories, validate credentials, and apply database migrations:

# ```bash

# python setup\_v1.py

# ```

# 

# \### 3. Start API Server

# Run the production server using Uvicorn:

# ```bash

# uvicorn main:app --host 0.0.0.0 --port 8000

# ```

# 

# \### 4. Deploy Guardian Bot

# ```bash

# python bot.py

\### 5. Export for Meta CAPI (Manual Mode)

If you prefer not to give API access, use Manual Mode:



1\. Visit `http://localhost:8000/api/v1/export/meta-capi-csv` to download CSV

2\. Go to Meta Events Manager → Data Sources → Your Pixel → Settings

3\. Click "Upload Offline Events" → Upload the CSV

4\. Meta will auto-deduplicate using `event\_id` for EMQ >8.0



\*\*Why Manual?\*\* You keep full control of PII. TrueROAS never sees customer emails. Zero GDPR risk.

# ```

# 

# \## 📊 Monitoring \& API

# 

# \- \*\*Dashboard\*\*: Visit `http://localhost:8000/` for the real-time Truth dashboard.

# \- \*\*API Docs\*\*: Swagger UI is available at `http://localhost:8000/docs`.

# \- \*\*Health Check\*\*: Access `GET /health` to verify system status.

# \- \*\*Sync Trigger\*\*: POST to `/api/v1/sync` to force a data refresh.

# 

# \## 🛡 Security \& Compliance

# 

# TrueROAS is built with security as a priority:

# \- \*\*Zero Raw PII Persistence\*\*: Emails and phones are hashed using salt + BLAKE2b before ingestion.

# \- \*\*Audit Logging\*\*: Every autonomous action is recorded in an immutable ledger.

# \- \*\*Circuit Breaker\*\*: Automation is gated by financial variance thresholds (default 10%).

# \- ## Marketing ROAS vs Financial ROAS

# Tools like Wetracked measure total marketing impact across 28-day windows.

# TrueROAS measures Meta-specific settled cash in 7-day windows for CFO reporting.

# Use both for full picture.

# 

# \---

# \*TrueROAS: Precision over vanity.\*

