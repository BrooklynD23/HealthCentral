"""Stdlib-only PDF writer for synthetic extraction fixtures (HC-M06).

One Helvetica text line per string, one page per list. Enough for pdfplumber's
text extraction; draws no ruling lines, so table-layout PDFs are out of scope.
"""

from __future__ import annotations

import io


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def minimal_pdf(pages: list[list[str]]) -> bytes:
    objects: list[bytes] = []
    font_id = 3 + 2 * len(pages)
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(len(pages)))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    for i, lines in enumerate(pages):
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {4 + 2 * i} 0 R >>".encode()
        )
        ops = ["BT", "/F1 11 Tf", "14 TL", "50 740 Td"] + [f"({_escape(l)}) Tj T*" for l in lines] + ["ET"]
        stream = "\n".join(ops).encode("latin-1")
        objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    out.write("".join(f"{o:010d} 00000 n \n" for o in offsets).encode())
    out.write(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return out.getvalue()


def text_then_image_pdf(text_lines: list[str]) -> bytes:
    """Raw-bytes two-page PDF: page 1 text lines, page 2 one image and no text operators."""
    page1 = ["BT", "/F1 11 Tf", "14 TL", "50 740 Td"]
    page1 += [f"({_escape(line)}) Tj T*" for line in text_lines]
    page1.append("ET")
    page2 = ["q", "300 0 0 300 100 400 cm", "/Im1 Do", "Q"]
    stream1 = "\n".join(page1).encode("latin-1")
    stream2 = "\n".join(page2).encode("latin-1")
    pixels = bytes([0, 64, 128, 255] * 4)  # 4x4 greyscale, 8 bits per component
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 6 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /XObject << /Im1 7 0 R >> >> /Contents 8 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(stream1) + stream1 + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /XObject /Subtype /Image /Width 4 /Height 4 /ColorSpace /DeviceGray "
        b"/BitsPerComponent 8 /Length 16 >>\nstream\n" + pixels + b"\nendstream",
        b"<< /Length %d >>\nstream\n" % len(stream2) + stream2 + b"\nendstream",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objs, start=1):
        offsets.append(out.tell())
        out.write(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    out.write("".join(f"{o:010d} 00000 n \n" for o in offsets).encode())
    out.write(f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return out.getvalue()
