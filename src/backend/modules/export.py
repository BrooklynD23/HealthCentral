"""
Export module.

Handles:
- Doctor-ready summary generation
- CSV/JSON data export
- Question list generation
"""

from typing import Optional
from dataclasses import dataclass
from datetime import datetime
import json
import csv
import re
from html import escape
from io import StringIO

FORMULA_PREFIXES = ("=", "+", "-", "@")
FORMULA_BYPASS_PREFIXES = (" ", "\t", "\r", "\n")
HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def sanitize_spreadsheet_cell(value):
    """
    Prevent formula injection in spreadsheet software.

    Prefixes risky string values with a single quote so spreadsheet apps
    interpret them as literal text.
    """
    if isinstance(value, str):
        normalized = value.lstrip("".join(FORMULA_BYPASS_PREFIXES))
        if normalized[:1] in FORMULA_PREFIXES:
            return f"'{value}"
    return value


def _escape_html(value: object) -> str:
    """HTML-escape untrusted content before interpolation."""
    return escape(str(value), quote=True)


def _escape_html_multiline(value: object) -> str:
    """Escape untrusted text while preserving line breaks."""
    return _escape_html(value).replace("\n", "<br>")


@dataclass
class SummarySection:
    """Section of a doctor summary."""
    title: str
    content: str
    citations: list[str] = None


@dataclass
class DoctorSummary:
    """Generated doctor-ready summary."""
    summary_id: str
    profile_id: str
    generated_at: datetime
    date_range_start: Optional[datetime]
    date_range_end: Optional[datetime]
    
    # Summary content
    key_findings: list[str]
    sections: list[SummarySection]
    
    # Statistics
    total_observations: int
    abnormal_count: int
    critical_count: int


@dataclass  
class QuestionPrompt:
    """A discussion prompt for clinician visits."""
    category: str  # "trend", "abnormal", "clarification"
    question: str
    context: str
    related_analytes: list[str]


class ExportModule:
    """
    Export generation service.
    
    Creates clinician-ready outputs and data exports.
    """
    
    def __init__(self):
        """Initialize export module."""
        pass
    
    async def generate_doctor_summary(
        self,
        profile_id: str,
        observations: list[dict],
        trends: list[dict],
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        include_all_values: bool = False,
        include_trends: bool = True,
    ) -> DoctorSummary:
        """
        Generate a doctor-ready summary.
        
        Creates a 1-2 page summary with:
        - Key findings (abnormalities, trends)
        - Organized by panel/category
        - Exact values and dates
        - Trend narratives
        """
        import uuid
        
        # Filter observations by date
        filtered_obs = observations
        if from_date:
            filtered_obs = [o for o in filtered_obs if o.get("collected_at", datetime.min) >= from_date]
        if to_date:
            filtered_obs = [o for o in filtered_obs if o.get("collected_at", datetime.max) <= to_date]
        
        # Identify key findings
        key_findings = []
        abnormal_count = 0
        critical_count = 0
        
        for obs in filtered_obs:
            if obs.get("is_abnormal"):
                abnormal_count += 1
                if obs.get("flag") in ["HH", "LL", "CRITICAL"]:
                    critical_count += 1
                    key_findings.append(
                        f"{obs['analyte_canonical']}: {obs['value']} {obs.get('unit', '')} "
                        f"(critical - {obs.get('flag')})"
                    )
                else:
                    key_findings.append(
                        f"{obs['analyte_canonical']}: {obs['value']} {obs.get('unit', '')} "
                        f"({obs.get('flag', 'abnormal')})"
                    )
        
        # Build sections
        sections = []
        
        # Summary section
        sections.append(SummarySection(
            title="Overview",
            content=self._generate_overview(
                total=len(filtered_obs),
                abnormal=abnormal_count,
                critical=critical_count,
                from_date=from_date,
                to_date=to_date,
            ),
        ))
        
        # Abnormal values section
        if abnormal_count > 0:
            sections.append(SummarySection(
                title="Values Outside Reference Range",
                content=self._format_abnormal_values(
                    [o for o in filtered_obs if o.get("is_abnormal")]
                ),
            ))
        
        # Trends section
        if include_trends and trends:
            sections.append(SummarySection(
                title="Notable Trends",
                content=self._format_trends(trends),
            ))
        
        return DoctorSummary(
            summary_id=str(uuid.uuid4()),
            profile_id=profile_id,
            generated_at=datetime.utcnow(),
            date_range_start=from_date,
            date_range_end=to_date,
            key_findings=key_findings[:10],  # Limit to top 10
            sections=sections,
            total_observations=len(filtered_obs),
            abnormal_count=abnormal_count,
            critical_count=critical_count,
        )
    
    def _generate_overview(
        self,
        total: int,
        abnormal: int,
        critical: int,
        from_date: Optional[datetime],
        to_date: Optional[datetime],
    ) -> str:
        """Generate overview paragraph."""
        parts = [f"This summary includes {total} lab values"]
        
        if from_date and to_date:
            parts.append(f"from {from_date.strftime('%B %d, %Y')} to {to_date.strftime('%B %d, %Y')}")
        elif from_date:
            parts.append(f"since {from_date.strftime('%B %d, %Y')}")
        
        parts.append(".")
        
        if abnormal > 0:
            parts.append(f"{abnormal} values were outside the reference range as flagged by the reporting lab.")
        if critical > 0:
            parts.append(f"{critical} values were flagged as critical.")
        
        return " ".join(parts)
    
    def _format_abnormal_values(self, observations: list[dict]) -> str:
        """Format abnormal values section."""
        lines = []
        for obs in sorted(observations, key=lambda x: x.get("collected_at", datetime.min), reverse=True):
            date_str = obs.get("collected_at", "").strftime("%m/%d/%Y") if obs.get("collected_at") else "Unknown date"
            lines.append(
                f"• {obs['analyte_canonical']}: {obs['value']} {obs.get('unit', '')} "
                f"(ref: {obs.get('ref_low', '?')}-{obs.get('ref_high', '?')}) "
                f"[{obs.get('flag', 'abnormal')}] - {date_str}"
            )
        return "\n".join(lines)
    
    def _format_trends(self, trends: list[dict]) -> str:
        """Format trends section."""
        lines = []
        for trend in trends:
            direction = trend.get("trend_direction", "stable")
            if direction != "stable":
                lines.append(
                    f"• {trend['analyte']}: {direction} trend "
                    f"({trend.get('delta_percent', 0):.1f}% change from prior)"
                )
        return "\n".join(lines) if lines else "No notable trends identified."

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

        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
        except ImportError:
            # Keep PDF/HTML export functional in environments without plotting deps.
            return self._build_fallback_chart_png()
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

    def _build_fallback_chart_png(self, width: int = 480, height: int = 240) -> bytes:
        """Generate a valid placeholder PNG when matplotlib is unavailable."""
        import struct
        import zlib

        width = max(width, 2)
        height = max(height, 2)

        def chunk(tag: bytes, payload: bytes) -> bytes:
            crc = zlib.crc32(tag + payload) & 0xFFFFFFFF
            return (
                struct.pack("!I", len(payload))
                + tag
                + payload
                + struct.pack("!I", crc)
            )

        raw = bytearray()
        for y in range(height):
            raw.append(0)  # Filter method 0 for each scanline.
            for x in range(width):
                base = 230 - int((y / (height - 1)) * 40)
                stripe = 18 if (x // 24) % 2 == 0 else 0
                r = max(0, min(255, base - stripe))
                g = max(0, min(255, base + 10))
                b = max(0, min(255, 245 - stripe))
                raw.extend((r, g, b))

        ihdr = struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0)
        idat = zlib.compress(bytes(raw), level=6)
        return (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", idat)
            + chunk(b"IEND", b"")
        )

    def export_csv(
        self,
        observations: list[dict],
        analyte_filter: Optional[list[str]] = None,
    ) -> str:
        """
        Export observations as CSV.
        
        Returns CSV string.
        """
        if analyte_filter:
            observations = [o for o in observations if o.get("analyte_canonical") in analyte_filter]
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Date",
            "Analyte",
            "Value",
            "Unit",
            "Reference Low",
            "Reference High",
            "Flag",
            "Verified",
        ])
        
        # Data rows
        for obs in sorted(observations, key=lambda x: (x.get("analyte_canonical", ""), x.get("collected_at", datetime.min))):
            date_str = obs.get("collected_at", "").strftime("%Y-%m-%d") if obs.get("collected_at") else ""
            writer.writerow([
                sanitize_spreadsheet_cell(date_str),
                sanitize_spreadsheet_cell(obs.get("analyte_canonical", "")),
                sanitize_spreadsheet_cell(obs.get("value", "")),
                sanitize_spreadsheet_cell(obs.get("unit", "")),
                sanitize_spreadsheet_cell(obs.get("ref_low", "")),
                sanitize_spreadsheet_cell(obs.get("ref_high", "")),
                sanitize_spreadsheet_cell(obs.get("flag", "")),
                sanitize_spreadsheet_cell("Yes" if obs.get("user_verified") else "No"),
            ])
        
        return output.getvalue()
    
    def export_json(
        self,
        observations: list[dict],
        analyte_filter: Optional[list[str]] = None,
    ) -> str:
        """
        Export observations as JSON.
        
        Returns JSON string.
        """
        if analyte_filter:
            observations = [o for o in observations if o.get("analyte_canonical") in analyte_filter]
        
        # Convert datetime objects to ISO strings
        export_data = []
        for obs in observations:
            export_obs = dict(obs)
            if "collected_at" in export_obs and export_obs["collected_at"]:
                export_obs["collected_at"] = export_obs["collected_at"].isoformat()
            export_data.append(export_obs)
        
        return json.dumps(export_data, indent=2)

    def export_excel(
        self,
        observations: list[dict],
        trends: list[dict],
        medications: Optional[list[dict]] = None,
    ) -> bytes:
        """
        Export data as formatted Excel workbook.

        Returns xlsx bytes with sheets: Summary, Labs, Medications, Trends.
        Includes conditional formatting for abnormal values.
        """
        from openpyxl import Workbook
        from openpyxl.styles import PatternFill, Font, Alignment
        from openpyxl.worksheet.datavalidation import DataValidation
        from io import BytesIO

        medications = medications or []
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
        ws_summary.append([f"Medications: {len(medications)}"])
        ws_summary.append([])
        ws_summary.append(["Workbook Metrics", "Value"])
        ws_summary["A7"].font = header_font
        ws_summary["B7"].font = header_font
        ws_summary["A7"].fill = header_fill
        ws_summary["B7"].fill = header_fill
        ws_summary.append(["Total Observations (formula)", '=MAX(0,COUNTA(Labs!B:B)-1)'])
        ws_summary.append([
            "Abnormal Values (formula)",
            '=MAX(0,COUNTIFS(Labs!A:A,"<>",Labs!G:G,"<>")-1)',
        ])
        ws_summary.append(["Medication Count (formula)", '=MAX(0,COUNTA(Medications!A:A)-1)'])
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
                sanitize_spreadsheet_cell(date_str),
                sanitize_spreadsheet_cell(obs.get("analyte_canonical", "")),
                sanitize_spreadsheet_cell(obs.get("value", "")),
                sanitize_spreadsheet_cell(obs.get("unit", "")),
                sanitize_spreadsheet_cell(obs.get("ref_low", "")),
                sanitize_spreadsheet_cell(obs.get("ref_high", "")),
                sanitize_spreadsheet_cell(obs.get("flag", "")),
                sanitize_spreadsheet_cell("Yes" if obs.get("user_verified") else "No"),
            ]
            ws_labs.append(row)
            if obs.get("is_abnormal"):
                row_idx = ws_labs.max_row
                for col_idx in range(1, len(lab_headers) + 1):
                    ws_labs.cell(row=row_idx, column=col_idx).fill = abnormal_fill

        flag_validation = DataValidation(
            type="list",
            formula1='"N,L,H,LL,HH,CRITICAL"',
            allow_blank=True,
        )
        verified_validation = DataValidation(
            type="list",
            formula1='"Yes,No"',
            allow_blank=False,
        )
        ws_labs.add_data_validation(flag_validation)
        ws_labs.add_data_validation(verified_validation)
        flag_validation.add("G2:G1048576")
        verified_validation.add("H2:H1048576")

        # Auto-width columns
        for col in ws_labs.columns:
            max_len = max((len(str(cell.value or "")) for cell in col), default=10)
            ws_labs.column_dimensions[col[0].column_letter].width = min(max_len + 2, 30)

        # --- Medications Sheet ---
        ws_meds = wb.create_sheet("Medications")
        medication_headers = [
            "Medication",
            "Generic Name",
            "Dosage",
            "Frequency",
            "Active",
            "Reminder Enabled",
            "Started",
            "Ended",
            "Instructions",
        ]
        ws_meds.append(medication_headers)
        for col_idx, _ in enumerate(medication_headers, 1):
            cell = ws_meds.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
        ws_meds.freeze_panes = "A2"

        for med in medications:
            dosage_parts = []
            amount = med.get("dosage_amount")
            unit = med.get("dosage_unit")
            if amount is not None:
                dosage_parts.append(str(amount))
            if unit:
                dosage_parts.append(str(unit))
            dosage = " ".join(dosage_parts)

            started_at = med.get("started_at")
            ended_at = med.get("ended_at")
            started_str = (
                started_at.strftime("%Y-%m-%d")
                if hasattr(started_at, "strftime")
                else str(started_at or "")
            )
            ended_str = (
                ended_at.strftime("%Y-%m-%d")
                if hasattr(ended_at, "strftime")
                else str(ended_at or "")
            )

            ws_meds.append([
                sanitize_spreadsheet_cell(med.get("name", "")),
                sanitize_spreadsheet_cell(med.get("generic_name", "")),
                sanitize_spreadsheet_cell(dosage),
                sanitize_spreadsheet_cell(med.get("frequency", "")),
                "TRUE" if med.get("is_active", True) else "FALSE",
                "TRUE" if med.get("reminder_enabled", False) else "FALSE",
                sanitize_spreadsheet_cell(started_str),
                sanitize_spreadsheet_cell(ended_str),
                sanitize_spreadsheet_cell(med.get("instructions", "")),
            ])

        bool_validation = DataValidation(
            type="list",
            formula1='"TRUE,FALSE"',
            allow_blank=False,
        )
        ws_meds.add_data_validation(bool_validation)
        bool_validation.add("E2:F1048576")

        for col in ws_meds.columns:
            max_len = max((len(str(cell.value or "")) for cell in col), default=10)
            ws_meds.column_dimensions[col[0].column_letter].width = min(max_len + 2, 40)

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
                sanitize_spreadsheet_cell(trend.get("analyte", "")),
                sanitize_spreadsheet_cell(trend.get("trend_direction", "")),
                round(trend.get("delta_percent", 0), 1),
            ])

        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf.read()

    def render_html_summary(
        self,
        summary_data: dict,
        chart_images: Optional[dict[str, bytes]] = None,
        template_options: Optional[dict] = None,
    ) -> str:
        """
        Render a doctor summary as an inline-CSS HTML document.

        Args:
            summary_data: Summary data dict with sections, key_findings, etc.
            template_options: Optional branding/section customization options.

        Returns:
            HTML string suitable for email/print
        """
        template_options = template_options or {}

        def _flag(name: str, default: bool = True) -> bool:
            value = template_options.get(name)
            return default if value is None else bool(value)

        brand_name = str(template_options.get("brand_name") or "HealthCentral").strip()[:80]
        brand_tagline = str(
            template_options.get("brand_tagline") or "Lab Results Summary"
        ).strip()[:120]
        accent_color = str(template_options.get("accent_color") or "#2D7D6F").strip()
        if not HEX_COLOR_RE.fullmatch(accent_color):
            accent_color = "#2D7D6F"
        safe_brand_name = _escape_html(brand_name)
        safe_brand_tagline = _escape_html(brand_tagline)

        include_key_findings = _flag("include_key_findings", default=True)
        include_overview = _flag("include_overview", default=True)
        include_abnormal = _flag("include_abnormal", default=True)
        include_trends = _flag("include_trends", default=True)
        include_questions = _flag("include_questions", default=True)
        include_disclaimer = _flag("include_disclaimer", default=True)

        date_range = summary_data.get("date_range", "")
        safe_date_range = _escape_html(date_range)
        key_findings = summary_data.get("key_findings", [])
        sections = summary_data.get("sections", [])
        questions = summary_data.get("questions", [])

        findings_html = ""
        for finding in key_findings:
            finding_text = str(finding)
            lower = finding_text.lower()
            color = "#b91c1c" if "critical" in lower else "#d97706" if any(
                f in lower for f in ["high", "low", "abnormal"]
            ) else "#374151"
            findings_html += f'<li style="color:{color};margin-bottom:4px;">{_escape_html(finding_text)}</li>'

        sections_html = ""
        for section in sections:
            title = str(section.get("title", ""))
            normalized_title = title.lower()
            if "overview" in normalized_title and not include_overview:
                continue
            if "outside reference range" in normalized_title and not include_abnormal:
                continue
            if "trend" in normalized_title and not include_trends:
                continue
            content = _escape_html_multiline(section.get("content", ""))
            sections_html += f"""
            <div style="margin-bottom:20px;">
                <h3 style="color:#1f2937;font-size:16px;margin-bottom:8px;border-bottom:1px solid #e5e7eb;padding-bottom:4px;">{_escape_html(title)}</h3>
                <p style="color:#4b5563;font-size:14px;line-height:1.6;">{content}</p>
            </div>"""

        questions_html = ""
        if include_questions and questions:
            questions_html = '<div style="margin-top:20px;"><h3 style="color:#1f2937;font-size:16px;margin-bottom:8px;">Questions for Your Provider</h3><ul style="color:#4b5563;font-size:14px;">'
            for q in questions:
                q_text = q.get("question", q) if isinstance(q, dict) else q
                questions_html += f"<li style='margin-bottom:6px;'>{_escape_html(q_text)}</li>"
            questions_html += "</ul></div>"

        charts_html = ""
        if chart_images:
            import base64
            charts_html = '<div style="margin-top:24px;"><h3 style="color:#1f2937;font-size:16px;margin-bottom:12px;">Trend Charts</h3>'
            for analyte_name, png_bytes in chart_images.items():
                b64 = base64.b64encode(png_bytes).decode('ascii')
                safe_analyte = _escape_html(analyte_name)
                charts_html += f'<div style="margin-bottom:16px;"><img src="data:image/png;base64,{b64}" alt="{safe_analyte} trend chart" style="max-width:100%;border:1px solid #e5e7eb;border-radius:8px;"></div>'
            charts_html += '</div>'

        disclaimer_html = ""
        if include_disclaimer:
            disclaimer_html = (
                '<p style="color:#9ca3af;font-size:12px;font-style:italic;">'
                "This is an AI-assisted summary of your lab results. It is not medical advice. "
                "Please discuss all findings with your healthcare provider."
                "</p>"
            )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{safe_brand_name} Summary</title></head>
<body style="font-family:'Source Sans 3',Arial,sans-serif;max-width:800px;margin:0 auto;padding:24px;background:#fff;">
    <div style="background:{accent_color};color:white;padding:20px 24px;border-radius:12px;margin-bottom:24px;">
        <h1 style="margin:0;font-family:'Fraunces',Georgia,serif;font-size:24px;">{safe_brand_name}</h1>
        <p style="margin:4px 0 0;font-size:14px;opacity:0.9;">{safe_brand_tagline}</p>
        {f'<p style="margin:4px 0 0;font-size:13px;opacity:0.8;">{safe_date_range}</p>' if date_range else ''}
    </div>

    {f'<div style="margin-bottom:20px;"><h2 style="color:#1f2937;font-size:18px;">Key Findings</h2><ul style="padding-left:20px;">{findings_html}</ul></div>' if include_key_findings and findings_html else ''}

    {sections_html}

    {questions_html}

    {charts_html}

    <div style="margin-top:32px;padding-top:16px;border-top:1px solid #e5e7eb;">
        {disclaimer_html}
        <p style="color:#9ca3af;font-size:11px;">Generated by {safe_brand_name} &bull; {datetime.utcnow().strftime('%B %d, %Y')}</p>
    </div>
</body>
</html>"""
        return html

    def render_pdf_summary(
        self,
        summary_data: dict,
        chart_images: Optional[dict[str, bytes]] = None,
        template_options: Optional[dict] = None,
    ) -> bytes:
        """
        Render a doctor summary as PDF using WeasyPrint.

        Args:
            summary_data: Summary data dict

        Returns:
            PDF bytes

        Raises:
            ImportError: If WeasyPrint is not installed
        """
        try:
            from weasyprint import HTML
        except ImportError:
            raise ImportError(
                "WeasyPrint is not installed. Install it with: pip install weasyprint\n"
                "System dependencies needed: libpango1.0-dev libgdk-pixbuf2.0-dev"
            )

        html_content = self.render_html_summary(
            summary_data,
            chart_images=chart_images,
            template_options=template_options,
        )
        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes

    def generate_questions(
        self,
        observations: list[dict],
        trends: list[dict],
    ) -> list[QuestionPrompt]:
        """
        Generate discussion prompts for clinician visits.
        
        Framed as discussion starters, not medical questions.
        """
        questions = []
        
        # Questions about abnormal values
        abnormal_obs = [o for o in observations if o.get("is_abnormal")]
        for obs in abnormal_obs[:3]:  # Limit to top 3
            questions.append(QuestionPrompt(
                category="abnormal",
                question=f"I noticed my {obs['analyte_canonical']} was outside the reference range. What might that indicate?",
                context=f"Value: {obs['value']} {obs.get('unit', '')}, flagged as {obs.get('flag', 'abnormal')}",
                related_analytes=[obs["analyte_canonical"]],
            ))
        
        # Questions about trends
        for trend in trends:
            if trend.get("trend_direction") in ["up", "down"]:
                questions.append(QuestionPrompt(
                    category="trend",
                    question=f"My {trend['analyte']} has been {trend['trend_direction']}. Should I be concerned?",
                    context=f"Changed {trend.get('delta_percent', 0):.1f}% from prior value",
                    related_analytes=[trend["analyte"]],
                ))
        
        return questions
