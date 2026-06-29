"""Adapter from the master-DB knowledge base to the agent's ``ReferenceRange``.

Thin wrapper around ``modules.knowledge_loader.KnowledgeLoader`` so
``tools/lookup_reference.py`` stays a simple read-call. This is curated
master-DB data (``BiomarkerKnowledge``), never PHI (PRD reconciliation R-5
context: chunks/observations are profile-scoped PHI; this is not).
"""

from __future__ import annotations

from typing import Any


async def lookup_reference_range(analyte: str, master_db: Any):
    """Return a ``ReferenceRange`` for ``analyte`` from the knowledge base, or ``None``.

    ``ref_range_adult_json`` is keyed by demographic (e.g. "default", "male",
    "female"); the "default" bucket is preferred when present, else the first
    available bucket. Returns ``None`` (not an error) when the analyte has no
    knowledge-base entry or no usable range — the caller treats that as a
    graceful "no curated reference available".
    """
    from .tools.lookup_reference import ReferenceRange
    from ..knowledge_loader import get_knowledge_loader

    loader = get_knowledge_loader()
    info = await loader.get_biomarker_knowledge(analyte, master_db)
    if info is None:
        return None

    ref_range = info.ref_range_adult or {}
    bucket = ref_range.get("default") or next(iter(ref_range.values()), None)
    if not bucket:
        return None

    return ReferenceRange(
        analyte=info.analyte_canonical,
        low=bucket.get("low"),
        high=bucket.get("high"),
        unit=info.standard_unit or None,
    )
