"""
Tier 1 structural robustness experiment (response to Bioinformatics Advances
Reviewer 2's comment that the original five-accession aggregation test used
only well-annotated, reviewed human proteins that likely share one layout).

Runs the SAME, unchanged Single Page Mode wrapper configs used in the
141-resource benchmark (uniprot_entry / clinicaltrials_study in resources.py)
against real, harder target pages the benchmark never used for selector
authoring or scoring:

  - UniProt: two unreviewed (TrEMBL) entries, one human and one non-human
    (Drosophila melanogaster), plus one sparsely annotated non-human plant
    entry (Arabidopsis thaliana) -- all identified live via the UniProt REST
    search API immediately before this run, not hand-picked in advance.
  - ClinicalTrials.gov: one real study WITHOUT posted results and one real
    study WITH posted results, identified live via the ClinicalTrials.gov
    API v2 immediately before this run.

This is a real run against the real production extraction path
(_run_scraping_async), against real live pages, scored against independently
fetched API ground truth -- not a simulation. Per-field pass/fail is
reported explicitly (not just aggregate P/R) because a field-level failure
rate is what Reviewer 2 asked for.
"""
import asyncio, json, os, sys, time

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import django
django.setup()

from wrapper.views import _run_scraping_async
from resources import uniprot_entry, clinicaltrials_study
from fetch_ground_truth import ground_truth_uniprot_entry, ground_truth_clinicaltrials_study

# Identified live via the UniProt REST search API (reviewed:false) immediately
# before this run -- not cherry-picked from the main benchmark.
UNIPROT_HARD_CASES = [
    ("A0A0A0MS99", "unreviewed (TrEMBL), Homo sapiens"),
    ("A0A0B4JCU1", "unreviewed (TrEMBL), Drosophila melanogaster"),
    ("F4I2K0",     "unreviewed (TrEMBL), Arabidopsis thaliana"),
]

# Identified live via the ClinicalTrials.gov API v2 immediately before this run.
CLINICALTRIALS_HARD_CASES = [
    ("NCT07689214", "no posted results"),
    ("NCT04007393", "has posted results"),
]


def _norm(s):
    return " ".join((s or "").replace("​", "").strip().lower().split())


def score_fields(extracted, truth):
    """Per-field pass/fail; substring match in either direction, case-insensitive."""
    out = {}
    for field in set(extracted.keys()) | set(truth.keys()):
        ex = _norm(extracted.get(field, ""))
        gt = _norm(truth.get(field, ""))
        if not gt:
            out[field] = ("SKIP (no ground truth)", ex, gt)
        elif ex and (ex == gt or gt in ex or ex in gt):
            out[field] = ("PASS", ex, gt)
        else:
            out[field] = ("FAIL", ex, gt)
    return out


async def run_uniprot_hard_cases():
    print("=" * 70)
    print("UniProt Single Page Mode -- unreviewed / non-human / sparse entries")
    print("=" * 70)
    sample = uniprot_entry(UNIPROT_HARD_CASES[0][0])
    config = {
        "mode": sample["mode"],
        "row_xpath": sample["row_xpath"],
        "columns": sample["columns"],
        "pagination": sample["pagination"],
    }
    results = []
    for accession, label in UNIPROT_HARD_CASES:
        url = uniprot_entry(accession)["url"]
        t0 = time.monotonic()
        try:
            records = await _run_scraping_async(config=config, target_urls=[url], max_items=0, col_mapping=None)
            extracted = records[0] if records else {}
        except Exception as e:
            extracted = {}
            print(f"  [EXTRACTION ERROR] {accession}: {e}")
        elapsed = time.monotonic() - t0
        truth = ground_truth_uniprot_entry(accession)[0]
        field_scores = score_fields(extracted, truth)
        n_pass = sum(1 for v in field_scores.values() if v[0] == "PASS")
        n_fail = sum(1 for v in field_scores.values() if v[0] == "FAIL")
        n_skip = sum(1 for v in field_scores.values() if v[0].startswith("SKIP"))
        print(f"\n{accession} ({label}), {elapsed:.1f}s:")
        for field, (verdict, ex, gt) in sorted(field_scores.items()):
            print(f"    {field:15s} {verdict:6s}  extracted={ex!r:40s} truth={gt!r}")
        results.append({
            "accession": accession, "label": label, "elapsed_seconds": elapsed,
            "extracted": extracted, "ground_truth": truth,
            "field_pass": n_pass, "field_fail": n_fail, "field_skip": n_skip,
        })
        time.sleep(0.3)
    return results


async def run_clinicaltrials_hard_cases():
    print("\n" + "=" * 70)
    print("ClinicalTrials.gov Single Page Mode -- with/without posted results")
    print("=" * 70)
    sample = clinicaltrials_study(CLINICALTRIALS_HARD_CASES[0][0])
    config = {
        "mode": sample["mode"],
        "row_xpath": sample["row_xpath"],
        "columns": sample["columns"],
        "pagination": sample["pagination"],
    }
    results = []
    for nct_id, label in CLINICALTRIALS_HARD_CASES:
        url = clinicaltrials_study(nct_id)["url"]
        t0 = time.monotonic()
        try:
            records = await _run_scraping_async(config=config, target_urls=[url], max_items=0, col_mapping=None)
            extracted = records[0] if records else {}
        except Exception as e:
            extracted = {}
            print(f"  [EXTRACTION ERROR] {nct_id}: {e}")
        elapsed = time.monotonic() - t0
        truth = ground_truth_clinicaltrials_study(nct_id)[0]
        field_scores = score_fields(extracted, truth)
        n_pass = sum(1 for v in field_scores.values() if v[0] == "PASS")
        n_fail = sum(1 for v in field_scores.values() if v[0] == "FAIL")
        n_skip = sum(1 for v in field_scores.values() if v[0].startswith("SKIP"))
        print(f"\n{nct_id} ({label}), {elapsed:.1f}s:")
        for field, (verdict, ex, gt) in sorted(field_scores.items()):
            print(f"    {field:15s} {verdict:6s}  extracted={ex!r:40s} truth={gt!r}")
        results.append({
            "nct_id": nct_id, "label": label, "elapsed_seconds": elapsed,
            "extracted": extracted, "ground_truth": truth,
            "field_pass": n_pass, "field_fail": n_fail, "field_skip": n_skip,
        })
        time.sleep(0.3)
    return results


async def main():
    uniprot_results = await run_uniprot_hard_cases()
    ct_results = await run_clinicaltrials_hard_cases()

    total_pass = sum(r["field_pass"] for r in uniprot_results + ct_results)
    total_fail = sum(r["field_fail"] for r in uniprot_results + ct_results)
    total_skip = sum(r["field_skip"] for r in uniprot_results + ct_results)

    print("\n" + "=" * 70)
    print("SUMMARY (field-level, varied/harder Tier 1 entries)")
    print("=" * 70)
    print(f"Total fields scored: {total_pass + total_fail + total_skip}")
    print(f"  PASS: {total_pass}")
    print(f"  FAIL: {total_fail}")
    print(f"  SKIP (no ground truth value to compare): {total_skip}")
    if (total_pass + total_fail) > 0:
        print(f"  Field-level success rate (excl. skips): {100*total_pass/(total_pass+total_fail):.1f}%")

    out_path = os.path.join(os.path.dirname(__file__), "tier1_robustness_result.json")
    with open(out_path, "w") as f:
        json.dump({
            "experiment": "Tier 1 structural robustness on varied/harder entries (unreviewed, non-human, sparse; with/without posted results)",
            "uniprot_hard_cases": uniprot_results,
            "clinicaltrials_hard_cases": ct_results,
            "total_fields_scored": total_pass + total_fail + total_skip,
            "total_pass": total_pass,
            "total_fail": total_fail,
            "total_skip": total_skip,
        }, f, indent=2)
    print(f"\nSaved full result to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
