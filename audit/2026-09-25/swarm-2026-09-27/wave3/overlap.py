import itertools
SL={'CLAUDE.md#count','AGENT.md#count'}
F={
'S-1':{'core/config.py','core/database.py','core/profile_database.py','config/.env.example','tests/security/test_sql_echo_phi.py','plans/S01'}|SL,
'P2':{'main.py','core/auth.py','modules/notification_scheduler.py','api/notifications.py','tests/test_notification_scheduler_wiring.py','docs/architecture/README.md','docs/features/00_features_index.md','docs/features/TASK_LIST.md'}|SL,
'W-1':{'.claude/agents/*','.gitignore','tests/test_claude_agent_definitions.py','docs/agentic/harness.md','docs/agentic/roadmap.md','CS4610_Report_Demo/README.md','capstone/claims-ledger.md','capstone/matrix?','capstone/contract?','plans/W01'}|SL,
'P4-core':{'docs/agentic/evals.md','README.md','docs/features/00_features_index.md','docs/features/TASK_LIST.md','docs/compliance/security-review-sprint06.md','docs/user/faq.md','CONTRIBUTING.md','skills/asclexis-agent/SKILL.md','skills/asclexis-evals/SKILL.md','AGENT.md#rows','.serena/memories/*','docs/00_architecture_plans_index.md','docs/architecture/pipelines.md','docs/architecture/README.md','docs/architecture/backend.md','docs/architecture/ci-and-quality-gates.md','core/config.py','docs/INDEX.md','plans/P04','config/.env.example?','api/__init__.py?','modules/agent/__init__.py?','scripts/download_models.py(root)?'},
'W-10':{'CLAUDE.md#invariants','docs/compliance/data-privacy.md'},
'W-10b':{'docs/compliance/data-privacy.md'},
'P5':{'models/*(14)','models/document_category.py','api/documents.py','api/observations.py','api/interpretations.py','api/notifications.py','api/profiles.py','api/model_settings.py','modules/notification_scheduler.py','modules/adherence_patterns.py','modules/platform_notifications.py','modules/agent/*','modules/export.py','modules/ingest.py','modules/rl_dataset.py','modules/hardware_detection.py','modules/model_selector.py','tests/test_time_source.py','tests/test_documents_api.py','tests/test_export_api.py','tests/agent/*','scripts/time_source_lint.py','.github/workflows/ci.yml','docs/features/TASK_LIST.md'},
'P6':{'core/fk_audit.py','scripts/fk_orphan_audit.py','tests/test_fk_audit.py','migrations/profile/013','models/document_category.py','models/care_plan_task.py','core/database.py','core/profile_database.py','tests/support/db.py','tests/test_fk_enforcement.py','tests/test_care_tasks.py(undeclared)','docs/features/TASK_LIST.md'},
'P7':{'tests/support/routes.py','tests/test_profile_test_reset.py','api/profiles.py','docs/features/TASK_LIST.md'},
'P8':{'audit/gated-items-decision-packet.md','docs/features/TASK_LIST.md'},
'W-2':{'tests/test_export_redaction.py','modules/export.py','api/export.py','plans/W02'}|SL,
'W-3':{'tests/test_verified_only_consumers.py','fe/TrendVerificationMarkers.tsx','fe/__tests__/TrendVerificationMarkers.test.tsx','fe/__tests__/InterpretedTrendChart.test.tsx','api/observations.py','modules/rag.py','fe/services/types.ts','fe/TrendsDashboard.tsx','fe/InterpretedTrendChart.tsx','fe/__tests__/TrendsDashboard.test.tsx','api/assistant.py?'}|SL,
'W-4':{'tests/legacy_eval/*','tests/test_legacy_abstain.py','scripts/legacy_eval_gate.py','api/assistant.py','.github/workflows/ci.yml','docs/agentic/evals.md','capstone/matrix','capstone/contract','docs/INDEX.md'}|SL,
'W-5':{'modules/rag.py','tests/test_rag_citation_prompt.py','docs/features/01_lab_result_interpreter_architecture.md','docs/compliance/ai-safety.md','docs/user/faq.md','docs/user/workflows.md','plans/W05'}|SL,
'W-6':{'core/external_runner.py','tests/test_external_runner_hardening.py','tests/test_redaction.py','api/model_settings.py','fe/ExternalApiBreakGlassWarning.tsx','fe/__tests__/ExternalApiBreakGlassWarning.test.tsx','fe/services/modelSettings.ts','fe/pages/SettingsPage.tsx'},
'W-7':{'modules/interpret.py','modules/model_selector.py','api/interpretations.py','tests/test_llm_import_boundary.py','tests/test_interpret_tiered.py'}|SL,
'W-8':{'modules/embeddings.py','core/config.py','.gitignore','config/.env.example','backend/scripts/download_models.py','.github/workflows/ci.yml','modules/rag.py','api/documents.py','tests/test_embedding_bundle.py','tests/test_embedding_fail_closed_paths.py','AGENT.md#rows','CLAUDE.md#passcount','capstone/contract','capstone/matrix','capstone/overview','capstone/claims-ledger.md','docs/architecture/ci-and-quality-gates.md','docs/architecture/performance-scalability-review.md'}|SL,
'W-11a/PR-1':{'tests/support/master_db.py','tests/support/routes.py','tests/test_profile_route_guards.py','tests/test_profile_route_audit.py','api/profiles.py','capstone/matrix','capstone/contract','docs/features/TASK_LIST.md'}|SL,
'W-11a/PR-2':{'tests/security/test_vault_ciphertext.py','capstone/matrix','capstone/contract','docs/features/TASK_LIST.md'}|SL,
'W-11a/PR-3':{'tests/test_migration_heads.py','.github/workflows/ci.yml','capstone/matrix','capstone/contract','docs/architecture/ci-and-quality-gates.md','docs/features/TASK_LIST.md'}|SL,
'W-11a/PR-4':{'capstone/matrix','capstone/claims-ledger.md','capstone/overview','docs/features/TASK_LIST.md','audit/repository-audit-dashboard.html'},
'G-C1':{'tests/test_export_artifact_persistence.py','models/export_artifact.py','models/__init__.py','migrations/profile/014','api/profiles.py','tests/test_care_tasks.py(undeclared)','api/export.py','api/pinboards.py','tests/test_visit_prep_packet.py','tests/test_fhir_export.py','plans/W11b'}|SL,
'G-C2':{'openwiki/**','docs/00_architecture_plans_index.md','AGENT.md#rows','docs/INDEX.md'},
'G-C3a':{'tests/support/minimal_pdf.py','tests/fixtures/extraction_golden/*','tests/test_extraction_golden.py','docs/agentic/eval-cards/extraction.md','docs/agentic/evals.md','docs/INDEX.md'}|SL,
'G-C3b':{'core/logging_setup.py','main.py','security/audit_middleware.py','tests/monitoring/test_correlation.py','tests/security/test_audit_middleware.py','fe/e2e/health-smoke.spec.ts'}|SL,
'G-C4':{'plans/<date>-packaging-decision.md','docs/INDEX.md','feature_list.json'},
'N8':{'docs/architecture/pipelines.md','docs/features/00_features_index.md','docs/features/04_self_improvement_loop.md','docs/features/TASK_LIST.md'},
'N9':{'docs/compliance/hipaa-controls.md'},
'N10':{'skills/asclexis-guardrails/SKILL.md'},
'F1-F6':{'docs/architecture/pipelines.md','docs/architecture/README.md','docs/architecture/backend.md','docs/architecture/ci-and-quality-gates.md'},
}
def norm(s): return s.rstrip('?').replace('(undeclared)','')
import collections
by=collections.defaultdict(list)
for k,v in F.items():
    for f in v: by[norm(f)].append(k)
print("## shared files (>=2 phases)")
for f in sorted(by, key=lambda x:(-len(by[x]),x)):
    if len(by[f])>1: print(f"{f}: {', '.join(by[f])}")
print("\n## disjoint check excluding count slots")
keys=list(F)
def fs(k,slots): return {norm(x) for x in F[k] if slots or x not in SL}
for a,b in itertools.combinations(keys,2):
    pass
# candidate parallel sets
for grp in [['S-1','W-6','G-C4','P8'],['P2','W-6','G-C4','W-11a/PR-2'],['W-1','W-6','G-C4','P8','W-5'],['W-10','P5'],['P6','W-4','W-2'],['P6','W-4','W-7'],['P7','W-3'],['W-2','W-4','W-7'],['W-11a/PR-1','W-3','G-C3a']]:
    for slots in (True,False):
        bad=[(a,b,sorted(fs(a,slots)&fs(b,slots))) for a,b in itertools.combinations(grp,2) if fs(a,slots)&fs(b,slots)]
        print(grp,'slots' if slots else 'no-slots', 'OK' if not bad else bad)
print("\n## proposed groups")
F['W-6']=F['W-6']|SL  # after BLOCKER fix
F['P5']=F['P5']|SL; F['P6']=F['P6']|SL; F['P7']=F['P7']|SL
for grp in [['S-1','W-6','G-C4','P8'],['P2','W-6','G-C4'],['W-1','W-6','G-C4','P8'],['W-5','W-6','G-C4','P8'],['W-11a/PR-2','W-6','G-C4'],['W-10','P5'],['P6','W-4'],['P6','W-2'],['W-2','W-4'],['P7','W-3'],['W-7','W-11a/PR-1'],['G-C3a','G-C3b'],['W-11a/PR-3','W-7'],['W-10','W-6'],['P4-core','W-6','P8'],['P4-core','S-1'],['W-11a/PR-4','W-1']]:
    for slots in (False,True):
        bad=[(a,b,sorted(fs(a,slots)&fs(b,slots))) for a,b in itertools.combinations(grp,2) if fs(a,slots)&fs(b,slots)]
        print(grp,'merge(slots)' if slots else 'dev(no-slots)', 'DISJOINT' if not bad else bad)
