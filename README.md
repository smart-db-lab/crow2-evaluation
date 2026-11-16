# CroW 2.0 — Evaluation & Chart Artifacts

This repository holds the evaluation data, ground truth, and chart-generation
code referenced by the CroW 2.0 paper. **It is a data/evaluation artifact
release, not the CroW application source code.** The platform source is not
included here.

It contains two independent things. Don't confuse them — they measure
different claims in the paper.

## 1. `benchmark/` — real, controlled extraction-quality benchmark

A real benchmark of scientific web resources, **complete at N=141** across
all five of the paper's target categories (biomedical search, clinical
registries, protein knowledgebases, genomic repositories, disease
databases), executed through CroW's production extraction engine against
live websites, checked against ground truth fetched independently from each
portal's own public API (NCBI E-utilities, ClinicalTrials.gov API v2,
UniProt REST API, MedlinePlus). Every precision/recall/F1 number reported in
the paper is recomputed from the raw files here.

Beyond the original N=141 run, this folder also holds: a real comparison
against ScrapeGraphAI (17-resource subset), two Tier 1 structural
experiments (aggregation across pages, and robustness on harder/atypical
pages identified live), and a 95-day unmodified re-run of the full benchmark
measuring how precision/recall change over time on live, uncontrolled
portals. See `benchmark/README.md` for all of it in detail.

**What you can rerun yourself, with nothing else installed but this repo's
Python dependencies:**
```bash
cd benchmark
python fetch_ground_truth.py     # hits live public APIs, writes ground_truth/*.json
python compute_metrics.py        # pure computation from extracted/ + ground_truth/, writes results.csv
python generate_figures.py       # regenerates the benchmark-construction figures from results.csv
python generate_drift_figure.py  # regenerates the 95-day re-run comparison from results_aug12_baseline.csv + results_nov15.csv
```

**What you cannot rerun from this repo alone:** `run_extraction.py` calls
`wrapper.views._run_scraping_async`, the CroW application's real extraction
engine. That application's source is not included in this repository, so
`run_extraction.py` will not execute here — it's included for transparency
(to show exactly what was called and how) and as documentation of the
method, not as a self-contained reproduction step. The `extracted/*.json`
files it already produced are included, so `compute_metrics.py` still
reproduces every reported precision/recall/F1 number without needing to
re-run extraction.

See `benchmark/README.md` for full methodology, current status, and a
record of failed attempts at sites we couldn't yet integrate.

## 2. `generate_charts.py` + `reviewer_export/` — seeded operational corpus

A **synthetic** corpus (100 seeded wrapper configs, 1,352 generated run
records) used in the paper only to validate the repository, run-history, and
charting pipeline at scale — explicitly *not* evidence of real-world
extraction reliability. `reviewer_export/` is the raw seeded data;
`generate_charts.py` reads it and produces the corresponding figures.

```bash
pip install numpy pandas matplotlib seaborn
python generate_charts.py
# writes figures to ./charts/
```

This script has no dependency on the CroW application — it only reads the
CSV/JSON files under `reviewer_export/`.

## Scope

This repository intentionally does not include: the CroW Django application
source, wrapper induction/selector code, deployment configuration, or
credentials. It is the evaluation and reproducibility layer only.

## Citation

If you use this data, please cite the CroW paper (Naha and Jamil). A
manuscript describing CroW's design and evaluation is in preparation;
citation details will be added here once it is published.
