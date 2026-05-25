"""
generate_clv_data.py

Generates 100,000 synthetic domestic energy customer records for Customer
Lifetime Value (CLV) analysis and segmentation.

Output : data/raw_clv_data.csv
"""

import os
import sys

# ── Dependency check ──────────────────────────────────────────────────────────
try:
    import numpy as np
    import pandas as pd
except ImportError:
    import subprocess
    print("Installing required libraries …")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy", "pandas"])
    import numpy as np
    import pandas as pd

from datetime import date, timedelta

# ═════════════════════════════════════════════════════════════════════════════
# Configuration
# ═════════════════════════════════════════════════════════════════════════════
SEED        = 42
N           = 100_000
TODAY       = date(2026, 5, 25)
OUTPUT_PATH = os.path.join("data", "raw_clv_data.csv")

rng = np.random.default_rng(SEED)

# ═════════════════════════════════════════════════════════════════════════════
# 1. customer_id  ── format: A-XXXXXXXX  (8 random digits, guaranteed unique)
# ═════════════════════════════════════════════════════════════════════════════
raw_ids      = rng.choice(90_000_000, size=N, replace=False) + 10_000_000
customer_ids = [f"A-{i}" for i in raw_ids]

# ═════════════════════════════════════════════════════════════════════════════
# 2. signup_date  ── spread uniformly over the last 3 years
# ═════════════════════════════════════════════════════════════════════════════
START_DATE   = date(2023, 5, 25)
DAYS_RANGE   = (TODAY - START_DATE).days                   # 1 096 days
day_offsets  = rng.integers(0, DAYS_RANGE, size=N)
signup_dates = np.array([START_DATE + timedelta(days=int(d)) for d in day_offsets])

# ═════════════════════════════════════════════════════════════════════════════
# 3. tenure_months  ── calendar months from signup to TODAY
# ═════════════════════════════════════════════════════════════════════════════
tenure_months = np.array([(TODAY - sd).days for sd in signup_dates]) // 30

# ═════════════════════════════════════════════════════════════════════════════
# 4. tariff_type
#    Fixed 30% | Variable 25% | Prepay 5% | Deemed 15% |
#    Economy 7 10% | EV 10% | Heat Pump 5%
# ═════════════════════════════════════════════════════════════════════════════
TARIFFS  = ["Fixed", "Variable", "Prepay", "Deemed", "Economy 7", "EV", "Heat Pump"]
TARIFF_P = [0.30,    0.25,       0.05,     0.15,     0.10,        0.10,  0.05]
tariff   = rng.choice(TARIFFS, size=N, p=TARIFF_P)

# ═════════════════════════════════════════════════════════════════════════════
# 5. region  ── 5 regions, equally distributed
# ═════════════════════════════════════════════════════════════════════════════
REGIONS = ["North", "South", "East", "West", "Midlands"]
region  = rng.choice(REGIONS, size=N)                      # uniform by default

# ═════════════════════════════════════════════════════════════════════════════
# 6. annual_spend  ── £400–£2,500; higher for Fixed and Variable tariffs
#    UK domestic energy baseline: typical household ~£1,200–£1,800 p.a.
#    EV / Heat Pump customers have elevated electricity consumption.
#    Prepay customers tend to use less (pay-as-you-go behaviour).
# ═════════════════════════════════════════════════════════════════════════════
SPEND_PARAMS = {              # (mean £, std dev £)
    "Fixed":     (1_820, 370),
    "Variable":  (1_680, 360),
    "Prepay":    (  870, 210),
    "Deemed":    (1_110, 260),
    "Economy 7": (1_220, 280),
    "EV":        (1_640, 350),
    "Heat Pump": (1_700, 360),
}

annual_spend = np.empty(N)
for name, (mu, sigma) in SPEND_PARAMS.items():
    mask = tariff == name
    annual_spend[mask] = rng.normal(mu, sigma, size=int(mask.sum()))

annual_spend = np.round(np.clip(annual_spend, 400.0, 2_500.0), 2)

# ═════════════════════════════════════════════════════════════════════════════
# 7. payment_method  ── Direct Debit 60% | Credit Card 20% | Prepay 10% | Manual 10%
# ═════════════════════════════════════════════════════════════════════════════
PAY_METHODS    = ["Direct Debit", "Credit Card", "Prepay",  "Manual"]
PAY_P          = [0.60,           0.20,          0.10,      0.10]
payment_method = rng.choice(PAY_METHODS, size=N, p=PAY_P)

# ═════════════════════════════════════════════════════════════════════════════
# 8. num_products  ── 1–5, weighted heavily toward 1 and 2
# ═════════════════════════════════════════════════════════════════════════════
num_products = rng.choice([1, 2, 3, 4, 5], size=N, p=[0.42, 0.30, 0.14, 0.09, 0.05])

# ═════════════════════════════════════════════════════════════════════════════
# 9. complaint_count  ── 0–8; Poisson-distributed, most customers have 0 or 1
# ═════════════════════════════════════════════════════════════════════════════
complaint_count = np.clip(rng.poisson(lam=0.5, size=N), 0, 8).astype(int)

# ═════════════════════════════════════════════════════════════════════════════
# 10. late_payment_count  ── 0–6; most customers have 0
# ═════════════════════════════════════════════════════════════════════════════
late_payment_count = np.clip(rng.poisson(lam=0.35, size=N), 0, 6).astype(int)

# ═════════════════════════════════════════════════════════════════════════════
# 11. smart_meter  ── 70% Yes
# ═════════════════════════════════════════════════════════════════════════════
smart_meter = np.where(rng.random(N) < 0.70, "Yes", "No")

# ═════════════════════════════════════════════════════════════════════════════
# 12. app_registered  ── 65% Yes
# ═════════════════════════════════════════════════════════════════════════════
app_registered = np.where(rng.random(N) < 0.65, "Yes", "No")

# ═════════════════════════════════════════════════════════════════════════════
# 13. renewal_count  ── 0–8; correlated with tenure
#     Domestic energy contracts run ~12 months, so:
#     expected renewals ≈ floor(tenure_months / 12), ±1 jitter
# ═════════════════════════════════════════════════════════════════════════════
base_renewals = (tenure_months // 12).astype(int)
renewal_jitter = rng.integers(-1, 2, size=N)               # values: -1, 0, or +1
renewal_count  = np.clip(base_renewals + renewal_jitter, 0, 8).astype(int)

# ═════════════════════════════════════════════════════════════════════════════
# 14. last_renewal_date  ── realistic relative to renewal_count
#     0 renewals  → still on first contract → last_renewal_date = signup_date
#     n renewals  → n × 12-month intervals from signup, capped at TODAY
# ═════════════════════════════════════════════════════════════════════════════
def _last_renewal(signup: date, renewals: int) -> date:
    if renewals == 0:
        return signup
    estimated = signup + timedelta(days=int(renewals * 365))
    return min(estimated, TODAY)

last_renewal_dates = np.array([
    _last_renewal(sd, rc)
    for sd, rc in zip(signup_dates, renewal_count)
])

# ═════════════════════════════════════════════════════════════════════════════
# 15. churn_flag  ── ~12% overall; elevated for Prepay tariff & Manual payers
#
#     Risk factors and additive increments:
#       Prepay tariff       +0.18  (price-sensitive, high churn segment)
#       Deemed tariff       +0.04  (out-of-contract, higher risk)
#       Manual payment      +0.12  (disengaged customers)
#       Prepay payment      +0.06  (correlated with financial difficulty)
#       ≥3 complaints       +0.07  (dissatisfied customers)
#       ≥3 late payments    +0.05  (financially stressed)
#
#     All probabilities are linearly scaled so the fleet-wide mean = 12.0%.
# ═════════════════════════════════════════════════════════════════════════════
churn_prob = np.full(N, 0.09, dtype=float)

churn_prob[tariff         == "Prepay"]  += 0.18
churn_prob[tariff         == "Deemed"]  += 0.04
churn_prob[payment_method == "Manual"]  += 0.12
churn_prob[payment_method == "Prepay"]  += 0.06
churn_prob[complaint_count    >= 3]     += 0.07
churn_prob[late_payment_count >= 3]     += 0.05

# Calibrate so the fleet-wide mean equals exactly 12 %
churn_prob = np.clip(churn_prob * (0.12 / churn_prob.mean()), 0.0, 1.0)

churn_flag = (rng.random(N) < churn_prob).astype(int)

# ═════════════════════════════════════════════════════════════════════════════
# Assemble DataFrame
# ═════════════════════════════════════════════════════════════════════════════
df = pd.DataFrame({
    "customer_id":        customer_ids,
    "signup_date":        signup_dates,
    "tenure_months":      tenure_months,
    "tariff_type":        tariff,
    "region":             region,
    "annual_spend":       annual_spend,
    "payment_method":     payment_method,
    "num_products":       num_products,
    "complaint_count":    complaint_count,
    "late_payment_count": late_payment_count,
    "smart_meter":        smart_meter,
    "app_registered":     app_registered,
    "renewal_count":      renewal_count,
    "last_renewal_date":  last_renewal_dates,
    "churn_flag":         churn_flag,
})

# ═════════════════════════════════════════════════════════════════════════════
# Save to CSV
# ═════════════════════════════════════════════════════════════════════════════
os.makedirs("data", exist_ok=True)
df.to_csv(OUTPUT_PATH, index=False)

# ═════════════════════════════════════════════════════════════════════════════
# Summary report
# ═════════════════════════════════════════════════════════════════════════════
W  = 56                                             # report width
HL = "-" * W

def header(title: str) -> None:
    print(f"\n{HL}")
    print(f"  {title}")
    print(HL)

print("\n" + "=" * W)
print("   CLV Data Generation  --  Summary Report")
print("=" * W)
print(f"  Customers generated : {N:,}")
print(f"  Output file         : {OUTPUT_PATH}")
print(f"  Columns             : {len(df.columns)}")
print(f"  Reference date      : {TODAY}")

# ── Tariff type
header("Tariff Type Distribution")
for t in TARIFFS:
    cnt = int((df["tariff_type"] == t).sum())
    print(f"  {t:<12}  {cnt:>7,}  ({cnt / N * 100:>5.1f}%)")

# ── Region
header("Region Distribution")
for r in REGIONS:
    cnt = int((df["region"] == r).sum())
    print(f"  {r:<10}  {cnt:>7,}  ({cnt / N * 100:>5.1f}%)")

# ── Payment method
header("Payment Method Distribution")
for p in PAY_METHODS:
    cnt = int((df["payment_method"] == p).sum())
    print(f"  {p:<14}  {cnt:>7,}  ({cnt / N * 100:>5.1f}%)")

# ── Annual spend
header("Annual Spend (£)")
print(f"  Minimum    : £{df['annual_spend'].min():>9,.2f}")
print(f"  Maximum    : £{df['annual_spend'].max():>9,.2f}")
print(f"  Mean       : £{df['annual_spend'].mean():>9,.2f}")
print(f"  Median     : £{df['annual_spend'].median():>9,.2f}")
print(f"  Std Dev    : £{df['annual_spend'].std():>9,.2f}")
print()
print(f"  {'Tariff':<12}  {'Mean spend':>12}  {'Median spend':>12}")
print(f"  {'------':<12}  {'----------':>12}  {'------------':>12}")
for t in TARIFFS:
    sub = df.loc[df["tariff_type"] == t, "annual_spend"]
    print(f"  {t:<12}  £{sub.mean():>10,.2f}  £{sub.median():>11,.2f}")

# ── Tenure
header("Tenure (months)")
print(f"  Minimum  : {df['tenure_months'].min()}")
print(f"  Maximum  : {df['tenure_months'].max()}")
print(f"  Mean     : {df['tenure_months'].mean():.1f}")
print(f"  Median   : {df['tenure_months'].median():.0f}")

# ── Key binary flags
header("Key Flags")
print(f"  Churn rate     : {df['churn_flag'].mean() * 100:.2f}%  "
      f"({df['churn_flag'].sum():,} customers)")
print(f"  Smart meter    : {(df['smart_meter']    == 'Yes').mean() * 100:.1f}%")
print(f"  App registered : {(df['app_registered'] == 'Yes').mean() * 100:.1f}%")

# ── Churn by tariff
header("Churn Rate by Tariff Type")
churn_by_tariff = (
    df.groupby("tariff_type")["churn_flag"]
      .mean()
      .mul(100)
      .round(2)
      .sort_values(ascending=False)
)
for t, pct in churn_by_tariff.items():
    bar = "|" * int(pct / 1.5)
    print(f"  {t:<12}  {pct:>5.2f}%  {bar}")

# ── Churn by payment method
header("Churn Rate by Payment Method")
churn_by_pay = (
    df.groupby("payment_method")["churn_flag"]
      .mean()
      .mul(100)
      .round(2)
      .sort_values(ascending=False)
)
for p, pct in churn_by_pay.items():
    bar = "|" * int(pct / 1.5)
    print(f"  {p:<14}  {pct:>5.2f}%  {bar}")

# ── Products distribution
header("Number of Products Distribution")
for n, cnt in df["num_products"].value_counts().sort_index().items():
    print(f"  {n} product(s)  :  {cnt:>7,}  ({cnt / N * 100:.1f}%)")

# ── Renewal count distribution
header("Renewal Count Distribution")
for n, cnt in df["renewal_count"].value_counts().sort_index().items():
    print(f"  {n} renewal(s)  :  {cnt:>7,}  ({cnt / N * 100:.1f}%)")

# ── Complaint & late-payment distributions
header("Complaint Count Distribution")
for n, cnt in df["complaint_count"].value_counts().sort_index().items():
    print(f"  {n} complaint(s) :  {cnt:>7,}  ({cnt / N * 100:.1f}%)")

header("Late Payment Count Distribution")
for n, cnt in df["late_payment_count"].value_counts().sort_index().items():
    print(f"  {n} late pmt(s)  :  {cnt:>7,}  ({cnt / N * 100:.1f}%)")

print(f"\n{'=' * W}")
print("  [DONE]  Data generation complete.")
print(f"{'=' * W}\n")
