# Extraction Eval Card (HC-M06)

**Owner:** repository owner
**Refresh Trigger:** `tests/test_extraction_golden.py::test_hc_extr_003_eval_card_matches_measurement` fails (dataset, parser or extractor changed).

What it measures: precision/recall of `ExtractModule.extract_from_pdf` on a synthetic, fictional
golden set (`src/backend/tests/fixtures/extraction_golden/manifest.json`) for three fields:
analyte, unit, collection date. Thresholds live in the test and are never lowered.

## Current (checked by HC-EXTR-003; paste the test's output, do not hand-edit numbers)

<!-- eval-card:current:start -->
```json
{
  "dataset_version": "2026.10-v1",
  "parser_version": "0.1.0",
  "fields": {
    "analyte": {
      "tp": 28,
      "fp": 0,
      "fn": 0
    },
    "unit": {
      "tp": 28,
      "fp": 0,
      "fn": 0
    },
    "date": {
      "tp": 28,
      "fp": 0,
      "fn": 0
    }
  }
}
```
<!-- eval-card:current:end -->

## Run log

| Date | Dataset | Parser | analyte tp/fp/fn | unit tp/fp/fn | date tp/fp/fn | Interpreter | Command |
|---|---|---|---|---|---|---|---|
| 2026-10-17 | 2026.10-v1 | 0.1.0 | 26/0/2 | 26/0/2 | 26/0/2 | Python 3.11.17 | `python -m pytest tests/test_extraction_golden.py -q` |
| 2026-10-18 | 2026.10-v1 | 0.1.0 | 28/0/0 | 28/0/0 | 28/0/0 | Python 3.11.17 | `python -m pytest tests/test_extraction_golden.py -q` |

## Not covered

- Table-layout PDFs (`_extract_from_table`), scanned/OCR PDFs, images.
- Value, reference range and flag correctness.
- Known miss: lines whose unit is outside `ExtractModule.VALUE_PATTERN` (for example `ug/dL`, `mIU/L`) are dropped whole (lab_06).
- Environment: counts are CI's (Linux, Python 3.11). `pdfplumber>=0.10.0` is unpinned, so another version may differ.
