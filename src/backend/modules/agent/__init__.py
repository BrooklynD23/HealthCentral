"""Asclexis read-only plan->act->reflect agent (E1 — Agent Core).

SHIPPED: this is the default ``/assistant/chat`` path
(``settings.AGENT_ENABLED_DEFAULT = True``). The per-profile ``agent_enabled``
setting is a kill switch back to the legacy single-shot RAG path, not a gate for
unfinished code. Any agent exception also falls back to the legacy path.

The one inviolable rule: the agent is READ-ONLY over clinical data. No module
here may write an observation, interpretation, medication, or any clinical row.
Write capability is a NEW epic, never a story (AGILE_PLAN §7).

Contents: the graph runner, the plan/act/reflect/draft nodes (draft composes
from templates and makes no LLM call), the read-only tool registry (8 tools),
the guardrails, and the eval scorer. Several modules import backend packages
(SQLAlchemy models, ``core.audit``, ``modules.faithfulness``,
``modules.redaction``), so the package no longer imports with only the standard
library and pydantic. Changes here affect the production safety path: read
skills/asclexis-agent and skills/asclexis-guardrails first.
"""
