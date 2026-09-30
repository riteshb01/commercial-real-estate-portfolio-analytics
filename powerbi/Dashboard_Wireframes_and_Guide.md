# Commercial Real Estate Portfolio — Executive Power BI Dashboard Specification

This document provides visual wireframes, layout grids, slicer hierarchies, and component configurations for the 4-page Commercial Real Estate Portfolio & Lease Risk Executive Dashboard.

---

## Page 1: Executive Portfolio Overview & Scorecard

**Target Audience:** Chief Investment Officer (CIO), Head of Asset Management, Portfolio Managers  
**Core Question Answered:** *How is our multi-asset Sunbelt commercial portfolio performing in revenue, occupancy, and NOI margins?*

### Layout Structure & Visual Hierarchy

```
+---------------------------------------------------------------------------------------------------+
|  [LOGO] COMMERCIAL REAL ESTATE PORTFOLIO PERFORMANCE & LEASE RISK DASHBOARD                       |
|  Filters: [Market: All] | [Asset Class: All] | [Year: 2025] | [Credit Rating: All]                |
+---------------------------------------------------------------------------------------------------+
|  [ CARD 1 ]          [ CARD 2 ]          [ CARD 3 ]          [ CARD 4 ]          [ CARD 5 ]       |
|  Total Portfolio RSF  Occupancy Rate %    2025 Annual NOI     NOI Margin %        Portfolio WALT  |
|  6,440,000 RSF        74.9% (+2.1% YoY)   $42.64M (+6.4% YoY) 44.7%               3.56 Years      |
+--------------------------------------------------+------------------------------------------------+
|  VISUAL 1: Cluster Bar Chart                     |  VISUAL 2: Area / Line Trend Chart             |
|  Total RSF vs Occupied RSF by Market             |  36-Month Gross Revenue vs NOI ($M)            |
|  - Austin: 1.55M RSF (83.8% Occ)                 |  - Jan 2023 -> Dec 2025                        |
|  - DFW: 2.12M RSF (71.9% Occ)                    |  - Shaded Area: Total OPEX                     |
|  - Atlanta: 1.63M RSF (76.8% Occ)                |  - Solid Line: Net Operating Income            |
|  - Charlotte: 1.14M RSF (64.8% Occ)              |                                                |
+--------------------------------------------------+------------------------------------------------+
|  VISUAL 3: Donut Chart                           |  VISUAL 4: Summary Matrix Table                |
|  Revenue by Asset Class                          |  Market x Asset Class Scorecard                |
|  - Industrial: $42.2M (44.3%)                    |  Columns: RSF | Occ % | Rev PSF | NOI | Margin |
|  - Office: $35.8M (37.5%)                        |  Includes Conditional Formatting Data Bars     |
|  - Retail: $17.3M (18.2%)                        |                                                |
+--------------------------------------------------+------------------------------------------------+
```

---

## Page 2: Property Financial Performance & NOI Deep Dive

**Target Audience:** Regional Asset Managers, Property Controllers  
**Core Question Answered:** *Which properties are outperforming/underperforming in NOI margin, and where are operational expense leaks?*

### Layout Structure

```
+---------------------------------------------------------------------------------------------------+
|  PROPERTY PERFORMANCE & EXPENSE BENCHMARKING DEEP DIVE                                            |
|  Filters: [Property Selector] | [Expense Category] | [Time Horizon: T12 / YTD]                    |
+--------------------------------------------------+------------------------------------------------+
|  VISUAL 1: Ranked Horizontal Bar Chart           |  VISUAL 2: Stacked Bar Chart                   |
|  Property NOI Margin % (Target: > 50%)           |  OPEX Decomposition ($/SF/Year)                |
|  Top: Austin Distribution Center (74.2%)         |  - CAM Charges                                 |
|  Lagging: Uptown Charlotte Office (21.4%)        |  - Property Taxes                              |
|  Includes benchmark target line                  |  - Insurance, Utilities, Mgmt Fees             |
+--------------------------------------------------+------------------------------------------------+
|  VISUAL 3: Interactive Property Performance Grid Table                                             |
|  Property Name | Market | Asset Class | Total RSF | Occ % | Rev PSF | OPEX PSF | NOI | Margin %   |
|  (Drill-through enabled to Page 3 & Page 4)                                                      |
+---------------------------------------------------------------------------------------------------+
```

---

## Page 3: Lease Rollover & Expiration Schedule

**Target Audience:** Director of Leasing, Asset Managers, Underwriting Teams  
**Core Question Answered:** *When do our major leases expire, what revenue is at risk, and what is our rollover exposure?*

### Layout Structure

```
+---------------------------------------------------------------------------------------------------+
|  LEASE ROLLOVER EXPOSURE & EXPIRATION TIMELINE                                                    |
|  Filters: [Rollover Horizon: 12M / 24M / 36M / All] | [Urgency Tier: Critical / Elevated]         |
+---------------------------------------------------------------------------------------------------+
|  [ CARD 1 ]                  [ CARD 2 ]                  [ CARD 3 ]             [ CARD 4 ]        |
|  Expiring RSF (Next 24M)     Expiring Revenue (24M)      24M Rollover Exposure  Portfolio WALT    |
|  1,482,000 RSF               $27.8M                      30.7% of Portfolio     3.56 Years        |
+--------------------------------------------------+------------------------------------------------+
|  VISUAL 1: Dual-Axis Bar & Line Chart            |  VISUAL 2: Scatter Plot                        |
|  Annual Expiration Schedule (2026 - 2033+)       |  WALT (Years) vs Occupancy % by Property       |
|  - Bars: Expiring Square Footage                 |  - Bubble Size: Total RSF                      |
|  - Line: Annual Revenue at Risk ($M)             |  - Quadrant: High Occ / Short WALT (Risk)      |
+--------------------------------------------------+------------------------------------------------+
|  VISUAL 3: Upcoming 24-Month Lease Expiration Alert Table                                         |
|  Tenant Name | Property | Suite | Leased SF | Base Rent PSF | Annual Rent | Exp Date | Priority  |
+---------------------------------------------------------------------------------------------------+
```

---

## Page 4: Tenant Credit & Concentration Risk

**Target Audience:** Risk Committee, Chief Financial Officer, Underwriting  
**Core Question Answered:** *Are we overly exposed to single tenants, speculative credit ratings, or volatile industry sectors?*

### Layout Structure

```
+---------------------------------------------------------------------------------------------------+
|  TENANT CONCENTRATION & CREDIT EXPOSURE ANALYSIS                                                  |
|  Filters: [Credit Rating: IG / Speculative / NR] | [Industry Sector] | [Public vs Private]       |
+---------------------------------------------------------------------------------------------------+
|  [ CARD 1 ]                  [ CARD 2 ]                  [ CARD 3 ]             [ CARD 4 ]        |
|  Top 10 Tenant Rev %         Investment Grade Rev %      HHI Score              Unique Tenants    |
|  38.2% of Portfolio          61.4% of Portfolio          195.2 (Diversified)    99 Companies      |
+--------------------------------------------------+------------------------------------------------+
|  VISUAL 1: Treemap                               |  VISUAL 2: Donut Chart                         |
|  Tenant Revenue Concentration                    |  Credit Rating Breakdown                       |
|  - Sized by: Annual Contract Rent                |  - Investment Grade (AAA - BBB): 61.4%         |
|  - Colored by: Credit Quality Tier               |  - Speculative Grade (BB - B): 24.1%           |
|                                                  |  - Non-Rated (NR): 14.5%                       |
+--------------------------------------------------+------------------------------------------------+
|  VISUAL 3: Mark-to-Market Rent Variance Gap ($/SF by Asset Class & Market)                        |
|  In-Place Contract Rent vs Market Asking Rate: Identifies Loss-to-Lease Upside on Renewal         |
+---------------------------------------------------------------------------------------------------+
```
