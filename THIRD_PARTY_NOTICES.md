# Third-party notices

Asclexis reads scanned lab pages on the patient's own machine with RapidOCR.
This file names the third-party packages that feature installs and the licence
each one carries. It is linked from the OCR block of
[`src/backend/requirements.txt`](src/backend/requirements.txt).

Asclexis does not copy these packages into this repository. `pip install -r
src/backend/requirements.txt` fetches each wheel from PyPI, and every wheel
brings its own licence text, installed under
`site-packages/<name>-<version>.dist-info/` (see the last column). If Asclexis
is ever distributed as an installer that bundles these wheels, that installer
takes on the obligations below; the installer work must ship this file and keep
the FFmpeg libraries replaceable.

## Packages in the OCR block

| Package | Pinned version | Licence | Full licence text, once installed |
| --- | --- | --- | --- |
| `rapidocr` | ==3.10.0 | Apache-2.0 | `rapidocr-3.10.0.dist-info/licenses/LICENSE`, `…/MODEL_LICENSES.md` |
| `onnxruntime` | ==1.31.0 | MIT | `onnxruntime-1.31.0.dist-info/` (`METADATA`) |
| `opencv-python-headless` | ==5.0.0.93 | Apache-2.0 (package); LGPL-2.1 (bundled FFmpeg libraries, see below) | `opencv_python_headless-5.0.0.93.dist-info/LICENSE.txt`, `…/LICENSE-3RD-PARTY.txt` |
| `pypdfium2` | >=5.14.0 | BSD-3-Clause OR Apache-2.0 (package); BSD-3-Clause and others (bundled PDFium) | `pypdfium2-<version>.dist-info/licenses/` |
| `pillow` | >=10.2.0 | MIT-CMU (HPND) | `pillow-<version>.dist-info/licenses/LICENSE` |
| `pytesseract` | >=0.3.10 | Apache-2.0 | `pytesseract-<version>.dist-info/LICENSE` |
| `pdf2image` | >=1.17.0 | MIT | `pdf2image-<version>.dist-info/LICENSE` |

Versions marked `==` are the exact versions measured. Versions marked `>=` are
the lowest version the code accepts; the version installed at build time is the
one whose licence file applies. Tesseract itself (an optional system program)
and Poppler (needed by `pdf2image`) are installed by the patient and are not
distributed by Asclexis.

RapidOCR also pulls in other pure-Python and binary dependencies (for example
`shapely`, `pyclipper`, `omegaconf`, `numpy`, `requests`). The resolver picks
them, and each wheel carries its own licence in its `*.dist-info/`.

## FFmpeg (LGPL) inside opencv-python-headless

The `opencv-python-headless` wheel redistributes FFmpeg: its
`LICENSE-3RD-PARTY.txt` says "FFmpeg is redistributed within all opencv-python
packages", under the GNU Lesser General Public License, version 2.1. The shared libraries
sit next to the package, in the wheel's `opencv_python_headless.libs/`
directory:

- `libavcodec`
- `libavformat`
- `libavutil`
- `libswscale`
- `libswresample`

(The same directory holds further libraries, such as `libpng` and
`libopenblas`, each covered by the wheel's `LICENSE-3RD-PARTY.txt`.) These are
shared libraries that Asclexis uses as the wheel ships them: a user may substitute another
build of the same libraries. Asclexis does not statically link FFmpeg and does
not modify it. The source code of the FFmpeg version in the wheel is available
from <https://ffmpeg.org/> and from the opencv-python project
(<https://github.com/opencv/opencv-python>).

## PaddleOCR models (Apache-2.0)

The `rapidocr` wheel ships three ONNX model files in `rapidocr/models/`,
converted from official PaddleOCR models:

| File | Upstream model | SHA-256 |
| --- | --- | --- |
| `PP-OCRv6_det_small.onnx` | `PP-OCRv6_small_det` | `090f04abcd9d9a7498bc4ebf677e4cb9bdce1fe4197ddb7e529f1ef44e1ff94f` |
| `PP-OCRv6_rec_small.onnx` | `PP-OCRv6_small_rec` | `6f327246b50388f3c176ae304bd95767ea6dc0c9ae92153ef8cbe210b3c14884` |
| `ch_ppocr_mobile_v2.0_cls_mobile.onnx` | `ch_ppocr_mobile_v2.0_cls` | `e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c` |

PaddleOCR and its models are licensed under the Apache License, Version 2.0
(<https://www.apache.org/licenses/LICENSE-2.0>). The models are used unchanged
from the `rapidocr` wheel: Asclexis verifies the three SHA-256 values above
before it loads them and does not modify them.

Modification notice, from RapidOCR's `MODEL_LICENSES.md` section 7, for the
converted files:

> Converted from an official PaddleOCR model to the indicated inference format
> and packaged for use with RapidOCR. The upstream model weights are copyright
> Baidu and/or the applicable PaddleOCR rights holders and are licensed under
> the Apache License, Version 2.0.

This notice does not state or imply endorsement by Baidu, the PaddleOCR
project or RapidOCR (Apache-2.0 grants no right to use their names or marks).
