"""
generate_clv_summary.py

Loads the scored CLV dataset, registers it in DuckDB, executes all six
analytical queries from run_clv_queries.sql, and produces a plain-English
executive summary report.

Input  : data/clean_clv_data.csv
         scripts/run_clv_queries.sql
Output : data/clv_summary.txt  (also printed to terminal)
"""

import logging
import os
import re
import sys
from datetime import date

# =============================================================================
# Dependency check
# =============================================================================
try:
    import duckdb
    import pandas as pd
except ImportError:
    import subprocess
    logging.warning("Required libraries not found -- installing now.")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "duckdb", "pandas"]
    )
    import duckdb
    import pandas as pd

# =============================================================================
# Logging configuration
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================
TODAY       = date(2026, 5, 25)
DATA_PATH   = os.path.join("data", "clean_clv_data.csv")
SQL_PATH    = os.path.join("scripts", "run_clv_queries.sql")
REPORT_PATH = os.path.join("data", "clv_summary.txt")

QUERY_LABELS = [
    "Segment Distribution",
    "Segment Profile",
    "Churn Risk by Segment",
    "Regional CLV Performance",
    "Payment Method vs CLV",
    "Product Holdings vs CLV",
]

# =============================================================================
# Step 1: Load data/clean_clv_data.csv
# =============================================================================
log.info("Starting CLV summary generation.")
log.info("Loading dataset: %s", DATA_PATH)

if not os.path.exists(DATA_PATH):
    log.error("Input file not found: %s", DATA_PATH)
    log.error("Run clean_and_score_clv.py first to generate the scored dataset.")
    sys.exit(1)

df = pd.read_csv(DATA_PATH)
log.info("Dataset loaded -- %s rows, %s columns.", f"{len(df):,}", df.shape[1])

# =============================================================================
# Step 2: Register DataFrame in DuckDB as table 'customers'
# =============================================================================
log.info("Opening DuckDB in-memory connection.")
con = duckdb.connect()

log.info("Registering DataFrame as DuckDB table 'customers'.")
con.register("customers", df)

row_check = con.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
log.info("Table 'customers' verified -- %s rows registered.", f"{row_check:,}")

# =============================================================================
# Step 3: Read and parse run_clv_queries.sql
# =============================================================================
log.info("Reading SQL file: %s", SQL_PATH)

if not os.path.exists(SQL_PATH):
    log.error("SQL file not found: %s", SQL_PATH)
    sys.exit(1)

with open(SQL_PATH, "r", encoding="utf-8") as fh:
    raw_sql = fh.read()

log.info("SQL file read -- %s characters.", len(raw_sql))

# Strip single-line SQL comments before splitting so that semicolons embedded
# inside comment text do not create spurious statement boundaries.
log.info("Stripping inline SQL comments before parsing.")
stripped_sql = re.sub(r"--[^\n]*", "", raw_sql)

# Split on semicolons and keep only blocks that open with a SELECT keyword.
all_blocks = [b.strip() for b in stripped_sql.split(";") if b.strip()]
queries    = [
    b for b in all_blocks
    if re.search(r"^\s*SELECT", b, re.MULTILINE | re.IGNORECASE)
]

log.info("Parsed %s executable SELECT statements from SQL file.", len(queries))

if len(queries) != 6:
    log.warning(
        "Expected 6 queries but found %s -- results may be incomplete.",
        len(queries),
    )

# =============================================================================
# Step 4: Execute all 6 queries and store results
# =============================================================================
log.info("Executing queries against 'customers' table.")

results = {}
for label, sql in zip(QUERY_LABELS, queries):
    log.info("  Running: %s ...", label)
    try:
        results[label] = con.execute(sql).df()
        log.info("  -> OK  (%s rows returned)", len(results[label]))
    except Exception as exc:
        log.error("  -> FAILED  %s: %s", label, exc)
        sys.exit(1)

con.close()
log.info("All %s queries executed. DuckDB connection closed.", len(queries))

# =============================================================================
# Helper functions
# =============================================================================

def clv_fmt(val: float) -> str:
    """Format a CLV value with comma separator and 2 decimal places."""
    return f"{val:,.2f}"

def pct_fmt(val: float) -> str:
    """Format a percentage with 1 decimal place."""
    return f"{val:.1f}"

# =============================================================================
# Step 5: Extract values from query results
# =============================================================================
log.info("Extracting values from query results to build report.")

q1 = results["Segment Distribution"]       # segment | customer_count | pct_of_total | avg_clv | avg_annual_spend
q3 = results["Churn Risk by Segment"]      # segment | churn_risk | customer_count | pct_within_segment | avg_clv
q4 = results["Regional CLV Performance"]   # region  | total_customers | avg_clv | avg_spend | champion_count | champion_pct | lost_count | lost_pct
q5 = results["Payment Method vs CLV"]      # payment_method | customer_count | avg_clv | avg_spend | avg_late_payments | churn_rate_pct
q6 = results["Product Holdings vs CLV"]    # num_products | customer_count | avg_clv | avg_spend | churn_rate_pct | avg_renewals

# -- Segment counts and average CLV values
def seg_val(segment_name: str, column: str):
    """Return a scalar from Q1 for the given segment and column."""
    rows = q1[q1["segment"] == segment_name]
    if rows.empty:
        log.warning("Segment '%s' not found in Q1 results.", segment_name)
        return 0
    return rows[column].values[0]

champ_count = int(seg_val("Champions",       "customer_count"))
loyal_count = int(seg_val("Loyal Customers", "customer_count"))
risk_count  = int(seg_val("At Risk",         "customer_count"))
lost_count  = int(seg_val("Lost Customers",  "customer_count"))
total_fleet = champ_count + loyal_count + risk_count + lost_count

champ_clv = float(seg_val("Champions",       "avg_clv"))
loyal_clv = float(seg_val("Loyal Customers", "avg_clv"))
risk_clv  = float(seg_val("At Risk",         "avg_clv"))
lost_clv  = float(seg_val("Lost Customers",  "avg_clv"))

log.info(
    "Segments: Champions=%s | Loyal=%s | At Risk=%s | Lost=%s | Total=%s",
    f"{champ_count:,}", f"{loyal_count:,}", f"{risk_count:,}",
    f"{lost_count:,}", f"{total_fleet:,}",
)

# -- Churn risk figures (from Q3)
high_risk_df    = q3[q3["churn_risk"] == "High"]
high_risk_total = int(high_risk_df["customer_count"].sum())
high_risk_pct   = round(high_risk_total / total_fleet * 100, 1)

champ_high_rows  = q3[(q3["segment"] == "Champions") & (q3["churn_risk"] == "High")]
champ_high_count = int(champ_high_rows["customer_count"].values[0]) if not champ_high_rows.empty else 0

log.info(
    "Churn risk: High=%s (%s%%) | Champions at High risk=%s",
    f"{high_risk_total:,}", high_risk_pct, f"{champ_high_count:,}",
)

# -- Regional performance (from Q4)
q4_asc  = q4.sort_values("avg_clv", ascending=True).reset_index(drop=True)
q4_desc = q4.sort_values("avg_clv", ascending=False).reset_index(drop=True)

strongest_region     = str(q4_desc.iloc[0]["region"])
strongest_region_clv = float(q4_desc.iloc[0]["avg_clv"])
weakest_region       = str(q4_asc.iloc[0]["region"])
weakest_region_clv   = float(q4_asc.iloc[0]["avg_clv"])

log.info(
    "Regions: strongest=%s (CLV %.2f) | weakest=%s (CLV %.2f)",
    strongest_region, strongest_region_clv,
    weakest_region, weakest_region_clv,
)

# -- Payment method insight (from Q5)
q5_asc  = q5.sort_values("avg_clv", ascending=True).reset_index(drop=True)
q5_desc = q5.sort_values("avg_clv", ascending=False).reset_index(drop=True)

highest_pay_method = str(q5_desc.iloc[0]["payment_method"])
highest_pay_clv    = float(q5_desc.iloc[0]["avg_clv"])
lowest_pay_method  = str(q5_asc.iloc[0]["payment_method"])
lowest_pay_clv     = float(q5_asc.iloc[0]["avg_clv"])

manual_rows      = q5[q5["payment_method"] == "Manual"]
manual_churn_pct = float(manual_rows["churn_rate_pct"].values[0]) if not manual_rows.empty else 0.0

log.info(
    "Payment: highest CLV=%s (%.2f) | lowest CLV=%s (%.2f) | Manual churn=%.1f%%",
    highest_pay_method, highest_pay_clv,
    lowest_pay_method, lowest_pay_clv,
    manual_churn_pct,
)

# -- Product cross-sell (from Q6)
prod1_rows = q6[q6["num_products"] == 1]
prod5_rows = q6[q6["num_products"] == 5]
prod1_clv  = float(prod1_rows["avg_clv"].values[0]) if not prod1_rows.empty else 0.0
prod5_clv  = float(prod5_rows["avg_clv"].values[0]) if not prod5_rows.empty else 0.0

log.info(
    "Products: 1-product avg CLV=%.2f | 5-product avg CLV=%.2f",
    prod1_clv, prod5_clv,
)

# =============================================================================
# Step 5 (continued): Build report text
# =============================================================================
log.info("Building plain-English summary report.")

week_ending = TODAY.strftime("%d %B %Y")

report_lines = [
    "== CUSTOMER CLV & SEGMENTATION REPORT ==",
    f"Week ending: {week_ending}",
    "",
    "SEGMENT OVERVIEW:",
    f"  Champions:       {champ_count:,} customers  avg CLV £{clv_fmt(champ_clv)}",
    f"  Loyal Customers: {loyal_count:,} customers  avg CLV £{clv_fmt(loyal_clv)}",
    f"  At Risk:         {risk_count:,} customers  avg CLV £{clv_fmt(risk_clv)}",
    f"  Lost Customers:  {lost_count:,} customers  avg CLV £{clv_fmt(lost_clv)}",
    "",
    "CHURN RISK ALERTS:",
    f"  High risk customers: {high_risk_total:,} ({pct_fmt(high_risk_pct)}% of total fleet)",
    f"  Champions at High risk: {champ_high_count:,} -- immediate retention priority",
    "",
    "REGIONAL PERFORMANCE:",
    f"  Strongest region: {strongest_region} avg CLV £{clv_fmt(strongest_region_clv)}",
    f"  Weakest region: {weakest_region} avg CLV £{clv_fmt(weakest_region_clv)}",
    "",
    "PAYMENT METHOD INSIGHT:",
    f"  Highest CLV method: {highest_pay_method} avg CLV £{clv_fmt(highest_pay_clv)}",
    f"  Lowest CLV method: {lowest_pay_method} avg CLV £{clv_fmt(lowest_pay_clv)}",
    f"  Manual payer churn rate: {pct_fmt(manual_churn_pct)}%",
    "",
    "PRODUCT CROSS-SELL INSIGHT:",
    f"  Customers with 1 product: avg CLV £{clv_fmt(prod1_clv)}",
    f"  Customers with 5 products: avg CLV £{clv_fmt(prod5_clv)}",
    "",
    "KEY RECOMMENDATIONS:",
    f"  1. Prioritise retention outreach to {champ_high_count:,} Champions",
    f"     flagged as High churn risk",
    f"  2. Target Manual payers with Direct Debit incentives",
    f"     to reduce {pct_fmt(manual_churn_pct)}% churn rate",
    "  3. Focus cross-sell campaigns on At Risk segment",
    "     to increase product holdings and reduce churn",
    f"  4. Investigate {weakest_region} underperformance",
    "     with regional operations team",
]

report = "\n".join(report_lines)

# =============================================================================
# Step 6: Print report to terminal
# =============================================================================
log.info("Printing report to terminal.")
print()
print(report)
print()

# =============================================================================
# Step 7: Save report to data/clv_summary.txt
# =============================================================================
log.info("Saving report to: %s", REPORT_PATH)
os.makedirs("data", exist_ok=True)

with open(REPORT_PATH, "w", encoding="utf-8") as fh:
    fh.write(report + "\n")

file_size = os.path.getsize(REPORT_PATH)
log.info("Report saved -- %s bytes written.", file_size)
log.info("CLV summary generation complete.")
