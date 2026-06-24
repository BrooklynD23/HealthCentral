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
    """Register a read-only tool by its ``name``; reject duplicate names."""
    if tool.name in _REGISTRY:
        raise ValueError(f"tool already registered: {tool.name!r}")
    _REGISTRY[tool.name] = tool
    return tool


def get(name: str) -> ReadOnlyTool:
    """Look up a registered tool by name, or raise KeyError."""
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(f"no such tool registered: {name!r}") from None


def validate_args(name: str, raw_args: dict) -> ToolInput:
    """Validate raw args against the tool's InputModel (the first guardrail layer).

    Raises ``pydantic.ValidationError`` on malformed input so the args NEVER
    reach ``run``. Raises ``KeyError`` if ``name`` is not registered.
    """
    tool = get(name)
    return tool.InputModel(**raw_args)


def _register_builtin_tools() -> None:
    """Register Sprint 1's read-only tool(s). Idempotent across re-imports."""
    from .query_observations import QueryObservationsTool

    if QueryObservationsTool.name not in _REGISTRY:
        register(QueryObservationsTool())


_register_builtin_tools()
