# Sprint Plan Review and Audit Checklist

**Last Updated:** 2026-02-15
**Owner:** Review Agent
**Refresh Trigger:** Any sprint doc modification

## Purpose

Provide a deterministic review flow for auditing sprint plans before implementation begins.

## Step 1 - Completeness Review

- Confirm every PM finding from `docs/plans/pm-complete-unimplemented-features-2026-02-15.md` is mapped to at least one sprint doc.
- Confirm each sprint doc includes:
  - architecture scope
  - concrete file paths
  - acceptance criteria and/or test targets
  - dependency notes

## Step 2 - Sequence and Dependency Audit

- Validate that cross-sprint dependencies are explicit and technically coherent.
- Flag any work package that depends on undefined contracts or missing schemas.
- Confirm parallelizable items are not incorrectly serialized.

## Step 3 - Implementation Readiness Audit

- Check that new files are explicitly marked as `(new)` where applicable.
- Check that modified existing files are named at least once per work package.
- Check that each sprint has a test plan aligned to the scope.

## Step 4 - Governance and Documentation Checks

- Run `python3 scripts/docs_lint.py`.
- Confirm `docs/00_architecture_plans_index.md` references active sprint planning docs.
- Confirm no historical docs are presented as active trackers.

## Signoff Template

- Review date:
- Reviewer:
- Blocking issues:
- Non-blocking recommendations:
- Approval status: Approved / Changes Requested
