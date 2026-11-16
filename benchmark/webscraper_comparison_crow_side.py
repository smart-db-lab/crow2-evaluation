"""
CroW's side of the controlled comparison against Web Scraper (Chrome
extension), requested to address Bioinformatics Advances Reviewer 1's
claim of successfully extracting UniProt entry pages and ClinicalTrials.gov
search results with Web Scraper.

Reuses the EXACT same wrapper configs and target resources already in the
N=141 benchmark (resources.py), so this is scored against the same
ground truth already on disk -- no new ground-truth fetching needed.

Real run against the real production extraction path
(_run_scraping_async), not a simulation.
"""
import asyncio, json, os, sys, time

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import django
django.setup()

from wrapper.views import _run_scraping_async
from resources import RESOURCES

TIER0_IDS = ["clinicaltrials_crispr", "clinicaltrials_diabetes", "clinicaltrials_alzheimer_disease"]
TIER1_IDS = ["uniprot_entry_p01308", "uniprot_entry_p04637", "uniprot_entry_p38398"]

by_id = {r["id"]: r for r in RESOURCES}


async def run_one(res):
    config = {
        "mode": res["mode"],
        "row_xpath": res["row_xpath"],
        "columns": res["columns"],
        "pagination": res["pagination"],
    }
    t0 = time.monotonic()
    records = await _run_scraping_async(
        config=config, target_urls=[res["url"]], max_items=0, col_mapping=None
    )
    elapsed = time.monotonic() - t0
    return records, elapsed


async def main():
    results = {"tier0_clinicaltrials": [], "tier1_uniprot": []}

    print("=" * 70)
    print("Tier 0: ClinicalTrials.gov (same wrapper, 3 queries -- reuse test)")
    print("=" * 70)
    for rid in TIER0_IDS:
        res = by_id[rid]
        records, elapsed = await run_one(res)
        print(f"{rid}: {len(records)} records in {elapsed:.2f}s")
        results["tier0_clinicaltrials"].append({
            "resource_id": rid, "url": res["url"], "elapsed_seconds": elapsed,
            "record_count": len(records), "records": records,
        })
        time.sleep(0.3)

    print()
    print("=" * 70)
    print("Tier 1: UniProt entries (same wrapper, 3 pages -- combine into one dataset)")
    print("=" * 70)
    for rid in TIER1_IDS:
        res = by_id[rid]
        records, elapsed = await run_one(res)
        print(f"{rid}: {len(records)} records in {elapsed:.2f}s")
        results["tier1_uniprot"].append({
            "resource_id": rid, "url": res["url"], "elapsed_seconds": elapsed,
            "record_count": len(records), "records": records,
        })
        time.sleep(0.3)

    out_path = os.path.join(os.path.dirname(__file__), "webscraper_comparison_crow_side.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
