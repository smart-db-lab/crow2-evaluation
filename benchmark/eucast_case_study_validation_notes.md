# EUCAST case study — validation notes

This is a manual, same-session cross-check against the live EUCAST site,
performed by directly reading the rendered page and comparing it to
`eucast_case_study_result.json`. It is **not** independent API-based
ground truth (EUCAST has no public API for distribution-level MIC data)
and does **not** establish a general accuracy figure. It is scoped to
the four rows checked below.

Live page: `https://mic.eucast.org/search/?search[method]=mic&search[antibiotic]={123|109}&search[species]=-1&search[disk_content]=-1&search[limit]=500`,
read on 2026-11-17 via direct DOM inspection in a browser tab, independently
of the CroW extraction run.

## Meropenem (antibiotic id 123)

**Klebsiella pneumoniae** — live page vs. CroW extraction: identical on
all 19 dilution counts (0,0,211,954,2951,11322,520,220,138,93,57,44,33,43,48,11,5,1,0),
Distributions=42, Observations=16651, ECOFF=0.125, Confidence interval=0.03–0.125.

**Escherichia coli** — live page vs. CroW extraction: identical on all
19 dilution counts (0,0,670,3929,2296,273,78,45,16,15,11,11,13,14,16,9,0,0,0),
Distributions=45, Observations=7396, ECOFF=0.06, Confidence interval=0.03–0.06.

## Imipenem (antibiotic id 109)

**Klebsiella pneumoniae** — live page vs. CroW extraction: identical on
all 19 dilution counts (0,0,39,68,98,2400,23905,16398,12842,1871,441,109,45,68,12,11,3,0,0),
Distributions=45, Observations=58310, ECOFF=1, Confidence interval=0.5–1.

**Escherichia coli** — live page vs. CroW extraction: identical on all
19 dilution counts (0,0,36,91,315,4895,14910,9106,2047,433,212,68,21,22,8,10,2,0,0),
Distributions=57, Observations=32176, ECOFF=0.5, Confidence interval=0.25–0.5.

## Internal consistency check

For both Klebsiella pneumoniae records, the sum of the 19 extracted
dilution counts equals the extracted Observations field exactly
(Meropenem: 16651 = 16651; Imipenem: 58310 = 58310), a check run
programmatically in `eucast_case_study_final.py` across the full record
set, not only the two species cross-checked manually above.

## What this does and does not establish

- Four species-records (2 species x 2 antibiotics), hand-checked against
  the live page, matched exactly on every field checked.
- This supports that the fixed wrapper (`tr[td]` row selector) extracts
  the fields it targets correctly for the rows checked.
- It does not establish an accuracy percentage across all 103 (Meropenem)
  or 94 (Imipenem) extracted species, and no independent reference
  dataset exists to compute one against.
