# TrueROAS v1.0

## Marketing Reconciliation & Decision Intelligence Platform

TrueROAS helps e-commerce businesses reconcile platform-reported marketing performance with business outcomes, enabling more informed and defensible budget decisions.

> Platform metrics tell you what was reported.
>
> TrueROAS helps you understand what happened, what might explain it, and what to investigate next.

---

# Why TrueROAS?

Marketing platforms, analytics tools, and financial systems often tell different stories.

A campaign may appear highly profitable in an advertising platform while financial outcomes suggest a different picture.

TrueROAS provides an independent reconciliation layer between:

* Meta Ads performance data
* Shopify business data
* Financial outcomes
* Operational signals

The goal is not to determine which platform is "right."

The goal is to help business owners make better decisions under uncertainty.

---

# Core Principles

### Evidence Before Conclusions

TrueROAS separates:

* Observations
* Findings
* Hypotheses
* Risks
* Recommendations

This reduces premature conclusions and encourages evidence-based decision making.

### Financial Reconciliation

Platform-reported results are compared against available business data to identify significant variances that may warrant investigation.

### Confidence-Based Recommendations

Recommendations are generated with explicit confidence levels and assumptions.

The system recognizes uncertainty rather than hiding it.

### Decision Intelligence

TrueROAS is designed to answer:

* What changed?
* Why might it have changed?
* How confident are we?
* What should we investigate next?
* What action is reasonable?

---

# Business Problems Addressed

### Attribution Uncertainty

Different platforms often claim credit for the same conversion.

### Reporting Variance

Marketing reports and business outcomes may not align.

### Budget Allocation Risk

Scaling decisions based solely on platform metrics can increase risk.

### Operational Blind Spots

Returns, refunds, tracking issues, and attribution settings can affect reported performance.

---

# What TrueROAS Does

## Data Collection

Integrates with:

* Meta Graph API
* Shopify APIs

## Reconciliation Engine

Processes and compares:

* Ad spend
* Platform-reported conversions
* Revenue signals
* Financial outcomes

## Variance Detection

Identifies meaningful differences between:

* Platform reporting
* Business outcomes

## Risk Monitoring

Monitors:

* Spend anomalies
* Variance thresholds
* Reconciliation gaps

## Reporting

Produces:

* Executive summaries
* Reconciliation reports
* Investigation guidance
* Decision-support recommendations

---

# Decision Intelligence Workflow

TrueROAS follows a structured process:

Observation

↓

Evidence Review

↓

Potential Explanations

↓

Confidence Assessment

↓

Risk Evaluation

↓

Recommended Next Actions

The objective is not certainty.

The objective is defensible decision making.

---

# Example Executive Output

## Observation

Platform-reported ROAS exceeds financially reconciled performance.

## Evidence

A material variance exists between advertising platform reporting and business outcome data.

## Possible Explanations

* Attribution overlap
* Tracking discrepancies
* Delayed reporting
* Refund activity
* Customer journey complexity

## Confidence

Medium

## Recommended Action

Investigate attribution settings and reconciliation variance before increasing spend.

---

# Key Features

* Multi-tenant architecture
* Automated schema migrations
* Financial circuit breaker
* Reconciliation engine
* CSV export workflows
* Telegram monitoring bot
* Confidence-based reporting
* Operational risk monitoring

---

# Security

Security is treated as a first-class requirement.

Features include:

* Salted hashing for sensitive identifiers
* Path sanitization
* Transactional migrations
* Tenant isolation
* Controlled configuration management

---

# Quick Start

## Configure Environment

Create a `.env` file using `.env.example`.

## Start API

```bash
python main.py
```

## Start Monitoring Bot

```bash
python bot.py
```

---

# Current Status

Version: v1.0

Development Status:

* Core reconciliation engine implemented
* Meta integration implemented
* Shopify integration implemented
* CSV export workflow implemented
* Decision intelligence layer evolving

---

# Philosophy

TrueROAS does not attempt to provide a perfect version of reality.

Instead, it provides an independently reconciled view of marketing performance and supports better business decisions through evidence, context, and structured analysis.

---

**TrueROAS**

*Precision over vanity. Evidence over assumptions. Decisions over dashboards.*
