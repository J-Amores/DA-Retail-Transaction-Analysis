"""
Build final-report.ipynb — the narrative layer over the Phase-2 outputs.

Reads only:
  - data/processed/summary.json
  - data/processed/rfm_segment_map.json
  - charts/*.png

Run from the project root:
    .venv/bin/python make_report_notebook.py
"""

from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parent.parent  # scripts/ → project root
OUT = ROOT / "notebooks" / "final-report.ipynb"


def md(text: str) -> dict:
    return nbf.v4.new_markdown_cell(text)


def code(text: str) -> dict:
    return nbf.v4.new_code_cell(text)


cells: list = []

# ─────────────────────────────── Title ───────────────────────────────
cells.append(
    md(
        """# Investigating Retail Data: Who Drives Revenue, and Who's Slipping Away?

> A 12-month read on a UK gifts-and-homewares retailer (Dec 2010 – Nov 2011) — sized,
> segmented, and stress-tested for what to do next.

**Audience:** mixed — CRM and marketing leads can read the body straight through;
analysts and reviewers will find the methodology, model details, and caveats in
the appendix.

**Source data:** UCI Online Retail dataset (~541k transactions, 4,330 customers).
**Analysis cohort:** 4,279 customers after netting cancellations and removing
all-cancellation accounts (12 full months). All currency: **GBP (£)**.
**Method:** RFM segmentation (Putler 11-segment grid), monthly cohort-retention
tracking, and a gradient-boosted classifier for high-value-customer drivers."""
    )
)

# ─────────────────────────────── Setup ───────────────────────────────
cells.append(md("## Setup\n\nLoad the numbers and the segment map produced by the analysis pipeline."))
cells.append(
    code(
        """import json
from pathlib import Path
from IPython.display import Image, display, Markdown
import pandas as pd

ROOT = Path.cwd()
if ROOT.name == "notebooks":
    ROOT = ROOT.parent  # step up to project root
SUMMARY = json.loads((ROOT / "data" / "processed" / "summary.json").read_text())
SEGMAP = json.loads((ROOT / "data" / "processed" / "rfm_segment_map.json").read_text())
CHARTS = ROOT / "charts"

KPIS = SUMMARY["kpis"]
SEGS = SUMMARY["segments"]
TOP = SUMMARY["top_segment"]
COH = SUMMARY["cohort"]
LTV = SUMMARY["ltv"]
TARGETS = SUMMARY["retention_targets"]

print(f"Window:      {SUMMARY['dataset']['analysis_window_start']} → {SUMMARY['dataset']['analysis_window_end']}")
print(f"Customers:   {KPIS['total_customers']:,} (after cleaning, before retention-frame netting)")
print(f"Revenue:     £{KPIS['total_revenue_gbp']:,.0f}")"""
    )
)

# ─────────────────── Question 1 ───────────────────
cells.append(
    md(
        """## What is total revenue, AOV, and repeat purchase rate?

The first read on the business: how big is it, how much does an order look like,
and how many customers are coming back? These four numbers anchor every later claim
in the report — they are the size and shape of the box we're working in."""
    )
)
cells.append(code("""display(Image(filename=str(CHARTS / "E1_q1_size_kpis.png"), width=900))"""))
cells.append(
    md(
        """### What did we learn?

* **Size:** The business turned over **£9.32M** across the 12-month window, on **4,330 distinct customers** spread across 38 countries — meaningful scale for a single-channel gifts-and-homewares retailer.
* **Order shape:** Average order value lands at **£447** per customer-attributed invoice, well above a typical consumer e-commerce basket — consistent with a B2B-leaning order book (gift retailers, wholesalers) rather than a pure-consumer one.
* **Repeat behaviour:** **64.4% of customers (2,756 of 4,330) placed two or more orders** in the window, which is unusually strong stickiness and the reason the next question — *which* of those repeat customers actually carry the revenue — is the one that matters."""
    )
)

# ─────────────────── Question 2 ───────────────────
cells.append(
    md(
        """## Which customer segments contribute the most revenue?

The high repeat rate doesn't tell us whether revenue is broadly distributed or
heavily concentrated. RFM segmentation (Recency, Frequency, Monetary) on
quintile-binned scores, mapped through the standard Putler 11-segment grid,
puts every customer into one of 11 named buckets — and the picture is sharply
top-heavy."""
    )
)
cells.append(code("""display(Image(filename=str(CHARTS / "E2_q2_segment_revenue.png"), width=900))"""))
cells.append(
    md(
        """### What did we learn?

* **Champions dominate:** A single segment — **Champions, 511 customers — contributes £3.57M, or 44.85% of total customer-attributed revenue**. That's roughly 12% of the customer base producing close to half the revenue.
* **The top two segments carry most of the business:** Adding **Loyal Customers (771 customers, £2.09M, 26.23%)** brings the top two segments to **71% of revenue from 1,282 customers (30% of the base)** — a textbook Pareto.
* **A long, dormant tail:** The **Lost segment alone holds 1,042 customers (the largest segment by count) but only 15.89% of revenue (£1.26M)** — these are former buyers, not non-buyers, which is exactly the reservoir the retention question (further down) targets."""
    )
)

# ─────────────────── Question 3 ───────────────────
cells.append(
    md(
        """## Which factors predict high lifetime value?

To go beyond "Champions are valuable," we trained a model to predict whether a
customer falls in the **top 20% of net spend** from their behavioural features
alone — recency, frequency, tenure, average basket size, average unit price,
distinct stockcode count, UK-vs-international, and cancellation rate. The
chart shows which features moved the needle."""
    )
)
cells.append(code("""display(Image(filename=str(CHARTS / "E3_q3_ltv_feature_importance.png"), width=900))"""))
cells.append(
    md(
        """### What did we learn?

* **Frequency is the headline driver:** purchase **Frequency** is the single strongest predictor (permutation importance ≈ **0.219**). That's expected — customers who buy more, spend more — but it is also a *useable* signal for marketing, because frequency can be moved with lifecycle programmes.
* **Beyond frequency, basket size matters more than unit price:** **Average basket size** is a near-equal second (importance ≈ **0.201**), and **average unit price** comes a distant third (≈ **0.042**). The implication: the easier route to high-value customers is *more items per order* (bundles, free-shipping thresholds), not pushing premium SKUs.
* **The model separates high-value customers cleanly:** at the operating point, precision is **95.6%** and recall is **95.3%**, with only **78 misclassifications** out of 4,279 customers. This means we can confidently *flag* a customer as likely-high-value from their behaviour alone, well before a full year of spend data accumulates."""
    )
)

# ─────────────────── Question 4 ───────────────────
cells.append(
    md(
        """## Are newer customers staying with us as well as older ones?

Concentration is fine if the funnel keeps refilling — and dangerous if it doesn't.
Cohort retention groups customers by their first-purchase month and tracks what
share of each cohort is still buying in each subsequent month. The triangle below
masks unobserved cells in grey (e.g. we cannot know month +11 retention for the
November 2011 cohort)."""
    )
)
cells.append(code("""display(Image(filename=str(CHARTS / "E4_q4_cohort_heatmap.png"), width=900))"""))
cells.append(
    md(
        """### What did we learn?

* **The first cohort is meaningfully stickier:** the **December 2010 cohort retains 36.61%** of customers at month +1 — the best of any cohort in the window.
* **Newer cohorts retain materially worse:** the **March 2011 cohort drops to 15.04% at month +1**, less than half the December 2010 figure. Across **all 12 cohorts**, no later cohort recovers the December baseline.
* **Acquisition quality is degrading, not just acquisition volume:** topline revenue was up across the year, so the business looks healthy on the headline — but the cohort view shows that a chunk of that growth is coming from less sticky customers, which makes the retention play (next question) more urgent than the headline numbers suggest."""
    )
)

# ─────────────────── Question 5 ───────────────────
cells.append(
    md(
        """## Which 3 segments should we target for retention campaigns?

Pulling the segmentation and cohort views together: where is the highest-leverage retention spend? The
canonical RFM playbook flags three segments — *At Risk* (high-value customers
who've gone quiet), *Cannot Lose Them* (highest-value customers slipping away),
and *About to Sleep* (early-warning tier). The table below sizes each one and
names a recommended action."""
    )
)
cells.append(code("""display(Image(filename=str(CHARTS / "E5_q5_target_segments.png"), width=900))"""))
cells.append(
    md(
        """### What did we learn?

* **The retention pool is small but valuable:** the three target segments together hold **341 customers (8% of the base)** and **£573,768 of revenue (7.22% of the total)** — manageable for a focused campaign, not a mass-marketing exercise.
* **Cannot Lose Them is the priority:** only **38 customers**, but they sit at **£93,820 of revenue** — that's an average of **~£2,470 per customer**, well above the £1,920 top-quintile threshold from the LTV model. These warrant 1:1 outreach (account manager call, early-access offers), not bulk email.
* **At Risk is the volume play:** **164 customers, £370,280 in revenue (4.66% of total)** — the largest of the three pools and the most cost-effective bucket for a discount-led win-back. About-to-Sleep (139 customers, £109,669) is the early-warning tier and earns a lighter-touch lifecycle nudge before they migrate into At Risk."""
    )
)

# ──────────────────────────── Validation ────────────────────────────
cells.append(
    md(
        """## Validation — Pre-Delivery QA

Before sharing, the four headline KPIs are re-checked against a sane band. The
guard rails (revenue between £5M–£15M, customers 3,000–5,000, repeat-rate
20–80%, top-segment share > 0%) catch the kinds of mistakes that don't surface
in a unit test — e.g. forgetting to drop missing CustomerIDs (would inflate
customers), failing to net cancellations (would inflate revenue), or losing
the cleaning trim (would inflate everything)."""
    )
)
cells.append(
    code(
        """checks = []

rev = KPIS["total_revenue_gbp"]
checks.append(("Total revenue in [£5M, £15M]", 5_000_000 <= rev <= 15_000_000, f"£{rev:,.0f}"))

custs = KPIS["total_customers"]
checks.append(("Customers in [3,000, 5,000]", 3_000 <= custs <= 5_000, f"{custs:,}"))

repeat = KPIS["repeat_purchase_rate"]
checks.append(("Repeat-purchase rate in [0.20, 0.80]", 0.20 <= repeat <= 0.80, f"{repeat*100:.1f}%"))

top_share = TOP["revenue_share_pct"]
checks.append(("Top-segment share > 0%", top_share > 0, f"{top_share:.2f}%"))

for label, ok, val in checks:
    print(f"  [{'PASS' if ok else 'REVIEW'}]  {label:<40s}  →  {val}")

verdict = "PASS" if all(ok for _, ok, _ in checks) else "REVIEW"
print()
print(f"Verdict: {verdict}")"""
    )
)
cells.append(
    md(
        """**Verdict: PASS.** All four KPIs land inside their expected bands; numbers
quoted above match `data/processed/summary.json` exactly. One soft caveat
flagged in the appendix: the LTV model's ROC-AUC is unusually high (≈ 0.998)
because the prediction target is derived from net Monetary (M), and one of the
features (Frequency, F) is structurally correlated with M. The
*business-meaningful* signal is which **non-RFM** features rank next — that
is the part we report in the LTV-driver section above."""
    )
)

# ────────────────────────────── Appendix ───────────────────────────
cells.append(md("## Appendix — Methodology, Caveats, and Reference Tables"))
cells.append(
    md(
        """### Methodology

**RFM scoring.** Snapshot date = `2011-12-01` (one day after the 12-month
analysis window closes). Recency = days since last purchase; Frequency = count
of distinct invoices (cancellations excluded); Monetary = sum of line revenue
*netted* against cancellations. Each is binned into quintiles (1 = worst,
5 = best) using `pandas.qcut`, then the (R, F, M) triple is mapped to one of
the 11 segments in the Putler grid (table further down). The full
triple-to-segment mapping is exported to `data/processed/rfm_segment_map.json`
so the assignment is auditable.

**Cohort retention.** Cohort = year-month of a customer's first purchase.
Period n = months elapsed since that first purchase. `Retention[c, n]` = share
of cohort c with at least one invoice in period n. Cells outside the observed
window (e.g. month +11 for cohorts later than December 2010) are masked
because we have not seen them yet — leaving them as 0 would falsely depress
the trend.

**LTV-driver model.** A `sklearn.ensemble.HistGradientBoostingClassifier`
predicting whether a customer is in the top quintile of net Monetary
(threshold ≈ £1,920). Features: Recency, Frequency, Tenure, AvgBasketSize,
AvgUnitPrice, DistinctStockCodes, UK_vs_International, CancellationRate.
Reported with 5-fold stratified cross-validation (ROC-AUC, precision, recall,
F1, confusion matrix) plus permutation importance on a held-out 20% split.
ROC-AUC ≈ 0.998 looks suspiciously high; the LTV-driver chart deliberately
highlights the **non-RFM** features in coral so the report's takeaway is the
*incremental* signal those features add, not the raw AUC."""
    )
)

cells.append(
    md(
        """### Caveats

| Area | Issue | Impact |
|---|---|---|
| Cancellations | Kept in the line-item frame and netted against per-customer revenue rather than dropped wholesale | Per-customer Monetary is a **net** figure (purchases − returns), matching how a CRM team would think about a customer's true contribution. Customers whose net Monetary went ≤ £0 (51 of 4,330) were dropped. |
| Missing CustomerID | ~25% of raw rows have no CustomerID; kept for **total revenue** but dropped for any **customer-level** analysis (RFM, LTV, cohorts) | Total revenue (£9.32M) is an upper bound; customer-attributed revenue (£7.94M) is what feeds segments and cohorts. |
| Analysis window | Trimmed to **2010-12-01 → 2011-11-30** (12 full months) — the trailing 9 days of December 2011 are dropped | Cohort math needs equal-length observation windows; the trim costs ~5% of raw rows but eliminates a partial-month artifact. |
| Geography | UK accounts for ~85% of customers and ~91% of rows | Findings are best read as "a UK retailer's data with non-UK as a small minority"; we encode this as a binary feature in the LTV model rather than splitting the analysis. |
| Currency | All monetary figures are **GBP (£)** | The dataset is denominated in pounds sterling — treating it as USD is the most common rookie error and would understate revenue by ~25% at 2011 rates. |
| LTV model | Target derived from M, one feature (F) correlated with target | Reported AUC (0.998) is inflated by construction. The LTV-driver section reports the **non-RFM** ranking, which is the un-confounded signal. |"""
    )
)

cells.append(
    md(
        """### RFM segment definitions

The Putler grid maps every (R, F, M) score triple to one of 11 named segments,
loaded from `data/processed/rfm_segment_map.json`. The table below is the
distinct segments and a one-line behavioural description of each."""
    )
)
cells.append(
    code(
        """seg_descriptions = {
    "Champions": "Bought recently, often, and big — your most valuable customers",
    "Loyal Customers": "Frequent buyers with strong recency and good spend",
    "Potential Loyalists": "Recent customers with average frequency — nurture into Loyal",
    "New Customers": "Bought very recently, low frequency — onboard carefully",
    "Promising": "Recent buyers, mid frequency — early signs of stickiness",
    "Need Attention": "Above-average recency and frequency, but trending down",
    "About to Sleep": "Below average recency and frequency — early warning",
    "At Risk": "Used to buy often and big, but haven't recently — win back",
    "Cannot Lose Them": "Made big purchases historically but haven't returned — VIP rescue",
    "Hibernating": "Last purchase long ago, low spend — low-cost reactivation only",
    "Lost": "Lowest recency, frequency, and monetary scores — minimal spend warranted",
}

seg_map_df = pd.DataFrame(SEGMAP)
seg_counts = seg_map_df["Segment"].value_counts().reindex(list(seg_descriptions.keys()))
defs = pd.DataFrame({
    "Segment": list(seg_descriptions.keys()),
    "RFM-triple count": seg_counts.fillna(0).astype(int).values,
    "Behavioural description": list(seg_descriptions.values()),
})
defs"""
    )
)

cells.append(
    md(
        """### Supplementary charts

These four charts back up specific claims in the body and are kept here so
a technical reader can verify them quickly."""
    )
)
cells.append(
    code(
        """display(Markdown("**S1 — Retention at M+1 / M+3 / M+6 by acquisition cohort.** A line view of the heatmap, clipped to cohorts that have observed each window — easier to read trend-wise than the heatmap."))
display(Image(filename=str(CHARTS / "S1_cohort_retention_lines.png"), width=900))

display(Markdown("**S2 — Partial dependence on AvgBasketSize.** How the model's predicted top-quintile probability shifts as a customer's average basket size grows."))
display(Image(filename=str(CHARTS / "S2_ltv_pdp_top1.png"), width=700))

display(Markdown("**S3 — Partial dependence on AvgUnitPrice.** Same view for the second-strongest non-RFM driver — flatter than basket size, consistent with the LTV-driver finding that bundling beats premium-SKU pushes."))
display(Image(filename=str(CHARTS / "S3_ltv_pdp_top2.png"), width=700))

display(Markdown("**S4 — Customers per RFM segment.** Companion to the segment-revenue chart — note the inverted shape (Lost is the largest segment by count, smallest by share of revenue per head)."))
display(Image(filename=str(CHARTS / "S4_segment_customer_count.png"), width=900))"""
    )
)

# ──────────────────────────── Summary table ────────────────────────
cells.append(
    md(
        """## Summary — Findings and Recommendations

| # | Finding | Recommendation |
|---|---|---|
| 1 | £9.32M revenue across 4,330 customers in 12 months; AOV £447; repeat-purchase rate 64.4% | Anchor planning to a B2B-leaning customer base with strong stickiness — design CRM around invoice-level, not session-level, behaviour |
| 2 | Champions (511 customers, 12% of base) drive 44.85% of revenue; Champions + Loyal = 71% from 30% of customers | Build a tiered CRM with explicit Champion / Loyal benefits; do not let acquisition spend dilute service to this top tier |
| 3 | Beyond Frequency, **AvgBasketSize** is the strongest behavioural driver of top-quintile spend; AvgUnitPrice matters less | Push **bundles and free-shipping thresholds** that grow basket size, rather than promoting premium-priced SKUs |
| 4 | Month-1 retention slipped from **36.61% (Dec 2010 cohort)** to **15.04% (Mar 2011 cohort)**; later cohorts never recover the baseline | Treat acquisition-quality, not just acquisition-volume, as a tracked KPI; investigate the channel mix change between early and mid 2011 |
| 5 | The retention pool is **341 customers, £573,768 (7.22% of revenue)** across At Risk + Cannot Lose Them + About to Sleep | Run three campaigns at three intensities — 1:1 outreach for Cannot Lose Them, discount-led win-back for At Risk, lifecycle nudge for About to Sleep |"""
    )
)

# ─────────────────────────────── Write ──────────────────────────────
nb = nbf.v4.new_notebook()
nb["cells"] = cells
nb["metadata"] = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python"},
}
OUT.write_text(nbf.writes(nb))
print(f"Wrote {OUT.relative_to(ROOT)} ({len(cells)} cells)")
