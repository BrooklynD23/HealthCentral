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
from pathlib import Path
from typing import Optional, Union, BinaryIO
from dataclasses import dataclass, field
import re

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


class ExtractModule:
    """
    Document extraction service.
    
    Phase 0: Text-based PDF extraction using pdfplumber
    Phase 1+: OCR support for scanned documents
    """
    
    # Common lab value patterns
    VALUE_PATTERN = re.compile(
        r"(\d+\.?\d*)\s*(mg/dL|g/dL|mmol/L|mEq/L|U/L|IU/L|ng/mL|pg/mL|%|fL|K/uL|M/uL|cells/uL)?",
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

        with pdfplumber.open(pdf_source) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract text
                text = page.extract_text() or ""
                pages_text.append(text)
                
                # Extract tables (more structured)
                tables = page.extract_tables() or []
                
                # Process tables for lab values
                for table in tables:
                    table_obs = self._extract_from_table(
                        table, page_num, document_id
                    )
                    observations.extend(table_obs)
                
                # If no tables, try text extraction
                if not tables:
                    text_obs = self._extract_from_text(
                        text, page_num, document_id
                    )
                    observations.extend(text_obs)
                
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
        
        # Get value
        value_text = get_cell(value_col) if value_col >= 0 else ""
        value = None
        if value_text:
            match = self.VALUE_PATTERN.search(value_text)
            if match:
                try:
                    value = float(match.group(1))
                except ValueError:
                    logger.warning(
                        "Failed to parse observation value",
                        extra={"analyte": analyte, "raw_value": value_text, "page": page_num},
                    )
        
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
    
    # Pattern for "Analyte: Value Unit" format
    LINE_PATTERN = re.compile(
        r"^([A-Za-z][A-Za-z0-9\s,\-]+?):\s*"  # Analyte name ending with colon
        r"(\d+\.?\d*)\s*"  # Numeric value
        r"(mg/dL|g/dL|mmol/L|mEq/L|U/L|IU/L|ng/mL|pg/mL|%|fL|K/uL|M/uL|cells/uL)?"  # Unit
        r"(?:\s*\((?:Normal:|Ref:?)?\s*([<>]?\d+\.?\d*)\s*[-–]?\s*(\d+\.?\d*)?\))?"  # Reference range
        r"(?:\s*(H|L|HH|LL|HIGH|LOW|ABNORMAL|CRITICAL))?"  # Flag
        r"\s*$",
        re.IGNORECASE | re.MULTILINE
    )

    # Alternative pattern for "Analyte Value Unit (Range)" without colon
    ALT_LINE_PATTERN = re.compile(
        r"^([A-Za-z][A-Za-z0-9\s,\-]+?)\s+"  # Analyte name
        r"(\d+\.?\d*)\s*"  # Value
        r"(mg/dL|g/dL|mmol/L|mEq/L|U/L|IU/L|ng/mL|pg/mL|%|fL|K/uL|M/uL|cells/uL)\s*"  # Required unit
        r"(?:\(([<>]?\d+\.?\d*)\s*[-–]?\s*(\d+\.?\d*)?\))?"  # Reference range
        r"(?:\s*(H|L|HH|LL|HIGH|LOW|ABNORMAL|CRITICAL))?"  # Flag
        r"\s*$",
        re.IGNORECASE | re.MULTILINE
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
        if not match:
            # Try alternative format: "Glucose 95 mg/dL (70-100)"
            match = self.ALT_LINE_PATTERN.match(line)

        if not match:
            return None

        groups = match.groups()
        analyte = groups[0].strip() if groups[0] else None
        value_str = groups[1] if len(groups) > 1 else None
        unit = groups[2] if len(groups) > 2 else None
        ref_low_str = groups[3] if len(groups) > 3 else None
        ref_high_str = groups[4] if len(groups) > 4 else None
        flag = groups[5].upper() if len(groups) > 5 and groups[5] else None

        if not analyte or not value_str:
            return None

        # Parse numeric values
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
            unit=unit,
            ref_low=ref_low,
            ref_high=ref_high,
            ref_range_text=f"{ref_low_str or ''}-{ref_high_str or ''}" if ref_low_str else None,
            flag=flag,
            provenance=Provenance(page=page_num, text_snippet=line),
            confidence=min(confidence, 1.0),
            extraction_method="pdf_text",
        )
    
    async def extract_from_scanned_pdf(
        self,
        pdf_source: Union[Path, BinaryIO, io.BytesIO],
        document_id: str,
    ) -> ExtractionResult:
        """
        Extract lab values from a scanned PDF using OCR.

        Uses pdf2image to convert pages to images, then pytesseract for OCR.
        OCR observations get base confidence 0.4 (lower than text extraction).
        Returns graceful result with ocr_unavailable=True if OCR deps missing.
        """
        from core.config import is_ocr_available

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
            from pdf2image import convert_from_bytes
            import pytesseract
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
    ) -> ExtractionResult:
        """
        Extract lab values from a direct image import (.png/.jpg).

        Uses pytesseract for OCR. Observations get base confidence 0.4.
        Returns graceful result with ocr_unavailable=True if OCR deps missing.
        """
        from core.config import is_ocr_available

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
            from PIL import Image
            import pytesseract
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

    def _extract_dates(self, text: str) -> list[str]:
        """Extract collection dates from text."""
        # Common date patterns
        date_patterns = [
            r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b",
            r"\b(\d{1,2}-\d{1,2}-\d{2,4})\b",
            r"\b(\w{3}\s+\d{1,2},?\s+\d{4})\b",
        ]
        
        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)
        
        return dates
