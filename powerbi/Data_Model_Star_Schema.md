# Commercial Real Estate Portfolio Analytics — Star Schema Data Model

This document outlines the Star Schema relational data model designed in PostgreSQL and optimized for Power BI / Analysis Services.

---

## 1. Star Schema Architecture Diagram

```mermaid
erDiagram
    dim_markets ||--o{ dim_properties : "1 to Many (market_id)"
    dim_properties ||--o{ fct_leases : "1 to Many (property_id)"
    dim_tenants ||--o{ fct_leases : "1 to Many (tenant_id)"
    dim_properties ||--o{ fct_property_monthly_financials : "1 to Many (property_id)"
    dim_date ||--o{ fct_property_monthly_financials : "1 to Many (period_date -> date_key)"
    dim_date ||--o{ fct_leases : "1 to Many (lease_expiration_date -> date_key)"

    dim_markets {
        int market_id PK
        varchar metro_area
        char state
        varchar submarket
        numeric avg_class_a_rent_psf
        numeric avg_class_b_rent_psf
        numeric avg_industrial_rent_psf
        numeric avg_retail_rent_psf
        numeric market_vacancy_rate
        numeric market_cap_rate
    }

    dim_properties {
        int property_id PK
        varchar property_name
        int market_id FK
        varchar asset_class
        varchar property_subtype
        int total_rsf
        smallint year_built
        date acquisition_date
        numeric acquisition_price
        smallint number_of_floors
        int parking_spaces
        varchar address
    }

    dim_tenants {
        int tenant_id PK
        varchar tenant_name
        varchar industry
        varchar credit_rating
        varchar tenant_type
        boolean public_company
    }

    dim_date {
        date date_key PK
        smallint year
        smallint quarter
        smallint month
        varchar month_name
        varchar year_month
        varchar year_quarter
        smallint day_of_week
        varchar day_name
        boolean is_month_start
        boolean is_month_end
        boolean is_quarter_end
        smallint fiscal_year
        smallint fiscal_quarter
    }

    fct_leases {
        int lease_id PK
        int property_id FK
        int tenant_id FK
        varchar suite_number
        int leased_sqft
        date lease_start_date
        date lease_expiration_date FK
        numeric base_rent_psf_year
        numeric annual_escalation_pct
        varchar lease_type
        varchar lease_status
        smallint free_rent_months
        numeric tenant_improvement_psf
    }

    fct_property_monthly_financials {
        int record_id PK
        int property_id FK
        date period_date FK
        numeric gross_rental_revenue
        numeric other_income
        numeric cam_charges
        numeric property_taxes
        numeric insurance
        numeric utilities
        numeric repairs_maintenance
        numeric management_fees
    }
```

---

## 2. Table Granularity & Schema Specification

### Dimension Tables

| Dimension | Primary Key | Granularity | Business Purpose |
| :--- | :--- | :--- | :--- |
| **`dim_markets`** | `market_id` | 1 row per Sunbelt Metro Submarket | Market asking rents, baseline cap rates & market vacancy benchmarks |
| **`dim_properties`** | `property_id` | 1 row per physical commercial property | Property master data: Asset class, RSF, Acquisition price, physical attributes |
| **`dim_tenants`** | `tenant_id` | 1 row per corporate tenant | Credit rating, industry classification, tenant scale (National/Regional/Local) |
| **`dim_date`** | `date_key` | 1 row per calendar day (2020–2030) | Master calendar for DAX time intelligence, fiscal calendar, reporting periods |

### Fact Tables

| Fact Table | Primary Key | Foreign Keys | Granularity | Business Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **`fct_leases`** | `lease_id` | `property_id`, `tenant_id`, `lease_expiration_date` | 1 row per executed lease contract | Contractual base rent PSF, escalation, leased square footage, expiration dates |
| **`fct_property_monthly_financials`** | `record_id` | `property_id`, `period_date` | 1 row per property per month (36 months) | Actual gross revenue, OPEX breakdown (CAM, taxes, insurance, utilities, maintenance, management) |

---

## 3. Power BI Relationship Configuration

1. **`dim_properties` (1) ➔ `fct_leases` (\*)**:
   - Cardinality: One-to-Many (`1:*`)
   - Cross-filter direction: Single (`dim_properties` filters `fct_leases`)
   - Relationship Key: `property_id`

2. **`dim_tenants` (1) ➔ `fct_leases` (\*)**:
   - Cardinality: One-to-Many (`1:*`)
   - Cross-filter direction: Single (`dim_tenants` filters `fct_leases`)
   - Relationship Key: `tenant_id`

3. **`dim_properties` (1) ➔ `fct_property_monthly_financials` (\*)**:
   - Cardinality: One-to-Many (`1:*`)
   - Cross-filter direction: Single (`dim_properties` filters `fct_property_monthly_financials`)
   - Relationship Key: `property_id`

4. **`dim_date` (1) ➔ `fct_property_monthly_financials` (\*)**:
   - Cardinality: One-to-Many (`1:*`)
   - Cross-filter direction: Single (`dim_date` filters `fct_property_monthly_financials`)
   - Relationship Key: `dim_date[date_key] = fct_property_monthly_financials[period_date]` (Active)

5. **`dim_date` (1) ➔ `fct_leases` (\*)**:
   - Cardinality: One-to-Many (`1:*`)
   - Cross-filter direction: Single
   - Relationship Key: `dim_date[date_key] = fct_leases[lease_expiration_date]` (Active for Rollover Schedule)
   - Secondary Inactive Relationship: `dim_date[date_key] = fct_leases[lease_start_date]` (Activated via `USERELATIONSHIP` in DAX)

6. **`dim_markets` (1) ➔ `dim_properties` (\*)**:
   - Cardinality: One-to-Many (`1:*`)
   - Cross-filter direction: Single (`dim_markets` filters `dim_properties`)
   - Relationship Key: `market_id`
