"""
EUCAST feasibility investigation (requested audit, NOT part of the N=141
benchmark and NOT added to resources.py). Tests whether CroW's real,
unmodified production extraction engine (_run_scraping_async, the same
path used throughout the benchmark) can execute a hand-authored wrapper
against the live EUCAST MIC-distribution search page, and whether that
wrapper reuses across two different antibiotic queries by URL-parameter
substitution alone, the same reuse mechanism used for the ClinicalTrials.gov
case study.

Selectors below were authored by direct DOM inspection of the live page
(table id="search-results-table", one <tbody><tr> per species row, ECOFF
cell carries class="ecoff-value"), the same positional/class style the
two-click visual tool produces, exactly as documented in resources.py's
own docstring.

This script does NOT fetch independent ground truth (EUCAST has no public
API for this; values below are cross-checked only against what was read
directly off the live page during this same investigation -- a sanity
check, not independent validation).
"""
import asyncio, json, os, sys, time

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import django
django.setup()

from wrapper.views import _run_scraping_async

ANTIBIOTICS = {
    "meropenem": 123,
    "imipenem": 109,
}

COLUMNS = [
    {"name": "Species", "xpath": ".//a/span[@class='name']"},
    {"name": "Distributions", "xpath": ".//td[21]"},
    {"name": "Observations", "xpath": ".//td[22]"},
    {"name": "ECOFF", "xpath": ".//td[@class='ecoff-value']"},
    {"name": "ConfidenceInterval", "xpath": ".//td[24]"},
]

ROW_XPATH = "//table[@id='search-results-table']/tbody/tr"


async def run_one(antibiotic_id):
    url = (
        "https://mic.eucast.org/search/"
        "?search[method]=mic&search[antibiotic]={}&search[species]=-1"
        "&search[disk_content]=-1&search[limit]=500"
    ).format(antibiotic_id)
    config = {
        "mode": "A",
        "row_xpath": ROW_XPATH,
        "columns": COLUMNS,
        "pagination": {"type": "none"},
    }
    t0 = time.monotonic()
    records = await _run_scraping_async(
        config=config, target_urls=[url], max_items=0, col_mapping=None
    )
    elapsed = time.monotonic() - t0
    return records, elapsed, url


async def main():
    out = {}
    for name, aid in ANTIBIOTICS.items():
        print(f"Running {name} (antibiotic id={aid}) ...", flush=True)
        records, elapsed, url = await run_one(aid)
        kleb = [r for r in records if r.get("Species", "").strip() == "Klebsiella pneumoniae"]
        out[name] = {
            "url": url,
            "elapsed_seconds": elapsed,
            "total_records": len(records),
            "klebsiella_pneumoniae_row": kleb[0] if kleb else None,
        }
        print(f"  {name}: {len(records)} records in {elapsed:.1f}s; "
              f"K. pneumoniae row found: {bool(kleb)}", flush=True)

    out_path = os.path.join(os.path.dirname(__file__), "eucast_feasibility_result.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
