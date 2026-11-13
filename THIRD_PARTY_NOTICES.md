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

## SQLCipher in the Windows `sqlcipher3` wheel

On Windows, `src/backend/requirements-sqlcipher-win.txt` pins `sqlcipher3==0.6.5`
(wheel `sqlcipher3-0.6.5-cp311-cp311-win_amd64.whl`, sha256
`698d58f9ea5d5208bb06ee542678f3aa7921078b3bee8783f7c3fb861910eca6`). The wheel is
self-contained: it carries SQLCipher 4.20.0 (community edition) and OpenSSL 3.6.0 inside
its `_sqlite3.cp311-win_amd64.pyd`. Asclexis does not copy these into this repository
and does not modify them. If Asclexis is ever distributed as an installer that bundles
this wheel, the installer must ship this file and the three licence texts below.

| Component | Version in the wheel | Licence | Where the text was read |
| --- | --- | --- | --- |
| `sqlcipher3` (the Python binding) | 0.6.5 | zlib-style (Gerhard Haering, 2004-2007; the pysqlite licence) | The wheel's own `sqlcipher3-0.6.5.dist-info/licenses/LICENSE`; the upstream `coleifer/sqlcipher3` `LICENSE` on `master` has the same words. |
| SQLCipher (Zetetic LLC) | 4.20.0 community | BSD-style (3 clauses: keep the notice in source, reproduce it in binary documentation, no use of the Zetetic name for endorsement) | Upstream `sqlcipher/sqlcipher` `LICENSE.md` at tag `v4.12.0`. The wheel bundles 4.20.0; that tag was not read, so the 4.20.0 text is assumed unchanged and is not verified. |
| OpenSSL | 3.6.0 | Apache-2.0 | Upstream `openssl/openssl` `LICENSE.txt` at tag `openssl-3.6.0`, the version string inside the wheel's binary. |

The wheel ships only the `sqlcipher3` licence file; it does not include the SQLCipher or
OpenSSL texts. Neither appears in the wheel's `METADATA`. The sqlcipher3 package on PyPI
has no provenance attestation, so the install is protected by the sha256 pin above.

