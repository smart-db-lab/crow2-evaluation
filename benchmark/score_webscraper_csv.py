"""
Scores Web Scraper's exported CSV output against the same ground truth
used for CroW, with the same matching logic as the rest of the benchmark
(compute_metrics.py): List Mode (Tier 0) matched by natural key as sets,
Single Page Mode (Tier 1) matched field by field.

Usage:
    python3 score_webscraper_csv.py <resource_id> <path_to_webscraper_export.csv>

<resource_id> must be one of:
    clinicaltrials_crispr, clinicaltrials_diabetes, clinicaltrials_alzheimer_disease
    uniprot_entry_p01308, uniprot_entry_p04637, uniprot_entry_p38398

Web Scraper's CSV columns are mapped to CroW's field names below -- edit
WEBSCRAPER_COLUMN_MAP if your exported column headers differ from what the
manual protocol specified (rows/title/nct_id/status for Tier 0;
protein_name/gene_name/organism/status for Tier 1).
"""
import csv, json, os, re, sys

sys.path.insert(0, os.path.dirname(__file__))
from resources import RESOURCES
from compute_metrics import score_list_mode, score_single_page_mode, _normalize_text

BASE = os.path.dirname(__file__)
by_id = {r["id"]: r for r in RESOURCES}

TIER0_IDS = {"clinicaltrials_crispr", "clinicaltrials_diabetes", "clinicaltrials_alzheimer_disease"}
TIER1_IDS = {"uniprot_entry_p01308", "uniprot_entry_p04637", "uniprot_entry_p38398"}

# Web Scraper export column -> CroW field name, per resource type.
# Includes both the manual-protocol names and the AI Wizard's actual
# auto-generated column names observed in practice (study_title,
# nct_number), so either workflow's export scores correctly.
TIER0_COLUMN_MAP = {
    "title": "Title", "study_title": "Title",
    "nct_id": "NCT_ID", "nct_number": "NCT_ID",
    "status": "Status",
}
TIER1_COLUMN_MAP = {
    "protein_name": "ProteinName", "proteinname": "ProteinName",
    "gene_name": "GeneName", "genename": "GeneName",
    "organism": "Organism",
    "status": "Status",
}


NCT_ID_RE = re.compile(r"^NCT\d{8}$")


def load_webscraper_csv_tier0(path):
    """List Mode scoring (score_list_mode) only uses the key_field (NCT_ID)
    for set-based matching -- Title/Status don't affect this metric. The AI
    Wizard assigns different, non-semantic column names on different runs
    (observed: "nct_number" on one export, generic "data"/"data2" on
    another), so NCT_ID is located by content pattern (NCT + 8 digits) as a
    fallback whenever no column is named something recognizable. This is a
    real, reportable property of the tool: its auto-generated column names
    are not stable across runs on different queries."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    nct_col = None
    for key in (rows[0].keys() if rows else []):
        if key.strip().lower() in ("nct_id", "nct_number"):
            nct_col = key
            break
    if nct_col is None:
        for key in (rows[0].keys() if rows else []):
            if all(NCT_ID_RE.match((row.get(key) or "").strip()) for row in rows if row.get(key)):
                if any((row.get(key) or "").strip() for row in rows):
                    nct_col = key
                    break

    records = []
    for row in rows:
        rec = {}
        for ws_col, crow_field in TIER0_COLUMN_MAP.items():
            for key in row:
                if key.strip().lower() == ws_col:
                    rec[crow_field] = row[key]
                    break
        if nct_col is not None:
            rec["NCT_ID"] = row.get(nct_col, rec.get("NCT_ID", ""))
        records.append(rec)
    return {"records": records}


def load_webscraper_csv_tier1(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if not rows:
            return {"records": [{}]}
        row = rows[0]
        rec = {}
        for ws_col, crow_field in TIER1_COLUMN_MAP.items():
            for key in row:
                if key.strip().lower() == ws_col:
                    rec[crow_field] = row[key]
                    break
        return {"records": [rec]}


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    resource_id, csv_path = sys.argv[1], sys.argv[2]
    if resource_id not in by_id:
        print(f"Unknown resource_id: {resource_id}")
        sys.exit(1)

    res = by_id[resource_id]
    gt = json.load(open(os.path.join(BASE, "ground_truth", f"{resource_id}.json")))

    if resource_id in TIER0_IDS:
        extracted = load_webscraper_csv_tier0(csv_path)
        tp, fp, fn, ex_count, gt_count = score_list_mode(res, extracted, gt)
    elif resource_id in TIER1_IDS:
        extracted = load_webscraper_csv_tier1(csv_path)
        tp, fp, fn, ex_count, gt_count = score_single_page_mode(res, extracted, gt)
    else:
        print(f"{resource_id} is not part of this comparison's resource set.")
        sys.exit(1)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    print(f"{resource_id}: extracted={ex_count} ground_truth={gt_count} "
          f"TP={tp} FP={fp} FN={fn} "
          f"precision={precision*100:.1f}% recall={recall*100:.1f}% F1={f1*100:.1f}%")


if __name__ == "__main__":
    main()
