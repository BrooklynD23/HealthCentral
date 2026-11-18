"""HC-MIF-001..002: ``import models`` registers every model table.

Both tests run ``import models`` in a fresh interpreter. Pytest collection
already imports ``models.response_feedback`` through other test modules, so an
in-process check would pass even when ``models/__init__.py`` omits it.
"""

import ast
import json
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = BACKEND_DIR / "models"


def _run_backend_python(code: str) -> str:
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _declared_tablenames() -> set[str]:
    """Every class-level ``__tablename__ = "<str>"`` in models/*.py."""
    names: set[str] = set()
    for path in sorted(MODELS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
            for stmt in cls.body:
                if isinstance(stmt, ast.Assign):
                    targets, value = stmt.targets, stmt.value
                elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
                    targets, value = [stmt.target], stmt.value
                else:
                    continue
                if (
                    any(isinstance(t, ast.Name) and t.id == "__tablename__" for t in targets)
                    and isinstance(value, ast.Constant)
                    and isinstance(value.value, str)
                ):
                    names.add(value.value)
    return names


def test_hc_mif_001_import_models_registers_response_feedback():
    out = _run_backend_python(
        "import models; "
        "from core.profile_database import ProfileDatabaseBase; "
        "print('response_feedback' in ProfileDatabaseBase.metadata.tables)"
    )
    assert out == "True"


def test_hc_mif_002_import_models_registers_every_declared_table():
    registered = set(
        json.loads(
            _run_backend_python(
                "import json, models; "
                "from core.database import Base; "
                "from core.profile_database import ProfileDatabaseBase; "
                "print(json.dumps(sorted(set(Base.metadata.tables) "
                "| set(ProfileDatabaseBase.metadata.tables))))"
            )
        )
    )
    declared = _declared_tablenames()

    # An empty or partial scan must not pass trivially.
    assert declared, "AST scan found no __tablename__ in models/*.py"
    assert "response_feedback" in declared, "AST scan missed response_feedback"

    assert registered == declared, (
        f"declared in models/*.py but not registered by `import models`: "
        f"{sorted(declared - registered)}; "
        f"registered but not declared by an AST-visible __tablename__: "
        f"{sorted(registered - declared)}"
    )
