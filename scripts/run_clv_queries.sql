-- =============================================================================
-- run_clv_queries.sql
--
-- Customer Lifetime Value (CLV) & Segmentation Analysis Queries
-- Table   : customers
-- Purpose : Six analytical queries covering segment distribution, customer
--           profiles, churn risk, regional performance, payment behaviour,
--           and product-holding analysis. Designed for SQLite, DuckDB,
--           PostgreSQL, or any SQL engine that supports window functions.
-- =============================================================================


-- =============================================================================
-- QUERY 1: Segment Distribution
--
-- Summarises how the customer base splits across CLV segments.
-- Reports customer volumes, percentage share of the total portfolio,
-- average CLV score, and average annual spend per segment.
-- pct_of_total uses a window function so the GROUP BY totals are available
-- without a subquery.
-- Ordered by avg_clv descending to rank segments from most to least valuable.
-- =============================================================================

SELECT
    segment,
    COUNT(*)                                                        AS customer_count,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (),
        2
    )                                                               AS pct_of_total,
    ROUND(AVG(clv_score), 2)                                        AS avg_clv,
    ROUND(AVG(annual_spend), 2)                                     AS avg_annual_spend
FROM   customers
GROUP  BY segment
ORDER  BY avg_clv DESC;


-- =============================================================================
-- QUERY 2: Segment Profile
--
-- Builds a behavioural profile for each segment to support targeted
-- retention and engagement strategies.
-- Covers tenure, spend, product holdings, complaint levels, smart-meter
-- and app adoption rates, and renewal activity.
-- smart_meter_pct and app_registered_pct use CASE WHEN to convert the
-- Yes/No string column into a 0/1 flag before averaging.
-- =============================================================================

SELECT
    segment,
    ROUND(AVG(tenure_months),    1)                                 AS avg_tenure_months,
    ROUND(AVG(annual_spend),     2)                                 AS avg_annual_spend,
    ROUND(AVG(num_products),     2)                                 AS avg_products,
    ROUND(AVG(complaint_count),  2)                                 AS avg_complaints,
    ROUND(
        AVG(CASE WHEN smart_meter    = 'Yes' THEN 1.0 ELSE 0.0 END) * 100,
        1
    )                                                               AS smart_meter_pct,
    ROUND(
        AVG(CASE WHEN app_registered = 'Yes' THEN 1.0 ELSE 0.0 END) * 100,
        1
    )                                                               AS app_registered_pct,
    ROUND(AVG(renewal_count),    2)                                 AS avg_renewals
FROM   customers
GROUP  BY segment
ORDER  BY avg_renewals DESC;


-- =============================================================================
-- QUERY 3: Churn Risk by Segment
--
-- Breaks down the churn risk distribution within each segment.
-- pct_within_segment uses PARTITION BY segment so the denominator is the
-- segment total rather than the grand total, giving a within-segment
-- percentage. avg_clv shows the CLV value associated with each
-- segment-risk combination.
-- Ordered by segment and churn_risk for easy reading.
-- =============================================================================

SELECT
    segment,
    churn_risk,
    COUNT(*)                                                        AS customer_count,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY segment),
        2
    )                                                               AS pct_within_segment,
    ROUND(AVG(clv_score), 2)                                        AS avg_clv
FROM   customers
GROUP  BY segment, churn_risk
ORDER  BY segment, churn_risk;


-- =============================================================================
-- QUERY 4: Regional CLV Performance
--
-- Compares CLV performance across the five geographic regions.
-- CASE WHEN expressions flag Champions and Lost Customers so their counts
-- and portfolio percentages can be derived in a single pass without
-- self-joins or subqueries.
-- champion_pct and lost_pct are expressed as a percentage of that region's
-- total customer count.
-- Ordered by avg_clv descending to surface the highest-value regions first.
-- =============================================================================

SELECT
    region,
    COUNT(*)                                                        AS total_customers,
    ROUND(AVG(clv_score),    2)                                     AS avg_clv,
    ROUND(AVG(annual_spend), 2)                                     AS avg_spend,
    SUM(CASE WHEN segment = 'Champions'     THEN 1 ELSE 0 END)      AS champion_count,
    ROUND(
        SUM(CASE WHEN segment = 'Champions'     THEN 1.0 ELSE 0.0 END)
        / COUNT(*) * 100,
        2
    )                                                               AS champion_pct,
    SUM(CASE WHEN segment = 'Lost Customers' THEN 1 ELSE 0 END)     AS lost_count,
    ROUND(
        SUM(CASE WHEN segment = 'Lost Customers' THEN 1.0 ELSE 0.0 END)
        / COUNT(*) * 100,
        2
    )                                                               AS lost_pct
FROM   customers
GROUP  BY region
ORDER  BY avg_clv DESC;


-- =============================================================================
-- QUERY 5: Payment Method vs CLV
--
-- Analyses how payment method correlates with customer value and risk.
-- churn_rate_pct uses AVG(churn_flag) * 100, which works because churn_flag
-- is stored as 0/1; averaging it yields the proportion churned, then
-- multiplying by 100 gives the percentage.
-- avg_late_payments highlights the financial engagement level of each
-- payment cohort.
-- Ordered by avg_clv descending to rank payment methods by profitability.
-- =============================================================================

SELECT
    payment_method,
    COUNT(*)                                                        AS customer_count,
    ROUND(AVG(clv_score),          2)                               AS avg_clv,
    ROUND(AVG(annual_spend),       2)                               AS avg_spend,
    ROUND(AVG(late_payment_count), 2)                               AS avg_late_payments,
    ROUND(AVG(churn_flag) * 100,   2)                               AS churn_rate_pct
FROM   customers
GROUP  BY payment_method
ORDER  BY avg_clv DESC;


-- =============================================================================
-- QUERY 6: Product Holdings vs CLV
--
-- Examines whether customers with more products generate higher lifetime
-- value, display lower churn, and renew more frequently.
-- Results help quantify the up-sell and cross-sell opportunity: each
-- additional product should correlate with higher CLV and lower churn.
-- Ordered by num_products ascending for a clear progression view.
-- =============================================================================

SELECT
    num_products,
    COUNT(*)                                                        AS customer_count,
    ROUND(AVG(clv_score),    2)                                     AS avg_clv,
    ROUND(AVG(annual_spend), 2)                                     AS avg_spend,
    ROUND(AVG(churn_flag) * 100, 2)                                 AS churn_rate_pct,
    ROUND(AVG(renewal_count), 2)                                    AS avg_renewals
FROM   customers
GROUP  BY num_products
ORDER  BY num_products;
