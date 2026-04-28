"""
Assemble analysis.ipynb from build_pipeline.py.

The pipeline is the source of truth. This script slices it into logical
chunks at the existing section markers, wraps each with a 1–2 sentence
markdown framing cell, and writes a runnable Jupyter notebook.

Run from the project root:
    .venv/bin/python make_notebook.py
"""

from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "build_pipeline.py"
OUT = ROOT / "analysis.ipynb"

src_lines = SRC.read_text().splitlines()


def chunk(start: int, end: int) -> str:
    """1-indexed, inclusive line range from build_pipeline.py."""
    body = "\n".join(src_lines[start - 1 : end]).rstrip()
    return body


# Patch the BASE-path resolution for the notebook context
# (build_pipeline.py uses __file__, which doesn't exist in a notebook)
SETUP = chunk(1, 98).replace(
    "BASE = Path(__file__).resolve().parent",
    'BASE = Path.cwd()',
)


def md(text: str) -> dict:
    return nbf.v4.new_markdown_cell(text)


def code(text: str) -> dict:
    return nbf.v4.new_code_cell(text)


cells: list = []

# ─────────────────────────────── Title ───────────────────────────────
cells.append(
    md(
        """# Investigating Retail Data: Who Drives Revenue, and Who's Slipping Away?

End-to-end analysis of the UCI Online Retail dataset — a UK-based gifts and
homewares retailer, ~541k transactions over Dec 2010 – Dec 2011.

The notebook follows a five-stage pipeline:

| Stage | Purpose | Outputs |
|---|---|---|
| **A — Explore** | Load the raw `.xlsx`, sanity-check shape and quality | `A1`, `A2` charts |
| **B — Profile** | Distributions, seasonality, and quality flags before any cleaning | `B1`–`B5` charts |
| **C — Clean** | Apply the locked cleaning policy; every rule logs a before/after row count | cleaning log |
| **D — Shape** | Export cleaned line items and build a per-customer feature frame for the LTV model | `online_retail_clean.csv`, `online_retail_analysis.csv`, `rfm_segment_map.json` |
| **E — Analyze** | Answer the five reader-facing questions: revenue / segments / LTV drivers / cohorts / targets | `E1`–`E5` + `S1`–`S4` charts, `summary.json` |

The pipeline is also packaged as a single script (`build_pipeline.py`) for
headless re-runs. Currency throughout: **GBP (£)**."""
    )
)

# ─────────────────────────────── Setup ───────────────────────────────
cells.append(
    md(
        """## Setup

Imports, paths, the project palette, and small plotting helpers.
The Putler 11-segment grid (`assign_segment`) is defined here so it stays
auditable alongside the rest of the constants."""
    )
)
cells.append(code(SETUP))

# ─────────────────────────────── Stage A ─────────────────────────────
cells.append(
    md(
        """## Stage A — Explore

Load the raw spreadsheet and get a first read on shape, cardinalities, and the
obvious data-quality flags. Nothing is cleaned yet — Stage A's job is just to
*look*."""
    )
)
cells.append(
    md(
        """### A1 — Data overview

A four-panel snapshot: monthly transaction volume, top countries, headline
cardinalities, and counts of the data-quality flags that Stage C will address."""
    )
)
cells.append(code(chunk(103, 184)))

cells.append(
    md(
        """### A2 — Missingness

Per-column null counts. Two columns dominate: `CustomerID` (~25%) and
`Description` (~0.3%). The CustomerID gap is the load-bearing decision in
Stage C — those rows are kept for total revenue but dropped for any
customer-level analysis (RFM, LTV, cohorts)."""
    )
)
cells.append(code(chunk(186, 198)))

# ─────────────────────────────── Stage B ─────────────────────────────
cells.append(
    md(
        """## Stage B — Profile

With the raw frame loaded, Stage B looks at distributions, seasonality, and
the relative size of returns vs. purchases. These charts inform the cleaning
choices in Stage C — they are not the final reader-facing visuals."""
    )
)
cells.append(
    md(
        """### B1 — Monthly net revenue

Headline seasonality on the *raw* data: a clear pre-Christmas ramp through
Q4 2011, with a tail of December 2011 that we will trim in Stage C
(only the first 9 days of Dec 2011 are observed, which corrupts cohort math)."""
    )
)
cells.append(code(chunk(208, 223)))

cells.append(
    md(
        """### B2 — Country distribution

The dataset is UK-dominated (~91% of rows, ~85% of customers). All other
countries are tracked but treated as a single `International` segment in the
LTV-driver feature set."""
    )
)
cells.append(code(chunk(225, 239)))

cells.append(
    md(
        """### B3 — Quantity and unit-price distributions

Both are heavy-tailed; log–log axes make the long tail (a few very large
quantities and a handful of luxury-priced items) legible alongside the bulk
of the data."""
    )
)
cells.append(code(chunk(241, 260)))

cells.append(
    md(
        """### B4 — Invoice-size distribution

Lines per invoice and total £ per invoice. Used to validate the AOV
calculation in Stage E (clipping at £2 000 for visibility — the long tail
runs much higher)."""
    )
)
cells.append(code(chunk(262, 281)))

cells.append(
    md(
        """### B5 — Returns vs purchases over time

Returns / cancellations as a share of monthly volume. They are small in
absolute terms but concentrated in a handful of large credits — which is
why Stage C *nets* them rather than dropping them."""
    )
)
cells.append(code(chunk(283, 300)))

# ─────────────────────────────── Stage C ─────────────────────────────
cells.append(
    md(
        """## Stage C — Clean

Apply the locked cleaning policy from the spec (§3). Every rule prints a
`before → after` row count so the policy is auditable, and the same counts
are persisted to `summary.json` so the report can quote them directly.

Two frames carry forward:

- `df_c` — cleaned line items (kept for total revenue, includes
  missing-CustomerID rows).
- `df_with_cust` — customer-attributed subset (used for RFM, LTV, cohorts)."""
    )
)
cells.append(code(chunk(310, 366)))

# ─────────────────────────────── Stage D ─────────────────────────────
cells.append(
    md(
        """## Stage D — Shape & Export

Persist the cleaned line items, then build a per-customer feature frame
that feeds both the RFM scoring and the LTV-driver model. This stage is
where the dataset transitions from *transactions* to *customers*."""
    )
)
cells.append(
    md(
        """### D.1 — Export cleaned line items

Saves `online_retail_clean.csv` (~509k rows). Used downstream by the
report notebook and as the input for any future product-level work."""
    )
)
cells.append(code(chunk(376, 392)))

cells.append(
    md(
        """### D.2 — Per-customer feature frame

Aggregate to one row per customer with: Recency / Frequency / Monetary
(NET of cancellations), tenure, average basket size, average unit price,
distinct stockcode count, cancellation rate, and a UK-vs-International
binary. Customers with net Monetary ≤ 0 (all-cancellation cases) are
dropped here — they would corrupt the LTV target."""
    )
)
cells.append(code(chunk(395, 433)))

cells.append(
    md(
        """### D.3 — RFM scoring + Putler segment assignment

Quintile bins (1 = worst, 5 = best) on each of R, F, M independently. The
(R, F, M) score triple maps to one of 11 named segments via the standard
Putler grid. The full mapping table is exported as `rfm_segment_map.json`
so the assignment is auditable."""
    )
)
cells.append(code(chunk(436, 482)))

# ─────────────────────────────── Stage E ─────────────────────────────
cells.append(
    md(
        """## Stage E — Analyze

Answer the five reader-facing questions. Each `E#` chart is the canonical
visual for one question; `S#` charts are supplementary (used in the
report's data-notes section).

The five questions:

1. What is total revenue, AOV, and repeat purchase rate?
2. Which customer segments contribute the most revenue?
3. Which factors predict high lifetime value?
4. Are newer customers staying with us as well as older ones?
5. Which 3 segments should we target for retention campaigns?"""
    )
)

cells.append(
    md(
        """### E1 — Headline KPIs

Total revenue, active customer count, average order value, and
repeat-purchase rate. Total revenue uses the full cleaned frame
(includes missing-CustomerID rows); AOV and repeat-rate are
customer-attributed."""
    )
)
cells.append(code(chunk(493, 523)))

cells.append(
    md(
        """### E2 — Revenue by RFM segment

Segment revenue contribution, with the top three segments highlighted in
coral. The shape of this chart — a steep fall-off after the leading
segment — drives the central finding."""
    )
)
cells.append(code(chunk(526, 549)))

cells.append(
    md(
        """### S4 — Customers per segment (companion to E2)

Pairs with E2 in the report. The size of the leading segment in customer
*count* is much smaller than its share of revenue — exactly what you'd
expect, and the rationale for treating these customers as a high-value
retention target."""
    )
)
cells.append(code(chunk(552, 563)))

cells.append(
    md(
        """### E3 — LTV-driver model

A `HistGradientBoostingClassifier` trained to predict whether a customer
falls in the top quintile of net Monetary. Reported with 5-fold stratified
CV (ROC-AUC, precision, recall, F1, confusion matrix) and permutation
importance on a held-out 20% split.

**Caveat (also flagged in the report appendix):** because the target is
derived from M, the RFM features dominate by construction. The interesting
signal is what the *non-RFM* behavioural features add on top — those are
highlighted in coral on the chart."""
    )
)
cells.append(code(chunk(566, 625)))

cells.append(
    md(
        """### S2 / S3 — Partial dependence on the top-2 non-RFM features

Shows how the model's predicted top-quintile probability moves with each
of the two strongest non-RFM features. Used in the report's data-notes
section to make the "what predicts high value, beyond RFM?" answer concrete."""
    )
)
cells.append(code(chunk(627, 647)))

cells.append(
    md(
        """### E4 — Cohort retention heatmap

Cohort = year-month of first invoice. Period n = months elapsed.
`retention[c, n]` = share of cohort `c` with ≥1 invoice in period `n`.
Cells beyond the observed window (e.g. month +11 for the November 2011
cohort) are masked to grey so the eye does not read 0% retention where
the truth is "we haven't observed it yet"."""
    )
)
cells.append(code(chunk(651, 710)))

cells.append(
    md(
        """### S1 — Retention at M+1 / M+3 / M+6 by cohort

A line view of the same cohort data, clipped to cohorts that have observed
the corresponding window. Easier to read trend-wise than the heatmap, and
used as the companion chart in the report."""
    )
)
cells.append(code(chunk(713, 732)))

cells.append(
    md(
        """### E5 — Top 3 segments to target for retention

Combines the segment table from E2 with a recommended action per segment.
*At Risk* and *Cannot Lose Them* are the canonical retention targets;
*About to Sleep* is the early-warning tier."""
    )
)
cells.append(code(chunk(737, 783)))

# ──────────────────────────── Persist summary ────────────────────────
cells.append(
    md(
        """## Persist `summary.json`

Final step: serialise the cleaning log, KPIs, segment table, top segment,
cohort metrics, LTV model results, and retention targets to
`data/processed/summary.json`. This is the single source of numbers the
report notebook (`final-report.ipynb`) and HTML report (`index.html`) read
from — the body of the report quotes these values directly."""
    )
)
cells.append(code(chunk(789, 872)))

# ─────────────────────────────── Write ──────────────────────────────
nb = nbf.v4.new_notebook()
nb["cells"] = cells
nb["metadata"] = {
    "kernelspec": {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    },
    "language_info": {"name": "python"},
}

OUT.write_text(nbf.writes(nb))
print(f"Wrote {OUT.relative_to(ROOT)} ({len(cells)} cells)")
