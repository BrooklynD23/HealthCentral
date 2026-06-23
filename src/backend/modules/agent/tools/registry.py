"""Typed tool registry (Phase 1, story S1-1).

Resolves a tool by name and validates args against its InputModel BEFORE
execution. Malformed args -> ValidationError, never executed. The registry only
ever holds read-only tools; a registry test asserts no tool exposes a write path
(invariant SG-6).
"""

from __future__ import annotations

from .base import ReadOnlyTool, ToolInput

_REGISTRY: dict[str, ReadOnlyTool] = {}


def register(tool: ReadOnlyTool) -> ReadOnlyTool:
    """Register a read-only tool by its ``name``. SCAFFOLD: S1-1."""
    raise NotImplementedError("S1-1: register read-only tool; reject duplicates")


def get(name: str) -> ReadOnlyTool:
    """Look up a registered tool by name. SCAFFOLD: S1-1."""
    raise NotImplementedError("S1-1: resolve tool or raise KeyError")


def validate_args(name: str, raw_args: dict) -> ToolInput:
    """Validate raw args against the tool's InputModel (the first guardrail layer).

    SCAFFOLD: S1-1. Must raise pydantic.ValidationError on malformed input so the
    args NEVER reach ``run``.
    """
    raise NotImplementedError("S1-1: validate raw_args against tool.InputModel")
