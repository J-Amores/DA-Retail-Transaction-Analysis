"""
End-to-end analysis pipeline for the Online Retail dataset.
Run once to produce: charts/*, data/processed/*.csv, data/processed/*.json.
The notebook (analysis.ipynb) wraps this same logic in stages with markdown framing.
"""

import json
import os
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import PartialDependenceDisplay, permutation_importance
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score
from sklearn.metrics import (
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
)

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent  # scripts/ → project root
RAW = BASE / "data" / "raw" / "Online Retail.xlsx"
PROC = BASE / "data" / "processed"
CHARTS = BASE / "charts"
PROC.mkdir(parents=True, exist_ok=True)
CHARTS.mkdir(parents=True, exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────────────────
PALETTE = ["#1E3A5F", "#E07856", "#C9A961", "#2D7A82"]
ANALYSIS_START = pd.Timestamp("2010-12-01")
ANALYSIS_END = pd.Timestamp("2011-11-30 23:59:59")  # 12 full months

# Putler 11-segment grid: maps (R-score, F-score) → segment name.
# F here is mean(F, M) per the standard simplification (so the 2-D grid is auditable).
SEGMENT_GRID = {
    # (R_high_low, FM_high_low) buckets are derived from R quintile + mean(F,M) quintile
    # Format: lambda r, fm -> name
}


def assign_segment(r: int, f: int, m: int) -> str:
    """Putler-style 11-segment assignment from R, F, M quintile scores (1=worst, 5=best)."""
    fm = (f + m) / 2  # combine F and M into a single 'engagement' score
    # Putler standard grid
    if r >= 5 and fm >= 4:
        return "Champions"
    if r >= 4 and fm >= 3:
        return "Loyal Customers"
    if r >= 4 and fm <= 2:
        return "Potential Loyalists"
    if r == 5 and fm <= 2:
        return "New Customers"
    if r >= 3 and fm == 3:
        return "Promising"
    if r == 3 and fm <= 2:
        return "Need Attention"
    if r == 2 and fm == 3:
        return "About to Sleep"
    if r == 2 and fm >= 4:
        return "At Risk"
    if r == 1 and fm >= 4:
        return "Cannot Lose Them"
    if r <= 2 and fm <= 2:
        return "Hibernating"
    return "Lost"


def style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


plt.rcParams.update(
    {
        "figure.dpi": 150,
        "font.family": "sans-serif",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
    }
)


def save(name):
    plt.savefig(CHARTS / name, dpi=150, bbox_inches="tight")
    plt.close()


# ─────────────────────────────────────────────────────────────────────────────
# STAGE A — EXPLORE
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("STAGE A — EXPLORE")
print("=" * 70)

df = pd.read_excel(RAW)
df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
print(f"Loaded {len(df):,} rows × {df.shape[1]} cols")
print(f"Date range: {df['InvoiceDate'].min()} → {df['InvoiceDate'].max()}")
ROWS_RAW = len(df)

# A1 — data overview (4-panel)
fig, axes = plt.subplots(2, 2, figsize=(13, 8))
ax = axes[0, 0]
df.groupby(df["InvoiceDate"].dt.to_period("M")).size().plot(
    kind="bar", ax=ax, color=PALETTE[0]
)
ax.set_title("Transactions per month (raw)", fontweight="bold")
ax.set_xlabel("")
ax.set_ylabel("Rows")
ax.tick_params(axis="x", rotation=45)

ax = axes[0, 1]
top_countries = df["Country"].value_counts().head(8)
ax.barh(top_countries.index[::-1], top_countries.values[::-1], color=PALETTE[3])
ax.set_title("Top 8 countries by row count", fontweight="bold")
ax.set_xlabel("Rows")

ax = axes[1, 0]
ax.axis("off")
overview_table = pd.DataFrame(
    {
        "metric": [
            "Rows",
            "Distinct InvoiceNo",
            "Distinct StockCode",
            "Distinct CustomerID",
            "Countries",
            "Date span (days)",
        ],
        "value": [
            f"{len(df):,}",
            f"{df['InvoiceNo'].nunique():,}",
            f"{df['StockCode'].nunique():,}",
            f"{df['CustomerID'].nunique():,}",
            f"{df['Country'].nunique():,}",
            f"{(df['InvoiceDate'].max() - df['InvoiceDate'].min()).days}",
        ],
    }
)
table = ax.table(
    cellText=overview_table.values,
    colLabels=["Metric", "Value"],
    loc="center",
    cellLoc="left",
)
table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 1.6)
ax.set_title("Dataset cardinalities", fontweight="bold", y=0.95)

ax = axes[1, 1]
issue_counts = pd.Series(
    {
        "Cancellations\n(InvoiceNo C*)": df["InvoiceNo"].astype(str).str.startswith("C").sum(),
        "Negative Quantity": (df["Quantity"] <= 0).sum(),
        "UnitPrice ≤ 0": (df["UnitPrice"] <= 0).sum(),
        "Missing CustomerID": df["CustomerID"].isna().sum(),
        "Exact duplicates": df.duplicated().sum(),
    }
)
issue_counts.plot(kind="barh", ax=ax, color=PALETTE[1])
ax.set_title("Data-quality flags (raw)", fontweight="bold")
ax.set_xlabel("Rows affected")
for i, v in enumerate(issue_counts.values):
    ax.text(v, i, f" {v:,}", va="center", fontsize=9)

plt.suptitle(
    "Online Retail — raw data overview", fontsize=14, fontweight="bold", y=1.00
)
plt.tight_layout()
save("A1_data_overview.png")
print("  → charts/A1_data_overview.png")

# A2 — missingness
nulls = df.isna().sum().sort_values(ascending=True)
fig, ax = plt.subplots(figsize=(9, 4.5))
bars = ax.barh(nulls.index, nulls.values, color=PALETTE[2])
for i, (col, n) in enumerate(zip(nulls.index, nulls.values)):
    pct = n / len(df) * 100
    ax.text(n, i, f" {n:,} ({pct:.2f}%)", va="center", fontsize=9)
ax.set_title("Missingness per column (raw)", fontweight="bold")
ax.set_xlabel("Null count")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, p: f"{int(v):,}"))
plt.tight_layout()
save("A2_missingness.png")
print("  → charts/A2_missingness.png")


# ─────────────────────────────────────────────────────────────────────────────
# STAGE B — PROFILE
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("STAGE B — PROFILE")
print("=" * 70)

# Net per-row revenue (raw)
df["LineRevenue"] = df["Quantity"] * df["UnitPrice"]

# B1 — revenue over time
fig, ax = plt.subplots(figsize=(11, 4.5))
monthly = df.groupby(df["InvoiceDate"].dt.to_period("M"))["LineRevenue"].sum() / 1e6
ax.plot(monthly.index.astype(str), monthly.values, marker="o", color=PALETTE[0], lw=2)
ax.fill_between(monthly.index.astype(str), 0, monthly.values, alpha=0.15, color=PALETTE[0])
ax.set_title("Monthly net revenue (raw, GBP) — full data window", fontweight="bold")
ax.set_xlabel("")
ax.set_ylabel("Revenue (£ millions)")
ax.tick_params(axis="x", rotation=45)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, p: f"£{v:.1f}M"))
plt.tight_layout()
save("B1_revenue_over_time.png")
print("  → charts/B1_revenue_over_time.png")

# B2 — country distribution
country_rev = df.groupby("Country")["LineRevenue"].sum().sort_values(ascending=False).head(10)
country_count = df.groupby("Country").size().reindex(country_rev.index)
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
axes[0].barh(country_rev.index[::-1], country_rev.values[::-1] / 1e6, color=PALETTE[0])
axes[0].set_title("Top 10 countries — revenue (£M)", fontweight="bold")
axes[0].set_xlabel("Revenue (£ millions)")
axes[0].xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, p: f"£{v:.1f}M"))
axes[1].barh(country_count.index[::-1], country_count.values[::-1], color=PALETTE[3])
axes[1].set_title("Top 10 countries — order rows", fontweight="bold")
axes[1].set_xlabel("Rows")
axes[1].xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, p: f"{int(v):,}"))
plt.tight_layout()
save("B2_country_distribution.png")
print("  → charts/B2_country_distribution.png")

# B3 — quantity & unitprice distributions (log-scale)
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
qty_pos = df.loc[df["Quantity"] > 0, "Quantity"]
axes[0].hist(qty_pos, bins=60, color=PALETTE[0])
axes[0].set_yscale("log")
axes[0].set_xscale("log")
axes[0].set_title("Quantity per line item (positive only, log–log)", fontweight="bold")
axes[0].set_xlabel("Quantity")
axes[0].set_ylabel("Lines (log)")

up_pos = df.loc[df["UnitPrice"] > 0, "UnitPrice"]
axes[1].hist(up_pos, bins=60, color=PALETTE[3])
axes[1].set_yscale("log")
axes[1].set_xscale("log")
axes[1].set_title("Unit price (positive only, log–log)", fontweight="bold")
axes[1].set_xlabel("Unit price (£)")
axes[1].set_ylabel("Lines (log)")
plt.tight_layout()
save("B3_qty_unitprice_dist.png")
print("  → charts/B3_qty_unitprice_dist.png")

# B4 — invoice size (lines per invoice, £ per invoice)
inv_grp = df.groupby("InvoiceNo").agg(
    Lines=("StockCode", "size"), Total=("LineRevenue", "sum")
)
inv_grp_pos = inv_grp[inv_grp["Total"] > 0]
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
axes[0].hist(inv_grp_pos["Lines"], bins=60, color=PALETTE[0])
axes[0].set_yscale("log")
axes[0].set_title("Lines per invoice (positive-revenue invoices)", fontweight="bold")
axes[0].set_xlabel("Lines per invoice")
axes[0].set_ylabel("Invoices (log)")

axes[1].hist(inv_grp_pos["Total"].clip(upper=2000), bins=60, color=PALETTE[3])
axes[1].set_yscale("log")
axes[1].set_title("Invoice total (£, clipped at £2 000)", fontweight="bold")
axes[1].set_xlabel("Invoice total (£)")
axes[1].set_ylabel("Invoices (log)")
plt.tight_layout()
save("B4_invoice_size_dist.png")
print("  → charts/B4_invoice_size_dist.png")

# B5 — returns vs purchases over time
df["IsReturn"] = (df["InvoiceNo"].astype(str).str.startswith("C")) | (df["Quantity"] < 0)
month = df["InvoiceDate"].dt.to_period("M")
purch = df[~df["IsReturn"]].groupby(month)["LineRevenue"].sum() / 1e6
ret = df[df["IsReturn"]].groupby(month)["LineRevenue"].sum() / 1e6  # negative
fig, ax = plt.subplots(figsize=(11, 4.5))
ax.bar(purch.index.astype(str), purch.values, color=PALETTE[0], label="Purchases")
ax.bar(ret.index.astype(str), ret.values, color=PALETTE[1], label="Returns / cancellations")
ax.set_title("Purchases vs returns by month (£M, raw)", fontweight="bold")
ax.set_xlabel("")
ax.set_ylabel("Revenue (£M)")
ax.axhline(0, color="black", lw=0.5)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, p: f"£{v:.1f}M"))
ax.legend(loc="upper left")
ax.tick_params(axis="x", rotation=45)
plt.tight_layout()
save("B5_returns_vs_purchases.png")
print("  → charts/B5_returns_vs_purchases.png")


# ─────────────────────────────────────────────────────────────────────────────
# STAGE C — CLEAN
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("STAGE C — CLEAN")
print("=" * 70)

cleaning_log = {}


def log_step(name, before, after, note=""):
    cleaning_log[name] = {"rows_before": int(before), "rows_after": int(after), "note": note}
    print(f"  {name:40s}  {before:>9,} → {after:>9,}   {note}")


df_c = df.copy()

# C.1 Trim to 12 full months (2010-12-01 → 2011-11-30)
b = len(df_c)
df_c = df_c[(df_c["InvoiceDate"] >= ANALYSIS_START) & (df_c["InvoiceDate"] <= ANALYSIS_END)].copy()
log_step("01_trim_period", b, len(df_c), "2010-12-01 → 2011-11-30")

# C.2 Drop UnitPrice <= 0
b = len(df_c)
df_c = df_c[df_c["UnitPrice"] > 0].copy()
log_step("02_drop_unitprice_le_0", b, len(df_c))

# C.3 Drop exact duplicates
b = len(df_c)
df_c = df_c.drop_duplicates().copy()
log_step("03_drop_exact_duplicates", b, len(df_c))

# C.4 Cancellations (InvoiceNo starts with C OR Quantity<0): KEEP, but flag
df_c["IsCancellation"] = (df_c["InvoiceNo"].astype(str).str.startswith("C")) | (df_c["Quantity"] < 0)
n_cancel = int(df_c["IsCancellation"].sum())
log_step(
    "04_flag_cancellations",
    len(df_c),
    len(df_c),
    f"{n_cancel:,} kept and netted (per spec)",
)

# C.5 Drop missing CustomerID for customer-level analyses (separate frame)
b = len(df_c)
df_with_cust = df_c.dropna(subset=["CustomerID"]).copy()
df_with_cust["CustomerID"] = df_with_cust["CustomerID"].astype(int)
log_step("05_drop_missing_customer", b, len(df_with_cust), "for customer-level analyses")

# C.6 Non-product StockCodes audit (not removed; documented)
df_c["StockCode_str"] = df_c["StockCode"].astype(str)
non_product_mask = df_c["StockCode_str"].str.upper().isin(
    ["POST", "M", "DOT", "BANK CHARGES", "AMAZONFEE", "CRUK", "B", "S"]
) | df_c["StockCode_str"].str.upper().str.startswith("GIFT_")
n_nonprod = int(non_product_mask.sum())
log_step(
    "06_non_product_codes",
    len(df_c),
    len(df_c),
    f"{n_nonprod:,} fee/postage/gift rows kept (no product-level analysis in scope)",
)

# Net line revenue (used everywhere from here)
df_c["LineRevenue"] = df_c["Quantity"] * df_c["UnitPrice"]
df_with_cust["LineRevenue"] = df_with_cust["Quantity"] * df_with_cust["UnitPrice"]


# ─────────────────────────────────────────────────────────────────────────────
# STAGE D — SHAPE & EXPORT
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("STAGE D — SHAPE & EXPORT")
print("=" * 70)

# D.1 Export cleaned line items
clean_out = df_c[
    [
        "InvoiceNo",
        "StockCode",
        "Description",
        "Quantity",
        "InvoiceDate",
        "UnitPrice",
        "CustomerID",
        "Country",
        "IsCancellation",
        "LineRevenue",
    ]
].copy()
clean_out.to_csv(PROC / "online_retail_clean.csv", index=False)
print(f"  → data/processed/online_retail_clean.csv  ({len(clean_out):,} rows)")

# D.2 Build per-customer feature frame for the LTV model
SNAPSHOT = ANALYSIS_END.normalize() + pd.Timedelta(days=1)  # 2011-12-01

cust = df_with_cust.copy()
cust["IsCancellation"] = (cust["InvoiceNo"].astype(str).str.startswith("C")) | (cust["Quantity"] < 0)

agg = cust.groupby("CustomerID").apply(
    lambda g: pd.Series(
        {
            "first_invoice": g["InvoiceDate"].min(),
            "last_invoice": g["InvoiceDate"].max(),
            "Recency": (SNAPSHOT - g["InvoiceDate"].max()).days,
            "Frequency": g.loc[~g["IsCancellation"], "InvoiceNo"].nunique(),
            "Monetary": g["LineRevenue"].sum(),  # NET (cancellations are negative)
            "TotalQuantity": g.loc[~g["IsCancellation"], "Quantity"].sum(),
            "TotalLines": int((~g["IsCancellation"]).sum()),
            "DistinctStockCodes": g.loc[~g["IsCancellation"], "StockCode"].nunique(),
            "CancellationRate": g["IsCancellation"].mean(),
            "Country": g["Country"].mode().iat[0],
        }
    )
)
agg = agg.reset_index()
agg["Tenure_days"] = (agg["last_invoice"] - agg["first_invoice"]).dt.days
agg["AvgBasketSize"] = (agg["TotalQuantity"] / agg["Frequency"].clip(lower=1)).round(2)
agg["AvgUnitPrice"] = (
    agg["Monetary"].clip(lower=0) / agg["TotalQuantity"].clip(lower=1)
).round(3)
agg["UK_vs_International"] = (agg["Country"] == "United Kingdom").astype(int)

# Drop pathological rows (e.g., customers with all-cancellation, net Monetary <= 0)
n_before = len(agg)
agg = agg[agg["Monetary"] > 0].copy()
n_after = len(agg)
log_step(
    "07_drop_net_negative_customers",
    n_before,
    n_after,
    "customers with net Monetary <= 0 after netting cancellations",
)

# D.3 RFM scoring (quintile bins)
agg["R_score"] = pd.qcut(-agg["Recency"], q=5, labels=[1, 2, 3, 4, 5], duplicates="drop").astype(int)
agg["F_score"] = pd.qcut(
    agg["Frequency"].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5], duplicates="drop"
).astype(int)
agg["M_score"] = pd.qcut(
    agg["Monetary"].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5], duplicates="drop"
).astype(int)
agg["Segment"] = agg.apply(
    lambda r: assign_segment(r["R_score"], r["F_score"], r["M_score"]), axis=1
)

# Export segment map (R, F, M score triples → segment), for auditability
seg_map = []
for r in range(1, 6):
    for f in range(1, 6):
        for m in range(1, 6):
            seg_map.append({"R": r, "F": f, "M": m, "Segment": assign_segment(r, f, m)})
with open(PROC / "rfm_segment_map.json", "w") as fh:
    json.dump(seg_map, fh, indent=2)
print(f"  → data/processed/rfm_segment_map.json  ({len(seg_map)} triples)")

# Export analysis frame
agg_out_cols = [
    "CustomerID",
    "Country",
    "UK_vs_International",
    "first_invoice",
    "last_invoice",
    "Tenure_days",
    "Recency",
    "Frequency",
    "Monetary",
    "TotalQuantity",
    "TotalLines",
    "DistinctStockCodes",
    "AvgBasketSize",
    "AvgUnitPrice",
    "CancellationRate",
    "R_score",
    "F_score",
    "M_score",
    "Segment",
]
agg[agg_out_cols].to_csv(PROC / "online_retail_analysis.csv", index=False)
print(
    f"  → data/processed/online_retail_analysis.csv  ({len(agg):,} customers × {len(agg_out_cols)} cols)"
)


# ─────────────────────────────────────────────────────────────────────────────
# STAGE E — ANALYZE
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("STAGE E — ANALYZE")
print("=" * 70)

# E1 — Q1: total revenue, AOV, repeat-purchase rate
total_rev_all = float(df_c["LineRevenue"].sum())  # includes missing-CustomerID rows
total_rev_cust = float(df_with_cust["LineRevenue"].sum())  # customer-level only
total_customers = int(df_with_cust["CustomerID"].nunique())
total_invoices_cust = int(
    df_with_cust.loc[~df_with_cust["IsCancellation"], "InvoiceNo"].nunique()
)
aov = total_rev_cust / total_invoices_cust  # GBP per invoice (customer-attributed)
n_repeat = int((agg["Frequency"] >= 2).sum())
repeat_rate = n_repeat / len(agg)

# 4-panel KPI block
fig, axes = plt.subplots(1, 4, figsize=(15, 4.2))


def kpi(ax, label, value, sub):
    ax.axis("off")
    ax.text(0.5, 0.7, value, ha="center", va="center", fontsize=24, fontweight="bold", color=PALETTE[0])
    ax.text(0.5, 0.42, label, ha="center", va="center", fontsize=11, color="#333")
    ax.text(0.5, 0.22, sub, ha="center", va="center", fontsize=9, color="#666")


kpi(axes[0], "Total revenue (12 months)", f"£{total_rev_all/1e6:.2f}M", "All sales · Dec 2010 – Nov 2011")
kpi(axes[1], "Active customers", f"{total_customers:,}", "Distinct CustomerIDs")
kpi(axes[2], "Average order value", f"£{aov:,.0f}", "Customer-attributed invoices")
kpi(axes[3], "Repeat-purchase rate", f"{repeat_rate*100:.1f}%", f"{n_repeat:,} customers with ≥ 2 orders")
plt.suptitle(
    "Headline KPIs — Online Retail, Dec 2010 – Nov 2011", fontsize=14, fontweight="bold"
)
plt.tight_layout()
save("E1_q1_size_kpis.png")
print("  → charts/E1_q1_size_kpis.png")

# E2 — Q2: segment revenue contribution
seg_summary = (
    agg.groupby("Segment")
    .agg(Revenue=("Monetary", "sum"), Customers=("CustomerID", "size"))
    .sort_values("Revenue", ascending=False)
)
seg_summary["Revenue_share"] = seg_summary["Revenue"] / seg_summary["Revenue"].sum() * 100

fig, ax = plt.subplots(figsize=(11, 5.5))
y = np.arange(len(seg_summary))
bars = ax.barh(y[::-1], seg_summary["Revenue"].values / 1e6, color=PALETTE[0])
# highlight top 3 in coral
for i, (idx, row) in enumerate(seg_summary.iterrows()):
    if i < 3:
        bars[len(seg_summary) - 1 - i].set_color(PALETTE[1])
ax.set_yticks(y[::-1])
ax.set_yticklabels(seg_summary.index)
ax.set_xlabel("Revenue (£ millions)")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, p: f"£{v:.1f}M"))
for i, (rev, share) in enumerate(zip(seg_summary["Revenue"].values, seg_summary["Revenue_share"].values)):
    ax.text(rev / 1e6, len(seg_summary) - 1 - i, f"  {share:.1f}%", va="center", fontsize=9)
ax.set_title("Revenue by RFM segment, Dec 2010 – Nov 2011 (top 3 highlighted)", fontweight="bold")
plt.tight_layout()
save("E2_q2_segment_revenue.png")
print("  → charts/E2_q2_segment_revenue.png")

# S4 — segment customer count companion
fig, ax = plt.subplots(figsize=(11, 5.5))
ax.barh(y[::-1], seg_summary["Customers"].values, color=PALETTE[3])
ax.set_yticks(y[::-1])
ax.set_yticklabels(seg_summary.index)
ax.set_xlabel("Customers")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, p: f"{int(v):,}"))
for i, n in enumerate(seg_summary["Customers"].values):
    ax.text(n, len(seg_summary) - 1 - i, f"  {n:,}", va="center", fontsize=9)
ax.set_title("Customers per RFM segment", fontweight="bold")
plt.tight_layout()
save("S4_segment_customer_count.png")
print("  → charts/S4_segment_customer_count.png")

# E3 — Q3: LTV-driver model
features = [
    "Recency",
    "Frequency",
    "Tenure_days",
    "AvgBasketSize",
    "AvgUnitPrice",
    "DistinctStockCodes",
    "UK_vs_International",
    "CancellationRate",
]
m_q80 = agg["Monetary"].quantile(0.80)
agg["IsTopQuintileM"] = (agg["Monetary"] >= m_q80).astype(int)
X = agg[features].astype(float).values
y_true = agg["IsTopQuintileM"].values

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
clf = HistGradientBoostingClassifier(random_state=42)
auc_scores = cross_val_score(clf, X, y_true, scoring="roc_auc", cv=skf, n_jobs=-1)
roc_auc_mean = float(auc_scores.mean())
roc_auc_std = float(auc_scores.std())

# Out-of-fold predictions for confusion matrix + precision/recall
y_pred = cross_val_predict(clf, X, y_true, cv=skf, n_jobs=-1)
y_prob = cross_val_predict(clf, X, y_true, cv=skf, method="predict_proba", n_jobs=-1)[:, 1]
prec, rec, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", zero_division=0)
cm = confusion_matrix(y_true, y_pred)

# Permutation importance on a held-out 80/20 split for stability
from sklearn.model_selection import train_test_split

X_tr, X_te, y_tr, y_te = train_test_split(
    X, y_true, test_size=0.2, stratify=y_true, random_state=42
)
clf_full = HistGradientBoostingClassifier(random_state=42).fit(X_tr, y_tr)
perm = permutation_importance(
    clf_full, X_te, y_te, n_repeats=10, random_state=42, n_jobs=-1, scoring="roc_auc"
)
imp = pd.DataFrame(
    {"feature": features, "importance": perm.importances_mean, "std": perm.importances_std}
).sort_values("importance", ascending=True)
RFM_FEATURES = {"Recency", "Frequency"}  # spec note: M is the target, F/R dominate by construction

fig, ax = plt.subplots(figsize=(10, 5.5))
colors = [PALETTE[1] if f not in RFM_FEATURES else PALETTE[0] for f in imp["feature"]]
ax.barh(imp["feature"], imp["importance"], xerr=imp["std"], color=colors, alpha=0.92)
ax.set_xlabel("Permutation importance (Δ ROC-AUC)")
ax.set_title(
    f"What predicts top-quintile customer revenue?  (5-fold ROC-AUC = {roc_auc_mean:.3f} ± {roc_auc_std:.3f})",
    fontweight="bold",
)
import matplotlib.patches as mpatches

handles = [
    mpatches.Patch(color=PALETTE[0], label="RFM (Recency / Frequency)"),
    mpatches.Patch(color=PALETTE[1], label="Other behavioural / customer features"),
]
ax.legend(handles=handles, loc="lower right")
plt.tight_layout()
save("E3_q3_ltv_feature_importance.png")
print("  → charts/E3_q3_ltv_feature_importance.png")

# Top-2 NON-RFM features for partial dependence
non_rfm_imp = imp[~imp["feature"].isin(RFM_FEATURES)].sort_values("importance", ascending=False)
top1, top2 = non_rfm_imp["feature"].iloc[0], non_rfm_imp["feature"].iloc[1]
print(f"  Top non-RFM features: 1) {top1}   2) {top2}")

for chart_name, fname in [("S2_ltv_pdp_top1.png", top1), ("S3_ltv_pdp_top2.png", top2)]:
    fig, ax = plt.subplots(figsize=(7, 4.2))
    PartialDependenceDisplay.from_estimator(
        clf_full,
        X_tr,
        features=[features.index(fname)],
        feature_names=features,
        ax=ax,
        line_kw={"color": PALETTE[1], "linewidth": 2},
    )
    ax.set_title(f"Partial dependence — {fname}", fontweight="bold")
    ax.set_xlabel(fname)
    ax.set_ylabel("Partial dependence on top-quintile probability")
    plt.tight_layout()
    save(chart_name)
    print(f"  → charts/{chart_name}")

# E4 — Q4: cohort retention heatmap (masked)
# cohort_month = year-month of first invoice; period_n = months elapsed for each invoice
inv_per_cust = (
    df_with_cust[~df_with_cust["IsCancellation"]]
    .groupby(["CustomerID", df_with_cust[~df_with_cust["IsCancellation"]]["InvoiceDate"].dt.to_period("M")])
    .size()
    .reset_index(name="orders")
    .rename(columns={"InvoiceDate": "InvMonth"})
)
inv_per_cust.columns = ["CustomerID", "InvMonth", "orders"]
first_month = (
    df_with_cust[~df_with_cust["IsCancellation"]]
    .groupby("CustomerID")["InvoiceDate"]
    .min()
    .dt.to_period("M")
    .rename("CohortMonth")
)
inv_per_cust = inv_per_cust.merge(first_month, on="CustomerID")
inv_per_cust["PeriodN"] = (
    (inv_per_cust["InvMonth"].astype("period[M]") - inv_per_cust["CohortMonth"].astype("period[M]"))
    .apply(lambda x: x.n)
)
cohort_size = first_month.value_counts().sort_index().rename("size")
retained = (
    inv_per_cust.groupby(["CohortMonth", "PeriodN"])["CustomerID"]
    .nunique()
    .unstack(fill_value=0)
)
retention = retained.div(cohort_size, axis=0) * 100  # percent

# Mask cells beyond observed window (cohort_idx + period > 11 for the 12-month window)
cohort_index = list(retention.index)
n_periods = retention.shape[1]
mask = np.zeros_like(retention.values, dtype=bool)
for i, c in enumerate(cohort_index):
    for n in range(n_periods):
        # cohort c starting at month i (0..11); we observe up to month 11 (Nov 2011)
        if i + n > 11:
            mask[i, n] = True

fig, ax = plt.subplots(figsize=(11, 6))
sns.heatmap(
    retention,
    annot=True,
    fmt=".0f",
    cmap="Blues",
    mask=mask,
    cbar_kws={"label": "Retention %"},
    linewidths=0.4,
    ax=ax,
    vmin=0,
    vmax=60,
)
ax.set_title(
    "Cohort retention — % of cohort customers active in each month after acquisition",
    fontweight="bold",
)
ax.set_xlabel("Months since acquisition")
ax.set_ylabel("Acquisition cohort")
plt.tight_layout()
save("E4_q4_cohort_heatmap.png")
print("  → charts/E4_q4_cohort_heatmap.png")

# S1 — cohort retention lines (M+1 / M+3 / M+6, clipped to observed)
fig, ax = plt.subplots(figsize=(11, 4.8))
windows = [1, 3, 6]
window_colors = [PALETTE[0], PALETTE[1], PALETTE[3]]
for w, col in zip(windows, window_colors):
    series = []
    for i, c in enumerate(cohort_index):
        if i + w <= 11 and w in retention.columns:
            series.append((str(c), retention.loc[c, w]))
    if series:
        xs = [s[0] for s in series]
        ys = [s[1] for s in series]
        ax.plot(xs, ys, marker="o", lw=2, color=col, label=f"M+{w}")
ax.set_title("Retention at M+1, M+3, M+6 by acquisition cohort", fontweight="bold")
ax.set_xlabel("Acquisition cohort")
ax.set_ylabel("Retention %")
ax.legend()
ax.tick_params(axis="x", rotation=45)
plt.tight_layout()
save("S1_cohort_retention_lines.png")
print("  → charts/S1_cohort_retention_lines.png")

# E5 — Q5: top 3 segments to target for retention campaigns
# Heuristic: combine "revenue at risk" (segment revenue × declining R) with "saveable size".
# At Risk and Cannot Lose Them are the canonical retention targets; About to Sleep is the warning tier.
target_segments = ["At Risk", "Cannot Lose Them", "About to Sleep"]
ts = seg_summary.reindex(
    [s for s in target_segments if s in seg_summary.index]
).copy()
ts["Action"] = [
    "Win-back: discount + personalized re-engagement",
    "VIP rescue: account manager outreach + early-access offers",
    "Awareness nudge: lifecycle email + best-seller promo",
][: len(ts)]

fig, ax = plt.subplots(figsize=(12, 5))
ax.axis("off")
table = ax.table(
    cellText=[
        [
            seg,
            f"{int(row['Customers']):,}",
            f"£{row['Revenue']/1e6:.2f}M",
            f"{row['Revenue_share']:.1f}%",
            row["Action"],
        ]
        for seg, row in ts.iterrows()
    ],
    colLabels=["Segment", "Customers", "Revenue (12 mo)", "Share", "Suggested action"],
    loc="center",
    cellLoc="left",
    colWidths=[0.16, 0.10, 0.13, 0.08, 0.45],
)
table.auto_set_font_size(False)
table.set_fontsize(11)
table.scale(1, 2.0)
# Color header row
for j in range(5):
    cell = table[(0, j)]
    cell.set_facecolor(PALETTE[0])
    cell.set_text_props(color="white", fontweight="bold")
# Color first column (segment name) with accent stripe
for i in range(1, len(ts) + 1):
    table[(i, 0)].set_text_props(fontweight="bold", color=PALETTE[1])
ax.set_title(
    "Top 3 segments to target for retention campaigns",
    fontweight="bold",
    fontsize=14,
    y=0.92,
)
save("E5_q5_target_segments.png")
print("  → charts/E5_q5_target_segments.png")


# ─────────────────────────────────────────────────────────────────────────────
# Persist summary.json
# ─────────────────────────────────────────────────────────────────────────────
top_seg_name = seg_summary.index[0]
top_seg_row = seg_summary.iloc[0]

# Apply the same mask used in E4 so unobserved cohort/period cells are excluded
retention_observed = retention.astype(float).mask(
    pd.DataFrame(mask, index=retention.index, columns=retention.columns)
)
m1_obs = retention_observed[1].dropna() if 1 in retention_observed.columns else pd.Series(dtype=float)
best_cohort = m1_obs.idxmax() if not m1_obs.empty else None
best_m1 = float(m1_obs.max()) if not m1_obs.empty else None
worst_m1 = float(m1_obs.min()) if not m1_obs.empty else None
worst_cohort = m1_obs.idxmin() if not m1_obs.empty else None

summary = {
    "dataset": {
        "raw_rows": ROWS_RAW,
        "cleaned_rows": int(len(df_c)),
        "customers": int(total_customers),
        "analysis_window_start": str(ANALYSIS_START.date()),
        "analysis_window_end": str(ANALYSIS_END.date()),
        "currency": "GBP",
    },
    "cleaning": cleaning_log,
    "kpis": {
        "total_revenue_gbp": round(total_rev_all, 2),
        "total_revenue_customer_attributed_gbp": round(total_rev_cust, 2),
        "aov_gbp": round(aov, 2),
        "total_customers": total_customers,
        "total_invoices_customer_attributed": total_invoices_cust,
        "repeat_purchase_rate": round(repeat_rate, 4),
        "repeat_customer_count": n_repeat,
    },
    "segments": {
        seg: {
            "revenue_gbp": round(float(row["Revenue"]), 2),
            "revenue_share_pct": round(float(row["Revenue_share"]), 2),
            "customers": int(row["Customers"]),
        }
        for seg, row in seg_summary.iterrows()
    },
    "top_segment": {
        "name": top_seg_name,
        "revenue_gbp": round(float(top_seg_row["Revenue"]), 2),
        "revenue_share_pct": round(float(top_seg_row["Revenue_share"]), 2),
        "customer_count": int(top_seg_row["Customers"]),
    },
    "cohort": {
        "best_cohort_month": str(best_cohort) if best_cohort is not None else None,
        "best_m1_retention_pct": round(best_m1, 2) if best_m1 is not None else None,
        "worst_cohort_month": str(worst_cohort) if worst_cohort is not None else None,
        "worst_m1_retention_pct": round(worst_m1, 2) if worst_m1 is not None else None,
        "n_cohorts": int(retention.shape[0]),
    },
    "ltv": {
        "model": "HistGradientBoostingClassifier",
        "target": "top quintile of customer net Monetary",
        "target_threshold_gbp": round(float(m_q80), 2),
        "cv": "5-fold stratified, random_state=42",
        "roc_auc_mean": round(roc_auc_mean, 4),
        "roc_auc_std": round(roc_auc_std, 4),
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1": round(float(f1), 4),
        "confusion_matrix": cm.tolist(),
        "top_3_features": [
            {"name": row["feature"], "importance": round(float(row["importance"]), 5)}
            for _, row in imp.sort_values("importance", ascending=False).head(3).iterrows()
        ],
        "top_2_non_rfm_features": [top1, top2],
    },
    "retention_targets": [
        {
            "segment": seg,
            "customers": int(row["Customers"]),
            "revenue_gbp": round(float(row["Revenue"]), 2),
            "revenue_share_pct": round(float(row["Revenue_share"]), 2),
        }
        for seg, row in ts.iterrows()
    ],
}

with open(PROC / "summary.json", "w") as fh:
    json.dump(summary, fh, indent=2, default=str)
print(f"  → data/processed/summary.json")

print("=" * 70)
print("DONE")
print("=" * 70)
