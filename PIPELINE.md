# Customer Lifetime Value (CLV) & Segmentation Pipeline

## Overview

This pipeline computes, scores, and segments customers by their **Customer Lifetime Value (CLV)** — the predicted net revenue a business can expect from each customer over their entire relationship. Outputs are used to drive targeted marketing, retention strategies, and resource prioritisation.

---

## Pipeline Stages

### 1. Data Generation — `scripts/generate_clv_data.py`
Produces or ingests raw customer transaction records. Outputs structured data files to the `data/` directory for downstream processing.

### 2. Cleaning & Scoring — `scripts/clean_and_score_clv.py`
- Cleans and validates raw transaction data (deduplication, null handling, type coercion).
- Engineers CLV-relevant features: purchase frequency, average order value, customer tenure, churn probability.
- Applies a scoring model (RFM-based or probabilistic) to assign each customer a CLV score and segment label (e.g. High-Value, At-Risk, Dormant, New).

### 3. SQL Analysis — `scripts/run_clv_queries.sql`
Runs aggregate queries against the scored dataset to surface:
- Segment-level revenue contribution.
- Cohort retention rates.
- Top-N high-value customers.
- Churn risk distribution.

### 4. Summary Reporting — `scripts/generate_clv_summar.py`
Generates human-readable summary reports and exports segment-level insights ready for consumption in Power BI or other BI tools.

---

## Directory Structure

```
customer-clv-segmentation/
├── data/               # Raw and processed data files (not tracked by git)
├── powerbi/            # Power BI report templates and exports
├── scripts/
│   ├── generate_clv_data.py        # Stage 1 – Data ingestion / generation
│   ├── clean_and_score_clv.py      # Stage 2 – Cleaning, feature engineering & scoring
│   ├── run_clv_queries.sql         # Stage 3 – SQL-based analysis
│   └── generate_clv_summar.py      # Stage 4 – Summary reporting
├── .gitignore
├── PIPELINE.md         # This file
└── README.md
```

---

## Key Concepts

| Term | Definition |
|------|------------|
| **CLV** | Customer Lifetime Value — total net revenue expected from a customer |
| **RFM** | Recency, Frequency, Monetary — a classic segmentation framework |
| **Churn** | A customer becoming inactive or disengaging from the business |
| **Segment** | A group of customers with similar CLV characteristics |

---

## Getting Started

1. **Install dependencies** (if any — see `requirements.txt` when added).
2. **Run data generation:** `python scripts/generate_clv_data.py`
3. **Clean and score:** `python scripts/clean_and_score_clv.py`
4. **Execute SQL queries** against your database or query engine using `scripts/run_clv_queries.sql`.
5. **Generate summaries:** `python scripts/generate_clv_summar.py`
6. Open the Power BI report from the `powerbi/` folder for visual exploration.

---

## Notes

- All data files (`data/*.csv`, `data/*.json`) are excluded from version control via `.gitignore`.
- Secrets and environment variables must be stored in a `.env` file (also excluded from version control).
