#!/usr/bin/env python3
"""
Commercial Real Estate Portfolio Data Generator
================================================

Generates synthetic but realistic institutional-quality CRE portfolio data
for a multi-property investment portfolio across 4 Sunbelt markets.

Portfolio Profile:
    - 25 institutional-grade properties (Industrial, Office, Retail)
    - 4 markets:  Austin TX, Dallas-Fort Worth TX, Atlanta GA, Charlotte NC
    - ~100 tenants across 7 industry sectors
    - ~170 leases with structured expiration profiles
    - 36 months of monthly property-level financials (Jan 2023 – Dec 2025)

Deliberate Analytical Signals (designed for discovery):
    1. Two underperforming office properties (IDs 2, 17) with rising vacancy
    2. One property (ID 14) with abnormal utility cost spike in Q3 2024
    3. A lease-expiration cliff concentrated in 2026-2027 (~35 % of portfolio RSF)

Outputs:
    - data/raw/*.csv   — CSV files for each table
    - sql/02_seed_data.sql — PostgreSQL INSERT statements

Usage:
    python python/generate_cre_data.py

Author: Ritesh Bastola
"""

import os
import sys
import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


# =====================================================================
# CONFIGURATION
# =====================================================================

RANDOM_SEED = 42
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw"
SQL_OUTPUT = PROJECT_ROOT / "sql" / "02_seed_data.sql"

ANALYSIS_START = date(2023, 1, 1)
ANALYSIS_END = date(2025, 12, 31)

# Properties with deliberate analytical anomalies
UNDERPERFORMING_IDS = {2, 17}   # High vacancy / declining occupancy
OPEX_ANOMALY_ID = 14            # Utility cost spike in Q3 2024

np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)


# =====================================================================
# 1.  MARKETS  (4 Sunbelt Metros)
# =====================================================================

def generate_markets() -> pd.DataFrame:
    """
    Generate market-level benchmark data for 4 high-growth Sunbelt CRE markets.

    Benchmarks represent 2023 mid-year asking rents ($/SF/year) and prevailing
    vacancy and cap rates sourced from CoStar / CBRE market reports.
    """
    data = [
        # market_id, metro, state, submarket, A_rent, B_rent, ind_rent, ret_rent, vacancy%, cap%
        (1, "Austin",           "TX", "Austin-Round Rock MSA",             42.50, 32.00, 8.75, 28.00, 12.5, 5.8),
        (2, "Dallas-Fort Worth","TX", "DFW Metroplex",                     38.00, 28.50, 7.50, 24.00, 10.8, 6.2),
        (3, "Atlanta",          "GA", "Atlanta Metro",                     36.00, 26.00, 7.00, 22.50, 11.2, 6.5),
        (4, "Charlotte",        "NC", "Charlotte-Concord-Gastonia MSA",    34.00, 25.00, 6.80, 21.00,  9.8, 6.0),
    ]
    columns = [
        "market_id", "metro_area", "state", "submarket",
        "avg_class_a_rent_psf", "avg_class_b_rent_psf",
        "avg_industrial_rent_psf", "avg_retail_rent_psf",
        "market_vacancy_rate", "market_cap_rate",
    ]
    return pd.DataFrame(data, columns=columns)


# =====================================================================
# 2.  PROPERTIES  (25 Institutional-Grade Assets)
# =====================================================================

def generate_properties() -> pd.DataFrame:
    """
    Generate 25 commercial properties across Office, Industrial, and Retail
    asset classes distributed across 4 Sunbelt markets.

    Mix:  11 Industrial  |  8 Office (Class A/B)  |  6 Retail
    """
    properties = [
        # ── Austin, TX  (7 properties) ──────────────────────────────────
        ( 1, "Austin Tech Center",           1, "Office",     "Class A Office",       220_000, 2018, "2021-03-15", 85_000_000, 12, 880,  "300 West 6th Street, Austin, TX 78701"),
        ( 2, "Lakeline Office Park",         1, "Office",     "Class B Office",       140_000, 2005, "2020-07-01", 38_000_000,  4, 560,  "14000 N US-183, Austin, TX 78717"),
        ( 3, "Round Rock Distribution Hub",  1, "Industrial", "Distribution Center",  450_000, 2019, "2021-01-10", 52_000_000,  1, 200,  "2500 S AW Grimes Blvd, Round Rock, TX 78664"),
        ( 4, "Pflugerville Logistics Center", 1, "Industrial","Logistics Facility",   350_000, 2020, "2022-04-15", 42_000_000,  1, 180,  "19000 Pflugerville Pkwy, Pflugerville, TX 78660"),
        ( 5, "Domain Retail Center",         1, "Retail",     "Neighborhood Center",   85_000, 2015, "2020-11-01", 22_000_000,  1, 340,  "11600 Domain Dr, Austin, TX 78758"),
        ( 6, "Cedar Park Commerce Center",   1, "Industrial", "Flex Industrial",      280_000, 2017, "2021-06-01", 32_000_000,  1, 140,  "1400 E Whitestone Blvd, Cedar Park, TX 78613"),
        ( 7, "South Congress Office",        1, "Office",     "Class A Office",       180_000, 2021, "2022-09-01", 72_000_000,  8, 720,  "1200 S Congress Ave, Austin, TX 78704"),

        # ── Dallas-Fort Worth, TX  (7 properties) ──────────────────────
        ( 8, "Alliance Gateway Industrial",  2, "Industrial", "Distribution Center",  550_000, 2016, "2020-02-01", 58_000_000,  1, 250,  "2200 Alliance Gateway Fwy, Fort Worth, TX 76177"),
        ( 9, "DFW Logistics Park West",      2, "Industrial", "Logistics Facility",   420_000, 2018, "2021-05-15", 48_000_000,  1, 200,  "4500 W Airfield Dr, Dallas, TX 75261"),
        (10, "Irving Corporate Center",      2, "Office",     "Class A Office",       200_000, 2014, "2020-09-01", 62_000_000, 10, 800,  "6000 N O'Connor Blvd, Irving, TX 75039"),
        (11, "Plano Crossing Retail",        2, "Retail",     "Power Center",         110_000, 2010, "2019-12-01", 28_000_000,  1, 500,  "8600 Preston Rd, Plano, TX 75024"),
        (12, "Frisco Tech Office",           2, "Office",     "Class B Office",       160_000, 2012, "2021-03-01", 40_000_000,  5, 640,  "5900 S Main St, Frisco, TX 75034"),
        (13, "Mesquite Distribution Center", 2, "Industrial", "Distribution Center",  380_000, 2019, "2022-01-15", 40_000_000,  1, 180,  "3200 Hwy 80, Mesquite, TX 75150"),
        (14, "Richardson Business Park",     2, "Office",     "Class B Office",       120_000, 2008, "2020-06-01", 28_000_000,  3, 480,  "1200 E Campbell Rd, Richardson, TX 75081"),

        # ── Atlanta, GA  (6 properties) ────────────────────────────────
        (15, "Hartsfield Logistics Hub",     3, "Industrial", "Logistics Facility",   600_000, 2020, "2022-03-01", 65_000_000,  1, 300,  "4800 S Fulton Industrial Blvd, Atlanta, GA 30336"),
        (16, "Peachtree Corporate Tower",    3, "Office",     "Class A Office",       250_000, 2017, "2021-08-01", 78_000_000, 15, 1000, "3500 Peachtree Rd NE, Atlanta, GA 30326"),
        (17, "Alpharetta Business Center",   3, "Office",     "Class B Office",       130_000, 2009, "2020-04-01", 30_000_000,  4, 520,  "5500 Windward Pkwy, Alpharetta, GA 30004"),
        (18, "Buckhead Retail Plaza",        3, "Retail",     "Grocery-Anchored",      95_000, 2013, "2020-10-01", 24_000_000,  1, 380,  "3200 Peachtree Rd NE, Atlanta, GA 30305"),
        (19, "McDonough Distribution Center",3, "Industrial", "Distribution Center",  480_000, 2021, "2022-06-01", 55_000_000,  1, 220,  "100 Industrial Park Dr, McDonough, GA 30253"),
        (20, "Marietta Town Center",         3, "Retail",     "Neighborhood Center",   75_000, 2011, "2019-08-01", 16_000_000,  1, 300,  "200 Cobb Pkwy SE, Marietta, GA 30060"),

        # ── Charlotte, NC  (5 properties) ──────────────────────────────
        (21, "Mooresville Industrial Park",  4, "Industrial", "Flex Industrial",      400_000, 2018, "2021-11-01", 42_000_000,  1, 190,  "500 Gateway Blvd, Mooresville, NC 28117"),
        (22, "Uptown Charlotte Office",      4, "Office",     "Class A Office",       190_000, 2019, "2022-02-01", 68_000_000, 11, 760,  "301 S Tryon St, Charlotte, NC 28202"),
        (23, "Concord Logistics Center",     4, "Industrial", "Logistics Facility",   320_000, 2020, "2022-07-01", 36_000_000,  1, 160,  "7500 Bruton Smith Blvd, Concord, NC 28027"),
        (24, "SouthPark Retail Center",      4, "Retail",     "Power Center",         105_000, 2012, "2020-05-01", 26_000_000,  1, 450,  "4400 Sharon Rd, Charlotte, NC 28211"),
        (25, "University Research Park",     4, "Office",     "Class B Office",       150_000, 2010, "2020-01-01", 32_000_000,  4, 600,  "9000 J.M. Keynes Dr, Charlotte, NC 28262"),
    ]
    columns = [
        "property_id", "property_name", "market_id", "asset_class", "property_subtype",
        "total_rsf", "year_built", "acquisition_date", "acquisition_price",
        "number_of_floors", "parking_spaces", "address",
    ]
    return pd.DataFrame(properties, columns=columns)


# =====================================================================
# 3.  TENANTS  (~99 Commercial Tenants)
# =====================================================================

# Realistic CRE tenant names by industry sector
TENANT_POOL = {
    "Technology": [
        "Vertex Software", "Quantum Data Systems", "NovaTech Solutions",
        "Pinnacle Cloud Services", "Horizon AI Labs", "Summit Digital",
        "Cipher Technologies", "Nexus Platforms", "Forge Analytics",
        "Pulse Networks", "Synapse Computing", "Atlas Tech Group",
        "Prism Software", "Vortex Systems", "Meridian Digital",
        "Catalyst Innovation", "Arcadia Tech", "Stratos Computing",
        "Cobalt Data", "Zephyr Software",
    ],
    "Financial Services": [
        "Meridian Capital Group", "Sterling Financial Advisors",
        "Apex Insurance Holdings", "Granite Investment Partners",
        "Ironclad Wealth Management", "Crestview Capital",
        "Patriot National Insurance", "Cornerstone Financial",
        "Summit Ridge Advisors", "Vanguard Credit Solutions",
        "Pacific Trust Financial", "Silverline Asset Management",
        "Harbor Point Capital", "Eagle Rock Financial",
        "Ridgeline Banking Group",
    ],
    "Healthcare": [
        "Vitality Health Systems", "Precision Medical Group",
        "CarePoint Health Services", "Meridian Diagnostics",
        "Summit Health Partners", "Beacon Wellness Center",
        "ProMed Clinical Research", "Heritage Health Network",
        "Ascend Medical Associates", "BlueStar Health",
        "Clearview Imaging", "Pinnacle Dental Group",
    ],
    "Logistics & Distribution": [
        "SwiftLine Logistics", "Continental Supply Chain",
        "Apex Freight Solutions", "Ironbridge Logistics",
        "Pacific Coast Shipping", "Evergreen Distribution",
        "Trident Fulfillment", "Atlas Global Logistics",
        "Velocity Cargo", "Redstone Supply Co",
        "Bridgepoint Logistics", "Falcon Transport",
        "Sterling Freight", "Compass Distribution",
        "Keystone Shipping",
    ],
    "Professional Services": [
        "Baker & Associates Consulting", "Whitfield Legal Group",
        "Cornerstone Advisory", "Blackwood Strategy",
        "Pinnacle HR Solutions", "Delaney & Partners LLP",
        "Summit Accounting Group", "Crestwood Legal",
        "Archer Consulting", "Ridgemont Strategy Group",
        "Benchmark Advisory", "Sterling Partners Consulting",
        "Graystone Legal", "Ironwood Consulting",
        "Evergreen Professional Services",
    ],
    "Retail & Consumer": [
        "FreshMart Grocers", "Urban Living Home",
        "Bright Home Furnishings", "The Daily Grind Coffee",
        "Sunrise Fitness", "GreenLeaf Organics",
        "BlueWave Salon & Spa", "Mountain Trail Outfitters",
        "CityBrew Coffee", "The Pet Corner",
        "Golden Harvest Restaurant", "Luxe Nails Studio",
    ],
    "Manufacturing": [
        "Atlas Manufacturing Co", "Steelworks Industrial",
        "Precision Components Inc", "Ironforge Fabrication",
        "Duratech Manufacturing", "Patriot Steel Products",
        "Cascade Materials", "Summit Machining",
        "Bridgeport Manufacturing", "Keystone Metals",
    ],
}

# Credit quality distribution by industry (realistic CRE underwriting)
_CREDIT_WEIGHTS = {
    "Technology":              (["A", "BBB", "BB", "A", "BBB"], ["National", "National", "Regional", "Regional", "Local"]),
    "Financial Services":      (["AA", "A", "A", "BBB", "AA"],  ["National", "National", "Regional", "Regional", "Local"]),
    "Healthcare":              (["A", "BBB", "A", "BBB", "BB"], ["Regional", "Regional", "National", "Local", "Local"]),
    "Logistics & Distribution":(["BBB", "BB", "A", "BBB", "BB"],["National", "National", "Regional", "National", "Regional"]),
    "Professional Services":   (["A", "BBB", "BBB", "A", "BB"],["Regional", "National", "Local", "Regional", "Local"]),
    "Retail & Consumer":       (["BBB", "BB", "B", "BBB", "BB"],["National", "Regional", "Local", "Local", "Local"]),
    "Manufacturing":           (["BBB", "BB", "A", "BBB", "B"], ["National", "Regional", "Regional", "National", "Local"]),
}


def generate_tenants() -> pd.DataFrame:
    """
    Generate ~99 commercial tenants spanning 7 industry sectors.

    Each tenant receives:
      - Credit rating (investment-grade ≥ BBB, speculative < BBB)
      - Operating scale (National / Regional / Local)
      - Public company flag
    """
    tenants = []
    tenant_id = 1

    for industry, names in TENANT_POOL.items():
        credits, types = _CREDIT_WEIGHTS[industry]
        for name in names:
            cr = random.choice(credits)
            tt = random.choice(types)
            is_public = random.random() < (
                0.40 if tt == "National" else 0.15 if tt == "Regional" else 0.05
            )
            tenants.append({
                "tenant_id": tenant_id,
                "tenant_name": name,
                "industry": industry,
                "credit_rating": cr,
                "tenant_type": tt,
                "public_company": is_public,
            })
            tenant_id += 1

    return pd.DataFrame(tenants)


# =====================================================================
# 4.  LEASES  (~170 Multi-Year Commercial Leases)
# =====================================================================

# Map asset class → preferred tenant industries
_INDUSTRY_AFFINITY = {
    "Office":     ["Technology", "Financial Services", "Healthcare", "Professional Services"],
    "Industrial": ["Logistics & Distribution", "Manufacturing", "Technology"],
    "Retail":     ["Retail & Consumer", "Healthcare", "Financial Services", "Professional Services"],
}

# Lease vintage → rent adjustment factor (earlier = lower market rent at signing)
_VINTAGE_FACTORS = {
    2015: 0.78, 2016: 0.80, 2017: 0.83, 2018: 0.85, 2019: 0.88,
    2020: 0.90, 2021: 0.93, 2022: 0.97, 2023: 1.00, 2024: 1.03,
}


def _get_benchmark_rent(market_row, asset_class: str, subtype: str) -> float:
    """Look up the appropriate market benchmark rent for a property."""
    if asset_class == "Office":
        if "Class A" in subtype:
            return market_row["avg_class_a_rent_psf"]
        return market_row["avg_class_b_rent_psf"]
    elif asset_class == "Industrial":
        return market_row["avg_industrial_rent_psf"]
    else:
        return market_row["avg_retail_rent_psf"]


def _get_lease_type(asset_class: str, subtype: str) -> str:
    """Determine lease structure based on asset class."""
    if asset_class == "Industrial":
        return "NNN"
    elif asset_class == "Office":
        return "Full Service Gross" if "Class A" in subtype else "Modified Gross"
    else:
        return "Percentage" if "Grocery" in subtype else "NNN"


def _generate_suite_number(asset_class: str, index: int) -> str:
    """Generate a realistic suite/bay identifier."""
    if asset_class == "Industrial":
        return f"Bay {chr(65 + index)}"        # Bay A, Bay B, ...
    elif asset_class == "Office":
        floor = (index // 3) + 2               # Start floor 2
        unit = (index % 3) + 1
        return f"Suite {floor * 100 + unit}"    # Suite 201, 202, ...
    else:
        return f"Suite {chr(65 + index)}"       # Suite A, Suite B, ...


def generate_leases(
    properties_df: pd.DataFrame,
    tenants_df: pd.DataFrame,
    markets_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Generate ~170 commercial leases with structured expiration profiles.

    Expiration Distribution:
        ~15 % expire in 2025 (some mid-period)
        ~35 % expire in 2026–2027  →  LEASE EXPIRATION CLIFF
        ~30 % expire in 2028–2030
        ~20 % expire in 2031+

    Underperforming properties (IDs 2, 17) have 2 tenants whose leases
    expire in mid-2024 and are NOT renewed, causing occupancy decline.
    """
    leases = []
    lease_id = 1

    # Build tenant pools by asset-class affinity
    tenant_pools = {}
    for asset_class, industries in _INDUSTRY_AFFINITY.items():
        pool = tenants_df[tenants_df.industry.isin(industries)].tenant_id.tolist()
        tenant_pools[asset_class] = pool

    # Track global tenant assignments (prefer unique, allow multi-property for nationals)
    assigned_global = set()

    for _, prop in properties_df.iterrows():
        pid          = prop["property_id"]
        asset_class  = prop["asset_class"]
        subtype      = prop["property_subtype"]
        total_rsf    = prop["total_rsf"]
        market_id    = prop["market_id"]

        market = markets_df[markets_df.market_id == market_id].iloc[0]
        benchmark_rent = _get_benchmark_rent(market, asset_class, subtype)
        lease_type = _get_lease_type(asset_class, subtype)

        # Number of tenants (realistic by asset class)
        if asset_class == "Industrial":
            num_leases = np.random.randint(2, 6)
        elif asset_class == "Office":
            num_leases = np.random.randint(5, 13)
        else:
            num_leases = np.random.randint(4, 9)

        # Target occupancy at portfolio inception
        target_occ = np.random.uniform(0.89, 0.96)
        target_sqft = int(total_rsf * target_occ)

        # Select tenants (prefer unassigned; allow national reuse)
        pool = tenant_pools[asset_class]
        unassigned = [t for t in pool if t not in assigned_global]
        if len(unassigned) < num_leases:
            unassigned = pool.copy()

        selected = random.sample(unassigned, min(num_leases, len(unassigned)))
        assigned_global.update(selected)

        # Distribute square footage using Dirichlet (natural variation)
        alpha = 2.0 if asset_class == "Industrial" else 1.5 if asset_class == "Retail" else 1.0
        if len(selected) > 1:
            portions = np.random.dirichlet(np.ones(len(selected)) * alpha) * target_sqft
            sqft_list = [max(int(s), 1500) for s in portions]
        else:
            sqft_list = [target_sqft]

        # Cap at total RSF
        total_assigned = sum(sqft_list)
        if total_assigned > total_rsf:
            scale = (total_rsf * 0.95) / total_assigned
            sqft_list = [max(int(s * scale), 1000) for s in sqft_list]

        # Generate individual leases
        for i, tenant_id in enumerate(selected):
            sqft = sqft_list[i]

            # ── Expiration bucket assignment ──
            is_underperformer_departure = (
                pid in UNDERPERFORMING_IDS and i >= len(selected) - 2
            )

            if is_underperformer_departure:
                # These tenants leave mid-analysis → occupancy decline signal
                exp_year = 2024
                exp_month = random.choice([3, 4, 5, 6, 7, 8, 9])
            else:
                r = random.random()
                if r < 0.15:
                    # 15 %: expire during 2025
                    exp_year = 2025
                    exp_month = random.randint(1, 12)
                elif r < 0.50:
                    # 35 %: CLIFF — expire 2026-2027
                    exp_year = random.choice([2026, 2026, 2027, 2027])
                    exp_month = random.randint(1, 12)
                elif r < 0.80:
                    # 30 %: expire 2028-2030
                    exp_year = random.choice([2028, 2029, 2030])
                    exp_month = random.randint(1, 12)
                else:
                    # 20 %: long-duration, 2031+
                    exp_year = random.choice([2031, 2032, 2033, 2034])
                    exp_month = random.randint(1, 12)

            # Clamp expiration month
            exp_month = min(exp_month, 12)
            exp_date = date(exp_year, exp_month, 1) - timedelta(days=1)

            # Lease term length (work backward from expiration)
            # Ensure lease starts BEFORE the analysis window so it generates
            # revenue during 2023-2025.  Minimum start: no later than 2023.
            if asset_class == "Industrial":
                min_term = max(7, exp_year - 2022)   # Must start ≤ 2022
                term_years = random.randint(min_term, max(min_term, 12))
            elif asset_class == "Office":
                min_term = max(3, exp_year - 2022)
                term_years = random.randint(min_term, max(min_term, 7))
            else:
                min_term = max(5, exp_year - 2022)
                term_years = random.randint(min_term, max(min_term, 10))

            start_year = max(exp_year - term_years, 2015)
            # Safety clamp: lease must start no later than Jan 2023
            start_year = min(start_year, 2023)
            start_month = min(exp_month, 12)
            start_date = date(start_year, start_month, 1)

            # Rent pricing: market benchmark × vintage factor × property noise
            vintage_key = max(min(start_year, 2024), 2015)
            vf = _VINTAGE_FACTORS.get(vintage_key, 0.85)
            noise = np.random.uniform(0.88, 1.14)
            base_rent = round(benchmark_rent * vf * noise, 2)

            # Annual escalation (industry standard: 2–3.5 %)
            escalation = round(np.random.uniform(2.0, 3.5), 2)

            # Lease status (snapshot as of analysis end date)
            if exp_date < ANALYSIS_END:
                status = "Expired"
            else:
                status = "Active"

            # Tenant concessions
            if start_year >= 2022:
                if asset_class == "Office":
                    ti = round(np.random.uniform(30, 65), 2)
                    free_months = random.choice([0, 2, 3, 4, 6])
                elif asset_class == "Retail":
                    ti = round(np.random.uniform(15, 35), 2)
                    free_months = random.choice([0, 1, 2, 3])
                else:
                    ti = round(np.random.uniform(5, 15), 2)
                    free_months = random.choice([0, 0, 1, 2])
            else:
                ti = round(np.random.uniform(8, 25), 2)
                free_months = random.choice([0, 0, 1, 2])

            leases.append({
                "lease_id":              lease_id,
                "property_id":           pid,
                "tenant_id":             tenant_id,
                "suite_number":          _generate_suite_number(asset_class, i),
                "leased_sqft":           sqft,
                "lease_start_date":      start_date.isoformat(),
                "lease_expiration_date": exp_date.isoformat(),
                "base_rent_psf_year":    base_rent,
                "annual_escalation_pct": escalation,
                "lease_type":            lease_type,
                "lease_status":          status,
                "free_rent_months":      free_months,
                "tenant_improvement_psf": ti,
            })
            lease_id += 1

    return pd.DataFrame(leases)


# =====================================================================
# 5.  PROPERTY MONTHLY FINANCIALS  (36 months × 25 properties = 900 rows)
# =====================================================================

def _precompute_opex_params(properties_df: pd.DataFrame) -> dict:
    """
    Pre-compute stable annual OPEX cost parameters per property.

    OPEX rates are fixed per property and only vary ±3 % month-to-month
    to simulate realistic cost consistency with minor operational noise.
    """
    params = {}

    for _, prop in properties_df.iterrows():
        pid = prop["property_id"]
        ac  = prop["asset_class"]
        age = 2025 - prop["year_built"]
        age_factor = 1.0 + (age / 50)   # Older buildings → slightly higher R&M

        if ac == "Industrial":
            cam  = np.random.uniform(0.80, 1.40)    # NNN — low landlord CAM
            util = np.random.uniform(0.50, 1.00)    # Minimal landlord utility
            ins  = np.random.uniform(0.30, 0.55)
            rm   = np.random.uniform(0.40, 0.80) * age_factor
            tax_psf = np.random.uniform(2.00, 3.50) # $/SF/year property taxes
        elif ac == "Office":
            cam  = np.random.uniform(2.00, 3.50)    # Full-service = higher CAM
            util = np.random.uniform(1.80, 2.80)    # HVAC-intensive
            ins  = np.random.uniform(0.40, 0.70)
            rm   = np.random.uniform(0.80, 1.50) * age_factor
            tax_psf = np.random.uniform(4.00, 6.50)
        else:  # Retail
            cam  = np.random.uniform(1.50, 2.80)
            util = np.random.uniform(1.20, 2.00)
            ins  = np.random.uniform(0.35, 0.60)
            rm   = np.random.uniform(0.60, 1.20) * age_factor
            tax_psf = np.random.uniform(3.00, 5.00)

        mgmt_rate = np.random.uniform(0.030, 0.045)   # % of gross revenue

        params[pid] = {
            "cam_psf":    cam,
            "util_psf":   util,
            "ins_psf":    ins,
            "rm_psf":     rm,
            "tax_psf":    tax_psf,
            "mgmt_rate":  mgmt_rate,
            "total_rsf":  prop["total_rsf"],
            "asset_class": ac,
        }

    return params


def generate_monthly_financials(
    properties_df: pd.DataFrame,
    leases_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Generate 36 months (Jan 2023 – Dec 2025) of property-level financials.

    Revenue is derived from active leases with annual rent escalations.
    OPEX components include CAM, property taxes, insurance, utilities,
    repairs & maintenance, and property management fees.

    Anomaly: Property 14 (Richardson Business Park) has a utility cost
    spike in Jul–Sep 2024 (2.8–3.5× normal) simulating HVAC failure.
    """
    records = []
    record_id = 1

    months = pd.date_range(ANALYSIS_START, ANALYSIS_END, freq="MS")
    opex_params = _precompute_opex_params(properties_df)

    # Prepare lease date columns for vectorized filtering
    leases = leases_df.copy()
    leases["_start"] = pd.to_datetime(leases["lease_start_date"]).dt.date
    leases["_end"]   = pd.to_datetime(leases["lease_expiration_date"]).dt.date

    for _, prop in properties_df.iterrows():
        pid = prop["property_id"]
        p   = opex_params[pid]
        rsf = p["total_rsf"]

        prop_leases = leases[leases.property_id == pid]

        for month_ts in months:
            month_dt = month_ts.date()
            month_num = month_dt.month

            # ── Active leases this month ──
            active = prop_leases[
                (prop_leases["_start"] <= month_dt) &
                (prop_leases["_end"]   >= month_dt)
            ]

            # ── Revenue calculation ──
            total_rent = 0.0
            for _, lease in active.iterrows():
                years_elapsed = (
                    (month_dt.year - lease["_start"].year)
                    + (month_dt.month - lease["_start"].month) / 12
                )
                months_elapsed = int(years_elapsed * 12)

                # Skip free-rent concession months
                if months_elapsed < lease["free_rent_months"]:
                    continue

                # Annual step-up escalation
                full_years = int(years_elapsed)
                escalated = lease["base_rent_psf_year"] * (
                    1 + lease["annual_escalation_pct"] / 100
                ) ** full_years
                monthly_rent = (lease["leased_sqft"] * escalated) / 12
                total_rent += monthly_rent

            # Other income (parking, storage, late fees — 2–5 % of rent)
            other_income = total_rent * np.random.uniform(0.02, 0.05)

            # ── OPEX calculations ──
            noise = lambda: np.random.uniform(0.97, 1.03)

            cam       = (rsf * p["cam_psf"]  * noise()) / 12
            prop_tax  = (rsf * p["tax_psf"]) / 12    # Stable (assessed per SF)
            insurance = (rsf * p["ins_psf"]  * noise()) / 12

            # Utilities — seasonal variation
            if p["asset_class"] in ("Office", "Retail"):
                if month_num in (6, 7, 8):        # Summer peak (cooling)
                    season = np.random.uniform(1.15, 1.30)
                elif month_num in (12, 1, 2):     # Winter bump (heating)
                    season = np.random.uniform(1.05, 1.15)
                else:                             # Shoulder months
                    season = np.random.uniform(0.85, 1.00)
            else:  # Industrial — minimal seasonal swing
                season = np.random.uniform(0.95, 1.05)

            util_base = (rsf * p["util_psf"] * noise()) / 12

            # ── OPEX ANOMALY: Richardson Business Park Q3 2024 ──
            if pid == OPEX_ANOMALY_ID and month_dt.year == 2024 and month_num in (7, 8, 9):
                season *= np.random.uniform(2.8, 3.5)

            utilities = util_base * season
            repairs   = (rsf * p["rm_psf"] * noise()) / 12
            mgmt_fees = (total_rent + other_income) * p["mgmt_rate"]

            records.append({
                "record_id":            record_id,
                "property_id":          pid,
                "period_date":          month_dt.isoformat(),
                "gross_rental_revenue": round(total_rent, 2),
                "other_income":         round(other_income, 2),
                "cam_charges":          round(cam, 2),
                "property_taxes":       round(prop_tax, 2),
                "insurance":            round(insurance, 2),
                "utilities":            round(utilities, 2),
                "repairs_maintenance":  round(repairs, 2),
                "management_fees":      round(mgmt_fees, 2),
            })
            record_id += 1

    return pd.DataFrame(records)


# =====================================================================
# 6.  SQL INSERT GENERATION
# =====================================================================

def _sql_literal(value) -> str:
    """Convert a Python value to a PostgreSQL literal."""
    if pd.isna(value):
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float, np.integer, np.floating)):
        return str(value)
    # String — escape single quotes
    return "'" + str(value).replace("'", "''") + "'"


def generate_sql_inserts(dfs: dict, output_path: Path) -> None:
    """
    Generate a PostgreSQL-compatible SQL file with INSERT statements
    for all dimension and fact tables.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Table name mapping (DataFrame key → SQL table)
    table_map = [
        ("markets",                     "dim_markets"),
        ("tenants",                     "dim_tenants"),
        ("properties",                  "dim_properties"),
        ("leases",                      "fct_leases"),
        ("property_monthly_financials", "fct_property_monthly_financials"),
    ]

    with open(output_path, "w") as f:
        f.write("-- ============================================================\n")
        f.write("-- CRE Portfolio Analytics — Seed Data\n")
        f.write("-- Auto-generated by python/generate_cre_data.py\n")
        f.write("-- ============================================================\n\n")
        f.write("SET search_path TO cre_analytics, public;\n\n")
        f.write("BEGIN;\n\n")

        for df_key, table_name in table_map:
            df = dfs[df_key]
            # Skip internal columns (prefixed with _)
            cols = [c for c in df.columns if not c.startswith("_")]

            f.write(f"-- {table_name} ({len(df)} rows)\n")
            for _, row in df.iterrows():
                col_str = ", ".join(cols)
                val_str = ", ".join(_sql_literal(row[c]) for c in cols)
                f.write(f"INSERT INTO {table_name} ({col_str}) VALUES ({val_str});\n")
            f.write("\n")

        # Reset sequences after bulk insert
        f.write("-- Reset sequences to max(id) + 1\n")
        seq_resets = [
            ("dim_markets",  "market_id",  "dim_markets_market_id_seq"),
            ("dim_tenants",  "tenant_id",  "dim_tenants_tenant_id_seq"),
            ("dim_properties","property_id","dim_properties_property_id_seq"),
            ("fct_leases",   "lease_id",   "fct_leases_lease_id_seq"),
            ("fct_property_monthly_financials", "record_id",
             "fct_property_monthly_financials_record_id_seq"),
        ]
        for table, col, seq in seq_resets:
            f.write(
                f"SELECT setval('{seq}', COALESCE((SELECT MAX({col}) FROM {table}), 0) + 1, false);\n"
            )

        f.write("\nCOMMIT;\n")

    print(f"  → SQL inserts written to {output_path}")


# =====================================================================
# 7.  CSV EXPORT
# =====================================================================

def export_csvs(dfs: dict, output_dir: Path) -> None:
    """Export all DataFrames to CSV files in the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, df in dfs.items():
        # Drop internal columns
        export_df = df[[c for c in df.columns if not c.startswith("_")]]
        path = output_dir / f"{name}.csv"
        export_df.to_csv(path, index=False)
        print(f"  → {path.name:40s}  {len(df):>6,} rows")


# =====================================================================
# 8.  SUMMARY STATISTICS
# =====================================================================

def print_summary(dfs: dict, properties_df: pd.DataFrame, leases_df: pd.DataFrame) -> None:
    """Print a portfolio summary to verify data quality."""
    markets    = dfs["markets"]
    tenants    = dfs["tenants"]
    leases     = dfs["leases"]
    financials = dfs["property_monthly_financials"]

    print("\n" + "=" * 60)
    print("PORTFOLIO SUMMARY")
    print("=" * 60)

    print(f"\n  Markets:       {len(markets)}")
    print(f"  Properties:    {len(properties_df)}")
    print(f"  Tenants:       {len(tenants)}")
    print(f"  Leases:        {len(leases)}")
    print(f"  Monthly Fin:   {len(financials)} rows ({len(financials) // 25} months × 25 properties)")

    # Asset class breakdown
    print("\n  Properties by Asset Class:")
    for ac, count in properties_df.asset_class.value_counts().items():
        rsf = properties_df[properties_df.asset_class == ac].total_rsf.sum()
        print(f"    {ac:12s}  {count:>2} properties   {rsf:>12,} RSF")

    # Market breakdown
    print("\n  Properties by Market:")
    for mid in sorted(properties_df.market_id.unique()):
        mkt = markets[markets.market_id == mid].iloc[0]
        count = len(properties_df[properties_df.market_id == mid])
        print(f"    {mkt.metro_area:20s}  {count:>2} properties")

    # Lease status
    print("\n  Lease Status:")
    for status, count in leases.lease_status.value_counts().items():
        sqft = leases[leases.lease_status == status].leased_sqft.sum()
        print(f"    {status:10s}  {count:>3} leases   {sqft:>12,} SF")

    # Expiration distribution
    leases_copy = leases.copy()
    leases_copy["exp_year"] = pd.to_datetime(leases_copy["lease_expiration_date"]).dt.year
    print("\n  Lease Expiration Schedule:")
    for year in sorted(leases_copy.exp_year.unique()):
        yr_leases = leases_copy[leases_copy.exp_year == year]
        count = len(yr_leases)
        sqft = yr_leases.leased_sqft.sum()
        pct = sqft / leases.leased_sqft.sum() * 100
        bar = "█" * int(pct / 2)
        print(f"    {year}:  {count:>3} leases   {sqft:>10,} SF   ({pct:5.1f}%)  {bar}")

    # Portfolio-level financials snapshot (latest 12 months)
    fin = financials.copy()
    fin["period_date"] = pd.to_datetime(fin["period_date"])
    last_12 = fin[fin.period_date >= "2025-01-01"]
    total_rev = last_12["gross_rental_revenue"].sum() + last_12["other_income"].sum()
    total_opex = (
        last_12["cam_charges"].sum()
        + last_12["property_taxes"].sum()
        + last_12["insurance"].sum()
        + last_12["utilities"].sum()
        + last_12["repairs_maintenance"].sum()
        + last_12["management_fees"].sum()
    )
    noi = total_rev - total_opex
    margin = (noi / total_rev * 100) if total_rev > 0 else 0

    print(f"\n  2025 YTD Portfolio Financials:")
    print(f"    Total Revenue:  ${total_rev:>14,.2f}")
    print(f"    Total OPEX:     ${total_opex:>14,.2f}")
    print(f"    Net Operating:  ${noi:>14,.2f}")
    print(f"    NOI Margin:     {margin:>13.1f}%")

    print("\n" + "=" * 60)


# =====================================================================
# MAIN
# =====================================================================

def main():
    """
    Orchestrate full CRE portfolio data generation pipeline.

    1. Generate dimension tables (Markets, Properties, Tenants)
    2. Generate fact tables (Leases, Monthly Financials)
    3. Export to CSV (data/raw/) and SQL (sql/02_seed_data.sql)
    4. Print portfolio summary statistics
    """
    print("=" * 60)
    print("  CRE Portfolio Data Generator")
    print("  Generating institutional-grade commercial real estate data...")
    print("=" * 60 + "\n")

    # ── Step 1: Dimensions ──
    print("Step 1/5 — Generating market benchmarks...")
    markets_df = generate_markets()

    print("Step 2/5 — Generating 25 property assets...")
    properties_df = generate_properties()

    print("Step 3/5 — Generating tenant universe...")
    tenants_df = generate_tenants()

    # ── Step 2: Facts ──
    print("Step 4/5 — Generating lease abstracts...")
    leases_df = generate_leases(properties_df, tenants_df, markets_df)

    print("Step 5/5 — Generating 36 months of property financials...")
    financials_df = generate_monthly_financials(properties_df, leases_df)

    # ── Step 3: Export ──
    dfs = {
        "markets":                     markets_df,
        "properties":                  properties_df,
        "tenants":                     tenants_df,
        "leases":                      leases_df,
        "property_monthly_financials": financials_df,
    }

    print("\nExporting CSV files:")
    export_csvs(dfs, OUTPUT_DIR)

    print("\nGenerating SQL seed file:")
    generate_sql_inserts(dfs, SQL_OUTPUT)

    # ── Step 4: Summary ──
    print_summary(dfs, properties_df, leases_df)

    print("\n✅  Data generation complete!")
    print(f"    CSV files:  {OUTPUT_DIR}/")
    print(f"    SQL file:   {SQL_OUTPUT}")
    print("\n  Next steps:")
    print("    1. Start PostgreSQL:        docker compose up -d")
    print("    2. Run schema DDL:          psql -f sql/01_schema_ddl.sql")
    print("    3. Load seed data:          psql -f sql/02_seed_data.sql")
    print("    4. Run analytical queries:  psql -f sql/03_analytical_views.sql")


if __name__ == "__main__":
    main()
