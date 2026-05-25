"""
clean_and_score_clv.py

Loads raw customer data, engineers CLV-related features, and produces a
fully scored and segmented dataset ready for reporting and modelling.

Input  : data/raw_clv_data.csv
Output : data/clean_clv_data.csv
"""

import os
import sys

# ── Dependency check ──────────────────────────────────────────────────────────
try:
    import numpy as np
    import pandas as pd
except ImportError:
    import subprocess
    print("Installing required libraries ...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy", "pandas"])
    import numpy as np
    import pandas as pd

from datetime import date

# =============================================================================
# Configuration
# =============================================================================
TODAY       = date(2026, 5, 25)
TODAY_TS    = pd.Timestamp(TODAY)
INPUT_PATH  = os.path.join("data", "raw_clv_data.csv")
OUTPUT_PATH = os.path.join("data", "clean_clv_data.csv")

# =============================================================================
# Load
# =============================================================================
print(f"\nLoading data from: {INPUT_PATH}")
df = pd.read_csv(INPUT_PATH, parse_dates=["signup_date", "last_renewal_date"])
print(f"  Rows loaded      : {len(df):,}")
print(f"  Columns (raw)    : {df.shape[1]}")

if df.isnull().sum().sum() > 0:
    print("  WARNING: null values detected in input - review raw data.")
else:
    print("  Null check       : OK (0 nulls)")

# =============================================================================
# 1. clv_score
#    Formula: annual_spend x (tenure_months / 12) x (renewal_count + 1)
#    - tenure_months / 12 converts months to years (time-value weight)
#    - (renewal_count + 1) is a loyalty multiplier; min value is 1
# =============================================================================
df["clv_score"] = (
    df["annual_spend"]
    * (df["tenure_months"] / 12)
    * (df["renewal_count"] + 1)
).round(2)

# =============================================================================
# 2. rfm_recency  (1 = oldest, 5 = most recent)
#    Scored from days since last_renewal_date.
#    Customers who renewed most recently receive the highest score (5).
#    rank(method='first') is used before qcut to handle integer-day ties
#    cleanly and guarantee exactly 5 equal-sized buckets.
# =============================================================================
df["_days_since_renewal"] = (TODAY_TS - df["last_renewal_date"]).dt.days

# Invert labels so fewer days (more recent) maps to a higher score
df["rfm_recency"] = pd.qcut(
    df["_days_since_renewal"].rank(method="first"),
    q=5,
    labels=[5, 4, 3, 2, 1],   # 5 = most recent quintile, 1 = oldest quintile
).astype(int)

# =============================================================================
# 3. rfm_frequency  (1 = lowest, 5 = highest renewal activity)
#    Scored from renewal_count. rank(method='first') handles the discrete
#    distribution (0, 1, 2, 3, 4) which would otherwise produce duplicate
#    bin edges and fail a plain qcut.
# =============================================================================
df["rfm_frequency"] = pd.qcut(
    df["renewal_count"].rank(method="first"),
    q=5,
    labels=[1, 2, 3, 4, 5],
).astype(int)

# =============================================================================
# 4. rfm_monetary  (1 = lowest spend, 5 = highest spend)
#    Scored from annual_spend. Continuous distribution; rank used for
#    consistency and to handle any accidental ties at bin boundaries.
# =============================================================================
df["rfm_monetary"] = pd.qcut(
    df["annual_spend"].rank(method="first"),
    q=5,
    labels=[1, 2, 3, 4, 5],
).astype(int)

# =============================================================================
# 5. rfm_total  (range: 3 to 15)
# =============================================================================
df["rfm_total"] = df["rfm_recency"] + df["rfm_frequency"] + df["rfm_monetary"]

# =============================================================================
# 6. segment  (based on rfm_total thresholds)
#    13 - 15  : Champions
#    10 - 12  : Loyal Customers
#     7 -  9  : At Risk
#    below 7  : Lost Customers
# =============================================================================
seg_conditions = [
    df["rfm_total"] >= 13,
    df["rfm_total"] >= 10,
    df["rfm_total"] >= 7,
]
seg_choices = ["Champions", "Loyal Customers", "At Risk"]
df["segment"] = np.select(seg_conditions, seg_choices, default="Lost Customers")

# =============================================================================
# 7. churn_risk
#    High   : complaint_count >= 3  OR  late_payment_count >= 3
#             OR  rfm_recency <= 2
#    Low    : complaint_count == 0  AND  rfm_recency >= 4
#    Medium : everyone else
#
#    np.select evaluates conditions top-down, so High takes precedence over
#    Low where both could theoretically apply.
# =============================================================================
risk_conditions = [
    (
        (df["complaint_count"]    >= 3) |
        (df["late_payment_count"] >= 3) |
        (df["rfm_recency"]        <= 2)
    ),
    (
        (df["complaint_count"] == 0) &
        (df["rfm_recency"]     >= 4)
    ),
]
risk_choices = ["High", "Low"]
df["churn_risk"] = np.select(risk_conditions, risk_choices, default="Medium")

# =============================================================================
# Tidy up: drop intermediate helper column
# =============================================================================
df.drop(columns=["_days_since_renewal"], inplace=True)

# =============================================================================
# Save
# =============================================================================
os.makedirs("data", exist_ok=True)
df.to_csv(OUTPUT_PATH, index=False)
print(f"\nSaved enriched dataset to: {OUTPUT_PATH}")
print(f"  Rows  : {len(df):,}")
print(f"  Cols  : {df.shape[1]}  (raw {df.shape[1] - 7} + 7 derived)")

# =============================================================================
# Summary report
# =============================================================================
W = 58

def section(title):
    print(f"\n{'-' * W}")
    print(f"  {title}")
    print('-' * W)

print("\n" + "=" * W)
print("   Clean & Score CLV  --  Summary Report")
print("=" * W)

# ── New columns added
section("Derived Columns Added")
derived = [
    ("clv_score",     "annual_spend x (tenure_months/12) x (renewal_count+1)"),
    ("rfm_recency",   "1-5 quintile score (5=most recent renewal)"),
    ("rfm_frequency", "1-5 quintile score (5=most renewals)"),
    ("rfm_monetary",  "1-5 quintile score (5=highest spend)"),
    ("rfm_total",     "sum of recency + frequency + monetary  [3-15]"),
    ("segment",       "Champions / Loyal Customers / At Risk / Lost Customers"),
    ("churn_risk",    "High / Medium / Low"),
]
for col, desc in derived:
    print(f"  {col:<16}  {desc}")

# ── CLV score statistics
section("CLV Score Statistics")
cs = df["clv_score"]
print(f"  Min      : {cs.min():>12,.2f}")
print(f"  Max      : {cs.max():>12,.2f}")
print(f"  Mean     : {cs.mean():>12,.2f}")
print(f"  Median   : {cs.median():>12,.2f}")
print(f"  Std Dev  : {cs.std():>12,.2f}")
print(f"  Zeros    : {(cs == 0).sum():>12,}  "
      f"(customers with 0 tenure months)")

# ── RFM score distributions
section("RFM Score Distributions  (each bucket = 20% of customers)")
for col in ["rfm_recency", "rfm_frequency", "rfm_monetary"]:
    counts = df[col].value_counts().sort_index()
    row = "  " + col + ": "
    row += "  ".join(f"[{i}] {counts.get(i, 0):,}" for i in range(1, 6))
    print(row)

print()
rfm_tot = df["rfm_total"].value_counts().sort_index()
print("  rfm_total distribution:")
for score, cnt in rfm_tot.items():
    bar = "|" * (cnt // 1000)
    print(f"    {score:>2}  {cnt:>7,}  {bar}")

# ── Segment distribution
section("Segment Distribution")
seg_order = ["Champions", "Loyal Customers", "At Risk", "Lost Customers"]
seg_counts = df["segment"].value_counts()
for seg in seg_order:
    cnt = seg_counts.get(seg, 0)
    pct = cnt / len(df) * 100
    bar = "|" * int(pct / 1.5)
    print(f"  {seg:<18}  {cnt:>7,}  ({pct:>5.1f}%)  {bar}")

# ── CLV score by segment
section("Mean CLV Score by Segment")
clv_by_seg = df.groupby("segment")["clv_score"].mean().reindex(seg_order)
for seg, val in clv_by_seg.items():
    print(f"  {seg:<18}  {val:>10,.2f}")

# ── Churn risk breakdown
section("Churn Risk Breakdown")
risk_order = ["High", "Medium", "Low"]
risk_counts = df["churn_risk"].value_counts()
for risk in risk_order:
    cnt = risk_counts.get(risk, 0)
    pct = cnt / len(df) * 100
    bar = "|" * int(pct / 1.5)
    print(f"  {risk:<8}  {cnt:>7,}  ({pct:>5.1f}%)  {bar}")

# ── Churn risk x Segment cross-tab
section("Churn Risk  x  Segment (row %)")
crosstab = pd.crosstab(
    df["segment"], df["churn_risk"],
    normalize="index"
).mul(100).round(1)
# Ensure columns in order
for col in risk_order:
    if col not in crosstab.columns:
        crosstab[col] = 0.0
crosstab = crosstab[risk_order]

header_row = f"  {'Segment':<18}  {'High':>8}  {'Medium':>8}  {'Low':>8}"
print(header_row)
print(f"  {'-'*18}  {'-'*8}  {'-'*8}  {'-'*8}")
for seg in seg_order:
    if seg in crosstab.index:
        row = crosstab.loc[seg]
        print(f"  {seg:<18}  {row['High']:>7.1f}%  {row['Medium']:>7.1f}%  {row['Low']:>7.1f}%")

# ── Churn flag vs churn_risk validation
section("Churn Flag Rate by Churn Risk Label  (sanity check)")
churn_by_risk = (
    df.groupby("churn_risk")["churn_flag"]
      .mean()
      .mul(100)
      .round(2)
      .reindex(risk_order)
)
for risk, pct in churn_by_risk.items():
    print(f"  {risk:<8}  {pct:>6.2f}% churned")

# ── Segment x actual churn
section("Actual Churn Rate by Segment  (sanity check)")
churn_by_seg = (
    df.groupby("segment")["churn_flag"]
      .mean()
      .mul(100)
      .round(2)
      .reindex(seg_order)
)
for seg, pct in churn_by_seg.items():
    print(f"  {seg:<18}  {pct:>6.2f}% churned")

print(f"\n{'=' * W}")
print("  [DONE]  Cleaning and scoring complete.")
print(f"{'=' * W}\n")
