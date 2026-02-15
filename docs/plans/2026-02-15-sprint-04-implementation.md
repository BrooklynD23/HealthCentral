# Sprint 04 - Data Interoperability Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement 6 work packages for export (PDF+charts, Excel, FHIR R4), search (hybrid FTS5+semantic backend, UI), and import (multi-source external parsers).

**Architecture:** Extends existing ExportModule with matplotlib charts and openpyxl. Adds FHIR R4 Pydantic models with LOINC lookup via BiomarkerKnowledge. Creates hybrid search with FTS5 virtual tables + SQL-cosine semantic reranking via RRF. Adds pluggable importer package with synthetic Document provenance records.

**Tech Stack:** Python/FastAPI, matplotlib (Agg), openpyxl, defusedxml, SQLite FTS5, React/TypeScript, React Query, Vitest

**Dependency Order:**
- Tasks 1-7 (DATA-001/002/003): parallel, no dependencies
- Task 8-12 (DATA-004): must complete before Task 13-14 (DATA-005)
- Task 15-21 (DATA-006): parallel with everything except shares `_fetch_observations` from export.py

---

## Task 0: Add Dependencies to requirements.txt

**Files:**
- Modify: `src/backend/requirements.txt`

**Step 1: Add new dependencies**

Append to `src/backend/requirements.txt`:
```
# Sprint 04: Data Interoperability
matplotlib>=3.8.0
openpyxl>=3.1.0
defusedxml>=0.7.0
```

**Step 2: Commit**

```bash
git add src/backend/requirements.txt
git commit -m "chore: add matplotlib, openpyxl, defusedxml for Sprint 04"
```

---

## Task 1: DATA-001 — Chart Generation (ExportModule)

**Files:**
- Modify: `src/backend/modules/export.py:204` (after `_format_trends`)
- Test: `src/backend/tests/test_export_pdf.py` (new)

**Step 1: Write the failing test**

Create `src/backend/tests/test_export_pdf.py`:

```python
"""Tests for PDF export with chart generation."""

import pytest
from datetime import datetime
from modules.export import ExportModule


class TestGenerateChartImage:
    """Tests for ExportModule.generate_chart_image."""

    def setup_method(self):
        self.export = ExportModule()

    def test_returns_png_bytes(self):
        data_points = [
            {"collected_at": datetime(2024, 1, 1), "value": 95.0},
            {"collected_at": datetime(2024, 6, 1), "value": 102.0},
            {"collected_at": datetime(2024, 12, 1), "value": 98.0},
        ]
        result = self.export.generate_chart_image(
            analyte="glucose",
            data_points=data_points,
            unit="mg/dL",
            ref_low=70.0,
            ref_high=100.0,
        )
        assert isinstance(result, bytes)
        assert result[:8] == b'\x89PNG\r\n\x1a\n'  # PNG magic bytes

    def test_empty_data_returns_empty_bytes(self):
        result = self.export.generate_chart_image(
            analyte="glucose",
            data_points=[],
            unit="mg/dL",
        )
        assert result == b''

    def test_single_point_returns_png(self):
        data_points = [
            {"collected_at": datetime(2024, 1, 1), "value": 95.0},
        ]
        result = self.export.generate_chart_image(
            analyte="glucose",
            data_points=data_points,
            unit="mg/dL",
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_abnormal_points_highlighted(self):
        data_points = [
            {"collected_at": datetime(2024, 1, 1), "value": 95.0, "is_abnormal": False},
            {"collected_at": datetime(2024, 6, 1), "value": 130.0, "is_abnormal": True},
        ]
        result = self.export.generate_chart_image(
            analyte="glucose",
            data_points=data_points,
            unit="mg/dL",
            ref_low=70.0,
            ref_high=100.0,
        )
        assert isinstance(result, bytes)
        assert len(result) > 100  # Non-trivial image


class TestRenderHtmlWithCharts:
    """Tests for ExportModule.render_html_summary with chart_images."""

    def setup_method(self):
        self.export = ExportModule()

    def test_charts_embedded_as_base64(self):
        summary_data = {
            "key_findings": ["Glucose: 130 mg/dL (H)"],
            "sections": [{"title": "Overview", "content": "Test"}],
            "questions": [],
        }
        # Minimal 1x1 red PNG
        chart_images = {"glucose": b'\x89PNG\r\n\x1a\n' + b'\x00' * 50}
        result = self.export.render_html_summary(
            summary_data, chart_images=chart_images
        )
        assert "data:image/png;base64," in result
        assert "glucose" in result.lower()

    def test_no_charts_produces_standard_html(self):
        summary_data = {
            "key_findings": [],
            "sections": [{"title": "Overview", "content": "Test"}],
            "questions": [],
        }
        result = self.export.render_html_summary(summary_data, chart_images={})
        assert "data:image/png;base64," not in result
```

**Step 2: Run test — verify FAIL**

```bash
cd src/backend && python -m pytest tests/test_export_pdf.py -v
```
Expected: FAIL — `generate_chart_image` does not exist.

**Step 3: Implement generate_chart_image**

Add to `src/backend/modules/export.py` after line 204 (`_format_trends` method):

```python
    def generate_chart_image(
        self,
        analyte: str,
        data_points: list[dict],
        unit: str = "",
        ref_low: Optional[float] = None,
        ref_high: Optional[float] = None,
    ) -> bytes:
        """
        Generate a trend line chart as PNG bytes.

        Uses matplotlib Agg backend (no display needed).
        Returns empty bytes if data_points is empty.
        """
        if not data_points:
            return b''

        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from io import BytesIO

        dates = [p["collected_at"] for p in data_points]
        values = [p["value"] for p in data_points]

        fig, ax = plt.subplots(figsize=(6, 3), dpi=150)

        # Reference range shading
        if ref_low is not None and ref_high is not None:
            ax.axhspan(ref_low, ref_high, alpha=0.15, color='#2D7D6F', label='Reference range')

        # Main line
        ax.plot(dates, values, color='#1f2937', linewidth=1.5, marker='o', markersize=4)

        # Highlight abnormal points
        abnormal_dates = [p["collected_at"] for p in data_points if p.get("is_abnormal")]
        abnormal_values = [p["value"] for p in data_points if p.get("is_abnormal")]
        if abnormal_dates:
            ax.scatter(abnormal_dates, abnormal_values, color='#b91c1c', s=40, zorder=5)

        ax.set_title(f"{analyte} ({unit})" if unit else analyte, fontsize=10, fontweight='bold')
        ax.set_ylabel(unit, fontsize=8)
        ax.tick_params(axis='both', labelsize=7)

        if len(dates) > 1:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
            fig.autofmt_xdate(rotation=30)

        ax.grid(axis='y', alpha=0.3)
        fig.tight_layout()

        buf = BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        return buf.read()
```

**Step 4: Update render_html_summary to accept chart_images**

Modify `render_html_summary` at `export.py:273` — change signature to:

```python
    def render_html_summary(
        self, summary_data: dict, chart_images: Optional[dict[str, bytes]] = None
    ) -> str:
```

Add chart embedding before the closing `</body>` tag (before `export.py:337`):

```python
        charts_html = ""
        if chart_images:
            import base64
            charts_html = '<div style="margin-top:24px;"><h3 style="color:#1f2937;font-size:16px;margin-bottom:12px;">Trend Charts</h3>'
            for analyte_name, png_bytes in chart_images.items():
                b64 = base64.b64encode(png_bytes).decode('ascii')
                charts_html += f'<div style="margin-bottom:16px;"><img src="data:image/png;base64,{b64}" alt="{analyte_name} trend chart" style="max-width:100%;border:1px solid #e5e7eb;border-radius:8px;"></div>'
            charts_html += '</div>'
```

Insert `{charts_html}` into the HTML template after `{questions_html}`.

**Step 5: Update render_pdf_summary to pass through chart_images**

Modify `render_pdf_summary` at `export.py:341`:

```python
    def render_pdf_summary(
        self, summary_data: dict, chart_images: Optional[dict[str, bytes]] = None
    ) -> bytes:
```

Change the body to:
```python
        html_content = self.render_html_summary(summary_data, chart_images=chart_images)
```

**Step 6: Run tests — verify PASS**

```bash
cd src/backend && python -m pytest tests/test_export_pdf.py -v
```

**Step 7: Commit**

```bash
git add src/backend/modules/export.py src/backend/tests/test_export_pdf.py
git commit -m "feat(DATA-001): add chart generation with matplotlib and embed in HTML/PDF summaries"
```

---

## Task 2: DATA-001 — Wire include_charts to download endpoint

**Files:**
- Modify: `src/backend/api/export.py:279-394` (download_summary endpoint)
- Modify: `src/backend/api/export.py:230` (store observations in summary_data for chart generation)

**Step 1: Modify summary storage to include observations for chart generation**

At `api/export.py:230`, add `"observations"` to `summary_data`:

```python
    summary_data = {
        ...existing fields...,
        "observations": observations,  # Needed for chart generation
    }
```

**Step 2: Add include_charts query param to download_summary**

Modify `download_summary` at `api/export.py:279`:

```python
@router.get("/doctor-summary/{summary_id}/download")
async def download_summary(
    summary_id: str,
    session: RequireAuth,
    format: str = Query("text", description="Download format: text, html, or pdf"),
    include_charts: bool = Query(False, description="Embed trend charts in PDF/HTML"),
    master_db: AsyncSession = Depends(get_db),
):
```

In the `format == "pdf"` and `format == "html"` branches, add chart generation:

```python
    chart_images = {}
    if include_charts and format in ("pdf", "html"):
        observations = summary_data.get("observations", [])
        # Group by analyte for charting
        from collections import defaultdict
        analyte_data = defaultdict(list)
        for obs in observations:
            if obs.get("value") is not None and obs.get("collected_at"):
                analyte_data[obs["analyte_canonical"]].append(obs)

        for analyte, points in analyte_data.items():
            if len(points) >= 2:
                sorted_points = sorted(points, key=lambda x: x["collected_at"])
                chart_images[analyte] = export_module.generate_chart_image(
                    analyte=analyte,
                    data_points=sorted_points,
                    unit=sorted_points[0].get("unit", ""),
                    ref_low=sorted_points[0].get("ref_low"),
                    ref_high=sorted_points[0].get("ref_high"),
                )
```

Pass `chart_images` to `render_html_summary` and `render_pdf_summary`.

Update audit log detail to include `include_charts`:

```python
    details={"summary_id": summary_id, "format": format, "include_charts": include_charts},
```

**Step 3: Commit**

```bash
git add src/backend/api/export.py
git commit -m "feat(DATA-001): wire include_charts param to summary download endpoint"
```

---

## Task 3: DATA-002 — Excel Export Module

**Files:**
- Modify: `src/backend/modules/export.py` (add export_excel after export_json)
- Test: `src/backend/tests/test_export_excel.py` (new)

**Step 1: Write the failing test**

Create `src/backend/tests/test_export_excel.py`:

```python
"""Tests for Excel export with formatting."""

import pytest
from datetime import datetime
from io import BytesIO
from modules.export import ExportModule


class TestExportExcel:
    """Tests for ExportModule.export_excel."""

    def setup_method(self):
        self.export = ExportModule()
        self.sample_observations = [
            {
                "analyte_canonical": "glucose",
                "value": 95.0,
                "unit": "mg/dL",
                "ref_low": 70.0,
                "ref_high": 100.0,
                "flag": None,
                "is_abnormal": False,
                "user_verified": True,
                "collected_at": datetime(2024, 1, 15),
            },
            {
                "analyte_canonical": "hemoglobin_a1c",
                "value": 6.5,
                "unit": "%",
                "ref_low": 4.0,
                "ref_high": 5.6,
                "flag": "H",
                "is_abnormal": True,
                "user_verified": False,
                "collected_at": datetime(2024, 1, 15),
            },
        ]
        self.sample_trends = [
            {"analyte": "glucose", "trend_direction": "up", "delta_percent": 8.5},
        ]

    def test_returns_valid_xlsx_bytes(self):
        result = self.export.export_excel(self.sample_observations, self.sample_trends)
        assert isinstance(result, bytes)
        # XLSX files start with PK (zip format)
        assert result[:2] == b'PK'

    def test_workbook_has_expected_sheets(self):
        from openpyxl import load_workbook
        result = self.export.export_excel(self.sample_observations, self.sample_trends)
        wb = load_workbook(BytesIO(result))
        sheet_names = wb.sheetnames
        assert "Summary" in sheet_names
        assert "Labs" in sheet_names
        assert "Trends" in sheet_names

    def test_labs_sheet_has_header_row(self):
        from openpyxl import load_workbook
        result = self.export.export_excel(self.sample_observations, self.sample_trends)
        wb = load_workbook(BytesIO(result))
        ws = wb["Labs"]
        headers = [cell.value for cell in ws[1]]
        assert "Date" in headers
        assert "Analyte" in headers
        assert "Value" in headers
        assert "Flag" in headers

    def test_labs_sheet_has_data_rows(self):
        from openpyxl import load_workbook
        result = self.export.export_excel(self.sample_observations, self.sample_trends)
        wb = load_workbook(BytesIO(result))
        ws = wb["Labs"]
        assert ws.max_row == 3  # header + 2 data rows

    def test_abnormal_rows_have_fill(self):
        from openpyxl import load_workbook
        result = self.export.export_excel(self.sample_observations, self.sample_trends)
        wb = load_workbook(BytesIO(result))
        ws = wb["Labs"]
        # Row 3 is hemoglobin_a1c (abnormal)
        fill_color = ws.cell(row=3, column=1).fill.start_color.rgb
        assert fill_color is not None  # Has conditional fill

    def test_empty_observations_returns_valid_xlsx(self):
        result = self.export.export_excel([], [])
        assert isinstance(result, bytes)
        assert result[:2] == b'PK'

    def test_frozen_header_row(self):
        from openpyxl import load_workbook
        result = self.export.export_excel(self.sample_observations, self.sample_trends)
        wb = load_workbook(BytesIO(result))
        ws = wb["Labs"]
        assert ws.freeze_panes == "A2"
```

**Step 2: Run test — verify FAIL**

```bash
cd src/backend && python -m pytest tests/test_export_excel.py -v
```

**Step 3: Implement export_excel**

Add to `src/backend/modules/export.py` after `export_json` (after line 271):

```python
    def export_excel(
        self,
        observations: list[dict],
        trends: list[dict],
        medications: Optional[list[dict]] = None,
    ) -> bytes:
        """
        Export data as formatted Excel workbook.

        Returns xlsx bytes with sheets: Summary, Labs, Trends.
        Includes conditional formatting for abnormal values.
        """
        from openpyxl import Workbook
        from openpyxl.styles import PatternFill, Font, Alignment
        from io import BytesIO

        wb = Workbook()
        abnormal_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
        header_font = Font(bold=True, size=11)
        header_fill = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")

        # --- Summary Sheet ---
        ws_summary = wb.active
        ws_summary.title = "Summary"
        ws_summary.append(["HealthCentral Lab Export"])
        ws_summary["A1"].font = Font(bold=True, size=14)
        ws_summary.append([f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"])
        ws_summary.append([f"Total Observations: {len(observations)}"])
        abnormal_count = sum(1 for o in observations if o.get("is_abnormal"))
        ws_summary.append([f"Abnormal Values: {abnormal_count}"])
        ws_summary.append([])
        ws_summary.append(["This export contains data from your uploaded lab reports."])
        ws_summary.append(["Reference ranges are as stated in each source document."])

        # --- Labs Sheet ---
        ws_labs = wb.create_sheet("Labs")
        lab_headers = ["Date", "Analyte", "Value", "Unit", "Ref Low", "Ref High", "Flag", "Verified"]
        ws_labs.append(lab_headers)
        for col_idx, _ in enumerate(lab_headers, 1):
            cell = ws_labs.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
        ws_labs.freeze_panes = "A2"

        sorted_obs = sorted(
            observations,
            key=lambda x: (x.get("analyte_canonical", ""), x.get("collected_at") or datetime.min),
        )
        for obs in sorted_obs:
            date_str = obs["collected_at"].strftime("%Y-%m-%d") if obs.get("collected_at") else ""
            row = [
                date_str,
                obs.get("analyte_canonical", ""),
                obs.get("value", ""),
                obs.get("unit", ""),
                obs.get("ref_low", ""),
                obs.get("ref_high", ""),
                obs.get("flag", ""),
                "Yes" if obs.get("user_verified") else "No",
            ]
            ws_labs.append(row)
            if obs.get("is_abnormal"):
                row_idx = ws_labs.max_row
                for col_idx in range(1, len(lab_headers) + 1):
                    ws_labs.cell(row=row_idx, column=col_idx).fill = abnormal_fill

        # Auto-width columns
        for col in ws_labs.columns:
            max_len = max((len(str(cell.value or "")) for cell in col), default=10)
            ws_labs.column_dimensions[col[0].column_letter].width = min(max_len + 2, 30)

        # --- Trends Sheet ---
        ws_trends = wb.create_sheet("Trends")
        trend_headers = ["Analyte", "Direction", "Change %"]
        ws_trends.append(trend_headers)
        for col_idx, _ in enumerate(trend_headers, 1):
            cell = ws_trends.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
        ws_trends.freeze_panes = "A2"

        for trend in trends:
            ws_trends.append([
                trend.get("analyte", ""),
                trend.get("trend_direction", ""),
                round(trend.get("delta_percent", 0), 1),
            ])

        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf.read()
```

Also add `from typing import Optional` if not already imported (it is at line 10).

**Step 4: Run tests — verify PASS**

```bash
cd src/backend && python -m pytest tests/test_export_excel.py -v
```

**Step 5: Commit**

```bash
git add src/backend/modules/export.py src/backend/tests/test_export_excel.py
git commit -m "feat(DATA-002): add Excel export with multi-sheet workbook and conditional formatting"
```

---

## Task 4: DATA-002 — Excel Export API Endpoint

**Files:**
- Modify: `src/backend/api/export.py` (add endpoint after export_json)

**Step 1: Add GET /export/excel endpoint**

Add after the `export_json` endpoint (after `api/export.py:570`):

```python
@router.get("/excel")
async def export_excel(
    session: RequireAuth,
    analytes: Optional[str] = Query(None, description="Comma-separated analyte filter"),
    from_date: Optional[datetime] = Query(None, description="Start date"),
    to_date: Optional[datetime] = Query(None, description="End date"),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Export observations as formatted Excel workbook.

    Multi-sheet with conditional formatting for abnormal values.
    Only includes data from the authenticated profile.
    """
    profile_id = session.profile_id

    analyte_filter = None
    if analytes:
        analyte_filter = [a.strip().lower() for a in analytes.split(",")]

    observations = await _fetch_observations(
        profile_db, profile_id,
        from_date=from_date, to_date=to_date, analyte_filter=analyte_filter,
    )

    trends = _compute_trends(observations)

    export_module = ExportModule()
    xlsx_bytes = export_module.export_excel(observations, trends)

    try:
        await log_export_event(
            db=master_db, profile_id=profile_id, export_type="excel",
            details={"observation_count": len(observations)},
        )
        await master_db.commit()
    except Exception as e:
        logger.warning(f"Failed to log export event: {e}")

    filename = f"health_data_{datetime.now(timezone.utc).strftime('%Y%m%d')}.xlsx"

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

**Step 2: Commit**

```bash
git add src/backend/api/export.py
git commit -m "feat(DATA-002): add GET /export/excel API endpoint"
```

---

## Task 5: DATA-003 — FHIR R4 Pydantic Models

**Files:**
- Create: `src/backend/models/fhir_resources.py` (new)
- Test: `src/backend/tests/test_export_fhir.py` (new)

**Step 1: Write the failing test**

Create `src/backend/tests/test_export_fhir.py`:

```python
"""Tests for FHIR R4 export models and mapping."""

import json
import pytest
from datetime import datetime
from models.fhir_resources import (
    FHIRPatient,
    FHIRObservation,
    FHIRBundle,
    map_observation_to_fhir,
    create_fhir_bundle,
)


class TestFHIRPatient:
    def test_minimal_patient(self):
        patient = FHIRPatient(id="test-123", display_name="John Doe")
        data = patient.model_dump(by_alias=True, exclude_none=True)
        assert data["resourceType"] == "Patient"
        assert data["id"] == "test-123"
        assert data["name"][0]["text"] == "John Doe"

    def test_absent_fields_have_extension(self):
        patient = FHIRPatient(id="test-123", display_name="Jane Doe")
        data = patient.model_dump(by_alias=True, exclude_none=True)
        assert "_birthDate" in data
        assert data["_birthDate"]["extension"][0]["url"] == (
            "http://hl7.org/fhir/StructureDefinition/data-absent-reason"
        )


class TestFHIRObservation:
    def test_observation_mapping(self):
        obs = {
            "id": "obs-001",
            "analyte_canonical": "glucose",
            "value": 95.0,
            "unit": "mg/dL",
            "ref_low": 70.0,
            "ref_high": 100.0,
            "collected_at": datetime(2024, 1, 15, 10, 30),
            "is_abnormal": False,
        }
        fhir_obs = map_observation_to_fhir(obs, patient_ref="Patient/test-123")
        data = fhir_obs.model_dump(by_alias=True, exclude_none=True)
        assert data["resourceType"] == "Observation"
        assert data["status"] == "final"
        assert data["valueQuantity"]["value"] == 95.0
        assert data["valueQuantity"]["unit"] == "mg/dL"
        assert len(data["referenceRange"]) == 1

    def test_observation_with_loinc(self):
        obs = {
            "id": "obs-002",
            "analyte_canonical": "glucose",
            "value": 95.0,
            "unit": "mg/dL",
            "collected_at": datetime(2024, 1, 15),
        }
        loinc_map = {"glucose": ["2345-7"]}
        fhir_obs = map_observation_to_fhir(
            obs, patient_ref="Patient/p1", loinc_map=loinc_map
        )
        data = fhir_obs.model_dump(by_alias=True, exclude_none=True)
        codings = data["code"]["coding"]
        assert any(c["system"] == "http://loinc.org" for c in codings)
        assert any(c["code"] == "2345-7" for c in codings)

    def test_observation_without_value_uses_text(self):
        obs = {
            "id": "obs-003",
            "analyte_canonical": "urinalysis_color",
            "value": None,
            "value_text": "Yellow",
            "collected_at": datetime(2024, 1, 15),
        }
        fhir_obs = map_observation_to_fhir(obs, patient_ref="Patient/p1")
        data = fhir_obs.model_dump(by_alias=True, exclude_none=True)
        assert "valueString" in data
        assert data["valueString"] == "Yellow"


class TestFHIRBundle:
    def test_bundle_structure(self):
        patient = FHIRPatient(id="p1", display_name="Test User")
        obs = {
            "id": "obs-001",
            "analyte_canonical": "glucose",
            "value": 95.0,
            "unit": "mg/dL",
            "collected_at": datetime(2024, 1, 15),
        }
        fhir_obs = map_observation_to_fhir(obs, patient_ref="Patient/p1")
        bundle = create_fhir_bundle(patient, [fhir_obs])
        data = bundle.model_dump(by_alias=True, exclude_none=True)
        assert data["resourceType"] == "Bundle"
        assert data["type"] == "collection"
        assert len(data["entry"]) == 2  # patient + 1 observation

    def test_bundle_json_serializable(self):
        patient = FHIRPatient(id="p1", display_name="Test")
        bundle = create_fhir_bundle(patient, [])
        data = bundle.model_dump(by_alias=True, exclude_none=True)
        json_str = json.dumps(data)
        assert '"resourceType": "Bundle"' in json_str
```

**Step 2: Run test — verify FAIL**

```bash
cd src/backend && python -m pytest tests/test_export_fhir.py -v
```

**Step 3: Implement FHIR models**

Create `src/backend/models/fhir_resources.py`:

```python
"""
FHIR R4 resource models for export.

Pydantic models (not SQLAlchemy) for serializing observations
and profile data into FHIR R4 JSON format.

Design Decision DD-4: Minimal Patient resource, LOINC via BiomarkerKnowledge lookup.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class FHIRCoding(BaseModel):
    system: Optional[str] = None
    code: Optional[str] = None
    display: Optional[str] = None


class FHIRCodeableConcept(BaseModel):
    coding: list[FHIRCoding] = Field(default_factory=list)
    text: Optional[str] = None


class FHIRHumanName(BaseModel):
    text: str


class FHIRAbsentExtension(BaseModel):
    url: str = "http://hl7.org/fhir/StructureDefinition/data-absent-reason"
    valueCode: str = "unknown"


class FHIRAbsentField(BaseModel):
    extension: list[FHIRAbsentExtension] = Field(
        default_factory=lambda: [FHIRAbsentExtension()]
    )


class FHIRQuantity(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None
    system: str = "http://unitsofmeasure.org"


class FHIRReferenceRange(BaseModel):
    low: Optional[FHIRQuantity] = None
    high: Optional[FHIRQuantity] = None


class FHIRReference(BaseModel):
    reference: str


class FHIRPatient(BaseModel):
    resourceType: str = Field(default="Patient", alias="resourceType")
    id: str
    display_name: str = Field(exclude=True)
    name: list[FHIRHumanName] = None
    _birthDate: Optional[FHIRAbsentField] = Field(
        default_factory=FHIRAbsentField, alias="_birthDate"
    )

    def model_post_init(self, __context) -> None:
        if self.name is None:
            self.name = [FHIRHumanName(text=self.display_name)]

    class Config:
        populate_by_name = True


class FHIRObservation(BaseModel):
    resourceType: str = Field(default="Observation", alias="resourceType")
    id: str
    status: str = "final"
    code: FHIRCodeableConcept
    subject: Optional[FHIRReference] = None
    effectiveDateTime: Optional[str] = Field(default=None, alias="effectiveDateTime")
    valueQuantity: Optional[FHIRQuantity] = Field(default=None, alias="valueQuantity")
    valueString: Optional[str] = Field(default=None, alias="valueString")
    referenceRange: list[FHIRReferenceRange] = Field(
        default_factory=list, alias="referenceRange"
    )

    class Config:
        populate_by_name = True


class FHIRBundleEntry(BaseModel):
    resource: dict


class FHIRBundle(BaseModel):
    resourceType: str = Field(default="Bundle", alias="resourceType")
    type: str = "collection"
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    entry: list[FHIRBundleEntry] = Field(default_factory=list)

    class Config:
        populate_by_name = True


def map_observation_to_fhir(
    obs: dict,
    patient_ref: str,
    loinc_map: Optional[dict[str, list[str]]] = None,
) -> FHIRObservation:
    """Map an observation dict to a FHIR R4 Observation resource."""
    analyte = obs.get("analyte_canonical", "")

    # Build code with LOINC lookup
    codings = []
    if loinc_map and analyte in loinc_map:
        for loinc_code in loinc_map[analyte]:
            codings.append(FHIRCoding(
                system="http://loinc.org",
                code=loinc_code,
                display=analyte,
            ))
    codings.append(FHIRCoding(display=analyte))
    code = FHIRCodeableConcept(coding=codings, text=analyte)

    # Value
    value_quantity = None
    value_string = None
    if obs.get("value") is not None:
        value_quantity = FHIRQuantity(value=obs["value"], unit=obs.get("unit", ""))
    elif obs.get("value_text"):
        value_string = obs["value_text"]

    # Reference range
    ref_ranges = []
    if obs.get("ref_low") is not None or obs.get("ref_high") is not None:
        ref_range = FHIRReferenceRange()
        if obs.get("ref_low") is not None:
            ref_range.low = FHIRQuantity(value=obs["ref_low"], unit=obs.get("unit", ""))
        if obs.get("ref_high") is not None:
            ref_range.high = FHIRQuantity(value=obs["ref_high"], unit=obs.get("unit", ""))
        ref_ranges.append(ref_range)

    # Effective date
    effective_dt = None
    if obs.get("collected_at"):
        dt = obs["collected_at"]
        effective_dt = dt.isoformat() if isinstance(dt, datetime) else str(dt)

    return FHIRObservation(
        id=obs.get("id", ""),
        code=code,
        subject=FHIRReference(reference=patient_ref),
        effectiveDateTime=effective_dt,
        valueQuantity=value_quantity,
        valueString=value_string,
        referenceRange=ref_ranges,
    )


def create_fhir_bundle(
    patient: FHIRPatient,
    observations: list[FHIRObservation],
) -> FHIRBundle:
    """Create a FHIR Bundle containing a Patient and Observations."""
    entries = [
        FHIRBundleEntry(resource=patient.model_dump(by_alias=True, exclude_none=True))
    ]
    for obs in observations:
        entries.append(
            FHIRBundleEntry(resource=obs.model_dump(by_alias=True, exclude_none=True))
        )
    return FHIRBundle(entry=entries)
```

**Step 4: Run tests — verify PASS**

```bash
cd src/backend && python -m pytest tests/test_export_fhir.py -v
```

**Step 5: Commit**

```bash
git add src/backend/models/fhir_resources.py src/backend/tests/test_export_fhir.py
git commit -m "feat(DATA-003): add FHIR R4 Pydantic models with LOINC lookup support"
```

---

## Task 6: DATA-003 — FHIR Export API Endpoint

**Files:**
- Modify: `src/backend/api/export.py` (add GET /fhir endpoint)

**Step 1: Add FHIR endpoint**

Add import at top of `api/export.py`:
```python
from models.fhir_resources import FHIRPatient, map_observation_to_fhir, create_fhir_bundle
```

Add endpoint after the excel endpoint:

```python
@router.get("/fhir")
async def export_fhir(
    session: RequireAuth,
    analytes: Optional[str] = Query(None, description="Comma-separated analyte filter"),
    from_date: Optional[datetime] = Query(None, description="Start date"),
    to_date: Optional[datetime] = Query(None, description="End date"),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Export observations as FHIR R4 JSON Bundle.

    Maps observations to FHIR Observation resources with LOINC codes
    (when available via BiomarkerKnowledge lookup).
    """
    import json as json_lib
    from models import BiomarkerKnowledge

    profile_id = session.profile_id

    analyte_filter = None
    if analytes:
        analyte_filter = [a.strip().lower() for a in analytes.split(",")]

    observations = await _fetch_observations(
        profile_db, profile_id,
        from_date=from_date, to_date=to_date, analyte_filter=analyte_filter,
    )

    # LOINC lookup from BiomarkerKnowledge (master DB)
    loinc_map: dict[str, list[str]] = {}
    try:
        from sqlalchemy import select as sa_select
        result = await master_db.execute(
            sa_select(
                BiomarkerKnowledge.analyte_canonical,
                BiomarkerKnowledge.loinc_codes_json,
            )
        )
        for row in result.all():
            if row.loinc_codes_json:
                codes = json_lib.loads(row.loinc_codes_json)
                if isinstance(codes, list) and codes:
                    loinc_map[row.analyte_canonical] = codes
    except Exception as e:
        logger.warning(f"LOINC lookup failed, proceeding without: {e}")

    # Build FHIR resources
    patient = FHIRPatient(id=profile_id, display_name=session.profile_name or "Unknown")
    patient_ref = f"Patient/{profile_id}"

    fhir_observations = [
        map_observation_to_fhir(obs, patient_ref=patient_ref, loinc_map=loinc_map)
        for obs in observations
    ]

    bundle = create_fhir_bundle(patient, fhir_observations)
    bundle_json = json_lib.dumps(
        bundle.model_dump(by_alias=True, exclude_none=True), indent=2
    )

    try:
        await log_export_event(
            db=master_db, profile_id=profile_id, export_type="fhir_r4",
            details={"observation_count": len(observations), "loinc_mapped": len(loinc_map)},
        )
        await master_db.commit()
    except Exception as e:
        logger.warning(f"Failed to log export event: {e}")

    filename = f"health_data_{datetime.now(timezone.utc).strftime('%Y%m%d')}_fhir.json"

    return Response(
        content=bundle_json,
        media_type="application/fhir+json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

**Step 2: Commit**

```bash
git add src/backend/api/export.py
git commit -m "feat(DATA-003): add GET /export/fhir endpoint with LOINC lookup"
```

---

## Task 7: DATA-001/002/003 — Frontend Export Hooks

**Files:**
- Modify: `src/frontend/src/services/export.ts` (add hooks)
- Modify: `src/frontend/src/services/index.ts` (re-export)
- Modify: `src/frontend/src/pages/ExportPage.tsx` (add buttons)

**Step 1: Add new API functions and hooks to export.ts**

Add after `useGenerateQuestions` in `src/frontend/src/services/export.ts` (after line 188):

```typescript
// --- Sprint 04: New Export Functions ---

async function exportExcel(filters?: ExportFilters): Promise<Blob> {
  const params: Record<string, string> = {};
  if (filters?.analytes?.length) params.analytes = filters.analytes.join(',');
  if (filters?.from_date) params.from_date = filters.from_date;
  if (filters?.to_date) params.to_date = filters.to_date;

  const response = await apiGetRaw('/export/excel', params);
  return response.blob();
}

async function exportFHIR(filters?: ExportFilters): Promise<string> {
  const params: Record<string, string> = {};
  if (filters?.analytes?.length) params.analytes = filters.analytes.join(',');
  if (filters?.from_date) params.from_date = filters.from_date;
  if (filters?.to_date) params.to_date = filters.to_date;

  const response = await apiGetRaw('/export/fhir', params);
  return response.text();
}

/**
 * Mutation hook for exporting Excel workbook.
 */
export function useExportExcel() {
  return useMutation({
    mutationFn: (filters?: ExportFilters) => exportExcel(filters),
    onSuccess: (blob) => {
      triggerDownload(blob, `health_data_${new Date().toISOString().split('T')[0]}.xlsx`);
    },
  });
}

/**
 * Mutation hook for exporting FHIR R4 Bundle.
 */
export function useExportFHIR() {
  return useMutation({
    mutationFn: (filters?: ExportFilters) => exportFHIR(filters),
    onSuccess: (content) => {
      const blob = new Blob([content], { type: 'application/fhir+json' });
      triggerDownload(blob, `health_data_${new Date().toISOString().split('T')[0]}_fhir.json`);
    },
  });
}
```

Update `downloadSummary` function to accept `include_charts`:

```typescript
async function downloadSummary(
  summaryId: string,
  format: ExportFormat = 'text',
  includeCharts: boolean = false,
): Promise<{ blob: Blob; contentType: string; extension: string }> {
  const params: Record<string, string> = { format };
  if (includeCharts) params.include_charts = 'true';

  const response = await apiGetRaw(
    `/export/doctor-summary/${summaryId}/download`,
    params,
  );
  // ...rest unchanged
```

Update `useDownloadSummary` mutation type:

```typescript
export function useDownloadSummary() {
  return useMutation({
    mutationFn: ({ summaryId, format, includeCharts }: {
      summaryId: string;
      format: ExportFormat;
      includeCharts?: boolean;
    }) => downloadSummary(summaryId, format, includeCharts),
    onSuccess: ({ blob, extension }, { summaryId }) => {
      triggerDownload(blob, `health_summary_${summaryId.substring(0, 8)}${extension}`);
    },
  });
}
```

**Step 2: Re-export from services/index.ts**

Add to the export block in `src/frontend/src/services/index.ts` (around line 83):

```typescript
export {
  useExportCSV,
  useExportJSON,
  useExportExcel,
  useExportFHIR,
  useGenerateSummary,
  useDownloadSummary,
  useGenerateQuestions,
} from './export';
```

**Step 3: Add buttons to ExportPage**

In `src/frontend/src/pages/ExportPage.tsx`, add imports:

```typescript
import { Table2, Heart } from 'lucide-react';
import { useExportExcel, useExportFHIR } from '@/services';
```

Add hooks after existing ones (around line 58):

```typescript
  const exportExcel = useExportExcel();
  const exportFHIR = useExportFHIR();
```

Add Excel and FHIR buttons in the header button group (after JSON button, around line 155):

```tsx
          <Button variant="secondary" className="gap-2" onClick={() => exportExcel.mutate(undefined)} disabled={isLoading}>
            {exportExcel.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Table2 className="w-4 h-4" />}
            Excel
          </Button>
          <Button variant="secondary" className="gap-2" onClick={() => exportFHIR.mutate(undefined)} disabled={isLoading}>
            {exportFHIR.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Heart className="w-4 h-4" />}
            FHIR
          </Button>
```

Update `isLoading` to include new hooks:

```typescript
  const isLoading =
    exportCSV.isPending || exportJSON.isPending || exportExcel.isPending ||
    exportFHIR.isPending || generateSummary.isPending || downloadSummary.isPending;
```

**Step 4: Run frontend build to verify**

```bash
cd src/frontend && npx tsc --noEmit
```

**Step 5: Commit**

```bash
git add src/frontend/src/services/export.ts src/frontend/src/services/index.ts src/frontend/src/pages/ExportPage.tsx
git commit -m "feat(DATA-001/002/003): add Excel, FHIR, chart export hooks and ExportPage buttons"
```

---

## Task 8: DATA-004 — FTS5 Migration

**Files:**
- Create: `src/backend/migrations/profile/versions/003_add_fts5_indexes.py` (new)

**Step 1: Create migration**

Create `src/backend/migrations/profile/versions/003_add_fts5_indexes.py`:

```python
"""Add FTS5 virtual tables for search.

Revision ID: 003
Revises: 002
Create Date: 2026-02-15

Design Decision DD-5: Index both observations and chunks for full-text search.
"""

revision = "003"
down_revision = "002"

from alembic import op


def upgrade() -> None:
    # FTS5 for observations (analyte names, text values, notes)
    op.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts
        USING fts5(
            analyte_canonical,
            analyte_raw,
            value_text,
            notes,
            content=observations,
            content_rowid=rowid
        )
    """)

    # FTS5 for document chunks (full text content)
    op.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
        USING fts5(
            text,
            content=chunks,
            content_rowid=rowid
        )
    """)

    # Triggers to keep FTS indexes in sync with source tables
    # Observations
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS observations_ai AFTER INSERT ON observations BEGIN
            INSERT INTO observations_fts(rowid, analyte_canonical, analyte_raw, value_text, notes)
            VALUES (new.rowid, new.analyte_canonical, new.analyte_raw, new.value_text, new.notes);
        END
    """)
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS observations_ad AFTER DELETE ON observations BEGIN
            INSERT INTO observations_fts(observations_fts, rowid, analyte_canonical, analyte_raw, value_text, notes)
            VALUES ('delete', old.rowid, old.analyte_canonical, old.analyte_raw, old.value_text, old.notes);
        END
    """)
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS observations_au AFTER UPDATE ON observations BEGIN
            INSERT INTO observations_fts(observations_fts, rowid, analyte_canonical, analyte_raw, value_text, notes)
            VALUES ('delete', old.rowid, old.analyte_canonical, old.analyte_raw, old.value_text, old.notes);
            INSERT INTO observations_fts(rowid, analyte_canonical, analyte_raw, value_text, notes)
            VALUES (new.rowid, new.analyte_canonical, new.analyte_raw, new.value_text, new.notes);
        END
    """)

    # Chunks
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
            INSERT INTO chunks_fts(rowid, text)
            VALUES (new.rowid, new.text);
        END
    """)
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, text)
            VALUES ('delete', old.rowid, old.text);
        END
    """)
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, text)
            VALUES ('delete', old.rowid, old.text);
            INSERT INTO chunks_fts(rowid, text)
            VALUES (new.rowid, new.text);
        END
    """)

    # Backfill existing data into FTS indexes
    op.execute("""
        INSERT INTO observations_fts(rowid, analyte_canonical, analyte_raw, value_text, notes)
        SELECT rowid, analyte_canonical, analyte_raw, value_text, notes FROM observations
    """)
    op.execute("""
        INSERT INTO chunks_fts(rowid, text)
        SELECT rowid, text FROM chunks
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS observations_ai")
    op.execute("DROP TRIGGER IF EXISTS observations_ad")
    op.execute("DROP TRIGGER IF EXISTS observations_au")
    op.execute("DROP TRIGGER IF EXISTS chunks_ai")
    op.execute("DROP TRIGGER IF EXISTS chunks_ad")
    op.execute("DROP TRIGGER IF EXISTS chunks_au")
    op.execute("DROP TABLE IF EXISTS observations_fts")
    op.execute("DROP TABLE IF EXISTS chunks_fts")
```

**Step 2: Commit**

```bash
git add src/backend/migrations/profile/versions/003_add_fts5_indexes.py
git commit -m "feat(DATA-004): add FTS5 virtual tables and sync triggers for observations and chunks"
```

---

## Task 9: DATA-004 — Search Module

**Files:**
- Create: `src/backend/modules/search.py` (new)
- Test: `src/backend/tests/test_search_ranking.py` (new)

**Step 1: Write the failing test**

Create `src/backend/tests/test_search_ranking.py`:

```python
"""Tests for search module ranking logic."""

import pytest
from modules.search import reciprocal_rank_fusion, SearchResult


class TestReciprocalRankFusion:
    def test_single_list(self):
        results = [
            SearchResult(id="a", type="observation", title="Glucose", score=1.0),
            SearchResult(id="b", type="observation", title="HbA1c", score=0.8),
        ]
        fused = reciprocal_rank_fusion([results], k=60)
        assert fused[0].id == "a"
        assert fused[1].id == "b"

    def test_two_lists_merge(self):
        list1 = [
            SearchResult(id="a", type="observation", title="Glucose", score=1.0),
            SearchResult(id="b", type="observation", title="HbA1c", score=0.8),
        ]
        list2 = [
            SearchResult(id="b", type="observation", title="HbA1c", score=1.0),
            SearchResult(id="c", type="chunk", title="Doc chunk", score=0.5),
        ]
        fused = reciprocal_rank_fusion([list1, list2], k=60)
        # "b" appears in both lists, should be ranked higher
        ids = [r.id for r in fused]
        assert ids.index("b") < ids.index("c")

    def test_empty_lists(self):
        fused = reciprocal_rank_fusion([], k=60)
        assert fused == []

    def test_score_is_rrf_sum(self):
        list1 = [SearchResult(id="a", type="observation", title="X", score=1.0)]
        list2 = [SearchResult(id="a", type="observation", title="X", score=1.0)]
        fused = reciprocal_rank_fusion([list1, list2], k=60)
        # rank 1 in both => 1/(60+1) + 1/(60+1) = 2/61
        expected = 2.0 / 61.0
        assert abs(fused[0].score - expected) < 0.001

    def test_deduplication_by_id(self):
        list1 = [SearchResult(id="a", type="observation", title="X", score=1.0)]
        list2 = [SearchResult(id="a", type="observation", title="X", score=0.9)]
        fused = reciprocal_rank_fusion([list1, list2], k=60)
        assert len(fused) == 1
```

**Step 2: Run test — verify FAIL**

```bash
cd src/backend && python -m pytest tests/test_search_ranking.py -v
```

**Step 3: Implement SearchModule**

Create `src/backend/modules/search.py`:

```python
"""
Search module.

Provides hybrid search combining:
- FTS5 full-text search on observations and chunks
- Semantic similarity using existing embeddings (SQL + cosine)
- Reciprocal Rank Fusion (RRF) for score combination

Design Decision DD-1: SQL+cosine for v1, no FAISS.
Design Decision DD-5: FTS5 on both observations and chunks.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result."""
    id: str
    type: str  # "observation" or "chunk"
    title: str
    score: float = 0.0
    snippet: str = ""
    highlight: str = ""
    collected_at: Optional[datetime] = None
    analyte: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    explanation: str = ""


@dataclass
class SearchFilters:
    """Filters for search queries."""
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    analyte: Optional[str] = None
    abnormal_only: bool = False


@dataclass
class SearchResponse:
    """Complete search response."""
    results: list[SearchResult] = field(default_factory=list)
    total_count: int = 0
    query: str = ""
    mode: str = "hybrid"


def reciprocal_rank_fusion(
    ranked_lists: list[list[SearchResult]],
    k: int = 60,
) -> list[SearchResult]:
    """
    Combine multiple ranked lists using Reciprocal Rank Fusion.

    score(doc) = sum(1 / (k + rank_i)) for each list i.
    """
    if not ranked_lists:
        return []

    scores: dict[str, float] = {}
    result_map: dict[str, SearchResult] = {}

    for ranked_list in ranked_lists:
        for rank, result in enumerate(ranked_list, start=1):
            rrf_score = 1.0 / (k + rank)
            scores[result.id] = scores.get(result.id, 0.0) + rrf_score
            if result.id not in result_map:
                result_map[result.id] = result

    # Sort by fused score descending
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    fused_results = []
    for doc_id in sorted_ids:
        result = result_map[doc_id]
        result.score = scores[doc_id]
        fused_results.append(result)

    return fused_results


class SearchModule:
    """
    Hybrid search engine combining FTS5 and semantic similarity.
    """

    async def search_fulltext(
        self,
        query: str,
        profile_db: AsyncSession,
        profile_id: str,
        filters: Optional[SearchFilters] = None,
        limit: int = 20,
    ) -> list[SearchResult]:
        """Search using FTS5 on observations and chunks."""
        results = []

        # Sanitize query for FTS5
        safe_query = query.replace('"', '""')

        # Search observations FTS
        try:
            obs_sql = text("""
                SELECT o.id, o.analyte_canonical, o.value, o.unit, o.collected_at,
                       o.is_abnormal, snippet(observations_fts, 0, '<b>', '</b>', '...', 32) as snip,
                       rank
                FROM observations_fts
                JOIN observations o ON observations_fts.rowid = o.rowid
                WHERE observations_fts MATCH :query
                  AND o.profile_id = :profile_id
                ORDER BY rank
                LIMIT :limit
            """)
            params = {"query": f'"{safe_query}"', "profile_id": profile_id, "limit": limit}
            result = await profile_db.execute(obs_sql, params)
            for row in result.fetchall():
                r = SearchResult(
                    id=row.id,
                    type="observation",
                    title=row.analyte_canonical,
                    snippet=row.snip or "",
                    analyte=row.analyte_canonical,
                    value=row.value,
                    unit=row.unit,
                    collected_at=row.collected_at,
                    explanation="Full-text match on observation",
                )
                if filters:
                    if filters.abnormal_only and not row.is_abnormal:
                        continue
                    if filters.from_date and row.collected_at and row.collected_at < filters.from_date:
                        continue
                    if filters.to_date and row.collected_at and row.collected_at > filters.to_date:
                        continue
                    if filters.analyte and row.analyte_canonical != filters.analyte:
                        continue
                results.append(r)
        except Exception as e:
            logger.warning(f"Observation FTS search failed: {e}")

        # Search chunks FTS
        try:
            chunk_sql = text("""
                SELECT c.id, c.doc_id, c.text, c.page_number,
                       snippet(chunks_fts, 0, '<b>', '</b>', '...', 48) as snip,
                       rank
                FROM chunks_fts
                JOIN chunks c ON chunks_fts.rowid = c.rowid
                WHERE chunks_fts MATCH :query
                ORDER BY rank
                LIMIT :limit
            """)
            chunk_params = {"query": f'"{safe_query}"', "limit": limit}
            result = await profile_db.execute(chunk_sql, chunk_params)
            for row in result.fetchall():
                results.append(SearchResult(
                    id=row.id,
                    type="chunk",
                    title=f"Document content (page {row.page_number or '?'})",
                    snippet=row.snip or row.text[:200],
                    explanation="Full-text match on document content",
                ))
        except Exception as e:
            logger.warning(f"Chunk FTS search failed: {e}")

        return results

    async def search_semantic(
        self,
        query: str,
        profile_db: AsyncSession,
        profile_id: str,
        top_k: int = 10,
    ) -> list[SearchResult]:
        """
        Semantic search using existing embeddings with SQL+cosine.

        Reuses the pattern from rag.py:_search_vectors_async.
        """
        try:
            from modules.rag import RAGModule
            rag = RAGModule()
            vector_results = await rag._search_vectors_async(
                query=query,
                profile_id=profile_id,
                top_k=top_k,
                profile_db=profile_db,
            )
            results = []
            for chunk_data, similarity in vector_results:
                results.append(SearchResult(
                    id=chunk_data.get("chunk_id", ""),
                    type="chunk",
                    title=chunk_data.get("doc_title", "Document"),
                    snippet=chunk_data.get("text", "")[:200],
                    score=similarity,
                    explanation=f"Semantic similarity: {similarity:.3f}",
                ))
            return results
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return []

    async def search_hybrid(
        self,
        query: str,
        profile_db: AsyncSession,
        profile_id: str,
        filters: Optional[SearchFilters] = None,
        limit: int = 20,
    ) -> SearchResponse:
        """Hybrid search combining FTS5 + semantic via RRF."""
        fts_results = await self.search_fulltext(
            query, profile_db, profile_id, filters, limit=limit
        )

        semantic_results = await self.search_semantic(
            query, profile_db, profile_id, top_k=limit
        )

        fused = reciprocal_rank_fusion([fts_results, semantic_results], k=60)

        return SearchResponse(
            results=fused[:limit],
            total_count=len(fused),
            query=query,
            mode="hybrid",
        )

    async def get_suggestions(
        self,
        prefix: str,
        profile_db: AsyncSession,
        profile_id: str,
        limit: int = 10,
    ) -> list[str]:
        """Autocomplete suggestions from observation analyte names."""
        safe_prefix = prefix.replace("'", "''")
        sql = text("""
            SELECT DISTINCT analyte_canonical
            FROM observations
            WHERE profile_id = :profile_id
              AND analyte_canonical LIKE :prefix
            ORDER BY analyte_canonical
            LIMIT :limit
        """)
        result = await profile_db.execute(sql, {
            "profile_id": profile_id,
            "prefix": f"{safe_prefix}%",
            "limit": limit,
        })
        return [row[0] for row in result.fetchall()]
```

**Step 4: Run tests — verify PASS**

```bash
cd src/backend && python -m pytest tests/test_search_ranking.py -v
```

**Step 5: Commit**

```bash
git add src/backend/modules/search.py src/backend/tests/test_search_ranking.py
git commit -m "feat(DATA-004): add SearchModule with FTS5, semantic search, and RRF ranking"
```

---

## Task 10: DATA-004 — Search API + Audit

**Files:**
- Create: `src/backend/api/search.py` (new)
- Modify: `src/backend/api/__init__.py:39` (register router)
- Modify: `src/backend/core/audit.py` (add log_search_event)
- Test: `src/backend/tests/test_search_api.py` (new)

**Step 1: Add log_search_event to audit.py**

Add after `log_auth_event` in `src/backend/core/audit.py` (after line 207):

```python
async def log_search_event(
    db: AsyncSession,
    profile_id: str,
    query: str,
    mode: str,
    result_count: int,
    details: Optional[dict[str, Any]] = None,
) -> "AuditLog":
    """Log a search query event."""
    return await create_audit_log(
        db=db,
        event_type="search.query",
        action=f"Searched for '{query}' ({mode} mode, {result_count} results)",
        profile_id=profile_id,
        entity_type="search",
        details={**(details or {}), "query": query, "mode": mode, "result_count": result_count},
    )
```

**Step 2: Create search API**

Create `src/backend/api/search.py`:

```python
"""
Search API endpoints.

Hybrid full-text + semantic search with RRF ranking.
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import RequireAuth, ProfileDbSession
from core.audit import log_search_event
from modules.search import SearchModule, SearchFilters

logger = logging.getLogger(__name__)

router = APIRouter()


class SearchResultItem(BaseModel):
    id: str
    type: str
    title: str
    score: float
    snippet: str
    highlight: str = ""
    collected_at: Optional[str] = None
    analyte: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    explanation: str = ""


class SearchResponseModel(BaseModel):
    results: list[SearchResultItem]
    total_count: int
    query: str
    mode: str


@router.get("", response_model=SearchResponseModel)
async def search(
    session: RequireAuth,
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    mode: str = Query("hybrid", description="Search mode: hybrid, text, or semantic"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    analyte: Optional[str] = Query(None),
    abnormal_only: bool = Query(False),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Search observations and documents.

    Supports hybrid (FTS5 + semantic), text-only, or semantic-only modes.
    """
    profile_id = session.profile_id
    search_module = SearchModule()

    filters = SearchFilters(
        from_date=from_date,
        to_date=to_date,
        analyte=analyte,
        abnormal_only=abnormal_only,
    )

    if mode == "text":
        results = await search_module.search_fulltext(
            q, profile_db, profile_id, filters, limit=limit + offset,
        )
        total = len(results)
        results = results[offset:offset + limit]
        response_mode = "text"
    elif mode == "semantic":
        results_raw = await search_module.search_semantic(
            q, profile_db, profile_id, top_k=limit + offset,
        )
        total = len(results_raw)
        results = results_raw[offset:offset + limit]
        response_mode = "semantic"
    else:
        search_response = await search_module.search_hybrid(
            q, profile_db, profile_id, filters, limit=limit + offset,
        )
        total = search_response.total_count
        results = search_response.results[offset:offset + limit]
        response_mode = "hybrid"

    try:
        await log_search_event(
            db=master_db, profile_id=profile_id,
            query=q, mode=response_mode, result_count=total,
        )
        await master_db.commit()
    except Exception as e:
        logger.warning(f"Failed to log search event: {e}")

    return SearchResponseModel(
        results=[
            SearchResultItem(
                id=r.id,
                type=r.type,
                title=r.title,
                score=r.score,
                snippet=r.snippet,
                highlight=r.highlight,
                collected_at=r.collected_at.isoformat() if r.collected_at else None,
                analyte=r.analyte,
                value=r.value,
                unit=r.unit,
                explanation=r.explanation,
            )
            for r in results
        ],
        total_count=total,
        query=q,
        mode=response_mode,
    )


@router.get("/suggestions", response_model=list[str])
async def search_suggestions(
    session: RequireAuth,
    prefix: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=50),
    profile_db: ProfileDbSession = None,
):
    """Autocomplete suggestions for analyte names."""
    search_module = SearchModule()
    return await search_module.get_suggestions(
        prefix=prefix,
        profile_db=profile_db,
        profile_id=session.profile_id,
        limit=limit,
    )
```

**Step 3: Register router**

In `src/backend/api/__init__.py`, add import and include:

```python
from .search import router as search_router
```

Add at end of router includes (after line 38):

```python
router.include_router(search_router, prefix="/search", tags=["search"])
```

**Step 4: Commit**

```bash
git add src/backend/api/search.py src/backend/api/__init__.py src/backend/core/audit.py
git commit -m "feat(DATA-004): add search API endpoints with hybrid/text/semantic modes and audit logging"
```

---

## Task 11: DATA-004 — Search Frontend Service

**Files:**
- Create: `src/frontend/src/services/search.ts` (new)
- Modify: `src/frontend/src/services/index.ts` (re-export)

**Step 1: Create search service**

Create `src/frontend/src/services/search.ts`:

```typescript
/**
 * Search API Service
 *
 * React Query hooks for hybrid search functionality.
 * Sprint 04: DATA-004/005
 */

import { useQuery } from '@tanstack/react-query';
import { apiGet } from './api';

export interface SearchFilters {
  mode?: 'hybrid' | 'text' | 'semantic';
  limit?: number;
  offset?: number;
  from_date?: string;
  to_date?: string;
  analyte?: string;
  abnormal_only?: boolean;
}

export interface SearchResultItem {
  id: string;
  type: 'observation' | 'chunk';
  title: string;
  score: number;
  snippet: string;
  highlight: string;
  collected_at: string | null;
  analyte: string | null;
  value: number | null;
  unit: string | null;
  explanation: string;
}

export interface SearchResponse {
  results: SearchResultItem[];
  total_count: number;
  query: string;
  mode: string;
}

async function fetchSearchResults(
  query: string,
  filters: SearchFilters = {},
): Promise<SearchResponse> {
  const params: Record<string, string> = { q: query };
  if (filters.mode) params.mode = filters.mode;
  if (filters.limit) params.limit = String(filters.limit);
  if (filters.offset) params.offset = String(filters.offset);
  if (filters.from_date) params.from_date = filters.from_date;
  if (filters.to_date) params.to_date = filters.to_date;
  if (filters.analyte) params.analyte = filters.analyte;
  if (filters.abnormal_only) params.abnormal_only = 'true';

  return apiGet<SearchResponse>('/search', params);
}

async function fetchSuggestions(prefix: string, limit = 10): Promise<string[]> {
  return apiGet<string[]>('/search/suggestions', {
    prefix,
    limit: String(limit),
  });
}

/**
 * Search hook with debounced query.
 * Only fires when query is non-empty.
 */
export function useSearch(query: string, filters: SearchFilters = {}) {
  return useQuery({
    queryKey: ['search', query, filters],
    queryFn: () => fetchSearchResults(query, filters),
    enabled: query.length > 0,
    staleTime: 1000 * 60,
  });
}

/**
 * Autocomplete suggestions hook.
 */
export function useSearchSuggestions(prefix: string) {
  return useQuery({
    queryKey: ['search', 'suggestions', prefix],
    queryFn: () => fetchSuggestions(prefix),
    enabled: prefix.length >= 1,
    staleTime: 1000 * 60 * 5,
  });
}
```

**Step 2: Re-export from services/index.ts**

Add to `src/frontend/src/services/index.ts`:

```typescript
// Search hooks
export { useSearch, useSearchSuggestions } from './search';
export type { SearchFilters, SearchResultItem, SearchResponse } from './search';
```

**Step 3: Commit**

```bash
git add src/frontend/src/services/search.ts src/frontend/src/services/index.ts
git commit -m "feat(DATA-004): add search service hooks with useSearch and useSearchSuggestions"
```

---

## Task 12: DATA-005 — Search UI Components

**Files:**
- Create: `src/frontend/src/components/SearchResults.tsx` (new)
- Create: `src/frontend/src/pages/SearchPage.tsx` (new)
- Modify: `src/frontend/src/pages/index.ts` (export)
- Modify: `src/frontend/src/App.tsx` (route)
- Test: `src/frontend/src/__tests__/SearchPage.test.tsx` (new)

**Step 1: Create SearchResults component**

Create `src/frontend/src/components/SearchResults.tsx`:

```tsx
/**
 * SearchResults - Renders search result cards
 *
 * Sprint 04: DATA-005
 */

import { FileText, FlaskConical, Calendar } from 'lucide-react';
import { Badge } from '@/components/ui';
import type { SearchResultItem } from '@/services/search';

interface SearchResultsProps {
  results: SearchResultItem[];
  isLoading?: boolean;
}

function ResultSkeleton() {
  return (
    <div className="animate-pulse space-y-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="bg-surface-muted rounded-xl p-4 space-y-2">
          <div className="h-4 bg-black/[0.06] rounded w-1/3" />
          <div className="h-3 bg-black/[0.04] rounded w-2/3" />
        </div>
      ))}
    </div>
  );
}

export function SearchResults({ results, isLoading }: SearchResultsProps) {
  if (isLoading) return <ResultSkeleton />;

  if (results.length === 0) {
    return (
      <div className="text-center py-12">
        <FileText className="w-12 h-12 text-ink-tertiary mx-auto mb-4" />
        <p className="text-ink-secondary">No results found.</p>
        <p className="text-sm text-ink-tertiary mt-1">Try a different search term or adjust filters.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {results.map((result) => (
        <div
          key={result.id}
          className="bg-white rounded-xl border border-black/[0.06] p-4 hover:border-accent/30 transition-colors"
        >
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-surface-muted flex items-center justify-center flex-shrink-0 mt-0.5">
              {result.type === 'observation' ? (
                <FlaskConical className="w-4 h-4 text-accent" />
              ) : (
                <FileText className="w-4 h-4 text-ink-secondary" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="text-sm font-semibold text-ink truncate">{result.title}</h3>
                {result.value !== null && result.unit && (
                  <Badge variant="default">{result.value} {result.unit}</Badge>
                )}
                <Badge variant={result.type === 'observation' ? 'verified' : 'default'}>
                  {result.type === 'observation' ? 'Lab' : 'Document'}
                </Badge>
              </div>
              <p
                className="text-sm text-ink-secondary line-clamp-2"
                dangerouslySetInnerHTML={{ __html: result.snippet }}
              />
              <div className="flex items-center gap-4 mt-2 text-xs text-ink-tertiary">
                {result.collected_at && (
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {new Date(result.collected_at).toLocaleDateString()}
                  </span>
                )}
                <span>Relevance: {(result.score * 100).toFixed(1)}%</span>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
```

**Step 2: Create SearchPage**

Create `src/frontend/src/pages/SearchPage.tsx`:

```tsx
/**
 * SearchPage - Hybrid search with faceted filters
 *
 * Sprint 04: DATA-005
 */

import { useState, useMemo, useCallback } from 'react';
import { Search, SlidersHorizontal, X } from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { SearchResults } from '@/components/SearchResults';
import { useSearch } from '@/services/search';
import type { SearchFilters } from '@/services/search';

export function SearchPage() {
  const [inputValue, setInputValue] = useState('');
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState<SearchFilters>({
    mode: 'hybrid',
    limit: 20,
    offset: 0,
  });
  const [showFilters, setShowFilters] = useState(false);

  const { data, isLoading, isFetching } = useSearch(query, filters);

  // Debounced search
  const debounceRef = useMemo(() => ({ timer: null as ReturnType<typeof setTimeout> | null }), []);

  const handleInputChange = useCallback(
    (value: string) => {
      setInputValue(value);
      if (debounceRef.timer) clearTimeout(debounceRef.timer);
      debounceRef.timer = setTimeout(() => {
        setQuery(value.trim());
        setFilters((prev) => ({ ...prev, offset: 0 }));
      }, 300);
    },
    [debounceRef],
  );

  const handleModeChange = (mode: SearchFilters['mode']) => {
    setFilters((prev) => ({ ...prev, mode, offset: 0 }));
  };

  const handleClear = () => {
    setInputValue('');
    setQuery('');
  };

  const handlePageNext = () => {
    setFilters((prev) => ({
      ...prev,
      offset: (prev.offset || 0) + (prev.limit || 20),
    }));
  };

  const handlePagePrev = () => {
    setFilters((prev) => ({
      ...prev,
      offset: Math.max(0, (prev.offset || 0) - (prev.limit || 20)),
    }));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
          Search
        </h1>
        <p className="text-ink-secondary mt-1">
          Search across your lab results and documents
        </p>
      </div>

      {/* Search bar */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-ink-tertiary" />
        <input
          type="text"
          value={inputValue}
          onChange={(e) => handleInputChange(e.target.value)}
          placeholder="Search analytes, values, documents..."
          className="w-full pl-12 pr-20 py-3 rounded-xl border border-black/[0.08] bg-white text-ink placeholder:text-ink-tertiary focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
        />
        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
          {inputValue && (
            <button onClick={handleClear} className="p-1.5 rounded-lg hover:bg-surface-muted">
              <X className="w-4 h-4 text-ink-tertiary" />
            </button>
          )}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="p-1.5 rounded-lg hover:bg-surface-muted"
          >
            <SlidersHorizontal className="w-4 h-4 text-ink-secondary" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Results */}
        <div className="col-span-2">
          {query ? (
            <>
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm text-ink-secondary">
                  {data ? `${data.total_count} results for "${data.query}"` : 'Searching...'}
                </p>
                {(isFetching) && (
                  <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                )}
              </div>
              <SearchResults results={data?.results || []} isLoading={isLoading} />
              {/* Pagination */}
              {data && data.total_count > (filters.limit || 20) && (
                <div className="flex items-center justify-center gap-4 mt-6">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handlePagePrev}
                    disabled={(filters.offset || 0) === 0}
                  >
                    Previous
                  </Button>
                  <span className="text-sm text-ink-secondary">
                    {(filters.offset || 0) + 1}–{Math.min((filters.offset || 0) + (filters.limit || 20), data.total_count)} of {data.total_count}
                  </span>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handlePageNext}
                    disabled={(filters.offset || 0) + (filters.limit || 20) >= data.total_count}
                  >
                    Next
                  </Button>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-16">
              <Search className="w-12 h-12 text-ink-tertiary mx-auto mb-4" />
              <p className="text-ink-secondary">Enter a search term to find lab results and documents.</p>
            </div>
          )}
        </div>

        {/* Filters sidebar */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Search Mode</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {(['hybrid', 'text', 'semantic'] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => handleModeChange(mode)}
                  className={`w-full text-left px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                    filters.mode === mode
                      ? 'bg-accent-subtle text-accent'
                      : 'bg-surface-muted text-ink-secondary hover:bg-surface-sunken'
                  }`}
                >
                  {mode === 'hybrid' ? 'Hybrid (Recommended)' : mode === 'text' ? 'Full Text' : 'Semantic'}
                </button>
              ))}
            </CardContent>
          </Card>

          {showFilters && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Filters</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <label className="flex items-center gap-2 text-sm text-ink-secondary">
                  <input
                    type="checkbox"
                    checked={filters.abnormal_only || false}
                    onChange={(e) =>
                      setFilters((prev) => ({ ...prev, abnormal_only: e.target.checked, offset: 0 }))
                    }
                    className="rounded border-black/[0.12]"
                  />
                  Abnormal values only
                </label>
                <div>
                  <label className="text-xs text-ink-tertiary mb-1 block">From date</label>
                  <input
                    type="date"
                    value={filters.from_date || ''}
                    onChange={(e) =>
                      setFilters((prev) => ({ ...prev, from_date: e.target.value || undefined, offset: 0 }))
                    }
                    className="w-full px-3 py-1.5 rounded-lg border border-black/[0.08] text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-ink-tertiary mb-1 block">To date</label>
                  <input
                    type="date"
                    value={filters.to_date || ''}
                    onChange={(e) =>
                      setFilters((prev) => ({ ...prev, to_date: e.target.value || undefined, offset: 0 }))
                    }
                    className="w-full px-3 py-1.5 rounded-lg border border-black/[0.08] text-sm"
                  />
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
```

**Step 3: Export SearchPage from pages/index.ts**

Add to `src/frontend/src/pages/index.ts`:

```typescript
export { SearchPage } from './SearchPage';
```

**Step 4: Add route to App.tsx**

In `src/frontend/src/App.tsx`, add import:

```typescript
import { SearchPage } from './pages';
```

(Already imported via barrel — just need to add to destructured import on line 28-30.)

Add route inside the protected layout (after `export` route, before `settings`):

```tsx
              <Route path="search" element={<SearchPage />} />
```

**Step 5: Write SearchPage test**

Create `src/frontend/src/__tests__/SearchPage.test.tsx`:

```tsx
/**
 * SearchPage Tests
 *
 * Sprint 04: DATA-005
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SearchPage } from '@/pages/SearchPage';
import * as api from '@/services/api';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiGetRaw: vi.fn(),
  apiPost: vi.fn(),
  ApiError: class ApiError extends Error {
    constructor(public status: number, public statusText: string, message: string) {
      super(message);
    }
  },
}));

vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion');
  return {
    ...actual,
    motion: {
      div: ({ children, ...props }: React.PropsWithChildren<object>) => <div {...props}>{children}</div>,
    },
  };
});

function renderWithProviders(component: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{component}</BrowserRouter>
    </QueryClientProvider>
  );
}

describe('SearchPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders search input', () => {
    renderWithProviders(<SearchPage />);
    expect(screen.getByPlaceholderText(/search analytes/i)).toBeInTheDocument();
  });

  it('shows empty state before search', () => {
    renderWithProviders(<SearchPage />);
    expect(screen.getByText(/enter a search term/i)).toBeInTheDocument();
  });

  it('displays results after typing', async () => {
    const mockResponse = {
      results: [
        {
          id: 'obs-1', type: 'observation', title: 'Glucose',
          score: 0.95, snippet: 'Glucose: 95 mg/dL', highlight: '',
          collected_at: '2024-01-15', analyte: 'glucose',
          value: 95, unit: 'mg/dL', explanation: 'FTS match',
        },
      ],
      total_count: 1, query: 'glucose', mode: 'hybrid',
    };
    vi.mocked(api.apiGet).mockResolvedValue(mockResponse);

    const user = userEvent.setup();
    renderWithProviders(<SearchPage />);

    await user.type(screen.getByPlaceholderText(/search analytes/i), 'glucose');

    await waitFor(() => {
      expect(screen.getByText('Glucose')).toBeInTheDocument();
    }, { timeout: 2000 });
  });

  it('shows search mode buttons', () => {
    renderWithProviders(<SearchPage />);
    expect(screen.getByText(/hybrid/i)).toBeInTheDocument();
    expect(screen.getByText(/full text/i)).toBeInTheDocument();
    expect(screen.getByText(/semantic/i)).toBeInTheDocument();
  });
});
```

**Step 6: Run tests**

```bash
cd src/frontend && npx vitest run src/__tests__/SearchPage.test.tsx
```

**Step 7: Commit**

```bash
git add src/frontend/src/components/SearchResults.tsx src/frontend/src/pages/SearchPage.tsx src/frontend/src/pages/index.ts src/frontend/src/App.tsx src/frontend/src/__tests__/SearchPage.test.tsx
git commit -m "feat(DATA-005): add SearchPage and SearchResults with faceted filters, pagination, and mode selector"
```

---

## Task 13: DATA-006 — Importer Base Class and Registry

**Files:**
- Create: `src/backend/modules/importers/__init__.py` (new)
- Create: `src/backend/modules/importers/base.py` (new)

**Step 1: Create base module**

Create `src/backend/modules/importers/__init__.py`:

```python
"""
External source importers.

Pluggable parsers for Apple Health, Google Fit, Quest, LabCorp, HL7 v2, and generic CSV.
"""

from .base import BaseImporter, ImportResult, ImportedObservation, ImportError as ImportRowError
from .apple_health import AppleHealthImporter
from .google_fit import GoogleFitImporter
from .generic_csv import GenericCSVImporter
from .quest import QuestImporter
from .labcorp import LabCorpImporter
from .hl7v2 import HL7v2Importer

IMPORTER_REGISTRY: dict[str, type[BaseImporter]] = {
    "apple_health": AppleHealthImporter,
    "google_fit": GoogleFitImporter,
    "generic_csv": GenericCSVImporter,
    "quest": QuestImporter,
    "labcorp": LabCorpImporter,
    "hl7v2": HL7v2Importer,
}

def get_importer(source_type: str) -> BaseImporter:
    """Get an importer instance by source type."""
    cls = IMPORTER_REGISTRY.get(source_type)
    if cls is None:
        raise ValueError(f"Unknown source type: {source_type}. Supported: {list(IMPORTER_REGISTRY.keys())}")
    return cls()

__all__ = [
    "BaseImporter", "ImportResult", "ImportedObservation", "ImportRowError",
    "IMPORTER_REGISTRY", "get_importer",
]
```

Create `src/backend/modules/importers/base.py`:

```python
"""
Base importer interface.

All external source parsers implement BaseImporter.
Design Decisions DD-2, DD-8: Synthetic Document provenance, security guardrails.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from core.config import settings


@dataclass
class ImportedObservation:
    """A single observation parsed from an external source."""
    analyte_raw: str
    value: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    collected_at: Optional[datetime] = None
    ref_low: Optional[float] = None
    ref_high: Optional[float] = None
    flag: Optional[str] = None


@dataclass
class ImportError:
    """A per-row parsing error."""
    row: int
    field: str
    message: str


@dataclass
class ImportResult:
    """Result of parsing an external file."""
    observations: list[ImportedObservation] = field(default_factory=list)
    source_metadata: dict = field(default_factory=dict)
    errors: list[ImportError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class BaseImporter(ABC):
    """Abstract base for all external source importers."""

    source_name: str = ""
    supported_extensions: list[str] = []

    # Security limits (DD-8)
    max_rows: int = 100_000
    max_columns: int = 50
    max_error_rate: float = 0.10  # Hard-fail above 10%

    def validate_file_size(self, file_bytes: bytes) -> None:
        """Check file size against config limit."""
        max_bytes = settings.max_import_file_size_mb * 1024 * 1024
        if len(file_bytes) > max_bytes:
            raise ValueError(
                f"File too large: {len(file_bytes) / 1024 / 1024:.1f}MB "
                f"(max: {settings.max_import_file_size_mb}MB)"
            )

    def validate_extension(self, filename: str) -> None:
        """Check file extension against allowed list."""
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext not in self.supported_extensions:
            raise ValueError(
                f"Unsupported extension '.{ext}' for {self.source_name}. "
                f"Supported: {self.supported_extensions}"
            )

    def check_error_rate(self, result: ImportResult) -> None:
        """Hard-fail if error rate exceeds threshold."""
        total = len(result.observations) + len(result.errors)
        if total > 0 and len(result.errors) / total > self.max_error_rate:
            raise ValueError(
                f"Error rate {len(result.errors)}/{total} ({len(result.errors)/total:.0%}) "
                f"exceeds maximum of {self.max_error_rate:.0%}"
            )

    @abstractmethod
    def parse(self, file_bytes: bytes, filename: str) -> ImportResult:
        """Parse an external file into observations."""
        ...

    def safe_parse(self, file_bytes: bytes, filename: str) -> ImportResult:
        """Parse with validation guardrails."""
        self.validate_file_size(file_bytes)
        self.validate_extension(filename)
        result = self.parse(file_bytes, filename)
        self.check_error_rate(result)
        return result
```

**Step 2: Commit (placeholder — other importers created in next tasks)**

```bash
git add src/backend/modules/importers/base.py
git commit -m "feat(DATA-006): add BaseImporter ABC with security guardrails"
```

---

## Task 14: DATA-006 — Apple Health Importer

**Files:**
- Create: `src/backend/modules/importers/apple_health.py` (new)
- Test: `src/backend/tests/test_import_health_apps.py` (new)

**Step 1: Write the failing test**

Create `src/backend/tests/test_import_health_apps.py`:

```python
"""Tests for Apple Health and Google Fit importers."""

import pytest
from datetime import datetime
from modules.importers.base import ImportResult
from modules.importers.apple_health import AppleHealthImporter


SAMPLE_APPLE_HEALTH_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
  <Record type="HKQuantityTypeIdentifierBloodGlucose"
          sourceName="Health" unit="mg/dL" value="95"
          startDate="2024-01-15 08:30:00 -0500"
          endDate="2024-01-15 08:30:00 -0500"/>
  <Record type="HKQuantityTypeIdentifierBodyMass"
          sourceName="Health" unit="lb" value="175"
          startDate="2024-01-15 07:00:00 -0500"
          endDate="2024-01-15 07:00:00 -0500"/>
  <Record type="HKQuantityTypeIdentifierHeartRate"
          sourceName="Apple Watch" unit="count/min" value="72"
          startDate="2024-01-15 12:00:00 -0500"
          endDate="2024-01-15 12:00:00 -0500"/>
</HealthData>
"""


class TestAppleHealthImporter:
    def setup_method(self):
        self.importer = AppleHealthImporter()

    def test_parse_valid_xml(self):
        result = self.importer.parse(SAMPLE_APPLE_HEALTH_XML, "export.xml")
        assert isinstance(result, ImportResult)
        assert len(result.observations) == 3
        assert len(result.errors) == 0

    def test_observation_values_mapped(self):
        result = self.importer.parse(SAMPLE_APPLE_HEALTH_XML, "export.xml")
        glucose = next(o for o in result.observations if "glucose" in o.analyte_raw.lower())
        assert glucose.value == 95.0
        assert glucose.unit == "mg/dL"

    def test_dates_parsed(self):
        result = self.importer.parse(SAMPLE_APPLE_HEALTH_XML, "export.xml")
        for obs in result.observations:
            assert obs.collected_at is not None
            assert isinstance(obs.collected_at, datetime)

    def test_source_metadata(self):
        result = self.importer.parse(SAMPLE_APPLE_HEALTH_XML, "export.xml")
        assert result.source_metadata["source"] == "apple_health"
        assert "record_count" in result.source_metadata

    def test_empty_xml_returns_empty(self):
        xml = b'<?xml version="1.0"?><HealthData></HealthData>'
        result = self.importer.parse(xml, "empty.xml")
        assert len(result.observations) == 0

    def test_malformed_xml_raises(self):
        with pytest.raises(ValueError, match="XML"):
            self.importer.parse(b"not xml at all", "bad.xml")

    def test_supported_extensions(self):
        assert "xml" in self.importer.supported_extensions
```

**Step 2: Implement Apple Health importer**

Create `src/backend/modules/importers/apple_health.py`:

```python
"""
Apple Health XML importer.

Parses Apple Health export.xml files.
Uses defusedxml for safe XML parsing (DD-8: prevents XXE).
"""

import logging
from datetime import datetime
from typing import Optional

from .base import BaseImporter, ImportResult, ImportedObservation, ImportError

logger = logging.getLogger(__name__)

# Map Apple Health type identifiers to canonical analyte names
TYPE_MAP = {
    "HKQuantityTypeIdentifierBloodGlucose": "blood_glucose",
    "HKQuantityTypeIdentifierBodyMass": "body_mass",
    "HKQuantityTypeIdentifierBodyMassIndex": "bmi",
    "HKQuantityTypeIdentifierHeartRate": "heart_rate",
    "HKQuantityTypeIdentifierBloodPressureSystolic": "blood_pressure_systolic",
    "HKQuantityTypeIdentifierBloodPressureDiastolic": "blood_pressure_diastolic",
    "HKQuantityTypeIdentifierOxygenSaturation": "oxygen_saturation",
    "HKQuantityTypeIdentifierBodyTemperature": "body_temperature",
    "HKQuantityTypeIdentifierRespiratoryRate": "respiratory_rate",
    "HKQuantityTypeIdentifierLeanBodyMass": "lean_body_mass",
    "HKQuantityTypeIdentifierBodyFatPercentage": "body_fat_percentage",
}


def _parse_apple_date(date_str: str) -> Optional[datetime]:
    """Parse Apple Health date format: '2024-01-15 08:30:00 -0500'."""
    try:
        # Strip timezone offset for simplicity (store as naive UTC-ish)
        parts = date_str.rsplit(" ", 1)
        return datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S")
    except (ValueError, IndexError):
        return None


class AppleHealthImporter(BaseImporter):
    source_name = "apple_health"
    supported_extensions = ["xml"]

    def parse(self, file_bytes: bytes, filename: str) -> ImportResult:
        try:
            import defusedxml.ElementTree as ET
        except ImportError:
            import xml.etree.ElementTree as ET
            logger.warning("defusedxml not available, falling back to stdlib xml (less safe)")

        try:
            root = ET.fromstring(file_bytes)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML: {e}")

        observations = []
        errors = []
        row_idx = 0

        for record in root.iter("Record"):
            row_idx += 1
            if row_idx > self.max_rows:
                errors.append(ImportError(
                    row=row_idx, field="", message=f"Row limit {self.max_rows} exceeded"
                ))
                break

            record_type = record.get("type", "")
            analyte_raw = TYPE_MAP.get(record_type, record_type)

            try:
                value_str = record.get("value", "")
                value = float(value_str) if value_str else None
            except ValueError:
                errors.append(ImportError(
                    row=row_idx, field="value",
                    message=f"Non-numeric value: {record.get('value')}",
                ))
                continue

            collected_at = _parse_apple_date(record.get("startDate", ""))
            unit = record.get("unit", "")

            observations.append(ImportedObservation(
                analyte_raw=analyte_raw,
                value=value,
                unit=unit,
                collected_at=collected_at,
            ))

        return ImportResult(
            observations=observations,
            source_metadata={
                "source": "apple_health",
                "record_count": row_idx,
                "filename": filename,
            },
            errors=errors,
        )
```

**Step 3: Run tests — verify PASS**

```bash
cd src/backend && python -m pytest tests/test_import_health_apps.py -v
```

**Step 4: Commit**

```bash
git add src/backend/modules/importers/apple_health.py src/backend/tests/test_import_health_apps.py
git commit -m "feat(DATA-006): add Apple Health XML importer with defusedxml"
```

---

## Task 15: DATA-006 — Remaining Importers (Google Fit, CSV, Quest, LabCorp, HL7v2)

**Files:**
- Create: `src/backend/modules/importers/google_fit.py`
- Create: `src/backend/modules/importers/generic_csv.py`
- Create: `src/backend/modules/importers/quest.py`
- Create: `src/backend/modules/importers/labcorp.py`
- Create: `src/backend/modules/importers/hl7v2.py`
- Test: `src/backend/tests/test_import_lab_providers.py` (new)

Each importer follows the same pattern as Apple Health. Implement all five parsers, then the __init__.py registry, then tests.

**Key implementation notes per parser:**

- **google_fit.py**: Parse JSON array of data points. Supported extensions: `["json"]`.
- **generic_csv.py**: CSV with configurable column mapping via header detection. Extensions: `["csv"]`. Enforce `max_rows` and `max_columns`.
- **quest.py**: Extends GenericCSVImporter with Quest-specific column names (Test Name, Result, Units, Reference Range, Abnormal Flag). Extensions: `["csv"]`.
- **labcorp.py**: Extends GenericCSVImporter with LabCorp-specific columns (Test, Result, Reference Interval, Flag). Extensions: `["csv"]`.
- **hl7v2.py**: Parse pipe-delimited HL7 v2 messages. Extract OBX segments. Segment limit: 10,000. Field length limit: 10KB. Extensions: `["hl7"]`.

**Test file:** `test_import_lab_providers.py` with fixtures for each provider format and tests for:
- Happy path parsing
- Column mapping
- Error handling for malformed rows
- Row count limits

**Step N (final): Commit all importers and tests**

```bash
git add src/backend/modules/importers/ src/backend/tests/test_import_lab_providers.py
git commit -m "feat(DATA-006): add Google Fit, generic CSV, Quest, LabCorp, and HL7v2 importers with tests"
```

---

## Task 16: DATA-006 — External Import API Endpoint

**Files:**
- Modify: `src/backend/api/documents.py` (add /import/external endpoint)

**Step 1: Add endpoint**

Add import at top of `api/documents.py`:

```python
from modules.importers import get_importer, IMPORTER_REGISTRY
```

Add new response model:

```python
class ExternalImportResponse(BaseModel):
    document_id: str
    source_type: str
    observation_count: int
    error_count: int
    warnings: list[str]
```

Add endpoint after existing `import_document` endpoint:

```python
@router.post(
    "/import/external",
    response_model=ExternalImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_external(
    session: RequireAuth,
    source_type: str = Query(..., description=f"Source type: {list(IMPORTER_REGISTRY.keys())}"),
    file: UploadFile = File(...),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Import observations from an external source file.

    Creates a synthetic Document for provenance (DD-2).
    Route under /documents/import/external (DD-3).
    """
    import uuid
    from datetime import datetime as dt

    profile_id = session.profile_id
    file_bytes = await file.read()

    # Parse using appropriate importer
    importer = get_importer(source_type)
    result = importer.safe_parse(file_bytes, file.filename or "unknown")

    # Create synthetic Document (DD-2)
    doc_id = str(uuid.uuid4())
    from models import Document, Observation
    import hashlib

    content_hash = hashlib.sha256(file_bytes).hexdigest()
    path_hash = hashlib.sha256((file.filename or "").encode()).hexdigest()

    doc = Document(
        id=doc_id,
        profile_id=profile_id,
        path_hash=path_hash,
        content_hash=content_hash,
        doc_type="external_import",
        source=source_type,
        status="parsed",
        page_count=None,
        collection_date=result.observations[0].collected_at if result.observations else None,
        imported_at=dt.utcnow(),
        parsed_at=dt.utcnow(),
        metadata_json=json.dumps(result.source_metadata) if hasattr(json, 'dumps') else None,
    )
    profile_db.add(doc)

    # Create Observations
    obs_count = 0
    for imported_obs in result.observations:
        obs_id = str(uuid.uuid4())
        obs = Observation(
            id=obs_id,
            profile_id=profile_id,
            doc_id=doc_id,
            analyte_canonical=imported_obs.analyte_raw.lower().replace(" ", "_"),
            analyte_raw=imported_obs.analyte_raw,
            value=imported_obs.value,
            value_text=imported_obs.value_text,
            unit=imported_obs.unit,
            ref_low=imported_obs.ref_low,
            ref_high=imported_obs.ref_high,
            flag=imported_obs.flag,
            is_abnormal=imported_obs.flag is not None and imported_obs.flag != "",
            collected_at=imported_obs.collected_at,
            user_verified=False,
            extraction_confidence=0.9,
            version=1,
            created_at=dt.utcnow(),
            updated_at=dt.utcnow(),
        )
        profile_db.add(obs)
        obs_count += 1

    await profile_db.commit()

    # Audit log
    try:
        from core.audit import log_document_event
        await log_document_event(
            db=master_db, event="import", profile_id=profile_id,
            document_id=doc_id, filename=file.filename,
            details={"source": source_type, "type": "external", "observation_count": obs_count},
        )
        await master_db.commit()
    except Exception as e:
        logger.warning(f"Failed to log import event: {e}")

    return ExternalImportResponse(
        document_id=doc_id,
        source_type=source_type,
        observation_count=obs_count,
        error_count=len(result.errors),
        warnings=result.warnings[:10],
    )
```

**Step 2: Commit**

```bash
git add src/backend/api/documents.py
git commit -m "feat(DATA-006): add POST /documents/import/external with synthetic Document provenance"
```

---

## Task 17: DATA-006 — Frontend Import Hook

**Files:**
- Modify: `src/frontend/src/services/documents.ts` (add useImportExternal)
- Modify: `src/frontend/src/services/index.ts` (re-export)

**Step 1: Add hook**

Add to `src/frontend/src/services/documents.ts` after `useDeleteDocument`:

```typescript
export interface ExternalImportResponse {
  document_id: string;
  source_type: string;
  observation_count: number;
  error_count: number;
  warnings: string[];
}

async function importExternal(
  file: File,
  sourceType: string,
): Promise<ExternalImportResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(
    `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/documents/import/external?source_type=${encodeURIComponent(sourceType)}`,
    {
      method: 'POST',
      headers: {
        ...(() => {
          const token = (await import('@/stores/authStore')).useAuthStore.getState().token;
          return token ? { Authorization: `Bearer ${token}` } : {};
        })(),
      },
      body: formData,
    },
  );
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export function useImportExternal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ file, sourceType }: { file: File; sourceType: string }) =>
      importExternal(file, sourceType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}
```

**Step 2: Re-export**

Add to `src/frontend/src/services/index.ts`:

```typescript
export { useImportExternal } from './documents';
export type { ExternalImportResponse } from './documents';
```

**Step 3: Commit**

```bash
git add src/frontend/src/services/documents.ts src/frontend/src/services/index.ts
git commit -m "feat(DATA-006): add useImportExternal hook for external source imports"
```

---

## Task 18: Final — Build Verification and Test Run

**Step 1: Run frontend TypeScript check**

```bash
cd src/frontend && npx tsc --noEmit
```

**Step 2: Run frontend tests**

```bash
cd src/frontend && npx vitest run
```

**Step 3: Run backend tests (if pytest available)**

```bash
cd src/backend && python -m pytest tests/ -v
```

**Step 4: Fix any issues**

Address any TypeScript errors or test failures.

**Step 5: Final commit**

```bash
git add -A
git commit -m "chore: Sprint 04 build verification and test fixes"
```

---

## Summary

| Task | WP | Description | Files |
|------|-----|------------|-------|
| 0 | setup | Add dependencies | requirements.txt |
| 1 | DATA-001 | Chart generation | export.py, test_export_pdf.py |
| 2 | DATA-001 | Wire include_charts | api/export.py |
| 3 | DATA-002 | Excel export module | export.py, test_export_excel.py |
| 4 | DATA-002 | Excel API endpoint | api/export.py |
| 5 | DATA-003 | FHIR models | fhir_resources.py, test_export_fhir.py |
| 6 | DATA-003 | FHIR API endpoint | api/export.py |
| 7 | DATA-001/2/3 | Frontend hooks + buttons | export.ts, ExportPage.tsx |
| 8 | DATA-004 | FTS5 migration | 003_add_fts5_indexes.py |
| 9 | DATA-004 | Search module | search.py, test_search_ranking.py |
| 10 | DATA-004 | Search API + audit | api/search.py, audit.py |
| 11 | DATA-004 | Search frontend service | search.ts |
| 12 | DATA-005 | Search UI | SearchPage.tsx, SearchResults.tsx |
| 13 | DATA-006 | Importer base | base.py, __init__.py |
| 14 | DATA-006 | Apple Health | apple_health.py, test_import_health_apps.py |
| 15 | DATA-006 | Remaining importers | 5 parser files, test_import_lab_providers.py |
| 16 | DATA-006 | Import API | api/documents.py |
| 17 | DATA-006 | Import frontend hook | documents.ts |
| 18 | all | Build verification | — |
