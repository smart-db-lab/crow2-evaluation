"""
Evidence audit for the EUCAST feasibility investigation (requested
follow-up, NOT part of the N=141 benchmark, NOT touching resources.py).

Unlike eucast_feasibility_test.py (which only extracted five summary
columns: Species, Distributions, Observations, ECOFF, ConfidenceInterval),
this script extracts ALL 24 columns of the live table, including the 19
per-dilution isolate-count columns, to answer directly: does CroW's
execution engine actually extract the MIC distribution itself (isolate
counts per dilution step), not just summary statistics about it?

It also re-runs both antibiotic queries and audits the full record list
(not just the Klebsiella pneumoniae row) for count, duplicates, and
empty/missing fields, and re-fetches the Klebsiella pneumoniae row a
second, independent time per antibiotic (two consecutive, separately
timed runs) to check run-to-run consistency of the extracted values.

Same real production engine (_run_scraping_async), same real live site,
same hand-authored row/column selector style as the original test.
"""
import asyncio, json, os, sys, time
from collections import Counter

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

DILUTIONS = ["0.002", "0.004", "0.008", "0.016", "0.03", "0.06", "0.125",
             "0.25", "0.5", "1", "2", "4", "8", "16", "32", "64", "128",
             "256", "512"]

COLUMNS = [{"name": "Species", "xpath": ".//a/span[@class='name']"}]
for i, d in enumerate(DILUTIONS):
    # dilution columns are td[2] .. td[20]
    COLUMNS.append({"name": f"MIC_{d}", "xpath": f".//td[{i+2}]"})
COLUMNS += [
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


def audit_records(records):
    species_list = [r.get("Species", "").strip() for r in records]
    counts = Counter(species_list)
    duplicates = {s: c for s, c in counts.items() if c > 1}
    empty_species = sum(1 for s in species_list if not s)
    field_names = COLUMNS[0]["name"], COLUMNS[-1]["name"]
    empty_field_counts = {}
    for col in COLUMNS:
        name = col["name"]
        n_empty = sum(1 for r in records if not str(r.get(name, "")).strip())
        if n_empty:
            empty_field_counts[name] = n_empty
    return {
        "total_records": len(records),
        "unique_species": len(counts),
        "duplicate_species": duplicates,
        "empty_species_name_count": empty_species,
        "fields_with_any_empty_value": empty_field_counts,
    }


async def main():
    out = {}
    for name, aid in ANTIBIOTICS.items():
        print(f"=== {name} (antibiotic id={aid}) ===", flush=True)
        run_a, elapsed_a, url = await run_one(aid)
        run_b, elapsed_b, _ = await run_one(aid)  # second independent run, same params

        kleb_a = [r for r in run_a if r.get("Species", "").strip() == "Klebsiella pneumoniae"]
        kleb_b = [r for r in run_b if r.get("Species", "").strip() == "Klebsiella pneumoniae"]

        audit_a = audit_records(run_a)
        print(f"  run 1: {audit_a['total_records']} records, "
              f"{audit_a['unique_species']} unique species, "
              f"{elapsed_a:.1f}s", flush=True)
        print(f"  run 1 duplicates: {audit_a['duplicate_species']}", flush=True)
        print(f"  run 1 empty fields: {audit_a['fields_with_any_empty_value']}", flush=True)
        print(f"  run 2: {len(run_b)} records, {elapsed_b:.1f}s", flush=True)
        print(f"  Klebsiella pneumoniae run1 == run2: {kleb_a == kleb_b if (kleb_a and kleb_b) else 'N/A'}", flush=True)
        if kleb_a:
            print(f"  Klebsiella pneumoniae full record (run 1): {json.dumps(kleb_a[0], indent=2)}", flush=True)

        out[name] = {
            "url": url,
            "elapsed_seconds_run1": elapsed_a,
            "elapsed_seconds_run2": elapsed_b,
            "audit_run1": audit_a,
            "klebsiella_pneumoniae_run1": kleb_a[0] if kleb_a else None,
            "klebsiella_pneumoniae_run2": kleb_b[0] if kleb_b else None,
            "run1_run2_identical_for_klebsiella": (kleb_a == kleb_b) if (kleb_a and kleb_b) else None,
            "all_records_run1": run_a,
        }

    out_path = os.path.join(os.path.dirname(__file__), "eucast_evidence_audit_result.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
