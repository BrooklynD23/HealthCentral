# High-Reasoning Goal Prompt — Asclexis Plan and Contract Recovery

**Use:** Start a fresh session with the highest-reasoning agent available, invoke its `/goal` (or equivalent project-planning slash command), and paste the goal block below. The repository has a prior `/goal` handoff at `audit/2026-09-25/handoff-prompt-claude-orchestrator.md`; this prompt supersedes its planning scope where the two differ.

```text
/goal Reconcile and repair the Asclexis audit, research, and proposal package against the live HealthCentral repository. Produce an evidence-backed architecture and integration overview, a normative architecture/engineering contract, a specs-compliance matrix, and a safe, dependency-ordered implementation program. Correct material errors in the existing research, claims, handoffs, and execution plans. Preserve the existing independent review as history and publish a dated follow-up that dispositions every finding. Planning and documentation only: do not implement product changes, merge branches, or commit.
```

## Goal charter

You are the planning orchestrator for Asclexis / HealthCentral, a local-first medical-results companion and a CS4610 capstone studying agentic software engineering. Use the highest-reasoning model available. You may delegate independent read-only research, architecture mapping, source verification, and adversarial review to a sub-orchestrator and subagents. Keep one owner for edits and final integration; assign non-overlapping read/review slices; reconcile disagreements against repository evidence. Do not let a subagent's conclusion substitute for verification.

### Start with current state

1. Read `AGENT.md`, `CLAUDE.md`, `docs/agentic/recurring-failures.md`, and `docs/00_architecture_plans_index.md` before editing. Respect their invariants, protected paths, and documentation rules.
2. Run `git status --short`, `git rev-parse HEAD`, and inspect relevant branch refs before relying on dated audit facts. Preserve all pre-existing edits and untracked files. The prior review observed changes to `.serena/project.yml` and `docs/INDEX.md`; treat them as user-owned unless the current checkout proves otherwise.
3. Treat dates, commit hashes, test totals, branches, local user configuration, owner approvals, and external research as time-sensitive. Recheck them or mark them historical/unverified. Do not claim tests passed when they were not run.

### Source package to reconcile

Read the complete current contents of these sources; do not rely on the prior handoff's summaries:

- Original goal and report package: `docs/capstone-report/00-original-goal.md`, `claims-ledger.md`, `report-outline.md`, `README.md`, and every file in `docs/capstone-report/research/`.
- Prior audit and proposals: `audit/2026-09-25/Devin-Audit-report.md`, both `audit/2026-09-25/handoff-prompt-*.md` files, all eight `audit/2026-09-25/plans/0*.md`, and `audit/2026-09-25/asclexis-showcase.html` (context only; do not treat the showcase as an audit artifact).
- Independent review to disposition: `audit/2026-09-25/review/Asclexis-Package-Review.md`. Preserve this file unchanged. Add a dated follow-up beside it.
- Architecture/product references: `docs/architecture/README.md` and all Markdown files in `docs/architecture/`; `docs/01_backend_architecture_plan.md` through `docs/04_local_models_inference_plan.md`; `docs/Local_First_Medical_Results_Companion_PRD_v0_1.md`; `docs/features/03_features_prd.md`; `docs/api/endpoints.md`; and relevant entries in `docs/features/TASK_LIST.md`.
- Verify implementation claims directly in the current source, tests, migrations, CI workflows, and repository configuration. Follow links to the cited primary research, vendor documents, and legal sources when available. Date-stamp external-source checks and distinguish primary evidence from vendor claims and owner preference.

### Required work

**1. Reconcile the evidence and repair the document package.** For every finding F-01 through F-17 in the prior review, record exactly one status: `confirmed`, `fixed`, `partly fixed`, `stale`, `refuted`, or `open`. Give current evidence (`file:line`, command/output, commit, or source link), the resulting action, and remaining uncertainty. Recheck each finding against the present checkout. Then correct the material errors in affected research files, research index, claims ledger, original goal, report outline, README, handoffs, and plans. Keep historical audit claims distinguishable from current repository state; use scoped corrections/addenda when changing an audit would erase provenance. Do not silently change the independent review.

**2. Create `docs/capstone-report/specs-compliance-matrix.md`.** Map each product, privacy, safety, data-isolation, LLM, export, migration, and engineering invariant to its authoritative source; implementation and tests; enforcement gate; current status; evidence; and owner/approval gate where applicable. Show unenforced or partial controls as gaps. Do not call a legal conclusion, owner preference, proposal, comment, or document statement an implemented control.

**3. Create `docs/capstone-report/architecture-overview.md`.** Describe verified current architecture and separately labeled proposed changes. Include system/process boundaries, frontend-to-API flow, module/service boundaries, master DB versus per-profile encrypted vaults, document and assistant paths, model boundary, network boundary, migrations, background jobs, and CI/test gates. Include a Mermaid integration diagram and a concise table of subsystem, owning module, input/output, persistence/security boundary, and dependencies. Mark unknowns and divergences from existing architecture diagrams; do not draw proposed behavior as current behavior.

**4. Create `docs/capstone-report/architecture-engineering-contract.md`.** State testable contracts for privacy/local-first behavior, profile isolation, SQLCipher/key lifecycle, human verification, assistant citations and medical-safety limits, redaction-before-export, ModelRunner-only inference, timestamp semantics, migration ownership, API/frontend integration, background scheduling, audit data, and verification gates. For each contract include scope, MUST/MUST NOT rule, enforcement location, verification evidence/command, failure response, and any unresolved decision owner. Separate binding repo invariants from proposed engineering decisions and owner-gated choices.

**5. Create `docs/capstone-report/implementation-program.md`.** Replace the stale pending plan with an executable planning document that sequences the eight existing plans and audit workstreams, incorporates the review corrections, and covers gaps with no existing plan. Each phase needs: outcome, inputs/owned files, dependencies, explicit stop gates, verification commands, measured acceptance criteria, rollback/recovery notes where relevant, and owner sign-offs. Represent dependencies as a Mermaid graph or equivalent table. Never use guessed test-count deltas as acceptance criteria; require a measured baseline from the actual target tree. Distinguish documentation preparation from product implementation and from owner approval. Do not execute the program.

**6. Publish the review follow-up and navigation.** Add `audit/2026-09-25/review/2026-09-27-followup.md` with the 17-item disposition table, evidence, corrected document locations, unresolved blockers, and independent-review summary. Update `docs/capstone-report/README.md` and `report-outline.md` to link to the four deliverables and follow-up, refresh dates, and correct pending/status language. Update `docs/00_architecture_plans_index.md` only if needed to make the new canonical documents discoverable; preserve unrelated edits and keep links valid.

### Decision and evidence rules

- Use the live checkout as the authority for current implementation facts; use the prior review as a checklist, not an unquestionable verdict. Cite specific evidence for every changed verdict.
- Keep these states distinct: `implemented`, `wired`, `tested`, `proposed`, `owner-approved`, `owner-gated`, and `unknown`. One state never implies another.
- Preserve all safety and privacy invariants. In particular, do not weaken guards, lower evaluation thresholds, route PHI over a network, bypass `ProfileDbSession`, bypass redaction, add direct LLM access outside `ModelRunner`, or change data deletion/foreign-key semantics without explicit evidence and owner approval.
- Reconcile conflicting proposals explicitly. For each, record source, evidence, decision, rationale, dependencies, and who has authority to approve it. Do not invent owner approval or resolve a product/legal decision on the owner's behalf.
- Correct unsupported causal, economic, benchmark, hardware, compliance, and quantified multi-agent claims. Present observations as case studies unless the underlying denominators, protocol, and raw evidence support stronger language.
- Mark inaccessible sources, absent artifacts, unavailable dependencies, and unrun checks as blocked/unverified with the exact reason. Never fabricate output or claim comprehensive research verification from a sample.
- Keep `audit/2026-09-25/review/Asclexis-Package-Review.md` unchanged; its follow-up is additive and may respectfully disagree when new evidence warrants it.

### Independent review and validation

Before finalizing, have at least one independent reviewer inspect the proposed contracts and implementation sequence against the repository, and one reviewer check evidence/claims and the F-01–F-17 dispositions. Reviewers should be read-only and report exact paths/lines. The orchestrator owns all edits and reconciles each material objection in the follow-up or work summary. Parallel work must not write the same files.

Run only relevant documentation/link checks that are available and safe in the current environment. Report commands and actual outputs. Do not run production implementation, branch merges, commits, or broad tests unrelated to these documentation artifacts. If a check needs missing dependencies, report it as unrun with the exact blocker.

### Completion criteria

The goal is complete only when:

1. All 17 review findings have evidence-backed dispositions; no blocker is disguised as resolved.
2. The four required capstone documents exist, are mutually consistent, and separate current architecture from proposed work.
3. Material source/research/proposal errors are corrected or explicitly marked open, and the navigation links to the deliverables resolve.
4. Independent reviewers' findings are reconciled, and documentation validation results are reported honestly.
5. Your final response names changed files, key corrections, validation run/unrun, unresolved owner gates, and one immediate next action. Do not claim product work was implemented.
```

## Scope note

This prompt authorizes a documentation correction and planning pass. It does not authorize implementation of the eight plans, code changes, merges, commits, or decisions reserved for the product owner.
