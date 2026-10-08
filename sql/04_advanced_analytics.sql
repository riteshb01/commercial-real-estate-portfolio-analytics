-- Commercial Real Estate Portfolio Analytics
-- Advanced SQL Query Suite (PostgreSQL 16)
-- Schema: cre_analytics


SET search_path TO cre_analytics, public;

-- Query 1: Executive Portfolio Scorecard & YTD Metrics by Asset Class


WITH property_active_leases AS (
    SELECT
        p.property_id,
        p.property_name,
        p.asset_class,
        m.metro_area,
        p.total_rsf,
        p.acquisition_price,
        COUNT(DISTINCT l.lease_id) AS active_lease_count,
        COALESCE(SUM(l.leased_sqft), 0) AS leased_sqft,
        COALESCE(SUM(l.leased_sqft * l.base_rent_psf_year), 0) AS total_annual_contract_rent
    FROM dim_properties p
    JOIN dim_markets m ON p.market_id = m.market_id
    LEFT JOIN fct_leases l 
        ON p.property_id = l.property_id 
        AND l.lease_status = 'Active'
    GROUP BY p.property_id, p.property_name, p.asset_class, m.metro_area, p.total_rsf, p.acquisition_price
),
property_2025_financials AS (
    SELECT
        property_id,
        SUM(gross_rental_revenue + other_income) AS annual_2025_revenue,
        SUM(cam_charges + property_taxes + insurance + utilities + repairs_maintenance + management_fees) AS annual_2025_opex,
        SUM((gross_rental_revenue + other_income) - 
            (cam_charges + property_taxes + insurance + utilities + repairs_maintenance + management_fees)) AS annual_2025_noi
    FROM fct_property_monthly_financials
    WHERE period_date BETWEEN '2025-01-01' AND '2025-12-31'
    GROUP BY property_id
)
SELECT
    pal.asset_class,
    COUNT(DISTINCT pal.property_id) AS property_count,
    SUM(pal.total_rsf) AS total_rsf,
    SUM(pal.leased_sqft) AS occupied_rsf,
    ROUND((SUM(pal.leased_sqft)::NUMERIC / SUM(pal.total_rsf)) * 100, 2) AS occupancy_rate_pct,
    ROUND(SUM(pfin.annual_2025_revenue), 2) AS annual_2025_revenue,
    ROUND(SUM(pfin.annual_2025_opex), 2) AS annual_2025_opex,
    ROUND(SUM(pfin.annual_2025_noi), 2) AS annual_2025_noi,
    ROUND((SUM(pfin.annual_2025_noi) / NULLIF(SUM(pfin.annual_2025_revenue), 0)) * 100, 2) AS noi_margin_pct,
    ROUND((SUM(pfin.annual_2025_revenue) / NULLIF(SUM(pal.total_rsf), 0)), 2) AS revenue_psf,
    ROUND((SUM(pfin.annual_2025_opex) / NULLIF(SUM(pal.total_rsf), 0)), 2) AS opex_psf,
    ROUND((SUM(pfin.annual_2025_noi) / NULLIF(SUM(pal.total_rsf), 0)), 2) AS noi_psf,
    ROUND((SUM(pfin.annual_2025_noi) / NULLIF(SUM(pal.acquisition_price), 0)) * 100, 2) AS cap_rate_on_cost_pct
FROM property_active_leases pal
JOIN property_2025_financials pfin ON pal.property_id = pfin.property_id
GROUP BY pal.asset_class
ORDER BY annual_2025_revenue DESC;


-- Query 2: Rolling 3-Month & 12-Month NOI and Margin Trends


WITH monthly_totals AS (
    SELECT
        f.period_date,
        d.year,
        d.month,
        d.year_month,
        SUM(f.gross_rental_revenue + f.other_income) AS monthly_revenue,
        SUM(f.cam_charges + f.property_taxes + f.insurance + f.utilities + f.repairs_maintenance + f.management_fees) AS monthly_opex,
        SUM((f.gross_rental_revenue + f.other_income) - 
            (f.cam_charges + f.property_taxes + f.insurance + f.utilities + f.repairs_maintenance + f.management_fees)) AS monthly_noi
    FROM fct_property_monthly_financials f
    JOIN dim_date d ON f.period_date = d.date_key
    GROUP BY f.period_date, d.year, d.month, d.year_month
)
SELECT
    year_month,
    ROUND(monthly_revenue, 2) AS monthly_revenue,
    ROUND(monthly_opex, 2) AS monthly_opex,
    ROUND(monthly_noi, 2) AS monthly_noi,
    ROUND((monthly_noi / NULLIF(monthly_revenue, 0)) * 100, 2) AS monthly_noi_margin_pct,
    
    -- Trailing 3-Month Rolling Averages
    ROUND(AVG(monthly_revenue) OVER (
        ORDER BY period_date 
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2) AS t3m_avg_revenue,
    ROUND(AVG(monthly_noi) OVER (
        ORDER BY period_date 
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2) AS t3m_avg_noi,
    
    -- Trailing 12-Month (T12) Cumulative Sums
    ROUND(SUM(monthly_revenue) OVER (
        ORDER BY period_date 
        ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
    ), 2) AS t12m_cumulative_revenue,
    ROUND(SUM(monthly_noi) OVER (
        ORDER BY period_date 
        ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
    ), 2) AS t12m_cumulative_noi,
    
    -- T12 Rolling NOI Margin
    ROUND(
        (SUM(monthly_noi) OVER (ORDER BY period_date ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) /
         NULLIF(SUM(monthly_revenue) OVER (ORDER BY period_date ROWS BETWEEN 11 PRECEDING AND CURRENT ROW), 0)) * 100, 2
    ) AS t12m_rolling_noi_margin_pct
FROM monthly_totals
ORDER BY period_date ASC;


-- Query 3: Lease Rollover Schedule & WALT by Property


WITH lease_term_calc AS (
    SELECT
        l.property_id,
        p.property_name,
        p.asset_class,
        m.metro_area,
        p.total_rsf,
        l.lease_id,
        l.leased_sqft,
        l.base_rent_psf_year,
        (l.leased_sqft * l.base_rent_psf_year) AS annual_rent,
        EXTRACT(YEAR FROM l.lease_expiration_date)::INT AS exp_year,
        -- Remaining term in years from reference date (2025-12-31)
        GREATEST(0, (EXTRACT(YEAR FROM AGE(l.lease_expiration_date, '2025-12-31'::DATE)) + 
                     EXTRACT(MONTH FROM AGE(l.lease_expiration_date, '2025-12-31'::DATE))/12.0)) AS remaining_years
    FROM fct_leases l
    JOIN dim_properties p ON l.property_id = p.property_id
    JOIN dim_markets m ON p.market_id = m.market_id
    WHERE l.lease_status = 'Active'
)
SELECT
    property_name,
    asset_class,
    metro_area,
    total_rsf,
    SUM(leased_sqft) AS occupied_rsf,
    ROUND((SUM(leased_sqft)::NUMERIC / total_rsf) * 100, 2) AS occupancy_pct,
    
    -- Weighted Average Lease Term (WALT) in Years (Square-Footage Weighted)
    ROUND(
        (SUM(leased_sqft * remaining_years) / NULLIF(SUM(leased_sqft), 0))::NUMERIC, 2
    ) AS sqft_walt_years,
    
    -- Weighted Average Lease Term (WALT) in Years (Rent Weighted)
    ROUND(
        (SUM(annual_rent * remaining_years) / NULLIF(SUM(annual_rent), 0))::NUMERIC, 2
    ) AS rent_walt_years,
    
    -- Rollover Expiration Buckets (% of Leased RSF Expiring)
    ROUND(COALESCE(SUM(CASE WHEN exp_year <= 2026 THEN leased_sqft END), 0)::NUMERIC / NULLIF(SUM(leased_sqft), 0) * 100, 1) AS pct_expiring_2026,
    ROUND(COALESCE(SUM(CASE WHEN exp_year = 2027 THEN leased_sqft END), 0)::NUMERIC / NULLIF(SUM(leased_sqft), 0) * 100, 1) AS pct_expiring_2027,
    ROUND(COALESCE(SUM(CASE WHEN exp_year = 2028 THEN leased_sqft END), 0)::NUMERIC / NULLIF(SUM(leased_sqft), 0) * 100, 1) AS pct_expiring_2028,
    ROUND(COALESCE(SUM(CASE WHEN exp_year >= 2029 THEN leased_sqft END), 0)::NUMERIC / NULLIF(SUM(leased_sqft), 0) * 100, 1) AS pct_expiring_2029_plus
FROM lease_term_calc
GROUP BY property_id, property_name, asset_class, metro_area, total_rsf
ORDER BY sqft_walt_years ASC;


-- Query 4: Tenant Concentration & Credit Risk Exposure (Top 10 + HHI)


WITH tenant_portfolio_share AS (
    SELECT
        t.tenant_id,
        t.tenant_name,
        t.industry,
        t.credit_rating,
        t.tenant_type,
        COUNT(DISTINCT l.property_id) AS property_count,
        SUM(l.leased_sqft) AS total_leased_sqft,
        ROUND(SUM(l.leased_sqft * l.base_rent_psf_year), 2) AS annual_contract_revenue,
        -- Total portfolio annual revenue across all active leases
        SUM(SUM(l.leased_sqft * l.base_rent_psf_year)) OVER () AS portfolio_total_annual_revenue
    FROM dim_tenants t
    JOIN fct_leases l ON t.tenant_id = l.tenant_id
    WHERE l.lease_status = 'Active'
    GROUP BY t.tenant_id, t.tenant_name, t.industry, t.credit_rating, t.tenant_type
),
ranked_tenants AS (
    SELECT
        tenant_name,
        industry,
        credit_rating,
        tenant_type,
        property_count,
        total_leased_sqft,
        annual_contract_revenue,
        ROUND((annual_contract_revenue / portfolio_total_annual_revenue) * 100, 2) AS revenue_share_pct,
        -- Cumulative revenue share
        ROUND(
            SUM((annual_contract_revenue / portfolio_total_annual_revenue) * 100) OVER (
                ORDER BY annual_contract_revenue DESC 
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ), 2
        ) AS cumulative_revenue_share_pct,
        -- Revenue rank
        ROW_NUMBER() OVER (ORDER BY annual_contract_revenue DESC) AS revenue_rank,
        -- Credit category
        CASE 
            WHEN credit_rating IN ('AAA', 'AA', 'A', 'BBB') THEN 'Investment Grade'
            WHEN credit_rating IN ('BB', 'B') THEN 'Speculative Grade'
            ELSE 'Non-Rated'
        END AS credit_tier
    FROM tenant_portfolio_share
)
SELECT
    revenue_rank,
    tenant_name,
    industry,
    credit_rating,
    credit_tier,
    tenant_type,
    property_count,
    total_leased_sqft,
    annual_contract_revenue,
    revenue_share_pct,
    cumulative_revenue_share_pct
FROM ranked_tenants
WHERE revenue_rank <= 10
ORDER BY revenue_rank ASC;


-- Query 5: Mark-to-Market Rent Gap & Loss-to-Lease Analysis


WITH property_market_benchmark AS (
    SELECT
        p.property_id,
        p.property_name,
        p.asset_class,
        m.metro_area,
        l.lease_id,
        t.tenant_name,
        l.leased_sqft,
        l.base_rent_psf_year AS in_place_rent_psf,
        l.lease_expiration_date,
        -- Matching prevailing market asking rent
        CASE
            WHEN p.asset_class = 'Office' AND p.property_subtype ILIKE '%Class A%' THEN m.avg_class_a_rent_psf
            WHEN p.asset_class = 'Office' THEN m.avg_class_b_rent_psf
            WHEN p.asset_class = 'Industrial' THEN m.avg_industrial_rent_psf
            WHEN p.asset_class = 'Retail' THEN m.avg_retail_rent_psf
        END AS market_asking_rent_psf
    FROM fct_leases l
    JOIN dim_properties p ON l.property_id = p.property_id
    JOIN dim_markets m ON p.market_id = m.market_id
    JOIN dim_tenants t ON l.tenant_id = t.tenant_id
    WHERE l.lease_status = 'Active'
)
SELECT
    metro_area,
    asset_class,
    COUNT(DISTINCT property_id) AS property_count,
    COUNT(lease_id) AS total_leases,
    SUM(leased_sqft) AS total_leased_sqft,
    ROUND(AVG(in_place_rent_psf), 2) AS avg_in_place_rent_psf,
    ROUND(AVG(market_asking_rent_psf), 2) AS avg_market_rent_psf,
    ROUND(AVG(market_asking_rent_psf - in_place_rent_psf), 2) AS avg_rent_gap_psf,
    ROUND(((AVG(market_asking_rent_psf) - AVG(in_place_rent_psf)) / AVG(in_place_rent_psf)) * 100, 2) AS mark_to_market_gap_pct,
    -- Total Portfolio Loss-to-Lease / Annual Mark-to-Market Opportunity ($)
    ROUND(SUM(leased_sqft * (market_asking_rent_psf - in_place_rent_psf)), 2) AS total_annual_mtm_opportunity
FROM property_market_benchmark
GROUP BY metro_area, asset_class
ORDER BY total_annual_mtm_opportunity DESC;


-- Query 6: Month-over-Month (MoM) & Year-over-Year (YoY) Variance


WITH monthly_portfolio_performance AS (
    SELECT
        f.period_date,
        d.year,
        d.month,
        d.year_month,
        SUM(f.gross_rental_revenue + f.other_income) AS total_revenue,
        SUM((f.gross_rental_revenue + f.other_income) - 
            (f.cam_charges + f.property_taxes + f.insurance + f.utilities + f.repairs_maintenance + f.management_fees)) AS total_noi
    FROM fct_property_monthly_financials f
    JOIN dim_date d ON f.period_date = d.date_key
    GROUP BY f.period_date, d.year, d.month, d.year_month
),
variance_analysis AS (
    SELECT
        year_month,
        total_revenue,
        total_noi,
        -- Prior Month Values (LAG 1)
        LAG(total_revenue, 1) OVER (ORDER BY period_date) AS prior_month_revenue,
        LAG(total_noi, 1) OVER (ORDER BY period_date) AS prior_month_noi,
        -- Prior Year Same Month Values (LAG 12)
        LAG(total_revenue, 12) OVER (ORDER BY period_date) AS prior_year_revenue,
        LAG(total_noi, 12) OVER (ORDER BY period_date) AS prior_year_noi
    FROM monthly_portfolio_performance
)
SELECT
    year_month,
    ROUND(total_revenue, 2) AS total_revenue,
    ROUND(total_noi, 2) AS total_noi,
    
    -- Month-over-Month (MoM) Growth
    ROUND(((total_revenue - prior_month_revenue) / NULLIF(prior_month_revenue, 0)) * 100, 2) AS revenue_mom_growth_pct,
    ROUND(((total_noi - prior_month_noi) / NULLIF(prior_month_noi, 0)) * 100, 2) AS noi_mom_growth_pct,
    
    -- Year-over-Year (YoY) Growth
    ROUND(((total_revenue - prior_year_revenue) / NULLIF(prior_year_revenue, 0)) * 100, 2) AS revenue_yoy_growth_pct,
    ROUND(((total_noi - prior_year_noi) / NULLIF(prior_year_noi, 0)) * 100, 2) AS noi_yoy_growth_pct
FROM variance_analysis
WHERE prior_year_revenue IS NOT NULL  -- Filter to periods with YoY comparisons (2024-2025)
ORDER BY year_month ASC;


-- Query 7: Lease Rollover Stress Testing & Cash Flow Sensitivity
-- Scenarios: 100% / 70% / 40% renewal across 2026-2027 expirations


WITH upcoming_expirations AS (
    SELECT
        p.asset_class,
        m.metro_area,
        COUNT(l.lease_id) AS expiring_lease_count,
        SUM(l.leased_sqft) AS expiring_sqft,
        SUM(l.leased_sqft * l.base_rent_psf_year) AS expiring_annual_revenue
    FROM fct_leases l
    JOIN dim_properties p ON l.property_id = p.property_id
    JOIN dim_markets m ON p.market_id = m.market_id
    WHERE l.lease_status = 'Active'
      AND l.lease_expiration_date BETWEEN '2026-01-01' AND '2027-12-31'
    GROUP BY p.asset_class, m.metro_area
)
SELECT
    metro_area,
    asset_class,
    expiring_lease_count,
    expiring_sqft,
    ROUND(expiring_annual_revenue, 2) AS base_expiring_revenue_100pct,
    
    -- Scenario 1: Moderate Stress (70% Renewal Rate, 30% Loss)
    ROUND(expiring_annual_revenue * 0.70, 2) AS scenario_moderate_revenue_70pct,
    ROUND(expiring_annual_revenue * 0.30, 2) AS moderate_revenue_at_risk_loss,
    
    -- Scenario 2: Severe Stress (40% Renewal Rate, 60% Loss)
    ROUND(expiring_annual_revenue * 0.40, 2) AS scenario_severe_revenue_40pct,
    ROUND(expiring_annual_revenue * 0.60, 2) AS severe_revenue_at_risk_loss,
    
    -- Scenario 3: Total Vacancy Loss (0% Renewal)
    ROUND(expiring_annual_revenue, 2) AS worst_case_100pct_loss
FROM upcoming_expirations
ORDER BY expiring_annual_revenue DESC;


-- Query 8: Operating Expense Efficiency & Outlier Detection


WITH property_opex_2025 AS (
    SELECT
        p.property_id,
        p.property_name,
        p.asset_class,
        m.metro_area,
        p.total_rsf,
        SUM(f.cam_charges) AS annual_cam,
        SUM(f.property_taxes) AS annual_taxes,
        SUM(f.insurance) AS annual_insurance,
        SUM(f.utilities) AS annual_utilities,
        SUM(f.repairs_maintenance) AS annual_repairs,
        SUM(f.management_fees) AS annual_mgmt,
        SUM(f.cam_charges + f.property_taxes + f.insurance + f.utilities + f.repairs_maintenance + f.management_fees) AS total_annual_opex
    FROM dim_properties p
    JOIN dim_markets m ON p.market_id = m.market_id
    JOIN fct_property_monthly_financials f ON p.property_id = f.property_id
    WHERE f.period_date BETWEEN '2025-01-01' AND '2025-12-31'
    GROUP BY p.property_id, p.property_name, p.asset_class, m.metro_area, p.total_rsf
),
opex_psf_metrics AS (
    SELECT
        property_id,
        property_name,
        asset_class,
        metro_area,
        total_rsf,
        ROUND((total_annual_opex / total_rsf), 2) AS total_opex_psf,
        ROUND((annual_cam / total_rsf), 2) AS cam_psf,
        ROUND((annual_taxes / total_rsf), 2) AS taxes_psf,
        ROUND((annual_insurance / total_rsf), 2) AS insurance_psf,
        ROUND((annual_utilities / total_rsf), 2) AS utilities_psf,
        ROUND((annual_repairs / total_rsf), 2) AS repairs_psf,
        -- Asset Class Benchmark Average OPEX PSF
        ROUND(AVG(total_annual_opex / total_rsf) OVER (PARTITION BY asset_class), 2) AS asset_class_avg_opex_psf,
        -- Variance from Asset Class Average
        ROUND(
            (total_annual_opex / total_rsf) - 
            AVG(total_annual_opex / total_rsf) OVER (PARTITION BY asset_class), 2
        ) AS variance_from_benchmark_psf
    FROM property_opex_2025
)
SELECT
    property_name,
    asset_class,
    metro_area,
    total_rsf,
    total_opex_psf,
    asset_class_avg_opex_psf,
    variance_from_benchmark_psf,
    cam_psf,
    taxes_psf,
    insurance_psf,
    utilities_psf,
    repairs_psf,
    CASE 
        WHEN variance_from_benchmark_psf > 2.00 THEN 'High Cost Outlier (> +$2.00/SF)'
        WHEN variance_from_benchmark_psf < -1.50 THEN 'Highly Efficient (< -$1.50/SF)'
        ELSE 'In-Line with Peers'
    END AS cost_efficiency_rating
FROM opex_psf_metrics
ORDER BY variance_from_benchmark_psf DESC;


-- Query 9: Property Asset Class & Market Performance Matrix


WITH property_summary_2025 AS (
    SELECT
        p.market_id,
        m.metro_area,
        p.asset_class,
        p.property_id,
        p.total_rsf,
        COALESCE(SUM(l.leased_sqft), 0) AS occupied_rsf,
        fin.revenue,
        fin.noi
    FROM dim_properties p
    JOIN dim_markets m ON p.market_id = m.market_id
    LEFT JOIN fct_leases l ON p.property_id = l.property_id AND l.lease_status = 'Active'
    JOIN (
        SELECT 
            property_id,
            SUM(gross_rental_revenue + other_income) AS revenue,
            SUM((gross_rental_revenue + other_income) - 
                (cam_charges + property_taxes + insurance + utilities + repairs_maintenance + management_fees)) AS noi
        FROM fct_property_monthly_financials
        WHERE period_date BETWEEN '2025-01-01' AND '2025-12-31'
        GROUP BY property_id
    ) fin ON p.property_id = fin.property_id
    GROUP BY p.market_id, m.metro_area, p.asset_class, p.property_id, p.total_rsf, fin.revenue, fin.noi
)
SELECT
    metro_area,
    asset_class,
    COUNT(DISTINCT property_id) AS property_count,
    SUM(total_rsf) AS total_rsf,
    SUM(occupied_rsf) AS occupied_rsf,
    ROUND((SUM(occupied_rsf)::NUMERIC / SUM(total_rsf)) * 100, 2) AS occupancy_pct,
    ROUND(SUM(revenue), 2) AS total_annual_revenue,
    ROUND(SUM(noi), 2) AS total_annual_noi,
    ROUND((SUM(noi) / NULLIF(SUM(revenue), 0)) * 100, 2) AS noi_margin_pct,
    ROUND((SUM(revenue) / NULLIF(SUM(total_rsf), 0)), 2) AS revenue_psf,
    ROUND((SUM(noi) / NULLIF(SUM(total_rsf), 0)), 2) AS noi_psf
FROM property_summary_2025
GROUP BY metro_area, asset_class
ORDER BY metro_area, asset_class;


-- Query 10: Actionable Asset Management Expiration Alert (24-Month)
-- Prioritizes upcoming lease expirations by tenant size and urgency


SELECT
    l.lease_id,
    p.property_name,
    p.asset_class,
    m.metro_area,
    t.tenant_name,
    t.industry,
    t.credit_rating,
    l.suite_number,
    l.leased_sqft,
    l.base_rent_psf_year,
    ROUND(l.leased_sqft * l.base_rent_psf_year, 2) AS annual_rent_at_risk,
    l.lease_expiration_date,
    (l.lease_expiration_date - '2025-12-31'::DATE) AS days_until_expiration,
    ROUND((l.lease_expiration_date - '2025-12-31'::DATE) / 30.4, 1) AS months_until_expiration,
    
    -- Action Priority Tier
    CASE
        WHEN l.leased_sqft >= 30000 AND l.lease_expiration_date <= '2026-12-31'::DATE THEN 'URGENT: Tier 1 Major Anchor (Expiring < 12M)'
        WHEN l.lease_expiration_date <= '2026-12-31'::DATE THEN 'HIGH: Tier 2 Expiration (< 12M)'
        WHEN l.leased_sqft >= 30000 THEN 'MEDIUM: Tier 3 Anchor Expiration (12-24M)'
        ELSE 'STANDARD: Tier 4 Lease Expiration (12-24M)'
    END AS asset_management_action_priority

FROM fct_leases l
JOIN dim_properties p ON l.property_id = p.property_id
JOIN dim_markets m ON p.market_id = m.market_id
JOIN dim_tenants t ON l.tenant_id = t.tenant_id
WHERE l.lease_status = 'Active'
  AND l.lease_expiration_date BETWEEN '2026-01-01' AND '2027-12-31'
ORDER BY l.lease_expiration_date ASC, l.leased_sqft DESC;
