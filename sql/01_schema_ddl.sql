-- ============================================================
-- Commercial Real Estate Portfolio Analytics
-- Database Schema Definition (PostgreSQL 16)
-- ============================================================
--
-- Portfolio: 25 institutional-grade properties across 4 Sunbelt
--            markets (Austin, DFW, Atlanta, Charlotte)
-- Schema:    cre_analytics (normalized 3NF + analytical support)
--
-- Tables:
--   Dimensions:  dim_date, dim_markets, dim_properties, dim_tenants
--   Facts:       fct_leases, fct_property_monthly_financials
--
-- ============================================================

-- Create dedicated schema
CREATE SCHEMA IF NOT EXISTS cre_analytics;
SET search_path TO cre_analytics, public;

-- ============================================================
-- DIMENSION TABLES
-- ============================================================

-- ---------------------------------------------------------
-- Date Dimension (for Star Schema / Power BI time intelligence)
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_date (
    date_key            DATE        PRIMARY KEY,
    year                SMALLINT    NOT NULL,
    quarter             SMALLINT    NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    month               SMALLINT    NOT NULL CHECK (month BETWEEN 1 AND 12),
    month_name          VARCHAR(20) NOT NULL,
    year_month          VARCHAR(7)  NOT NULL,       -- '2023-01'
    year_quarter        VARCHAR(7)  NOT NULL,       -- '2023-Q1'
    day_of_week         SMALLINT    NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    day_name            VARCHAR(15) NOT NULL,
    is_month_start      BOOLEAN     NOT NULL,
    is_month_end        BOOLEAN     NOT NULL,
    is_quarter_end      BOOLEAN     NOT NULL,
    fiscal_year         SMALLINT    NOT NULL,
    fiscal_quarter      SMALLINT    NOT NULL
);

COMMENT ON TABLE dim_date
    IS 'Date dimension for time-series analysis, Power BI star schema, and DAX time intelligence.';

-- Populate date dimension (2020-01-01 through 2030-12-31)
INSERT INTO dim_date (
    date_key, year, quarter, month, month_name, year_month, year_quarter,
    day_of_week, day_name, is_month_start, is_month_end, is_quarter_end,
    fiscal_year, fiscal_quarter
)
SELECT
    d::DATE                                                     AS date_key,
    EXTRACT(YEAR FROM d)::SMALLINT                              AS year,
    EXTRACT(QUARTER FROM d)::SMALLINT                           AS quarter,
    EXTRACT(MONTH FROM d)::SMALLINT                             AS month,
    TO_CHAR(d, 'Month')                                         AS month_name,
    TO_CHAR(d, 'YYYY-MM')                                       AS year_month,
    EXTRACT(YEAR FROM d)::TEXT || '-Q' || EXTRACT(QUARTER FROM d)::TEXT AS year_quarter,
    EXTRACT(DOW FROM d)::SMALLINT                               AS day_of_week,
    TO_CHAR(d, 'Day')                                           AS day_name,
    (d = DATE_TRUNC('month', d)::DATE)                          AS is_month_start,
    (d = (DATE_TRUNC('month', d) + INTERVAL '1 month - 1 day')::DATE) AS is_month_end,
    (d = (DATE_TRUNC('quarter', d) + INTERVAL '3 months - 1 day')::DATE) AS is_quarter_end,
    -- Fiscal year: Oct-Sep (Oct 2024 = FY2025)
    CASE WHEN EXTRACT(MONTH FROM d) >= 10
         THEN EXTRACT(YEAR FROM d)::SMALLINT + 1
         ELSE EXTRACT(YEAR FROM d)::SMALLINT
    END                                                         AS fiscal_year,
    CASE
        WHEN EXTRACT(MONTH FROM d) >= 10 THEN ((EXTRACT(MONTH FROM d)::INT - 10) / 3) + 1
        ELSE ((EXTRACT(MONTH FROM d)::INT + 2) / 3)
    END::SMALLINT                                               AS fiscal_quarter
FROM generate_series('2020-01-01'::DATE, '2030-12-31'::DATE, '1 day'::INTERVAL) d
ON CONFLICT (date_key) DO NOTHING;


-- ---------------------------------------------------------
-- Markets Dimension
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_markets (
    market_id               SERIAL      PRIMARY KEY,
    metro_area              VARCHAR(100) NOT NULL,
    state                   CHAR(2)     NOT NULL,
    submarket               VARCHAR(150),
    avg_class_a_rent_psf    NUMERIC(10,2),   -- $/SF/Year Class A Office
    avg_class_b_rent_psf    NUMERIC(10,2),   -- $/SF/Year Class B Office
    avg_industrial_rent_psf NUMERIC(10,2),   -- $/SF/Year Industrial
    avg_retail_rent_psf     NUMERIC(10,2),   -- $/SF/Year Retail
    market_vacancy_rate     NUMERIC(5,2),    -- Overall vacancy (%)
    market_cap_rate         NUMERIC(5,2)     -- Prevailing cap rate (%)
);

COMMENT ON TABLE dim_markets
    IS 'CRE market benchmarks for 4 Sunbelt metros. Rents are annual $/SF averages.';
COMMENT ON COLUMN dim_markets.avg_class_a_rent_psf
    IS 'Average asking rent for Class A office space ($/SF/year).';
COMMENT ON COLUMN dim_markets.market_cap_rate
    IS 'Prevailing market capitalization rate — key metric for property valuation.';


-- ---------------------------------------------------------
-- Properties Dimension
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_properties (
    property_id         SERIAL          PRIMARY KEY,
    property_name       VARCHAR(200)    NOT NULL,
    market_id           INT             NOT NULL REFERENCES dim_markets(market_id),
    asset_class         VARCHAR(50)     NOT NULL
                        CHECK (asset_class IN ('Office', 'Industrial', 'Retail')),
    property_subtype    VARCHAR(100),
    total_rsf           INT             NOT NULL CHECK (total_rsf > 0),
    year_built          SMALLINT,
    acquisition_date    DATE,
    acquisition_price   NUMERIC(15,2),
    number_of_floors    SMALLINT,
    parking_spaces      INT,
    address             VARCHAR(300)
);

COMMENT ON TABLE dim_properties
    IS '25 institutional-grade commercial properties across Austin, DFW, Atlanta, and Charlotte.';
COMMENT ON COLUMN dim_properties.total_rsf
    IS 'Total Rentable Square Feet — the leasable area of the property.';
COMMENT ON COLUMN dim_properties.asset_class
    IS 'Primary asset classification: Office (Class A/B), Industrial, or Retail.';
COMMENT ON COLUMN dim_properties.acquisition_price
    IS 'Purchase price at acquisition — basis for cap rate & return calculations.';

CREATE INDEX IF NOT EXISTS idx_properties_market
    ON dim_properties(market_id);
CREATE INDEX IF NOT EXISTS idx_properties_asset_class
    ON dim_properties(asset_class);


-- ---------------------------------------------------------
-- Tenants Dimension
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_tenants (
    tenant_id       SERIAL          PRIMARY KEY,
    tenant_name     VARCHAR(200)    NOT NULL,
    industry        VARCHAR(100),
    credit_rating   VARCHAR(10)
                    CHECK (credit_rating IN ('AAA', 'AA', 'A', 'BBB', 'BB', 'B', 'NR')),
    tenant_type     VARCHAR(50)
                    CHECK (tenant_type IN ('National', 'Regional', 'Local')),
    public_company  BOOLEAN         DEFAULT FALSE
);

COMMENT ON TABLE dim_tenants
    IS 'Commercial tenants across Technology, Finance, Healthcare, Logistics, and other sectors.';
COMMENT ON COLUMN dim_tenants.credit_rating
    IS 'Credit quality: investment-grade (BBB and above), speculative-grade (BB and below), NR = not rated.';
COMMENT ON COLUMN dim_tenants.tenant_type
    IS 'Operating scale: National (multi-market), Regional (single region), Local (single market).';

CREATE INDEX IF NOT EXISTS idx_tenants_industry
    ON dim_tenants(industry);
CREATE INDEX IF NOT EXISTS idx_tenants_credit
    ON dim_tenants(credit_rating);


-- ============================================================
-- FACT TABLES
-- ============================================================

-- ---------------------------------------------------------
-- Leases Fact Table
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS fct_leases (
    lease_id                SERIAL          PRIMARY KEY,
    property_id             INT             NOT NULL REFERENCES dim_properties(property_id),
    tenant_id               INT             NOT NULL REFERENCES dim_tenants(tenant_id),
    suite_number            VARCHAR(20),
    leased_sqft             INT             NOT NULL CHECK (leased_sqft > 0),
    lease_start_date        DATE            NOT NULL,
    lease_expiration_date   DATE            NOT NULL,
    base_rent_psf_year      NUMERIC(10,2)   NOT NULL CHECK (base_rent_psf_year > 0),
    annual_escalation_pct   NUMERIC(5,2)    DEFAULT 3.00,
    lease_type              VARCHAR(50)
                            CHECK (lease_type IN (
                                'NNN', 'Modified Gross', 'Full Service Gross', 'Percentage'
                            )),
    lease_status            VARCHAR(20)     DEFAULT 'Active'
                            CHECK (lease_status IN ('Active', 'Expired', 'Pending')),
    free_rent_months        SMALLINT        DEFAULT 0,
    tenant_improvement_psf  NUMERIC(10,2)   DEFAULT 0.00,

    -- Expiration must be after commencement
    CONSTRAINT chk_lease_dates CHECK (lease_expiration_date > lease_start_date)
);

COMMENT ON TABLE fct_leases
    IS 'Individual lease agreements linking tenants to specific property suites/bays.';
COMMENT ON COLUMN fct_leases.base_rent_psf_year
    IS 'Base annual rent per square foot at lease inception — escalates per annual_escalation_pct.';
COMMENT ON COLUMN fct_leases.lease_type
    IS 'Lease structure: NNN (tenant pays taxes/insurance/CAM), Modified Gross, Full Service Gross, Percentage (retail).';
COMMENT ON COLUMN fct_leases.free_rent_months
    IS 'Number of months of free rent (concession) at lease commencement.';
COMMENT ON COLUMN fct_leases.tenant_improvement_psf
    IS 'Landlord-funded tenant improvement allowance ($/SF) — amortized over lease term.';

CREATE INDEX IF NOT EXISTS idx_leases_property
    ON fct_leases(property_id);
CREATE INDEX IF NOT EXISTS idx_leases_tenant
    ON fct_leases(tenant_id);
CREATE INDEX IF NOT EXISTS idx_leases_expiration
    ON fct_leases(lease_expiration_date);
CREATE INDEX IF NOT EXISTS idx_leases_dates
    ON fct_leases(lease_start_date, lease_expiration_date);
CREATE INDEX IF NOT EXISTS idx_leases_status
    ON fct_leases(lease_status);


-- ---------------------------------------------------------
-- Property Monthly Financials Fact Table
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS fct_property_monthly_financials (
    record_id               SERIAL          PRIMARY KEY,
    property_id             INT             NOT NULL REFERENCES dim_properties(property_id),
    period_date             DATE            NOT NULL,  -- First of month (YYYY-MM-01)

    -- Revenue
    gross_rental_revenue    NUMERIC(15,2)   NOT NULL DEFAULT 0,
    other_income            NUMERIC(15,2)   DEFAULT 0,      -- Parking, storage, late fees

    -- Operating Expenses (OPEX)
    cam_charges             NUMERIC(15,2)   DEFAULT 0,      -- Common Area Maintenance
    property_taxes          NUMERIC(15,2)   DEFAULT 0,
    insurance               NUMERIC(15,2)   DEFAULT 0,
    utilities               NUMERIC(15,2)   DEFAULT 0,
    repairs_maintenance     NUMERIC(15,2)   DEFAULT 0,
    management_fees         NUMERIC(15,2)   DEFAULT 0,      -- Property management (% of revenue)

    -- One row per property per month
    CONSTRAINT uq_property_period UNIQUE (property_id, period_date)
);

COMMENT ON TABLE fct_property_monthly_financials
    IS '36 months (Jan 2023 – Dec 2025) of property-level operating financials.';
COMMENT ON COLUMN fct_property_monthly_financials.period_date
    IS 'First day of the reporting month (always YYYY-MM-01).';
COMMENT ON COLUMN fct_property_monthly_financials.gross_rental_revenue
    IS 'Total base rent collected from all active leases in the property for the month.';
COMMENT ON COLUMN fct_property_monthly_financials.cam_charges
    IS 'Common Area Maintenance: janitorial, landscaping, security, common-area utilities.';

CREATE INDEX IF NOT EXISTS idx_fin_property
    ON fct_property_monthly_financials(property_id);
CREATE INDEX IF NOT EXISTS idx_fin_period
    ON fct_property_monthly_financials(period_date);
CREATE INDEX IF NOT EXISTS idx_fin_property_period
    ON fct_property_monthly_financials(property_id, period_date);


-- ============================================================
-- GRANT READ ACCESS (for analytics/BI read-only user)
-- ============================================================
-- Uncomment if creating a read-only analytics user:
-- CREATE ROLE cre_analyst WITH LOGIN PASSWORD 'analyst_readonly';
-- GRANT USAGE ON SCHEMA cre_analytics TO cre_analyst;
-- GRANT SELECT ON ALL TABLES IN SCHEMA cre_analytics TO cre_analyst;
