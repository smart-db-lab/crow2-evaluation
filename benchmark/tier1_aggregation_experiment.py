"""
Tier 1 aggregation demonstration (experiment I-1 from OUP-DATABASE-REVISION-PLAN.md).

Runs the EXISTING, already-induced Single Page Mode wrapper config (same field
XPaths as resources.uniprot_entry) against FIVE UniProt accessions NOT in the
141-resource benchmark, in a single call to CroW's real production extraction
function (_run_scraping_async, target_urls as a list) -- the same mechanism
already validated for Tier 0's 17-condition ClinicalTrials.gov batch. This is
the real Bulk-Paste multi-value operation, not a simulation: one wrapper
definition, one batch call, a real headless Chromium browser, real UniProt
pages, real UniProt REST API ground truth.

Purpose: demonstrate that Tier 1 (a table whose rows are distributed
one-per-page across many pages) can actually be assembled into one logical
multi-row dataset by CroW, which the existing 141-resource benchmark does not
show (each Single Page Mode resource there is scored as an isolated page).
"""
import asyncio, json, os, sys, time

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import django
django.setup()

from wrapper.views import _run_scraping_async
from resources import uniprot_entry
from fetch_ground_truth import ground_truth_uniprot_entry

# Five accessions NOT among the 13 already in the 141-resource benchmark
# (P01308, P04637, P38398, P00533, P60484, P01116, P01106, P15692, P13569,
# P01375, P05231, P42336, P15056) -- chosen as well-known human cancer /
# signaling proteins, same difficulty class as the existing set.
NEW_ACCESSIONS = [
    ("P01112", "HRAS"),
    ("P04629", "NTRK1"),
    ("P11362", "FGFR1"),
    ("P35222", "CTNNB1"),
    ("P42345", "MTOR"),
]


def _normalize_text(s):
    return " ".join((s or "").replace("​", "").split())


def score_one(ex_rec, gt_rec):
    field_names = set(ex_rec.keys()) | set(gt_rec.keys())
    tp = fp = fn = 0
    for field in field_names:
        ex_val = _normalize_text((ex_rec.get(field) or "").strip())
        gt_val = _normalize_text((gt_rec.get(field) or "").strip())
        match = ex_val and gt_val and (ex_val == gt_val or gt_val in ex_val or ex_val in gt_val)
        if match:
            tp += 1
        elif ex_val:
            fp += 1
        elif gt_val:
            fn += 1
    return tp, fp, fn


async def main():
    accessions = [a for a, _ in NEW_ACCESSIONS]
    names = dict(NEW_ACCESSIONS)

    # Build the wrapper config exactly as resources.uniprot_entry() does --
    # this is the SAME induced wrapper definition, just applied to new
    # accession values via URL substitution (the real parameterization path).
    sample = uniprot_entry(accessions[0])
    config = {
        "mode": sample["mode"],
        "row_xpath": sample["row_xpath"],
        "columns": sample["columns"],
        "pagination": sample["pagination"],
    }
    target_urls = [uniprot_entry(acc)["url"] for acc in accessions]

    print(f"Batch job: 1 wrapper, {len(target_urls)} accessions, 1 call to the "
          f"real production extraction engine (_run_scraping_async).")
    print("URLs:")
    for u in target_urls:
        print(f"  {u}")

    t0 = time.monotonic()
    records = await _run_scraping_async(
        config=config,
        target_urls=target_urls,
        max_items=0,
        col_mapping=None,
    )
    elapsed = time.monotonic() - t0

    print(f"\nExtraction complete: {len(records)} records assembled from "
          f"{len(target_urls)} pages in {elapsed:.1f}s (one batch job).")

    print("\nFetching independent ground truth from the UniProt REST API for the same accessions...")
    gt_records = []
    for acc in accessions:
        gt_records.append(ground_truth_uniprot_entry(acc)[0])
        time.sleep(0.3)

    print("\n--- Assembled Tier 1 table (one row per page, aggregated by one wrapper) ---")
    rows_out = []
    total_tp = total_fp = total_fn = 0
    for i, acc in enumerate(accessions):
        ex_rec = records[i] if i < len(records) else {}
        gt_rec = gt_records[i]
        tp, fp, fn = score_one(ex_rec, gt_rec)
        total_tp += tp; total_fp += fp; total_fn += fn
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        print(f"  [{i+1}] {acc} ({names[acc]}): extracted={ex_rec}  P={prec:.2f} R={rec:.2f}")
        rows_out.append({"accession": acc, "gene": names[acc], "extracted": ex_rec,
                          "ground_truth": gt_rec, "tp": tp, "fp": fp, "fn": fn})

    overall_prec = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0.0
    overall_rec = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0.0
    overall_f1 = (2 * overall_prec * overall_rec / (overall_prec + overall_rec)
                  if (overall_prec + overall_rec) else 0.0)

    print(f"\n=== RESULT ===")
    print(f"Rows assembled: {len(records)} / {len(accessions)} requested")
    print(f"Overall field-level precision: {overall_prec*100:.1f}%")
    print(f"Overall field-level recall:    {overall_rec*100:.1f}%")
    print(f"Overall field-level F1:        {overall_f1*100:.1f}%")
    print(f"Wall-clock time for the batch: {elapsed:.1f}s")

    out_path = os.path.join(os.path.dirname(__file__), "tier1_aggregation_result.json")
    with open(out_path, "w") as f:
        json.dump({
            "experiment": "Tier 1 multi-page aggregation demonstration",
            "wrapper_config": config,
            "n_requested": len(accessions),
            "n_assembled": len(records),
            "elapsed_seconds": elapsed,
            "overall_precision": overall_prec,
            "overall_recall": overall_rec,
            "overall_f1": overall_f1,
            "rows": rows_out,
        }, f, indent=2)
    print(f"\nSaved full result to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
