# RapidOCR premises: licence, offline behaviour, size, accuracy (RAPIDOCR-RESEARCH)

**Last Updated:** 2026-10-23
**Owner:** repository owner
**Refresh Trigger:** OCR-DEFAULT-ON or RAPIDOCR-BUNDLE is planned or answered; `rapidocr`, `onnxruntime` or `opencv-python-headless` ships a new major version; the PP-OCR model set changes; `modules/extract.py` text patterns change.

> **Point-in-time measurement (2026-10-23).** Planning and documentation only. Nothing under `src/` changed and no dependency was added to the project. Everything was measured in a scratch venv outside the repo (`/tmp/claude-1000/rapidocr-scratch`). Markers: **[V]** a command I ran on 2026-10-23 (output pasted or summarised); **[A]** read from a source without independent re-check; **[U]** not confirmed.

## Result up front

Owner answer OCR-FOR-MVP (b) "Bundle RapidOCR" rested on four premises.

| Premise | Result | Number |
|---|---|---|
| Licence is Apache-2.0 | **PASS, with one flag** [V] | rapidocr and the 3 bundled models are Apache-2.0. Flag: the `opencv-python-headless` wheel redistributes FFmpeg under LGPL (`LICENSE-3RD-PARTY.txt:243`). |
| Offline at runtime | **PASS** [V] | Models ship inside the wheel; OCR ran under `unshare -rn` with no download, no `~/.cache` write, no package-dir write. |
| Added size is about 150 MB or less | **FAIL on installed size** [V] | 271.0 MB installed is new to the project venv (31.0 MB of it models). Wheels are 86.0 MB (win_amd64) to 112.2 MB (manylinux x86_64) compressed. |
| Accuracy usable on lab tables | **PARTIAL** [V] | 117/140 analytes found (83.6%); 116 correct value; 117 correct unit; 1 silent wrong value (Chloride 98 read as 86, OCR score 1.0). Ruled grids are the weak layout (38/56). |

**Failed premise: size.** L0 takes it back to the owner with the numbers above; RAPIDOCR-BUNDLE stays blocked until then. The doc continues regardless.

**Recommendation: adopt with changes** (see the end). No owner answer is drafted here.

## 1. Licences

Commands [V]:

```
uv venv --python 3.11 venv            # python3.11 is not on PATH; uv's CPython 3.11.17
uv pip freeze > out/freeze-before.txt # 0 packages
uv pip install rapidocr onnxruntime pip-licenses
uv pip freeze > out/freeze-after.txt  # 23 packages
venv/bin/pip-licenses --format=markdown --with-urls
```

`pip-licenses` and its two dependencies (`prettytable`, `wcwidth`) are measurement tooling and are not part of the product set. The other 20 packages:

| Package | Version | Licence (pip-licenses) |
|---|---|---|
| rapidocr | 3.10.0 | Apache-2.0 |
| onnxruntime | 1.31.0 | MIT |
| opencv-python-headless | 5.0.0.93 | Apache Software License (wheel also bundles FFmpeg, LGPL; see below) |
| numpy | 2.4.6 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| pillow | 13.0.0 | MIT-CMU |
| shapely | 2.2.0 | BSD-3-Clause |
| pyclipper | 1.4.0 | MIT |
| omegaconf | 2.4.0 | BSD |
| PyYAML | 6.0.3 | MIT |
| protobuf | 7.36.2 | BSD-3-Clause |
| flatbuffers | 25.12.19 | Apache |
| requests | 2.34.2 | Apache |
| urllib3 | 2.8.0 | MIT |
| idna | 3.20 | BSD-3-Clause |
| charset-normalizer | 3.5.2 | MIT |
| certifi | 2026.10.23 | MPL-2.0 |
| tqdm | 4.70.1 | MPL-2.0 AND MIT |
| colorlog | 6.12.0 | MIT |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| six | 1.17.0 | MIT |

The two MPL-2.0 packages (`certifi`, `tqdm`) are already in the project venv [V] (`importlib.metadata`: certifi 2026.7.22, tqdm 4.70.1), so they are not new.

**FFmpeg flag [V].** `opencv_python_headless-5.0.0.93.dist-info/LICENSE-3RD-PARTY.txt:243` reads "FFmpeg is redistributed within all opencv-python packages", followed by the LGPL text. `opencv_python_headless.libs/` contains `libavcodec`, `libavformat`, `libavutil`, `libswscale`, `libswresample`. A bundled installer would redistribute LGPL libraries, so it must ship the notices and keep the libraries replaceable (dynamic `.so`/`.dll`). Not a blocker; it is a packaging obligation for RAPIDOCR-BUNDLE. Whether a PyInstaller one-file build satisfies the "replaceable" condition is **[U]**.

**Model files.** The wheel's `rapidocr-3.10.0.dist-info/licenses/MODEL_LICENSES.md` [V] says the weights are copyright Baidu/PaddleOCR rights holders, distributed under Apache-2.0, with a required modification notice for converted files (section 7).

| File in `rapidocr/models/` | Bytes | Upstream | Licence evidence |
|---|---|---|---|
| `PP-OCRv6_det_small.onnx` | 9,929,594 | `PP-OCRv6_small_det` | HF API tag `license:apache-2.0` for `PaddlePaddle/PP-OCRv6_small_det_onnx` [V] |
| `PP-OCRv6_rec_small.onnx` | 21,234,383 | `PP-OCRv6_small_rec` | HF API tag `license:apache-2.0` for `PaddlePaddle/PP-OCRv6_small_rec_onnx` [V] |
| `ch_ppocr_mobile_v2.0_cls_mobile.onnx` | 585,532 | `ch_ppocr_mobile_v2.0_cls` | MODEL_LICENSES.md only; no HF card exists (the file says it predates HF hosting). PaddleOCR repo licence is Apache-2.0 (GitHub licence API, `spdx_id` Apache-2.0) [V]. The per-model statement is [A]. |

Source URL (from `default_models.yaml`, ModelScope, release v3.10.0), for example the det model: `https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.10.0/onnx/PP-OCRv6/det/PP-OCRv6_det_small.onnx`. The SHA-256 of all three installed files equals the value in `default_models.yaml` and in MODEL_LICENSES.md section 6 [V] (`sha256sum`).

**PyPI re-read [V]** (`scripts/pypi_sizes.py`): rapidocr latest 3.10.0, `license_expression` Apache-2.0, one wheel `rapidocr-3.10.0-py3-none-any.whl` 27,288,134 bytes, `requests` is a hard dependency; `python-bidi` is an extra only. This matches the planner's read.

## 2. No network at runtime

Method: `unshare -rn` worked (user namespaces are available), so no `socket.socket` patch was needed. Inside it, name resolution fails [V]:

```
unshare -rn venv/bin/python -I -c "import socket; socket.create_connection(('pypi.org',443),3)"
blocked: gaierror [Errno -3] Temporary failure in name resolution
```

OCR of `page01_grid.png` under `unshare -rn`:

```
File exists and is valid: .../site-packages/rapidocr/models/ch_ppocr_mobile_v2.0_cls_mobile.onnx
File exists and is valid: .../site-packages/rapidocr/models/PP-OCRv6_rec_small.onnx
init_s=0.01 first_call_s=2.78 n_boxes=72
```

Findings:

- **First use does not download.** The three models ship in the wheel under `rapidocr/models/`. The default config (`config.yaml`: Det/Rec `PP-OCRv6` small, Cls `PP-OCRv4` mobile) points at exactly those files. Models load lazily on the first call (`rapidocr/main.py:123-133`), which is why construction takes 0.01 s and the first call 2.8 to 4.8 s.
- **Where a download would come from.** `rapidocr/inference_engine/onnxruntime/main.py:61` calls `DownloadFile.run` unconditionally; it returns early at `rapidocr/utils/download_file.py:37` when the file exists and its SHA-256 matches (`:48-63`). The only network call is `requests.get` at `rapidocr/utils/download_file.py:70`. The URL is ModelScope (`default_models.yaml`).
- **Proof the download path is real.** With an empty `Global.model_root_dir` under `unshare -rn`, the first call raises `DownloadFileException: Failed to download https://www.modelscope.cn/.../PP-OCRv6_det_small.onnx`, and the empty directory stays empty [V].
- **Which config keeps it offline.** Defaults are offline only while the shipped files are present and uncorrupted: a missing or hash-mismatched file silently turns into a network fetch. A stronger guarantee is to pin `Det.model_path`, `Rec.model_path` and `Cls.model_path`; `onnxruntime/main.py:31` then skips the download branch entirely. Verified under `unshare -rn` with the three files copied elsewhere: `OK pinned model_path, boxes: 19` and no `File exists` log line [V]. The ONNX recogniser carries its own character list, so the dictionary download at `ch_ppocr_rec/main.py:85` is not reached.
- **Other download sites.** `utils/vis_res.py:49,63,75` (visualisation fonts only) and the paddle, mnn, openvino and tensorrt engines. None run on the ONNX OCR path [V by grep]. `rapidocr/cli.py:41` has a sample-image URL (CLI only).
- **Writes.** `~/.cache` listing hash unchanged after all runs and no `rapid`/`onnx` entry in it. No non-`__pycache__` file in `rapidocr/` changed (`find -newer` empty). Python writes `.pyc` files into site-packages on first import; pre-compile or set `PYTHONDONTWRITEBYTECODE` in the bundle [V].
- `requests` is imported at module import (`download_file.py:10`, reached from `rapidocr/main.py:19`), so it must be installed even though it is never called offline.

## 3. Size

Installed size, from each package's RECORD files excluding `__pycache__` (`scripts/pkgsize.py`) [V]:

| New to the project venv | MB |
|---|---|
| opencv-python-headless | 159.5 |
| onnxruntime | 64.5 |
| rapidocr (incl. 31.0 MB models) | 32.4 |
| shapely | 7.8 |
| pyclipper | 3.7 |
| protobuf | 1.4 |
| omegaconf | 1.0 |
| urllib3, requests, flatbuffers, colorlog, six | 0.8 |
| **Total new** | **271.0** |

Already in the project venv (numpy 57.4, pillow 20.4, PyYAML 2.9, certifi, charset-normalizer, idna, packaging, tqdm): 82.7 MB, so all 20 runtime packages together are about 353.7 MB. Whole scratch `site-packages` after install: 355,820 KB on disk, 363,292 KB apparent, including the measurement tooling [V]. Model files: 31,016 KB for `rapidocr/models/` (`du -sk`). Peak RSS for one page: 601,876 KB (`/usr/bin/time -v`, 1 thread) [V].

Wheel sizes from PyPI JSON for the installed versions [V]:

| Platform | rapidocr | onnxruntime 1.31.0 | opencv-python-headless 5.0.0.93 | Sum (bytes) |
|---|---|---|---|---|
| win_amd64 | 27,288,134 | 14,885,750 | 43,825,962 | 85,999,846 |
| macOS arm64 | 27,288,134 | 20,871,717 (`macosx_14_0_arm64`) | 48,322,581 (`macosx_13_0_arm64`) | 96,482,432 |
| manylinux x86_64 | 27,288,134 | 23,753,636 (`manylinux_2_28`) | 61,204,038 (`manylinux_2_28`; the 2014 wheel is 56,563,598) | 112,245,808 |

Shapely, pyclipper and the small pure-Python packages are not in the sums (win/mac wheel sizes not read: **[U]**).

**Against the premise.** The planner's "about 150 MB added" is read here as installed size, which is what a bundled installer carries. 271.0 MB is 1.8 times that: **FAIL**. Compressed wheels (86 to 112 MB) are under 150 MB. The biggest lever is OpenCV (159.5 MB, of which `opencv_python_headless.libs` is 82.7 MB and carries FFmpeg, libaom, libvpx and OpenBLAS that this pipeline does not use). Whether stripping those libraries still leaves a working `cv2` is **[U]** and not tested; replacing OpenCV is not possible without patching rapidocr (it is a hard dependency).

## 4. Rasterising without Poppler

`pypdfium2` 5.14.0 (PDFium 156.0.8076.0) is a `pdfplumber` 0.11.10 dependency [V]. Four of the synthetic pages were wrapped into single-page image PDFs (`PIL.Image.save(..., "PDF", resolution=200)`) and rendered with `page.render(scale=dpi/72)` (`scripts/raster.py`) [V]:

| Page | dpi | render s | size px | PNG bytes |
|---|---|---|---|---|
| page01_grid | 200 | 0.050 | 1700x2200 | 539,979 |
| page01_grid | 300 | 0.096 | 2550x3301 | 921,135 |
| page02_grid | 200 / 300 | 0.038 / 0.070 | same | 516,715 / 872,359 |
| page03_grid | 200 / 300 | 0.028 / 0.060 | same | 503,146 / 839,923 |
| page10_summary | 200 / 300 | 0.031 / 0.068 | same | 429,895 / 739,507 |

Rasterising is negligible (under 0.1 s per page). Caveat: these PDFs hold one embedded image, which is what a scan is; a vector text PDF would render at different cost [U]. 300 dpi did not help OCR: the four pages scored identically at 200 and 300 dpi (42/56 found both ways, section 5) and cost the same CPU, because the detector rescales the input.

## 5. Accuracy and CPU time

**Order check [V]** (before timings, run from the worktree): `nvidia-smi --query-compute-apps=pid,process_name --format=csv` returned only the header (GPU idle); `gh pr list --state open --json title --jq '.[].title'` listed no MEASURE or model-host item (`grep -ciE "MEASURE|model-host"` = 0; the open PRs are claims and one blocked item). The box was shared, though: load average was 13.7 to 16.2 on 24 threads because other agents were running vitest, `tsc` and `docs_lint`. Wall-clock times below are therefore upper-ish bounds; CPU seconds are less affected.

**Test set [V].** `scripts/gen_pages.py` draws 10 synthetic letter pages at 200 dpi with 14 analytes each (seeded; no real patient data): 4 ruled grids (Test, Result, Flag, Units, Reference), 3 whitespace column pages, 3 summary boxes (`Analyte: value unit (range) flag`). Each gets Gaussian blur 0.6 to 1.0, rotation of 0.2 to 0.4 degrees and JPEG quality 50 to 75. Ground truth is one JSON per page.

**Pipeline [V].** Scratch venv: RapidOCR (default models) gives boxes; `scripts/ocr_pages.py` groups boxes into lines (cluster by y within half the median box height, order by x) and writes text. Project venv, cwd `src/backend`: `modules.extract.ExtractModule()._extract_from_text(text, page, doc)` (`extract.py:382`, read-only). Scoring (`scripts/score.py`): found = an observation whose normalised analyte name equals the truth name; value correct = equal to truth; unit correct = equal after case and micro-sign normalisation. The line-grouping step is mine, not the product's; the real integration needs an equivalent.

Per page, RapidOCR text (200 dpi), with the same extractor on the exact clean text as a ceiling [V]:

| Page | Layout | Found / 14 | Value correct | Unit correct | Spurious | Clean-text ceiling |
|---|---|---|---|---|---|---|
| 01 | grid | 9 | 9 | 9 | 0 | 14/14/14 |
| 02 | grid | 9 | 9 | 9 | 0 | 14/14/14 |
| 03 | grid | 10 | 10 | 10 | 0 | 14/14/14 |
| 04 | grid | 10 | 10 | 10 | 0 | 14/14/14 |
| 05 | column | 12 | 11 | 12 | 0 | 14/14/14 |
| 06 | column | 13 | 13 | 13 | 0 | 14/14/14 |
| 07 | column | 13 | 13 | 13 | 0 | 14/14/14 |
| 08 | summary | 13 | 13 | 13 | 1 (`HDLCholesterol`) | 14/14/14 |
| 09 | summary | 14 | 14 | 14 | 0 | 14/14/14 |
| 10 | summary | 14 | 14 | 14 | 0 | 14/14/14 |
| **Total** | | **117/140 (83.6%)** | **116** | **117** | **1** | 140/140 |

By layout: grid 38/56 (67.9%), column 38/42 (90.5%), summary 41/42 (97.6%).

What failed:

- **Unit misreads drop the row.** Most misses are a garbled unit: `g/dL` read as `7p/6`, `mg/dL` as `m9/dl` or `m9/6dl`, `U/L` as `7/n` or `7/0`, `ng/dL` as `7p/6u`. The extractor requires a known unit, so the row is not found. This fails closed (a missing row, not a wrong one).
- **One silent wrong value.** Page 05 Chloride: the image shows `98` (crop checked by eye), OCR returned `86` with score 1.0, the extractor produced `value=86.0 mmol/L`. That is 1 wrong value in 117 found (0.9%) and it carries full OCR confidence, so a recogniser score cannot be used as a trust signal.
- **Merged words.** Page 08: `HDLCholesterol: 41mg/dL(40-90)` has no spaces, so the name does not match the truth name and the row is counted missing plus one spurious. The extractor did parse it.
- **Grid rules matter.** Removing ruled lines first (`scripts/derule.py`: OpenCV morphological open with 120 px kernels, painted white) raised the four grid pages from 38/56 to 49/56 (87.5%), all values and units correct, no cost in time (about 4 CPU s per page). Remaining misses are `g/dL` and `U/L` unit garbles. This is one synthetic font (DejaVu Sans) on synthetic noise, so treat it as a direction, not a rate.
- **Resolution.** 300 dpi from PDF raster: pages 01, 02, 03, 10 scored 9, 9, 10, 14 found, identical to 200 dpi.

**CPU time per page [V]** (pages 2 to 10, excluding the first call, which also loads models: 2.8 to 4.8 s wall):

| Config | CPU s per page (mean, min to max) | Wall s per page (mean) |
|---|---|---|
| default threads (`intra_op_num_threads: -1`, 24 threads, contended box) | 36.54 (25.17 to 43.09) | 1.67 |
| `intra_op_num_threads=1`, `inter_op_num_threads=1` | 3.62 (2.75 to 4.26) | 3.25 |

The default CPU figure counts ONNX Runtime worker threads spinning across 24 cores; the 1-thread figure is the cost of the work itself. Dense pages (about 70 boxes) take 3.7 to 4.3 CPU s, sparse summary pages (19 boxes) 2.8 to 2.9 s.

**Tesseract comparison: skipped.** `which tesseract` is empty and the brief forbids installing system packages. The existing path (`extract.py:523-575`, `pdf2image` plus `pytesseract`) is therefore unmeasured here, so "better or worse than the current OCR" is **[U]**.

## 6. Recommendation: adopt with changes

Numbers support RapidOCR as an offline reader, not as a trusted extractor, and the size premise failed.

1. **Owner decision first on size.** 271.0 MB installed against about 150 MB. Options for the owner: accept it, or require a smaller build (OpenCV trimming is untested **[U]**).
2. **Pin the three model paths** (`Det/Rec/Cls.model_path`) and ship the SHA-256 values, so a corrupt file can never become a network call. Pre-compile bytecode.
3. **Ship licence notices**: Apache-2.0 text, the MODEL_LICENSES.md modification notice, and the FFmpeg LGPL notices; keep the FFmpeg libraries dynamically linked and replaceable.
4. **Pre-process ruled grids** (line removal) and write the box-to-line grouping with word-spacing repair; both measurably matter.
5. **Treat every OCR observation as unverified.** A 98 to 86 read at score 1.0 means OCR rows must go through the verification workbench before any trend, summary or interpretation uses them. OCR-confidence must not raise extraction confidence. Rows lost to unit garbles must be visible to the user as "page read, N rows not understood" rather than silently omitted. Do not add unit aliases such as `7p/6` to `g/dL`; that is guessing on medical data.

**Inputs OCR-DEFAULT-ON needs** (no answer drafted): the owner's size decision; the per-page CPU cost (3.6 CPU s single-threaded, 36.5 CPU s with default threads, about 600 MB peak RSS, 2.8 to 4.8 s first-call model load); the measured loss (16.4% of rows not found, 0.9% of found rows silently wrong, on synthetic pages); the Tesseract gap (unmeasured); and whether OCR output always lands in the verification workbench.

## Appendix: scratch layout and commands

```
/tmp/claude-1000/rapidocr-scratch/{venv,dl,pages,scripts,out}
python -I  (all Python run on downloaded or generated data)
OCR_THREADS=1 venv/bin/python -I scripts/ocr_pages.py out/ocr1 pages/page*.png
cd src/backend && ~/venvs/asclexis-311/bin/python -I scripts/score.py out/ocr1 pages
```

Nothing was installed into `~/venvs/asclexis-311`. No new test ids and no product code: the RED/GREEN rule is replaced by measuring; the collected-test delta is 0.

### scripts/gen_pages.py

```python
"""Generate 10 SYNTHETIC lab pages + ground truth. No real patient data."""
import json, random, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
W, H = 1700, 2200  # letter @ 200 dpi
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
font, fontb, fonth = (ImageFont.truetype(F, 28), ImageFont.truetype(FB, 28), ImageFont.truetype(FB, 40))

# name, unit, lo, hi, decimals
POOL = [("Glucose","mg/dL",70,100,0),("Creatinine","mg/dL",0.6,1.3,2),("BUN","mg/dL",7,20,0),
 ("Sodium","mmol/L",136,145,0),("Potassium","mmol/L",3.5,5.1,1),("Chloride","mmol/L",98,107,0),
 ("Calcium","mg/dL",8.6,10.2,1),("Total Cholesterol","mg/dL",100,200,0),("HDL Cholesterol","mg/dL",40,90,0),
 ("LDL Cholesterol","mg/dL",50,100,0),("Triglycerides","mg/dL",40,150,0),("Hemoglobin","g/dL",12.0,17.0,1),
 ("Hematocrit","%",36,50,1),("WBC","K/uL",4.0,11.0,1),("Platelets","K/uL",150,400,0),("RBC","M/uL",4.2,5.9,2),
 ("ALT","U/L",7,55,0),("AST","U/L",8,48,0),("TSH","mIU/L",0.4,4.0,2),("Ferritin","ng/mL",24,336,0),
 ("HbA1c","%",4.0,5.6,1),("Albumin","g/dL",3.5,5.0,1),("Magnesium","mg/dL",1.7,2.2,1),("Free T4","ng/dL",0.8,1.8,2)]
LAYOUTS = ["grid"]*4 + ["column"]*3 + ["summary"]*3
NOISE = [  # blur radius, rotation deg, jpeg quality
 (0.6,0.3,70),(0.8,-0.3,60),(1.0,0.4,55),(0.6,-0.2,75),(0.8,0.3,65),(1.0,-0.4,55),(0.6,0.2,70),
 (0.8,-0.3,60),(1.0,0.4,50),(0.6,-0.2,75)]

def rows_for(rng, n=14):
    out = []
    for name, unit, lo, hi, d in rng.sample(POOL, n):
        span = hi - lo
        v = rng.uniform(lo - 0.4*span, hi + 0.4*span)
        v = round(max(v, lo*0.3), d)
        v = int(v) if d == 0 else v
        flag = "H" if v > hi else "L" if v < lo else ""
        fmt = (lambda x: str(int(x))) if d == 0 else (lambda x, d=d: f"{x:.{d}f}")
        out.append(dict(analyte=name, value=float(v), value_str=fmt(v), unit=unit,
                        ref=f"{fmt(lo)}-{fmt(hi)}", flag=flag))
    return out

def draw_header(dr, i):
    dr.text((100, 90), "SYNTHETIC REFERENCE LABORATORY", font=fonth, fill=0)
    dr.text((100, 150), "Patient: TEST PATIENT (synthetic)   Collected: 03/14/2025   Page 1 of 1", font=font, fill=0)
    dr.text((100, 190), f"Specimen: Serum   Report ID: SYN-{i:03d}", font=font, fill=0)

def render(layout, rows, i):
    im = Image.new("L", (W, H), 255); dr = ImageDraw.Draw(im); draw_header(dr, i)
    truth_text = []
    y0 = 300
    if layout == "grid":
        cols = [100, 560, 760, 960, 1260, 1600]  # Test|Result|Flag|Units|Reference
        heads = ["Test", "Result", "Flag", "Units", "Reference"]
        rh = 62
        for k in range(len(rows)+2):
            dr.line([(cols[0], y0+k*rh), (cols[-1], y0+k*rh)], fill=0, width=2)
        for c in cols:
            dr.line([(c, y0), (c, y0+(len(rows)+1)*rh)], fill=0, width=2)
        for c, h in zip(cols, heads): dr.text((c+12, y0+14), h, font=fontb, fill=0)
        for k, r in enumerate(rows):
            y = y0+(k+1)*rh+14
            for c, t in zip(cols, [r["analyte"], r["value_str"], r["flag"], r["unit"], r["ref"]]):
                dr.text((c+12, y), t, font=font, fill=0)
            truth_text.append(" ".join(x for x in [r["analyte"], r["value_str"], r["flag"], r["unit"], r["ref"]] if x))
    elif layout == "column":
        xs = [100, 600, 800, 1000, 1250]
        for x, h in zip(xs, ["Test", "Result", "Units", "Range", "Flag"]): dr.text((x, y0), h, font=fontb, fill=0)
        for k, r in enumerate(rows):
            y = y0+60+k*56
            for x, t in zip(xs, [r["analyte"], r["value_str"], r["unit"], r["ref"], r["flag"]]):
                if t: dr.text((x, y), t, font=font, fill=0)
            truth_text.append(" ".join(x for x in [r["analyte"], r["value_str"], r["unit"], r["ref"], r["flag"]] if x))
    else:  # summary box
        n = len(rows); bh = 80+n*54
        dr.rectangle([100, y0, 1600, y0+bh], outline=0, width=4)
        dr.text((130, y0+20), "Summary of Results", font=fontb, fill=0)
        for k, r in enumerate(rows):
            line = f"{r['analyte']}: {r['value_str']} {r['unit']} ({r['ref']})" + (f" {r['flag']}" if r["flag"] else "")
            dr.text((130, y0+80+k*54), line, font=font, fill=0)
    dr.text((100, 2050), "This is a synthetic test document. Not a real lab report.", font=font, fill=0)
    return im

for i, layout in enumerate(LAYOUTS, 1):
    rng = random.Random(1000+i)
    rows = rows_for(rng)
    clean = render(layout, rows, i)
    blur, rot, q = NOISE[i-1]
    im = clean.filter(ImageFilter.GaussianBlur(blur)).rotate(rot, resample=Image.BICUBIC, fillcolor=255)
    p = OUT / f"page{i:02d}_{layout}"
    im.save(str(p)+".tmp.jpg", quality=q); Image.open(str(p)+".tmp.jpg").convert("L").save(str(p)+".png")
    Path(str(p)+".tmp.jpg").unlink()
    json.dump(dict(page=i, layout=layout, blur=blur, rotation_deg=rot, jpeg_quality=q, rows=rows),
              open(str(p)+".truth.json", "w"), indent=1)
    print(p.name, layout, len(rows), "rows")
```

### scripts/ocr_pages.py

```python
"""Scratch venv: RapidOCR on every page -> out/ocr_<stem>.json (lines + timing)."""
import sys, json, time, os, glob, statistics
from pathlib import Path
from rapidocr import RapidOCR
import logging; logging.disable(logging.INFO)

def lines_from(boxes, txts):
    items=[]
    for b,t in zip(boxes,txts):
        xs=[p[0] for p in b]; ys=[p[1] for p in b]
        items.append((sum(ys)/4, min(xs), max(ys)-min(ys), t))
    if not items: return []
    hs=sorted(i[2] for i in items); mh=hs[len(hs)//2]
    items.sort(key=lambda i:i[0]); rows=[]
    for it in items:
        if rows and abs(it[0]-sum(r[0] for r in rows[-1])/len(rows[-1]))<0.5*mh: rows[-1].append(it)
        else: rows.append([it])
    return [" ".join(i[3] for i in sorted(r,key=lambda i:i[1])) for r in rows]

if __name__=="__main__":
    outdir=Path(sys.argv[1]); files=sys.argv[2:]
    th=int(os.environ.get('OCR_THREADS','0'))
    eng=RapidOCR(params={'EngineConfig.onnxruntime.intra_op_num_threads':th,'EngineConfig.onnxruntime.inter_op_num_threads':(1 if th else -1)} if th else None)
    print('threads', th or 'default(-1)')
    for i,f in enumerate(files):
        t0=time.perf_counter(); c0=time.process_time()
        r=eng(f)
        wall=time.perf_counter()-t0; cpu=time.process_time()-c0
        boxes=[] if r.boxes is None else r.boxes.tolist(); txts=list(r.txts or ())
        rec=dict(file=f, wall_s=wall, cpu_s=cpu, first_call=(i==0), n_boxes=len(txts),
                 lines=lines_from(boxes,txts), raw=txts, scores=[float(s) for s in (r.scores or ())])
        json.dump(rec, open(outdir/(Path(f).stem+".json"),"w"), indent=1)
        print(f"{Path(f).stem}: wall={wall:.2f}s cpu={cpu:.2f}s boxes={len(txts)}{' (first call, includes lazy model load)' if i==0 else ''}")
```

### scripts/score.py

```python
"""Project venv, cwd = worktree src/backend: OCR text -> ExtractModule._extract_from_text -> score vs truth."""
import sys, json, re
from pathlib import Path
sys.path.insert(0, ".")
from modules.extract import ExtractModule
ocr_dir=Path(sys.argv[1]); pages=Path(sys.argv[2]); suf=sys.argv[3] if len(sys.argv)>3 else ""
ex=ExtractModule()
nz=lambda s:re.sub(r"\s+"," ",s.strip().lower())
nu=lambda u:(u or "").lower().replace("µ","u").replace("μ","u")
def clean_lines(layout, rows):
    out=[]
    for r in rows:
        if layout=="grid": out.append(" ".join(x for x in [r["analyte"],r["value_str"],r["flag"],r["unit"],r["ref"]] if x))
        elif layout=="column": out.append(" ".join(x for x in [r["analyte"],r["value_str"],r["unit"],r["ref"],r["flag"]] if x))
        else: out.append(f"{r['analyte']}: {r['value_str']} {r['unit']} ({r['ref']})"+(f" {r['flag']}" if r["flag"] else ""))
    return out
def score(text, rows, pg):
    obs=ex._extract_from_text(text, pg, "doc")
    by={}
    for o in obs: by.setdefault(nz(o.analyte_raw),o)
    found=val=unit=0; miss=[]
    for r in rows:
        o=by.get(nz(r["analyte"]))
        if not o: miss.append(r["analyte"]+" (not found)"); continue
        found+=1
        v_ok = o.value is not None and abs(o.value-r["value"])<1e-9
        u_ok = nu(o.unit)==nu(r["unit"])
        val+=v_ok; unit+=u_ok
        if not (v_ok and u_ok): miss.append(f"{r['analyte']}: got {o.value} {o.unit} want {r['value_str']} {r['unit']}")
    truth={nz(r["analyte"]) for r in rows}
    spurious=[o.analyte_raw for o in obs if nz(o.analyte_raw) not in truth]
    return dict(n=len(rows), found=found, value_ok=val, unit_ok=unit, spurious=len(spurious), spurious_names=spurious, miss=miss)
tot=dict(n=0,found=0,value_ok=0,unit_ok=0,spurious=0); ctot=dict(tot)
print(f"{'page':16s} {'n':>3} | OCR: {'found':>5} {'value':>5} {'unit':>5} {'spur':>4} | clean-text ceiling: found value unit")
for tf in sorted(pages.glob("page*.truth.json")):
    t=json.load(open(tf)); stem=tf.name.replace(".truth.json","")
    if not (ocr_dir/(stem+suf+".json")).exists(): continue
    rec=json.load(open(ocr_dir/(stem+suf+".json")))
    s=score("\n".join(rec["lines"]), t["rows"], t["page"])
    c=score("\n".join(clean_lines(t["layout"],t["rows"])), t["rows"], t["page"])
    for k in tot: tot[k]+=s[k]; ctot[k]+=c[k]
    print(f"{stem:16s} {s['n']:3d} |      {s['found']:5d} {s['value_ok']:5d} {s['unit_ok']:5d} {s['spurious']:4d} |                     {c['found']:5d} {c['value_ok']:5d} {c['unit_ok']:5d}")
    for m in s["miss"]: print("     miss:", m)
    if s["spurious_names"]: print("     spurious:", s["spurious_names"])
print("TOTAL OCR   ", tot); print("TOTAL CLEAN ", ctot)
```

### scripts/derule.py

```python
import sys, cv2, numpy as np
from pathlib import Path
src=Path(sys.argv[1]); out=Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
for f in sorted(src.glob("page0[1-4]_grid.png")):
    g=cv2.imread(str(f),0); b=cv2.threshold(g,0,255,cv2.THRESH_BINARY_INV|cv2.THRESH_OTSU)[1]
    h=cv2.morphologyEx(b,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(120,1)))
    v=cv2.morphologyEx(b,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(1,120)))
    m=cv2.dilate(cv2.bitwise_or(h,v),np.ones((5,5),np.uint8))
    r=g.copy(); r[m>0]=255
    cv2.imwrite(str(out/(f.stem+"_derule.png")),r)
```

### scripts/pkgsize.py

```python
import importlib.metadata as m, os, sys
new="colorlog flatbuffers omegaconf onnxruntime opencv-python-headless protobuf pyclipper rapidocr requests shapely six urllib3".split()
allp="certifi charset-normalizer idna numpy packaging pillow pyyaml tqdm".split()
def size(name):
    d=m.distribution(name); tot=0; seen=set()
    for f in d.files or []:
        p=d.locate_file(f)
        if p.is_file() and "__pycache__" not in str(p) and p not in seen:
            seen.add(p); tot+=p.stat().st_size
    return tot
for label, names in (("NEW vs project venv",new),("already in project venv",allp)):
    t=0
    for n in names:
        s=size(n); t+=s; print(f"  {label[:3]} {n:24s}{s/1e6:9.1f} MB")
    print(f"{label}: {t/1e6:.1f} MB (sum of RECORD files, excl __pycache__)\n")
```

### scripts/raster.py

```python
import sys, time
from pathlib import Path
from PIL import Image
import pypdfium2 as pdfium
src=Path(sys.argv[1]); pdfs=Path(sys.argv[2]); out=Path(sys.argv[3])
print("pypdfium2", pdfium.version.PYPDFIUM_INFO, pdfium.version.PDFIUM_INFO)
for png in sorted(src.glob("page0[1-3]_*.png")) + sorted(src.glob("page10_*.png")):
    pdf=pdfs/(png.stem+".pdf")
    Image.open(png).convert("RGB").save(pdf, "PDF", resolution=200.0)
    doc=pdfium.PdfDocument(str(pdf)); page=doc[0]
    for dpi in (200,300):
        t=time.perf_counter(); bm=page.render(scale=dpi/72); im=bm.to_pil(); dt=time.perf_counter()-t
        p=out/f"{png.stem}_{dpi}.png"; im.save(p)
        print(f"{png.stem} dpi={dpi} render_s={dt:.3f} size={im.size} png_bytes={p.stat().st_size} pdf_bytes={pdf.stat().st_size}")
```
