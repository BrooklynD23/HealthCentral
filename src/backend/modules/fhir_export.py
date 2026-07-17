"""FHIR R4 export mapping (HC-M22).

Pure, DB-free mapping from HealthCentral's internal per-profile records to a
FHIR R4 Bundle (``type: "collection"``). Export-only — there is no import or
write-back path. Callers (api/export.py) fetch rows via ``ProfileDbSession``
and pass plain dicts in; this module does no I/O and makes no network calls.

Hard invariants enforced here (do not weaken):
- Unverified-data policy: observations with ``user_verified is not True`` and
  document entities with ``verified_by_user is not True`` are excluded
  entirely, matching the HC-M18 "excluded everywhere" policy. Callers may
  pre-filter, but this module re-checks — it is the last choke point before
  data leaves the device.
- Redaction: every free-text string sourced from user or document narrative
  (display name, entity values, quotes, task titles, medication names/
  instructions, document metadata titles) is passed through
  ``modules.redaction.RedactionEngine(policy_level="strict")`` before it is
  placed in the bundle. Structured fields (ISO-8601 dates, numeric values,
  coded enums like status/frequency/analyte_canonical) are left as-is.
- No invented dates: a missing date/datetime is omitted from the resource
  entirely rather than defaulted to "now" or an empty string.
"""

import json
import uuid
from typing import Optional

from core.time import utcnow
from modules.redaction import RedactionEngine

# Tag placed on every resource's meta.source and on the bundle-level tag,
# identifying this as a local, on-device export (never a network fetch).
FHIR_SOURCE = "urn:healthcentral:local-export"

# care_plan_task.status -> FHIR CarePlan.activity.detail.status.
# "ignored" tasks are excluded before this map is consulted (see
# build_fhir_bundle), so it intentionally has no entry for them.
_TASK_STATUS_MAP = {
    "open": "in-progress",
    "done": "completed",
    "needs_review": "scheduled",
}

# Verified entity types that can support a DiagnosticReport conclusion.
_DIAGNOSTIC_ENTITY_TYPES = ("impression", "finding", "diagnosis")


class _Redactor:
    """Wraps ``RedactionEngine(policy_level="strict")`` and tallies hits.

    Call pattern mirrors modules/export.py's
    ``compose_visit_prep_packet`` (~lines 635-642): one engine instance,
    ``engine.redact(text)`` per string, accumulate ``redacted_count``.
    """

    def __init__(self) -> None:
        self._engine = RedactionEngine(policy_level="strict")
        self.count = 0

    def __call__(self, text: Optional[str]) -> Optional[str]:
        if not text:
            return text
        result = self._engine.redact(text)
        self.count += result.redacted_count
        return result.text


def _iso(value) -> Optional[str]:
    """ISO-8601 string for a date/datetime, or None. Never invents a date."""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _base_resource(resource_type: str, resource_id: str) -> dict:
    return {
        "resourceType": resource_type,
        "id": resource_id,
        "meta": {"source": FHIR_SOURCE},
    }


def _entry(resource: dict) -> dict:
    return {"fullUrl": f"urn:uuid:{resource['id']}", "resource": resource}


def _document_title(doc: dict) -> Optional[str]:
    """Extract an optional title from a document's metadata_json, if any."""
    raw = doc.get("metadata_json")
    if not raw:
        return None
    try:
        metadata = json.loads(raw)
    except (TypeError, ValueError):
        return None
    if isinstance(metadata, dict):
        title = metadata.get("title")
        if title:
            return str(title)
    return None


def build_patient(display_name: str, redact) -> dict:
    """Patient resource. No dedicated DB row exists, so a fresh id is used."""
    resource = _base_resource("Patient", str(uuid.uuid4()))
    resource["name"] = [{"text": redact(display_name or "")}]
    return resource


def build_observation(obs: dict, patient_ref: str, redact) -> dict:
    resource = _base_resource("Observation", obs["id"])
    resource["status"] = "final"
    # analyte_canonical is a controlled vocabulary term (no LOINC codes
    # exist in this data), not user narrative — left unredacted, text-only.
    resource["code"] = {"text": obs.get("analyte_canonical")}
    resource["subject"] = {"reference": patient_ref}

    value = obs.get("value")
    value_text = obs.get("value_text")
    if value is not None:
        quantity: dict = {"value": value}
        if obs.get("unit"):
            quantity["unit"] = obs["unit"]
        resource["valueQuantity"] = quantity
    elif value_text:
        resource["valueString"] = redact(value_text)

    ref_range: dict = {}
    if obs.get("ref_low") is not None:
        ref_range["low"] = {"value": obs["ref_low"]}
    if obs.get("ref_high") is not None:
        ref_range["high"] = {"value": obs["ref_high"]}
    if obs.get("ref_range_text"):
        ref_range["text"] = redact(obs["ref_range_text"])
    if ref_range:
        resource["referenceRange"] = [ref_range]

    if obs.get("flag"):
        # Short coded flag (H/L/critical/...), not narrative — unredacted.
        resource["interpretation"] = [{"text": obs["flag"]}]

    effective = _iso(obs.get("collected_at"))
    if effective:
        resource["effectiveDateTime"] = effective

    return resource


def build_medication_statement(med: dict, patient_ref: str, redact) -> dict:
    resource = _base_resource("MedicationStatement", med["id"])
    resource["status"] = "active" if med.get("is_active") else "completed"
    resource["subject"] = {"reference": patient_ref}

    med_concept: dict = {"text": redact(med.get("name") or "")}
    if med.get("generic_name"):
        med_concept["coding"] = [{"display": redact(med["generic_name"])}]
    resource["medicationCodeableConcept"] = med_concept

    parts: list[str] = []
    amount, unit, form, frequency = (
        med.get("dosage_amount"),
        med.get("dosage_unit"),
        med.get("dosage_form"),
        med.get("frequency"),
    )
    if amount is not None:
        parts.append(f"{amount}{(' ' + unit) if unit else ''}")
    if form:
        parts.append(str(form))
    if frequency:
        parts.append(str(frequency).replace("_", " "))
    instructions = redact(med.get("instructions"))
    if instructions:
        parts.append(instructions)
    if parts:
        resource["dosage"] = [{"text": " ".join(parts)}]

    started = _iso(med.get("started_at"))
    ended = _iso(med.get("ended_at"))
    if started or ended:
        period: dict = {}
        if started:
            period["start"] = started
        if ended:
            period["end"] = ended
        resource["effectivePeriod"] = period

    return resource


def build_condition(entity: dict, patient_ref: str, redact) -> dict:
    """Condition from a verified 'diagnosis' document entity.

    Framed as an unconfirmed document mention, never a clinical diagnosis
    (safety requirement — this is a record of what a document said, not a
    medical determination).
    """
    resource = _base_resource("Condition", entity["id"])
    resource["subject"] = {"reference": patient_ref}
    resource["verificationStatus"] = {
        "coding": [
            {
                "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                "code": "unconfirmed",
            }
        ],
        "text": "unconfirmed",
    }
    resource["code"] = {"text": redact(entity.get("entity_value") or "")}
    quote = redact(entity.get("quote"))
    if quote:
        resource["note"] = [{"text": quote}]
        resource["evidence"] = [{"detail": [{"display": quote}]}]
    return resource


def build_document_reference(doc: dict, patient_ref: str, redact) -> dict:
    resource = _base_resource("DocumentReference", doc["id"])
    resource["status"] = "current"
    resource["subject"] = {"reference": patient_ref}
    if doc.get("category"):
        # Category label (lab/imaging/pathology/visit_notes) — coded, not
        # narrative — left unredacted.
        resource["type"] = {"text": doc["category"]}
    date = _iso(doc.get("collection_date") or doc.get("imported_at"))
    if date:
        resource["date"] = date
    title = _document_title(doc)
    if title:
        resource["description"] = redact(title)
    return resource


def build_encounter(
    doc: dict, visit_type_value: Optional[str], patient_ref: str, redact
) -> dict:
    """Encounter for a visit_notes document. No dedicated row — fresh id."""
    resource = _base_resource("Encounter", str(uuid.uuid4()))
    resource["status"] = "finished"
    resource["subject"] = {"reference": patient_ref}
    if visit_type_value:
        resource["class"] = {"text": redact(visit_type_value)}
    date = _iso(doc.get("collection_date"))
    if date:
        resource["period"] = {"start": date}
    return resource


def build_care_plan(tasks: list[dict], patient_ref: str, redact) -> Optional[dict]:
    """One CarePlan with an activity per open/needs_review/done task.

    Care-plan tasks are user-accepted by construction (HC-M15) — no
    verification filter is needed. "ignored" tasks are excluded from the
    activity list entirely, per the milestone's status-mapping rule.
    """
    included = [t for t in tasks if t.get("status") != "ignored"]
    if not included:
        return None

    resource = _base_resource("CarePlan", str(uuid.uuid4()))
    resource["status"] = "active"
    resource["intent"] = "plan"
    resource["subject"] = {"reference": patient_ref}

    activities = []
    for task in included:
        detail: dict = {
            "status": _TASK_STATUS_MAP.get(task.get("status"), "unknown"),
            "description": redact(task.get("title") or ""),
        }
        due = _iso(task.get("due_date"))
        if due:
            detail["scheduledString"] = due
        activity: dict = {"detail": detail}
        quote = redact(task.get("source_quote"))
        if quote:
            activity["progress"] = [{"text": quote}]
        activities.append(activity)

    resource["activity"] = activities
    return resource


def build_diagnostic_report(
    doc: dict, entity_values: list[str], patient_ref: str, redact
) -> Optional[dict]:
    """DiagnosticReport for an imaging/pathology doc with verified findings.

    No dedicated row — fresh id. Result-less (references the source
    document via subject/category only; lab data lives in Observation).
    """
    redacted_values = [redact(v) for v in entity_values if v]
    redacted_values = [v for v in redacted_values if v]
    if not redacted_values:
        return None

    resource = _base_resource("DiagnosticReport", str(uuid.uuid4()))
    resource["status"] = "final"
    resource["subject"] = {"reference": patient_ref}
    resource["code"] = {"text": doc.get("category") or ""}
    date = _iso(doc.get("collection_date"))
    if date:
        resource["effectiveDateTime"] = date
    resource["conclusion"] = " ".join(redacted_values)
    return resource


def _count_by_type(resources: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for resource in resources:
        counts[resource["resourceType"]] = counts.get(resource["resourceType"], 0) + 1
    return counts


def build_fhir_bundle(
    profile_display_name: str,
    observations: list[dict],
    medications: list[dict],
    documents: list[dict],
    entities: list[dict],
    care_tasks: list[dict],
    *,
    include_observations: bool = True,
    include_medications: bool = True,
    include_conditions: bool = True,
    include_documents: bool = True,
    include_encounters: bool = True,
    include_care_plan: bool = True,
    include_reports: bool = True,
) -> dict:
    """Build a FHIR R4 Bundle (type "collection") from per-profile records.

    Returns ``{"bundle": <dict>, "redaction_count": int,
    "resource_counts": {resourceType: count}}``. Pure function — no DB
    access, no network calls. Unverified observations (``user_verified is
    not True``) and unverified/rejected entities (``verified_by_user is not
    True``) are excluded regardless of the include_* flags, which only
    toggle whole resource *types* on/off.
    """
    redact = _Redactor()
    resources: list[dict] = []

    patient = build_patient(profile_display_name, redact)
    patient_ref = f"Patient/{patient['id']}"
    resources.append(patient)

    entities_by_doc: dict[str, list[dict]] = {}
    for ent in entities or []:
        entities_by_doc.setdefault(ent.get("doc_id"), []).append(ent)

    if include_observations:
        for obs in observations or []:
            if obs.get("user_verified") is not True:
                continue
            resources.append(build_observation(obs, patient_ref, redact))

    if include_medications:
        for med in medications or []:
            resources.append(build_medication_statement(med, patient_ref, redact))

    if include_conditions:
        for ent in entities or []:
            if ent.get("entity_type") != "diagnosis":
                continue
            if ent.get("verified_by_user") is not True:
                continue
            resources.append(build_condition(ent, patient_ref, redact))

    if include_documents:
        for doc in documents or []:
            resources.append(build_document_reference(doc, patient_ref, redact))

    if include_encounters:
        for doc in documents or []:
            if doc.get("category") != "visit_notes":
                continue
            visit_type_value = next(
                (
                    ent.get("entity_value")
                    for ent in entities_by_doc.get(doc["id"], [])
                    if ent.get("entity_type") == "visit_type"
                    and ent.get("verified_by_user") is True
                ),
                None,
            )
            resources.append(build_encounter(doc, visit_type_value, patient_ref, redact))

    if include_care_plan:
        plan = build_care_plan(care_tasks or [], patient_ref, redact)
        if plan:
            resources.append(plan)

    if include_reports:
        for doc in documents or []:
            if doc.get("category") not in ("imaging", "pathology"):
                continue
            values = [
                ent.get("entity_value")
                for ent in entities_by_doc.get(doc["id"], [])
                if ent.get("entity_type") in _DIAGNOSTIC_ENTITY_TYPES
                and ent.get("verified_by_user") is True
            ]
            report = build_diagnostic_report(doc, values, patient_ref, redact)
            if report:
                resources.append(report)

    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "timestamp": utcnow().isoformat() + "Z",
        "meta": {
            "tag": [
                {
                    "system": FHIR_SOURCE,
                    "code": "user-verified-only",
                    "display": "user-verified data only",
                }
            ]
        },
        "entry": [_entry(r) for r in resources],
    }

    return {
        "bundle": bundle,
        "redaction_count": redact.count,
        "resource_counts": _count_by_type(resources),
    }
