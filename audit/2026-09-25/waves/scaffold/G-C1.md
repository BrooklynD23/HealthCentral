**BLOCKED** — hard dependencies P5, W-2, P6 and P7 are not merged on `origin/main`; the first missing one is P5.

# G-C1 — Persist export artifacts (W-11b) · readiness pack (sections 1-3 only)

**Written:** 2026-10-07 · **Measured on:** worktree `hc-scaffold` @ `8d6f02e`, `origin/main` = `6b4dd84` · **Plan:** [`docs/plans/2026-09-27-W11b-roadmap-items-gc1-gc4.md`](../../../../docs/plans/2026-09-27-W11b-roadmap-items-gc1-gc4.md) (Tasks C1.0-C1.5) · **Status:** scaffold only. Nothing here is implemented, signed or approved. Work stops at the blocker; sections 4-7 are not written.

## 1. Readiness verdict

| Dependency / gate | State |
|---|---|
| P0-B2 (plan set on main, PR #19) | merged |
| P1 (A + B) | merged |
| D9 venv | present |
| **P5** | **NOT merged** → BLOCKED |
| **W-2** (doctor-summary redaction; G-C1 persists the redacted dict) | **NOT merged** |
| **P6** (profile head `013`; G-C1 adds `014`) | **NOT merged** |
| **P7** (`_SYNTHETIC_RESET_MODELS`) | **NOT merged** |
| S-C1-1 (go + storage design; blocks all of G-C1) | **UNSIGNED** |
| S-C1-2 (docstring in `api/profiles.py`) | **UNSIGNED** |

Architectural phase (orchestration §5: "persisted export store"): Codex plan review + diff review apply once unblocked. security-reviewer applies (export, PHI at rest, auth file).

## 2. Task 0 evidence (measured; the plan's own Task C1.0 probes, run against `origin/main`)

| Check | Command | Output |
|---|---|---|
| base | `git rev-parse --short origin/main` | `6b4dd84` |
| P1 | `git merge-base --is-ancestor 7b2ff1f origin/main && git merge-base --is-ancestor 692fdf3 origin/main && echo post-P1-ok` | `post-P1-ok` |
| D9 venv | `~/venvs/asclexis-311/bin/python --version` | `Python 3.11.16` |
| **P5 missing** | `git grep -c 'datetime.utcnow' origin/main -- src/backend/api/export.py src/backend/modules/export.py` | `origin/main:src/backend/modules/export.py:2` (the plan expects 0 for both) |
| **W-2 missing** | `git grep -n 'redact_summary_data' origin/main -- src/backend/api/export.py \| wc -l` | `0` (plan expects ≥ 1) |
| W-2 missing | `ls src/backend/tests/test_export_redaction.py` | No such file |
| **P6 missing** | `git ls-tree --name-only origin/main src/backend/migrations/profile/versions/ \| tail -1` | `…/012_pinboards.py` (plan expects head `013_fk_cascade_alignment`) |
| **P7 missing** | `git grep -n '_SYNTHETIC_RESET_MODELS' origin/main -- src/backend/api/profiles.py \| wc -l` | `0` (plan expects ≥ 1) |
| P7 missing | `git grep -il 'hc_reset_010' origin/main -- src/backend/tests \| wc -l` | `0` (plan expects 1 file) |
| open PRs on shared files | `gh pr list --state open` | only #49 (docs); none touches `api/profiles.py` or `api/export.py` |
| plan tracked | `git ls-files docs/plans/2026-09-27-W11b-roadmap-items-gc1-gc4.md` | path printed; also on `origin/main` |

**Owner gates**

| Gate | Row | State |
|---|---|---|
| P0-B2 | `docs/capstone-report/owner-decisions-2026-09-27.md:28` | signed |
| D9 / D9-SRC | `owner-decisions-2026-09-27.md:12`, `:29` | signed |
| SLOT-RULE | `owner-decisions-2026-09-27.md:31` | signed |
| S-C1-1 | `grep -n "S-C1" owner-decisions-2026-09-27.md` → 0 rows; plan `:1944` has no name or date | **UNSIGNED** |
| S-C1-2 | 0 rows; plan `:1945` blank | **UNSIGNED** |
| S-C3-1, S-C3-3 (`:48`, `:49`) | signed, but they are G-C3's gates | n/a |

Plan `:87-92`: "G-C1: no owner option text … The whole group is owner-gated on S-C1-1".

## 3. Owner questions still to ask (after P5, W-2, P6 and P7 merge)

**Q1 — S-C1-1, go and storage design (blocks everything; plan `:1944`, wording kept).**
"Persist doctor-summary, visit-prep/pinboard and FHIR artifacts as rows in a new profile-vault table `export_artifact` (profile migration `014`), kept until profile deletion. Download requires the vault unlocked. `ExportArtifact` is added to P7's reset tuple in `api/profiles.py` (that line only). Nine existing direct-call tests change mechanism with every assertion kept; four of them (HC-PKT-014/015, HC-FHIR-103/104) remain legacy direct-call status checks. The rollback keeps migration 014. No list UI and no TTL now."

| Option | Effect |
|---|---|
| **(a) Sign as written (vault table)** — the plan's recommendation | No new PHI location: rows live in the same SQLCipher `vault.db` and are erased with the vault. After a real restart the first download returns 403 until the user logs in again. |
| (b) Encrypted files under the profile directory | A new PHI-at-rest location and new crypto calls; the plan rejects it and no decision covers it. |
| (c) Do not persist; document PRIV-08 as accepted | Downloads keep returning 404 after a restart. |

**Q2 — retention (plan O-C1-3; relevant to D10's HIPAA-aligned posture).** "Stored artifacts are derived copies of vault data. Keep them how long?" Options: **(a) until profile deletion, no prune job now — the plan's recommendation**; (b) a TTL (new job, separate decision); (c) delete on first download.

**Q3 — "recent exports" list (plan O-C1-2).** "After restart + re-login the SPA has lost the artifact ID (held only in React state), so persistence helps only while the page stays open. Add a list route and UI?" Options: **(a) not now — the plan's recommendation** (the program's acceptance asks only that a download succeeds after a restart); (b) add it (new route + UI + audit; a separate plan).

**Q4 — S-C1-2, docstring in ask-first `api/profiles.py` (plan `:1945`).**
"Amend the `delete_profile` docstring at `api/profiles.py:799-803` (one sentence) so it says downloadable export artifacts live in the vault and are erased with it."

| Option | Effect |
|---|---|
| **(a) Yes, one sentence, in its own commit** — the plan's recommendation | The docstring stops contradicting the code. |
| (b) No | The sentence "the export routes stream downloads rather than writing files server-side" stays, and is false after G-C1 (it is already false for `POST /feedback/export`, RL-EXPORTS). |

**Q5 — RL-EXPORTS (security; not in G-C1's scope).** "`src/backend/rl_exports/` is not git-ignored and is not swept by `DELETE /profiles`. G-C1 fixes only the docstring. Schedule the fix?" Options: **(a) its own small ask-first plan before or beside G-C1 (gitignore + erase sweep + test) — the program's proposal**; (b) fold it into G-C1 (edits the crypto-erase delete flow in `api/profiles.py`, which plan `:105` says G-C1 does not license); (c) leave it registered.

**Q6 — legacy direct-call tests (plan F-6).** "HC-PKT-014/015 and HC-FHIR-103/104 assert 403/404 by calling handlers as plain functions (recurring-failures #1). G-C1 keeps them and covers the same behaviour over HTTP in HC-EXPA-003/004/005/010. Convert or delete the four?" Options: **(a) keep as the plan says, not relied on — recommended for G-C1's scope**; (b) convert to `route_client` in G-C1 (more diff in two test files); (c) delete after the HTTP tests land.

**Ask-first edits in G-C1**

| File | Edit | Covered? |
|---|---|---|
| `src/backend/api/profiles.py` — P7's `_SYNTHETIC_RESET_MODELS` | add `ExportArtifact` (+ its import) | inside S-C1-1's text ("that line only"); **unsigned** |
| `src/backend/api/profiles.py:799-803` | one-sentence docstring | S-C1-2; **unsigned** |
| `src/backend/api/profiles.py` delete flow (crypto-erase) | none; the vault sweep already removes `vault.db` (plan `:300`) | n/a |
| `modules/redaction.py`, `interpret_safety.py`, `faithfulness.py`, `verifier_agent.py`, `core/auth.py`, `core/security.py`, `core/profile_database.py`, `core/migrations.py`, `core/document_crypto.py` | none; read-only, zero diff required (plan `:44`, `:241-243`) | n/a |

Non-ask-first files G-C1 edits or creates: `models/export_artifact.py` (new), `models/__init__.py`, `migrations/profile/versions/014_export_artifacts.py` (new; number = head + 1 measured at Task C1.0), `api/export.py`, `api/pinboards.py`, `tests/test_export_artifact_persistence.py` (new, 16 HC-EXPA items), `tests/test_care_tasks.py` (2 head literals), `tests/test_visit_prep_packet.py`, `tests/test_fhir_export.py`.

**Carry into the drift check once unblocked (seen while reading, not checked in depth):**
- Every `path:line` in the plan is against `main@40f590e`; `api/profiles.py`, `api/export.py` and `api/pinboards.py` will have been edited by P5, P7 and W-2 first.
- `tests/test_care_tasks.py:809,825` still read `"012_pinboards"` today (MATCH); P6 changes them to `013…`, G-C1 to `014…`.
- The plan's ask-first list names `core/document_crypto.py`; existence UNMEASURED by this pass.
- PR #45 (G-C3b) and PR #48 (SAFE-INTERP) merged after the plan was written; neither touches G-C1's files as far as this pass read (`main.py`, `monitoring/`, `api/interpretations.py`).
- AUDIT-ORDER ("Plan only", `owner-decisions:63`) applies to any new audit row G-C1's routes write.

**Next action:** wait for P5 → {W-2, P6 → P7} to merge, then re-run the four probes in §2 (expect `0`, `≥1`, a `013_…` head, `≥1`), ask Q1 and Q4 first, and write sections 4-7.
