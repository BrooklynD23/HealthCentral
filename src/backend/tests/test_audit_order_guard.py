"""HC-AUD-ORD-030: route-class guard for AUDIT-ORDER.

Every handler in api/ from which a session `.commit()` is reachable (static,
name-based call graph, over-approximate on purpose) must be classified:
A2 = started/completed intent pair, C = audit after change, or excluded with
a reason. A new committing handler, or a new dynamic call the graph cannot
follow, fails until someone classifies it (recurring-failures #9).
"""

from __future__ import annotations

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
    "api/gamification.py::list_badges": "excluded: read route, audit_and_commit only",
    "api/gamification.py::get_streaks": "excluded: read route, audit_and_commit only",
    "api/interpretations.py::generate_interpretation": "A2",
    "api/interpretations.py::generate_grounded_interpretation": "A2",
    "api/interpretations.py::get_interpretation": "C",  # row 21: GET sets viewed_at in the vault
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
    "api/medications.py::delete_schedule": "A2",
    "api/medications.py::log_dose": "C",
    "api/medications.py::get_adherence_stats": "excluded: read route, audit_and_commit only",
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
    "api/model_settings.py::get_gamification_settings": "excluded: read route, audit_and_commit only",
    "api/model_settings.py::update_gamification_settings": "C",
    "api/model_settings.py::get_environment_diagnostics": "excluded: read route, audit_and_commit only",
    "api/model_settings.py::recheck_environment_diagnostics": "excluded: read route, audit_and_commit only",
    "api/model_settings.py::update_ocr_settings": "C",
    "api/model_settings.py::update_agent_settings": "C",
    "api/notifications.py::get_notification_settings": "excluded: read route, audit_and_commit only",
    "api/notifications.py::update_notification_settings": "C",
    "api/notifications.py::get_notification_history": "excluded: read route, audit_and_commit only",
    "api/notifications.py::send_test_medication_notification": "excluded: read route, audit_and_commit only",
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
    "api/assistant.py::_serve_via_agent::RunContext(_db_session_factory)":
        "hands the request's profile_db to the agent as a factory; see RunContext.db_session",
    "api/model_settings.py::_make_progress_tqdm._ProgressTqdm.update::_set_live_progress(key)":
        "in-memory progress dict update; no session",
    "api/model_settings.py::start_model_download::background_tasks.add_task(_download_model_task)":
        "background download task; settings write is part of start_model_download (C)",
    "api/observations.py::get_panel_snapshots::snapshots.sort(sort_snap)":
        "sort key function; no session",
    "core/migrations.py::run_profile_migration_async::asyncio.to_thread(run_profile_migration)":
        "alembic runner in a thread; own connection, schema only",
    "modules/platform_notifications.py::DesktopNotifierProvider.send::DeliveryResult(platform)":
        "dataclass field named like a def; no call",
    "modules/platform_notifications.py::MockProvider.send::DeliveryResult(platform)":
        "dataclass field named like a def; no call",
    "modules/platform_notifications.py::PlyerProvider.send::DeliveryResult(platform)":
        "dataclass field named like a def; no call",
    "modules/platform_notifications.py::WindowsToastProvider.send::DeliveryResult(platform)":
        "dataclass field named like a def; no call",
    "modules/recommend.py::RecommendationEngine._sort_recommendations::sorted(sort_key)":
        "sort key function; no session",
    "modules/redaction.py::RedactionEngine.redact::RedactionMetadataEntry(start)":
        "dataclass field named like a def; no call",
}



def _scan(g: Graph):
    hs = g.handlers()
    reach = {f"{h[0]}::{h[1]}": g.reachable(h) for h in hs}
    committing = {k for k, r in reach.items() if g.commits(r)}
    dyn = set()
    for r in reach.values():  # every handler, committing or not
        dyn |= g.dynamic_sites(r)
    return hs, reach, committing, dyn


_G = Graph()
_HANDLERS, _REACH, _COMMITTING, _DYN = _scan(_G)


def test_hc_aud_ord_030_every_committing_handler_is_classified():
    assert len(_HANDLERS) > 100, "handler discovery found too few routes"
    unclassified = sorted(_COMMITTING - set(CLASSIFICATION))
    stale = sorted(set(CLASSIFICATION) - _COMMITTING)
    assert not unclassified, f"unclassified committing handlers: {unclassified}"
    assert not stale, f"stale classification entries: {stale}"
    for k, v in CLASSIFICATION.items():
        assert v in {"A2", "C"} or v.startswith("excluded: "), (k, v)


def test_hc_aud_ord_030_a2_handlers_reach_audit_intent():
    """Presence only, not order (Codex diff review MINOR 1). That `started` is
    committed before the first mutation is pinned per route by the HTTP tests
    HC-AUD-ORD-001a in tests/test_audit_order.py, which fail if it moves after."""
    for k, v in CLASSIFICATION.items():
        if v == "A2":
            assert _G.reaches(_REACH[k], "audit_intent"), f"{k} is A2 but never calls audit_intent"


def test_hc_aud_ord_030_dynamic_calls_are_named():
    unlisted = sorted(_DYN - set(NAMED_DYNAMIC_EXCLUSIONS))
    stale = sorted(set(NAMED_DYNAMIC_EXCLUSIONS) - _DYN)
    assert not unlisted, f"unlisted dynamic call sites: {unlisted}"
    assert not stale, f"stale dynamic exclusions: {stale}"


def test_hc_aud_ord_030_vault_writes_rely_on_a_reachable_commit():
    """Section 12 item 7: a direct profile_db write with no commit on the vault
    session depends on the vault exit commit, which runs after the response."""
    bad = [f"{h[0]}::{h[1]}" for h in _HANDLERS if _G.unscoped_vault_writes(h)]
    assert not bad, f"handlers writing profile_db with no commit on it: {bad}"


# --- break-its: the guard must catch each of these in a synthetic tree ------


def _overlay(tmp_path, handler_src: str, helper_src: str | None = None):
    (tmp_path / "api").mkdir()
    (tmp_path / "modules").mkdir()
    (tmp_path / "api" / "zz.py").write_text(
        "from fastapi import APIRouter\nrouter = APIRouter()\n" + handler_src)
    if helper_src:
        (tmp_path / "modules" / "zz_helper.py").write_text(helper_src)
    return _scan(Graph(tmp_path, ("api", "core", "modules")))


def test_hc_aud_ord_030_break_it_new_committing_handler(tmp_path):
    _, _, committing, _ = _overlay(tmp_path, (
        '@router.post("/zz")\nasync def zz(profile_db=None):\n'
        "    profile_db.add(1)\n    await profile_db.commit()\n"))
    assert committing - set(CLASSIFICATION) == {"api/zz.py::zz"}


def test_hc_aud_ord_030_break_it_commit_through_new_module_helper(tmp_path):
    _, _, committing, _ = _overlay(
        tmp_path,
        '@router.post("/zz")\nasync def zz(db=None):\n    await zz_commit(db)\n',
        "async def zz_commit(db):\n    await db.commit()\n")
    assert committing - set(CLASSIFICATION) == {"api/zz.py::zz"}


def test_hc_aud_ord_030_break_it_injected_callable(tmp_path):
    _, _, _, dyn = _overlay(tmp_path, (
        '@router.post("/zz")\nasync def zz(cb=None):\n    await cb()\n'))
    assert dyn - set(NAMED_DYNAMIC_EXCLUSIONS) == {"api/zz.py::zz::cb"}


def test_hc_aud_ord_030_break_it_def_passed_as_argument(tmp_path):
    _, _, _, dyn = _overlay(tmp_path, (
        "def work():\n    pass\n"
        '@router.post("/zz")\nasync def zz(loop=None):\n    await loop.run_in_executor(None, work)\n'))
    assert dyn - set(NAMED_DYNAMIC_EXCLUSIONS) == {"api/zz.py::zz::loop.run_in_executor(work)"}


def test_hc_aud_ord_030_break_it_vault_write_without_commit(tmp_path):
    hs, *_ = _overlay(tmp_path, (
        '@router.post("/zz")\nasync def zz(profile_db=None):\n    profile_db.add(1)\n'))
    g = Graph(tmp_path, ("api",))
    assert [h[1] for h in g.handlers() if g.unscoped_vault_writes(h)] == ["zz"]


def test_hc_aud_ord_030_vault_commit_must_be_on_profile_db(tmp_path):
    """A master-db commit does not count for a vault write (CR-2)."""
    _overlay(tmp_path, (
        '@router.post("/zz")\nasync def zz(profile_db=None, master_db=None):\n'
        "    profile_db.add(1)\n    await master_db.commit()\n"))
    g = Graph(tmp_path, ("api",))
    assert [h[1] for h in g.handlers() if g.unscoped_vault_writes(h)] == ["zz"]
