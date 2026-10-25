"""
Document extraction module.

Handles:
- PDF text extraction with layout awareness
- Lab value parsing and row extraction
- Provenance tracking (page, span, bbox)
- Confidence scoring
"""

import io
import logging
import re
from dataclasses import dataclass, field
from datetime import date as date_type
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class Provenance:
    """Location information for extracted data."""
    page: int
    span_start: Optional[int] = None
    span_end: Optional[int] = None
    bbox: Optional[tuple[float, float, float, float]] = None  # x0, y0, x1, y1
    text_snippet: str = ""


@dataclass
class ExtractedObservation:
    """Single extracted lab observation."""
    analyte_raw: str
    value: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    ref_low: Optional[float] = None
    ref_high: Optional[float] = None
    ref_range_text: Optional[str] = None
    flag: Optional[str] = None
    specimen_type: Optional[str] = None
    collected_at: Optional[str] = None
    provenance: Optional[Provenance] = None
    confidence: float = 0.0
    extraction_method: str = "pdf_text"


@dataclass
class ExtractionResult:
    """Result of document extraction."""
    document_id: str
    observations: list[ExtractedObservation] = field(default_factory=list)
    collection_dates: list[str] = field(default_factory=list)
    clinician: Optional[str] = None
    department: Optional[str] = None
    notes: list[str] = field(default_factory=list)
    parser_version: str = "0.1.0"
    overall_confidence: float = 0.0
    ocr_unavailable: bool = False
    extracted_text: Optional[str] = None
    # 1-based pages whose text layer has fewer than 20 non-space characters
    # (image-only or blank). Set by extract_from_pdf (IMPORT-SCANNED-PAGE).
    pages_without_text: list[int] = field(default_factory=list)


# Shared unit alternation. Longer alternatives precede their prefixes.
_UNIT_ALT = (
    r"mL/min/1\.73m2|x10E3/uL|x10\^3/uL|10\*3/uL|x10E6/uL|"
    r"mIU/L|[uµμ]IU/mL|ng/dL|[uµμ]g/dL|nmol/L|pmol/L|[uµμ]mol/L|"
    r"[uµμ]g/L|g/L|mg/dL|mg/L|g/dL|mmol/L|mEq/L|U/L|IU/L|ng/mL|pg/mL|%|fL|K/uL|M/uL|cells/uL"
)


class ExtractModule:
    """
    Document extraction service.

    Phase 0: Text-based PDF extraction using pdfplumber
    Phase 1+: OCR support for scanned documents
    """

    # Common lab value patterns
    VALUE_PATTERN = re.compile(
        r"(\d+\.?\d*)\s*(" + _UNIT_ALT + r")?",
        re.IGNORECASE
    )

    RANGE_PATTERN = re.compile(
        r"(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)",
        re.IGNORECASE
    )

    FLAG_PATTERN = re.compile(
        r"\b(H|L|HH|LL|A|HIGH|LOW|ABNORMAL|CRITICAL)\b",
        re.IGNORECASE
    )

    def __init__(self):
        """Initialize extraction module."""
        self.parser_version = "0.1.0"

    def has_extractable_text(self, pdf_source: Union[Path, BinaryIO, io.BytesIO]) -> bool:
        """
        Check if a PDF has extractable text (not scanned/image-only).

        Returns True if average chars per page >= 50, indicating real text content.
        """
        try:
            import pdfplumber
        except ImportError:
            return True  # Assume text-based if pdfplumber unavailable

        try:
            with pdfplumber.open(pdf_source) as pdf:
                if not pdf.pages:
                    return False
                total_chars = sum(len(page.extract_text() or "") for page in pdf.pages)
                avg_chars = total_chars / len(pdf.pages)
                return avg_chars >= 50
        except Exception:
            return True  # Default to text-based on error

    async def extract_from_pdf(
        self,
        pdf_source: Union[Path, BinaryIO, io.BytesIO],
        document_id: str,
    ) -> ExtractionResult:
        """
        Extract lab values from a text-based PDF.

        Args:
            pdf_source: Path to PDF file, or file-like object (BytesIO) containing PDF data.
                       BytesIO is used when reading decrypted documents from memory.
            document_id: Document ID for provenance

        Returns:
            ExtractionResult with observations
        """
        try:
            import pdfplumber
        except ImportError:
            raise RuntimeError("pdfplumber not installed")

        observations = []
        collection_dates = []
        pages_text: list[str] = []
        pages_without_text: list[int] = []

        with pdfplumber.open(pdf_source) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract text
                text = page.extract_text() or ""
                pages_text.append(text)
                if len("".join(text.split())) < 20:
                    pages_without_text.append(page_num)

                # Extract tables (more structured)
                tables = page.extract_tables() or []

                # Process tables for lab values
                table_obs_all: list[ExtractedObservation] = []
                table_yields: list[int] = []
                for table in tables:
                    table_obs = self._extract_from_table(
                        table, page_num, document_id
                    )
                    table_yields.append(len(table_obs))
                    table_obs_all.extend(table_obs)
                    observations.extend(table_obs)
                page_table_count = len(table_obs_all)

                if page_table_count == 0:
                    # No table gave observations: parse the whole page text.
                    # Table pages are noisy (demographics, IDs), so keep only
                    # rows with a recognised unit here.
                    text_obs = self._extract_from_text(
                        text, page_num, document_id
                    )
                    if tables:
                        text_obs = [o for o in text_obs if o.unit]
                    observations.extend(text_obs)
                else:
                    # Tables yielded: parse the text outside those tables only
                    # (a table that yielded nothing keeps its text), keep rows
                    # with a unit, and drop rows a table already gave.
                    found = page.find_tables()
                    region = page
                    if len(found) == len(tables):
                        for idx, n_obs in enumerate(table_yields):
                            if n_obs:
                                region = region.outside_bbox(found[idx].bbox, strict=False)
                    text_obs = self._extract_from_text(
                        region.extract_text() or "", page_num, document_id
                    )
                    seen = {
                        (o.analyte_raw.strip().lower(), o.value) for o in table_obs_all
                    }
                    observations.extend(
                        o for o in text_obs
                        if o.unit and (o.analyte_raw.strip().lower(), o.value) not in seen
                    )

                # Extract dates
                dates = self._extract_dates(text)
                collection_dates.extend(dates)

                # Propagate page-level date to observations missing collected_at
                if dates:
                    page_date = dates[0]  # Use first date found on this page
                    for obs in observations:
                        if obs.provenance and obs.provenance.page == page_num and obs.collected_at is None:
                            obs.collected_at = page_date

        # Final pass: assign earliest date to any observation still missing collected_at
        if collection_dates:
            fallback_date = collection_dates[0]
            for obs in observations:
                if obs.collected_at is None:
                    obs.collected_at = fallback_date

        # Calculate overall confidence
        if observations:
            overall_confidence = sum(o.confidence for o in observations) / len(observations)
        else:
            overall_confidence = 0.0

        return ExtractionResult(
            document_id=document_id,
            observations=observations,
            collection_dates=collection_dates,
            parser_version=self.parser_version,
            overall_confidence=overall_confidence,
            extracted_text="\f".join(pages_text),
            pages_without_text=pages_without_text,
        )

    def _extract_from_table(
        self,
        table: list[list[str]],
        page_num: int,
        document_id: str,
    ) -> list[ExtractedObservation]:
        """Extract observations from a table structure."""
        observations = []

        if not table or len(table) < 2:
            return observations

        # Try to identify header row
        header = table[0] if table else []

        # Find column indices
        name_col = self._find_column(header, ["test", "name", "analyte", "component"])
        value_col = self._find_column(header, ["result", "value"])
        unit_col = self._find_column(header, ["unit", "units"])
        range_col = self._find_column(header, ["range", "reference", "ref"])
        flag_col = self._find_column(header, ["flag", "status", "abnormal"])

        # Process data rows
        for row_idx, row in enumerate(table[1:], start=2):
            if not row or all(not cell for cell in row):
                continue

            obs = self._parse_table_row(
                row,
                name_col=name_col,
                value_col=value_col,
                unit_col=unit_col,
                range_col=range_col,
                flag_col=flag_col,
                page_num=page_num,
            )

            if obs:
                observations.append(obs)

        return observations

    def _find_column(self, header: list[str], keywords: list[str]) -> int:
        """Find column index by header keywords."""
        for idx, cell in enumerate(header):
            if cell:
                cell_lower = cell.lower()
                for keyword in keywords:
                    if keyword in cell_lower:
                        return idx
        return -1

    def _parse_table_row(
        self,
        row: list[str],
        name_col: int,
        value_col: int,
        unit_col: int,
        range_col: int,
        flag_col: int,
        page_num: int,
    ) -> Optional[ExtractedObservation]:
        """Parse a single table row into an observation."""

        def get_cell(idx: int) -> str:
            if 0 <= idx < len(row) and row[idx]:
                return row[idx].strip()
            return ""

        # Get analyte name
        analyte = get_cell(name_col) if name_col >= 0 else get_cell(0)
        if not analyte:
            return None

        # Get value: the whole cell must parse. A comparator (<, >, <=, >=) is a
        # bound, never an exact number; anything that does not fully match stays text.
        value_text = get_cell(value_col) if value_col >= 0 else ""
        value = None
        cell_flag = None
        if value_text:
            _num = r"(?P<num>[1-9]\d{0,2}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
            _flg = r"(?P<flag>\(?(?:HH|LL|H|L|A|HIGH|LOW|ABNORMAL|CRITICAL)\)?|\*)"
            _cmp = r"(?P<cmp>[<>]=?|≤|≥)"
            # Collapse whitespace runs first: adjacent \s* around optional groups
            # backtrack cubically on a long space run. value_text stays raw.
            cell = " ".join(value_text.split())
            cell_match = re.fullmatch(
                r"\s*" + _cmp + r"?\s*" + _num + r"\s*(?P<unit>" + _UNIT_ALT + r")?\s*" + _flg + r"?\s*",
                cell,
                re.IGNORECASE,
            ) or re.fullmatch(
                r"\s*" + _flg + r"\s*" + _cmp + r"?\s*" + _num + r"\s*(?P<unit>" + _UNIT_ALT + r")?\s*",
                cell,
                re.IGNORECASE,
            )
            if cell_match:
                # A comparator makes it a bound, not an exact value: value stays None.
                if not cell_match.group("cmp"):
                    value = float(cell_match.group("num").replace(",", ""))
                raw_flag = cell_match.group("flag")
                if raw_flag:
                    cell_flag = "A" if raw_flag == "*" else raw_flag.strip("()").upper()

        # Get unit
        unit = get_cell(unit_col) if unit_col >= 0 else None

        # Get reference range
        range_text = get_cell(range_col) if range_col >= 0 else ""
        ref_low, ref_high = None, None
        if range_text:
            range_match = self.RANGE_PATTERN.search(range_text)
            if range_match:
                try:
                    ref_low = float(range_match.group(1))
                    ref_high = float(range_match.group(2))
                except ValueError:
                    logger.warning(
                        "Failed to parse reference range",
                        extra={"analyte": analyte, "raw_range": range_text, "page": page_num},
                    )

        # Get flag
        flag = None
        flag_text = get_cell(flag_col) if flag_col >= 0 else ""
        if flag_text:
            flag_match = self.FLAG_PATTERN.search(flag_text)
            if flag_match:
                flag = flag_match.group(1).upper()
        if flag is None:
            flag = cell_flag  # the flag column wins; the in-cell flag is the fallback

        # Calculate confidence
        confidence = 0.5
        if value is not None:
            confidence += 0.2
        if ref_low is not None and ref_high is not None:
            confidence += 0.2
        if unit:
            confidence += 0.1

        return ExtractedObservation(
            analyte_raw=analyte,
            value=value,
            value_text=value_text if value is None else None,
            unit=unit,
            ref_low=ref_low,
            ref_high=ref_high,
            ref_range_text=range_text if range_text else None,
            flag=flag,
            provenance=Provenance(page=page_num, text_snippet=str(row)),
            confidence=min(confidence, 1.0),
            extraction_method="pdf_table",
        )

    # Optional comparator before a value (Quest/LabCorp "<0.5", ">90"). It makes the value a bound.
    _CMP_ALT = r"[<>]=?|≤|≥"
    # A number. The lookaheads keep each digit run in one group, so a long run cannot be
    # split between two groups (quadratic backtracking). Same language as \d+\.?\d*.
    _NUM = r"\d+(?!\d)(?:\.\d*(?!\d))?"

    # Pattern for "Analyte: Value Unit" format
    LINE_PATTERN = re.compile(
        r"^(?P<name>[A-Za-z][A-Za-z0-9\s,\-]+?):\s*"  # Analyte name ending with colon
        r"(?:(?P<cmp>" + _CMP_ALT + r")\s*)?"  # Comparator (a bound, not an exact value)
        r"(?P<value>" + _NUM + r")"  # Numeric value
        r"(?:\s*(?P<unit>" + _UNIT_ALT + r"))?"  # Unit (optional; the whitespace belongs to it)
        r"(?:\s*\((?:Normal:|Ref:?)?\s*(?P<ref_low>[<>]?" + _NUM + r")\s*(?:[-–]\s*)?(?P<ref_high>" + _NUM + r")?\))?"  # Reference range
        r"(?:\s*(?P<flag>H|L|HH|LL|HIGH|LOW|ABNORMAL|CRITICAL))?"  # Flag
        r"\s*$",
        re.IGNORECASE | re.MULTILINE
    )

    # Alternative pattern for "Analyte Value Unit (Range)" without colon
    ALT_LINE_PATTERN = re.compile(
        r"^(?P<name>[A-Za-z]\s|[A-Za-z](?:\s*[A-Za-z0-9,\-])+?)\s+"  # Analyte name (whitespace runs cannot backtrack; HC-ETF-006)
        r"(?:(?P<cmp>" + _CMP_ALT + r")\s*)?"  # Comparator (a bound, not an exact value)
        r"(?P<value>" + _NUM + r")\s*"  # Value
        r"(?P<unit>" + _UNIT_ALT + r")"  # Required unit
        r"(?:\s*\((?P<ref_low>[<>]?" + _NUM + r")\s*(?:[-–]\s*)?(?P<ref_high>" + _NUM + r")?\))?"  # Reference range
        r"(?:\s*(?P<flag>H|L|HH|LL|HIGH|LOW|ABNORMAL|CRITICAL))?"  # Flag
        r"\s*$",
        re.IGNORECASE | re.MULTILINE
    )

    # Column layout: "Analyte Value [Flag] Unit [Flag] [Range] [Flag]" (whitespace-separated,
    # unit required, range bare: a-b, <a, <=a, <OR=a, >a, >=a or >OR=a). Tried after the two
    # patterns above. A one-bound range sets one bound; a comparator before the value does not
    # make the value a number.
    _FLAG_ALT = r"HH|LL|HIGH|LOW|ABNORMAL|CRITICAL|H|L"
    COLUMN_LINE_PATTERN = re.compile(
        r"^(?P<name>[A-Za-z](?:\s*[A-Za-z0-9,\-])*?)\s+"  # Analyte name (no trailing whitespace: linear time)
        r"(?:(?P<cmp>" + _CMP_ALT + r")\s*)?"  # Comparator (a bound, not an exact value)
        r"(?P<value>" + _NUM + r")\s+"  # Value
        r"(?:(?P<flag_before>" + _FLAG_ALT + r")\s+)?"  # Flag before unit
        r"(?P<unit>" + _UNIT_ALT + r")"  # Required unit
        r"(?:\s+(?:(?P<flag_mid>" + _FLAG_ALT + r")\s+)?"  # Flag between unit and range (only with a range)
        r"(?:(?P<lo>" + _NUM + r")\s*[-–]\s*(?P<hi>" + _NUM + r")"  # Range a-b
        r"|(?P<one_lt><(?:OR=|=)?\s*(?P<lt>" + _NUM + r"))"  # Upper bound: <a, <=a, <OR=a
        r"|(?P<one_gt>>(?:OR=|=)?\s*(?P<gt>" + _NUM + r"))))?"  # Lower bound: >a, >=a, >OR=a
        r"(?:\s+(?P<flag_after>" + _FLAG_ALT + r"))?"  # Flag after range
        r"\s*$",
        re.IGNORECASE
    )

    def _extract_from_text(
        self,
        text: str,
        page_num: int,
        document_id: str,
    ) -> list[ExtractedObservation]:
        """
        Extract observations from unstructured text.

        Sprint 2 - S2-BE-002: Implement text-based extraction.

        Supports formats:
        - "Analyte: Value Unit (Range) FLAG"
        - "Analyte Value Unit (Range) FLAG"
        """
        observations = []

        # Process line by line
        for line in text.strip().split('\n'):
            line = line.strip()
            if not line:
                continue

            obs = self._parse_text_line(line, page_num)
            if obs:
                observations.append(obs)

        return observations

    def _parse_text_line(
        self,
        line: str,
        page_num: int,
    ) -> Optional[ExtractedObservation]:
        """Parse a single text line into an observation."""
        # Try colon format first: "Glucose: 95 mg/dL (70-100)"
        match = self.LINE_PATTERN.match(line)
        colon_match = bool(match)
        if not match:
            # Try alternative format: "Glucose 95 mg/dL (70-100)"
            match = self.ALT_LINE_PATTERN.match(line)
        if not match:
            # Column layout: "Glucose 95 mg/dL 70-99"
            match = self.COLUMN_LINE_PATTERN.match(line)
        if not match:
            return None

        fields = match.groupdict()
        analyte = fields["name"].strip() if fields["name"] else None
        value_str = fields["value"]
        cmp = fields.get("cmp")
        unit = fields.get("unit")
        # Flag before the unit wins, then the flag between unit and range, then the flag after the range.
        flag_text = (
            fields.get("flag") or fields.get("flag_before")
            or fields.get("flag_mid") or fields.get("flag_after")
        )
        flag = flag_text.upper() if flag_text else None
        # A one-bound range ("<100", ">=60") keeps its raw text; a-b ranges are rebuilt from the bounds.
        one_bound = fields.get("one_lt") or fields.get("one_gt")
        col_range_text = re.sub(r"\s+", "", one_bound) if one_bound else None
        ref_low_str = fields.get("ref_low") or fields.get("lo") or fields.get("gt")
        ref_high_str = fields.get("ref_high") or fields.get("hi") or fields.get("lt")

        if not analyte or not value_str:
            return None

        # Non-colon lines only: a numeric token after the analyte's first word is a
        # previous-result column ("Glucose 105 H 98 mg/dL", "Glucose 105H 98 mg/dL").
        # Any letters glued to the number count ("105H", "105HI", "105A"), whatever
        # the flag spelling. Ambiguous, so yield no value rather than a wrong one.
        # Colon matches are not guarded.
        if not colon_match and any(
            re.fullmatch(r"[\d.,]+[A-Za-z]*", t)
            for t in analyte.split()[1:]
        ):
            return None

        # A comparator (<, >, <=, >=) is a bound, never an exact number: value stays None
        # and the text is kept as value_text (as in _parse_table_row).
        value = None
        value_text = None
        if cmp:
            value_text = f"{cmp}{value_str}"
        else:
            try:
                value = float(value_str)
            except (ValueError, TypeError):
                return None

        ref_low = None
        ref_high = None
        if ref_low_str:
            try:
                ref_low = float(ref_low_str.lstrip('<>'))
            except (ValueError, TypeError):
                logger.warning(
                    "Failed to parse reference bound",
                    extra={"analyte": analyte, "raw_value": ref_low_str, "page": page_num},
                )
        if ref_high_str:
            try:
                ref_high = float(ref_high_str)
            except (ValueError, TypeError):
                logger.warning(
                    "Failed to parse reference bound",
                    extra={"analyte": analyte, "raw_value": ref_high_str, "page": page_num},
                )

        # Calculate confidence
        confidence = 0.5  # Base for text extraction
        if value is not None:
            confidence += 0.15
        if unit:
            confidence += 0.15
        if ref_low is not None or ref_high is not None:
            confidence += 0.1
        if flag:
            confidence += 0.1  # Flag detection adds confidence

        return ExtractedObservation(
            analyte_raw=analyte,
            value=value,
            value_text=value_text,
            unit=unit,
            ref_low=ref_low,
            ref_high=ref_high,
            ref_range_text=col_range_text or (
                f"{ref_low_str or ''}-{ref_high_str or ''}" if ref_low_str else None
            ),
            flag=flag,
            provenance=Provenance(page=page_num, text_snippet=line),
            confidence=min(confidence, 1.0),
            extraction_method="pdf_text",
        )

    async def extract_from_scanned_pdf(
        self,
        pdf_source: Union[Path, BinaryIO, io.BytesIO],
        document_id: str,
        *,
        effective_ocr: bool = True,
    ) -> ExtractionResult:
        """
        Extract lab values from a scanned PDF using OCR.

        Uses pdf2image to convert pages to images, then pytesseract for OCR.
        OCR observations get base confidence 0.4 (lower than text extraction).
        Returns graceful result with ocr_unavailable=True if OCR deps missing.
        """
        from core.config import is_ocr_available

        if not effective_ocr:
            return ExtractionResult(
                document_id=document_id,
                observations=[],
                collection_dates=[],
                parser_version=self.parser_version,
                overall_confidence=0.0,
                ocr_unavailable=True,
            )

        if not is_ocr_available():
            return ExtractionResult(
                document_id=document_id,
                observations=[],
                collection_dates=[],
                parser_version=self.parser_version,
                overall_confidence=0.0,
                ocr_unavailable=True,
            )

        try:
            import pytesseract
            from pdf2image import convert_from_bytes
        except ImportError:
            return ExtractionResult(
                document_id=document_id,
                observations=[],
                collection_dates=[],
                parser_version=self.parser_version,
                overall_confidence=0.0,
                ocr_unavailable=True,
            )

        # Read PDF bytes
        if isinstance(pdf_source, (Path, str)):
            pdf_bytes = Path(pdf_source).read_bytes()
        else:
            pdf_source.seek(0)
            pdf_bytes = pdf_source.read()

        images = convert_from_bytes(pdf_bytes)
        observations = []
        collection_dates = []
        pages_text: list[str] = []

        for page_num, image in enumerate(images, start=1):
            text = pytesseract.image_to_string(image)
            pages_text.append(text)
            # Use existing text extraction on OCR output
            text_obs = self._extract_from_text(text, page_num, document_id)
            # Lower confidence for OCR-derived observations
            for obs in text_obs:
                obs.confidence = min(obs.confidence * 0.8, 0.7)
                obs.extraction_method = "ocr_pdf"
            observations.extend(text_obs)
            dates = self._extract_dates(text)
            collection_dates.extend(dates)

            # Propagate page-level date to observations missing collected_at
            if dates:
                page_date = dates[0]
                for obs in text_obs:
                    if obs.collected_at is None:
                        obs.collected_at = page_date

        # Final pass: assign earliest date to any observation still missing collected_at
        if collection_dates:
            fallback_date = collection_dates[0]
            for obs in observations:
                if obs.collected_at is None:
                    obs.collected_at = fallback_date

        overall_confidence = (
            sum(o.confidence for o in observations) / len(observations)
            if observations else 0.0
        )

        return ExtractionResult(
            document_id=document_id,
            observations=observations,
            collection_dates=collection_dates,
            parser_version=self.parser_version,
            overall_confidence=overall_confidence,
            extracted_text="\f".join(pages_text),
        )

    async def extract_from_image(
        self,
        image_source: Union[Path, BinaryIO, io.BytesIO],
        document_id: str,
        *,
        effective_ocr: bool = True,
    ) -> ExtractionResult:
        """
        Extract lab values from a direct image import (.png/.jpg).

        Uses pytesseract for OCR. Observations get base confidence 0.4.
        Returns graceful result with ocr_unavailable=True if OCR deps missing.
        """
        from core.config import is_ocr_available

        if not effective_ocr:
            return ExtractionResult(
                document_id=document_id,
                observations=[],
                collection_dates=[],
                parser_version=self.parser_version,
                overall_confidence=0.0,
                ocr_unavailable=True,
            )

        if not is_ocr_available():
            return ExtractionResult(
                document_id=document_id,
                observations=[],
                collection_dates=[],
                parser_version=self.parser_version,
                overall_confidence=0.0,
                ocr_unavailable=True,
            )

        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            return ExtractionResult(
                document_id=document_id,
                observations=[],
                collection_dates=[],
                parser_version=self.parser_version,
                overall_confidence=0.0,
                ocr_unavailable=True,
            )

        if isinstance(image_source, (Path, str)):
            image = Image.open(image_source)
        else:
            image_source.seek(0)
            image = Image.open(image_source)

        text = pytesseract.image_to_string(image)
        observations = self._extract_from_text(text, 1, document_id)
        # Lower confidence for OCR-derived observations
        for obs in observations:
            obs.confidence = min(obs.confidence * 0.8, 0.7)
            obs.extraction_method = "ocr_image"
        collection_dates = self._extract_dates(text)

        # Propagate dates to observations missing collected_at
        if collection_dates:
            fallback_date = collection_dates[0]
            for obs in observations:
                if obs.collected_at is None:
                    obs.collected_at = fallback_date

        overall_confidence = (
            sum(o.confidence for o in observations) / len(observations)
            if observations else 0.0
        )

        return ExtractionResult(
            document_id=document_id,
            observations=observations,
            collection_dates=collection_dates,
            parser_version=self.parser_version,
            overall_confidence=overall_confidence,
            extracted_text=text,
        )

    # Collection-date label patterns (higher priority than generic dates)
    _COLLECTION_LABEL_RE = re.compile(
        r"(?:collected?(?:\s+date)?|collection\s+date|date\s+of\s+(?:service|collection)|"
        r"specimen\s+(?:date|collected)|drawn\s+(?:date|on)|accession\s+date)"
        r"[:\s]+([\w/\-,\s]+)",
        re.IGNORECASE,
    )

    # A birth label directly before a date marks it as a date of birth, never a
    # collection date. Checked on a fixed 32-character window (linear on long
    # whitespace runs); callers pass pos/endpos so `\b` still sees the real
    # character before the window.
    _BIRTH_LABEL_TAIL_RE = re.compile(
        r"(?:\bd\.?\s?o\.?\s?b\.?|\bdate\s+of\s+birth|\bbirth\s*date|\bborn(?:\s+on)?)"
        r"\s{0,3}[:\-]?\s{0,3}$",
        re.IGNORECASE,
    )
    _BIRTH_LABEL_WINDOW = 32

    @classmethod
    def _follows_birth_label(cls, text: str, start: int) -> bool:
        """True if the text just before *start* ends with a birth label."""
        return (
            cls._BIRTH_LABEL_TAIL_RE.search(text, max(0, start - cls._BIRTH_LABEL_WINDOW), start)
            is not None
        )

    # Plausibility bounds for extracted dates
    _DATE_MIN = date_type(1950, 1, 1)

    @staticmethod
    def _date_is_plausible(d: datetime) -> bool:
        """Return True if date falls within 1950..today+1 day."""
        from datetime import date as _date
        from datetime import timedelta
        today = _date.today()
        return ExtractModule._DATE_MIN <= d.date() <= today + timedelta(days=1)

    @staticmethod
    def _normalize_date_str(raw: str) -> Optional[str]:
        """
        Parse *raw* into a canonical ISO-8601 string (YYYY-MM-DD).

        Accepted formats (all US lab-report variants):
          YYYY-MM-DD [THH:MM[:SS]]  — ISO 8601, with or without time
          MM/DD/YYYY or MM/DD/YY
          MM-DD-YYYY or MM-DD-YY
          Month DD, YYYY  (full month name, comma optional)
          Mon DD, YYYY    (3-letter abbreviation, comma optional)
          DD-Mon-YYYY     (e.g. 15-Jan-2024)

        Returns None if unparseable or implausible.
        """
        raw = raw.strip()
        if not raw:
            return None

        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m/%d/%y",
            "%m-%d-%Y",
            "%m-%d-%y",
            "%B %d, %Y",
            "%B %d %Y",
            "%b %d, %Y",
            "%b %d %Y",
            "%d-%b-%Y",
        ]
        for fmt in formats:
            try:
                parsed = datetime.strptime(raw, fmt)
                if ExtractModule._date_is_plausible(parsed):
                    return parsed.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    def _extract_dates(self, text: str) -> list[str]:
        """
        Extract collection dates from lab-report text.

        Priority order:
          1. Text adjacent to collection-date labels
             ("Collected:", "Collection Date:", "Date of Service:", etc.)
          2. All other date-shaped strings

        Returns a list of ISO-8601 date strings (YYYY-MM-DD), deduplicated,
        in priority order.  Dates that cannot be parsed or are implausible
        (outside 1950..today+1) are silently dropped.
        """
        priority: list[str] = []
        generic: list[str] = []
        seen: set[str] = set()

        # --- Stage 1: collection-label dates (highest priority) ---
        for m in self._COLLECTION_LABEL_RE.finditer(text):
            # The capture group may contain extra words; try progressively
            # shorter substrings so we get just the date part.
            raw_tail = m.group(1).strip()
            tail_start = m.start(1) + (len(m.group(1)) - len(m.group(1).lstrip()))
            if self._follows_birth_label(text, tail_start):
                continue
            for candidate in _date_candidates_from_tail(raw_tail):
                iso = self._normalize_date_str(candidate)
                if iso and iso not in seen:
                    seen.add(iso)
                    priority.append(iso)
                    break  # first parseable candidate wins for this label

        # --- Stage 2: generic date-shaped tokens in the full text ---
        # Patterns ordered from most-specific to least-specific
        generic_patterns = [
            # ISO 8601 with optional time: 2024-01-15 or 2024-01-15T14:30
            r"\b(\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])(?:T\d{2}:\d{2}(?::\d{2})?)?)\b",
            # Full month name: January 15, 2024 or January 15 2024
            r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December)"
            r"\s+\d{1,2},?\s+\d{4})\b",
            # 3-letter abbrev: Jan 15, 2024 or Jan 15 2024
            r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2},?\s+\d{4})\b",
            # DD-Mon-YYYY: 15-Jan-2024
            r"\b(\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{4})\b",
            # MM/DD/YYYY or MM/DD/YY
            r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b",
            # MM-DD-YYYY or MM-DD-YY (only when NOT already matched as ISO)
            r"\b(\d{1,2}-\d{1,2}-\d{4})\b",
        ]

        for pattern in generic_patterns:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                if self._follows_birth_label(text, m.start(1)):
                    continue
                candidate = m.group(1).strip()
                iso = self._normalize_date_str(candidate)
                if iso and iso not in seen:
                    seen.add(iso)
                    generic.append(iso)

        return priority + generic


def _date_candidates_from_tail(tail: str) -> list[str]:
    """
    Given the text after a collection-date label, yield progressively
    shorter prefix strings so the caller can find the date token.

    E.g. "01/15/2024 Some extra text" -> ["01/15/2024 Some extra text",
                                           "01/15/2024 Some extra", "01/15/2024"]
    """
    words = tail.split()
    candidates = []
    for length in range(len(words), 0, -1):
        candidates.append(" ".join(words[:length]))
    return candidates
