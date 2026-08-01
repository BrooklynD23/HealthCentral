"""HealthCentral read-only plan->act->reflect agent (E1 — Agent Core).

SCAFFOLD ONLY. Bodies raise NotImplementedError; feature logic lands sprint by
sprint per docs/agile/sprints/. Governing skill: skills/asclexis-agent.

The one inviolable rule: the agent is READ-ONLY over clinical data. No module
here may write an observation, interpretation, medication, or any clinical row.
Write capability is a NEW epic, never a story (AGILE_PLAN §7).

All behavior sits behind the ``agent_enabled`` flag (see ``settings.py``); when
off, ``/assistant/chat`` must behave exactly as the legacy single-shot path.

These modules intentionally depend only on the standard library + pydantic so
they import-clean and collect under pytest without the full backend dependency
tree (see docs/agile/RECONCILIATION.md R-2). Real integration points
(core.audit, modules.redaction, the profile DB session, the RAG retriever) are
referenced in docstrings and wired at implementation time, not imported here.
"""
