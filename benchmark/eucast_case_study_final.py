"""
Final, corrected EUCAST case-study extraction (Results subsection "Case
Study: Extracting EUCAST Antimicrobial MIC Distributions"). NOT part of
the N=141 benchmark and NOT added to resources.py.

Supersedes eucast_feasibility_test.py (5 summary columns only) and
eucast_evidence_audit.py (24 columns, but row_xpath matched 6 repeated
<th> header rows per query as empty pseudo-records). This script fixes
the row selector with a tr[td] predicate (only <tr> elements that
contain at least one <td> -- EUCAST's repeated header rows use <th> and
are excluded) and extracts all 24 real fields: Species, the 19 MIC
dilution isolate counts, Distributions, Observations, ECOFF, and
ConfidenceInterval.

Same real production engine (_run_scraping_async) as every other
experiment in this paper. Same wrapper (same row_xpath, same columns)
reused across the Meropenem and Imipenem queries; only the antibiotic
URL parameter changes.

No independent ground truth exists for this page (EUCAST has no public
API for distribution-level data); validation here is a direct,
same-session manual cross-check against the live page, documented in
eucast_case_study_validation_notes.md, not an API-based or automated
accuracy evaluation.
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
    COLUMNS.append({"name": f"MIC_{d}", "xpath": f".//td[{i+2}]"})
COLUMNS += [
    {"name": "Distributions", "xpath": ".//td[21]"},
    {"name": "Observations", "xpath": ".//td[22]"},
    {"name": "ECOFF", "xpath": ".//td[@class='ecoff-value']"},
    {"name": "ConfidenceInterval", "xpath": ".//td[24]"},
]

# Fixed selector: tr[td] excludes EUCAST's repeated <th>-only header rows.
ROW_XPATH = "//table[@id='search-results-table']/tbody/tr[td]"

EXPECTED_RECORD_COUNT = {"meropenem": 103, "imipenem": 94}


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


def dilution_sum(record):
    return sum(int(record[f"MIC_{d}"]) for d in DILUTIONS)


async def main():
    out = {}
    for name, aid in ANTIBIOTICS.items():
        print(f"=== {name} (antibiotic id={aid}) ===", flush=True)
        records, elapsed, url = await run_one(aid)

        species_list = [r.get("Species", "").strip() for r in records]
        counts = Counter(species_list)
        duplicates = {s: c for s, c in counts.items() if c > 1}
        empty_species = sum(1 for s in species_list if not s)

        kleb = [r for r in records if r.get("Species", "").strip() == "Klebsiella pneumoniae"]
        kleb_rec = kleb[0] if kleb else None
        kleb_sum = dilution_sum(kleb_rec) if kleb_rec else None
        kleb_obs = int(kleb_rec["Observations"]) if kleb_rec else None

        print(f"  records: {len(records)} (expected {EXPECTED_RECORD_COUNT[name]})", flush=True)
        print(f"  empty species: {empty_species}, duplicate species: {duplicates}", flush=True)
        print(f"  elapsed: {elapsed:.1f}s", flush=True)
        if kleb_rec:
            print(f"  Klebsiella pneumoniae dilution-sum={kleb_sum} vs Observations={kleb_obs} "
                  f"({'MATCH' if kleb_sum == kleb_obs else 'MISMATCH'})", flush=True)

        out[name] = {
            "url": url,
            "elapsed_seconds": elapsed,
            "record_count": len(records),
            "expected_record_count": EXPECTED_RECORD_COUNT[name],
            "record_count_matches_expected": len(records) == EXPECTED_RECORD_COUNT[name],
            "empty_species_count": empty_species,
            "duplicate_species": duplicates,
            "klebsiella_pneumoniae": kleb_rec,
            "klebsiella_pneumoniae_dilution_sum": kleb_sum,
            "klebsiella_pneumoniae_observations_field": kleb_obs,
            "dilution_sum_matches_observations": kleb_sum == kleb_obs,
            "all_records": records,
        }

    out_path = os.path.join(os.path.dirname(__file__), "eucast_case_study_result.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
