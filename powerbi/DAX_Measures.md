# Commercial Real Estate Portfolio Analytics — DAX Measure Library

This document contains the complete DAX measure repository for the Commercial Real Estate Portfolio Performance & Lease Risk Analytics model.

---

## 1. Portfolio & Property Core Financial KPIs

### Total Portfolio RSF
```dax
Total Portfolio RSF = 
SUM(dim_properties[total_rsf])
```
*Format: `#,##0` (e.g., 6,440,000 RSF)*

### Occupied RSF
```dax
Occupied RSF = 
CALCULATE(
    SUM(fct_leases[leased_sqft]),
    fct_leases[lease_status] = "Active"
)
```
*Format: `#,##0`*

### Vacant RSF
```dax
Vacant RSF = 
[Total Portfolio RSF] - [Occupied RSF]
```
*Format: `#,##0`*

### Portfolio Occupancy Rate (%)
```dax
Occupancy Rate % = 
DIVIDE([Occupied RSF], [Total Portfolio RSF], 0)
```
*Format: `0.0%`*

### Portfolio Vacancy Rate (%)
```dax
Vacancy Rate % = 
1 - [Occupancy Rate %]
```
*Format: `0.0%`*

### Gross Rental Revenue
```dax
Gross Rental Revenue = 
SUM(fct_property_monthly_financials[gross_rental_revenue])
```
*Format: `$#,##0`*

### Total Revenue (Gross Rent + Other Income)
```dax
Total Revenue = 
SUM(fct_property_monthly_financials[gross_rental_revenue]) + 
SUM(fct_property_monthly_financials[other_income])
```
*Format: `$#,##0`*

### Total Operating Expenses (OPEX)
```dax
Total OPEX = 
SUM(fct_property_monthly_financials[cam_charges]) +
SUM(fct_property_monthly_financials[property_taxes]) +
SUM(fct_property_monthly_financials[insurance]) +
SUM(fct_property_monthly_financials[utilities]) +
SUM(fct_property_monthly_financials[repairs_maintenance]) +
SUM(fct_property_monthly_financials[management_fees])
```
*Format: `$#,##0`*

### Net Operating Income (NOI)
```dax
Net Operating Income (NOI) = 
[Total Revenue] - [Total OPEX]
```
*Format: `$#,##0`*

### NOI Margin (%)
```dax
NOI Margin % = 
DIVIDE([Net Operating Income (NOI)], [Total Revenue], 0)
```
*Format: `0.0%`*

### Operating Expense Ratio (%)
```dax
Operating Expense Ratio % = 
DIVIDE([Total OPEX], [Total Revenue], 0)
```
*Format: `0.0%`*

### Annualized Revenue PSF
```dax
Annualized Revenue PSF = 
DIVIDE([Total Revenue] * 12, [Total Portfolio RSF], 0)
```
*Format: `$#,##0.00`*

### Annualized OPEX PSF
```dax
Annualized OPEX PSF = 
DIVIDE([Total OPEX] * 12, [Total Portfolio RSF], 0)
```
*Format: `$#,##0.00`*

### Annualized NOI PSF
```dax
Annualized NOI PSF = 
DIVIDE([Net Operating Income (NOI)] * 12, [Total Portfolio RSF], 0)
```
*Format: `$#,##0.00`*

### Capitalization Rate on Acquisition Cost (%)
```dax
Cap Rate on Cost % = 
DIVIDE(
    [Net Operating Income (NOI)],
    SUM(dim_properties[acquisition_price]),
    0
)
```
*Format: `0.00%`*

---

## 2. Time Intelligence & Variance Measures

### Prior Year Revenue (PY)
```dax
Revenue PY = 
CALCULATE(
    [Total Revenue],
    SAMEPERIODLASTYEAR(dim_date[date_key])
)
```
*Format: `$#,##0`*

### Prior Year Net Operating Income (NOI PY)
```dax
NOI PY = 
CALCULATE(
    [Net Operating Income (NOI)],
    SAMEPERIODLASTYEAR(dim_date[date_key])
)
```
*Format: `$#,##0`*

### Year-over-Year NOI Growth ($)
```dax
NOI YoY Variance $ = 
[Net Operating Income (NOI)] - [NOI PY]
```
*Format: `$#,##0`*

### Year-over-Year NOI Growth (%)
```dax
NOI YoY Growth % = 
DIVIDE([NOI YoY Variance $], [NOI PY], 0)
```
*Format: `+0.0%;-0.0%;0.0%`*

### Trailing 12-Month (T12) Revenue
```dax
T12 Revenue = 
CALCULATE(
    [Total Revenue],
    DATESINPERIOD(dim_date[date_key], MAX(dim_date[date_key]), -12, MONTH)
)
```
*Format: `$#,##0`*

### Trailing 12-Month (T12) NOI
```dax
T12 NOI = 
CALCULATE(
    [Net Operating Income (NOI)],
    DATESINPERIOD(dim_date[date_key], MAX(dim_date[date_key]), -12, MONTH)
)
```
*Format: `$#,##0`*

---

## 3. Lease Rollover & Expiration Analytics

### Weighted Average Lease Term (WALT - Years)
```dax
WALT (Years) = 
VAR CurrentRefDate = MAX(dim_date[date_key])
VAR ActiveLeases = 
    FILTER(
        fct_leases,
        fct_leases[lease_status] = "Active" &&
        fct_leases[lease_expiration_date] > CurrentRefDate
    )
VAR WeightedRemainingYears = 
    SUMX(
        ActiveLeases,
        fct_leases[leased_sqft] * 
        MAX(0, DATEDIFF(CurrentRefDate, fct_leases[lease_expiration_date], MONTH) / 12.0)
    )
VAR TotalActiveSqft = 
    SUMX(ActiveLeases, fct_leases[leased_sqft])
RETURN
    DIVIDE(WeightedRemainingYears, TotalActiveSqft, 0)
```
*Format: `0.00 "Years"`*

### Expiring RSF (Next 12 Months)
```dax
Expiring RSF (Next 12M) = 
VAR CurrentRefDate = MAX(dim_date[date_key])
VAR TargetDate = EDATE(CurrentRefDate, 12)
RETURN
    CALCULATE(
        SUM(fct_leases[leased_sqft]),
        fct_leases[lease_status] = "Active",
        fct_leases[lease_expiration_date] > CurrentRefDate,
        fct_leases[lease_expiration_date] <= TargetDate
    )
```
*Format: `#,##0`*

### Expiring Annual Revenue (Next 12 Months)
```dax
Expiring Revenue (Next 12M) = 
VAR CurrentRefDate = MAX(dim_date[date_key])
VAR TargetDate = EDATE(CurrentRefDate, 12)
RETURN
    CALCULATE(
        SUMX(fct_leases, fct_leases[leased_sqft] * fct_leases[base_rent_psf_year]),
        fct_leases[lease_status] = "Active",
        fct_leases[lease_expiration_date] > CurrentRefDate,
        fct_leases[lease_expiration_date] <= TargetDate
    )
```
*Format: `$#,##0`*

### 12-Month Lease Rollover Exposure (%)
```dax
12M Rollover Exposure % = 
DIVIDE(
    [Expiring RSF (Next 12M)],
    [Occupied RSF],
    0
)
```
*Format: `0.0%`*

---

## 4. Tenant Concentration & Risk Analytics

### Top 5 Tenant Revenue Concentration (%)
```dax
Top 5 Tenant Revenue % = 
VAR Top5Revenue = 
    SUMX(
        TOPN(
            5,
            VALUES(dim_tenants[tenant_name]),
            [Annual Contract Rent]
        ),
        [Annual Contract Rent]
    )
RETURN
    DIVIDE(Top5Revenue, [Total Annual Contract Rent], 0)
```
*Format: `0.0%`*

### Investment Grade Revenue (%)
```dax
Investment Grade Revenue % = 
VAR IGRevenue = 
    CALCULATE(
        [Total Annual Contract Rent],
        dim_tenants[credit_rating] IN {"AAA", "AA", "A", "BBB"}
    )
RETURN
    DIVIDE(IGRevenue, [Total Annual Contract Rent], 0)
```
*Format: `0.0%`*

### Mark-to-Market Rent Upside ($)
```dax
Mark-to-Market Rent Upside $ = 
SUMX(
    FILTER(fct_leases, fct_leases[lease_status] = "Active"),
    VAR MarketRent = 
        SWITCH(
            RELATED(dim_properties[asset_class]),
            "Office", IF(SEARCH("Class A", RELATED(dim_properties[property_subtype]), 1, 0) > 0, RELATED(dim_markets[avg_class_a_rent_psf]), RELATED(dim_markets[avg_class_b_rent_psf])),
            "Industrial", RELATED(dim_markets[avg_industrial_rent_psf]),
            "Retail", RELATED(dim_markets[avg_retail_rent_psf]),
            fct_leases[base_rent_psf_year]
        )
    RETURN
        fct_leases[leased_sqft] * (MarketRent - fct_leases[base_rent_psf_year])
)
```
*Format: `$#,##0`*
