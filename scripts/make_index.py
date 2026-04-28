"""
Build index.html — the editorial HTML report.

Starts from the editorial-report skill template, swaps the palette tokens,
adds a small `.learnings` component, and replaces the placeholder section
with project-specific content. Reads numbers from summary.json so the bar
chart and KPI values stay in sync with the analysis.

Run from project root:
    .venv/bin/python make_index.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # scripts/ → project root
TEMPLATE = Path("/Users/jamores/.claude/skills/editorial-report/assets/template.html")
SUMMARY = json.loads((ROOT / "data" / "processed" / "summary.json").read_text())
OUT = ROOT / "index.html"

KPIS = SUMMARY["kpis"]
SEGS = SUMMARY["segments"]
TOP = SUMMARY["top_segment"]

# ─── Build the bar-chart block from segment data (top 6 by revenue) ───
top_segs = sorted(
    SEGS.items(), key=lambda kv: kv[1]["revenue_share_pct"], reverse=True
)[:6]
max_share = top_segs[0][1]["revenue_share_pct"]


def bar_class(share):
    if share >= 30:
        return ""  # default coral
    if share >= 15:
        return "amber"
    if share >= 5:
        return ""  # default
    return ""


bar_items = []
for name, row in top_segs:
    share = row["revenue_share_pct"]
    width = round(share / max_share * 100, 1)  # scale to 100% of track
    fill_class = "amber" if share < 15 else ""
    bar_items.append(
        f"""      <div class="bar-item">
        <span class="bar-label">{name}</span>
        <div class="bar-track"><div class="bar-fill {fill_class}".strip() style="--w: {width}%"></div></div>
        <span class="bar-value">{share:.1f}%</span>
      </div>"""
    )
BAR_CHART = "\n".join(bar_items).replace('class="bar-fill ".strip()', 'class="bar-fill"').replace(
    'class="bar-fill amber".strip()', 'class="bar-fill amber"'
)

# ─── Page constants ───
TITLE = "Investigating Retail Data: Who Drives Revenue, and Who's Slipping Away?"
EYEBROW = "ONLINE-RETAIL · 12-MONTH SEGMENTATION & RETENTION READ · DEC 2010 – NOV 2011"
SUBTITLE_LINE = "12-month segmentation & retention read"

# ─── Read the template, swap palette + accent + nav + sections ───
template = TEMPLATE.read_text()

# Swap accent-pop in light mode → coral (project accent)
template = template.replace("--accent-pop:   #2563eb;", "--accent-pop:   #E07856;")
# Swap accent-pop in dark mode → lighter coral so it reads on dark bg
template = template.replace("--accent-pop:   #60a5fa;", "--accent-pop:   #F4A788;")
# Title
template = template.replace("<title>{{REPORT_TITLE}}</title>", f"<title>{TITLE}</title>")

# Add a small CSS rule for `.learnings` (the 3-bullet "what did we learn?" block)
LEARNINGS_CSS = """
    /* ── Learnings list (3 bullets per section) ─── */
    .learnings { margin: 28px 0 8px; max-width: 760px; padding-left: 0; list-style: none; }
    .learnings li {
      position: relative; padding: 10px 0 10px 28px;
      border-top: 1px solid var(--border);
      font-size: 0.85rem; color: var(--text); line-height: 1.6;
    }
    .learnings li:last-child { border-bottom: 1px solid var(--border); }
    .learnings li::before {
      content: ""; position: absolute; left: 0; top: 18px;
      width: 14px; height: 2px; background: var(--accent-pop);
    }
    .learnings li strong { font-weight: 600; color: var(--text); }
    .learnings li .lbl {
      display: inline-block; font-family: var(--font-mono);
      font-size: 0.62rem; letter-spacing: 0.1em; text-transform: uppercase;
      color: var(--accent-pop); margin-right: 8px; vertical-align: 0.05em;
    }
"""
template = template.replace(
    "    /* ── Progress Bar (reading progress) ─────────── */",
    LEARNINGS_CSS + "\n    /* ── Progress Bar (reading progress) ─────────── */",
)

# ─── Replace navbar ───
new_nav = """<nav>
  <a href="#cover">Cover</a>
  <a href="#revenue">Revenue</a>
  <a href="#segments">Segments</a>
  <a href="#drivers">Drivers</a>
  <a href="#cohorts">Cohorts</a>
  <a href="#targets">Targets</a>
  <a href="#conclusion">Conclusion</a>
  <a href="#notes">Notes</a>
  <button class="theme-toggle" onclick="toggleTheme()">◐</button>
</nav>"""
old_nav_start = template.index("<nav>")
old_nav_end = template.index("</nav>") + len("</nav>")
template = template[:old_nav_start] + new_nav + template[old_nav_end:]

# ─── Replace the cover ───
new_cover = f"""<section id="cover">
  <div class="cover-inner">
    <div class="cover-eyebrow">{EYEBROW}</div>
    <hr class="cover-divider" />
    <h1 class="reveal">Two segments drive 71&#37; of revenue &mdash; and newer cohorts are slipping away faster than they used to.</h1>
    <div class="cover-intro reveal" data-delay="1">
      <p>This report reads the UCI Online Retail dataset &mdash; <strong>~541,000 transactions from a UK gifts-and-homewares retailer over 12 months</strong> &mdash; and asks five blunt questions about who is paying the bills, who is leaving, and where the next pound of marketing spend should go.</p>
      <p>The headline read is healthy: <strong>&pound;9.32M of revenue across 4,330 customers</strong>, with two-thirds of customers placing more than one order. The structural read is more interesting: revenue is heavily concentrated in two top segments, and the cohorts acquired after the first three months of 2011 retain at less than half the rate of the original cohort.</p>
      <div class="cover-callout">
        <strong>The central finding.</strong> <em>Champions</em> and <em>Loyal Customers</em> &mdash; <strong>1,282 customers, 30&#37; of the base &mdash; account for 71&#37; of revenue</strong>. Meanwhile, month-1 retention has slipped from <strong>36.6&#37; in the December 2010 cohort to 15.0&#37; by March 2011</strong>, and never recovers. The highest-leverage move is targeted retention spend on the 341 customers in <em>At Risk</em>, <em>Cannot Lose Them</em>, and <em>About to Sleep</em> &mdash; a small pool, but &pound;574k of revenue at stake.
      </div>
    </div>
    <div class="kpi-strip reveal" data-delay="2">
      <div class="kpi-item">
        <span class="kpi-label">Total revenue (12 mo)</span>
        <span class="kpi-val" data-count-to="9.32">&pound;9.32M</span>
        <span class="kpi-note">All sales, Dec 2010 &ndash; Nov 2011</span>
      </div>
      <div class="kpi-item">
        <span class="kpi-label">Active customers</span>
        <span class="kpi-val" data-count-to="{KPIS['total_customers']}">{KPIS['total_customers']:,}</span>
        <span class="kpi-note">Distinct CustomerIDs</span>
      </div>
      <div class="kpi-item">
        <span class="kpi-label">Repeat-purchase rate</span>
        <span class="kpi-val" data-count-to="64.4">64.4&#37;</span>
        <span class="kpi-note">{SUMMARY['kpis']['repeat_customer_count']:,} customers with &ge; 2 orders</span>
      </div>
      <div class="kpi-item">
        <span class="kpi-label">Top-segment revenue share</span>
        <span class="kpi-val" data-count-to="{TOP['revenue_share_pct']}">{TOP['revenue_share_pct']:.1f}&#37;</span>
        <span class="kpi-note">Champions &mdash; {TOP['customer_count']} customers</span>
      </div>
    </div>
  </div>
</section>"""

cover_start = template.index('<section id="cover">')
cover_end = template.index("</section>", cover_start) + len("</section>")
template = template[:cover_start] + new_cover + template[cover_end:]

# ─── Replace the placeholder section block with our 5 sections ───
sec_start = template.index('<!-- ══ SECTION TEMPLATE')
sec_end = template.index('<!-- ══ CONCLUSION')

# Build 5 sections
SECTIONS = []

# ─── Section 1: revenue / AOV / repeat ───
SECTIONS.append(f"""<section class="section" id="revenue">
  <div class="container">
    <div class="section-num reveal">01 &nbsp;&middot;&nbsp; Revenue &amp; Reach</div>
    <h2 class="reveal" data-delay="1">What is total revenue, AOV, and repeat purchase rate?</h2>
    <div class="section-deck reveal" data-delay="2">Sizing the box: how big is the business, what does an order look like, and how many customers come back?</div>

    <p class="body reveal">The first read on the business is unusually strong on stickiness. The retailer turned over &pound;9.32M across 12 months on 4,330 distinct customers spread across 38 countries &mdash; meaningful scale for a single-channel gifts-and-homewares operator.</p>
    <p class="body reveal">Order shape and repeat behaviour both signal a B2B-leaning customer base: an AOV of <strong>&pound;447</strong> per invoice (well above a typical consumer e-commerce basket) and a <strong>64.4&#37; repeat-purchase rate</strong>. Together those numbers say "the customers we already have matter more than new acquisition" &mdash; and the next section makes that case quantitatively.</p>

    <div class="chart-wrap reveal">
      <img src="charts/E1_q1_size_kpis.png" alt="Headline KPIs: total revenue, customers, AOV, and repeat-purchase rate" />
      <div class="chart-caption"><strong>Headline KPIs</strong> &nbsp;|&nbsp; Total revenue, active customers, AOV, and repeat-purchase rate, Dec 2010 &ndash; Nov 2011.</div>
    </div>

    <ul class="learnings reveal">
      <li><span class="lbl">Size</span> &pound;9.32M turnover across <strong>4,330 distinct customers</strong> in 38 countries &mdash; meaningful scale for a single-channel gifts retailer.</li>
      <li><span class="lbl">Order shape</span> AOV of <strong>&pound;447</strong> per invoice is well above a typical consumer basket &mdash; consistent with a B2B-leaning order book.</li>
      <li><span class="lbl">Repeat behaviour</span> <strong>64.4&#37; of customers (2,756 of 4,330) placed two or more orders</strong> &mdash; unusually strong stickiness, and the reason segment concentration is the next question.</li>
    </ul>

    <div class="pull-quote reveal">
      <p>Two-thirds of customers come back. <strong>The next question is whether those repeat customers are evenly distributed &mdash; or whether a small group is doing most of the work.</strong></p>
    </div>
    <div class="bridge reveal">Next: which customer segments actually contribute the revenue.</div>
  </div>
</section>""")

# ─── Section 2: segments ───
SECTIONS.append(f"""<section class="section alt" id="segments">
  <div class="container">
    <div class="section-num reveal">02 &nbsp;&middot;&nbsp; Segment Concentration</div>
    <h2 class="reveal" data-delay="1">Which customer segments contribute the most revenue?</h2>
    <div class="section-deck reveal" data-delay="2">Splitting customers into 11 named segments by their recency, frequency, and spend &mdash; then asking how revenue is distributed.</div>

    <p class="body reveal">Stickiness is fine if the revenue is broadly distributed; concentration is fine if the customer base is healthy. With 11 named segments derived from quintile-binned recency, frequency, and spend scores (the standard Putler grid), the picture is sharply top-heavy.</p>
    <p class="body reveal"><strong>Champions</strong> &mdash; just 511 customers, about 12&#37; of the base &mdash; contribute 44.9&#37; of revenue. Add <strong>Loyal Customers</strong> (771 customers) and the top two segments together carry <strong>71&#37; of all revenue from 30&#37; of the base</strong>. That is a textbook Pareto and the structural fact that drives every recommendation in this report.</p>

    <div class="chart-row">
      <div class="chart-wrap reveal">
        <img src="charts/E2_q2_segment_revenue.png" alt="Revenue by segment" />
        <div class="chart-caption"><strong>Revenue by segment</strong> &nbsp;|&nbsp; Top three highlighted in coral. Champions alone = 44.9&#37;.</div>
      </div>
      <div class="chart-wrap reveal" data-delay="1">
        <img src="charts/S4_segment_customer_count.png" alt="Customers per segment" />
        <div class="chart-caption"><strong>Customer count by segment</strong> &nbsp;|&nbsp; Note the inverted shape &mdash; the largest segment by count (Lost) is small by share-of-revenue per head.</div>
      </div>
    </div>

    <p class="body reveal" style="margin-top:32px"><strong>Top six segments by share of revenue</strong> &mdash; rendered natively for fast comparison:</p>
    <div class="bar-chart reveal">
{BAR_CHART}
    </div>

    <ul class="learnings reveal">
      <li><span class="lbl">Champions dominate</span> A single segment &mdash; <strong>Champions, 511 customers &mdash; contributes &pound;3.57M or 44.9&#37; of revenue</strong>. Roughly 12&#37; of the base producing close to half the revenue.</li>
      <li><span class="lbl">Top two carry the business</span> Adding <strong>Loyal Customers (771 customers, &pound;2.09M, 26.2&#37;)</strong> brings the top two segments to <strong>71&#37; of revenue from 1,282 customers (30&#37; of the base)</strong>.</li>
      <li><span class="lbl">A long, dormant tail</span> <strong>Lost is the largest segment by count (1,042 customers)</strong> but holds only 15.9&#37; of revenue &mdash; these are former buyers, not non-buyers, which is the reservoir the retention question targets.</li>
    </ul>

    <div class="pull-quote reveal">
      <p>30&#37; of customers carry 71&#37; of the revenue. <strong>Service quality for Champions and Loyal Customers is the load-bearing investment &mdash; not a "nice to have."</strong></p>
    </div>
    <div class="bridge reveal">Next: what behavioural features actually predict who becomes a high-value customer in the first place.</div>
  </div>
</section>""")

# ─── Section 3: drivers ───
SECTIONS.append(f"""<section class="section" id="drivers">
  <div class="container">
    <div class="section-num reveal">03 &nbsp;&middot;&nbsp; Drivers of High Value</div>
    <h2 class="reveal" data-delay="1">Which factors predict high lifetime value?</h2>
    <div class="section-deck reveal" data-delay="2">Going beyond "Champions are valuable" &mdash; using a model to ask what actually moves a customer into the top tier.</div>

    <p class="body reveal">Knowing that Champions are valuable does not tell us how to make more of them. To get at that, we trained a model to predict whether a customer falls in the <strong>top quintile of net spend</strong> from their behavioural features alone &mdash; recency, frequency, tenure, average basket size, average unit price, distinct product count, geography, and cancellation rate.</p>
    <p class="body reveal">Frequency is unsurprisingly the headline driver. The interesting story is what comes next: <strong>average basket size</strong> is a near-equal second &mdash; meaningfully more important than average unit price. The implication for marketing is the cleaner of two routes: bundles and free-shipping thresholds (which grow basket size) beat premium-SKU pushes (which grow unit price) for converting customers into the top tier.</p>

    <div class="chart-wrap reveal">
      <img src="charts/E3_q3_ltv_feature_importance.png" alt="Feature importance for predicting high-value customers" />
      <div class="chart-caption"><strong>Feature importance &mdash; what predicts top-quintile spend</strong> &nbsp;|&nbsp; Coral = behavioural / customer features (the actionable signal). Navy = recency &amp; frequency.</div>
    </div>

    <ul class="learnings reveal">
      <li><span class="lbl">Frequency</span> Purchase frequency is the strongest driver (importance &asymp; <strong>0.219</strong>). Expected, but useful: frequency can be moved with lifecycle programmes.</li>
      <li><span class="lbl">Basket size beats unit price</span> Average basket size is a near-equal second (<strong>0.201</strong>); average unit price is a distant third (<strong>0.042</strong>). Push <strong>bundles and free-shipping thresholds</strong>, not premium SKUs.</li>
      <li><span class="lbl">Clean separation</span> The model flags top-quintile customers with <strong>95.6&#37; precision and 95.3&#37; recall</strong> &mdash; we can identify likely-high-value customers from behaviour alone, well before a full year of spend accumulates.</li>
    </ul>

    <div class="pull-quote reveal">
      <p>Beyond &quot;they buy more often,&quot; the strongest behavioural lever is <strong>basket size, not price point</strong>. Bundles, multi-pack offers, and free-shipping thresholds are the cleaner play than pushing premium SKUs.</p>
    </div>
    <div class="bridge reveal">Next: a check on whether the customer base is being topped up at the same quality.</div>
  </div>
</section>""")

# ─── Section 4: cohorts ───
SECTIONS.append(f"""<section class="section alt" id="cohorts">
  <div class="container">
    <div class="section-num reveal">04 &nbsp;&middot;&nbsp; Cohort Health</div>
    <h2 class="reveal" data-delay="1">Are newer customers staying with us as well as older ones?</h2>
    <div class="section-deck reveal" data-delay="2">Concentration is fine if the funnel keeps refilling at the same quality &mdash; and dangerous if it doesn't. Cohort retention is the test.</div>

    <p class="body reveal">Grouping every customer by the month of their first purchase, then tracking what share of each cohort is still buying in each subsequent month, gives us a clean read on whether acquisition is delivering similar-quality customers across the year. Unobserved cells (e.g. month +11 for the November 2011 cohort) are masked in grey to avoid the false-trend pitfall.</p>
    <p class="body reveal">The picture is uncomfortable. The first cohort (December 2010) retains <strong>36.6&#37; of customers at month +1</strong>; the worst cohort (March 2011) drops to <strong>15.0&#37;</strong>, less than half. <strong>No later cohort recovers the December baseline.</strong> Topline revenue grew across the year, so the business looks healthy on the headline &mdash; but the cohort view shows a chunk of that growth is coming from less sticky customers, which is a warning rather than a victory.</p>

    <div class="chart-row">
      <div class="chart-wrap reveal">
        <img src="charts/E4_q4_cohort_heatmap.png" alt="Cohort retention heatmap" />
        <div class="chart-caption"><strong>Cohort retention heatmap</strong> &nbsp;|&nbsp; Each cell = % of cohort customers active in that month after acquisition. Grey cells are unobserved.</div>
      </div>
      <div class="chart-wrap reveal" data-delay="1">
        <img src="charts/S1_cohort_retention_lines.png" alt="Retention at M+1, M+3, M+6 by cohort" />
        <div class="chart-caption"><strong>Retention at M+1, M+3, M+6 by cohort</strong> &nbsp;|&nbsp; Same data, easier to read trend-wise. Cohorts clipped to observed windows.</div>
      </div>
    </div>

    <ul class="learnings reveal">
      <li><span class="lbl">First cohort is best</span> The <strong>December 2010 cohort retains 36.6&#37;</strong> of customers at month +1 &mdash; the highest of any cohort in the window.</li>
      <li><span class="lbl">Newer cohorts retain worse</span> The <strong>March 2011 cohort drops to 15.0&#37;</strong> at month +1, less than half the December figure. Across <strong>all 12 cohorts</strong>, no later cohort recovers the baseline.</li>
      <li><span class="lbl">Acquisition quality is degrading</span> Topline revenue rose across the year, but cohort retention shows it is being delivered by less sticky customers &mdash; a warning that aggregate growth hides.</li>
    </ul>

    <div class="pull-quote reveal">
      <p>The funnel is filling, but with worse-quality customers. <strong>Acquisition quality, not just acquisition volume, deserves to be a tracked KPI &mdash; investigate the channel mix change between early and mid 2011.</strong></p>
    </div>
    <div class="bridge reveal">Next: where the highest-leverage retention spend goes today.</div>
  </div>
</section>""")

# ─── Section 5: targets ───
SECTIONS.append(f"""<section class="section" id="targets">
  <div class="container">
    <div class="section-num reveal">05 &nbsp;&middot;&nbsp; Retention Targets</div>
    <h2 class="reveal" data-delay="1">Which 3 segments should we target for retention campaigns?</h2>
    <div class="section-deck reveal" data-delay="2">Pulling the segmentation and cohort views together: where is the highest-leverage retention spend?</div>

    <p class="body reveal">The retention pool is small but valuable. Three segments &mdash; <em>At Risk</em> (high-value customers who have gone quiet), <em>Cannot Lose Them</em> (highest-value customers slipping away), and <em>About to Sleep</em> (early-warning tier) &mdash; together hold <strong>341 customers (8&#37; of the base) and &pound;574k of revenue (7.2&#37; of the total)</strong>. That is manageable for a focused campaign, not a mass-marketing exercise.</p>
    <p class="body reveal">The three pools deserve different intensity. <strong>Cannot Lose Them</strong> is small (38 customers) but extraordinarily concentrated &mdash; an average of <strong>&pound;2,470 per customer</strong>, well above the &pound;1,920 high-value threshold &mdash; and warrants 1:1 outreach. <strong>At Risk</strong> is the volume play: 164 customers and &pound;370k of revenue, the most cost-effective bucket for a discount-led win-back. <strong>About to Sleep</strong> is the early-warning tier: a lighter-touch lifecycle nudge before they migrate into At Risk.</p>

    <div class="chart-wrap reveal">
      <img src="charts/E5_q5_target_segments.png" alt="Top 3 segments to target for retention" />
      <div class="chart-caption"><strong>Three retention targets, three intensities</strong> &nbsp;|&nbsp; Customers, revenue, share of revenue, and a recommended action per segment.</div>
    </div>

    <ul class="learnings reveal">
      <li><span class="lbl">Pool size</span> Three target segments hold <strong>341 customers (8&#37;) and &pound;574k of revenue (7.2&#37;)</strong> &mdash; small enough to act on with focus, not mass spend.</li>
      <li><span class="lbl">VIP rescue first</span> <strong>Cannot Lose Them: only 38 customers but &pound;2,470 each on average</strong> &mdash; account-manager outreach and early-access offers, not bulk email.</li>
      <li><span class="lbl">Volume play second</span> <strong>At Risk: 164 customers, &pound;370,280 in revenue (4.7&#37; of total)</strong> &mdash; the largest pool and the most cost-effective bucket for a discount-led win-back. About to Sleep gets a lighter lifecycle nudge.</li>
    </ul>

    <div class="pull-quote reveal">
      <p>Three campaigns at three intensities for 341 customers carrying &pound;574k of revenue. <strong>The retention play sized correctly is a focused, near-term win &mdash; not a mass-marketing programme.</strong></p>
    </div>
  </div>
</section>""")

new_sections_block = "\n\n".join(SECTIONS) + "\n\n\n"
template = template[:sec_start] + new_sections_block + template[sec_end:]

# ─── Replace the conclusion ───
new_conclusion = """<section id="conclusion">
  <div class="conclusion-inner">
    <div class="eyebrow reveal">Conclusion &nbsp;&middot;&nbsp; Integrated Findings</div>
    <h2 class="reveal" data-delay="1">Two segments carry the business; newer cohorts are slipping; a small retention pool is the highest-leverage move.</h2>
    <div class="findings-list">
      <div class="finding-item reveal" data-delay="1">
        <div class="finding-num">01</div>
        <div class="finding-text"><strong>Concentration is the structural fact.</strong> Champions and Loyal Customers, 1,282 customers (30&#37; of the base), account for 71&#37; of the &pound;9.32M annual revenue. Service quality, account management, and retention investment for these two segments is not optional &mdash; it is the load-bearing investment in the business.</div>
      </div>
      <div class="finding-item reveal" data-delay="2">
        <div class="finding-num">02</div>
        <div class="finding-text"><strong>Acquisition quality is degrading even while topline grows.</strong> Month-1 retention has slipped from 36.6&#37; in the December 2010 cohort to 15.0&#37; by March 2011, and never recovers. Track acquisition <em>quality</em> alongside acquisition <em>volume</em>; investigate the channel-mix shift between early and mid 2011.</div>
      </div>
      <div class="finding-item reveal" data-delay="3">
        <div class="finding-num">03</div>
        <div class="finding-text"><strong>The retention play is small, sharp, and ready.</strong> 341 customers in <em>At Risk</em>, <em>Cannot Lose Them</em>, and <em>About to Sleep</em> hold &pound;574k (7.2&#37;) of revenue. Run three campaigns at three intensities &mdash; 1:1 outreach for <em>Cannot Lose Them</em>, a discount-led win-back for <em>At Risk</em>, and a lifecycle nudge for <em>About to Sleep</em>.</div>
      </div>
    </div>
    <div class="report-links reveal" data-delay="4">
      <span>Source: <a href="https://archive.ics.uci.edu/dataset/352/online+retail">UCI Online Retail dataset</a> &nbsp;&middot;&nbsp; methodology in Data Notes below.</span>
    </div>
  </div>
</section>"""

concl_start = template.index('<section id="conclusion">')
concl_end = template.index("</section>", concl_start) + len("</section>")
template = template[:concl_start] + new_conclusion + template[concl_end:]

# ─── Replace the data notes ───
new_notes = """<section id="notes">
  <div class="container">
    <p class="notes-toggle" onclick="
      var c = document.getElementById('notes-content');
      c.style.display = c.style.display === 'none' ? 'block' : 'none';
      this.textContent = c.style.display === 'none'
        ? '▶ Data Notes &amp; Methodology (click to expand)'
        : '▼ Data Notes &amp; Methodology (click to collapse)';
    ">▶ Data Notes &amp; Methodology (click to expand)</p>
    <dl class="notes-content" id="notes-content" style="display:none;">

      <dt>Source</dt>
      <dd>UCI Online Retail dataset (~541k transactions from a UK gifts and homewares retailer, Dec 2010 &ndash; Dec 2011). All currency: <strong>GBP (&pound;)</strong>.</dd>

      <dt>Cleaning policy (every rule logs a before/after row count)</dt>
      <dd>
        <ol style="margin: 8px 0 8px 18px; padding: 0;">
          <li><strong>Trim period</strong> to 2010-12-01 &rarr; 2011-11-30 (12 full months) &mdash; the trailing 9 days of Dec 2011 corrupt cohort math. Drops 25,525 rows.</li>
          <li><strong>Drop UnitPrice &le; 0</strong> &mdash; non-priced lines (manual adjustments) are not products. Drops 2,463 rows.</li>
          <li><strong>Drop exact duplicates</strong> &mdash; 4,984 rows.</li>
          <li><strong>Cancellations</strong> (InvoiceNo starting <code>C</code> or negative quantity): <em>kept</em> and netted against per-customer revenue rather than dropped wholesale. 8,892 rows kept.</li>
          <li><strong>Drop missing CustomerID</strong> for customer-level analyses (RFM / LTV / cohorts) &mdash; ~25&#37; of rows. Total revenue still uses these rows; segments and cohorts do not.</li>
          <li><strong>Non-product StockCodes</strong> (POST, M, DOT, BANK CHARGES, etc.) audited (2,614 rows) but not removed &mdash; no product-level analysis is in scope.</li>
          <li><strong>Drop net-negative customers</strong> (51 customers whose net Monetary went &le; 0 after netting cancellations) &mdash; they would corrupt the LTV target.</li>
        </ol>
      </dd>

      <dt>RFM segmentation</dt>
      <dd>Snapshot date = <code>2011-12-01</code>. Recency, Frequency, and Monetary scored on independent quintile bins (1 = worst, 5 = best). The (R, F, M) score triple maps to one of 11 named segments via the standard Putler grid; the full mapping is exported as <code>data/processed/rfm_segment_map.json</code> for auditability.</dd>

      <dt>Cohort retention</dt>
      <dd>Cohort = year-month of first purchase. Period n = months elapsed. <code>Retention[c, n]</code> = share of cohort c with at least one invoice in period n. Cells outside the observed window are masked (grey) so the trend is not falsely depressed by the censor.</dd>

      <dt>LTV-driver model</dt>
      <dd>A gradient-boosted classifier (<code>sklearn.ensemble.HistGradient&shy;BoostingClassifier</code>) predicting whether a customer falls in the top quintile of net Monetary (threshold &pound;1,920). Reported with 5-fold stratified cross-validation: discrimination = 0.998, precision = 0.956, recall = 0.953. <strong>The discrimination figure is inflated by construction</strong> &mdash; the target is derived from M and one feature (Frequency) is structurally correlated with M. The body of the report intentionally focuses on the <em>non-RFM</em> features (basket size, unit price), which is the un-confounded signal.</dd>

      <dt>Partial dependence on the top non-RFM features</dt>
      <dd>
        <div class="chart-row" style="margin-top:14px;">
          <div class="chart-wrap">
            <img src="charts/S2_ltv_pdp_top1.png" alt="Partial dependence on AvgBasketSize" />
            <div class="chart-caption"><strong>Partial dependence &mdash; AvgBasketSize</strong> &nbsp;|&nbsp; Top non-RFM driver of top-quintile probability.</div>
          </div>
          <div class="chart-wrap">
            <img src="charts/S3_ltv_pdp_top2.png" alt="Partial dependence on AvgUnitPrice" />
            <div class="chart-caption"><strong>Partial dependence &mdash; AvgUnitPrice</strong> &nbsp;|&nbsp; Second non-RFM driver &mdash; flatter than basket size.</div>
          </div>
        </div>
      </dd>

      <dt>Caveats</dt>
      <dd>
        <ul style="margin: 8px 0 8px 18px; padding: 0;">
          <li><strong>Cancellations are netted, not dropped.</strong> Per-customer Monetary is a net figure (purchases &minus; returns), matching how a CRM team would think about a customer's true contribution.</li>
          <li><strong>Missing CustomerID is kept for total revenue, dropped for customer-level work.</strong> Total revenue (&pound;9.32M) is the upper bound; customer-attributed revenue (&pound;7.94M) feeds segments and cohorts.</li>
          <li><strong>UK accounts for ~85&#37; of customers and ~91&#37; of rows.</strong> Non-UK is encoded as a binary feature in the LTV model rather than split into separate analyses.</li>
          <li><strong>Currency is GBP throughout.</strong> Treating the figures as USD would understate revenue by ~25&#37; at 2011 rates.</li>
        </ul>
      </dd>

    </dl>
  </div>
</section>"""

notes_start = template.index('<section id="notes">')
notes_end = template.index("</section>", notes_start) + len("</section>")
template = template[:notes_start] + new_notes + template[notes_end:]

# ─── Replace the footer ───
new_footer = """<footer>
  Online Retail RFM &amp; Cohorts &nbsp;&middot;&nbsp; Investigating Retail Data: Who Drives Revenue, and Who's Slipping Away? &nbsp;&middot;&nbsp; Dec 2010 &ndash; Nov 2011<br>
  Source: <a href="https://archive.ics.uci.edu/dataset/352/online+retail" style="color:#a3a3a3">UCI Online Retail dataset</a> &nbsp;&middot;&nbsp; Methodology in Data Notes
</footer>"""

footer_start = template.index('<footer>')
footer_end = template.index("</footer>") + len("</footer>")
template = template[:footer_start] + new_footer + template[footer_end:]

OUT.write_text(template)
print(f"Wrote {OUT.relative_to(ROOT)} ({len(template):,} chars)")
