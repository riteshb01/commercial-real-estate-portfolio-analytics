"""
===============================================================================
Commercial Real Estate (CRE) Portfolio Performance & Lease Risk Analytics
Python Analytics Engine & Data Mart Pipeline
===============================================================================
Author: Commercial Real Estate Analytics Team
Description:
  1. Automated Data Quality & Schema Integrity Validation
  2. CRE Financial & Lease Feature Engineering (NOI, Occupancy, WALT, MTM)
  3. Analytics-Ready Data Mart Generation -> data/processed/
  4. Lease Rollover Sensitivity & Revenue-at-Risk Stress Testing
  5. Publication-Quality Figure Generation -> reports/figures/
===============================================================================
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns

# Set aesthetics for charts
sns.set_theme(style="whitegrid", font="sans-serif")
plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Helvetica", "Arial"]
plt.rcParams["axes.edgecolor"] = "#cccccc"
plt.rcParams["axes.linewidth"] = 0.8

# Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_RAW = os.path.join(BASE_DIR, "data", "raw")
DATA_PROC = os.path.join(BASE_DIR, "data", "processed")
FIGURES_DIR = os.path.join(BASE_DIR, "reports", "figures")

os.makedirs(DATA_PROC, exist_ok=True)
os.makedirs(FIGURES_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# 1. DATA EXTRACTION & INTEGRITY AUDIT
# -----------------------------------------------------------------------------
def load_and_validate_data():
    """Load raw CSV datasets and perform automated schema validation."""
    print("=" * 70)
    print("STEP 1: LOADING & VALIDATING COMMERCIAL REAL ESTATE DATASETS")
    print("=" * 70)
    
    markets = pd.read_csv(os.path.join(DATA_RAW, "markets.csv"))
    properties = pd.read_csv(os.path.join(DATA_RAW, "properties.csv"))
    tenants = pd.read_csv(os.path.join(DATA_RAW, "tenants.csv"))
    leases = pd.read_csv(os.path.join(DATA_RAW, "leases.csv"))
    financials = pd.read_csv(os.path.join(DATA_RAW, "property_monthly_financials.csv"))
    
    # Parse dates
    leases["lease_start_date"] = pd.to_datetime(leases["lease_start_date"])
    leases["lease_expiration_date"] = pd.to_datetime(leases["lease_expiration_date"])
    financials["period_date"] = pd.to_datetime(financials["period_date"])
    properties["acquisition_date"] = pd.to_datetime(properties["acquisition_date"])
    
    # Validation checks
    assert len(markets) == 4, f"Expected 4 markets, found {len(markets)}"
    assert len(properties) == 25, f"Expected 25 properties, found {len(properties)}"
    assert (leases["lease_expiration_date"] > leases["lease_start_date"]).all(), "Invalid lease date order found!"
    assert (financials["gross_rental_revenue"] >= 0).all(), "Negative revenue detected!"
    
    print(f"✔ Markets Loaded:     {len(markets):>4} records")
    print(f"✔ Properties Loaded:  {len(properties):>4} records (Total RSF: {properties['total_rsf'].sum():,})")
    print(f"✔ Tenants Loaded:     {len(tenants):>4} records")
    print(f"✔ Leases Loaded:      {len(leases):>4} records")
    print(f"✔ Monthly Financials: {len(financials):>4} records ({financials['period_date'].nunique()} months)")
    print("✔ All automated data integrity audits PASSED.\n")
    
    return markets, properties, tenants, leases, financials


# -----------------------------------------------------------------------------
# 2. FEATURE ENGINEERING & METRIC COMPUTATION
# -----------------------------------------------------------------------------
def compute_portfolio_metrics(markets, properties, tenants, leases, financials):
    """Compute CRE performance metrics: NOI, Occupancy, WALT, Mark-to-Market, Tenant HHI."""
    print("=" * 70)
    print("STEP 2: COMPUTING ADVANCED CRE PERFORMANCE METRICS & MARTS")
    print("=" * 70)
    
    # 2.1 Calculate Total OPEX & NOI for Monthly Financials
    financials["total_opex"] = (
        financials["cam_charges"] +
        financials["property_taxes"] +
        financials["insurance"] +
        financials["utilities"] +
        financials["repairs_maintenance"] +
        financials["management_fees"]
    )
    financials["total_revenue"] = financials["gross_rental_revenue"] + financials["other_income"]
    financials["noi"] = financials["total_revenue"] - financials["total_opex"]
    financials["noi_margin_pct"] = np.where(
        financials["total_revenue"] > 0,
        (financials["noi"] / financials["total_revenue"]) * 100,
        0
    )
    financials["opex_ratio_pct"] = np.where(
        financials["total_revenue"] > 0,
        (financials["total_opex"] / financials["total_revenue"]) * 100,
        0
    )
    
    # Merge Property and Market metadata into Financials
    fin_enriched = financials.merge(properties, on="property_id", how="left")
    fin_enriched = fin_enriched.merge(markets, on="market_id", how="left")
    fin_enriched["annualized_rev_psf"] = (fin_enriched["total_revenue"] * 12) / fin_enriched["total_rsf"]
    fin_enriched["annualized_opex_psf"] = (fin_enriched["total_opex"] * 12) / fin_enriched["total_rsf"]
    fin_enriched["annualized_noi_psf"] = (fin_enriched["noi"] * 12) / fin_enriched["total_rsf"]

    # 2.2 Active Leases & Occupancy Calculation
    ref_date = pd.Timestamp("2025-12-31")
    active_leases = leases[leases["lease_status"] == "Active"].copy()
    active_leases["annual_contract_rent"] = active_leases["leased_sqft"] * active_leases["base_rent_psf_year"]
    active_leases["remaining_term_years"] = np.maximum(
        0,
        (active_leases["lease_expiration_date"] - ref_date).dt.days / 365.25
    )
    active_leases["expiration_year"] = active_leases["lease_expiration_date"].dt.year
    
    # Merge property & tenant metadata to active leases
    active_leases = active_leases.merge(properties[["property_id", "property_name", "asset_class", "property_subtype", "total_rsf", "market_id"]], on="property_id", how="left")
    active_leases = active_leases.merge(markets[["market_id", "metro_area", "avg_class_a_rent_psf", "avg_class_b_rent_psf", "avg_industrial_rent_psf", "avg_retail_rent_psf"]], on="market_id", how="left")
    active_leases = active_leases.merge(tenants[["tenant_id", "tenant_name", "industry", "credit_rating", "tenant_type"]], on="tenant_id", how="left")

    # 2.3 Mark-to-Market Asking Rent Calculation
    def get_market_rent(row):
        ac = row["asset_class"]
        sub = str(row["property_subtype"])
        if ac == "Office" and "Class A" in sub:
            return row["avg_class_a_rent_psf"]
        elif ac == "Office":
            return row["avg_class_b_rent_psf"]
        elif ac == "Industrial":
            return row["avg_industrial_rent_psf"]
        elif ac == "Retail":
            return row["avg_retail_rent_psf"]
        return row["base_rent_psf_year"]

    active_leases["market_asking_rent_psf"] = active_leases.apply(get_market_rent, axis=1)
    active_leases["rent_variance_psf"] = active_leases["base_rent_psf_year"] - active_leases["market_asking_rent_psf"]
    active_leases["rent_variance_pct"] = (active_leases["rent_variance_psf"] / active_leases["market_asking_rent_psf"]) * 100
    active_leases["mtm_annual_gain_loss"] = active_leases["leased_sqft"] * (active_leases["market_asking_rent_psf"] - active_leases["base_rent_psf_year"])

    # 2.4 Property Summary Mart (2025 YTD Full Year)
    fin_2025 = fin_enriched[fin_enriched["period_date"].dt.year == 2025]
    prop_fin_2025 = fin_2025.groupby("property_id").agg(
        annual_revenue=("total_revenue", "sum"),
        annual_opex=("total_opex", "sum"),
        annual_noi=("noi", "sum")
    ).reset_index()
    
    prop_leases = active_leases.groupby("property_id").agg(
        occupied_rsf=("leased_sqft", "sum"),
        active_lease_count=("lease_id", "count"),
        annual_contract_rent=("annual_contract_rent", "sum"),
        sqft_weighted_walt=("remaining_term_years", lambda x: np.average(x, weights=active_leases.loc[x.index, "leased_sqft"]))
    ).reset_index()

    mart_property_kpis = properties.merge(markets[["market_id", "metro_area", "state"]], on="market_id", how="left")
    mart_property_kpis = mart_property_kpis.merge(prop_leases, on="property_id", how="left").fillna(0)
    mart_property_kpis = mart_property_kpis.merge(prop_fin_2025, on="property_id", how="left").fillna(0)
    
    mart_property_kpis["occupancy_rate_pct"] = (mart_property_kpis["occupied_rsf"] / mart_property_kpis["total_rsf"]) * 100
    mart_property_kpis["vacant_rsf"] = mart_property_kpis["total_rsf"] - mart_property_kpis["occupied_rsf"]
    mart_property_kpis["noi_margin_pct"] = np.where(mart_property_kpis["annual_revenue"] > 0, (mart_property_kpis["annual_noi"] / mart_property_kpis["annual_revenue"]) * 100, 0)
    mart_property_kpis["revenue_psf"] = mart_property_kpis["annual_revenue"] / mart_property_kpis["total_rsf"]
    mart_property_kpis["opex_psf"] = mart_property_kpis["annual_opex"] / mart_property_kpis["total_rsf"]
    mart_property_kpis["noi_psf"] = mart_property_kpis["annual_noi"] / mart_property_kpis["total_rsf"]
    mart_property_kpis["cap_rate_pct"] = (mart_property_kpis["annual_noi"] / mart_property_kpis["acquisition_price"]) * 100

    # 2.5 Tenant Concentration Mart
    total_active_rent = active_leases["annual_contract_rent"].sum()
    total_active_sf = active_leases["leased_sqft"].sum()
    
    mart_tenants = active_leases.groupby(["tenant_id", "tenant_name", "industry", "credit_rating", "tenant_type"]).agg(
        total_leased_sqft=("leased_sqft", "sum"),
        total_annual_rent=("annual_contract_rent", "sum"),
        properties_occupied=("property_id", "nunique"),
        tenant_walt_years=("remaining_term_years", lambda x: np.average(x, weights=active_leases.loc[x.index, "leased_sqft"]))
    ).reset_index()
    
    mart_tenants["pct_portfolio_revenue"] = (mart_tenants["total_annual_rent"] / total_active_rent) * 100
    mart_tenants["pct_portfolio_occupied_rsf"] = (mart_tenants["total_leased_sqft"] / total_active_sf) * 100
    mart_tenants = mart_tenants.sort_values(by="total_annual_rent", ascending=False).reset_index(drop=True)
    mart_tenants["revenue_rank"] = mart_tenants.index + 1
    mart_tenants["cumulative_revenue_pct"] = mart_tenants["pct_portfolio_revenue"].cumsum()
    
    # Herfindahl-Hirschman Index (HHI) for tenant concentration
    hhi_score = (mart_tenants["pct_portfolio_revenue"] ** 2).sum()
    
    # 2.6 Lease Rollover Schedule Mart
    mart_rollover = active_leases.groupby("expiration_year").agg(
        expiring_lease_count=("lease_id", "count"),
        expiring_sqft=("leased_sqft", "sum"),
        expiring_annual_rent=("annual_contract_rent", "sum")
    ).reset_index()
    mart_rollover["pct_portfolio_sqft"] = (mart_rollover["expiring_sqft"] / total_active_sf) * 100
    mart_rollover["pct_portfolio_rent"] = (mart_rollover["expiring_annual_rent"] / total_active_rent) * 100

    # Portfolio-level WALT
    portfolio_walt = (active_leases["remaining_term_years"] * active_leases["leased_sqft"]).sum() / total_active_sf

    print(f"✔ Portfolio RSF:          {properties['total_rsf'].sum():,}")
    print(f"✔ Occupied RSF:           {total_active_sf:,} ({total_active_sf / properties['total_rsf'].sum() * 100:.1f}%)")
    print(f"✔ Portfolio 2025 Revenue: ${mart_property_kpis['annual_revenue'].sum():,.2f}")
    print(f"✔ Portfolio 2025 NOI:     ${mart_property_kpis['annual_noi'].sum():,.2f}")
    print(f"✔ Portfolio NOI Margin:   {(mart_property_kpis['annual_noi'].sum() / mart_property_kpis['annual_revenue'].sum()) * 100:.1f}%")
    print(f"✔ Portfolio WALT:         {portfolio_walt:.2f} Years")
    print(f"✔ Tenant HHI Index:       {hhi_score:.1f} (Unconcentrated / Diversified < 1500)")
    print("✔ Metric computation complete.\n")

    return {
        "markets": markets,
        "properties": properties,
        "tenants": tenants,
        "leases": leases,
        "financials": fin_enriched,
        "active_leases": active_leases,
        "mart_property_kpis": mart_property_kpis,
        "mart_tenants": mart_tenants,
        "mart_rollover": mart_rollover,
        "portfolio_walt": portfolio_walt,
        "hhi_score": hhi_score
    }


# -----------------------------------------------------------------------------
# 3. EXPORT PROCESSED DATA MARTS
# -----------------------------------------------------------------------------
def export_processed_marts(data_dict):
    """Save processed datasets to data/processed/ for Power BI and reporting."""
    print("=" * 70)
    print("STEP 3: EXPORTING PROCESSED DATA MARTS TO data/processed/")
    print("=" * 70)
    
    data_dict["mart_property_kpis"].to_csv(os.path.join(DATA_PROC, "mart_property_kpis.csv"), index=False)
    data_dict["mart_tenants"].to_csv(os.path.join(DATA_PROC, "mart_tenant_concentration.csv"), index=False)
    data_dict["mart_rollover"].to_csv(os.path.join(DATA_PROC, "mart_lease_rollover_schedule.csv"), index=False)
    data_dict["active_leases"].to_csv(os.path.join(DATA_PROC, "fct_active_leases_enriched.csv"), index=False)
    data_dict["financials"].to_csv(os.path.join(DATA_PROC, "fct_monthly_financials_enriched.csv"), index=False)
    
    print("✔ mart_property_kpis.csv exported.")
    print("✔ mart_tenant_concentration.csv exported.")
    print("✔ mart_lease_rollover_schedule.csv exported.")
    print("✔ fct_active_leases_enriched.csv exported.")
    print("✔ fct_monthly_financials_enriched.csv exported.\n")


# -----------------------------------------------------------------------------
# 4. DATA VISUALIZATION & FIGURE GENERATION
# -----------------------------------------------------------------------------
def generate_visualizations(data_dict):
    """Generate high-resolution figures for reports and presentation."""
    print("=" * 70)
    print("STEP 4: GENERATING PUBLICATION-QUALITY FIGURES IN reports/figures/")
    print("=" * 70)

    palette_metro = {"Austin": "#2563EB", "Dallas-Fort Worth": "#10B981", "Atlanta": "#F59E0B", "Charlotte": "#8B5CF6"}
    palette_asset = {"Office": "#3B82F6", "Industrial": "#10B981", "Retail": "#EC4899"}

    # -------------------------------------------------------------------------
    # Figure 1: Occupancy Rate & Total RSF by Market & Asset Class
    # -------------------------------------------------------------------------
    fig, ax1 = plt.subplots(figsize=(10, 5.5), dpi=300)
    prop_kpi = data_dict["mart_property_kpis"]
    
    mkt_summary = prop_kpi.groupby("metro_area").agg(
        total_rsf=("total_rsf", "sum"),
        occupied_rsf=("occupied_rsf", "sum")
    ).reset_index()
    mkt_summary["occupancy_pct"] = (mkt_summary["occupied_rsf"] / mkt_summary["total_rsf"]) * 100
    mkt_summary = mkt_summary.sort_values(by="total_rsf", ascending=False)
    
    bars = ax1.bar(mkt_summary["metro_area"], mkt_summary["total_rsf"] / 1e6, color="#E2E8F0", width=0.55, label="Total RSF (M SF)")
    ax1.bar(mkt_summary["metro_area"], mkt_summary["occupied_rsf"] / 1e6, color="#3B82F6", width=0.55, label="Occupied RSF (M SF)")
    
    ax1.set_ylabel("Rentable Square Feet (Millions)", fontsize=11, fontweight="bold", color="#1E293B")
    ax1.set_ylim(0, max(mkt_summary["total_rsf"] / 1e6) * 1.25)
    
    # Line plot for occupancy percentage
    ax2 = ax1.twinx()
    ax2.plot(mkt_summary["metro_area"], mkt_summary["occupancy_pct"], color="#EF4444", marker="o", linewidth=2.5, markersize=8, label="Occupancy %")
    ax2.set_ylabel("Occupancy Rate (%)", fontsize=11, fontweight="bold", color="#EF4444")
    ax2.set_ylim(70, 100)
    ax2.yaxis.set_major_formatter(ticker.PercentFormatter())
    
    # Annotate values
    for i, row in mkt_summary.reset_index().iterrows():
        ax2.annotate(f"{row['occupancy_pct']:.1f}%", 
                     (row["metro_area"], row["occupancy_pct"]),
                     textcoords="offset points", xytext=(0, 10), ha="center",
                     fontsize=10, fontweight="bold", color="#EF4444")

    plt.title("Commercial Portfolio RSF & Occupancy Rate by Market (2025)", fontsize=13, fontweight="bold", pad=15, color="#0F172A")
    ax1.legend(loc="upper left", frameon=True)
    ax2.legend(loc="upper right", frameon=True)
    plt.tight_layout()
    fig1_path = os.path.join(FIGURES_DIR, "01_portfolio_occupancy_by_market.png")
    plt.savefig(fig1_path, dpi=300)
    plt.close()
    print("✔ Figure 1 saved: 01_portfolio_occupancy_by_market.png")

    # -------------------------------------------------------------------------
    # Figure 2: Monthly NOI Margin Trends by Asset Class (36 Months)
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(11, 5.5), dpi=300)
    fin_df = data_dict["financials"]
    
    monthly_ac = fin_df.groupby(["period_date", "asset_class"]).agg(
        revenue=("total_revenue", "sum"),
        noi=("noi", "sum")
    ).reset_index()
    monthly_ac["noi_margin_pct"] = (monthly_ac["noi"] / monthly_ac["revenue"]) * 100

    for ac, color in palette_asset.items():
        sub = monthly_ac[monthly_ac["asset_class"] == ac]
        ax.plot(sub["period_date"], sub["noi_margin_pct"], label=ac, color=color, linewidth=2.2)

    ax.set_title("36-Month Net Operating Income (NOI) Margin Trend by Asset Class (2023 - 2025)", fontsize=13, fontweight="bold", pad=15, color="#0F172A")
    ax.set_ylabel("NOI Margin (%)", fontsize=11, fontweight="bold", color="#1E293B")
    ax.set_xlabel("Operating Period", fontsize=11, fontweight="bold", color="#1E293B")
    ax.yaxis.set_major_formatter(ticker.PercentFormatter())
    ax.legend(title="Asset Class", loc="lower left", frameon=True)
    plt.tight_layout()
    fig2_path = os.path.join(FIGURES_DIR, "02_noi_margin_by_asset_class.png")
    plt.savefig(fig2_path, dpi=300)
    plt.close()
    print("✔ Figure 2 saved: 02_noi_margin_by_asset_class.png")

    # -------------------------------------------------------------------------
    # Figure 3: Lease Rollover & Expiration Schedule (2026 - 2033+)
    # -------------------------------------------------------------------------
    fig, ax1 = plt.subplots(figsize=(10, 5.5), dpi=300)
    rollover = data_dict["mart_rollover"]
    
    bars = ax1.bar(rollover["expiration_year"].astype(str), rollover["expiring_sqft"] / 1000, color="#6366F1", width=0.55, label="Expiring RSF (000s SF)")
    ax1.set_ylabel("Expiring Area (Thousand RSF)", fontsize=11, fontweight="bold", color="#1E293B")
    ax1.set_xlabel("Lease Expiration Year", fontsize=11, fontweight="bold", color="#1E293B")
    
    ax2 = ax1.twinx()
    ax2.plot(rollover["expiration_year"].astype(str), rollover["expiring_annual_rent"] / 1e6, color="#10B981", marker="s", linewidth=2.5, markersize=8, label="Annual Revenue at Risk ($M)")
    ax2.set_ylabel("Annual Revenue at Risk ($ Millions)", fontsize=11, fontweight="bold", color="#10B981")
    ax2.yaxis.set_major_formatter(ticker.StrMethodFormatter("${x:,.1f}M"))
    
    for i, row in rollover.iterrows():
        ax2.annotate(f"${row['expiring_annual_rent']/1e6:.1f}M\n({row['pct_portfolio_rent']:.1f}%)",
                     (str(int(row["expiration_year"])), row["expiring_annual_rent"] / 1e6),
                     textcoords="offset points", xytext=(0, 10), ha="center",
                     fontsize=8.5, fontweight="bold", color="#047857")

    plt.title("Portfolio Lease Rollover Schedule & Revenue-at-Risk Timeline", fontsize=13, fontweight="bold", pad=15, color="#0F172A")
    ax1.legend(loc="upper right", bbox_to_anchor=(0.85, 0.98), frameon=True)
    ax2.legend(loc="upper right", frameon=True)
    plt.tight_layout()
    fig3_path = os.path.join(FIGURES_DIR, "03_lease_rollover_schedule_timeline.png")
    plt.savefig(fig3_path, dpi=300)
    plt.close()
    print("✔ Figure 3 saved: 03_lease_rollover_schedule_timeline.png")

    # -------------------------------------------------------------------------
    # Figure 4: Top 10 Tenant Concentration & Credit Ratings
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)
    top10 = data_dict["mart_tenants"].head(10).copy()
    top10 = top10.sort_values(by="total_annual_rent", ascending=True)

    credit_colors = {"AAA": "#10B981", "AA": "#059669", "A": "#34D399", "BBB": "#3B82F6", "BB": "#F59E0B", "B": "#EF4444", "NR": "#94A3B8"}
    bar_colors = [credit_colors.get(c, "#64748B") for c in top10["credit_rating"]]

    bars = ax.barh(top10["tenant_name"], top10["total_annual_rent"] / 1e6, color=bar_colors, height=0.65)
    ax.set_xlabel("Annual Contract Rent ($ Millions)", fontsize=11, fontweight="bold", color="#1E293B")
    ax.set_title("Top 10 Tenant Concentration & Credit Rating Breakdown", fontsize=13, fontweight="bold", pad=15, color="#0F172A")
    ax.xaxis.set_major_formatter(ticker.StrMethodFormatter("${x:,.1f}M"))

    for bar, pct, cr in zip(bars, top10["pct_portfolio_revenue"], top10["credit_rating"]):
        ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2,
                f"{pct:.1f}% ({cr})", va="center", ha="left", fontsize=9, fontweight="bold", color="#334155")

    # Custom legend for credit rating
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#10B981", label="Investment Grade (AAA-A)"),
        Patch(facecolor="#3B82F6", label="Investment Grade (BBB)"),
        Patch(facecolor="#F59E0B", label="Speculative Grade (BB-B)"),
        Patch(facecolor="#94A3B8", label="Non-Rated (NR)")
    ]
    ax.legend(handles=legend_elements, loc="lower right", frameon=True)
    plt.tight_layout()
    fig4_path = os.path.join(FIGURES_DIR, "04_tenant_concentration_top10.png")
    plt.savefig(fig4_path, dpi=300)
    plt.close()
    print("✔ Figure 4 saved: 04_tenant_concentration_top10.png")

    # -------------------------------------------------------------------------
    # Figure 5: Mark-to-Market Rent Analysis (In-Place vs Market Asking)
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)
    active_leases = data_dict["active_leases"]
    
    mtm_summary = active_leases.groupby(["metro_area", "asset_class"]).agg(
        in_place_rent=("base_rent_psf_year", lambda x: np.average(x, weights=active_leases.loc[x.index, "leased_sqft"])),
        market_rent=("market_asking_rent_psf", lambda x: np.average(x, weights=active_leases.loc[x.index, "leased_sqft"]))
    ).reset_index()
    mtm_summary["category"] = mtm_summary["metro_area"] + "\n(" + mtm_summary["asset_class"] + ")"
    mtm_summary = mtm_summary.sort_values(by="in_place_rent", ascending=False)

    x = np.arange(len(mtm_summary))
    width = 0.38
    ax.bar(x - width/2, mtm_summary["in_place_rent"], width, label="In-Place Contract Rent ($/SF)", color="#3B82F6")
    ax.bar(x + width/2, mtm_summary["market_rent"], width, label="Market Asking Rent ($/SF)", color="#10B981")

    ax.set_ylabel("Annual Rent ($/SF/Year)", fontsize=11, fontweight="bold", color="#1E293B")
    ax.set_xticks(x)
    ax.set_xticklabels(mtm_summary["category"], rotation=0, fontsize=8.5)
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("${x:,.0f}"))
    ax.set_title("Mark-to-Market Rent Variance: In-Place Contract vs Market Asking Rate", fontsize=13, fontweight="bold", pad=15, color="#0F172A")
    ax.legend(loc="upper right", frameon=True)
    plt.tight_layout()
    fig5_path = os.path.join(FIGURES_DIR, "05_mark_to_market_rent_variance.png")
    plt.savefig(fig5_path, dpi=300)
    plt.close()
    print("✔ Figure 5 saved: 05_mark_to_market_rent_variance.png")

    # -------------------------------------------------------------------------
    # Figure 6: Lease Rollover Stress Testing & Cash Flow Sensitivity
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)
    
    # 2026-2027 Expirations
    exp_26_27 = active_leases[active_leases["expiration_year"].isin([2026, 2027])]
    total_exp_rev = exp_26_27["annual_contract_rent"].sum()
    
    scenarios = ["Base Case\n(100% Renewal)", "Mild Stress\n(80% Renewal)", "Moderate Stress\n(60% Renewal)", "Severe Stress\n(40% Renewal)", "Worst Case\n(0% Renewal)"]
    retention_rates = [1.0, 0.80, 0.60, 0.40, 0.0]
    retained_rev = [total_exp_rev * r / 1e6 for r in retention_rates]
    loss_rev = [total_exp_rev * (1 - r) / 1e6 for r in retention_rates]

    ax.bar(scenarios, retained_rev, label="Retained Annual Revenue ($M)", color="#10B981", width=0.55)
    ax.bar(scenarios, loss_rev, bottom=retained_rev, label="Revenue Loss at Risk ($M)", color="#EF4444", width=0.55)

    ax.set_ylabel("Annual Cash Flow Impact ($ Millions)", fontsize=11, fontweight="bold", color="#1E293B")
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("${x:,.1f}M"))
    ax.set_title("2026-2027 Lease Rollover Stress Test & Revenue-at-Risk Scenarios", fontsize=13, fontweight="bold", pad=15, color="#0F172A")
    
    for i, (ret, loss) in enumerate(zip(retained_rev, loss_rev)):
        if loss > 0:
            ax.text(i, ret + loss / 2, f"-${loss:.1f}M", ha="center", va="center", color="white", fontweight="bold", fontsize=9.5)
        ax.text(i, ret / 2 if ret > 0 else 0.5, f"${ret:.1f}M", ha="center", va="center", color="white" if ret > 0 else "#1E293B", fontweight="bold", fontsize=9.5)

    ax.legend(loc="upper right", frameon=True)
    plt.tight_layout()
    fig6_path = os.path.join(FIGURES_DIR, "06_revenue_at_risk_stress_test.png")
    plt.savefig(fig6_path, dpi=300)
    plt.close()
    print("✔ Figure 6 saved: 06_revenue_at_risk_stress_test.png\n")


# -----------------------------------------------------------------------------
# MAIN EXECUTION
# -----------------------------------------------------------------------------
def main():
    print("\n" + "=" * 70)
    print("COMMERCIAL REAL ESTATE PORTFOLIO ANALYTICS PIPELINE")
    print("=" * 70 + "\n")
    
    markets, properties, tenants, leases, financials = load_and_validate_data()
    data_dict = compute_portfolio_metrics(markets, properties, tenants, leases, financials)
    export_processed_marts(data_dict)
    generate_visualizations(data_dict)
    
    print("=" * 70)
    print("PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
