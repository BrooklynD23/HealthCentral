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
from io import StringIO


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
                date_str,
                obs.get("analyte_canonical", ""),
                obs.get("value", ""),
                obs.get("unit", ""),
                obs.get("ref_low", ""),
                obs.get("ref_high", ""),
                obs.get("flag", ""),
                "Yes" if obs.get("user_verified") else "No",
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
    
    def render_html_summary(self, summary_data: dict) -> str:
        """
        Render a doctor summary as an inline-CSS HTML document.

        Args:
            summary_data: Summary data dict with sections, key_findings, etc.

        Returns:
            HTML string suitable for email/print
        """
        date_range = summary_data.get("date_range", "")
        key_findings = summary_data.get("key_findings", [])
        sections = summary_data.get("sections", [])
        questions = summary_data.get("questions", [])

        findings_html = ""
        for finding in key_findings:
            # Color-code by severity
            color = "#b91c1c" if "critical" in finding.lower() else "#d97706" if any(
                f in finding.lower() for f in ["high", "low", "abnormal"]
            ) else "#374151"
            findings_html += f'<li style="color:{color};margin-bottom:4px;">{finding}</li>'

        sections_html = ""
        for section in sections:
            title = section.get("title", "")
            content = section.get("content", "").replace("\n", "<br>")
            sections_html += f"""
            <div style="margin-bottom:20px;">
                <h3 style="color:#1f2937;font-size:16px;margin-bottom:8px;border-bottom:1px solid #e5e7eb;padding-bottom:4px;">{title}</h3>
                <p style="color:#4b5563;font-size:14px;line-height:1.6;">{content}</p>
            </div>"""

        questions_html = ""
        if questions:
            questions_html = '<div style="margin-top:20px;"><h3 style="color:#1f2937;font-size:16px;margin-bottom:8px;">Questions for Your Provider</h3><ul style="color:#4b5563;font-size:14px;">'
            for q in questions:
                q_text = q.get("question", q) if isinstance(q, dict) else q
                questions_html += f"<li style='margin-bottom:6px;'>{q_text}</li>"
            questions_html += "</ul></div>"

        html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>HealthCentral Summary</title></head>
<body style="font-family:'Source Sans 3',Arial,sans-serif;max-width:800px;margin:0 auto;padding:24px;background:#fff;">
    <div style="background:#2D7D6F;color:white;padding:20px 24px;border-radius:12px;margin-bottom:24px;">
        <h1 style="margin:0;font-family:'Fraunces',Georgia,serif;font-size:24px;">HealthCentral</h1>
        <p style="margin:4px 0 0;font-size:14px;opacity:0.9;">Lab Results Summary</p>
        {f'<p style="margin:4px 0 0;font-size:13px;opacity:0.8;">{date_range}</p>' if date_range else ''}
    </div>

    {f'<div style="margin-bottom:20px;"><h2 style="color:#1f2937;font-size:18px;">Key Findings</h2><ul style="padding-left:20px;">{findings_html}</ul></div>' if findings_html else ''}

    {sections_html}

    {questions_html}

    <div style="margin-top:32px;padding-top:16px;border-top:1px solid #e5e7eb;">
        <p style="color:#9ca3af;font-size:12px;font-style:italic;">
            This is an AI-assisted summary of your lab results. It is not medical advice.
            Please discuss all findings with your healthcare provider.
        </p>
        <p style="color:#9ca3af;font-size:11px;">Generated by HealthCentral &bull; {datetime.utcnow().strftime('%B %d, %Y')}</p>
    </div>
</body>
</html>"""
        return html

    def render_pdf_summary(self, summary_data: dict) -> bytes:
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

        html_content = self.render_html_summary(summary_data)
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
