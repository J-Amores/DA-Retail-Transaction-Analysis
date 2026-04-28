# Investigating Retail Data: Who Drives Revenue, and Who's Slipping Away?

> **Status:** Delivered. Live report: see `index.html` (also published via GitHub Pages).

A portfolio data-analysis project on the UCI Online Retail dataset (~541K UK
e-commerce transactions, Dec 2010 – Nov 2011), answering five business questions
through RFM segmentation, cohort retention analysis, and an interpretable
LTV-driver model.

## The five questions

1. What is total revenue, AOV, and repeat purchase rate?
2. Which customer segments contribute the most revenue?
3. Which factors predict high lifetime value?
4. Are newer customers staying with us as well as older ones?
5. Which 3 segments should we target for retention campaigns?

## Deliverables

- `notebooks/analysis.ipynb` — end-to-end EDA, cleaning, RFM / cohort / LTV computations.
- `notebooks/final-report.ipynb` — narrative write-up answering the five questions.
- `index.html` — editorial HTML report (served via GitHub Pages).
- `scripts/` — pipeline (`build_pipeline.py`) and notebook/HTML generators (`make_*.py`).

## Reproducing this analysis

1. Clone this repo.
2. Download the UCI Online Retail dataset (~23 MB) from
   <https://archive.ics.uci.edu/dataset/352/online+retail> and save it to
   `data/raw/Online Retail.xlsx`. (The file is gitignored to keep the repo small.)
3. Set up the environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. Run the analysis pipeline, then open the notebooks:
   ```bash
   python scripts/build_pipeline.py            # regenerates charts/, data/processed/
   python scripts/make_notebook.py             # rebuilds notebooks/analysis.ipynb
   python scripts/make_report_notebook.py      # rebuilds notebooks/final-report.ipynb
   python scripts/make_index.py                # rebuilds index.html
   ```
   Or open `notebooks/analysis.ipynb` and `notebooks/final-report.ipynb` in Jupyter and run all cells.

## Dataset

UCI Machine Learning Repository — *Online Retail* (Daqing Chen, 2015).
Licence: CC BY 4.0.
