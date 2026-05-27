# Customer Lifetime Value and Segmentation Pipeline

> An end-to-end analytics pipeline that generates, scores, and segments 100,000 domestic energy customers by Customer Lifetime Value, delivering actionable retention and cross-sell intelligence via SQL analysis and Power BI dashboards.

---

## Table of Contents

- [Business Problem and Solution](#business-problem-and-solution)
- [Pipeline Architecture](#pipeline-architecture)
- [Scripts](#scripts)
- [SQL Queries](#sql-queries)
- [Power BI Dashboard](#power-bi-dashboard)
- [Key Insights](#key-insights)
- [Recommendations](#recommendations)
- [Tech Stack](#tech-stack)
- [How to Run](#how-to-run)
- [Project Structure](#project-structure)
- [Data Note](#data-note)

---

## Business Problem and Solution

Energy retailers face a fundamental challenge: not all customers are equal in value, yet most retention and marketing budgets are allocated without distinguishing between a high-spending loyal customer and a dormant low-value account. Without a structured view of Customer Lifetime Value (CLV), commercial teams cannot prioritise retention spend, identify which customers to protect, or target cross-sell campaigns at the segments most likely to respond. This pipeline addresses that problem end-to-end. It generates a realistic dataset of 100,000 domestic energy customers, calculates a CLV score for each account based on spend, tenure, and renewal behaviour, applies an RFM (Recency, Frequency, Monetary) scoring framework to classify every customer into one of four segments: Champions, Loyal Customers, At Risk, and Lost Customers, and identifies which high-value customers carry elevated churn risk. The outputs flow through SQL-based analysis in DuckDB into a Power BI dashboard and plain-English summary report, giving commercial and marketing teams a data-driven basis for prioritising retention investment rather than treating all 100,000 customers the same.

---

## Pipeline Architecture

```
┌──────────────────────────┐     ┌──────────────────────────┐
│   generate_clv_data.py   │     │  clean_and_score_clv.py  │
│                          │────▶│                          │
│  Python · NumPy · Pandas │     │  Python · Pandas         │
│  100,000 synthetic       │     │  CLV score · RFM scoring │
│  customer records        │     │  Segment · Churn risk    │
└──────────────────────────┘     └────────────┬─────────────┘
                                              │
                              clean_clv_data.csv
                                              │
                    ┌─────────────────────────┴──────────────────────┐
                    │                                                 │
                    ▼                                                 ▼
     ┌──────────────────────────┐              ┌────────────────────────────┐
     │   run_clv_queries.sql    │              │   generate_clv_summary.py  │
     │                          │              │                            │
     │  SQL · DuckDB            │              │  Python · DuckDB           │
     │  6 analytical queries    │              │  Executes all 6 queries    │
     │  Segment · Region ·      │              │  Builds plain-English      │
     │  Payment · Products      │──────────────│  executive summary report  │
     └──────────────────────────┘              └────────────────────────────┘
                                                             │
                                                   clv_summary.txt
                                                             │
                                                             ▼
                                              ┌─────────────────────────┐
                                              │       Power BI          │
                                              │                         │
                                              │  3-page interactive     │
                                              │  dashboard              │
                                              └─────────────────────────┘
```

**Data flow:**
`raw_clv_data.csv` → `clean_clv_data.csv` → DuckDB (in-memory) → `clv_summary.txt` → Power BI

---

## Scripts

### 1. `scripts/generate_clv_data.py`

Generates 100,000 synthetic domestic energy customer records with realistic distributions across 15 columns. Uses `numpy` with `SEED = 42` for full reproducibility. Customer attributes include tariff type (Fixed, Variable, Prepay, Deemed, Economy 7, EV, Heat Pump), region, annual spend calibrated by tariff, payment method, product holdings, complaint history, smart meter adoption, app registration, and renewal behaviour. Churn flags are generated with a fleet-wide rate of approximately 12%, with elevated rates for Prepay tariff customers and those paying by Manual method.

**Output:** `data/raw_clv_data.csv` — 100,000 rows × 15 columns

| Column | Description |
|--------|-------------|
| `customer_id` | Unique identifier in format `A-XXXXXXXX` |
| `signup_date` | Uniformly distributed over the last 3 years |
| `tenure_months` | Months from signup to reference date |
| `tariff_type` | One of 7 domestic tariff types |
| `region` | North / South / East / West / Midlands |
| `annual_spend` | £400 – £2,500, higher for Fixed and Variable tariffs |
| `payment_method` | Direct Debit (60%) / Credit Card (20%) / Prepay (10%) / Manual (10%) |
| `num_products` | 1 – 5, weighted toward 1 and 2 |
| `complaint_count` | 0 – 8, Poisson-distributed |
| `late_payment_count` | 0 – 6, Poisson-distributed |
| `smart_meter` | Yes (70%) / No (30%) |
| `app_registered` | Yes (65%) / No (35%) |
| `renewal_count` | 0 – 8, correlated with tenure |
| `last_renewal_date` | Derived from renewal count and signup date |
| `churn_flag` | 1 = churned, 0 = active (~12% overall) |

---

### 2. `scripts/clean_and_score_clv.py`

Loads `raw_clv_data.csv` and engineers 7 derived columns. Calculates a CLV score for every customer, applies quintile-based RFM scoring using `pandas.qcut` with rank-based tie-breaking, sums the three RFM dimensions into a total score, and assigns each customer to a named segment and churn risk label using threshold rules.

**Output:** `data/clean_clv_data.csv` — 100,000 rows × 22 columns

| Derived Column | Logic |
|----------------|-------|
| `clv_score` | `annual_spend × (tenure_months / 12) × (renewal_count + 1)` |
| `rfm_recency` | 1–5 quintile; 5 = renewed most recently |
| `rfm_frequency` | 1–5 quintile; 5 = highest renewal count |
| `rfm_monetary` | 1–5 quintile; 5 = highest annual spend |
| `rfm_total` | Sum of recency + frequency + monetary (range: 3 – 15) |
| `segment` | Champions (13–15) · Loyal Customers (10–12) · At Risk (7–9) · Lost Customers (<7) |
| `churn_risk` | **High** if complaints ≥ 3, late payments ≥ 3, or rfm_recency ≤ 2 · **Low** if complaints = 0 and rfm_recency ≥ 4 · **Medium** otherwise |

---

### 3. `scripts/run_clv_queries.sql`

Six analytical SQL queries designed to run against a table named `customers`. Compatible with DuckDB, PostgreSQL, SQLite, and any ANSI SQL engine that supports window functions. Each query answers a specific commercial question about the customer base. See [SQL Queries](#sql-queries) for the full breakdown.

---

### 4. `scripts/generate_clv_summary.py`

Orchestration script that ties the full pipeline together. Loads `clean_clv_data.csv` into pandas, registers it as a DuckDB in-memory table called `customers`, parses `run_clv_queries.sql` (stripping inline comments before splitting on semicolons to handle edge cases), executes all six queries, extracts key values from the results, and produces a plain-English executive summary report. Includes structured logging at every step with timestamps.

**Output:** `data/clv_summary.txt`

---

## SQL Queries

All six queries in `run_clv_queries.sql` target the table `customers` and are executed sequentially by `generate_clv_summary.py` via DuckDB.

| # | Query | Business Question Answered |
|---|-------|---------------------------|
| 1 | **Segment Distribution** | How are customers distributed across CLV segments, what share of the portfolio does each segment represent, and what is the average CLV and annual spend per segment? |
| 2 | **Segment Profile** | What is the behavioural profile of each segment — covering tenure, spend, product holdings, complaint levels, smart meter and app adoption, and renewal activity? |
| 3 | **Churn Risk by Segment** | Within each segment, how are customers split across High / Medium / Low churn risk, and what is the average CLV for each segment-risk combination? Uses `PARTITION BY segment` window function for within-segment percentages. |
| 4 | **Regional CLV Performance** | Which regions deliver the strongest and weakest CLV? How do Champion and Lost Customer concentrations vary by geography? Uses `CASE WHEN` to derive segment flags without subqueries. |
| 5 | **Payment Method vs CLV** | How does payment method correlate with CLV, average late payments, and churn rate? Churn rate is derived as `AVG(churn_flag) * 100` without requiring a separate aggregation. |
| 6 | **Product Holdings vs CLV** | Does holding more products translate into higher CLV, lower churn, and more renewals — and by how much? Ordered ascending by `num_products` to surface the cross-sell progression clearly. |

---

## Power BI Dashboard

The Power BI report in `powerbi/` connects directly to `data/clean_clv_data.csv` and is structured across three pages.

### Page 1 — Executive Segment Overview

High-level KPI cards showing total customers, fleet-wide average CLV, overall churn rate, and total revenue at risk. A donut chart shows segment share of portfolio. A bar chart ranks segments by average CLV. A scatter plot maps average CLV against average annual spend by segment, sized by customer count. Slicers for region, tariff type, and payment method allow filtering across all visuals on the page.

### Page 2 — Churn Risk and Retention Intelligence

A stacked bar chart shows the churn risk composition (High / Medium / Low) within each segment, immediately surfacing the 83% High-risk concentration in Lost Customers versus the 1.8% in Champions. A matrix table lists every segment-risk combination with customer count, percentage share, and average CLV. A highlight card calls out the 230 Champions classified as High churn risk. A trend line shows how churn rate varies with complaint count and late payment count to support proactive intervention targeting.

### Page 3 — Regional and Commercial Performance

A filled map visual shows average CLV by UK region with colour intensity indicating performance relative to fleet average. Side-by-side bar charts compare Champion percentage and Lost Customer percentage by region. A table breaks down CLV, churn rate, and average late payments by payment method to quantify the Direct Debit versus Manual payer gap. A product cross-sell chart plots average CLV against number of products held, illustrating the incremental value of each additional product in the portfolio.

---

## Key Insights

**1. Champions generate six times the CLV of Lost Customers**
Champions represent **12.6% of customers** but generate an average CLV of **£13,572** versus Lost Customers at **£2,258** — a 6× difference. This concentration of value in a small segment means that protecting Champions delivers disproportionate financial return relative to the cost of intervention.

**2. 230 Champions are flagged High churn risk and represent an immediate retention priority**
Despite their high value, **230 Champions** have been classified as High churn risk due to elevated complaint counts, late payment flags, or low recency scores. Each of these customers represents over £13,500 of expected lifetime revenue. Losing them to churn without intervention is an avoidable commercial loss.

**3. 41.2% of the total fleet is flagged High churn risk**
**41,237 customers** across all segments carry a High churn risk classification. This represents a significant proportion of the portfolio and signals that engagement and retention programmes need to operate at scale, not just target individual high-value accounts.

**4. Revenue at risk from high churn customers is £209.79M**
Aggregating CLV across all customers flagged as High churn risk yields a total **revenue at risk of £209.79M**. This figure provides the commercial justification for retention investment — even a modest reduction in churn rate among this group returns multiples of the programme cost.

**5. CLV increases consistently with customer tenure, confirming that retention investment compounds over time**
The CLV formula `annual_spend × (tenure_months / 12) × (renewal_count + 1)` means that every additional year a customer stays — and every contract they renew — multiplies their lifetime value. Champions have an average tenure of **23.2 months** versus **16.0 months** for At Risk and Lost customers. Investing in early tenure engagement to extend customer lifetime is a high-return strategy.

**6. Customers with more products held have significantly higher CLV, supporting the cross-sell business case**
Analysis across the 1–5 product holding range confirms that multi-product customers generate greater lifetime value and exhibit lower churn rates. This validates the commercial case for cross-sell campaigns: embedding customers more deeply in the product ecosystem increases both their revenue contribution and their propensity to stay.

---

## Recommendations

**1. Launch immediate retention outreach to 230 Champions flagged High churn risk before they downgrade**
These customers sit at the intersection of maximum value and elevated risk. A targeted outreach programme — personalised offers, proactive account reviews, or dedicated account management contact — should be triggered immediately. The cost of intervention is negligible relative to the £13,500+ CLV each customer represents.

**2. Introduce Direct Debit incentives targeting Manual and Prepay customers to reduce their higher churn rate**
Manual payment customers exhibit the highest churn rate in the fleet at **21.6%**. Converting these customers to Direct Debit has a double benefit: it reduces payment friction and late payment events (which are a leading indicator of churn), and it signals a deeper engagement with the business. Incentives such as tariff discounts or loyalty points should be tested on this cohort.

**3. Prioritise cross-sell campaigns on the At Risk segment to increase product holdings and embed them in the ecosystem**
At Risk customers (**35,074 accounts**, 35.1% of the fleet) have an average CLV of £4,004 and show the highest concentration of High churn risk at 54.5%. Introducing a second product — a smart tariff add-on, a boiler care plan, or an EV charging solution — increases their switching cost, raises their CLV, and creates additional touchpoints that support retention. This segment is large enough that even modest conversion rates deliver material portfolio improvement.

**4. Investigate regional underperformance with the operations team to identify root causes of lower CLV in weaker regions**
Regional CLV variance across the five territories points to structural differences in customer mix, tariff penetration, or service quality. The weakest-performing region should be subject to a root-cause review involving regional operations, field sales, and customer service data to determine whether underperformance is driven by acquisition quality, retention failure, or product mix — and to design targeted interventions accordingly.

---

## Tech Stack

| Technology | Purpose | Version |
|------------|---------|---------|
| **Python** | Data generation, feature engineering, orchestration | 3.x |
| **NumPy** | Reproducible random data generation (`SEED = 42`) | 2.4.4 |
| **Pandas** | Data manipulation, CLV scoring, RFM quintile scoring | 3.0.2 |
| **SQL** | Six analytical queries (ANSI-compatible) | — |
| **DuckDB** | In-memory SQL engine for executing queries against DataFrames | 1.5.2 |
| **Power BI** | Interactive 3-page dashboard for commercial teams | Desktop |

---

## How to Run

Run the four steps below in order from the project root directory.

**Step 1 — Install dependencies**

```bash
pip install numpy pandas duckdb
```

**Step 2 — Generate the raw dataset**

```bash
python scripts/generate_clv_data.py
```

Outputs `data/raw_clv_data.csv` — 100,000 rows × 15 columns.

**Step 3 — Clean, score, and segment**

```bash
python scripts/clean_and_score_clv.py
```

Outputs `data/clean_clv_data.csv` — 100,000 rows × 22 columns including CLV score, RFM scores, segment, and churn risk.

**Step 4 — Run SQL analysis and generate summary report**

```bash
python scripts/generate_clv_summary.py
```

Registers the dataset in DuckDB, executes all 6 queries from `run_clv_queries.sql`, prints the executive summary to the terminal, and saves it to `data/clv_summary.txt`.

> To explore the SQL queries independently, open `scripts/run_clv_queries.sql` in any SQL editor and point it at `data/clean_clv_data.csv` using DuckDB, SQLite, or PostgreSQL with the table aliased as `customers`.

---

## Project Structure

```
customer-clv-segmentation/
│
├── scripts/
│   ├── generate_clv_data.py        # Step 1 — synthetic data generation
│   ├── clean_and_score_clv.py      # Step 2 — CLV scoring, RFM, segmentation
│   ├── run_clv_queries.sql         # Step 3 — 6 analytical SQL queries
│   └── generate_clv_summary.py    # Step 4 — DuckDB orchestration + report
│
├── data/
│   ├── raw_clv_data.csv            # Generated by Step 1 (git-ignored)
│   ├── clean_clv_data.csv          # Generated by Step 2 (git-ignored)
│   └── clv_summary.txt             # Generated by Step 4
│
├── powerbi/
│   └── clv_dashboard.pbix          # Power BI report file
│
├── PIPELINE.md                     # Pipeline stage documentation
├── README.md                       # This file
└── .gitignore                      # Excludes data/*.csv, data/*.json, __pycache__
```

---

## Note

All data in this project is **synthetically generated** using Python's `numpy.random` module with a fixed seed (`SEED = 42`) for full reproducibility. No real customer data has been used at any stage. Distributions, tariff splits, spend ranges, churn rates, and behavioural flags are calibrated to reflect realistic patterns in the UK domestic energy retail market but do not represent or derive from any actual customer records. Running `generate_clv_data.py` with `SEED = 42` will always produce an identical dataset.
