"""
Export module.

Handles:
- Doctor-ready summary generation
- CSV/JSON data export
- Question list generation (HC-M17: multi-source, template-driven, no LLM)
- Visit-prep packet composition (HC-M18: redacted before it can leave)
"""

from typing import Optional
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import html
import json
import csv
from io import StringIO

from core.time import utcnow


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
    """A discussion prompt for clinician visits.

    HC-M17: every question carries provenance. Categories:
    "trend", "abnormal", "clarification", "follow_up",
    "medication_change", "test_ordered", "referral".
    """
    category: str
    question: str
    context: str
    related_analytes: list[str]
    # Provenance (HC-M17). Defaults keep pre-existing constructions valid.
    source_kind: str = "observation"  # observation | trend | care_task | entity
    source_id: Optional[str] = None
    source_quote: Optional[str] = None


# Open care tasks due within this many days count as "near due" (HC-M17).
NEAR_DUE_WINDOW_DAYS = 14


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
            findings_html += f'<li style="color:{color};margin-bottom:4px;">{html.escape(finding)}</li>'

        sections_html = ""
        for section in sections:
            title = html.escape(section.get("title", ""))
            content = html.escape(section.get("content", "")).replace("\n", "<br>")
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
                questions_html += f"<li style='margin-bottom:6px;'>{html.escape(q_text)}</li>"
            questions_html += "</ul></div>"

        html_doc = f"""<!DOCTYPE html>
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
        return html_doc

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
        care_tasks: Optional[list[dict]] = None,
        entities: Optional[list[dict]] = None,
        today: Optional[date] = None,
    ) -> list[QuestionPrompt]:
        """
        Generate discussion prompts for clinician visits (template-driven,
        no LLM). Framed as discussion starters, not medical advice — every
        question is interrogative and cites its source.

        New sources (HC-M17), all optional so existing callers keep working:
        - care_tasks: dicts with id, title, status, due_date, source_quote,
          source_entity_id. needs_review tasks ask for clarification; open
          tasks near/past due ask about scheduling.
        - entities: visit-note entity dicts with id, entity_type,
          entity_value, quote, verified_by_user. Only entities the user
          VERIFIED are used (unverified data is excluded — HC-M18 policy).
        """
        questions = []
        today = today or utcnow().date()

        # Questions about abnormal values
        abnormal_obs = [o for o in observations if o.get("is_abnormal")]
        for obs in abnormal_obs[:3]:  # Limit to top 3
            questions.append(QuestionPrompt(
                category="abnormal",
                question=f"I noticed my {obs['analyte_canonical']} was outside the reference range. What might that indicate?",
                context=f"Value: {obs['value']} {obs.get('unit', '')}, flagged as {obs.get('flag', 'abnormal')}",
                related_analytes=[obs["analyte_canonical"]],
                source_kind="observation",
                source_id=str(obs.get("id")) if obs.get("id") else None,
            ))

        # Questions about trends
        for trend in trends:
            if trend.get("trend_direction") in ["up", "down"]:
                questions.append(QuestionPrompt(
                    category="trend",
                    question=f"My {trend['analyte']} has been {trend['trend_direction']}. Should I be concerned?",
                    context=f"Changed {trend.get('delta_percent', 0):.1f}% from prior value",
                    related_analytes=[trend["analyte"]],
                    source_kind="trend",
                    source_id=trend["analyte"],
                ))

        # Questions from accepted care-plan tasks (HC-M17). Entity ids go
        # stale when a reprocess recreates the same extraction under a new
        # UUID, so dedupe also keys on the verbatim source quote.
        task_entity_ids = set()
        task_quotes = set()
        for task in care_tasks or []:
            if task.get("source_entity_id"):
                task_entity_ids.add(task["source_entity_id"])
            if task.get("source_quote"):
                task_quotes.add(task["source_quote"])
            status = task.get("status")
            quote = task.get("source_quote") or task.get("title", "")
            if status == "needs_review":
                questions.append(QuestionPrompt(
                    category="clarification",
                    question=f'The note says: "{quote}". Can you clarify when and with whom this should happen?',
                    context="This accepted follow-up item is marked needs review — no clear timing was found in the note.",
                    related_analytes=[],
                    source_kind="care_task",
                    source_id=task.get("id"),
                    source_quote=task.get("source_quote"),
                ))
            elif status == "open":
                due = task.get("due_date")
                if due is not None and due <= today + timedelta(days=NEAR_DUE_WINDOW_DAYS):
                    questions.append(QuestionPrompt(
                        category="follow_up",
                        question=f"This follow-up is still open: {task.get('title', '')}. Should it be scheduled?",
                        context=f"Open follow-up task due {due.isoformat()}.",
                        related_analytes=[],
                        source_kind="care_task",
                        source_id=task.get("id"),
                        source_quote=task.get("source_quote"),
                    ))

        # Questions from verified visit-note entities (HC-M17). Unverified
        # entities are excluded; entities already covered by an accepted care
        # task are skipped to avoid duplicate questions.
        for ent in entities or []:
            if ent.get("verified_by_user") is not True:
                continue
            if ent.get("id") in task_entity_ids:
                continue
            if ent.get("quote") and ent.get("quote") in task_quotes:
                continue
            entity_type = ent.get("entity_type")
            value = ent.get("entity_value", "")
            quote = ent.get("quote") or value
            if entity_type == "medication_change":
                question = f"Can you confirm this change to my medication list: {value}?"
                context = "Verified medication change found in a visit note."
            elif entity_type == "test_ordered":
                question = f"Can you explain why this test was ordered: {quote}?"
                context = "Verified test order found in a visit note."
            elif entity_type == "referral":
                question = f"Who should I schedule the {value} referral with, and how soon?"
                context = "Verified referral found in a visit note."
            else:
                continue
            questions.append(QuestionPrompt(
                category=entity_type,
                question=question,
                context=context,
                related_analytes=[],
                source_kind="entity",
                source_id=ent.get("id"),
                source_quote=ent.get("quote"),
            ))

        return questions

    def compose_visit_prep_packet(
        self,
        profile_id: str,
        reason_for_visit: Optional[str] = None,
        medications: Optional[list[dict]] = None,
        observations: Optional[list[dict]] = None,
        visit_mentions: Optional[list[dict]] = None,
        care_tasks: Optional[list[dict]] = None,
        questions: Optional[list[QuestionPrompt]] = None,
        selected_documents: Optional[list[dict]] = None,
        packet_title: str = "Visit Prep Packet",
        include_normal_observations: bool = False,
    ) -> dict:
        """Compose a visit-prep packet (HC-M18).

        Every section argument is optional: None means the user excluded the
        section; an empty list renders "None recorded." so the clinician can
        tell "excluded" from "empty".

        Unverified-data policy (applied everywhere): unverified observations
        and unverified entities are EXCLUDED. Care tasks exist only through
        explicit user acceptance, so they are user-verified by construction.

        Hard invariant: every piece of assembled content passes through
        modules/redaction.py (strict policy — matches the RL-dataset export,
        the strictest existing export path) BEFORE it is stored or rendered,
        so no downloadable format can carry unredacted text. Dates are
        rendered ISO-8601, which the strict numeric_date rule deliberately
        does not match.
        """
        import uuid
        from modules.redaction import RedactionEngine

        sections: list[dict] = []

        if reason_for_visit is not None and reason_for_visit.strip():
            sections.append({
                "title": "Reason for Visit",
                "content": reason_for_visit.strip(),
            })

        if medications is not None:
            lines = []
            for med in medications:
                dose = ""
                if med.get("dosage_amount") is not None:
                    amount = med["dosage_amount"]
                    amount_str = f"{amount:g}" if isinstance(amount, float) else str(amount)
                    dose = f" {amount_str} {med.get('dosage_unit') or ''}".rstrip()
                line = f"- {med.get('name', '')}{dose} — {med.get('frequency', '')}"
                if med.get("instructions"):
                    line += f" ({med['instructions']})"
                lines.append(line)
            sections.append({
                "title": "Current Medications",
                "content": "\n".join(lines) if lines else "None recorded.",
            })

        if observations is not None:
            verified_observations = [
                o for o in observations
                if o.get("user_verified")
                and (include_normal_observations or o.get("is_abnormal"))
            ]
            lines = []
            for obs in sorted(
                verified_observations,
                key=lambda x: x.get("collected_at") or datetime.min,
                reverse=True,
            ):
                collected = obs.get("collected_at")
                date_str = collected.date().isoformat() if collected else "no date"
                lines.append(
                    f"- {obs.get('analyte_canonical', '')}: {obs.get('value', '')} {obs.get('unit', '')} "
                    f"(ref {obs.get('ref_low', '?')}-{obs.get('ref_high', '?')}) "
                    f"[{obs.get('flag') or ('abnormal' if obs.get('is_abnormal') else 'normal')}] "
                    f"— {date_str}"
                )
            sections.append({
                "title": (
                    "Selected Lab Results (verified)"
                    if include_normal_observations
                    else "Recent Abnormal Lab Results (verified)"
                ),
                "content": "\n".join(lines) if lines else "None recorded.",
            })

        if visit_mentions is not None:
            lines = []
            for mention in visit_mentions:
                if mention.get("verified_by_user") is not True:
                    continue  # unverified data is excluded
                date_str = mention.get("doc_date") or "no date"
                label = str(mention.get("entity_type", "")).replace("_", " ")
                lines.append(f"- {date_str}: {label}: {mention.get('entity_value', '')}")
            sections.append({
                "title": "Recent Visits and Diagnoses (verified)",
                "content": "\n".join(lines) if lines else "None recorded.",
            })

        if care_tasks is not None:
            lines = []
            for task in care_tasks:
                due = task.get("due_date")
                due_str = due.isoformat() if due else "no due date"
                line = f"- [{task.get('status', '')}] {task.get('title', '')} (due: {due_str})"
                if task.get("source_quote"):
                    line += f' — note: "{task["source_quote"]}"'
                lines.append(line)
            sections.append({
                "title": "Open Follow-up Items",
                "content": "\n".join(lines) if lines else "None recorded.",
            })

        if questions is not None:
            lines = [f"- {q.question}" for q in questions]
            sections.append({
                "title": "Questions for Your Provider",
                "content": "\n".join(lines) if lines else "None recorded.",
            })

        if selected_documents is not None:
            lines = []
            for doc in selected_documents:
                collected = doc.get("collection_date")
                date_str = collected.date().isoformat() if collected else "no date"
                filename = str(doc.get("source") or "Document").replace("\\", "/").rsplit("/", 1)[-1]
                lines.append(f"- {filename} ({date_str})")
            sections.append({
                "title": "Source Documents",
                "content": "\n".join(lines) if lines else "None recorded.",
            })

        # Redaction before anything can leave (hard invariant). Strict policy:
        # matches or exceeds every existing export path.
        engine = RedactionEngine(policy_level="strict")
        redaction_count = 0
        for section in sections:
            result = engine.redact(section["content"])
            section["content"] = result.text
            redaction_count += result.redacted_count

        generated_at = utcnow()
        footer = (
            "Only user-verified data is included in this packet. "
            "This packet was generated by HealthCentral from your uploaded "
            "records. It is not medical advice — please review everything "
            "with your healthcare provider."
        )
        md_lines = [
            f"# {packet_title}",
            "",
            f"Generated: {generated_at.date().isoformat()}",
            "",
        ]
        for section in sections:
            md_lines.append(f"## {section['title']}")
            md_lines.append("")
            md_lines.append(section["content"])
            md_lines.append("")
        md_lines.append("---")
        md_lines.append(footer)

        return {
            "packet_id": str(uuid.uuid4()),
            "profile_id": profile_id,
            "generated_at": generated_at.isoformat(),
            "sections": sections,
            "questions": [
                {"question": q.question, "category": q.category}
                for q in (questions or [])
            ],
            "markdown": "\n".join(md_lines),
            "redaction_count": redaction_count,
            "packet_title": packet_title,
        }
