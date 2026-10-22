# 03 — Local PDF, table and OCR extraction

**Last Updated:** 2026-10-22
**Owner:** repository owner
**Refresh Trigger:** `modules/extract.py` changes its PDF library or OCR path; `ocr_enabled` default changes; owner answers Q5 in [07-owner-questions.md](07-owner-questions.md).

> **Point-in-time research (2026-10-22).** Markers as in [00-README.md](00-README.md).

## Today

- Text PDFs: `pdfplumber` (`page.extract_tables()` and `page.extract_text()`), in `modules/extract.py`. `pypdf` is declared in `requirements.txt:38`.
- OCR: `pdf2image` + `pytesseract`, gated by `core.config.is_ocr_available()`. `ocr_enabled` defaults to `False` (`core/config.py:132`), so a scanned PDF lands in `pending_ocr`.
- Observed limits on synthetic Quest/LabCorp-style PDFs (local repros at `d2843e8` with `ExtractModule.extract_from_pdf` on reportlab-generated PDFs, re-run by the orchestrator **[V]**; scripts not committed). Example grid row: `Platelet Count | 1,234 | | x10E3/uL | 150-379`, and `Creatinine | <0.5`, `WBC | 5.9 H`: ruled grid tables parse cleanly (12 of 12 rows). Silent loss or distortion comes from the parser rules, not from pdfplumber. `1,234` is read as 1.0, `<0.5` as 0.5, and the flag in `5.9 H` is dropped. A page with any table skips the text pass. A text PDF with one scanned page keeps only the text pages, with no warning.

Changing the PDF library would not fix these. They are fixes to `extract.py`, and L0 sequences them in the build-program queue. Parser code: `modules/extract.py:287-290` (value cell), `:168` (text pass skipped when a table yields a row), `:67-70` (unit list).

## Options

| Tool | Licence | Latest | Offline | Install | Table support | Verdict |
|---|---|---|---|---|---|---|
| pdfplumber | MIT **[V]** | 0.11.10, 2026-06-15 **[V]** | yes | pure-Python wheel (pdfminer.six, Pillow, pypdfium2) **[A]** | `vertical_strategy` / `horizontal_strategy`: `lines`, `lines_strict`, `text`, `explicit` **[A]** | **keep**; try `text` strategies for borderless tables |
| pypdfium2 | BSD-3-Clause, Apache-2.0 **[V]** | 5.14.0, 2026-10-04 **[V]** | yes | wheels bundle PDFium | renderer only | already a pdfplumber dependency; could replace `pdf2image` (no Poppler) for OCR rasterising **[U]** |
| pypdf | BSD-3-Clause **[A]** | 6.21.2 **[A]** | yes | pure Python | none | keep only if used; no import found in `extract.py` **[A]** |
| PyMuPDF | "Dual Licensed - GNU AFFERO GPL 3.0 or Artifex Commercial License" **[V]** | 2.0, 2026-10-19 **[V]** | yes | wheels | strong | **avoid**: AGPL for a distributed app unless an Artifex licence is bought |
| Camelot | MIT **[A]** | 2.0.0 **[A]** | yes | heavy (pandas, opencv-headless); Ghostscript optional **[A]** | lattice + stream | not needed |
| tabula-py | MIT **[A]** | 2.10.0 (2024) **[A]** | yes | needs Java | good on ruled tables | **avoid** (Java) |
| Tesseract + pytesseract | Apache-2.0 **[A]** | engine 5.5.3; pytesseract 0.3.13 (2024) **[A]** | yes | system binary (UB Mannheim installer on Windows) **[A]** | none | current path; needs the binary installed |
| tesserocr | MIT **[V]** | 2.12.0, 2026-10-22 **[V]** | yes | Windows wheels that link libtesseract **[A]** | none | faster binding if Tesseract stays |
| RapidOCR | Apache-2.0 **[V]** | 3.10.0, 2026-10-08 **[V]** | yes | about 27 MB with small PP-OCR models **[A]**, plus onnxruntime 1.31.0 (MIT **[V]**) | text only | **post-MVP OCR candidate**: no system binary |
| docTR | Apache-2.0 code **[A]** | 1.1.0 **[A]** | after weights fetch | torch | table and layout models | heavy |
| PaddleOCR | Apache-2.0 **[A]** | 3.7.0 **[A]** | after model fetch | paddlepaddle (heavy) **[U]** | strong layout | heavy |
| EasyOCR | Apache-2.0 **[A]** | 1.7.2 (2024) **[A]** | not by default: weights download on first use **[A]** | torch | — | **avoid** |
| Docling | MIT code **[V]**; model licences per model **[A]** | 2.142.0, 2026-10-22 **[V]** | air-gapped run documented **[A]** | heavy | layout + table models | post-MVP evaluation only |
| Marker | Apache-2.0 code **[V]**; weights under a modified OpenRAIL-M licence that limits commercial use above a revenue/funding threshold **[A]** | 2.0.0 **[V]** | models download on first use | heavy | good | **avoid** (weights licence) |
| unstructured | Apache-2.0 **[A]** | 0.27.34 **[A]** | yes with extras | heavy + system tesseract/poppler | general | not lab-table focused |

## Recommendation

1. **MVP (text PDFs):** keep pdfplumber. Fix the parser rules in `extract.py` (value qualifiers, thousands separators, flags in the value cell, more unit spellings, a per-page text check). Optionally test pdfplumber's `text` table strategy on borderless tables.
2. **Scanned PDFs (post-MVP, owner Q5):** RapidOCR + onnxruntime gives OCR with no system binary. Keep Tesseract as the fallback if it is already installed.
3. **Never bundle:** PyMuPDF (AGPL), Marker (weights licence), tabula-py (Java), EasyOCR (downloads at runtime).

## Sources

- https://pypi.org/project/pdfplumber/ ; https://github.com/jsvine/pdfplumber
- https://pypi.org/project/pypdfium2/ ; https://pypi.org/project/pypdf/
- https://pypi.org/project/PyMuPDF/ ; https://github.com/pymupdf/PyMuPDF
- https://pypi.org/project/camelot-py/ ; https://pypi.org/project/tabula-py/
- https://github.com/tesseract-ocr/tesseract ; https://github.com/UB-Mannheim/tesseract/wiki ; https://pypi.org/project/pytesseract/ ; https://pypi.org/project/tesserocr/
- https://pypi.org/project/rapidocr/ ; https://rapidai.github.io/RapidOCRDocs/main/install_usage/rapidocr/install/ ; https://pypi.org/project/onnxruntime/
- https://github.com/mindee/doctr ; https://pypi.org/project/paddleocr/ ; https://pypi.org/project/easyocr/
- https://github.com/docling-project/docling ; https://github.com/datalab-to/marker ; https://pypi.org/project/unstructured/
