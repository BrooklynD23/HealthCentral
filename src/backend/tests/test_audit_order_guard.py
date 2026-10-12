"""HC-AUD-ORD-030: route-class guard for AUDIT-ORDER.

Every handler in api/ from which a session `.commit()` is reachable (static,
name-based call graph, over-approximate on purpose) must be classified:
A2 = started/completed intent pair, C = audit after change, or excluded with
a reason. A new committing handler, or a new dynamic call the graph cannot
follow, fails until someone classifies it (recurring-failures #9).
"""

from __future__ import annotations

import pytest

from tests.support.callgraph import Graph

CLASSIFICATION: dict[str, str] = {
    "api/assistant.py::create_session": "C",
    "api/assistant.py::delete_session": "C",
    "api/assistant.py::update_memory_settings": "C",
    "api/assistant.py::chat": "C",
    "api/backup.py::list_backups": "excluded: read route, audit_and_commit only",
    "api/backup.py::create_backup": "excluded: writes backup files, master audit row only; no vault mutation",
    "api/backup.py::verify_backup": "excluded: read route, audit_and_commit only",
    "api/backup.py::download_backup": "excluded: read route, audit_and_commit only",
    "api/backup.py::restore_backup": "A2",
    "api/backup.py::prune_backups": "excluded: deletes backup files only; no vault mutation",
    "api/backup.py::get_schedule": "excluded: read route, audit_and_commit only",
    "api/backup.py::set_schedule": "excluded: master-only backup schedule row",
    "api/care_tasks.py::list_care_tasks": "excluded: read route, audit_and_commit only",
    "api/care_tasks.py::get_care_task_candidates": "excluded: read route, audit_and_commit only",
    "api/care_tasks.py::accept_care_task": "C",
    "api/care_tasks.py::update_care_task": "C",
    "api/documents.py::import_document": "C",
    "api/documents.py::list_documents": "excluded: read route, audit_and_commit only",
    "api/documents.py::get_document": "excluded: read route, audit_and_commit only",
    "api/documents.py::reprocess_document": "A2",
    "api/documents.py::verify_document": "C",
    "api/documents.py::get_document_category": "excluded: read route, audit_and_commit only",
    "api/documents.py::get_document_entities": "excluded: read route, audit_and_commit only",
    "api/documents.py::set_entity_verification": "C",
    "api/documents.py::get_highlights_summary": "excluded: read route, audit_and_commit only",
    "api/documents.py::get_document_highlights": "excluded: read route, audit_and_commit only",
    "api/documents.py::get_document_pages": "excluded: read route, audit_and_commit only",
    "api/documents.py::get_page_image": "excluded: read route, audit_and_commit only",
    "api/documents.py::delete_document": "A2",
    "api/export.py::generate_doctor_summary": "excluded: read route, audit_and_commit only",
    "api/export.py::download_summary": "excluded: read route, audit_and_commit only",
    "api/export.py::generate_questions": "excluded: read route, audit_and_commit only",
    "api/export.py::generate_visit_prep": "excluded: read route, audit_and_commit only",
    "api/export.py::download_visit_prep": "excluded: read route, audit_and_commit only",
    "api/export.py::export_csv": "excluded: read route, audit_and_commit only",
    "api/export.py::export_json": "excluded: read route, audit_and_commit only",
    "api/export.py::generate_fhir_export": "excluded: read route, audit_and_commit only",
    "api/export.py::download_fhir_export": "excluded: read route, audit_and_commit only",
    "api/feedback.py::upsert_feedback": "C",
    "api/feedback.py::export_dataset": "excluded: writes export files; master audit only",
    "api/interpretations.py::generate_interpretation": "A2",
    "api/interpretations.py::generate_grounded_interpretation": "A2",
    "api/interpretations.py::get_interpretation": "excluded: read route, audit_and_commit only",
    "api/interpretations.py::generate_panel_interpretation": "C",
    "api/interpretations.py::get_recent_interpretations": "excluded: read route, audit_and_commit only",
    "api/interpretations.py::batch_generate_interpretations": "A2",
    "api/med_reconcile.py::get_med_reconciliation": "excluded: read route, audit_and_commit only",
    "api/medications.py::create_medication": "C",
    "api/medications.py::get_medication_correlations": "excluded: read route, audit_and_commit only",
    "api/medications.py::update_medication": "C",
    "api/medications.py::delete_medication": "A2",
    "api/medications.py::create_schedule": "C",
    "api/medications.py::update_schedule": "C",
    "api/medications.py::delete_schedule": "C",
    "api/medications.py::log_dose": "C",
    "api/medications.py::learn_patterns": "C",
    "api/memory.py::create_memory_item": "C",
    "api/memory.py::list_memory_items": "excluded: read route, audit_and_commit only",
    "api/memory.py::get_memory_item": "excluded: read route, audit_and_commit only",
    "api/memory.py::update_memory_item": "C",
    "api/memory.py::delete_memory_item": "A2",
    "api/model_settings.py::get_model_settings": "excluded: read route, audit_and_commit only",
    "api/model_settings.py::run_hardware_detection": "C",
    "api/model_settings.py::set_model_tier": "C",
    "api/model_settings.py::list_tiers": "excluded: read route, audit_and_commit only",
    "api/model_settings.py::start_model_download": "C",
    "api/model_settings.py::save_external_api_settings": "C",
    "api/model_settings.py::set_timezone": "C",
    "api/model_settings.py::update_voice_settings": "C",
    "api/model_settings.py::get_environment_diagnostics": "excluded: read route, audit_and_commit only",
    "api/model_settings.py::recheck_environment_diagnostics": "excluded: read route, audit_and_commit only",
    "api/model_settings.py::update_ocr_settings": "C",
    "api/model_settings.py::update_agent_settings": "C",
    "api/notifications.py::update_notification_settings": "C",
    "api/notifications.py::record_reminder_interaction": "C",
    "api/observations.py::get_panel_snapshots": "excluded: read route, audit_and_commit only",
    "api/observations.py::list_observations": "excluded: read route, audit_and_commit only",
    "api/observations.py::get_observation": "excluded: read route, audit_and_commit only",
    "api/observations.py::verify_observation": "C",
    "api/observations.py::get_analyte_trend": "excluded: read route, audit_and_commit only",
    "api/observations.py::get_panel": "excluded: read route, audit_and_commit only",
    "api/pinboards.py::create_pinboard": "C",
    "api/pinboards.py::list_pinboards": "excluded: read route, audit_and_commit only",
    "api/pinboards.py::rename_pinboard": "C",
    "api/pinboards.py::delete_pinboard": "A2",
    "api/pinboards.py::add_pinboard_item": "C",
    "api/pinboards.py::list_pinboard_items": "A2",
    "api/pinboards.py::remove_pinboard_item": "C",
    "api/pinboards.py::export_pinboard_packet": "A2",
    "api/profiles.py::create_profile": "excluded: master-only profile row creation",
    "api/profiles.py::login": "excluded: master-only auth",
    "api/profiles.py::logout": "excluded: master-only auth",
    "api/profiles.py::reset_synthetic_test_profile": "excluded: test-only reset (3.1)",
    "api/profiles.py::issue_recovery_code": "excluded: master-only credential row",
    "api/profiles.py::recover_profile": "excluded: master-only credential row",
    "api/profiles.py::delete_profile": "A2",
    "api/profiles.py::lock_profile": "excluded: master-only lock flag",
    "api/profiles.py::unlock_profile": "excluded: master-only lock flag",
    "api/profiles.py::change_password": "excluded: master-only credential row",
    "api/search.py::get_search_results": "excluded: read route, audit_and_commit only",
    "api/timeline.py::get_timeline": "excluded: read route, audit_and_commit only",
}

# Calls the static graph cannot resolve (injected callables, class locals,
# subscripted tables). Key: relpath::qualname::call expression.
NAMED_DYNAMIC_EXCLUSIONS: dict[str, str] = {
    "core/audit.py::audit_and_commit::log_fn":
        "injected log_*_event; every caller passes a create_audit_log wrapper",
    "core/audit.py::create_audit_log::AuditLog":
        "local alias of the AuditLog model class (lazy import), a constructor",
    "api/documents.py::_classify_and_extract_entities::extractor":
        "extractor selected by doc type; no commit inside, vault commit is in the caller",
    "modules/agent/graph.py::RunContext.db_session::self.db_session_factory":
        "assistant.py:_db_session_factory yields the request's profile_db; "
        "the chat route commits explicitly (row 28, HC-AUD-ORD-060)",
    "modules/agent/nodes/plan.py::plan::planner":
        "injected planner callable; pure LLM planning, no session",
    "modules/backup_scheduler.py::_is_profile_unlocked::checker":
        "injected unlock predicate; read-only",
    "core/llm/llama_cpp_provider.py::LlamaCppProvider._ensure_initialized::Llama":
        "llama_cpp model constructor; no session",
    "modules/platform_notifications.py::WindowsToastProvider.send::self._toast_module['notification']":
        "OS toast API; no session",
    "modules/platform_notifications.py::WindowsToastProvider.send::self._toast_module['xml']":
        "OS toast API; no session",
}

_G = Graph()
_HANDLERS = _G.handlers()
_REACH = {f"{h[0]}::{h[1]}": _G.reachable(h) for h in _HANDLERS}
_COMMITTING = {k for k, r in _REACH.items() if _G.commits(r)}


def test_hc_aud_ord_030_every_committing_handler_is_classified():
    assert len(_HANDLERS) > 100, "handler discovery found too few routes"
    unclassified = sorted(_COMMITTING - set(CLASSIFICATION))
    stale = sorted(set(CLASSIFICATION) - _COMMITTING)
    assert not unclassified, f"unclassified committing handlers: {unclassified}"
    assert not stale, f"stale classification entries: {stale}"
    for k, v in CLASSIFICATION.items():
        assert v in {"A2", "C"} or v.startswith("excluded: "), (k, v)


def test_hc_aud_ord_030_a2_handlers_reach_audit_intent():
    for k, v in CLASSIFICATION.items():
        if v == "A2":
            assert _G.reaches(_REACH[k], "audit_intent"), f"{k} is A2 but never calls audit_intent"


def test_hc_aud_ord_030_dynamic_calls_are_named():
    found = set()
    for k in _COMMITTING:
        found |= _G.dynamic_sites(_REACH[k])
    unlisted = sorted(found - set(NAMED_DYNAMIC_EXCLUSIONS))
    stale = sorted(set(NAMED_DYNAMIC_EXCLUSIONS) - found)
    assert not unlisted, f"unlisted dynamic call sites: {unlisted}"
    assert not stale, f"stale dynamic exclusions: {stale}"


def test_hc_aud_ord_030_vault_writes_rely_on_a_reachable_commit():
    """Section 12 item 7: a direct profile_db write with no reachable commit
    depends on the vault exit commit, which runs after the response."""
    bad = [f"{h[0]}::{h[1]}" for h in _HANDLERS if _G.unscoped_vault_writes(h)]
    assert not bad, f"handlers writing profile_db with no reachable commit: {bad}"
