-- ============================================================
-- Commercial Real Estate Portfolio Analytics
-- SQL Views & Analytical Data Marts (PostgreSQL 16)
-- ============================================================
-- Schema: cre_analytics
--
-- This script creates pre-aggregated analytical views and data
-- marts designed for executive dashboards, Power BI star schema
-- consumption, and asset management decision support.
-- ============================================================

SET search_path TO cre_analytics, public;

-- ============================================================
-- 1. VIEW: Monthly Property Performance Metrics
-- ============================================================
-- Granularity: Property x Month
-- Metrics: Gross Revenue, Total OPEX, NOI, NOI Margin %, Revenue PSF,
--          OPEX PSF, Expense Ratio %, Occupied SF, Occupancy Rate %
-- ============================================================

CREATE OR REPLACE VIEW vw_property_monthly_kpis AS
WITH lease_occupancy_by_month AS (
    -- Calculate active leased square footage per property per month
    SELECT
        p.property_id,
        f.period_date,
        COALESCE(SUM(l.leased_sqft), 0) AS occupied_sqft,
        COUNT(DISTINCT l.lease_id) AS active_lease_count,
        COUNT(DISTINCT l.tenant_id) AS active_tenant_count
    FROM dim_properties p
    CROSS JOIN (
        SELECT DISTINCT period_date FROM fct_property_monthly_financials
    ) f
    LEFT JOIN fct_leases l
        ON p.property_id = l.property_id
        AND l.lease_start_date <= f.period_date
        AND l.lease_expiration_date >= f.period_date
        AND l.lease_status = 'Active'
    GROUP BY p.property_id, f.period_date
),
monthly_metrics AS (
    SELECT
        f.record_id,
        f.property_id,
        p.property_name,
        p.asset_class,
        p.property_subtype,
        m.market_id,
        m.metro_area,
        m.state,
        f.period_date,
        d.year,
        d.quarter,
        d.month,
        d.year_month,
        d.year_quarter,
        p.total_rsf,
        COALESCE(occ.occupied_sqft, 0) AS occupied_sqft,
        ROUND((COALESCE(occ.occupied_sqft, 0)::NUMERIC / NULLIF(p.total_rsf, 0)) * 100, 2) AS occupancy_rate_pct,
        (p.total_rsf - COALESCE(occ.occupied_sqft, 0)) AS vacant_sqft,
        ROUND(((p.total_rsf - COALESCE(occ.occupied_sqft, 0))::NUMERIC / NULLIF(p.total_rsf, 0)) * 100, 2) AS vacancy_rate_pct,
        COALESCE(occ.active_lease_count, 0) AS active_lease_count,
        COALESCE(occ.active_tenant_count, 0) AS active_tenant_count,
        
        -- Revenues
        f.gross_rental_revenue,
        f.other_income,
        (f.gross_rental_revenue + f.other_income) AS total_revenue,
        
        -- Operating Expenses (OPEX)
        f.cam_charges,
        f.property_taxes,
        f.insurance,
        f.utilities,
        f.repairs_maintenance,
        f.management_fees,
        (f.cam_charges + f.property_taxes + f.insurance + f.utilities + f.repairs_maintenance + f.management_fees) AS total_opex,
        
        -- Net Operating Income (NOI)
        ((f.gross_rental_revenue + f.other_income) - 
         (f.cam_charges + f.property_taxes + f.insurance + f.utilities + f.repairs_maintenance + f.management_fees)) AS net_operating_income,
        
        -- Financial Ratios & Unit Metrics (Annualized where appropriate)
        ROUND(
            (((f.gross_rental_revenue + f.other_income) - 
              (f.cam_charges + f.property_taxes + f.insurance + f.utilities + f.repairs_maintenance + f.management_fees)) / 
              NULLIF((f.gross_rental_revenue + f.other_income), 0)) * 100, 2
        ) AS noi_margin_pct,
        
        ROUND(
            ((f.cam_charges + f.property_taxes + f.insurance + f.utilities + f.repairs_maintenance + f.management_fees) / 
              NULLIF((f.gross_rental_revenue + f.other_income), 0)) * 100, 2
        ) AS opex_ratio_pct,
        
        ROUND(((f.gross_rental_revenue + f.other_income) * 12.0 / NULLIF(p.total_rsf, 0)), 2) AS annualized_rev_psf,
        ROUND(((f.cam_charges + f.property_taxes + f.insurance + f.utilities + f.repairs_maintenance + f.management_fees) * 12.0 / NULLIF(p.total_rsf, 0)), 2) AS annualized_opex_psf,
        ROUND((((f.gross_rental_revenue + f.other_income) - 
                (f.cam_charges + f.property_taxes + f.insurance + f.utilities + f.repairs_maintenance + f.management_fees)) * 12.0 / NULLIF(p.total_rsf, 0)), 2) AS annualized_noi_psf
    FROM fct_property_monthly_financials f
    JOIN dim_properties p ON f.property_id = p.property_id
    JOIN dim_markets m ON p.market_id = m.market_id
    JOIN dim_date d ON f.period_date = d.date_key
    LEFT JOIN lease_occupancy_by_month occ 
        ON f.property_id = occ.property_id 
        AND f.period_date = occ.period_date
)
SELECT * FROM monthly_metrics;

COMMENT ON VIEW vw_property_monthly_kpis
    IS 'Property-level monthly performance mart containing revenues, OPEX breakdown, NOI, occupancy, and PSF unit metrics.';


-- ============================================================
-- 2. VIEW: Lease Rollover & Expiration Risk Schedule
-- ============================================================
-- Granularity: Lease / Property / Expiration Year & Quarter
-- Metrics: Leased RSF expiring, Annual base rent expiring,
--          % of total portfolio RSF & revenue at risk, Remaining Term (Months)
-- ============================================================

CREATE OR REPLACE VIEW vw_lease_rollover_schedule AS
WITH portfolio_totals AS (
    SELECT
        SUM(total_rsf) AS total_portfolio_rsf,
        SUM(leased_sqft * base_rent_psf_year) AS total_portfolio_annual_rent
    FROM dim_properties p
    JOIN fct_leases l ON p.property_id = l.property_id
    WHERE l.lease_status = 'Active'
)
SELECT
    l.lease_id,
    l.property_id,
    p.property_name,
    p.asset_class,
    m.metro_area,
    l.tenant_id,
    t.tenant_name,
    t.industry,
    t.credit_rating,
    t.tenant_type,
    l.suite_number,
    l.leased_sqft,
    l.base_rent_psf_year,
    ROUND((l.leased_sqft * l.base_rent_psf_year), 2) AS annual_contract_rent,
    ROUND((l.leased_sqft * l.base_rent_psf_year) / 12.0, 2) AS monthly_contract_rent,
    l.lease_start_date,
    l.lease_expiration_date,
    l.lease_type,
    l.lease_status,
    d.year AS expiration_year,
    d.quarter AS expiration_quarter,
    d.year_quarter AS expiration_year_quarter,
    -- Remaining term in months from analysis reference date (2025-12-31)
    GREATEST(0, (EXTRACT(YEAR FROM AGE(l.lease_expiration_date, '2025-12-31'::DATE)) * 12 + 
                 EXTRACT(MONTH FROM AGE(l.lease_expiration_date, '2025-12-31'::DATE))))::INT AS remaining_term_months,
    ROUND(GREATEST(0, (EXTRACT(YEAR FROM AGE(l.lease_expiration_date, '2025-12-31'::DATE)) * 12 + 
                       EXTRACT(MONTH FROM AGE(l.lease_expiration_date, '2025-12-31'::DATE)))) / 12.0, 2) AS remaining_term_years,
    -- Risk percentages
    ROUND((l.leased_sqft::NUMERIC / pt.total_portfolio_rsf) * 100, 4) AS pct_portfolio_rsf,
    ROUND(((l.leased_sqft * l.base_rent_psf_year)::NUMERIC / pt.total_portfolio_annual_rent) * 100, 4) AS pct_portfolio_annual_rent,
    -- Rollover urgency classification
    CASE
        WHEN l.lease_expiration_date <= '2026-12-31'::DATE THEN 'Critical (Within 1 Year)'
        WHEN l.lease_expiration_date <= '2027-12-31'::DATE THEN 'Elevated (1 - 2 Years)'
        WHEN l.lease_expiration_date <= '2028-12-31'::DATE THEN 'Moderate (2 - 3 Years)'
        ELSE 'Long-Term (3+ Years)'
    END AS rollover_urgency_tier
FROM fct_leases l
JOIN dim_properties p ON l.property_id = p.property_id
JOIN dim_markets m ON p.market_id = m.market_id
JOIN dim_tenants t ON l.tenant_id = t.tenant_id
JOIN dim_date d ON l.lease_expiration_date = d.date_key
CROSS JOIN portfolio_totals pt
WHERE l.lease_status = 'Active';

COMMENT ON VIEW vw_lease_rollover_schedule
    IS 'Active lease rollover schedule with expiration timeline, remaining lease terms, and revenue-at-risk percentages.';


-- ============================================================
-- 3. VIEW: Tenant Concentration & Credit Exposure Mart
-- ============================================================
-- Granularity: Tenant
-- Metrics: Total leased RSF, Total annual rent, Number of properties,
--          % of total portfolio revenue, Credit rating, Concentration rank
-- ============================================================

CREATE OR REPLACE VIEW vw_tenant_concentration_risk AS
WITH portfolio_summary AS (
    SELECT
        SUM(l.leased_sqft) AS total_occupied_rsf,
        SUM(l.leased_sqft * l.base_rent_psf_year) AS total_annual_rent
    FROM fct_leases l
    WHERE l.lease_status = 'Active'
),
tenant_agg AS (
    SELECT
        t.tenant_id,
        t.tenant_name,
        t.industry,
        t.credit_rating,
        t.tenant_type,
        t.public_company,
        COUNT(DISTINCT l.lease_id) AS total_leases,
        COUNT(DISTINCT l.property_id) AS properties_occupied,
        ARRAY_TO_STRING(ARRAY_AGG(DISTINCT p.property_name), ', ') AS property_list,
        SUM(l.leased_sqft) AS total_leased_sqft,
        ROUND(SUM(l.leased_sqft * l.base_rent_psf_year), 2) AS total_annual_rent,
        ROUND(AVG(l.base_rent_psf_year), 2) AS weighted_avg_rent_psf,
        -- Weighted Average Lease Term (WALT) in years for this tenant
        ROUND(
            SUM(l.leased_sqft * GREATEST(0, (EXTRACT(YEAR FROM AGE(l.lease_expiration_date, '2025-12-31'::DATE)) + 
                                             EXTRACT(MONTH FROM AGE(l.lease_expiration_date, '2025-12-31'::DATE))/12.0))) / 
            NULLIF(SUM(l.leased_sqft), 0)::NUMERIC, 2
        ) AS tenant_walt_years
    FROM dim_tenants t
    JOIN fct_leases l ON t.tenant_id = l.tenant_id
    JOIN dim_properties p ON l.property_id = p.property_id
    WHERE l.lease_status = 'Active'
    GROUP BY t.tenant_id, t.tenant_name, t.industry, t.credit_rating, t.tenant_type, t.public_company
)
SELECT
    ta.*,
    ROUND((ta.total_leased_sqft::NUMERIC / ps.total_occupied_rsf) * 100, 2) AS pct_portfolio_occupied_rsf,
    ROUND((ta.total_annual_rent::NUMERIC / ps.total_annual_rent) * 100, 2) AS pct_portfolio_revenue,
    DENSE_RANK() OVER (ORDER BY ta.total_annual_rent DESC) AS revenue_rank,
    DENSE_RANK() OVER (ORDER BY ta.total_leased_sqft DESC) AS square_footage_rank,
    -- Investment grade flag
    CASE 
        WHEN ta.credit_rating IN ('AAA', 'AA', 'A', 'BBB') THEN 'Investment Grade'
        WHEN ta.credit_rating IN ('BB', 'B') THEN 'Speculative Grade'
        ELSE 'Non-Rated'
    END AS credit_category,
    -- Concentration risk flag
    CASE
        WHEN (ta.total_annual_rent::NUMERIC / ps.total_annual_rent) >= 0.05 THEN 'High Concentration (>5%)'
        WHEN (ta.total_annual_rent::NUMERIC / ps.total_annual_rent) >= 0.025 THEN 'Medium Concentration (2.5-5%)'
        ELSE 'Low Concentration (<2.5%)'
    END AS concentration_risk_tier
FROM tenant_agg ta
CROSS JOIN portfolio_summary ps;

COMMENT ON VIEW vw_tenant_concentration_risk
    IS 'Tenant concentration mart tracking revenue share, credit tier, WALT, and concentration risk categories.';


-- ============================================================
-- 4. VIEW: Mark-to-Market Rent Analysis (In-Place vs Market)
-- ============================================================
-- Granularity: Property x Asset Class
-- Purpose: Identifies loss-to-lease and upside potential upon renewal
-- ============================================================

CREATE OR REPLACE VIEW vw_market_rent_variance AS
SELECT
    p.property_id,
    p.property_name,
    p.asset_class,
    p.property_subtype,
    m.metro_area,
    m.state,
    p.total_rsf,
    COALESCE(SUM(l.leased_sqft), 0) AS occupied_sqft,
    
    -- In-place weighted average rent PSF
    ROUND(
        SUM(l.leased_sqft * l.base_rent_psf_year)::NUMERIC / 
        NULLIF(SUM(l.leased_sqft), 0), 2
    ) AS in_place_weighted_rent_psf,
    
    -- Prevailing market asking rent PSF based on asset class
    CASE
        WHEN p.asset_class = 'Office' AND p.property_subtype ILIKE '%Class A%' THEN m.avg_class_a_rent_psf
        WHEN p.asset_class = 'Office' THEN m.avg_class_b_rent_psf
        WHEN p.asset_class = 'Industrial' THEN m.avg_industrial_rent_psf
        WHEN p.asset_class = 'Retail' THEN m.avg_retail_rent_psf
    END AS market_asking_rent_psf,
    
    -- Variance: In-Place - Market
    ROUND(
        (SUM(l.leased_sqft * l.base_rent_psf_year)::NUMERIC / NULLIF(SUM(l.leased_sqft), 0)) -
        (CASE
            WHEN p.asset_class = 'Office' AND p.property_subtype ILIKE '%Class A%' THEN m.avg_class_a_rent_psf
            WHEN p.asset_class = 'Office' THEN m.avg_class_b_rent_psf
            WHEN p.asset_class = 'Industrial' THEN m.avg_industrial_rent_psf
            WHEN p.asset_class = 'Retail' THEN m.avg_retail_rent_psf
        END), 2
    ) AS rent_variance_psf,
    
    -- Variance %
    ROUND(
        (((SUM(l.leased_sqft * l.base_rent_psf_year)::NUMERIC / NULLIF(SUM(l.leased_sqft), 0)) -
          (CASE
              WHEN p.asset_class = 'Office' AND p.property_subtype ILIKE '%Class A%' THEN m.avg_class_a_rent_psf
              WHEN p.asset_class = 'Office' THEN m.avg_class_b_rent_psf
              WHEN p.asset_class = 'Industrial' THEN m.avg_industrial_rent_psf
              WHEN p.asset_class = 'Retail' THEN m.avg_retail_rent_psf
          END)) /
          NULLIF(CASE
              WHEN p.asset_class = 'Office' AND p.property_subtype ILIKE '%Class A%' THEN m.avg_class_a_rent_psf
              WHEN p.asset_class = 'Office' THEN m.avg_class_b_rent_psf
              WHEN p.asset_class = 'Industrial' THEN m.avg_industrial_rent_psf
              WHEN p.asset_class = 'Retail' THEN m.avg_retail_rent_psf
          END, 0)) * 100, 2
    ) AS rent_variance_pct,
    
    -- Annualized Mark-to-Market Revenue Opportunity (Positive = Upside on renewal, Negative = Above market / roll-down risk)
    ROUND(
        COALESCE(SUM(l.leased_sqft), 0) * 
        ((CASE
            WHEN p.asset_class = 'Office' AND p.property_subtype ILIKE '%Class A%' THEN m.avg_class_a_rent_psf
            WHEN p.asset_class = 'Office' THEN m.avg_class_b_rent_psf
            WHEN p.asset_class = 'Industrial' THEN m.avg_industrial_rent_psf
            WHEN p.asset_class = 'Retail' THEN m.avg_retail_rent_psf
        END) - 
        (SUM(l.leased_sqft * l.base_rent_psf_year)::NUMERIC / NULLIF(SUM(l.leased_sqft), 0))), 2
    ) AS annual_mark_to_market_gain_loss,
    
    -- Opportunity classification
    CASE
        WHEN (SUM(l.leased_sqft * l.base_rent_psf_year)::NUMERIC / NULLIF(SUM(l.leased_sqft), 0)) < 
             (CASE
                 WHEN p.asset_class = 'Office' AND p.property_subtype ILIKE '%Class A%' THEN m.avg_class_a_rent_psf
                 WHEN p.asset_class = 'Office' THEN m.avg_class_b_rent_psf
                 WHEN p.asset_class = 'Industrial' THEN m.avg_industrial_rent_psf
                 WHEN p.asset_class = 'Retail' THEN m.avg_retail_rent_psf
             END) * 0.95 THEN 'Below Market (Renewal Upside)'
        WHEN (SUM(l.leased_sqft * l.base_rent_psf_year)::NUMERIC / NULLIF(SUM(l.leased_sqft), 0)) > 
             (CASE
                 WHEN p.asset_class = 'Office' AND p.property_subtype ILIKE '%Class A%' THEN m.avg_class_a_rent_psf
                 WHEN p.asset_class = 'Office' THEN m.avg_class_b_rent_psf
                 WHEN p.asset_class = 'Industrial' THEN m.avg_industrial_rent_psf
                 WHEN p.asset_class = 'Retail' THEN m.avg_retail_rent_psf
             END) * 1.05 THEN 'Above Market (Roll-Down Risk)'
        ELSE 'At Market (Balanced)'
    END AS rent_position_status

FROM dim_properties p
JOIN dim_markets m ON p.market_id = m.market_id
LEFT JOIN fct_leases l ON p.property_id = l.property_id AND l.lease_status = 'Active'
GROUP BY p.property_id, p.property_name, p.asset_class, p.property_subtype, m.metro_area, m.state, p.total_rsf,
         m.avg_class_a_rent_psf, m.avg_class_b_rent_psf, m.avg_industrial_rent_psf, m.avg_retail_rent_psf;

COMMENT ON VIEW vw_market_rent_variance
    IS 'Mark-to-market comparison of in-place contract rents vs market asking rents by property.';


-- ============================================================
-- 5. VIEW: Portfolio Executive KPI Summary (2025 Full Year)
-- ============================================================
-- Granularity: Single Row / Executive Dashboard Card Metrics
-- ============================================================

CREATE OR REPLACE VIEW vw_executive_portfolio_summary AS
WITH active_leases AS (
    SELECT
        COUNT(DISTINCT l.lease_id) AS total_active_leases,
        COUNT(DISTINCT l.tenant_id) AS total_unique_tenants,
        SUM(l.leased_sqft) AS total_occupied_rsf,
        SUM(l.leased_sqft * l.base_rent_psf_year) AS total_annual_contract_rent,
        -- Portfolio WALT (Weighted Average Lease Term) in years
        ROUND(
            SUM(l.leased_sqft * GREATEST(0, (EXTRACT(YEAR FROM AGE(l.lease_expiration_date, '2025-12-31'::DATE)) + 
                                             EXTRACT(MONTH FROM AGE(l.lease_expiration_date, '2025-12-31'::DATE))/12.0))) / 
            NULLIF(SUM(l.leased_sqft), 0)::NUMERIC, 2
        ) AS portfolio_walt_years
    FROM fct_leases l
    WHERE l.lease_status = 'Active'
),
portfolio_props AS (
    SELECT
        COUNT(DISTINCT property_id) AS total_properties,
        COUNT(DISTINCT market_id) AS total_markets,
        SUM(total_rsf) AS total_portfolio_rsf,
        SUM(acquisition_price) AS total_acquisition_cost
    FROM dim_properties
),
y2025_financials AS (
    SELECT
        SUM(gross_rental_revenue + other_income) AS ytd_total_revenue,
        SUM(cam_charges + property_taxes + insurance + utilities + repairs_maintenance + management_fees) AS ytd_total_opex,
        SUM((gross_rental_revenue + other_income) - 
            (cam_charges + property_taxes + insurance + utilities + repairs_maintenance + management_fees)) AS ytd_noi
    FROM fct_property_monthly_financials
    WHERE period_date >= '2025-01-01' AND period_date <= '2025-12-31'
)
SELECT
    pp.total_properties,
    pp.total_markets,
    pp.total_portfolio_rsf,
    al.total_occupied_rsf,
    (pp.total_portfolio_rsf - al.total_occupied_rsf) AS total_vacant_rsf,
    ROUND((al.total_occupied_rsf::NUMERIC / NULLIF(pp.total_portfolio_rsf, 0)) * 100, 2) AS portfolio_occupancy_pct,
    al.total_active_leases,
    al.total_unique_tenants,
    al.portfolio_walt_years,
    pp.total_acquisition_cost,
    
    -- 2025 Annual Financials
    fin.ytd_total_revenue AS annual_2025_revenue,
    fin.ytd_total_opex AS annual_2025_opex,
    fin.ytd_noi AS annual_2025_noi,
    ROUND((fin.ytd_noi / NULLIF(fin.ytd_total_revenue, 0)) * 100, 2) AS portfolio_noi_margin_pct,
    ROUND((fin.ytd_total_opex / NULLIF(fin.ytd_total_revenue, 0)) * 100, 2) AS portfolio_opex_ratio_pct,
    
    -- Capitalization Rate on Acquisition Cost
    ROUND((fin.ytd_noi / NULLIF(pp.total_acquisition_cost, 0)) * 100, 2) AS portfolio_acq_cap_rate_pct,
    
    -- Unit metrics PSF
    ROUND((fin.ytd_total_revenue / NULLIF(pp.total_portfolio_rsf, 0)), 2) AS revenue_psf,
    ROUND((fin.ytd_total_opex / NULLIF(pp.total_portfolio_rsf, 0)), 2) AS opex_psf,
    ROUND((fin.ytd_noi / NULLIF(pp.total_portfolio_rsf, 0)), 2) AS noi_psf

FROM portfolio_props pp
CROSS JOIN active_leases al
CROSS JOIN y2025_financials fin;

COMMENT ON VIEW vw_executive_portfolio_summary
    IS 'Single-row executive scorecard summarizing total RSF, occupancy, WALT, 2025 NOI, NOI margin, and cap rates.';
